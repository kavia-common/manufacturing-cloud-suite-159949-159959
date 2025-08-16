from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.deps import get_tenant_session, require_roles
from src.repositories.qual import QualityRepository
from src.schemas.quality import InspectionRead, NonconformanceRead

router = APIRouter(prefix="/quality", tags=["Quality"])


# PUBLIC_INTERFACE
@router.get(
    "/inspections",
    response_model=List[InspectionRead],
    summary="List inspections",
    description="List quality inspections ordered by created_at desc.",
    dependencies=[Depends(require_roles("admin", "quality:view"))],
)
async def list_inspections(
    session: AsyncSession = Depends(get_tenant_session),
    work_order_id: Optional[UUID] = Query(None, description="Filter by work order"),
    lot_id: Optional[UUID] = Query(None, description="Filter by lot"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> List[InspectionRead]:
    repo = QualityRepository(session)
    rows = await repo.list_inspections(
        work_order_id=work_order_id, lot_id=lot_id, status=status, limit=limit, offset=offset
    )
    return [InspectionRead.model_validate(x) for x in rows]


# PUBLIC_INTERFACE
@router.get(
    "/nonconformances",
    response_model=List[NonconformanceRead],
    summary="List nonconformances",
    description="List quality nonconformances ordered by created_at desc.",
    dependencies=[Depends(require_roles("admin", "quality:view"))],
)
async def list_nonconformances(
    session: AsyncSession = Depends(get_tenant_session),
    status: Optional[str] = Query(None, description="Filter by status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> List[NonconformanceRead]:
    repo = QualityRepository(session)
    rows = await repo.list_nonconformances(
        status=status, severity=severity, limit=limit, offset=offset
    )
    return [NonconformanceRead.model_validate(x) for x in rows]
