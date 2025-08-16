from __future__ import annotations

from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.deps import get_tenant_id, get_tenant_session, get_current_active_user
from src.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from src.repositories.security import SecurityRepository
from src.schemas.auth import (
    Message,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    UserRead,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


def _user_to_read(user, roles: List[str]) -> UserRead:
    return UserRead(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superadmin=user.is_superadmin,
        created_at=user.created_at,
        updated_at=user.updated_at,
        roles=roles,
    )


# PUBLIC_INTERFACE
@router.post(
    "/register",
    response_model=UserRead,
    summary="Register user",
    description="Create a new user for the current tenant. If this is the first user in the tenant, it is assigned the 'admin' role.",
)
async def register_user(
    payload: RegisterRequest,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_tenant_session),
) -> UserRead:
    """Register a new user under the tenant."""
    repo = SecurityRepository(session)
    existing = await repo.get_user_by_email(payload.email)
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    hashed = get_password_hash(payload.password)
    user = await repo.create_user(
        email=payload.email, full_name=payload.full_name, hashed_password=hashed
    )

    # Assign admin role if first user for tenant
    if await repo.count_users() == 1:
        role = await repo.get_role_by_name("admin")
        if not role:
            role = await repo.create_role("admin", "Administrator")
        await repo.assign_role_to_user(user.id, role.id)

    roles = [r.name for r in await repo.list_roles_for_user(user.id)]
    return _user_to_read(user, roles)


# PUBLIC_INTERFACE
@router.post(
    "/login",
    response_model=TokenPair,
    summary="Login",
    description="Authenticate using OAuth2 password form and receive access/refresh tokens.",
)
async def login_for_tokens(
    form_data: OAuth2PasswordRequestForm = Depends(),
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_tenant_session),
) -> TokenPair:
    """Authenticate user and issue tokens."""
    repo = SecurityRepository(session)
    user = await repo.get_user_by_email(form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="User is inactive")

    roles = [r.name for r in await repo.list_roles_for_user(user.id)]
    access = create_access_token(subject=str(user.id), tenant_id=str(tenant_id), roles=roles)
    refresh = create_refresh_token(subject=str(user.id), tenant_id=str(tenant_id))
    return TokenPair(access_token=access, refresh_token=refresh)


# PUBLIC_INTERFACE
@router.post(
    "/refresh",
    response_model=TokenPair,
    summary="Refresh access token",
    description="Issue a new access token from a valid refresh token.",
)
async def refresh_token(
    payload: RefreshRequest,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_tenant_session),
) -> TokenPair:
    """Validate refresh token and issue a new access token pair."""
    try:
        claims: Dict[str, Any] = decode_token(payload.refresh_token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if claims.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")
    if str(tenant_id) != str(claims.get("tenant_id")):
        raise HTTPException(status_code=403, detail="Tenant mismatch")

    repo = SecurityRepository(session)
    user_id = claims.get("sub")
    user = await repo.get_user_by_id(UUID(user_id))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    roles = [r.name for r in await repo.list_roles_for_user(user.id)]
    access = create_access_token(subject=str(user.id), tenant_id=str(tenant_id), roles=roles)
    refresh = create_refresh_token(subject=str(user.id), tenant_id=str(tenant_id))
    return TokenPair(access_token=access, refresh_token=refresh)


# PUBLIC_INTERFACE
@router.post(
    "/logout",
    response_model=Message,
    summary="Logout",
    description="Stateless logout. Clients should discard tokens. No server state maintained.",
)
async def logout() -> Message:
    """Acknowledge logout in stateless JWT systems."""
    return Message(message="Logged out")


# PUBLIC_INTERFACE
@router.get(
    "/me",
    response_model=UserRead,
    summary="Read current user",
    description="Return the current authenticated user and their roles.",
)
async def read_current_user(
    user=Depends(get_current_active_user),
    session: AsyncSession = Depends(get_tenant_session),
) -> UserRead:
    """Return current user profile."""
    repo = SecurityRepository(session)
    roles = [r.name for r in await repo.list_roles_for_user(user.id)]
    return _user_to_read(user, roles)
