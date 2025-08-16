from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.deps import get_tenant_session, require_roles
from src.repositories.security import SecurityRepository
from src.schemas.auth import RoleCreate, RoleRead

router = APIRouter(prefix="/admin/roles", tags=["Roles"])


# PUBLIC_INTERFACE
@router.get(
    "",
    response_model=List[RoleRead],
    summary="List roles",
    dependencies=[Depends(require_roles("admin", "roles:manage"))],
)
async def list_roles(
    session: AsyncSession = Depends(get_tenant_session),
    limit: int = 100,
    offset: int = 0,
) -> List[RoleRead]:
    repo = SecurityRepository(session)
    roles = await repo.list_roles(limit=limit, offset=offset)
    return [RoleRead.model_validate(r) for r in roles]


# PUBLIC_INTERFACE
@router.post(
    "",
    response_model=RoleRead,
    summary="Create role",
    dependencies=[Depends(require_roles("admin", "roles:manage"))],
)
async def create_role(
    payload: RoleCreate,
    session: AsyncSession = Depends(get_tenant_session),
) -> RoleRead:
    repo = SecurityRepository(session)
    existing = await repo.get_role_by_name(payload.name)
    if existing:
        raise HTTPException(status_code=400, detail="Role already exists")
    role = await repo.create_role(payload.name, payload.description)
    return RoleRead.model_validate(role)


# PUBLIC_INTERFACE
@router.get(
    "/{role_id}",
    response_model=RoleRead,
    summary="Get role",
    dependencies=[Depends(require_roles("admin", "roles:manage"))],
)
async def get_role(
    role_id: UUID = Path(...),
    session: AsyncSession = Depends(get_tenant_session),
) -> RoleRead:
    repo = SecurityRepository(session)
    role = await repo.get_role_by_id(role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return RoleRead.model_validate(role)


# PUBLIC_INTERFACE
@router.delete(
    "/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete role",
    dependencies=[Depends(require_roles("admin", "roles:manage"))],
)
async def delete_role(
    role_id: UUID = Path(...),
    session: AsyncSession = Depends(get_tenant_session),
) -> None:
    repo = SecurityRepository(session)
    await repo.delete_role(role_id)
