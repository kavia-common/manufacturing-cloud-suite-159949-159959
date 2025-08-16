from __future__ import annotations

from sqlalchemy import MetaData, DateTime, text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# Standardized naming convention for alembic-friendly constraints/indexes.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base class with metadata naming conventions."""
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UUIDPkMixin:
    """Mixin that provides a UUID primary key with server-side generation."""
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )


class TimestampMixin:
    """Mixin that provides created_at and updated_at timestamp columns."""
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )


class TenantMixin:
    """Mixin that provides tenant scoping and FK to tenants.id."""
    tenant_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        server_default=text("current_setting('app.tenant_id', true)::uuid"),
    )
