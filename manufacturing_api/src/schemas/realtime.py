from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class WsEnvelope(BaseModel):
    """Envelope for WebSocket messages."""
    type: str = Field(..., description="Message type (e.g., 'kpi.snapshot', 'schedule.update').")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Message payload.")
    at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp (UTC).")
    user_id: Optional[UUID] = Field(default=None, description="Sender user id, if applicable.")
    channel: Optional[str] = Field(default=None, description="Optional sub-channel (e.g., board id).")


class KpiSnapshot(BaseModel):
    """Snapshot of core dashboard KPIs."""
    oee: float = Field(..., description="Estimated Overall Equipment Effectiveness (0-100).")
    scrap_rate: float = Field(..., description="Scrap rate as a percentage (0-100).")
    downtime_minutes: float = Field(..., description="Total downtime minutes for the recent period.")
    at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Snapshot timestamp (UTC).")


class SchedulerEvent(BaseModel):
    """Scheduler collaboration event."""
    event: str = Field(..., description="Event type (e.g., 'operation.move', 'operation.assign', 'schedule.update').")
    details: Dict[str, Any] = Field(default_factory=dict, description="Event details.")
    operation_id: Optional[UUID] = Field(default=None, description="Related operation id, if applicable.")
    board: Optional[str] = Field(default=None, description="Optional planner board/channel key.")
    at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Event timestamp (UTC).")
    user_id: Optional[UUID] = Field(default=None, description="Initiating user id (from token), if known.")
