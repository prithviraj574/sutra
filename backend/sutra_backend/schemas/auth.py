from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    firebase_uid: str
    email: str
    display_name: str | None = None
    photo_url: str | None = None
    created_at: datetime
    updated_at: datetime


class AuthMeResponse(BaseModel):
    user: UserRead
