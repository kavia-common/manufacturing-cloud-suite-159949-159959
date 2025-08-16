from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict
from uuid import uuid4

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi import WebSocket, WebSocketDisconnect

from src.core.settings import get_app_settings
from src.core.deps import get_tenant_id
from src.core.security import decode_token
from src.core.logging import configure_logging, correlation_id_var, tenant_id_var
from src.db.run_migrations import main as run_alembic
from src.db.seed import seed_all
from src.schemas.common import ErrorInfo, ErrorResponse, MessageResponse, TenantEcho
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

# Configure structured logging once at import
configure_logging()
logger = logging.getLogger(__name__)

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
    {"name": "Reports", "description": "Exportable business reports (CSV/Excel/PDF)."},
]

app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    openapi_tags=openapi_tags,
)

# CORS - avoid wildcard with credentials
cors_allow_credentials = settings.CORS_ALLOW_CREDENTIALS
if settings.CORS_ORIGINS == ["*"] and cors_allow_credentials:
    logger.warning("CORS_ALLOW_CREDENTIALS=True with '*' origins is not permitted; disabling credentials.")
    cors_allow_credentials = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=cors_allow_credentials,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    """
    Enrich request context with correlation_id and tenant_id for logging and error responses.
    Adds 'X-Correlation-ID' to every response.
    """
    corr = request.headers.get("X-Correlation-ID") or request.headers.get("X-Request-ID") or str(uuid4())
    tenant = request.headers.get("X-Tenant-ID")
    # Set context vars for this request lifecycle
    token_corr = correlation_id_var.set(corr)
    token_tenant = tenant_id_var.set(tenant)
    request.state.correlation_id = corr
    request.state.tenant_id = tenant

    logger.info("Incoming request %s %s", request.method, request.url.path)
    try:
        response = await call_next(request)
    except Exception as exc:
        # Let the global exception handlers format response consistently
        correlation_id_var.reset(token_corr)
        tenant_id_var.reset(token_tenant)
        raise exc

    response.headers["X-Correlation-ID"] = corr
    # Restore previous context
    correlation_id_var.reset(token_corr)
    tenant_id_var.reset(token_tenant)
    return response


def _build_error_response(
    request: Request,
    status_code: int,
    error_type: str,
    message: str,
    details: Any | None = None,
) -> JSONResponse:
    """Build a standardized ErrorResponse JSONResponse."""
    ts = datetime.now(tz=timezone.utc)
    corr = getattr(request.state, "correlation_id", None)
    tenant = getattr(request.state, "tenant_id", None)
    err = ErrorResponse(
        status=status_code,
        error=ErrorInfo(type=error_type, message=message, details=details),
        correlation_id=corr,
        tenant_id=tenant,
        path=request.url.path,
        method=request.method,
        timestamp=ts,
    )
    return JSONResponse(status_code=status_code, content=err.model_dump(mode="json"))


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Global handler for HTTPException to produce a standardized error envelope.
    """
    # For validation errors fastapi may wrap, but they are handled by RequestValidationError
    detail = exc.detail if isinstance(exc.detail, str) else "HTTP Error"
    return _build_error_response(
        request=request,
        status_code=exc.status_code,
        error_type="http_error",
        message=str(detail),
        details=None if isinstance(exc.detail, str) else exc.detail,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Global handler for request validation errors with a standard structure.
    """
    return _build_error_response(
        request=request,
        status_code=422,
        error_type="validation_error",
        message="Request validation failed",
        details=exc.errors(),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    Catch-all handler to avoid leaking stack traces and to return a structured error.
    """
    logger.exception("Unhandled error processing request")
    return _build_error_response(
        request=request,
        status_code=500,
        error_type="internal_error",
        message="An unexpected error occurred",
        details=None,
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


# Build API v1 router and include sub-routers
api_v1 = APIRouter(prefix="/api/v1")

# PUBLIC_INTERFACE
@api_v1.get(
    "/health",
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
@api_v1.get(
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
@api_v1.get(
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


# Include all routers under /api/v1
api_v1.include_router(auth_router)
api_v1.include_router(users_router)
api_v1.include_router(roles_router)
api_v1.include_router(masterdata_router)
api_v1.include_router(inventory_router)
api_v1.include_router(procurement_router)
api_v1.include_router(production_router)
api_v1.include_router(quality_router)
api_v1.include_router(scheduling_router)
api_v1.include_router(reports_router)

# Attach api_v1 to app
app.include_router(api_v1)


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
