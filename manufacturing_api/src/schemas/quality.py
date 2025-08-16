from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class InspectionRead(BaseModel):
    """Quality inspection read model."""
    id: UUID = Field(..., description="Inspection id")
    lot_id: Optional[UUID] = Field(None)
    work_order_id: Optional[UUID] = Field(None)
    status: Optional[str] = Field(None)
    result: Optional[str] = Field(None)
    inspector_id: Optional[UUID] = Field(None)
    inspection_date: Optional[datetime] = Field(None)
    data: dict = Field(default_factory=dict)
    created_at: datetime = Field(..., description="Created at")
    updated_at: datetime = Field(..., description="Updated at")

    class Config:
        from_attributes = True


class NonconformanceRead(BaseModel):
    """Nonconformance read model."""
    id: UUID = Field(..., description="NC id")
    source_type: Optional[str] = Field(None)
    source_id: Optional[UUID] = Field(None)
    severity: Optional[str] = Field(None)
    description: Optional[str] = Field(None)
    disposition: Optional[str] = Field(None)
    status: Optional[str] = Field(None)
    closed_at: Optional[datetime] = Field(None)
    created_at: datetime = Field(..., description="Created at")
    updated_at: datetime = Field(..., description="Updated at")

    class Config:
        from_attributes = True
