from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.deps import get_tenant_session, require_roles
from src.repositories.production import WorkOrderRepository, WorkOrderOperationRepository
from src.schemas.production import (
    WorkOrderRead,
    WorkOrderCreate,
    WorkOrderOperationRead,
)

router = APIRouter(prefix="/production", tags=["Production"])


# PUBLIC_INTERFACE
@router.get(
    "/work-orders",
    response_model=List[WorkOrderRead],
    summary="List work orders",
    description="List work orders for the tenant ordered by created_at desc.",
    dependencies=[Depends(require_roles("admin", "production:view"))],
)
async def list_work_orders(
    session: AsyncSession = Depends(get_tenant_session),
    status: Optional[str] = Query(None, description="Filter by status"),
    order_no: Optional[str] = Query(None, description="Filter by order number (substring)"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> List[WorkOrderRead]:
    repo = WorkOrderRepository(session)
    items = await repo.list_work_orders(status=status, order_no=order_no, limit=limit, offset=offset)
    return [WorkOrderRead.model_validate(x) for x in items]


# PUBLIC_INTERFACE
@router.post(
    "/work-orders",
    response_model=WorkOrderRead,
    summary="Create work order",
    description="Create a work order header.",
    dependencies=[Depends(require_roles("admin", "production:manage"))],
)
async def create_work_order(
    payload: WorkOrderCreate,
    session: AsyncSession = Depends(get_tenant_session),
) -> WorkOrderRead:
    repo = WorkOrderRepository(session)
    created = await repo.create_work_order(payload)
    return WorkOrderRead.model_validate(created)


# PUBLIC_INTERFACE
@router.get(
    "/work-orders/{wo_id}",
    response_model=WorkOrderRead,
    summary="Get work order",
    description="Get a work order by id.",
    dependencies=[Depends(require_roles("admin", "production:view"))],
)
async def get_work_order(
    wo_id: UUID = Path(...),
    session: AsyncSession = Depends(get_tenant_session),
) -> WorkOrderRead:
    repo = WorkOrderRepository(session)
    wo = await repo.get_work_order(wo_id)
    if not wo:
        raise HTTPException(status_code=404, detail="Work order not found")
    return WorkOrderRead.model_validate(wo)


# PUBLIC_INTERFACE
@router.get(
    "/operations",
    response_model=List[WorkOrderOperationRead],
    summary="List work order operations",
    description="List operations for all work orders, ordered by planned_start.",
    dependencies=[Depends(require_roles("admin", "production:view"))],
)
async def list_operations(
    session: AsyncSession = Depends(get_tenant_session),
    work_order_id: Optional[UUID] = Query(None, description="Filter by work order id"),
    status: Optional[str] = Query(None, description="Filter by operation status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> List[WorkOrderOperationRead]:
    repo = WorkOrderOperationRepository(session)
    ops = await repo.list_operations(
        work_order_id=work_order_id, status=status, limit=limit, offset=offset
    )
    return [WorkOrderOperationRead.model_validate(x) for x in ops]
