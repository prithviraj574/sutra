from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from sutra_backend.enums import GitHubAccountType


class GitHubConnectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    installation_id: str
    account_login: str
    account_type: GitHubAccountType
    connected_at: datetime
    created_at: datetime
    updated_at: datetime


class GitHubConnectionResponse(BaseModel):
    connection: GitHubConnectionRead


class GitHubConnectionStatusResponse(BaseModel):
    connection: GitHubConnectionRead | None


class GitHubOAuthCallbackResponse(BaseModel):
    success: bool
    connection: GitHubConnectionRead
