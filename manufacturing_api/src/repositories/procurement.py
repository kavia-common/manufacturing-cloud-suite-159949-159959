from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.procurement import Supplier, PurchaseOrder, PurchaseOrderLine
from .base import BaseRepository
from src.schemas.procurement import SupplierCreate, PurchaseOrderCreate


class SupplierRepository(BaseRepository):
    """Repository for suppliers."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_suppliers(
        self, *, search: Optional[str], limit: int, offset: int
    ) -> List[Supplier]:
        stmt = select(Supplier)
        if search:
            like = f"%{search}%"
            stmt = stmt.where(or_(Supplier.code.ilike(like), Supplier.name.ilike(like)))
        stmt = stmt.order_by(Supplier.code).offset(offset).limit(limit)
        res = await self.scalars(stmt)
        return list(res)

    async def create_supplier(self, payload: SupplierCreate) -> Supplier:
        row = Supplier(
            code=payload.code,
            name=payload.name,
            email=payload.email,
            phone=payload.phone,
            address=payload.address or {},
        )
        await self.add(row)
        await self.commit()
        stmt = select(Supplier).where(Supplier.id == row.id)
        return (await self.scalar_one_or_none(stmt))  # type: ignore


class PurchaseOrderRepository(BaseRepository):
    """Repository for purchase orders."""

    async def list_purchase_orders(
        self, *, supplier_id: Optional[UUID], status: Optional[str], limit: int, offset: int
    ) -> List[PurchaseOrder]:
        stmt = select(PurchaseOrder)
        if supplier_id:
            stmt = stmt.where(PurchaseOrder.supplier_id == supplier_id)
        if status:
            stmt = stmt.where(PurchaseOrder.status == status)
        stmt = stmt.order_by(PurchaseOrder.order_date.desc().nullslast(), PurchaseOrder.po_number)
        stmt = stmt.offset(offset).limit(limit)
        res = await self.scalars(stmt)
        return list(res)

    async def get_purchase_order(self, po_id: UUID) -> Optional[PurchaseOrder]:
        stmt = select(PurchaseOrder).where(PurchaseOrder.id == po_id)
        return await self.scalar_one_or_none(stmt)

    async def list_purchase_order_lines(self, po_id: UUID) -> List[PurchaseOrderLine]:
        stmt = (
            select(PurchaseOrderLine)
            .where(PurchaseOrderLine.purchase_order_id == po_id)
            .order_by(PurchaseOrderLine.line_no.asc())
        )
        res = await self.scalars(stmt)
        return list(res)

    async def create_purchase_order(self, payload: PurchaseOrderCreate) -> PurchaseOrder:
        row = PurchaseOrder(
            po_number=payload.po_number,
            supplier_id=payload.supplier_id,
            status=payload.status,
            order_date=payload.order_date,
            expected_date=payload.expected_date,
            total_amount=payload.total_amount,
            currency=payload.currency,
        )
        await self.add(row)
        await self.commit()
        stmt = select(PurchaseOrder).where(PurchaseOrder.id == row.id)
        return (await self.scalar_one_or_none(stmt))  # type: ignore
