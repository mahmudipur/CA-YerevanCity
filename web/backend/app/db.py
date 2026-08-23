"""SQLAlchemy engine/session plumbing for the multi-tenant user store.

Sync engine (stdlib sqlite3 driver) to match the rest of this codebase,
which is entirely synchronous (requests, sync route handlers). One table
(`users`) — no Alembic; `init_db()` just calls `create_all`, which is
sufficient for a single-table, additive-only schema at this stage.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import DB_PATH


class Base(DeclarativeBase):
    pass


# check_same_thread=False: FastAPI's threadpool may call in from a different
# thread than the one that created the engine; a Session is still only ever
# used within a single request's handling here (no cross-thread sharing of
# one Session instance).
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    from .models import user  # noqa: F401  (registers User with Base.metadata)

    Base.metadata.create_all(bind=engine)


def session_scope():
    """Context-manager-friendly session for use in a `with` block."""
    return SessionLocal()
