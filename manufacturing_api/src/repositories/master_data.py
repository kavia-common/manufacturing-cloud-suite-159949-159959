from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.master_data import Item, Bom, BomLine
from .base import BaseRepository
from src.schemas.master_data import ItemCreate


class ItemRepository(BaseRepository):
    """Repository for Items (products)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_items(
        self, *, search: Optional[str], status: Optional[str], limit: int, offset: int
    ) -> List[Item]:
        stmt = select(Item)
        if search:
            like = f"%{search}%"
            stmt = stmt.where(or_(Item.sku.ilike(like), Item.name.ilike(like)))
        if status:
            stmt = stmt.where(Item.status == status)
        stmt = stmt.order_by(Item.sku).offset(offset).limit(limit)
        res = await self.scalars(stmt)
        return list(res)

    async def create_item(self, payload: ItemCreate) -> Item:
        row = Item(
            sku=payload.sku,
            name=payload.name,
            description=payload.description,
            default_uom_id=payload.default_uom_id,
            status=payload.status or "active",
        )
        await self.add(row)
        await self.commit()
        stmt = select(Item).where(Item.id == row.id)
        return (await self.scalar_one_or_none(stmt))  # type: ignore


class BomRepository(BaseRepository):
    """Repository for BOMs."""

    async def list_boms(
        self, *, item_id: Optional[UUID], is_active: Optional[bool], limit: int, offset: int
    ) -> List[Bom]:
        stmt = select(Bom)
        if item_id:
            stmt = stmt.where(Bom.item_id == item_id)
        if is_active is not None:
            stmt = stmt.where(Bom.is_active == is_active)
        stmt = stmt.order_by(Bom.code).offset(offset).limit(limit)
        res = await self.scalars(stmt)
        return list(res)

    async def get_bom(self, bom_id: UUID) -> Optional[Bom]:
        stmt = select(Bom).where(Bom.id == bom_id)
        return await self.scalar_one_or_none(stmt)

    async def list_bom_lines(self, *, bom_id: UUID) -> List[BomLine]:
        stmt = select(BomLine).where(BomLine.bom_id == bom_id).order_by(BomLine.line_no.asc())
        res = await self.scalars(stmt)
        return list(res)
