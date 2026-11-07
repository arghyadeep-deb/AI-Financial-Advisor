"""Alembic environment.  The URL comes from the runner (DATABASE_URL)."""
from alembic import context
from sqlalchemy import create_engine, pool

from backend.core.config import config as app_config

target_metadata = None  # migrations are explicit; no autogenerate against live models

cfg = context.config


def _url() -> str:
    return cfg.get_main_option("sqlalchemy.url") or app_config.DATABASE_URL


def run_migrations_offline() -> None:
    context.configure(url=_url(), literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = cfg.attributes.get("connection")
    if connectable is None:
        connectable = create_engine(_url(), poolclass=pool.NullPool)
        with connectable.connect() as connection:
            _run(connection)
    else:
        _run(connectable)


def _run(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata,
                      render_as_batch=connection.dialect.name == "sqlite")
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
