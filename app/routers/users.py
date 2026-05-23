"""Users router — CRUD for registered user accounts."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import ConflictError, NotFoundError
from app.models.user import User
from app.schemas.user import UserCreate, UserRead, UserUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


def _get_user_or_404(db: Session, user_id: int) -> User:
    user: User | None = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise NotFoundError("User", user_id)
    return user


@router.get(
    "",
    response_model=list[UserRead],
    summary="List users",
)
def list_users(db: Session = Depends(get_db)) -> list[UserRead]:
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [UserRead.model_validate(u) for u in users]


@router.post(
    "",
    response_model=UserRead,
    status_code=201,
    summary="Create a user",
)
def create_user(body: UserCreate, db: Session = Depends(get_db)) -> UserRead:
    if db.query(User).filter(User.email == body.email).first():
        raise ConflictError(f"A user with email '{body.email}' already exists.")

    user = User(
        display_name=body.display_name,
        email=body.email,
        avatar_url=body.avatar_url,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("Created user '%s'", body.email)
    return UserRead.model_validate(user)


@router.get(
    "/{user_id}",
    response_model=UserRead,
    summary="Get a user",
)
def get_user(user_id: int, db: Session = Depends(get_db)) -> UserRead:
    return UserRead.model_validate(_get_user_or_404(db, user_id))


@router.patch(
    "/{user_id}",
    response_model=UserRead,
    summary="Update a user",
    description="Partial update — only provided fields are changed.",
)
def update_user(
    user_id: int,
    body: UserUpdate,
    db: Session = Depends(get_db),
) -> UserRead:
    user = _get_user_or_404(db, user_id)

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return UserRead.model_validate(user)


@router.delete(
    "/{user_id}",
    status_code=204,
    summary="Delete a user",
)
def delete_user(user_id: int, db: Session = Depends(get_db)) -> None:
    user = _get_user_or_404(db, user_id)
    db.delete(user)
    db.commit()
    logger.info("Deleted user id=%d", user_id)
    return Response(status_code=204)
