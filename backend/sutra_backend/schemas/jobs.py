from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from sutra_backend.schemas.catalog import SharedWorkspaceItemRead


class AutomationJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_id: UUID | None = None
    agent_id: UUID | None = None
    name: str
    schedule: str
    prompt: str
    enabled: bool
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AutomationJobListResponse(BaseModel):
    items: list[AutomationJobRead]


class AutomationJobCreateRequest(BaseModel):
    name: str
    schedule: str
    prompt: str
    team_id: UUID | None = None
    agent_id: UUID | None = None
    enabled: bool = True


class AutomationJobUpdateRequest(BaseModel):
    name: str | None = None
    schedule: str | None = None
    prompt: str | None = None
    enabled: bool | None = None


class AutomationJobResponse(BaseModel):
    job: AutomationJobRead


class AutomationJobRunResponse(BaseModel):
    job: AutomationJobRead
    conversation_id: UUID | None = None
    response_id: str | None = None
    output_text: str | None = None
    workspace_item_id: UUID | None = None
    generated_items: list[SharedWorkspaceItemRead] = []
