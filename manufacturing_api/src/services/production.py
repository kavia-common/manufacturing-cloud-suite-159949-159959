from __future__ import annotations

import logging

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.production import ProductionLog, WorkOrder, WorkOrderOperation
from src.repositories.production import WorkOrderRepository
from src.schemas.production import WorkOrderCreate
from src.schemas.realtime import KpiSnapshot, SchedulerEvent
from src.services.base import BaseService
from src.services.realtime import broadcast_manager

logger = logging.getLogger(__name__)


class ProductionService(BaseService):
    """
    Domain service for production features.

    Handles orchestrating repository actions and pushing real-time updates to subscribers.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.wo_repo = WorkOrderRepository(session)

    # PUBLIC_INTERFACE
    async def create_work_order(self, payload: WorkOrderCreate, tenant_id: UUID) -> WorkOrder:
        """
        Create a work order and broadcast relevant scheduler/KPI updates.

        Parameters:
            payload: WorkOrderCreate request
            tenant_id: Tenant context for broadcasting topics
        Returns:
            Created WorkOrder entity
        """
        created = await self.wo_repo.create_work_order(payload)

        # Fire a scheduler collaboration event so scheduler UIs can refresh
        try:
            evt = SchedulerEvent(event="work_order.created", details={"order_no": created.order_no, "work_order_id": str(created.id)})
            await broadcast_manager.publish_scheduler_event(tenant_id, evt)
        except Exception:
            logger.exception("Failed to publish scheduler event after create_work_order")

        # Publish a KPI snapshot for dashboards
        try:
            snapshot = await self._compute_kpis_snapshot()
            await broadcast_manager.publish_kpi_snapshot(tenant_id, snapshot)
        except Exception:
            logger.exception("Failed to publish KPI snapshot after create_work_order")

        return created

    async def _compute_kpis_snapshot(self) -> KpiSnapshot:
        """
        Compute a simple KPI snapshot from WorkOrderOperation and ProductionLog.

        Calculations:
          - scrap_rate = total_scrap / (total_good + total_scrap) * 100
          - downtime_minutes = sum(duration_minutes where log_type='downtime')
          - oee (estimate): quality rate * 100 (availability/performance components not derived here)
        """
        # totals from operations
        op_res = await self.session.execute(
            select(
                func.coalesce(func.sum(WorkOrderOperation.quantity_good), 0.0),
                func.coalesce(func.sum(WorkOrderOperation.quantity_scrap), 0.0),
            )
        )
        total_good, total_scrap = op_res.one()
        denom = float(total_good or 0) + float(total_scrap or 0)
        scrap_rate = (float(total_scrap) / denom * 100.0) if denom > 0 else 0.0

        # downtime minutes
        dt_res = await self.session.execute(
            select(func.coalesce(func.sum(ProductionLog.duration_minutes), 0.0)).where(ProductionLog.log_type == "downtime")
        )
        downtime_minutes = float(dt_res.scalar_one())

        # OEE as quality component proxy
        quality_rate = ((float(total_good) / denom) if denom > 0 else 1.0)
        oee_estimate = quality_rate * 100.0

        return KpiSnapshot(oee=round(oee_estimate, 2), scrap_rate=round(scrap_rate, 2), downtime_minutes=round(downtime_minutes, 2))
