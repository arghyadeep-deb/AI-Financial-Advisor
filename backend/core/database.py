"""Database wiring (T103).

* ``create_db_engine`` selects engine options by backend (SQLite for deliberate
  local use, PostgreSQL otherwise).
* Schema is owned by Alembic.  Startup no longer calls ``create_all``; it
  verifies the database is at the current head and (for local SQLite only,
  or when AUTO_MIGRATE=1) runs the migrations via ``migrations_runner``.
"""
import os
from typing import Optional

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from backend.core.config import config


def create_db_engine(url: Optional[str] = None) -> Engine:
    url = url or config.DATABASE_URL
    if url.startswith("sqlite"):
        eng = create_engine(url, connect_args={"check_same_thread": False})

        @event.listens_for(eng, "connect")
        def _sqlite_pragmas(dbapi_conn, _):  # pragma: no cover - trivial
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()
        return eng
    return create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=5)


engine = create_db_engine()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def upgrade_to_head(url: Optional[str] = None, **kwargs):
    from backend.core.migrations_runner import migrate
    return migrate(url or config.DATABASE_URL, **kwargs)


def init_db():
    """Ensure the schema is current.  Never creates tables ad hoc."""
    from backend.core.migrations_runner import current_state, migrate

    state = current_state(config.DATABASE_URL)
    if state["at_head"]:
        return state
    auto = os.getenv("AUTO_MIGRATE", "1" if config.DATABASE_URL.startswith("sqlite") else "0") == "1"
    if not auto:
        raise RuntimeError(
            f"Database schema is {state['status']} (current={state['current']}, head={state['head']}). "
            "Run `python -m backend.core.migrations_runner upgrade` (back up first) or set AUTO_MIGRATE=1."
        )
    return migrate(config.DATABASE_URL)


def get_db():
    """FastAPI dependency — yields DB session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
