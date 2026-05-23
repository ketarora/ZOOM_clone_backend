"""Participant ORM model.

Replaces the ``participantCount`` integer anti-pattern from the original
Node.js backend with a proper relational table.  Each row represents a
single person's presence in one meeting session and records:

  * **Identity** — optional FK to a registered ``User``; guests have ``user_id=NULL``
  * **Temporal** — ``joined_at`` / ``left_at`` (NULL while still in the room)
  * **Per-session state** — muted, camera, waiting-room admission, host flag

``CHECK`` constraints enforce the boolean-ness of the flag columns at the
database level (SQLite stores booleans as 0/1 integers).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Participant(Base):
    __tablename__ = "participants"
    __table_args__ = (
        Index("ix_participants_meeting_id", "meeting_id"),
        Index("ix_participants_user_id", "user_id"),
        Index("ix_participants_joined_at", "joined_at"),
        CheckConstraint("is_muted IN (0, 1)",      name="ck_participants_is_muted"),
        CheckConstraint("is_camera_off IN (0, 1)", name="ck_participants_is_camera_off"),
        CheckConstraint("is_admitted IN (0, 1)",   name="ck_participants_is_admitted"),
        CheckConstraint("is_host IN (0, 1)",       name="ck_participants_is_host"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    meeting_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
    )
    meeting: Mapped[Meeting] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Meeting",
        back_populates="participants",
    )

    # NULL when the participant is an unauthenticated guest.
    user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    user: Mapped[User | None] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "User",
        back_populates="participations",
    )

    # Snapshot of the display name at join-time — stays correct even if the
    # user later renames their profile.
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)

    is_muted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_camera_off: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # False while the participant is held in the waiting room.
    is_admitted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_host: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    # NULL while the participant is still active in the meeting.
    left_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<Participant id={self.id}"
            f" display_name={self.display_name!r}"
            f" meeting_id={self.meeting_id}>"
        )
