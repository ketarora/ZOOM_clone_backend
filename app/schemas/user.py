"""Pydantic schemas for User I/O."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, alias_generators

_ORM_CAMEL_CONFIG = ConfigDict(
    from_attributes=True,
    alias_generator=alias_generators.to_camel,
    populate_by_name=True,
)

_CAMEL_CONFIG = ConfigDict(
    alias_generator=alias_generators.to_camel,
    populate_by_name=True,
)


class UserCreate(BaseModel):
    model_config = _CAMEL_CONFIG

    display_name: str
    email: EmailStr
    avatar_url: str | None = None


class UserUpdate(BaseModel):
    model_config = _CAMEL_CONFIG

    display_name: str | None = None
    avatar_url: str | None = None


class UserRead(BaseModel):
    model_config = _ORM_CAMEL_CONFIG

    id: int
    display_name: str
    email: str
    avatar_url: str | None
    created_at: datetime
    updated_at: datetime
