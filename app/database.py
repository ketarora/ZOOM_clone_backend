"""SQLAlchemy engine, session factory, and declarative base.

Design decisions
----------------
* WAL journal mode is enabled for every SQLite connection — it allows
  concurrent reads while a write is in progress.
* Foreign-key enforcement (PRAGMA foreign_keys=ON) is activated per-connection
  because SQLite disables it by default.
* ``get_db`` is a FastAPI dependency that yields a session and guarantees
  clean-up via ``finally``.
"""

from __future__ import annotations

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
    pool_pre_ping=True,
    echo=False,
)


@event.listens_for(engine, "connect")
def _configure_sqlite(dbapi_connection: object, _record: object) -> None:
    """Apply per-connection SQLite pragmas."""
    if settings.database_url.startswith("sqlite"):
        cursor = dbapi_connection.cursor()  # type: ignore[union-attr]
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()


# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------

SessionFactory = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


# ---------------------------------------------------------------------------
# Declarative base
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

def get_db() -> Session:  # type: ignore[return]
    db: Session = SessionFactory()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Schema creation helper (called once at startup)
# ---------------------------------------------------------------------------

def create_tables() -> None:
    """Create all tables that are registered on ``Base.metadata``."""
    # Import models so their table definitions are registered before create_all.
    import app.models  # noqa: F401  (side-effect import)

    Base.metadata.create_all(bind=engine)
