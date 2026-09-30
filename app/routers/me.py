"""Current-user router — ``GET /api/me``.

The assignment assumes a default logged-in user (no auth). This endpoint
returns that user, creating the record on first call so the frontend never
needs hardcoded host names or emails.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserRead

router = APIRouter(tags=["me"])

_DEFAULT_HOST_EMAIL = "ketan.arora019@gmail.com"
_DEFAULT_HOST_NAME = "Ketan Arora"


@router.get(
    "/me",
    response_model=UserRead,
    summary="Get the default logged-in user",
)
def get_me(db: Annotated[Session, Depends(get_db)]) -> UserRead:
    user = db.query(User).filter(User.email == _DEFAULT_HOST_EMAIL).first()
    if user is None:
        user = User(display_name=_DEFAULT_HOST_NAME, email=_DEFAULT_HOST_EMAIL)
        db.add(user)
        db.commit()
        db.refresh(user)
    return UserRead.model_validate(user)
