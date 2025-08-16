from __future__ import annotations

import re
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings for database configuration and general environment.

    Reads from environment variables (or .env via pydantic-settings). Compatible
    with the manufacturing_db container variables:
      - POSTGRES_URL
      - POSTGRES_USER
      - POSTGRES_PASSWORD
      - POSTGRES_DB
      - POSTGRES_PORT
    """

    # Database (compatible with manufacturing_db env)
    POSTGRES_URL: Optional[str] = Field(
        default=None, description="If provided, full PostgreSQL connection URL."
    )
    POSTGRES_USER: Optional[str] = Field(default=None, description="DB username")
    POSTGRES_PASSWORD: Optional[str] = Field(default=None, description="DB password")
    POSTGRES_DB: Optional[str] = Field(default=None, description="Database name")
    POSTGRES_PORT: Optional[int] = Field(
        default=5432, description="Database port (default 5432)"
    )
    POSTGRES_HOST: Optional[str] = Field(
        default="localhost", description="Database host (default localhost)"
    )

    # SQLAlchemy engine options
    SQL_ECHO: bool = Field(
        default=False, description="Echo SQL statements for debugging (default False)"
    )

    # General environment
    ENVIRONMENT: Optional[str] = Field(
        default=None, description="Environment label (dev/test/prod)"
    )

    # Automatically load from .env at runtime. The orchestrator will provide these.
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    @property
    def database_url(self) -> str:
        """
        Compute the base (sync-neutral) database URL. Will prefer POSTGRES_URL
        if present, otherwise construct from individual POSTGRES_* variables.
        """
        if self.POSTGRES_URL:
            return self.POSTGRES_URL

        if not all([self.POSTGRES_USER, self.POSTGRES_PASSWORD, self.POSTGRES_DB]):
            raise ValueError(
                "Database configuration missing. Ensure POSTGRES_URL or "
                "POSTGRES_USER, POSTGRES_PASSWORD, and POSTGRES_DB are set in the environment."
            )
        host = self.POSTGRES_HOST or "localhost"
        port = self.POSTGRES_PORT or 5432
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{host}:{port}/{self.POSTGRES_DB}"

    @property
    def async_database_url(self) -> str:
        """
        Convert base URL to an asyncpg-enabled SQLAlchemy URL, required for AsyncEngine.
        """
        url = self.database_url
        # Normalize to postgresql+asyncpg scheme
        if url.startswith("postgresql+asyncpg://"):
            return url
        # Replace any existing driver marker or bare scheme with +asyncpg
        return re.sub(r"^postgresql(\+\w+)?://", "postgresql+asyncpg://", url)

    @property
    def sync_database_url(self) -> str:
        """
        Provide a sync URL variant. For Alembic offline mode this is sufficient; for
        online mode we use async URL. We avoid requiring psycopg by returning the base
        postgresql:// URL.
        """
        url = self.database_url
        # Strip any async driver tag if present
        return re.sub(r"^postgresql\+\w+://", "postgresql://", url)


# PUBLIC_INTERFACE
def get_settings() -> Settings:
    """Return a singleton-like settings object for reuse across modules."""
    # Settings is cheap to construct; for simplicity, we return a new instance.
    # If runtime caching is desired, we can implement an LRU or module-level cache.
    return Settings()
