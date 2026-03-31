from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PollerLeaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    owner_id: str | None = None
    state: str
    last_heartbeat_at: datetime | None = None
    lease_expires_at: datetime | None = None
    last_sweep_started_at: datetime | None = None
    last_sweep_completed_at: datetime | None = None
    last_executed_count: int
    created_at: datetime
    updated_at: datetime


class PollerStatusResponse(BaseModel):
    enabled: bool
    interval_seconds: int
    lease_seconds: int
    max_tasks_per_sweep: int
    is_active: bool
    lease: PollerLeaseRead | None = None
