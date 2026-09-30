"""User model — represents a registered identity in the system."""

from __future__ import annotations

from sqlalchemy import Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models._base import TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_email", "email", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    hosted_meetings: Mapped[list[Meeting]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Meeting",
        back_populates="host",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    participations: Mapped[list[Participant]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Participant",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"
