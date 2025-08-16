from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.inventory import Location
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
