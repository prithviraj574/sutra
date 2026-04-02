from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from sqlmodel import Session, select

from sutra_backend.config import Settings
from sutra_backend.models import AgentTeam, Artifact, GitHubConnection, SharedWorkspaceItem, User
from sutra_backend.services.teams import TeamServiceError


class GitHubIntegrationError(RuntimeError):
    """Raised when GitHub integration cannot be completed safely."""


@dataclass(frozen=True)
class GitHubRepository:
    id: int
    name: str
    full_name: str
    default_branch: str
    private: bool


@dataclass(frozen=True)
class GitHubExportResult:
    artifact: Artifact
    item: SharedWorkspaceItem
    repository_full_name: str
    branch: str
    commit_sha: str
    content_url: str
    commit_url: str


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _build_app_jwt(settings: Settings) -> str:
    if not settings.github_app_id or not settings.github_app_private_key:
        raise GitHubIntegrationError("GitHub App credentials are not configured.")

    header = _b64url(json.dumps({"alg": "RS256", "typ": "JWT"}, separators=(",", ":")).encode("utf-8"))
    now = int(time.time())
    payload = _b64url(
        json.dumps(
            {
                "iat": now - 60,
                "exp": now + 540,
                "iss": settings.github_app_id,
            },
            separators=(",", ":"),
        ).encode("utf-8")
    )
    signing_input = f"{header}.{payload}".encode("utf-8")

    private_key = serialization.load_pem_private_key(
        settings.github_app_private_key.encode("utf-8"),
        password=None,
    )
    signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    return f"{header}.{payload}.{_b64url(signature)}"


def _github_headers(token: str, *, is_jwt: bool = False) -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        **({} if is_jwt else {}),
    }


def _get_owned_connection(session: Session, *, user: User) -> GitHubConnection:
    connection = session.exec(
        select(GitHubConnection).where(GitHubConnection.user_id == user.id)
    ).first()
    if connection is None:
        raise GitHubIntegrationError("GitHub is not connected.")
    return connection


def _create_installation_token(settings: Settings, *, installation_id: str) -> str:
    app_jwt = _build_app_jwt(settings)
    response = httpx.post(
        f"https://api.github.com/app/installations/{installation_id}/access_tokens",
        headers=_github_headers(app_jwt, is_jwt=True),
        timeout=15.0,
    )
    response.raise_for_status()
    payload = response.json()
    token = payload.get("token")
    if not isinstance(token, str) or not token:
        raise GitHubIntegrationError("GitHub installation token was not returned.")
    return token


def list_accessible_repositories(
    session: Session,
    *,
    user: User,
    settings: Settings,
) -> list[GitHubRepository]:
    connection = _get_owned_connection(session, user=user)
    token = _create_installation_token(settings, installation_id=connection.installation_id)
    response = httpx.get(
        "https://api.github.com/installation/repositories",
        headers=_github_headers(token),
        timeout=15.0,
    )
    response.raise_for_status()
    payload = response.json()
    items = payload.get("repositories", [])
    repositories: list[GitHubRepository] = []
    for item in items:
        repositories.append(
            GitHubRepository(
                id=int(item["id"]),
                name=str(item["name"]),
                full_name=str(item["full_name"]),
                default_branch=str(item.get("default_branch") or "main"),
                private=bool(item.get("private", True)),
            )
        )
    return repositories


def export_workspace_item_to_github(
    session: Session,
    *,
    user: User,
    settings: Settings,
    team_id: UUID,
    item_id: UUID,
    repository_full_name: str,
    path: str,
    branch: str | None,
    commit_message: str,
) -> GitHubExportResult:
    team = session.exec(
        select(AgentTeam).where(AgentTeam.id == team_id).where(AgentTeam.user_id == user.id)
    ).first()
    if team is None:
        raise TeamServiceError("Team not found.")

    item = session.exec(
        select(SharedWorkspaceItem)
        .where(SharedWorkspaceItem.id == item_id)
        .where(SharedWorkspaceItem.team_id == team.id)
    ).first()
    if item is None:
        raise GitHubIntegrationError("Workspace item not found.")
    if not item.content_text:
        raise GitHubIntegrationError("Workspace item does not contain exportable text content.")

    repositories = list_accessible_repositories(session, user=user, settings=settings)
    repositories_by_name = {repository.full_name: repository for repository in repositories}
    repository = repositories_by_name.get(repository_full_name)
    if repository is None:
        raise GitHubIntegrationError("Requested repository is not available to this installation.")

    token = _create_installation_token(settings, installation_id=_get_owned_connection(session, user=user).installation_id)
    target_branch = branch or repository.default_branch
    normalized_path = path.strip().strip("/")
    if not normalized_path:
        raise GitHubIntegrationError("A destination path is required.")

    existing_sha = None
    existing_response = httpx.get(
        f"https://api.github.com/repos/{repository_full_name}/contents/{normalized_path}",
        headers=_github_headers(token),
        params={"ref": target_branch},
        timeout=15.0,
    )
    if existing_response.status_code == 200:
        existing_sha = existing_response.json().get("sha")
    elif existing_response.status_code != 404:
        existing_response.raise_for_status()

    content = base64.b64encode(item.content_text.encode("utf-8")).decode("ascii")
    body: dict[str, Any] = {
        "message": commit_message,
        "content": content,
        "branch": target_branch,
    }
    if existing_sha:
        body["sha"] = existing_sha

    response = httpx.put(
        f"https://api.github.com/repos/{repository_full_name}/contents/{normalized_path}",
        headers=_github_headers(token),
        json=body,
        timeout=20.0,
    )
    response.raise_for_status()
    payload = response.json()
    commit_sha = payload.get("commit", {}).get("sha")
    if not isinstance(commit_sha, str) or not commit_sha:
        raise GitHubIntegrationError("GitHub did not return a commit SHA.")
    content_url = (
        payload.get("content", {}).get("html_url")
        if isinstance(payload.get("content"), dict)
        else None
    )
    if not isinstance(content_url, str) or not content_url:
        content_url = f"https://github.com/{repository_full_name}/blob/{target_branch}/{normalized_path}"
    commit_url = f"https://github.com/{repository_full_name}/commit/{commit_sha}"

    artifact = Artifact(
        team_id=team.id,
        conversation_id=item.conversation_id,
        agent_id=item.agent_id,
        name=normalized_path.split("/")[-1],
        kind="github_export",
        uri=f"github://{repository_full_name}/{normalized_path}",
        preview_uri=content_url,
        github_repo=repository_full_name,
        github_branch=target_branch,
        github_sha=commit_sha,
    )
    session.add(artifact)
    session.commit()
    session.refresh(artifact)

    return GitHubExportResult(
        artifact=artifact,
        item=item,
        repository_full_name=repository_full_name,
        branch=target_branch,
        commit_sha=commit_sha,
        content_url=content_url,
        commit_url=commit_url,
    )
