"""Meeting ORM model.

Design notes
------------
* ``participant_count`` is **not** a stored column; it is injected in
  ``app/models/__init__.py`` as a SQL ``column_property`` (correlated COUNT
  subquery).  Storing it would be a normalisation violation — the value would
  drift whenever a participant row is inserted or left_at is stamped without
  remembering to update the count.
* ``CHECK`` constraints enforce the type/status enumerations at the database
  level, not just in application code.
* Explicit ``Index`` entries on the most-queried columns prevent full scans.
* The ``host`` relationship uses ``lazy="joined"`` so every Meeting query
  carries the host ``display_name`` and ``email`` in the same SQL round-trip.
  These are exposed as Python ``@property`` accessors (``host_name``,
  ``host_email``) which Pydantic reads transparently when building
  ``MeetingRead`` responses.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models._base import TimestampMixin


class Meeting(Base, TimestampMixin):
    __tablename__ = "meetings"
    __table_args__ = (
        # ── Indexes ──────────────────────────────────────────────────────
        Index("ix_meetings_meeting_id", "meeting_id", unique=True),
        Index("ix_meetings_status", "status"),
        Index("ix_meetings_host_id", "host_id"),
        Index("ix_meetings_created_at", "created_at"),
        # ── Enum-level integrity (3NF) ────────────────────────────────────
        CheckConstraint(
            "type IN ('instant', 'scheduled')",
            name="ck_meetings_type",
        ),
        CheckConstraint(
            "status IN ('waiting', 'active', 'ended')",
            name="ck_meetings_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # Human-readable Zoom-style ID: "XXX XXX XXXX"
    meeting_id: Mapped[str] = mapped_column(String(20), nullable=False)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    host_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    host: Mapped[User] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "User",
        back_populates="hosted_meetings",
        lazy="joined",
    )

    type: Mapped[str] = mapped_column(String(20), nullable=False, default="instant")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="waiting")

    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)

    invite_link: Mapped[str] = mapped_column(Text, nullable=False)
    passcode: Mapped[str | None] = mapped_column(String(50), nullable=True)

    participants: Mapped[list[Participant]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Participant",
        back_populates="meeting",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="select",
    )

    # ``participant_count`` is set as a ``column_property`` in
    # ``app/models/__init__.py`` after both Meeting and Participant are
    # imported.  It must NOT be declared here as a ``Mapped`` column — doing
    # so would confuse the SQLAlchemy mapper.

    @property
    def host_name(self) -> str:
        """Flattened from the related User — used by MeetingRead schema."""
        return self.host.display_name

    @property
    def host_email(self) -> str:
        """Flattened from the related User — used by MeetingRead schema."""
        return self.host.email

    def __repr__(self) -> str:
        return (
            f"<Meeting id={self.id} meeting_id={self.meeting_id!r}"
            f" status={self.status!r}>"
        )
