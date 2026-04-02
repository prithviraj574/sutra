from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from sutra_backend.enums import TeamTaskSource, TeamTaskStatus, TeamTaskUpdateType
from sutra_backend.schemas.catalog import SharedWorkspaceItemRead


class TeamResponseCreateRequest(BaseModel):
    input: str | list[dict[str, Any]]
    conversation_id: UUID | None = None
    instructions: str | None = None
    secret_ids: list[UUID] = Field(default_factory=list)


class TeamMemberResponseRead(BaseModel):
    agent_id: UUID
    agent_name: str
    role_name: str
    response_id: str
    output_text: str


class TeamTaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_id: UUID
    conversation_id: UUID
    assigned_agent_id: UUID
    title: str
    instruction: str
    status: TeamTaskStatus
    source: TeamTaskSource
    claim_token: str | None = None
    claimed_at: datetime | None = None
    claim_expires_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class TeamTaskUpdateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID
    team_id: UUID
    agent_id: UUID | None = None
    event_type: TeamTaskUpdateType
    content: str
    created_at: datetime
    updated_at: datetime


class TeamResponseCreateResponse(BaseModel):
    conversation_id: UUID
    output_text: str
    outputs: list[TeamMemberResponseRead]
    workspace_item_id: UUID | None = None
    generated_items: list[SharedWorkspaceItemRead] = Field(default_factory=list)


class TeamHuddleCreateRequest(BaseModel):
    input: str | list[dict[str, Any]]
    conversation_id: UUID | None = None
    instructions: str | None = None
    secret_ids: list[UUID] = Field(default_factory=list)


class TeamHuddleCreateResponse(BaseModel):
    conversation_id: UUID
    output_text: str
    outputs: list[TeamMemberResponseRead]
    tasks: list[TeamTaskRead]
    workspace_item_id: UUID | None = None


class TeamTaskListResponse(BaseModel):
    items: list[TeamTaskRead]


class TeamTaskUpdateListResponse(BaseModel):
    items: list[TeamTaskUpdateRead]


class TeamTaskDelegateRequest(BaseModel):
    assigned_agent_id: UUID
    note: str | None = None


class TeamTaskReportRequest(BaseModel):
    content: str
    agent_id: UUID | None = None


class TeamTaskMessageRequest(BaseModel):
    content: str
    agent_id: UUID | None = None


class TeamTaskCompleteRequest(BaseModel):
    content: str
    agent_id: UUID | None = None
    claim_token: str | None = None


class TeamTaskMutationResponse(BaseModel):
    task: TeamTaskRead


class AgentInboxClaimResponse(BaseModel):
    task: TeamTaskRead | None = None


class AgentInboxRunResponse(BaseModel):
    task: TeamTaskRead | None = None
    conversation_id: UUID | None = None
    response_id: str | None = None
    output_text: str | None = None
    workspace_item_id: UUID | None = None


class TeamInboxCycleItemRead(BaseModel):
    agent_id: UUID
    task: TeamTaskRead | None = None
    conversation_id: UUID | None = None
    response_id: str | None = None
    output_text: str | None = None
    workspace_item_id: UUID | None = None


class TeamInboxCycleResponse(BaseModel):
    executed_count: int
    results: list[TeamInboxCycleItemRead]
