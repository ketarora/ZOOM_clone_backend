"""Pydantic schemas for Participant I/O."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, alias_generators, field_validator

_ORM_CAMEL_CONFIG = ConfigDict(
    from_attributes=True,
    alias_generator=alias_generators.to_camel,
    populate_by_name=True,
)

_CAMEL_CONFIG = ConfigDict(
    alias_generator=alias_generators.to_camel,
    populate_by_name=True,
)


class JoinMeetingInput(BaseModel):
    """Body accepted by ``POST /api/meetings/join/{id}``.

    The frontend sends ``{"displayName": "…"}`` — the alias maps
    that to ``display_name`` on the Python model.
    """

    model_config = _CAMEL_CONFIG

    display_name: str = Field(min_length=1, max_length=120)

    @field_validator("display_name")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Display name must not be blank.")
        return v


class LeaveMeetingInput(BaseModel):
    """Body accepted by ``POST /api/meetings/{id}/leave``.

    Either field is sufficient. When both are absent the most recently
    joined active participant is marked as left (single-user demo fallback).
    """

    model_config = _CAMEL_CONFIG

    participant_id: int | None = None
    display_name: str | None = Field(default=None, max_length=120)


class ParticipantRead(BaseModel):
    model_config = _ORM_CAMEL_CONFIG

    id: int
    meeting_id: int
    user_id: int | None
    display_name: str
    is_muted: bool
    is_camera_off: bool
    is_admitted: bool
    is_host: bool
    joined_at: datetime
    left_at: datetime | None
