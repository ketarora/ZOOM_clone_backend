"""Database seeder — populates the SQLite database with realistic demo data.

Run once after the initial setup:

    python seed.py

The script is idempotent: it exits early if any users already exist so that
re-running it on a populated database is always safe.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.database import SessionFactory, create_tables
from app.logging_config import configure_logging
from app.models.meeting import Meeting
from app.models.participant import Participant
from app.models.user import User
from app.utils.meeting_utils import generate_invite_link, generate_meeting_id

configure_logging()
logger = logging.getLogger("seed")

NOW = datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Seed data definitions
# ---------------------------------------------------------------------------

_USERS: list[dict[str, str | None]] = [
    {"display_name": "Ketan Arora",  "email": "ketan.arora019@gmail.com", "avatar_url": None},
    {"display_name": "Priya Sharma", "email": "priya.sharma@example.com",  "avatar_url": None},
    {"display_name": "Rahul Mehta",  "email": "rahul.mehta@example.com",   "avatar_url": None},
    {"display_name": "Anjali Singh", "email": "anjali.singh@example.com",  "avatar_url": None},
    {"display_name": "Vikram Nair",  "email": "vikram.nair@example.com",   "avatar_url": None},
]


def _make_meeting(
    *,
    title: str,
    description: str | None,
    host: User,
    meeting_type: str,
    status: str,
    scheduled_offset_hours: float | None = None,
    duration_minutes: int = 60,
    passcode: str | None = None,
) -> Meeting:
    mid = generate_meeting_id()
    return Meeting(
        meeting_id=mid,
        title=title,
        description=description,
        host_id=host.id,
        type=meeting_type,
        status=status,
        scheduled_at=(
            NOW + timedelta(hours=scheduled_offset_hours)
            if scheduled_offset_hours is not None
            else None
        ),
        duration_minutes=duration_minutes,
        invite_link=generate_invite_link(mid),
        passcode=passcode,
    )


def _make_participant(
    *,
    meeting: Meeting,
    user: User,
    is_host: bool,
    already_left: bool = False,
) -> Participant:
    return Participant(
        meeting_id=meeting.id,
        user_id=user.id,
        display_name=user.display_name,
        is_host=is_host,
        is_admitted=True,
        is_muted=not is_host,
        is_camera_off=True,
        joined_at=NOW - timedelta(minutes=15) if already_left else NOW,
        left_at=NOW if already_left else None,
    )


# ---------------------------------------------------------------------------
# Seed logic
# ---------------------------------------------------------------------------


def seed(db: Session) -> None:
    if db.query(User).count() > 0:
        logger.info("Database already contains data — skipping seed.")
        return

    # ── Users ──────────────────────────────────────────────────────────────
    users: list[User] = [User(**u) for u in _USERS]  # type: ignore[arg-type]
    db.add_all(users)
    db.flush()
    ketan, priya, rahul, anjali, vikram = users
    logger.info("Inserted %d users.", len(users))

    # ── Meetings ───────────────────────────────────────────────────────────
    meetings: list[Meeting] = [
        # ── Active (currently in progress) ──
        _make_meeting(
            title="Daily Standup",
            description="15-minute engineering sync",
            host=ketan,
            meeting_type="instant",
            status="active",
        ),
        _make_meeting(
            title="Frontend Component Review",
            description="Review new UI components before merge",
            host=priya,
            meeting_type="instant",
            status="active",
        ),
        # ── Upcoming (scheduled, not started) ──
        _make_meeting(
            title="Sprint Planning — Q3 2026",
            description="Plan sprint goals and assign tasks across teams",
            host=ketan,
            meeting_type="scheduled",
            status="waiting",
            scheduled_offset_hours=2,
            duration_minutes=90,
        ),
        _make_meeting(
            title="Product Demo — Client XYZ",
            description="Showcase the new dashboard and reporting features",
            host=ketan,
            meeting_type="scheduled",
            status="waiting",
            scheduled_offset_hours=24,
            duration_minutes=45,
            passcode="Demo2026",
        ),
        _make_meeting(
            title="Architecture Deep-Dive",
            description="Discuss migration path from monolith to microservices",
            host=rahul,
            meeting_type="scheduled",
            status="waiting",
            scheduled_offset_hours=48,
            duration_minutes=120,
        ),
        _make_meeting(
            title="Weekly All-Hands",
            description="Company-wide weekly update and announcements",
            host=ketan,
            meeting_type="scheduled",
            status="waiting",
            scheduled_offset_hours=72,
        ),
        _make_meeting(
            title="Design System Workshop",
            description="Standardise component library tokens and guidelines",
            host=anjali,
            meeting_type="scheduled",
            status="waiting",
            scheduled_offset_hours=96,
        ),
        # ── Ended (historical) ──
        _make_meeting(
            title="Onboarding — Vikram Nair",
            description="New joiner walkthrough: systems, processes, and tools",
            host=ketan,
            meeting_type="scheduled",
            status="ended",
            scheduled_offset_hours=-48,
            duration_minutes=30,
        ),
        _make_meeting(
            title="Bug Bash — May 2026",
            description="Identify and triage open bugs across all services",
            host=rahul,
            meeting_type="instant",
            status="ended",
        ),
        _make_meeting(
            title="Quarterly Business Review — Q1",
            description="Q1 results, Q2 targets, and board discussion",
            host=ketan,
            meeting_type="scheduled",
            status="ended",
            scheduled_offset_hours=-168,
            duration_minutes=90,
        ),
        _make_meeting(
            title="UX Research Findings",
            description="Key insights from the latest round of user interviews",
            host=priya,
            meeting_type="scheduled",
            status="ended",
            scheduled_offset_hours=-72,
        ),
    ]
    db.add_all(meetings)
    db.flush()
    logger.info("Inserted %d meetings.", len(meetings))

    (
        standup, fe_review,
        sprint_planning, client_demo, arch_dive, all_hands, design_ws,
        onboarding, bug_bash, qbr, ux_research,
    ) = meetings

    # ── Participants ────────────────────────────────────────────────────────
    participant_specs: list[tuple[Meeting, list[tuple[User, bool]]]] = [
        (standup,    [(ketan, True),  (priya, False), (rahul, False)]),
        (fe_review,  [(priya, True),  (anjali, False)]),
        (onboarding, [(ketan, True),  (vikram, False)]),
        (bug_bash,   [(rahul, True),  (ketan, False), (priya, False), (anjali, False)]),
        (qbr,        [(ketan, True),  (priya, False), (rahul, False), (anjali, False), (vikram, False)]),
        (ux_research,[(priya, True),  (ketan, False)]),
    ]

    participants: list[Participant] = []
    for meeting, attendees in participant_specs:
        already_left = meeting.status == "ended"
        for user, is_host in attendees:
            participants.append(
                _make_participant(
                    meeting=meeting,
                    user=user,
                    is_host=is_host,
                    already_left=already_left,
                )
            )

    db.add_all(participants)
    db.commit()
    logger.info("Inserted %d participant records.", len(participants))
    logger.info(
        "Seed complete — %d users · %d meetings · %d participants.",
        len(users),
        len(meetings),
        len(participants),
    )


def main() -> None:
    create_tables()
    db = SessionFactory()
    try:
        seed(db)
    except Exception:
        logger.exception("Seed failed — rolling back.")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
