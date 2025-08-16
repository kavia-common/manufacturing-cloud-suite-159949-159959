from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from src.core.deps import get_tenant_session, require_roles
from src.db.models.production import WorkOrderOperation
from src.schemas.production import WorkOrderOperationRead

router = APIRouter(prefix="/scheduling", tags=["Scheduling"])


# PUBLIC_INTERFACE
@router.get(
    "/operations",
    response_model=List[WorkOrderOperationRead],
    summary="Upcoming operations",
    description="List upcoming (planned) operations ordered by planned_start ascending. Acts as a simple scheduler feed.",
    dependencies=[Depends(require_roles("admin", "production:view"))],
)
async def upcoming_operations(
    session: AsyncSession = Depends(get_tenant_session),
    from_time: Optional[datetime] = Query(None, description="Only operations with planned_start >= from_time"),
    to_time: Optional[datetime] = Query(None, description="Only operations with planned_start <= to_time"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(200, ge=1, le=2000),
    offset: int = Query(0, ge=0),
) -> List[WorkOrderOperationRead]:
    """
    Return tenant-scoped operations suitable for scheduling UI.
    """
    conditions = [WorkOrderOperation.planned_start.is_not(None)]
    if from_time is not None:
        conditions.append(WorkOrderOperation.planned_start >= from_time)
    if to_time is not None:
        conditions.append(WorkOrderOperation.planned_start <= to_time)
    if status is not None:
        conditions.append(WorkOrderOperation.status == status)

    stmt = (
        select(WorkOrderOperation)
        .where(and_(*conditions))
        .order_by(WorkOrderOperation.planned_start.asc())
        .offset(offset)
        .limit(limit)
    )
    res = await session.execute(stmt)
    ops = list(res.scalars())
    return [WorkOrderOperationRead.model_validate(x) for x in ops]
