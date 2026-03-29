from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TeamRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    description: str | None = None
    mode: str
    shared_workspace_uri: str | None = None
    created_at: datetime
    updated_at: datetime


class AgentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_id: UUID
    role_template_id: UUID | None = None
    name: str
    role_name: str
    status: str
    runtime_kind: str
    hermes_home_uri: str | None = None
    private_volume_uri: str | None = None
    shared_workspace_enabled: bool
    created_at: datetime
    updated_at: datetime


class TeamListResponse(BaseModel):
    items: list[TeamRead]


class AgentListResponse(BaseModel):
    items: list[AgentRead]
