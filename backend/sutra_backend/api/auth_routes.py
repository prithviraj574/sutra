from __future__ import annotations

from fastapi import APIRouter, Depends

from sutra_backend.api.github import github_router
from sutra_backend.auth.dependencies import get_current_user
from sutra_backend.models import User
from sutra_backend.schemas.auth import AuthMeResponse, UserRead


auth_router = APIRouter()
auth_router.include_router(github_router)


@auth_router.get("/auth/me", tags=["auth"], response_model=AuthMeResponse)
def read_current_user(user: User = Depends(get_current_user)) -> AuthMeResponse:
    return AuthMeResponse(user=UserRead.model_validate(user, from_attributes=True))
