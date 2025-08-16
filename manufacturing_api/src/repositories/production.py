from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.production import WorkOrder, WorkOrderOperation
from .base import BaseRepository
from src.schemas.production import WorkOrderCreate


class WorkOrderRepository(BaseRepository):
    """Repository for work orders."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_work_orders(
        self, *, status: Optional[str], order_no: Optional[str], limit: int, offset: int
    ) -> List[WorkOrder]:
        stmt = select(WorkOrder)
        if status:
            stmt = stmt.where(WorkOrder.status == status)
        if order_no:
            like = f"%{order_no}%"
            stmt = stmt.where(WorkOrder.order_no.ilike(like))
        stmt = stmt.order_by(WorkOrder.created_at.desc()).offset(offset).limit(limit)
        res = await self.scalars(stmt)
        return list(res)

    async def get_work_order(self, wo_id: UUID) -> Optional[WorkOrder]:
        stmt = select(WorkOrder).where(WorkOrder.id == wo_id)
        return await self.scalar_one_or_none(stmt)

    async def create_work_order(self, payload: WorkOrderCreate) -> WorkOrder:
        wo = WorkOrder(
            order_no=payload.order_no,
            status=payload.status,
            item_sku=payload.item_sku,
            quantity_planned=payload.quantity_planned,
            due_date=payload.due_date,
            priority=payload.priority,
            sales_order_id=payload.sales_order_id,
            bom_id=payload.bom_id,
            routing_id=payload.routing_id,
        )
        await self.add(wo)
        await self.commit()
        stmt = select(WorkOrder).where(WorkOrder.id == wo.id)
        return (await self.scalar_one_or_none(stmt))  # type: ignore


class WorkOrderOperationRepository(BaseRepository):
    """Repository for work order operations."""

    async def list_operations(
        self, *, work_order_id: Optional[UUID], status: Optional[str], limit: int, offset: int
    ) -> List[WorkOrderOperation]:
        stmt = select(WorkOrderOperation)
        if work_order_id:
            stmt = stmt.where(WorkOrderOperation.work_order_id == work_order_id)
        if status:
            stmt = stmt.where(WorkOrderOperation.status == status)
        stmt = stmt.order_by(WorkOrderOperation.planned_start.asc().nullslast()).offset(offset).limit(limit)
        res = await self.scalars(stmt)
        return list(res)
