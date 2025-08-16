from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class LocationRead(BaseModel):
    """Read model for inventory Location."""
    id: UUID = Field(..., description="Location ID")
    code: str = Field(..., description="Location code")
    name: Optional[str] = Field(None, description="Location name")
    type: Optional[str] = Field(None, description="Location type")
    parent_id: Optional[UUID] = Field(None, description="Parent location ID")
    created_at: datetime = Field(..., description="Creation timestamp (UTC)")
    updated_at: datetime = Field(..., description="Last update timestamp (UTC)")

    class Config:
        from_attributes = True


class LotRead(BaseModel):
    """Read model for inventory Lot (batch)."""
    id: UUID = Field(..., description="Lot ID")
    lot_no: str = Field(..., description="Lot number")
    item_sku: str = Field(..., description="Item SKU")
    uom: Optional[str] = Field(None, description="Unit of measure")
    quantity_on_hand: Optional[float] = Field(None, description="Quantity on hand")
    expiration_date: Optional[date] = Field(None, description="Expiration date")
    status: Optional[str] = Field(None, description="Lot status")
    created_at: datetime = Field(..., description="Created timestamp")
    updated_at: datetime = Field(..., description="Updated timestamp")

    class Config:
        from_attributes = True


class InventoryTransactionRead(BaseModel):
    """Read model for inventory transaction."""
    id: UUID = Field(..., description="Transaction ID")
    lot_id: Optional[UUID] = Field(None, description="Lot ID")
    from_location_id: Optional[UUID] = Field(None, description="From location ID")
    to_location_id: Optional[UUID] = Field(None, description="To location ID")
    quantity: float = Field(..., description="Quantity moved")
    uom: Optional[str] = Field(None, description="Unit of measure")
    reason_code: Optional[str] = Field(None, description="Reason code")
    ref_type: Optional[str] = Field(None, description="Reference type")
    ref_id: Optional[UUID] = Field(None, description="Reference ID")
    metadata: dict = Field(default_factory=dict, description="Additional details")
    created_at: datetime = Field(..., description="Created timestamp")
    updated_at: datetime = Field(..., description="Updated timestamp")

    class Config:
        from_attributes = True
