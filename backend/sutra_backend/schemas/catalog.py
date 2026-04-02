from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from sutra_backend.enums import AgentStatus, ArtifactKind, RuntimeKind, TeamMode, ToolProfile, WorkspaceItemKind


class TeamRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    description: str | None = None
    mode: TeamMode
    shared_workspace_uri: str | None = None
    created_at: datetime
    updated_at: datetime


class AgentRead(BaseModel):
    id: UUID
    user_id: UUID
    team_ids: list[UUID] = Field(default_factory=list)
    role_template_id: UUID | None = None
    name: str
    role_name: str
    status: AgentStatus
    runtime_kind: RuntimeKind
    hermes_home_uri: str | None = None
    private_volume_uri: str | None = None
    shared_workspace_enabled: bool
    created_at: datetime
    updated_at: datetime


class TeamListResponse(BaseModel):
    items: list[TeamRead]


class AgentListResponse(BaseModel):
    items: list[AgentRead]


class RoleTemplateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    key: str
    name: str
    description: str | None = None
    default_system_prompt: str
    default_tool_profile: ToolProfile
    created_at: datetime
    updated_at: datetime


class RoleTemplateListResponse(BaseModel):
    items: list[RoleTemplateRead]


class TeamAgentCreate(BaseModel):
    role_template_key: str
    name: str | None = None


class TeamCreateRequest(BaseModel):
    name: str
    description: str | None = None
    agents: list[TeamAgentCreate]


class TeamCreateResponse(BaseModel):
    team: TeamRead
    agents: list[AgentRead]


class SharedWorkspaceItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_id: UUID
    path: str
    kind: WorkspaceItemKind
    size_bytes: int | None = None
    content_text: str | None = None
    conversation_id: UUID | None = None
    agent_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class ArtifactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_id: UUID | None = None
    conversation_id: UUID | None = None
    agent_id: UUID | None = None
    name: str
    kind: ArtifactKind
    uri: str
    mime_type: str | None = None
    preview_uri: str | None = None
    github_repo: str | None = None
    github_branch: str | None = None
    github_sha: str | None = None
    created_at: datetime
    updated_at: datetime


class TeamArtifactListResponse(BaseModel):
    items: list[ArtifactRead]


class TeamWorkspaceResponse(BaseModel):
    team: TeamRead
    items: list[SharedWorkspaceItemRead]


class WorkspaceItemUpsertRequest(BaseModel):
    path: str
    kind: WorkspaceItemKind = WorkspaceItemKind.FILE
    content_text: str | None = None


class WorkspaceItemUpsertResponse(BaseModel):
    item: SharedWorkspaceItemRead
