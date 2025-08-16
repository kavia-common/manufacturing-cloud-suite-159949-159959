from __future__ import annotations

import sys
from pathlib import Path

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

# Ensure project root is on sys.path so `src.*` imports work when running Alembic
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[3]  # .../manufacturing_api
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.db.base import Base  # noqa: E402
from src.db.config import get_settings  # noqa: E402

# Alembic Config object; provides access to the values within the .ini in use.
config = context.config

# Get settings and URLs
settings = get_settings()
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    This configures the context with just a URL and not an Engine.
    """
    url = settings.sync_database_url  # base postgresql:// URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode using an async engine.
    """
    connectable: AsyncEngine = create_async_engine(
        settings.async_database_url,
        poolclass=pool.NullPool,
        # echo can be controlled by Settings.SQL_ECHO if desired
    )

    async with connectable.connect() as connection:
        await connection.run_sync(
            lambda sync_conn: context.configure(
                connection=sync_conn,
                target_metadata=target_metadata,
                compare_type=True,
                compare_server_default=True,
            )
        )

        await connection.run_sync(lambda _: context.begin_transaction())
        await connection.run_sync(lambda _: context.run_migrations())

    await connectable.dispose()


def run() -> None:
    if context.is_offline_mode():
        run_migrations_offline()
    else:
        import asyncio

        asyncio.run(run_migrations_online())


run()
