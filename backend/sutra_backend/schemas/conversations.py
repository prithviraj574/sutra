from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_id: UUID | None = None
    agent_id: UUID | None = None
    mode: str
    latest_response_id: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    actor_type: str
    actor_id: UUID | None = None
    content: str
    response_chain_id: str | None = None
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    items: list[ConversationRead]


class MessageListResponse(BaseModel):
    items: list[MessageRead]


class TeamConversationListResponse(BaseModel):
    items: list[ConversationRead]


class ConversationStreamEvent(BaseModel):
    event_id: str
    type: str
    conversation_id: UUID
    agent_id: UUID | None = None
    timestamp: datetime
    sequence: int
    payload: dict[str, Any] = Field(default_factory=dict)
