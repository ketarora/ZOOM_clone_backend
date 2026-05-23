"""Domain exceptions and FastAPI exception handlers.

Keeping HTTP concerns out of the domain layer: domain code raises
``NotFoundError`` / ``ConflictError`` etc., and the handlers here translate
them to the appropriate HTTP responses.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Domain exceptions
# ---------------------------------------------------------------------------


class ZoomCloneError(Exception):
    """Base class for all application-level errors."""


class NotFoundError(ZoomCloneError):
    def __init__(self, entity: str, identifier: str | int) -> None:
        self.entity = entity
        self.identifier = identifier
        super().__init__(f"{entity} '{identifier}' not found")


class ConflictError(ZoomCloneError):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class BusinessRuleError(ZoomCloneError):
    """Raised when a business invariant is violated (e.g. joining an ended meeting)."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


# ---------------------------------------------------------------------------
# FastAPI exception handlers
# ---------------------------------------------------------------------------


def _error_body(message: str) -> dict[str, str]:
    return {"error": message}


async def _not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content=_error_body(str(exc)))


async def _conflict_handler(request: Request, exc: ConflictError) -> JSONResponse:
    return JSONResponse(status_code=409, content=_error_body(str(exc)))


async def _business_rule_handler(
    request: Request, exc: BusinessRuleError
) -> JSONResponse:
    return JSONResponse(status_code=400, content=_error_body(str(exc)))


async def _unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
    # Let FastAPI's own handler deal with HTTPException (includes 404 from routing).
    if isinstance(exc, HTTPException):
        return await http_exception_handler(request, exc)

    logger.exception(
        "Unhandled exception during %s %s",
        request.method,
        request.url.path,
        exc_info=exc,
    )
    return JSONResponse(status_code=500, content=_error_body("Internal server error"))


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(NotFoundError, _not_found_handler)  # type: ignore[arg-type]
    app.add_exception_handler(ConflictError, _conflict_handler)  # type: ignore[arg-type]
    app.add_exception_handler(BusinessRuleError, _business_rule_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _unhandled_handler)
