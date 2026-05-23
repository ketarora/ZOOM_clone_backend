"""Shared response schemas used across multiple routers."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, alias_generators

T = TypeVar("T")

_CAMEL_CONFIG = ConfigDict(
    alias_generator=alias_generators.to_camel,
    populate_by_name=True,
)


class ErrorResponse(BaseModel):
    """Standard error envelope — matches the frontend ``ErrorResponse`` type."""

    model_config = _CAMEL_CONFIG

    error: str


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic pagination envelope.

    The raw list is also surfaced via ``X-Total-Count``, ``X-Page``, and
    ``X-Page-Size`` response headers so frontend clients can render page
    controls without parsing the body.
    """

    model_config = _CAMEL_CONFIG

    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int
