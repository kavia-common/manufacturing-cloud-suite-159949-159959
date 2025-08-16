from __future__ import annotations

import logging
from typing import AsyncGenerator
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_async_session, tenant_context

logger = logging.getLogger(__name__)


# PUBLIC_INTERFACE
async def get_tenant_id(x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID")) -> UUID:
    """
    Extract and validate the tenant id from the X-Tenant-ID header.

    Raises:
        HTTPException: 400 Bad Request if header missing or invalid UUID.
    Returns:
        UUID: tenant identifier
    """
    if not x_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Tenant-ID header is required.",
        )
    try:
        return UUID(x_tenant_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Tenant-ID header must be a valid UUID string.",
        )


# PUBLIC_INTERFACE
async def get_tenant_session(
    tenant_id: UUID = Depends(get_tenant_id),
    session_dep=Depends(get_async_session),
) -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an AsyncSession with Row-Level Security (RLS) configured for the given tenant.

    This dependency ensures the Postgres session GUC `app.tenant_id` is set to the
    provided tenant_id while the session is in use, then reset after use.
    """
    # get_async_session yields an AsyncSession via dependency
    async for session in session_dep:
        async with tenant_context(session, tenant_id):
            yield session


# PUBLIC_INTERFACE
async def get_session_no_tenant(
    session_dep=Depends(get_async_session),
) -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an AsyncSession without setting tenant context.

    Useful for system-level operations that must run outside RLS constraints,
    or when the SQL executed sets the tenant context manually (e.g., during seeding).
    """
    async for session in session_dep:
        yield session
