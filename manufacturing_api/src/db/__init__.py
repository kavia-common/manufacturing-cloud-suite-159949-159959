"""
Database package initializer exposing key public interfaces for configuration,
engine/session management, and tenant context helpers.
"""

from .base import Base
from .config import get_settings, Settings
from .session import (
    get_engine,
    get_async_session,
    set_current_tenant,
    tenant_context,
)

# Import models to ensure they are registered with SQLAlchemy metadata
# when the db package is imported.
from . import models as models  # noqa: F401

__all__ = [
    "Base",
    "Settings",
    "get_settings",
    "get_engine",
    "get_async_session",
    "set_current_tenant",
    "tenant_context",
    "models",
]
