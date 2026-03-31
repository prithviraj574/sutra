from __future__ import annotations

from dataclasses import dataclass
from tempfile import NamedTemporaryFile
from uuid import UUID

import httpx
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, select

from sutra_backend.auth import dependencies as auth_dependencies
from sutra_backend.config import Settings
from sutra_backend.db import create_database_engine, get_session
from sutra_backend.main import create_app
from sutra_backend.models import GitHubConnection, SharedWorkspaceItem, Team, User


@dataclass(frozen=True)
class FakeIdentity:
    uid: str
    email: str
    name: str | None = None
    picture: str | None = None


class MockResponse:
    def __init__(self, payload: dict[str, object], *, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.request = httpx.Request("GET", "https://github.test")

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "GitHub mock request failed.",
                request=self.request,
                response=httpx.Response(self.status_code, request=self.request),
            )

    def json(self) -> dict[str, object]:
        return self._payload


def build_client() -> tuple[TestClient, Session]:
    database_file = NamedTemporaryFile(suffix=".db")
    engine = create_database_engine(f"sqlite:///{database_file.name}")
    SQLModel.metadata.create_all(engine)
    session = Session(engine)

    settings = Settings(
        database_url=f"sqlite:///{database_file.name}",
        github_app_id="12345",
        github_app_private_key="test-private-key",
    )
    app = create_app(settings=settings)

    def override_get_session() -> Session:
        return session

    app.dependency_overrides[get_session] = override_get_session
    app.state._database_file = database_file
    return TestClient(app), session


def authenticate(client: TestClient, monkeypatch) -> User:
    monkeypatch.setattr(
        auth_dependencies,
        "verify_firebase_token",
        lambda _: FakeIdentity(uid="firebase-user-1", email="user@example.com"),
    )
    response = client.get("/api/auth/me", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 200
    return response.json()["user"]


def test_github_repository_listing_and_workspace_export(monkeypatch) -> None:
    client, session = build_client()
    user_payload = authenticate(client, monkeypatch)
    user = session.exec(select(User).where(User.id == UUID(user_payload["id"]))).one()

    team = Team(user_id=user.id, name="Launch Crew", mode="team", shared_workspace_uri="workspace://teams/team-1")
    session.add(team)
    session.commit()
    session.refresh(team)
    item = SharedWorkspaceItem(
        team_id=team.id,
        path="briefs/launch-plan.md",
        content_text="# Launch Plan\n",
        size_bytes=14,
    )
    connection = GitHubConnection(
        user_id=user.id,
        installation_id="1001",
        account_login="octocat",
        account_type="user",
    )
    session.add(item)
    session.add(connection)
    session.commit()
    session.refresh(item)

    def fake_post(url: str, *, headers: dict[str, str], timeout: float):
        assert url.endswith("/app/installations/1001/access_tokens")
        return MockResponse({"token": "installation-token"})

    def fake_get(url: str, *, headers: dict[str, str], timeout: float, params: dict[str, str] | None = None):
        if url.endswith("/installation/repositories"):
            return MockResponse(
                {
                    "repositories": [
                        {
                            "id": 1,
                            "name": "launch-repo",
                            "full_name": "octocat/launch-repo",
                            "default_branch": "main",
                            "private": True,
                        }
                    ]
                }
            )
        if url.endswith("/repos/octocat/launch-repo/contents/app/launch-plan.md"):
            return MockResponse({}, status_code=404)
        raise AssertionError(f"Unexpected GET url {url}")

    def fake_put(url: str, *, headers: dict[str, str], json: dict[str, object], timeout: float):
        assert url.endswith("/repos/octocat/launch-repo/contents/app/launch-plan.md")
        assert json["branch"] == "main"
        assert json["message"] == "Export launch plan"
        return MockResponse({"commit": {"sha": "commit-sha-123"}})

    monkeypatch.setattr("sutra_backend.services.github_integration.httpx.post", fake_post)
    monkeypatch.setattr("sutra_backend.services.github_integration.httpx.get", fake_get)
    monkeypatch.setattr("sutra_backend.services.github_integration.httpx.put", fake_put)
    monkeypatch.setattr(
        "sutra_backend.services.github_integration._build_app_jwt",
        lambda settings: "app-jwt",
    )

    repos_response = client.get(
        "/api/github/repositories",
        headers={"Authorization": "Bearer valid-token"},
    )
    export_response = client.post(
        f"/api/github/teams/{team.id}/workspace/items/{item.id}/export",
        headers={"Authorization": "Bearer valid-token"},
        json={
            "repository_full_name": "octocat/launch-repo",
            "path": "app/launch-plan.md",
            "commit_message": "Export launch plan",
        },
    )

    assert repos_response.status_code == 200
    assert repos_response.json()["items"][0]["full_name"] == "octocat/launch-repo"
    assert export_response.status_code == 200
    assert export_response.json()["repository_full_name"] == "octocat/launch-repo"
    assert export_response.json()["commit_sha"] == "commit-sha-123"
    assert export_response.json()["content_url"] == "https://github.com/octocat/launch-repo/blob/main/app/launch-plan.md"
    assert export_response.json()["commit_url"] == "https://github.com/octocat/launch-repo/commit/commit-sha-123"
    assert export_response.json()["artifact"]["preview_uri"] == "https://github.com/octocat/launch-repo/blob/main/app/launch-plan.md"

    artifacts_response = client.get(
        f"/api/teams/{team.id}/artifacts",
        headers={"Authorization": "Bearer valid-token"},
    )
    assert artifacts_response.status_code == 200
    assert artifacts_response.json()["items"][0]["github_sha"] == "commit-sha-123"
