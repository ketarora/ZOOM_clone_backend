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
    now = datetime.now(timezone.utc)

    all_meetings: list[Meeting] = (
        db.query(Meeting).order_by(Meeting.created_at.desc()).all()
    )

    active = [m for m in all_meetings if m.status == "active"]
    upcoming = [
        m
        for m in all_meetings
        if m.status == "waiting" and m.scheduled_at and m.scheduled_at >= now
    ]
    recent = [m for m in all_meetings if m.status == "ended"]

    def _read(m: Meeting) -> MeetingRead:
        return MeetingRead.model_validate(m)

    return DashboardSummary(
        total_meetings=len(all_meetings),
        upcoming_count=len(upcoming),
        recent_count=len(recent),
        active_meetings=[_read(m) for m in active],
        upcoming_meetings=[_read(m) for m in upcoming[:5]],
        recent_meetings=[_read(m) for m in recent[:5]],
    )
