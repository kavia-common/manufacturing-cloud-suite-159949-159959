from __future__ import annotations

from typing import Optional
from sqlalchemy import Text, Boolean, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base, UUIDPkMixin, TimestampMixin, TenantMixin


class UnitOfMeasure(UUIDPkMixin, TenantMixin, TimestampMixin, Base):
    """Unit of Measure master (e.g. EA, KG, HR)."""
    __tablename__ = "units_of_measure"

    code: Mapped[str] = mapped_column(Text, nullable=False)  # e.g., EA, KG
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # quantity/time/length/etc.


class Item(UUIDPkMixin, TenantMixin, TimestampMixin, Base):
    """Item/product master record."""
    __tablename__ = "items"

    sku: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    default_uom_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("units_of_measure.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # active/inactive/obsolete/etc.


class WorkCenter(UUIDPkMixin, TenantMixin, TimestampMixin, Base):
    """Work center or machine definition."""
    __tablename__ = "work_centers"

    code: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    asset_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True)


class Routing(UUIDPkMixin, TenantMixin, TimestampMixin, Base):
    """Manufacturing routing for an item."""
    __tablename__ = "routings"

    code: Mapped[str] = mapped_column(Text, nullable=False)
    item_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("items.id", ondelete="SET NULL"), nullable=True)
    revision: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")


class RoutingOperation(UUIDPkMixin, TenantMixin, TimestampMixin, Base):
    """Operations within a routing sequence."""
    __tablename__ = "routing_operations"

    routing_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("routings.id", ondelete="CASCADE"), nullable=False)
    seq_no: Mapped[int] = mapped_column(nullable=False)
    operation_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    work_center_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("work_centers.id", ondelete="SET NULL"), nullable=True)
    standard_time_minutes: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)


class Bom(UUIDPkMixin, TenantMixin, TimestampMixin, Base):
    """Bill of Materials for an item."""
    __tablename__ = "boms"

    code: Mapped[str] = mapped_column(Text, nullable=False)
    item_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("items.id", ondelete="SET NULL"), nullable=True)
    revision: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")


class BomLine(UUIDPkMixin, TenantMixin, TimestampMixin, Base):
    """Components required by a BOM."""
    __tablename__ = "bom_lines"

    bom_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("boms.id", ondelete="CASCADE"), nullable=False)
    line_no: Mapped[int] = mapped_column(nullable=False)
    component_item_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("items.id", ondelete="RESTRICT"), nullable=False)
    qty_per: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    uom_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("units_of_measure.id", ondelete="SET NULL"), nullable=True)
