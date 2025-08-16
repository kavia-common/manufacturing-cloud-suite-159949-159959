from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.settings import get_app_settings
from src.core.deps import get_tenant_id
from src.db.run_migrations import main as run_alembic
from src.db.seed import seed_all
from src.schemas.common import MessageResponse, TenantEcho

# Routers
from src.api.routes.auth import router as auth_router
from src.api.routes.users import router as users_router
from src.api.routes.roles import router as roles_router

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

settings = get_app_settings()

openapi_tags = [
    {"name": "System", "description": "System and operational endpoints."},
    {"name": "Health", "description": "Liveness and readiness probes."},
    {"name": "Auth", "description": "Authentication and token endpoints."},
    {"name": "Users", "description": "User administration endpoints."},
    {"name": "Roles", "description": "Role administration endpoints."},
    {
        "name": "WebSocket",
        "description": "WebSocket usage, endpoints, and connection details.",
    },
]

app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    openapi_tags=openapi_tags,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)


@app.on_event("startup")
async def on_startup() -> None:
    """
    Run migrations and optional seeding on service startup.

    This ensures the database schema is up to date. Seeding is opt-in via settings.
    """
    if settings.RUN_MIGRATIONS_ON_STARTUP:
        try:
            logger.info("Running Alembic migrations: upgrade head")
            run_alembic(["upgrade", "head"])
            logger.info("Migrations completed.")
        except Exception as exc:
            logger.exception("Migration step failed: %s", exc)
            # Do not crash the app in case of transient DB issues; rely on retries or later readiness probes.

    if settings.AUTO_SEED:
        try:
            logger.info("Running database seeding...")
            await seed_all()
            logger.info("Seeding completed.")
        except Exception as exc:
            logger.exception("Seeding step failed: %s", exc)
            # Safe to continue without seed; environments may not require it.


# PUBLIC_INTERFACE
@app.get(
    "/",
    response_model=MessageResponse,
    summary="Health Check",
    tags=["Health"],
)
def health_check() -> MessageResponse:
    """
    Basic liveness health check endpoint.

    Returns:
        MessageResponse: Simple confirmation that the service is running.
    """
    return MessageResponse(message="Healthy")


# PUBLIC_INTERFACE
@app.get(
    "/health/tenant",
    response_model=TenantEcho,
    summary="Tenant Health Echo",
    description="Echoes the tenant context to verify header handling and RLS setup.",
    tags=["Health"],
)
async def tenant_health_echo(tenant_id=Depends(get_tenant_id)) -> TenantEcho:
    """
    Echo the provided tenant ID to verify multi-tenant request handling.

    Parameters:
        X-Tenant-ID (header): UUID of the tenant.
    Returns:
        TenantEcho: The tenant_id extracted from the header.
    """
    return TenantEcho(tenant_id=tenant_id)


# PUBLIC_INTERFACE
@app.get(
    "/websocket-info",
    response_model=Dict[str, Any],
    summary="WebSocket Usage Information",
    description=(
        "Provides connection details for WebSocket endpoints, including authentication "
        "and subscription patterns. This is a placeholder for future real-time features."
    ),
    tags=["WebSocket"],
)
def websocket_info() -> Dict[str, Any]:
    """
    Describe how to connect to WebSocket endpoints in this service.

    Returns:
        JSON object with 'usage' notes and 'endpoints' list.
    """
    return {
        "usage": (
            "WebSocket endpoints will be documented here. In general, connect to "
            "ws(s)://<host>/ws/<topic>?token=<JWT> and include X-Tenant-ID header "
            "as applicable. Messages use JSON frames with 'type' and 'payload'."
        ),
        "endpoints": [],
    }

# Register routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(roles_router)


# Example dependency wiring for future endpoints:
# from fastapi import APIRouter
# router = APIRouter(prefix="/inventory", tags=["Inventory"])
#
# @router.get("/locations", response_model=list[LocationRead])
# async def list_locations(
#     session=Depends(get_tenant_session),
#     limit: int = 100, offset: int = 0,
# ):
#     repo = LocationRepository(session)
#     records = await repo.list_locations(limit=limit, offset=offset)
#     return [LocationRead.model_validate(r) for r in records]
#
# app.include_router(router)
