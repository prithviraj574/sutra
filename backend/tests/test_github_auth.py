from __future__ import annotations

from dataclasses import dataclass
from tempfile import NamedTemporaryFile
from urllib.parse import parse_qs, urlparse
from uuid import UUID

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, select

from sutra_backend.api import github as github_api
from sutra_backend.auth import dependencies as auth_dependencies
from sutra_backend.config import Settings
from sutra_backend.db import create_database_engine, get_session
from sutra_backend.main import create_app
from sutra_backend.models import GitHubConnection, User


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
        github_client_id="github-client-id",
        github_client_secret="github-client-secret",
    )
    app = create_app(settings=settings)

    def override_get_session() -> Session:
        return session

    app.dependency_overrides[get_session] = override_get_session
    app.state._database_file = database_file
    return TestClient(app), session


def test_github_auth_redirects_to_github_authorize_url(monkeypatch: pytest.MonkeyPatch) -> None:
    client, session = build_client()

    monkeypatch.setattr(
        auth_dependencies,
        "verify_firebase_token",
        lambda _: FakeIdentity(uid="firebase-user-1", email="user@example.com"),
    )

    response = client.get(
        "/api/auth/github",
        headers={"Authorization": "Bearer valid-token"},
        follow_redirects=False,
    )

    assert response.status_code == 302

    location = response.headers["location"]
    parsed = urlparse(location)
    params = parse_qs(parsed.query)

    user = session.exec(select(User).where(User.firebase_uid == "firebase-user-1")).one()

    assert parsed.scheme == "https"
    assert parsed.netloc == "github.com"
    assert parsed.path == "/login/oauth/authorize"
    assert params["client_id"] == ["github-client-id"]
    assert params["redirect_uri"] == ["http://testserver/api/auth/github/callback"]
    assert params["allow_signup"] == ["false"]
    state_payload = github_api._decode_state(
        state=params["state"][0],
        settings=Settings(
            database_url="sqlite://",
            github_client_id="github-client-id",
            github_client_secret="github-client-secret",
        ),
    )
    assert UUID(str(state_payload["user_id"])) == user.id
    assert response.cookies.get(github_api.GITHUB_OAUTH_STATE_COOKIE) == state_payload["nonce"]


def test_github_callback_exchanges_code_and_upserts_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    client, session = build_client()

    user = User(firebase_uid="firebase-user-1", email="user@example.com")
    session.add(user)
    session.commit()
    session.refresh(user)

    settings = Settings(
        database_url="sqlite://",
        github_client_id="github-client-id",
        github_client_secret="github-client-secret",
        frontend_url="http://localhost:5173",
    )
    state = github_api._encode_state(user_id=user.id, nonce="oauth-nonce", settings=settings)
    token_values = iter(["access-token-1", "access-token-2"])
    github_users = iter(
        [
            {"login": "octocat", "type": "User"},
            {"login": "octocat-renamed", "type": "User"},
        ]
    )
    installations = iter(
        [
            {"id": 1001, "account": {"login": "octocat", "type": "User"}},
            {"id": 2002, "account": {"login": "octocat-renamed", "type": "Organization"}},
        ]
    )

    def fake_post(url: str, *, headers: dict[str, str], data: dict[str, str], timeout: float) -> MockResponse:
        assert url == github_api.GITHUB_ACCESS_TOKEN_URL
        assert headers["Accept"] == "application/json"
        assert data["client_id"] == "github-client-id"
        assert data["client_secret"] == "github-client-secret"
        assert data["redirect_uri"] == "http://testserver/api/auth/github/callback"
        assert data["state"] == state
        return MockResponse({"access_token": next(token_values)})

    def fake_get(url: str, *, headers: dict[str, str], timeout: float) -> MockResponse:
        assert headers["Authorization"].startswith("Bearer access-token-")
        assert headers["Accept"] == "application/vnd.github+json"

        if url == github_api.GITHUB_USER_URL:
            return MockResponse(next(github_users))
        if url == github_api.GITHUB_USER_INSTALLATIONS_URL:
            return MockResponse({"installations": [next(installations)]})
        raise AssertionError(f"Unexpected GitHub URL: {url}")

    monkeypatch.setattr(github_api.httpx, "post", fake_post)
    monkeypatch.setattr(github_api.httpx, "get", fake_get)

    client.cookies.set(github_api.GITHUB_OAUTH_STATE_COOKIE, "oauth-nonce", path="/api/auth/github")
    first_response = client.get(
        "/api/auth/github/callback",
        params={"code": "oauth-code-1", "state": state},
        follow_redirects=False,
    )
    client.cookies.set(github_api.GITHUB_OAUTH_STATE_COOKIE, "oauth-nonce", path="/api/auth/github")
    second_response = client.get(
        "/api/auth/github/callback",
        params={"code": "oauth-code-2", "state": state},
        follow_redirects=False,
    )

    assert first_response.status_code == 302
    assert second_response.status_code == 302
    assert first_response.headers["location"] == "http://localhost:5173/?github=connected"
    assert second_response.headers["location"] == "http://localhost:5173/?github=connected"

    connections = session.exec(select(GitHubConnection)).all()
    assert len(connections) == 1
    assert connections[0].user_id == user.id
    assert connections[0].installation_id == "2002"
    assert connections[0].account_login == "octocat-renamed"
    assert connections[0].account_type == "organization"


def test_github_callback_rejects_missing_oauth_cookie(monkeypatch: pytest.MonkeyPatch) -> None:
    client, session = build_client()

    user = User(firebase_uid="firebase-user-1", email="user@example.com")
    session.add(user)
    session.commit()
    session.refresh(user)

    settings = Settings(
        database_url="sqlite://",
        github_client_id="github-client-id",
        github_client_secret="github-client-secret",
    )
    state = github_api._encode_state(user_id=user.id, nonce="expected-nonce", settings=settings)

    response = client.get(
        "/api/auth/github/callback",
        params={"code": "oauth-code-1", "state": state},
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "GitHub OAuth state mismatch."


def test_github_connection_status_returns_active_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    client, session = build_client()

    user = User(firebase_uid="firebase-user-1", email="user@example.com")
    session.add(user)
    session.commit()
    session.refresh(user)

    connection = GitHubConnection(
        user_id=user.id,
        installation_id="1001",
        account_login="octocat",
        account_type="user",
    )
    session.add(connection)
    session.commit()

    monkeypatch.setattr(
        auth_dependencies,
        "verify_firebase_token",
        lambda _: FakeIdentity(uid="firebase-user-1", email="user@example.com"),
    )

    response = client.get(
        "/api/auth/github/connection",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 200
    assert response.json()["connection"]["installation_id"] == "1001"
    assert response.json()["connection"]["account_login"] == "octocat"


def test_github_connection_status_returns_null_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    client, _session = build_client()

    monkeypatch.setattr(
        auth_dependencies,
        "verify_firebase_token",
        lambda _: FakeIdentity(uid="firebase-user-1", email="user@example.com"),
    )

    response = client.get(
        "/api/auth/github/connection",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 200
    assert response.json() == {"connection": None}
