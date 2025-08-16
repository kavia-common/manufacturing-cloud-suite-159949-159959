from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.quality import Inspection, Nonconformance
from .base import BaseRepository


class QualityRepository(BaseRepository):
    """Repository for quality inspections and nonconformances."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_inspections(
        self,
        *,
        work_order_id: Optional[UUID],
        lot_id: Optional[UUID],
        status: Optional[str],
        limit: int,
        offset: int,
    ) -> List[Inspection]:
        stmt = select(Inspection)
        if work_order_id:
            stmt = stmt.where(Inspection.work_order_id == work_order_id)
        if lot_id:
            stmt = stmt.where(Inspection.lot_id == lot_id)
        if status:
            stmt = stmt.where(Inspection.status == status)
        stmt = stmt.order_by(Inspection.created_at.desc()).offset(offset).limit(limit)
        res = await self.scalars(stmt)
        return list(res)

    async def list_nonconformances(
        self,
        *,
        status: Optional[str],
        severity: Optional[str],
        limit: int,
        offset: int,
    ) -> List[Nonconformance]:
        stmt = select(Nonconformance)
        if status:
            stmt = stmt.where(Nonconformance.status == status)
        if severity:
            stmt = stmt.where(Nonconformance.severity == severity)
        stmt = stmt.order_by(Nonconformance.created_at.desc()).offset(offset).limit(limit)
        res = await self.scalars(stmt)
        return list(res)
