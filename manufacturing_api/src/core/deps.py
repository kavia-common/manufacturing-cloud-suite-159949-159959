from __future__ import annotations

import logging
from typing import AsyncGenerator
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import decode_token
from src.db.session import get_async_session, tenant_context
from src.repositories.security import SecurityRepository

logger = logging.getLogger(__name__)

# OAuth2 bearer (used by docs); login endpoint path referenced here
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


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


# PUBLIC_INTERFACE
async def get_current_user(
    tenant_id: UUID = Depends(get_tenant_id),
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_tenant_session),
):
    """
    Resolve and return the current user from the Authorization bearer token.

    Validates the token, ensures tenant claim matches the incoming tenant header,
    and loads the user via RLS-scoped session.
    """
    try:
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    tok_tenant = payload.get("tenant_id")
    if not tok_tenant or str(tok_tenant) != str(tenant_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    repo = SecurityRepository(session)
    user = await repo.get_user_by_id(UUID(user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


# PUBLIC_INTERFACE
async def get_current_active_user(user=Depends(get_current_user)):
    """Ensure user is active."""
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return user


# PUBLIC_INTERFACE
def require_roles(*required: str):
    """
    Create a dependency that requires the current user to have one of the specified roles
    (or matching permission codes).
    """

    async def _dep(user=Depends(get_current_active_user), session: AsyncSession = Depends(get_tenant_session)):
        repo = SecurityRepository(session)
        roles = [r.name for r in await repo.list_roles_for_user(user.id)]
        role_set = set(roles)
        required_set = set(required)
        if role_set.isdisjoint(required_set):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return True

    return _dep
