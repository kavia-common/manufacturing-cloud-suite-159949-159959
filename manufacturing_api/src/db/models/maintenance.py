from __future__ import annotations

from typing import Optional
from sqlalchemy import Text, Numeric, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base, UUIDPkMixin, TimestampMixin, TenantMixin


class Asset(UUIDPkMixin, TenantMixin, TimestampMixin, Base):
    """Maintained asset (machine, tool, etc.)."""
    __tablename__ = "assets"

    code: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    location_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class MaintenanceWorkOrder(UUIDPkMixin, TenantMixin, TimestampMixin, Base):
    """Maintenance work order header."""
    __tablename__ = "maintenance_work_orders"

    asset_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    wo_number: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    requested_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    due_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    completed_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    created_by: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)


class MaintenanceLog(UUIDPkMixin, TenantMixin, TimestampMixin, Base):
    """Maintenance work order activity log."""
    __tablename__ = "maintenance_logs"

    maintenance_work_order_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    log_type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_minutes: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)
    cost: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)
