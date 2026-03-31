from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from sutra_backend.auth.dependencies import get_current_user
from sutra_backend.config import Settings, get_app_settings
from sutra_backend.db import get_session
from sutra_backend.models import User
from sutra_backend.schemas.catalog import ArtifactRead, SharedWorkspaceItemRead
from sutra_backend.schemas.github_integration import (
    GitHubExportRequest,
    GitHubExportResponse,
    GitHubRepositoryListResponse,
    GitHubRepositoryRead,
)
from sutra_backend.services.github_integration import (
    GitHubIntegrationError,
    export_workspace_item_to_github,
    list_accessible_repositories,
)
from sutra_backend.services.teams import TeamServiceError


github_integration_router = APIRouter(prefix="/github", tags=["github"])


@github_integration_router.get("/repositories", response_model=GitHubRepositoryListResponse)
def get_github_repositories(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_app_settings),
) -> GitHubRepositoryListResponse:
    try:
        repositories = list_accessible_repositories(session, user=user, settings=settings)
    except GitHubIntegrationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return GitHubRepositoryListResponse(
        items=[
            GitHubRepositoryRead.model_validate(repository, from_attributes=True)
            for repository in repositories
        ]
    )


@github_integration_router.post(
    "/teams/{team_id}/workspace/items/{item_id}/export",
    response_model=GitHubExportResponse,
)
def export_workspace_item(
    team_id: UUID,
    item_id: UUID,
    payload: GitHubExportRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_app_settings),
) -> GitHubExportResponse:
    try:
        result = export_workspace_item_to_github(
            session,
            user=user,
            settings=settings,
            team_id=team_id,
            item_id=item_id,
            repository_full_name=payload.repository_full_name,
            path=payload.path,
            branch=payload.branch,
            commit_message=payload.commit_message,
        )
    except TeamServiceError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except GitHubIntegrationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return GitHubExportResponse(
        artifact_id=result.artifact.id,
        artifact=ArtifactRead.model_validate(result.artifact, from_attributes=True),
        item=SharedWorkspaceItemRead.model_validate(result.item, from_attributes=True),
        repository_full_name=result.repository_full_name,
        branch=result.branch,
        commit_sha=result.commit_sha,
        content_url=result.content_url,
        commit_url=result.commit_url,
    )
