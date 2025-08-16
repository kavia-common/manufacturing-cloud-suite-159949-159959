from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.deps import get_tenant_session, require_roles
from src.core.security import get_password_hash
from src.repositories.security import SecurityRepository
from src.schemas.auth import UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="/admin/users", tags=["Users"])


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
@router.get(
    "",
    response_model=List[UserRead],
    summary="List users",
    description="List users for the current tenant.",
    dependencies=[Depends(require_roles("admin", "users:manage"))],
)
async def list_users(
    session: AsyncSession = Depends(get_tenant_session),
    limit: int = 100,
    offset: int = 0,
) -> List[UserRead]:
    repo = SecurityRepository(session)
    items = await repo.list_users(limit=limit, offset=offset)
    result: List[UserRead] = []
    for u in items:
        roles = [r.name for r in await repo.list_roles_for_user(u.id)]
        result.append(_user_to_read(u, roles))
    return result


# PUBLIC_INTERFACE
@router.post(
    "",
    response_model=UserRead,
    summary="Create user",
    description="Create a user. Requires admin or users:manage role.",
    dependencies=[Depends(require_roles("admin", "users:manage"))],
)
async def create_user(
    payload: UserCreate,
    session: AsyncSession = Depends(get_tenant_session),
) -> UserRead:
    repo = SecurityRepository(session)
    existing = await repo.get_user_by_email(payload.email)
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    hashed = get_password_hash(payload.password)
    user = await repo.create_user(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hashed,
        is_active=payload.is_active if payload.is_active is not None else True,
        is_superadmin=payload.is_superadmin if payload.is_superadmin is not None else False,
    )
    roles = [r.name for r in await repo.list_roles_for_user(user.id)]
    return _user_to_read(user, roles)


# PUBLIC_INTERFACE
@router.get(
    "/{user_id}",
    response_model=UserRead,
    summary="Get user",
    dependencies=[Depends(require_roles("admin", "users:manage"))],
)
async def get_user(
    user_id: UUID = Path(...),
    session: AsyncSession = Depends(get_tenant_session),
) -> UserRead:
    repo = SecurityRepository(session)
    user = await repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    roles = [r.name for r in await repo.list_roles_for_user(user.id)]
    return _user_to_read(user, roles)


# PUBLIC_INTERFACE
@router.patch(
    "/{user_id}",
    response_model=UserRead,
    summary="Update user",
    dependencies=[Depends(require_roles("admin", "users:manage"))],
)
async def update_user(
    user_id: UUID = Path(...),
    payload: UserUpdate = ...,
    session: AsyncSession = Depends(get_tenant_session),
) -> UserRead:
    repo = SecurityRepository(session)
    hashed = get_password_hash(payload.password) if payload.password else None
    updated = await repo.update_user(
        user_id,
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hashed,
        is_active=payload.is_active,
        is_superadmin=payload.is_superadmin,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    roles = [r.name for r in await repo.list_roles_for_user(updated.id)]
    return _user_to_read(updated, roles)


# PUBLIC_INTERFACE
@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user",
    dependencies=[Depends(require_roles("admin", "users:manage"))],
)
async def delete_user(
    user_id: UUID = Path(...),
    session: AsyncSession = Depends(get_tenant_session),
) -> None:
    repo = SecurityRepository(session)
    await repo.delete_user(user_id)


# PUBLIC_INTERFACE
@router.post(
    "/{user_id}/roles/{role_id}",
    response_model=UserRead,
    summary="Assign role to user",
    dependencies=[Depends(require_roles("admin", "users:manage"))],
)
async def assign_role(
    user_id: UUID,
    role_id: UUID,
    session: AsyncSession = Depends(get_tenant_session),
) -> UserRead:
    repo = SecurityRepository(session)
    user = await repo.get_user_by_id(user_id)
    role = await repo.get_role_by_id(role_id)
    if not user or not role:
        raise HTTPException(status_code=404, detail="User or role not found")
    await repo.assign_role_to_user(user_id, role_id)
    roles = [r.name for r in await repo.list_roles_for_user(user_id)]
    return _user_to_read(user, roles)


# PUBLIC_INTERFACE
@router.delete(
    "/{user_id}/roles/{role_id}",
    response_model=UserRead,
    summary="Remove role from user",
    dependencies=[Depends(require_roles("admin", "users:manage"))],
)
async def remove_role(
    user_id: UUID,
    role_id: UUID,
    session: AsyncSession = Depends(get_tenant_session),
) -> UserRead:
    repo = SecurityRepository(session)
    user = await repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await repo.remove_role_from_user(user_id, role_id)
    roles = [r.name for r in await repo.list_roles_for_user(user_id)]
    return _user_to_read(user, roles)
