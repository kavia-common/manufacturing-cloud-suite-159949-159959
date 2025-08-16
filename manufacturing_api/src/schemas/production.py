from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class WorkOrderRead(BaseModel):
    """Work order read model."""
    id: UUID = Field(..., description="Work order id")
    order_no: str = Field(..., description="Order number")
    status: Optional[str] = Field(None)
    item_sku: Optional[str] = Field(None)
    quantity_planned: Optional[float] = Field(None)
    quantity_completed: Optional[float] = Field(None)
    due_date: Optional[date] = Field(None)
    start_date: Optional[date] = Field(None)
    end_date: Optional[date] = Field(None)
    priority: Optional[int] = Field(None)
    sales_order_id: Optional[UUID] = Field(None)
    bom_id: Optional[UUID] = Field(None)
    routing_id: Optional[UUID] = Field(None)
    created_at: datetime = Field(..., description="Created at")
    updated_at: datetime = Field(..., description="Updated at")

    class Config:
        from_attributes = True


class WorkOrderCreate(BaseModel):
    """Create work order payload."""
    order_no: str = Field(..., description="Order number")
    status: Optional[str] = Field("planned")
    item_sku: Optional[str] = Field(None)
    quantity_planned: Optional[float] = Field(None)
    due_date: Optional[date] = Field(None)
    priority: Optional[int] = Field(None)
    sales_order_id: Optional[UUID] = Field(None)
    bom_id: Optional[UUID] = Field(None)
    routing_id: Optional[UUID] = Field(None)


class WorkOrderOperationRead(BaseModel):
    """Work order operation read model."""
    id: UUID = Field(..., description="Operation id")
    work_order_id: UUID = Field(..., description="Work order id")
    seq_no: int = Field(..., description="Sequence number")
    operation_code: Optional[str] = Field(None)
    work_center: Optional[str] = Field(None)
    planned_start: Optional[datetime] = Field(None)
    planned_end: Optional[datetime] = Field(None)
    actual_start: Optional[datetime] = Field(None)
    actual_end: Optional[datetime] = Field(None)
    status: Optional[str] = Field(None)
    quantity_good: Optional[float] = Field(None)
    quantity_scrap: Optional[float] = Field(None)
    created_at: datetime = Field(..., description="Created at")
    updated_at: datetime = Field(..., description="Updated at")

    class Config:
        from_attributes = True
