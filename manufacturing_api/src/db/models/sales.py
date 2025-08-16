from __future__ import annotations

from typing import Optional
from sqlalchemy import Text, Numeric, Date
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base, UUIDPkMixin, TimestampMixin, TenantMixin


class Customer(UUIDPkMixin, TenantMixin, TimestampMixin, Base):
    """Customer master."""
    __tablename__ = "customers"

    code: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    billing_address: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    shipping_address: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class SalesOrder(UUIDPkMixin, TenantMixin, TimestampMixin, Base):
    """Sales order header."""
    __tablename__ = "sales_orders"

    so_number: Mapped[str] = mapped_column(Text, nullable=False)
    customer_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    status: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    order_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    due_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    total_amount: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class SalesOrderLine(UUIDPkMixin, TenantMixin, TimestampMixin, Base):
    """Sales order line item."""
    __tablename__ = "sales_order_lines"

    sales_order_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    line_no: Mapped[int] = mapped_column(nullable=False)
    item_sku: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    qty_ordered: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    qty_shipped: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)
    uom: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    unit_price: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)
