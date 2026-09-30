"""Shared ORM base with auto-managed timestamp columns."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, event
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TimestampMixin:
    """Provides ``created_at`` and ``updated_at`` for any model that inherits it.

    ``updated_at`` is refreshed automatically on every ORM-level flush via a
    SQLAlchemy ``before_update`` event — this is more reliable than the
    ``onupdate`` Column parameter, which only fires if at least one *other*
    column is already dirty.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


@event.listens_for(Base, "before_update", propagate=True)
def _refresh_updated_at(mapper: object, connection: object, target: object) -> None:  # noqa: ARG001
    """Update the ``updated_at`` timestamp immediately before every flush."""
    if hasattr(target, "updated_at"):
        target.updated_at = datetime.now(timezone.utc)  # type: ignore[union-attr]
