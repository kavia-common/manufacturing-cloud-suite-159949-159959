from __future__ import annotations

from typing import Optional
from sqlalchemy import Text, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base, UUIDPkMixin, TimestampMixin, TenantMixin


class Inspection(UUIDPkMixin, TenantMixin, TimestampMixin, Base):
    """Quality inspection record (lot or work order context)."""
    __tablename__ = "inspections"

    lot_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    work_order_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    inspector_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    inspection_date: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class Nonconformance(UUIDPkMixin, TenantMixin, TimestampMixin, Base):
    """Quality nonconformance entry for issues and dispositions."""
    __tablename__ = "nonconformances"

    source_type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # e.g., lot/wo/so
    source_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    severity: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    disposition: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    closed_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
