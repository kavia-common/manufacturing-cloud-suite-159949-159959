from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Union
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .config import get_settings


_SETTINGS = get_settings()
_ENGINE: AsyncEngine | None = None
_SESSION_MAKER: async_sessionmaker[AsyncSession] | None = None


def _ensure_engine_initialized() -> None:
    """
    Lazily initialize the AsyncEngine and session maker.
    """
    global _ENGINE, _SESSION_MAKER
    if _ENGINE is None:
        _ENGINE = create_async_engine(
            _SETTINGS.async_database_url,
            echo=_SETTINGS.SQL_ECHO,
            pool_pre_ping=True,
        )
    if _SESSION_MAKER is None:
        _SESSION_MAKER = async_sessionmaker(
            bind=_ENGINE, expire_on_commit=False, autoflush=False, autocommit=False
        )


# PUBLIC_INTERFACE
def get_engine() -> AsyncEngine:
    """Return the global AsyncEngine instance."""
    _ensure_engine_initialized()
    assert _ENGINE is not None
    return _ENGINE


# PUBLIC_INTERFACE
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an AsyncSession suitable for FastAPI dependency injection.
    Ensures engine/session factory is initialized.
    """
    _ensure_engine_initialized()
    assert _SESSION_MAKER is not None
    async with _SESSION_MAKER() as session:
        yield session


# PUBLIC_INTERFACE
async def set_current_tenant(
    session: AsyncSession, tenant_id: Union[str, UUID]
) -> None:
    """
    Set the current tenant for the DB session using a custom GUC.

    This enables Row-Level Security (RLS) policies that reference:
      current_setting('app.tenant_id', true)

    Parameters:
      session: AsyncSession - an active async DB session/connection
      tenant_id: str | UUID - the tenant identifier to set
    """
    await session.execute(
        text("SELECT set_config('app.tenant_id', :tenant_id, false);"),
        {"tenant_id": str(tenant_id)},
    )


# PUBLIC_INTERFACE
@asynccontextmanager
async def tenant_context(
    session: AsyncSession, tenant_id: Union[str, UUID]
) -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager that sets and resets the tenant context on the session.

    Usage:
        async with tenant_context(session, tenant_id):
            # all queries inside will be automatically filtered by RLS
            ...

    Note: RLS requires the migration policies to be in place.
    """
    await set_current_tenant(session, tenant_id)
    try:
        yield session
    finally:
        # Reset to empty string (policy USING ... will fail to match and thus deny access)
        await session.execute(
            text("SELECT set_config('app.tenant_id', '', false);")
        )
