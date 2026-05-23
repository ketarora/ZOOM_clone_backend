"""Centralised logging configuration.

Call ``configure_logging()`` once at process start.  All loggers throughout
the application then inherit this configuration automatically.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

from app.config import settings

_CONFIGURED = False


def configure_logging() -> None:
    global _CONFIGURED  # noqa: PLW0603
    if _CONFIGURED:
        return

    fmt = "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s"
    datefmt = "%Y-%m-%dT%H:%M:%S"

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))

    root = logging.getLogger()
    root.setLevel(settings.log_level)
    root.handlers.clear()
    root.addHandler(handler)

    # Silence noisy third-party loggers
    for noisy in ("uvicorn.access", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)
