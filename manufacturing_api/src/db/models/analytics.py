from __future__ import annotations

from typing import Optional
from sqlalchemy import Text, Numeric, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base, UUIDPkMixin, TimestampMixin, TenantMixin


class Event(UUIDPkMixin, TenantMixin, TimestampMixin, Base):
    """Application event stream for audit/analytics."""
    __tablename__ = "events"

    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    entity_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    severity: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class KpiMeasurement(UUIDPkMixin, TenantMixin, TimestampMixin, Base):
    """Time-series KPI measurements captured for analytics."""
    __tablename__ = "kpi_measurements"

    metric_name: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    unit: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    dimensions: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
