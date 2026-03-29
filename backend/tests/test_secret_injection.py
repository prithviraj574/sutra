from __future__ import annotations

from dataclasses import dataclass
from tempfile import NamedTemporaryFile

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, select

from sutra_backend.auth import dependencies as auth_dependencies
from sutra_backend.config import Settings
from sutra_backend.db import create_database_engine, get_session
from sutra_backend.main import create_app
from sutra_backend.models import Agent
from sutra_backend.runtime.client import HermesResponse
from sutra_backend.services import runtime as runtime_service


@dataclass(frozen=True)
class FakeIdentity:
    uid: str
    email: str
    name: str | None = None
    picture: str | None = None


def build_client(settings: Settings) -> tuple[TestClient, Session]:
    database_file = NamedTemporaryFile(suffix=".db")
    engine = create_database_engine(f"sqlite:///{database_file.name}")
    SQLModel.metadata.create_all(engine)
    session = Session(engine)

    app = create_app(settings)

    def override_get_session() -> Session:
        return session

    app.dependency_overrides[get_session] = override_get_session
    app.state._database_file = database_file
    return TestClient(app), session


def authenticate_default_user(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(
        auth_dependencies,
        "verify_firebase_token",
        lambda _: FakeIdentity(
            uid="firebase-user-1",
            email="user@example.com",
            name="Sutra User",
            picture="https://example.com/avatar.png",
        ),
    )

    response = client.get("/api/auth/me", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 200


def test_agent_response_can_inject_owned_secret_as_transient_runtime_env(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        runtime_provider="static_dev",
        dev_runtime_base_url="http://runtime.internal",
        dev_runtime_api_key="runtime-key",
        master_encryption_key="6ef00a2158f3e62cb140cd506725497433c5debc49172fcd54b108a995dcb6ca",
    )
    client, session = build_client(settings)
    authenticate_default_user(client, monkeypatch)
    agent = session.exec(select(Agent)).one()

    secret_response = client.post(
        "/api/secrets",
        headers={"Authorization": "Bearer valid-token"},
        json={
            "name": "GITHUB_TOKEN",
            "value": "ghp_super_secret",
            "provider": "github",
            "scope": "user",
        },
    )
    secret_id = secret_response.json()["secret"]["id"]
    captured_request_env: list[dict[str, str] | None] = []

    async def fake_create_response(self, request, *, request_env=None):
        captured_request_env.append(request_env)
        return HermesResponse(
            response_id="resp_123",
            output_text="Secret-backed run complete.",
            raw_response={"id": "resp_123", "output": []},
        )

    monkeypatch.setattr(runtime_service.HermesRuntimeClient, "create_response", fake_create_response)

    response = client.post(
        f"/api/agents/{agent.id}/responses",
        headers={"Authorization": "Bearer valid-token"},
        json={
            "input": "Open the repo and prepare a commit.",
            "secret_ids": [secret_id],
        },
    )

    assert response.status_code == 200
    assert captured_request_env == [{"GITHUB_TOKEN": "ghp_super_secret"}]
