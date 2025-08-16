from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class IDModel(BaseModel):
    """Base schema exposing a UUID primary key."""
    id: UUID = Field(..., description="Unique identifier")


class Timestamps(BaseModel):
    """Common created/updated timestamp fields."""
    created_at: datetime = Field(..., description="Creation timestamp (UTC)")
    updated_at: datetime = Field(..., description="Last update timestamp (UTC)")


class Pagination(BaseModel):
    """Pagination parameters."""
    limit: int = Field(100, ge=1, le=1000, description="Max number of records to return")
    offset: int = Field(0, ge=0, description="Number of records to skip")


class MessageResponse(BaseModel):
    """Standard message response."""
    message: str = Field(..., description="Human readable message")
    details: Optional[dict] = Field(default=None, description="Optional extra data")


class TenantEcho(BaseModel):
    """Model to echo tenant context."""
    tenant_id: UUID = Field(..., description="Tenant ID extracted from request header")
