from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.inventory import Location, Lot, InventoryTransaction
from .base import BaseRepository


class LocationRepository(BaseRepository):
    """
    Repository for Locations.

    All queries are automatically tenant-scoped by Postgres RLS.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_locations(self, limit: int = 100, offset: int = 0) -> List[Location]:
        stmt = (
            select(Location)
            .order_by(Location.code)
            .offset(offset)
            .limit(limit)
        )
        result = await self.scalars(stmt)
        return list(result)

    async def get_location(self, location_id: UUID) -> Optional[Location]:
        stmt = select(Location).where(Location.id == location_id)
        return await self.scalar_one_or_none(stmt)


class LotRepository(BaseRepository):
    """Repository for Lots (batches)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_lots(
        self, *, item_sku: Optional[str], status: Optional[str], limit: int, offset: int
    ) -> List[Lot]:
        stmt = select(Lot)
        if item_sku:
            stmt = stmt.where(Lot.item_sku == item_sku)
        if status:
            stmt = stmt.where(Lot.status == status)
        stmt = stmt.order_by(Lot.created_at.desc()).offset(offset).limit(limit)
        res = await self.scalars(stmt)
        return list(res)


class InventoryTransactionRepository(BaseRepository):
    """Repository for inventory transactions."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_transactions(
        self, *, lot_id: Optional[UUID], limit: int, offset: int
    ) -> List[InventoryTransaction]:
        stmt = select(InventoryTransaction)
        if lot_id:
            stmt = stmt.where(InventoryTransaction.lot_id == lot_id)
        stmt = stmt.order_by(InventoryTransaction.created_at.desc()).offset(offset).limit(limit)
        res = await self.scalars(stmt)
        return list(res)
