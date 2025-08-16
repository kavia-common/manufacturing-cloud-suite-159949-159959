from __future__ import annotations

from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """
    Application-level settings for the FastAPI service.

    This is separate from src.db.config.Settings, which focuses on the database layer.
    """

    # FastAPI metadata
    APP_NAME: str = Field(default="Manufacturing API")
    APP_DESCRIPTION: str = Field(
        default=(
            "Backend API for a multi-tenant manufacturing ERP/MES platform. "
            "Provides business logic, data access, and integrations."
        )
    )
    APP_VERSION: str = Field(default="0.1.0")

    # CORS
    CORS_ORIGINS: List[str] = Field(
        default_factory=lambda: ["*"],
        description="Comma-separated list or JSON array of allowed origins. Default: *",
    )
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True)
    CORS_ALLOW_METHODS: List[str] = Field(default_factory=lambda: ["*"])
    CORS_ALLOW_HEADERS: List[str] = Field(default_factory=lambda: ["*"])

    # Startup behavior
    RUN_MIGRATIONS_ON_STARTUP: bool = Field(
        default=True,
        description="If true, run Alembic migrations (upgrade head) at app startup.",
    )
    AUTO_SEED: bool = Field(
        default=False,
        description="If true, run minimal database seeding after migrations.",
    )

    # Tenancy defaults (used only by utilities or examples)
    DEFAULT_TENANT_SLUG: str = Field(default="acme")

    # Environment label
    ENVIRONMENT: Optional[str] = Field(
        default=None, description="Environment label (dev/test/prod)"
    )

    # Automatically load from .env at runtime. The orchestrator will provide these.
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors_origins(cls, v):
        """
        Accept both JSON array format and comma-separated formats for CORS origins.
        """
        if v is None:
            return ["*"]
        if isinstance(v, str):
            # Try comma-separated
            parts = [p.strip() for p in v.split(",") if p.strip()]
            return parts or ["*"]
        if isinstance(v, list):
            return v or ["*"]
        return ["*"]


# PUBLIC_INTERFACE
def get_app_settings() -> AppSettings:
    """
    Return a new AppSettings instance populated from environment variables.

    Note:
      For simplicity we construct a new instance each time. If caching is desired,
      we can add a module-level cache or lru_cache.
    """
    return AppSettings()
