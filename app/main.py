"""FastAPI application factory.

Responsibilities
----------------
* Construct and configure the ``FastAPI`` instance.
* Register middleware, exception handlers, and the unified API router.
* Manage startup/shutdown via the ``lifespan`` context manager (the
  ``@app.on_event`` approach is deprecated since FastAPI 0.93).
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import create_tables
from app.exceptions import register_exception_handlers
from app.logging_config import configure_logging
from app.routers import api_router

configure_logging()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — startup & shutdown
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    logger.info("Starting up ZoomConnect API …")
    create_tables()
    logger.info("Database schema verified.")
    yield
    logger.info("Shutting down ZoomConnect API.")


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    app = FastAPI(
        title="ZoomConnect API",
        description=(
            "REST backend for ZoomConnect — a Zoom-style meeting platform.\n\n"
            "**Source**: [github.com/ketarora/ZOOM_clone_backend]"
            "(https://github.com/ketarora/ZOOM_clone_backend)"
        ),
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # ── Middleware ────────────────────────────────────────────────────────

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Total-Count", "X-Page", "X-Page-Size"],
    )

    @app.middleware("http")
    async def _request_logger(request: Request, call_next: object) -> Response:
        start = time.perf_counter()
        response: Response = await call_next(request)  # type: ignore[operator]
        elapsed_ms = (time.perf_counter() - start) * 1_000
        logger.info(
            "%s %s → %d  (%.1f ms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response

    # ── Exception handlers ────────────────────────────────────────────────

    register_exception_handlers(app)

    # ── Routes ───────────────────────────────────────────────────────────

    app.include_router(api_router, prefix="/api")

    return app


app: FastAPI = create_app()
