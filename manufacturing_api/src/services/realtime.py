from __future__ import annotations

import asyncio

import logging
from typing import Dict, Optional, Set
from uuid import UUID

from starlette.websockets import WebSocket, WebSocketState

from src.schemas.realtime import KpiSnapshot, SchedulerEvent, WsEnvelope

logger = logging.getLogger(__name__)


class BroadcastManager:
    """
    Simple in-process pub-sub manager for WebSocket topics.

    Topics:
      - dashboard:{tenant_id}
      - scheduler:{tenant_id} or scheduler:{tenant_id}:{board}
    """

    def __init__(self) -> None:
        self._topics: Dict[str, Set[WebSocket]] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

    def _topic_lock(self, topic: str) -> asyncio.Lock:
        if topic not in self._locks:
            self._locks[topic] = asyncio.Lock()
        return self._locks[topic]

    # PUBLIC_INTERFACE
    def dashboard_topic(self, tenant_id: UUID | str) -> str:
        """Return dashboard topic name for tenant."""
        return f"dashboard:{tenant_id}"

    # PUBLIC_INTERFACE
    def scheduler_topic(self, tenant_id: UUID | str, board: Optional[str] = None) -> str:
        """Return scheduler topic name for tenant and optional board channel."""
        base = f"scheduler:{tenant_id}"
        if board:
            return f"{base}:{board}"
        return base

    async def _ensure_topic(self, topic: str) -> None:
        async with self._global_lock:
            if topic not in self._topics:
                self._topics[topic] = set()

    # PUBLIC_INTERFACE
    async def connect(self, topic: str, websocket: WebSocket) -> None:
        """
        Accept the connection and add websocket to topic subscribers.
        """
        await self._ensure_topic(topic)
        async with self._topic_lock(topic):
            self._topics[topic].add(websocket)
            logger.info("WebSocket connected to topic=%s; subscribers=%d", topic, len(self._topics[topic]))

    # PUBLIC_INTERFACE
    async def disconnect(self, topic: str, websocket: WebSocket) -> None:
        """Remove websocket from topic subscribers."""
        if topic not in self._topics:
            return
        async with self._topic_lock(topic):
            self._topics[topic].discard(websocket)
            logger.info("WebSocket disconnected from topic=%s; subscribers=%d", topic, len(self._topics[topic]))

    # PUBLIC_INTERFACE
    async def broadcast(self, topic: str, message: dict, exclude: Optional[WebSocket] = None) -> None:
        """
        Broadcast a dict message to all subscribers in the topic.
        """
        await self._ensure_topic(topic)
        payload = message
        async with self._topic_lock(topic):
            to_drop: list[WebSocket] = []
            for ws in list(self._topics[topic]):
                if exclude is not None and ws is exclude:
                    continue
                try:
                    if ws.application_state == WebSocketState.DISCONNECTED or ws.client_state == WebSocketState.DISCONNECTED:
                        to_drop.append(ws)
                        continue
                    await ws.send_json(payload)
                except Exception:
                    logger.exception("Failed to send message to websocket; scheduling drop")
                    to_drop.append(ws)
            for ws in to_drop:
                self._topics[topic].discard(ws)

    # PUBLIC_INTERFACE
    async def publish_kpi_snapshot(self, tenant_id: UUID | str, snapshot: KpiSnapshot) -> None:
        """Publish KPI snapshot to dashboard topic for tenant."""
        env = WsEnvelope(type="kpi.snapshot", payload=snapshot.model_dump(), channel=None)
        await self.broadcast(self.dashboard_topic(tenant_id), env.model_dump())

    # PUBLIC_INTERFACE
    async def publish_scheduler_event(self, tenant_id: UUID | str, event: SchedulerEvent) -> None:
        """Publish scheduler collaboration event to scheduler topic for tenant (and optional board)."""
        topic = self.scheduler_topic(tenant_id, event.board)
        env = WsEnvelope(type=f"scheduler.{event.event}", payload=event.model_dump(), channel=event.board)
        await self.broadcast(topic, env.model_dump())


# Singleton instance
broadcast_manager = BroadcastManager()
