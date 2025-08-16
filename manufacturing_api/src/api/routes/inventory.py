from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.deps import get_tenant_session, require_roles
from src.repositories.inventory import (
    LocationRepository,
    LotRepository,
    InventoryTransactionRepository,
)
from src.schemas.inventory import (
    LocationRead,
    LotRead,
    InventoryTransactionRead,
)

router = APIRouter(prefix="/inventory", tags=["Inventory"])


# PUBLIC_INTERFACE
@router.get(
    "/locations",
    response_model=List[LocationRead],
    summary="List inventory locations",
    description="List inventory locations for the current tenant ordered by code.",
    dependencies=[Depends(require_roles("admin", "inventory:view"))],
)
async def list_locations(
    session: AsyncSession = Depends(get_tenant_session),
    limit: int = Query(100, ge=1, le=1000, description="Max records"),
    offset: int = Query(0, ge=0, description="Records to skip"),
) -> List[LocationRead]:
    """
    Return tenant-scoped inventory locations.

    Returns:
        List[LocationRead]: Locations ordered by code.
    """
    repo = LocationRepository(session)
    records = await repo.list_locations(limit=limit, offset=offset)
    return [LocationRead.model_validate(r) for r in records]


# PUBLIC_INTERFACE
@router.get(
    "/lots",
    response_model=List[LotRead],
    summary="List inventory lots",
    description="List lots (batches) for the current tenant with optional filters.",
    dependencies=[Depends(require_roles("admin", "inventory:view"))],
)
async def list_lots(
    session: AsyncSession = Depends(get_tenant_session),
    item_sku: Optional[str] = Query(None, description="Filter by item SKU"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> List[LotRead]:
    """
    Return tenant-scoped lots (batches).

    Query params allow filtering by item_sku and status.
    """
    repo = LotRepository(session)
    lots = await repo.list_lots(item_sku=item_sku, status=status, limit=limit, offset=offset)
    return [LotRead.model_validate(x) for x in lots]


# PUBLIC_INTERFACE
@router.get(
    "/transactions",
    response_model=List[InventoryTransactionRead],
    summary="List inventory transactions",
    description="List recent inventory transactions for the tenant ordered by created_at desc.",
    dependencies=[Depends(require_roles("admin", "inventory:view"))],
)
async def list_inventory_transactions(
    session: AsyncSession = Depends(get_tenant_session),
    lot_id: Optional[UUID] = Query(None, description="Filter by lot"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> List[InventoryTransactionRead]:
    """
    Return tenant-scoped inventory transactions.

    Optionally filter by lot_id.
    """
    repo = InventoryTransactionRepository(session)
    txns = await repo.list_transactions(lot_id=lot_id, limit=limit, offset=offset)
    return [InventoryTransactionRead.model_validate(x) for x in txns]
