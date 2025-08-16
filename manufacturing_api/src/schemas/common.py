from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
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


class ErrorInfo(BaseModel):
    """Structured error description."""
    type: str = Field(..., description="Machine-readable error type code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Any] = Field(default=None, description="Optional error details (e.g., validation issues)")


# PUBLIC_INTERFACE
class ErrorResponse(BaseModel):
    """Standardized API error envelope returned by exception handlers."""
    status: int = Field(..., description="HTTP status code")
    error: ErrorInfo = Field(..., description="Error details")
    correlation_id: Optional[str] = Field(default=None, description="Request correlation ID")
    tenant_id: Optional[str] = Field(default=None, description="Tenant ID (if available)")
    path: Optional[str] = Field(default=None, description="Request path")
    method: Optional[str] = Field(default=None, description="HTTP method")
    timestamp: datetime = Field(..., description="Error timestamp (UTC)")
