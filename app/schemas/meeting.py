"""Pydantic schemas for Meeting I/O.

Serialisation
-------------
All response models use ``alias_generator=alias_generators.to_camel`` so the
wire format matches the frontend TypeScript interfaces exactly
(``meetingId``, ``hostName``, ``scheduledAt``, ``participantCount``, …).

``populate_by_name=True`` lets us still construct models with Python
snake_case names inside the application layer — aliases only affect the
JSON boundary.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, alias_generators

MeetingType = Literal["instant", "scheduled"]
MeetingStatus = Literal["waiting", "active", "ended"]
MeetingFilter = Literal["upcoming", "recent", "all"]

# ---------------------------------------------------------------------------
# Shared model config
# ---------------------------------------------------------------------------

_CAMEL_CONFIG = ConfigDict(
    alias_generator=alias_generators.to_camel,
    populate_by_name=True,
)

_ORM_CAMEL_CONFIG = ConfigDict(
    from_attributes=True,
    alias_generator=alias_generators.to_camel,
    populate_by_name=True,
)


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class MeetingCreate(BaseModel):
    """Body accepted by ``POST /api/meetings``."""

    model_config = _CAMEL_CONFIG

    title: str
    description: str | None = None
    type: MeetingType
    scheduled_at: datetime | None = None
    duration_minutes: int = 60
    passcode: str | None = None


class MeetingUpdate(BaseModel):
    """Body accepted by ``PATCH /api/meetings/{id}``."""

    model_config = _CAMEL_CONFIG

    title: str | None = None
    description: str | None = None
    scheduled_at: datetime | None = None
    duration_minutes: int | None = None
    passcode: str | None = None
    status: MeetingStatus | None = None


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------


class MeetingRead(BaseModel):
    """Full meeting representation returned by every meeting endpoint.

    ``host_name`` / ``host_email`` are populated from the ``@property``
    accessors on the ORM model (which delegate to the related ``User``).
    ``participant_count`` is populated by the SQL ``column_property``
    defined in ``app/models/__init__.py`` — it is always accurate.
    """

    model_config = _ORM_CAMEL_CONFIG

    id: int
    meeting_id: str
    title: str
    description: str | None
    host_name: str
    host_email: str
    type: str
    status: str
    scheduled_at: datetime | None
    duration_minutes: int
    participant_count: int
    invite_link: str
    passcode: str | None
    created_at: datetime
    updated_at: datetime
