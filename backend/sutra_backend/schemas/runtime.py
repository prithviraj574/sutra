from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AgentResponseCreateRequest(BaseModel):
    input: str | list[dict[str, Any]]
    instructions: str | None = None
    conversation_id: UUID | None = None
    previous_response_id: str | None = None
    store: bool = True
    model: str = "hermes-agent"
    metadata: dict[str, Any] = Field(default_factory=dict)
    secret_ids: list[UUID] = Field(default_factory=list)


class AgentResponseCreateResponse(BaseModel):
    conversation_id: UUID
    response_id: str
    output_text: str
    raw_response: dict[str, Any]
    workspace_item_id: UUID | None = None
