from __future__ import annotations

from datetime import datetime
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
