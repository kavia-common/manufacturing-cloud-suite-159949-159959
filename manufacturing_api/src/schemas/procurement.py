from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SupplierRead(BaseModel):
    """Supplier read model."""
    id: UUID = Field(..., description="Supplier ID")
    code: str = Field(..., description="Supplier code")
    name: str = Field(..., description="Supplier name")
    email: Optional[str] = Field(None)
    phone: Optional[str] = Field(None)
    address: dict = Field(default_factory=dict)
    created_at: datetime = Field(..., description="Created at")
    updated_at: datetime = Field(..., description="Updated at")

    class Config:
        from_attributes = True


class SupplierCreate(BaseModel):
    """Create supplier payload."""
    code: str = Field(..., description="Unique code")
    name: str = Field(..., description="Supplier name")
    email: Optional[str] = Field(None)
    phone: Optional[str] = Field(None)
    address: dict = Field(default_factory=dict)


class PurchaseOrderRead(BaseModel):
    """PO header read model."""
    id: UUID = Field(..., description="PO ID")
    po_number: str = Field(..., description="PO number")
    supplier_id: UUID = Field(..., description="Supplier")
    status: Optional[str] = Field(None)
    order_date: Optional[date] = Field(None)
    expected_date: Optional[date] = Field(None)
    total_amount: Optional[float] = Field(None)
    currency: Optional[str] = Field(None)
    created_at: datetime = Field(..., description="Created at")
    updated_at: datetime = Field(..., description="Updated at")

    class Config:
        from_attributes = True


class PurchaseOrderLineRead(BaseModel):
    """PO line read model."""
    id: UUID = Field(..., description="Line ID")
    purchase_order_id: UUID = Field(..., description="PO id")
    line_no: int = Field(..., description="Line number")
    item_sku: str = Field(..., description="Item SKU")
    description: Optional[str] = Field(None)
    qty_ordered: float = Field(..., description="Ordered qty")
    qty_received: Optional[float] = Field(None)
    uom: Optional[str] = Field(None)
    unit_price: Optional[float] = Field(None)
    created_at: datetime = Field(..., description="Created at")
    updated_at: datetime = Field(..., description="Updated at")

    class Config:
        from_attributes = True


class PurchaseOrderCreate(BaseModel):
    """Create PO header payload."""
    po_number: str = Field(..., description="PO number (unique within tenant)")
    supplier_id: UUID = Field(..., description="Supplier id")
    status: Optional[str] = Field("open")
    order_date: Optional[date] = Field(None)
    expected_date: Optional[date] = Field(None)
    total_amount: Optional[float] = Field(None)
    currency: Optional[str] = Field(None)
