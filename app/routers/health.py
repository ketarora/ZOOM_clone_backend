"""Health-check endpoint — liveness probe.

No database query is performed intentionally.  The endpoint should respond
even when the DB is temporarily unavailable, so the process manager
(systemd, Kubernetes, etc.) does not restart the process unnecessarily.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthStatus(BaseModel):
    status: str


@router.get(
    "/healthz",
    response_model=HealthStatus,
    summary="Liveness probe",
    description="Returns ``{status: 'ok'}`` as long as the process is running.",
)
def health_check() -> HealthStatus:
    return HealthStatus(status="ok")
