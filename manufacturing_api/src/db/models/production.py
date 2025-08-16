from __future__ import annotations

from typing import Optional
from sqlalchemy import Text, Numeric, DateTime, Date
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base, UUIDPkMixin, TimestampMixin, TenantMixin


class WorkOrder(UUIDPkMixin, TenantMixin, TimestampMixin, Base):
    """Manufacturing work order header."""
    __tablename__ = "work_orders"

    order_no: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    item_sku: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    quantity_planned: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)
    quantity_completed: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)
    due_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    start_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    priority: Mapped[Optional[int]] = mapped_column(nullable=True)
    sales_order_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    bom_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    routing_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)


class WorkOrderOperation(UUIDPkMixin, TenantMixin, TimestampMixin, Base):
    """Operations/steps within a work order."""
    __tablename__ = "work_order_operations"

    work_order_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    seq_no: Mapped[int] = mapped_column(nullable=False)
    operation_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    work_center: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    planned_start: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    planned_end: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_start: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_end: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    quantity_good: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)
    quantity_scrap: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)


class ProductionLog(UUIDPkMixin, TenantMixin, TimestampMixin, Base):
    """General production event log (start/stop/scrap/downtime, etc.)."""
    __tablename__ = "production_logs"

    work_order_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    operation_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_by: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    log_type: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    quantity: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)
    duration_minutes: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)
    metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class ProductionStatusEvent(UUIDPkMixin, TenantMixin, TimestampMixin, Base):
    """Status change tracking for production entities."""
    __tablename__ = "production_status_events"

    entity_type: Mapped[str] = mapped_column(Text, nullable=False)  # e.g., work_order/operation
    entity_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    reason_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
