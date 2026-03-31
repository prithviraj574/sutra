from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from sutra_backend.auth.dependencies import get_current_user
from sutra_backend.config import Settings, get_app_settings
from sutra_backend.db import get_session
from sutra_backend.models import User
from sutra_backend.schemas.secrets import (
    SecretCreateRequest,
    SecretCreateResponse,
    SecretDeleteResponse,
    SecretListResponse,
    SecretRead,
)
from sutra_backend.services.secrets import (
    SecretVaultError,
    delete_user_secret,
    list_user_secrets,
    upsert_user_secret,
)


secrets_router = APIRouter()


@secrets_router.get("/secrets", tags=["secrets"], response_model=SecretListResponse)
def list_secrets(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> SecretListResponse:
    secrets = list_user_secrets(session, user=user)
    return SecretListResponse(
        items=[SecretRead.model_validate(secret, from_attributes=True) for secret in secrets]
    )


@secrets_router.post(
    "/secrets",
    tags=["secrets"],
    response_model=SecretCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_secret(
    payload: SecretCreateRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_app_settings),
) -> SecretCreateResponse:
    try:
        secret = upsert_user_secret(
            session,
            user=user,
            settings=settings,
            name=payload.name,
            value=payload.value,
            provider=payload.provider,
            scope=payload.scope,
            team_id=payload.team_id,
            agent_id=payload.agent_id,
        )
    except SecretVaultError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return SecretCreateResponse(secret=SecretRead.model_validate(secret, from_attributes=True))


@secrets_router.delete("/secrets/{secret_id}", tags=["secrets"], response_model=SecretDeleteResponse)
def remove_secret(
    secret_id: UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> SecretDeleteResponse:
    deleted = delete_user_secret(session, user=user, secret_id=secret_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Secret not found.")

    return SecretDeleteResponse(id=secret_id, deleted=True)
