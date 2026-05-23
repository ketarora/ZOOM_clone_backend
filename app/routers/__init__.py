"""Router registry — aggregates all sub-routers into a single ``api_router``.

``app/main.py`` mounts this router once under ``/api``, keeping the
application factory clean and making it trivial to version the API later
(e.g. swap ``/api`` for ``/api/v1``).
"""

from __future__ import annotations

from fastapi import APIRouter

from app.routers.dashboard import router as dashboard_router
from app.routers.health import router as health_router
from app.routers.meetings import router as meetings_router
from app.routers.users import router as users_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(meetings_router)
api_router.include_router(dashboard_router)
api_router.include_router(users_router)
