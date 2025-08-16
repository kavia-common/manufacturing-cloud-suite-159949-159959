from __future__ import annotations

from typing import Optional
from sqlalchemy import Text, Numeric, Date, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, UUIDPkMixin, TimestampMixin, TenantMixin


class Location(UUIDPkMixin, TenantMixin, TimestampMixin, Base):
    """Inventory storage location (e.g., warehouse, shelf, bin)."""
    __tablename__ = "locations"

    code: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parent_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.id", ondelete="SET NULL"), nullable=True
    )

    parent: Mapped["Location"] = relationship("Location", remote_side="Location.id")


class Lot(UUIDPkMixin, TenantMixin, TimestampMixin, Base):
    """Inventory lot/batch representing a quantity of an item."""
    __tablename__ = "lots"

    lot_no: Mapped[str] = mapped_column(Text, nullable=False)
    item_sku: Mapped[str] = mapped_column(Text, nullable=False)
    uom: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    quantity_on_hand: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)
    expiration_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class InventoryTransaction(UUIDPkMixin, TenantMixin, TimestampMixin, Base):
    """Movement of inventory quantity between locations/lots with a reason."""
    __tablename__ = "inventory_transactions"

    lot_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lots.id", ondelete="SET NULL"), nullable=True
    )
    from_location_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.id", ondelete="SET NULL"), nullable=True
    )
    to_location_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.id", ondelete="SET NULL"), nullable=True
    )
    quantity: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    uom: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reason_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ref_type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # e.g., WO/PO/SO
    ref_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
