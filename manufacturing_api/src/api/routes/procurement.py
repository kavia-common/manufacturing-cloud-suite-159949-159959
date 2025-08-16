from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.deps import get_tenant_session, require_roles
from src.repositories.procurement import SupplierRepository, PurchaseOrderRepository
from src.schemas.procurement import (
    SupplierRead,
    SupplierCreate,
    PurchaseOrderRead,
    PurchaseOrderLineRead,
    PurchaseOrderCreate,
)

router = APIRouter(prefix="/procurement", tags=["Procurement"])


# PUBLIC_INTERFACE
@router.get(
    "/suppliers",
    response_model=List[SupplierRead],
    summary="List suppliers",
    description="Return suppliers for the tenant ordered by code.",
    dependencies=[Depends(require_roles("admin", "procurement:view"))],
)
async def list_suppliers(
    session: AsyncSession = Depends(get_tenant_session),
    search: Optional[str] = Query(None, description="Filter by code or name (substring)"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> List[SupplierRead]:
    repo = SupplierRepository(session)
    items = await repo.list_suppliers(search=search, limit=limit, offset=offset)
    return [SupplierRead.model_validate(x) for x in items]


# PUBLIC_INTERFACE
@router.post(
    "/suppliers",
    response_model=SupplierRead,
    summary="Create supplier",
    description="Create a new supplier within the tenant scope.",
    dependencies=[Depends(require_roles("admin", "procurement:manage"))],
)
async def create_supplier(
    payload: SupplierCreate,
    session: AsyncSession = Depends(get_tenant_session),
) -> SupplierRead:
    repo = SupplierRepository(session)
    created = await repo.create_supplier(payload)
    return SupplierRead.model_validate(created)


# PUBLIC_INTERFACE
@router.get(
    "/purchase-orders",
    response_model=List[PurchaseOrderRead],
    summary="List purchase orders",
    description="Return purchase orders for the tenant ordered by order date desc.",
    dependencies=[Depends(require_roles("admin", "procurement:view"))],
)
async def list_purchase_orders(
    session: AsyncSession = Depends(get_tenant_session),
    supplier_id: Optional[UUID] = Query(None, description="Filter by supplier id"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> List[PurchaseOrderRead]:
    repo = PurchaseOrderRepository(session)
    rows = await repo.list_purchase_orders(
        supplier_id=supplier_id, status=status, limit=limit, offset=offset
    )
    return [PurchaseOrderRead.model_validate(x) for x in rows]


# PUBLIC_INTERFACE
@router.post(
    "/purchase-orders",
    response_model=PurchaseOrderRead,
    summary="Create purchase order",
    description="Create a new purchase order with header details.",
    dependencies=[Depends(require_roles("admin", "procurement:manage"))],
)
async def create_purchase_order(
    payload: PurchaseOrderCreate,
    session: AsyncSession = Depends(get_tenant_session),
) -> PurchaseOrderRead:
    repo = PurchaseOrderRepository(session)
    po = await repo.create_purchase_order(payload)
    return PurchaseOrderRead.model_validate(po)


# PUBLIC_INTERFACE
@router.get(
    "/purchase-orders/{po_id}",
    response_model=PurchaseOrderRead,
    summary="Get purchase order",
    description="Get a purchase order by id.",
    dependencies=[Depends(require_roles("admin", "procurement:view"))],
)
async def get_purchase_order(
    po_id: UUID = Path(..., description="Purchase order id"),
    session: AsyncSession = Depends(get_tenant_session),
) -> PurchaseOrderRead:
    repo = PurchaseOrderRepository(session)
    po = await repo.get_purchase_order(po_id)
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return PurchaseOrderRead.model_validate(po)


# PUBLIC_INTERFACE
@router.get(
    "/purchase-orders/{po_id}/lines",
    response_model=List[PurchaseOrderLineRead],
    summary="List purchase order lines",
    description="Return lines for a specific purchase order.",
    dependencies=[Depends(require_roles("admin", "procurement:view"))],
)
async def list_purchase_order_lines(
    po_id: UUID = Path(..., description="Purchase order id"),
    session: AsyncSession = Depends(get_tenant_session),
) -> List[PurchaseOrderLineRead]:
    repo = PurchaseOrderRepository(session)
    lines = await repo.list_purchase_order_lines(po_id)
    return [PurchaseOrderLineRead.model_validate(x) for x in lines]
