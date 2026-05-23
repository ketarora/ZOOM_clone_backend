"""Meetings router — full CRUD plus join, end, and participant listing.

Route ordering matters in FastAPI: ``/join/{meeting_id}`` and
``/{meeting_id}/end`` are declared *before* the generic ``/{meeting_id}``
GET/PATCH/DELETE routes so the router resolves them correctly without
ambiguity.

Lookup strategy for ``{meeting_id}`` path parameters
------------------------------------------------------
1. Normalise the raw string to ``XXX XXX XXXX`` format.
2. Exact match on the indexed ``meeting_id`` column.
3. If the raw value is a plain integer, fall back to the integer PK.
Full-table scans (LIKE queries, loading all rows into Python) are never used.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.models.meeting import Meeting
from app.models.participant import Participant
from app.models.user import User
from app.schemas.meeting import MeetingCreate, MeetingFilter, MeetingRead, MeetingUpdate
from app.schemas.participant import JoinMeetingInput, ParticipantRead
from app.utils.meeting_utils import (
    generate_invite_link,
    generate_meeting_id,
    normalize_meeting_id,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/meetings", tags=["meetings"])

# ---------------------------------------------------------------------------
# Default host constants — in a real multi-user system these would come from
# the auth token.  Kept here until authentication is wired up so all logic is
# in one place rather than scattered across the codebase.
# ---------------------------------------------------------------------------
_DEFAULT_HOST_EMAIL = "ketan.arora019@gmail.com"
_DEFAULT_HOST_NAME = "Ketan Arora"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_or_create_default_host(db: Session) -> User:
    """Return the seeded default host, creating the record if absent."""
    host = db.query(User).filter(User.email == _DEFAULT_HOST_EMAIL).first()
    if not host:
        logger.info("Creating default host user '%s'", _DEFAULT_HOST_EMAIL)
        host = User(display_name=_DEFAULT_HOST_NAME, email=_DEFAULT_HOST_EMAIL)
        db.add(host)
        db.flush()
    return host


def _lookup_meeting(db: Session, raw_id: str) -> Meeting:
    """Resolve a meeting from a raw path parameter.

    Tries normalised ``meeting_id`` first (indexed, O(log n)), then falls
    back to the integer primary key.  Raises ``NotFoundError`` if nothing
    matches.
    """
    normalised = normalize_meeting_id(raw_id)

    meeting: Meeting | None = (
        db.query(Meeting)
        .filter(Meeting.meeting_id == normalised)
        .first()
    )

    if meeting is None and raw_id.isdigit():
        meeting = db.query(Meeting).filter(Meeting.id == int(raw_id)).first()

    if meeting is None:
        raise NotFoundError("Meeting", raw_id)

    return meeting


def _to_read(meeting: Meeting) -> MeetingRead:
    return MeetingRead.model_validate(meeting)


# ---------------------------------------------------------------------------
# POST /api/meetings/join/{meeting_id}
# Declared BEFORE /{meeting_id} so FastAPI routes it correctly.
# ---------------------------------------------------------------------------


@router.post(
    "/join/{meeting_id}",
    response_model=MeetingRead,
    summary="Join a meeting",
    description=(
        "Validates the meeting exists and is joinable, records a new Participant "
        "row, and transitions the meeting to **active** if it was waiting."
    ),
)
def join_meeting(
    meeting_id: str,
    body: JoinMeetingInput,
    db: Annotated[Session, Depends(get_db)],
) -> MeetingRead:
    meeting = _lookup_meeting(db, meeting_id)

    if meeting.status == "ended":
        raise BusinessRuleError("This meeting has already ended.")

    participant = Participant(
        meeting_id=meeting.id,
        user_id=None,
        display_name=body.display_name,
        is_host=False,
        is_admitted=True,
    )
    db.add(participant)

    if meeting.status == "waiting":
        meeting.status = "active"

    db.commit()
    db.refresh(meeting)
    logger.info("User '%s' joined meeting %s", body.display_name, meeting.meeting_id)
    return _to_read(meeting)


# ---------------------------------------------------------------------------
# GET /api/meetings
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=list[MeetingRead],
    summary="List meetings",
    description=(
        "Returns a paginated list of meetings.  Use ``type`` to filter by "
        "status: ``upcoming`` (scheduled/active), ``recent`` (ended), or ``all``."
    ),
)
def list_meetings(
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    type: Annotated[MeetingFilter | None, Query(description="Filter preset")] = None,
    page: Annotated[int, Query(ge=1, description="1-based page number")] = 1,
    page_size: Annotated[
        int, Query(ge=1, le=100, description="Records per page (max 100)")
    ] = 20,
) -> list[MeetingRead]:
    now = datetime.now(timezone.utc)
    offset = (page - 1) * page_size

    base = db.query(Meeting)

    if type == "upcoming":
        base = base.filter(
            or_(Meeting.scheduled_at >= now, Meeting.status == "active")
        ).order_by(Meeting.scheduled_at.asc())
    elif type == "recent":
        base = base.filter(Meeting.status == "ended").order_by(
            Meeting.created_at.desc()
        )
    else:
        base = base.order_by(Meeting.created_at.desc())

    total: int = base.count()
    meetings: list[Meeting] = base.offset(offset).limit(page_size).all()

    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Page"] = str(page)
    response.headers["X-Page-Size"] = str(page_size)

    return [_to_read(m) for m in meetings]


# ---------------------------------------------------------------------------
# POST /api/meetings
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=MeetingRead,
    status_code=201,
    summary="Create a meeting",
    description="Creates an **instant** (immediately active) or **scheduled** meeting.",
)
def create_meeting(
    body: MeetingCreate,
    db: Annotated[Session, Depends(get_db)],
) -> MeetingRead:
    host = _get_or_create_default_host(db)
    meeting_id = generate_meeting_id()

    meeting = Meeting(
        meeting_id=meeting_id,
        title=body.title,
        description=body.description,
        host_id=host.id,
        type=body.type,
        status="active" if body.type == "instant" else "waiting",
        scheduled_at=body.scheduled_at,
        duration_minutes=body.duration_minutes,
        invite_link=generate_invite_link(meeting_id),
        passcode=body.passcode,
    )
    db.add(meeting)
    db.flush()

    if body.type == "instant":
        db.add(
            Participant(
                meeting_id=meeting.id,
                user_id=host.id,
                display_name=host.display_name,
                is_host=True,
                is_admitted=True,
            )
        )

    db.commit()
    db.refresh(meeting)
    logger.info("Created meeting %s (type=%s)", meeting.meeting_id, body.type)
    return _to_read(meeting)


# ---------------------------------------------------------------------------
# GET /api/meetings/{meeting_id}
# ---------------------------------------------------------------------------


@router.get(
    "/{meeting_id}",
    response_model=MeetingRead,
    summary="Get a meeting",
)
def get_meeting(
    meeting_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> MeetingRead:
    return _to_read(_lookup_meeting(db, meeting_id))


# ---------------------------------------------------------------------------
# PATCH /api/meetings/{meeting_id}
# ---------------------------------------------------------------------------


@router.patch(
    "/{meeting_id}",
    response_model=MeetingRead,
    summary="Update a meeting",
    description="Partial update — only provided fields are changed.",
)
def update_meeting(
    meeting_id: str,
    body: MeetingUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> MeetingRead:
    meeting = _lookup_meeting(db, meeting_id)

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(meeting, field, value)

    db.commit()
    db.refresh(meeting)
    return _to_read(meeting)


# ---------------------------------------------------------------------------
# DELETE /api/meetings/{meeting_id}
# ---------------------------------------------------------------------------


@router.delete(
    "/{meeting_id}",
    status_code=204,
    summary="Delete a meeting",
)
def delete_meeting(
    meeting_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    meeting = _lookup_meeting(db, meeting_id)
    db.delete(meeting)
    db.commit()
    logger.info("Deleted meeting %s", meeting.meeting_id)
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# POST /api/meetings/{meeting_id}/end
# ---------------------------------------------------------------------------


@router.post(
    "/{meeting_id}/end",
    response_model=MeetingRead,
    summary="End a meeting",
    description=(
        "Transitions the meeting to **ended** and stamps ``left_at`` on every "
        "participant who is still active."
    ),
)
def end_meeting(
    meeting_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> MeetingRead:
    meeting = _lookup_meeting(db, meeting_id)

    if meeting.status == "ended":
        raise BusinessRuleError("Meeting is already ended.")

    now = datetime.now(timezone.utc)
    meeting.status = "ended"

    active_participants = (
        db.query(Participant)
        .filter(
            Participant.meeting_id == meeting.id,
            Participant.left_at.is_(None),
        )
        .all()
    )
    for p in active_participants:
        p.left_at = now

    db.commit()
    db.refresh(meeting)
    logger.info("Ended meeting %s", meeting.meeting_id)
    return _to_read(meeting)


# ---------------------------------------------------------------------------
# GET /api/meetings/{meeting_id}/participants
# ---------------------------------------------------------------------------


@router.get(
    "/{meeting_id}/participants",
    response_model=list[ParticipantRead],
    summary="List participants",
    description="Returns all participant records for the given meeting.",
)
def list_participants(
    meeting_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> list[ParticipantRead]:
    meeting = _lookup_meeting(db, meeting_id)
    participants = (
        db.query(Participant)
        .filter(Participant.meeting_id == meeting.id)
        .order_by(Participant.joined_at.asc())
        .all()
    )
    return [ParticipantRead.model_validate(p) for p in participants]
