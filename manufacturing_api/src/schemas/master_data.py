from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ItemRead(BaseModel):
    """Item (product) read model."""
    id: UUID = Field(..., description="Item ID")
    sku: str = Field(..., description="Item SKU")
    name: str = Field(..., description="Item name")
    description: Optional[str] = Field(None)
    default_uom_id: Optional[UUID] = Field(None)
    status: Optional[str] = Field(None)
    created_at: datetime = Field(..., description="Created timestamp")
    updated_at: datetime = Field(..., description="Updated timestamp")

    class Config:
        from_attributes = True


class ItemCreate(BaseModel):
    """Create item payload."""
    sku: str = Field(..., description="SKU (unique within tenant)")
    name: str = Field(..., description="Name")
    description: Optional[str] = Field(None)
    default_uom_id: Optional[UUID] = Field(None)
    status: Optional[str] = Field("active")


class BomRead(BaseModel):
    """BOM read model."""
    id: UUID = Field(..., description="BOM ID")
    code: str = Field(..., description="BOM code")
    item_id: Optional[UUID] = Field(None, description="BOM item id")
    revision: Optional[str] = Field(None)
    is_active: bool = Field(..., description="Active flag")
    created_at: datetime = Field(..., description="Created at")
    updated_at: datetime = Field(..., description="Updated at")

    class Config:
        from_attributes = True


class BomLineRead(BaseModel):
    """BOM line read model."""
    id: UUID = Field(..., description="Line ID")
    bom_id: UUID = Field(..., description="BOM ID")
    line_no: int = Field(..., description="Line number")
    component_item_id: UUID = Field(..., description="Component item id")
    qty_per: float = Field(..., description="Quantity per")
    uom_id: Optional[UUID] = Field(None)
    created_at: datetime = Field(..., description="Created at")
    updated_at: datetime = Field(..., description="Updated at")

    class Config:
        from_attributes = True
