from __future__ import annotations

from typing import Optional
from sqlalchemy import Boolean, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, UUIDPkMixin, TimestampMixin, TenantMixin


class User(UUIDPkMixin, TenantMixin, TimestampMixin, Base):
    """Application user within a tenant."""
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
    )

    email: Mapped[str] = mapped_column(Text, nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    hashed_password: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    is_superadmin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    roles: Mapped[list["Role"]] = relationship(
        "Role",
        secondary="user_roles",
        primaryjoin="User.id==UserRole.user_id",
        secondaryjoin="Role.id==UserRole.role_id",
        back_populates="users",
        lazy="selectin",
    )


class Role(UUIDPkMixin, TenantMixin, TimestampMixin, Base):
    """Role assigned to users; groups permissions."""
    __tablename__ = "roles"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_roles_tenant_name"),
    )

    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    users: Mapped[list["User"]] = relationship(
        "User",
        secondary="user_roles",
        primaryjoin="Role.id==UserRole.role_id",
        secondaryjoin="User.id==UserRole.user_id",
        back_populates="roles",
        lazy="selectin",
    )
    permissions: Mapped[list["Permission"]] = relationship(
        "Permission",
        secondary="role_permissions",
        primaryjoin="Role.id==RolePermission.role_id",
        secondaryjoin="Permission.id==RolePermission.permission_id",
        back_populates="roles",
        lazy="selectin",
    )


class Permission(UUIDPkMixin, TenantMixin, TimestampMixin, Base):
    """Atomic permission code attached to roles."""
    __tablename__ = "permissions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_permissions_tenant_code"),
    )

    code: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    roles: Mapped[list["Role"]] = relationship(
        "Role",
        secondary="role_permissions",
        primaryjoin="Permission.id==RolePermission.permission_id",
        secondaryjoin="Role.id==RolePermission.role_id",
        back_populates="permissions",
        lazy="selectin",
    )


class UserRole(UUIDPkMixin, TenantMixin, TimestampMixin, Base):
    """Association of users to roles."""
    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", "role_id", name="uq_user_roles_tenant_user_role"),
    )

    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)


class RolePermission(UUIDPkMixin, TenantMixin, TimestampMixin, Base):
    """Association of roles to permissions."""
    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "role_id", "permission_id", name="uq_role_permissions_tenant_role_permission"),
    )

    role_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    permission_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False)
