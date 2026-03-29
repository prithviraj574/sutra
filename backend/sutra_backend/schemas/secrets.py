from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SecretCreateRequest(BaseModel):
    name: str
    value: str
    provider: str | None = None
    scope: str = "user"
    team_id: UUID | None = None
    agent_id: UUID | None = None


class SecretRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    team_id: UUID | None = None
    agent_id: UUID | None = None
    name: str
    provider: str | None = None
    scope: str
    last_used_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class SecretListResponse(BaseModel):
    items: list[SecretRead]


class SecretCreateResponse(BaseModel):
    secret: SecretRead


class SecretDeleteResponse(BaseModel):
    id: UUID
    deleted: bool
