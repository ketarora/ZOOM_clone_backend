"""Dashboard router — aggregated stats for the home screen.

The response schema intentionally mirrors the TypeScript ``DashboardSummary``
interface used by the frontend (field names serialised as camelCase via the
``alias_generator``).
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, alias_generators
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.meeting import Meeting
from app.schemas.meeting import MeetingRead

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_CAMEL_CONFIG = ConfigDict(
    alias_generator=alias_generators.to_camel,
    populate_by_name=True,
)


class DashboardSummary(BaseModel):
    """Matches the frontend ``DashboardSummary`` TypeScript interface exactly."""

    model_config = _CAMEL_CONFIG

    total_meetings: int
    upcoming_count: int
    recent_count: int
    active_meetings: list[MeetingRead]
    upcoming_meetings: list[MeetingRead]
    recent_meetings: list[MeetingRead]


@router.get(
    "/summary",
    response_model=DashboardSummary,
    summary="Dashboard summary",
    description=(
        "Returns aggregated meeting counts and up to 5 representative meetings "
        "in each category (active, upcoming, recently ended)."
    ),
)
def get_dashboard_summary(db: Session = Depends(get_db)) -> DashboardSummary:
    from sqlalchemy import func as _func

    total_meetings: int = db.query(_func.count(Meeting.id)).scalar() or 0
    upcoming_count: int = (
        db.query(_func.count(Meeting.id))
        .filter(Meeting.status.in_(["waiting", "active"]))
        .scalar()
        or 0
    )
    recent_count: int = (
        db.query(_func.count(Meeting.id))
        .filter(Meeting.status == "ended")
        .scalar()
        or 0
    )

    active = (
        db.query(Meeting)
        .filter(Meeting.status == "active")
        .order_by(Meeting.created_at.desc())
        .limit(5)
        .all()
    )
    upcoming = (
        db.query(Meeting)
        .filter(Meeting.status.in_(["waiting", "active"]))
        .order_by(Meeting.scheduled_at.asc().nulls_last(), Meeting.created_at.desc())
        .limit(5)
        .all()
    )
    recent = (
        db.query(Meeting)
        .filter(Meeting.status == "ended")
        .order_by(Meeting.created_at.desc())
        .limit(5)
        .all()
    )

    def _read(m: Meeting) -> MeetingRead:
        return MeetingRead.model_validate(m)

    return DashboardSummary(
        total_meetings=total_meetings,
        upcoming_count=upcoming_count,
        recent_count=recent_count,
        active_meetings=[_read(m) for m in active],
        upcoming_meetings=[_read(m) for m in upcoming],
        recent_meetings=[_read(m) for m in recent],
    )
