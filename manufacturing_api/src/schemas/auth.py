from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class TokenPair(BaseModel):
    """Access and refresh tokens."""
    token_type: str = Field("bearer", description="Token type, typically 'bearer'")
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")


class RefreshRequest(BaseModel):
    """Request to refresh an access token."""
    refresh_token: str = Field(..., description="Refresh token")


class RegisterRequest(BaseModel):
    """Registration details for creating a new user."""
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., min_length=6, description="User password")
    full_name: Optional[str] = Field(None, description="Full name")


class Message(BaseModel):
    """Simple message response."""
    message: str = Field(...)


class UserRead(BaseModel):
    """User read model."""
    id: UUID = Field(..., description="User ID")
    email: EmailStr = Field(..., description="User email")
    full_name: Optional[str] = Field(None)
    is_active: bool = Field(..., description="Active flag")
    is_superadmin: bool = Field(..., description="Superadmin flag")
    created_at: datetime = Field(..., description="Created timestamp")
    updated_at: datetime = Field(..., description="Updated timestamp")
    roles: List[str] = Field(default_factory=list, description="Role names assigned to the user")

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    """Admin create user payload."""
    email: EmailStr = Field(..., description="Email")
    password: str = Field(..., min_length=6, description="Password")
    full_name: Optional[str] = Field(None)
    is_active: Optional[bool] = Field(default=True)
    is_superadmin: Optional[bool] = Field(default=False)


class UserUpdate(BaseModel):
    """Admin update user payload."""
    email: Optional[EmailStr] = Field(None)
    password: Optional[str] = Field(None, min_length=6)
    full_name: Optional[str] = Field(None)
    is_active: Optional[bool] = Field(None)
    is_superadmin: Optional[bool] = Field(None)


class RoleRead(BaseModel):
    """Role read model."""
    id: UUID = Field(..., description="Role ID")
    name: str = Field(..., description="Role name")
    description: Optional[str] = Field(None)
    created_at: datetime = Field(..., description="Created timestamp")
    updated_at: datetime = Field(..., description="Updated timestamp")

    class Config:
        from_attributes = True


class RoleCreate(BaseModel):
    """Create role payload."""
    name: str = Field(..., description="Role name")
    description: Optional[str] = Field(None, description="Description")


class RoleUpdate(BaseModel):
    """Update role payload."""
    name: Optional[str] = Field(None)
    description: Optional[str] = Field(None)
