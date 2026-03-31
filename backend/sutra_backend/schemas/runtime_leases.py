from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RuntimeLeaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    agent_id: UUID
    vm_id: str
    host_vm_id: str | None = None
    host_api_base_url: str | None = None
    state: str
    provider: str
    api_base_url: str | None = None
    last_heartbeat_at: datetime | None = None
    started_at: datetime | None = None
    ready: bool
    heartbeat_fresh: bool
    readiness_stage: str
    readiness_reason: str
    probe_detail: str | None = None
    probe_checked_url: str | None = None
    isolation_ok: bool
    isolation_reason: str
    created_at: datetime
    updated_at: datetime


class RuntimeLeaseResponse(BaseModel):
    lease: RuntimeLeaseRead
