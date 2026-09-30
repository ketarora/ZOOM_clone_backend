"""ORM model registry.

Importing this package guarantees that every model class is registered on
``Base.metadata`` (required by ``create_all``).

``participant_count`` on ``Meeting`` is defined here — after both ``Meeting``
and ``Participant`` are imported — to break the circular-reference that would
arise if it were defined inside ``meeting.py``.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import column_property

from app.models.meeting import Meeting
from app.models.participant import Participant
from app.models.user import User

# Correlated subquery: live active-participant count computed in SQL.
# "Active" means the participant has not yet left (left_at IS NULL).
Meeting.participant_count = column_property(  # type: ignore[assignment]
    select(func.count(Participant.id))
    .where(
        Participant.meeting_id == Meeting.__table__.c.id,
        Participant.left_at.is_(None),
    )
    .correlate_except(Participant)
    .scalar_subquery(),
    deferred=False,
)

__all__ = ["User", "Meeting", "Participant"]
