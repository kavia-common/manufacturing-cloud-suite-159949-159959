from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import WebSocket, WebSocketDisconnect


from src.core.settings import get_app_settings
from src.core.deps import get_tenant_id
from src.core.security import decode_token
from src.db.run_migrations import main as run_alembic
from src.db.seed import seed_all
from src.schemas.common import MessageResponse, TenantEcho
from src.schemas.realtime import WsEnvelope
from src.services.realtime import broadcast_manager
from src.services.production import ProductionService
from src.db.session import get_engine
from sqlalchemy.ext.asyncio import async_sessionmaker

# Routers
from src.api.routes.auth import router as auth_router
from src.api.routes.users import router as users_router
from src.api.routes.roles import router as roles_router
# Domain routers
from src.api.routes.inventory import router as inventory_router
from src.api.routes.procurement import router as procurement_router
from src.api.routes.production import router as production_router
from src.api.routes.master_data import router as masterdata_router
from src.api.routes.quality import router as quality_router
from src.api.routes.scheduling import router as scheduling_router
from src.api.routes.reports import router as reports_router

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

settings = get_app_settings()

openapi_tags = [
    {"name": "System", "description": "System and operational endpoints."},
    {"name": "Health", "description": "Liveness and readiness probes."},
    {"name": "Auth", "description": "Authentication and token endpoints."},
    {"name": "Users", "description": "User administration endpoints."},
    {"name": "Roles", "description": "Role administration endpoints."},
    {"name": "Inventory", "description": "Inventory locations, lots, transactions."},
    {"name": "Procurement", "description": "Suppliers and purchase orders."},
    {"name": "Production", "description": "Work orders and operations."},
    {"name": "Master Data", "description": "Items/products and BOMs."},
    {"name": "Quality", "description": "Inspections and nonconformances."},
    {"name": "Scheduling", "description": "Planner/scheduler feeds."},
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
        JSON object with usage notes and endpoints list describing query params, headers, and message format.
    """
    return {
        "usage": (
            "Connect with a valid user JWT as a 'token' query parameter and include the 'X-Tenant-ID' header. "
            "For scheduler collaboration, clients may send messages which are re-broadcast to all subscribers. "
            "Message format is JSON with fields: { type: string, payload: object, at: ISO-8601, user_id?: string, channel?: string }."
        ),
        "security": {
            "token": "JWT must contain 'sub' (user id) and 'tenant_id' matching the X-Tenant-ID header.",
            "header": "X-Tenant-ID: UUID"
        },
        "endpoints": [
            {
                "path": "/ws/dashboard",
                "summary": "Real-time dashboard KPI snapshots (server push).",
                "query": ["token"],
                "headers": ["X-Tenant-ID"],
                "messages": {
                    "server_to_client": ["kpi.snapshot"]
                }
            },
            {
                "path": "/ws/scheduler",
                "summary": "Real-time collaborative scheduler board.",
                "query": ["token", "board?"],
                "headers": ["X-Tenant-ID"],
                "messages": {
                    "client_to_server": ["schedule.update", "operation.move", "operation.assign", "ping"],
                    "server_to_client": ["scheduler.schedule.update", "scheduler.operation.move", "scheduler.operation.assign", "kpi.snapshot"]
                }
            }
        ],
        "notes": "WebSocket endpoints are not represented in OpenAPI schema; refer to this endpoint for usage."
    }

# Register routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(roles_router)
# Domain routers
app.include_router(masterdata_router)
app.include_router(inventory_router)
app.include_router(procurement_router)
app.include_router(production_router)
app.include_router(quality_router)
app.include_router(scheduling_router)
app.include_router(reports_router)


async def _validate_ws_and_get_user(websocket: WebSocket) -> tuple[str, str]:
    """
    Validate WebSocket connection by checking 'token' query param and 'X-Tenant-ID' header.

    Returns:
        (tenant_id, user_id)
    Raises:
        WebSocketDisconnect if invalid.
    """
    token = websocket.query_params.get("token")
    tenant_id = websocket.headers.get("x-tenant-id")
    if not token or not tenant_id:
        # We must accept first to send close code details. If not yet accepted, accept then close.
        try:
            await websocket.accept()
        except Exception:
            pass
        await websocket.close(code=4401)
        raise WebSocketDisconnect(code=4401)

    try:
        claims = decode_token(token)
    except Exception:
        try:
            await websocket.accept()
        except Exception:
            pass
        await websocket.close(code=4401)
        raise WebSocketDisconnect(code=4401)

    if str(claims.get("tenant_id")) != str(tenant_id):
        try:
            await websocket.accept()
        except Exception:
            pass
        await websocket.close(code=4403)
        raise WebSocketDisconnect(code=4403)

    user_id = claims.get("sub")
    if not user_id:
        try:
            await websocket.accept()
        except Exception:
            pass
        await websocket.close(code=4401)
        raise WebSocketDisconnect(code=4401)

    return str(tenant_id), str(user_id)


# PUBLIC_INTERFACE
@app.websocket("/ws/dashboard")
async def ws_dashboard(websocket: WebSocket):
    """
    WebSocket endpoint for real-time dashboard KPI updates.

    Security:
      - Query param 'token' must be a valid JWT.
      - Header 'X-Tenant-ID' must match JWT tenant_id.
    Messages:
      - Server -> Client: type='kpi.snapshot' payload=KpiSnapshot
      - Client -> Server: optional 'ping' to keepalive; other messages ignored.
    """
    await websocket.accept()
    try:
        tenant_id, user_id = await _validate_ws_and_get_user(websocket)
    except WebSocketDisconnect:
        return

    topic = broadcast_manager.dashboard_topic(tenant_id)
    await broadcast_manager.connect(topic, websocket)

    # Send initial KPI snapshot on connect
    try:
        # Create a session to compute initial KPIs within tenant context
        engine = get_engine()
        maker = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False, autocommit=False)
        async with maker() as session:
            from src.db.session import tenant_context as _tenant_context
            async with _tenant_context(session, tenant_id):
                svc = ProductionService(session)
                snapshot = await svc._compute_kpis_snapshot()
        env = WsEnvelope(type="kpi.snapshot", payload=snapshot.model_dump()).model_dump()
        await websocket.send_json(env)
    except Exception:
        logger.exception("Failed to send initial KPI snapshot")

    try:
        while True:
            # Receive but ignore client messages except ping
            msg = await websocket.receive_text()
            if msg and msg.lower() == "ping":
                await websocket.send_text("pong")
            # otherwise ignore client messages for dashboard
    except WebSocketDisconnect:
        await broadcast_manager.disconnect(topic, websocket)
    except Exception:
        logger.exception("Error on ws_dashboard connection")
        await broadcast_manager.disconnect(topic, websocket)
        await websocket.close()


# PUBLIC_INTERFACE
@app.websocket("/ws/scheduler")
async def ws_scheduler(websocket: WebSocket):
    """
    WebSocket endpoint for real-time collaborative scheduler updates.

    Security:
      - Query param 'token' must be a valid JWT.
      - Header 'X-Tenant-ID' must match JWT tenant_id.

    Query Parameters:
      - token: JWT bearer token
      - board: Optional channel/board key

    Messages:
      - Client -> Server:
          type: 'schedule.update' | 'operation.move' | 'operation.assign' | 'ping'
          payload: object
      - Server -> Client:
          Rebroadcasts as 'scheduler.<type>' envelopes to all subscribers.

    Notes:
      The server does not persist scheduler messages here; persistence should be handled
      by REST endpoints or other dedicated routes. This channel is for collaboration.
    """
    await websocket.accept()
    try:
        tenant_id, user_id = await _validate_ws_and_get_user(websocket)
    except WebSocketDisconnect:
        return

    board = websocket.query_params.get("board")
    topic = broadcast_manager.scheduler_topic(tenant_id, board=board)
    await broadcast_manager.connect(topic, websocket)

    # Optionally push a KPI snapshot on scheduler connect to help boards display context
    try:
        engine = get_engine()
        maker = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False, autocommit=False)
        async with maker() as session:
            from src.db.session import tenant_context as _tenant_context
            async with _tenant_context(session, tenant_id):
                svc = ProductionService(session)
                snapshot = await svc._compute_kpis_snapshot()
        env = WsEnvelope(type="kpi.snapshot", payload=snapshot.model_dump(), channel=board).model_dump()
        await websocket.send_json(env)
    except Exception:
        logger.exception("Failed to send initial KPI snapshot to scheduler client")

    try:
        while True:
            data = await websocket.receive_json()
            # normalize envelope
            msg_type = data.get("type")
            payload = data.get("payload") or {}
            if msg_type == "ping":
                await websocket.send_text("pong")
                continue

            if not isinstance(msg_type, str):
                # ignore malformed
                continue

            # Rebroadcast to topic subscribers with namespaced type
            env = WsEnvelope(type=f"scheduler.{msg_type}", payload=payload, channel=board)
            await broadcast_manager.broadcast(topic, env.model_dump(), exclude=websocket)
    except WebSocketDisconnect:
        await broadcast_manager.disconnect(topic, websocket)
    except Exception:
        logger.exception("Error on ws_scheduler connection")
        await broadcast_manager.disconnect(topic, websocket)
        await websocket.close()


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
