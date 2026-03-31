from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from sutra_backend.schemas.catalog import ArtifactRead, SharedWorkspaceItemRead


class GitHubRepositoryRead(BaseModel):
    id: int
    name: str
    full_name: str
    default_branch: str
    private: bool


class GitHubRepositoryListResponse(BaseModel):
    items: list[GitHubRepositoryRead]


class GitHubExportRequest(BaseModel):
    repository_full_name: str
    path: str
    branch: str | None = None
    commit_message: str


class GitHubExportResponse(BaseModel):
    artifact_id: UUID
    artifact: ArtifactRead
    item: SharedWorkspaceItemRead
    repository_full_name: str
    branch: str
    commit_sha: str
    content_url: str
    commit_url: str
