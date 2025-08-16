from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.deps import get_tenant_session, require_roles
from src.repositories.master_data import ItemRepository, BomRepository
from src.schemas.master_data import (
    ItemRead,
    ItemCreate,
    BomRead,
    BomLineRead,
)

router = APIRouter(prefix="/master-data", tags=["Master Data"])


# PUBLIC_INTERFACE
@router.get(
    "/items",
    response_model=List[ItemRead],
    summary="List items (products)",
    description="List items/products for the tenant ordered by SKU.",
    dependencies=[Depends(require_roles("admin", "inventory:view", "production:view"))],
)
async def list_items(
    session: AsyncSession = Depends(get_tenant_session),
    search: str | None = Query(None, description="Filter by SKU or name (substring)"),
    status: str | None = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> List[ItemRead]:
    repo = ItemRepository(session)
    items = await repo.list_items(search=search, status=status, limit=limit, offset=offset)
    return [ItemRead.model_validate(x) for x in items]


# PUBLIC_INTERFACE
@router.post(
    "/items",
    response_model=ItemRead,
    summary="Create item (product)",
    description="Create a new item/product.",
    dependencies=[Depends(require_roles("admin", "inventory:manage", "production:manage"))],
)
async def create_item(
    payload: ItemCreate,
    session: AsyncSession = Depends(get_tenant_session),
) -> ItemRead:
    repo = ItemRepository(session)
    created = await repo.create_item(payload)
    return ItemRead.model_validate(created)


# PUBLIC_INTERFACE
@router.get(
    "/boms",
    response_model=List[BomRead],
    summary="List BOMs",
    description="List BOM headers for the tenant ordered by code.",
    dependencies=[Depends(require_roles("admin", "production:view"))],
)
async def list_boms(
    session: AsyncSession = Depends(get_tenant_session),
    item_id: UUID | None = Query(None, description="Filter by item id"),
    is_active: bool | None = Query(None, description="Filter by active flag"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> List[BomRead]:
    repo = BomRepository(session)
    boms = await repo.list_boms(item_id=item_id, is_active=is_active, limit=limit, offset=offset)
    return [BomRead.model_validate(x) for x in boms]


# PUBLIC_INTERFACE
@router.get(
    "/boms/{bom_id}",
    response_model=BomRead,
    summary="Get BOM",
    description="Get a BOM by id.",
    dependencies=[Depends(require_roles("admin", "production:view"))],
)
async def get_bom(
    bom_id: UUID = Path(...),
    session: AsyncSession = Depends(get_tenant_session),
) -> BomRead:
    repo = BomRepository(session)
    bom = await repo.get_bom(bom_id)
    if not bom:
        raise HTTPException(status_code=404, detail="BOM not found")
    return BomRead.model_validate(bom)


# PUBLIC_INTERFACE
@router.get(
    "/boms/{bom_id}/lines",
    response_model=List[BomLineRead],
    summary="List BOM lines",
    description="List BOM component lines for a BOM.",
    dependencies=[Depends(require_roles("admin", "production:view"))],
)
async def list_bom_lines(
    bom_id: UUID = Path(...),
    session: AsyncSession = Depends(get_tenant_session),
) -> List[BomLineRead]:
    repo = BomRepository(session)
    lines = await repo.list_bom_lines(bom_id=bom_id)
    return [BomLineRead.model_validate(x) for x in lines]
