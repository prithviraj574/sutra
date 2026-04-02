from __future__ import annotations

from dataclasses import dataclass
from tempfile import NamedTemporaryFile
from uuid import UUID

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, select

from sutra_backend.auth import dependencies as auth_dependencies
from sutra_backend.db import create_database_engine, get_session
from sutra_backend.main import create_app
from sutra_backend.config import Settings
from sutra_backend.models import Agent, AgentTeam, AgentTeamAssignment, RoleTemplate, RuntimeLease, User


@dataclass(frozen=True)
class FakeIdentity:
    uid: str
    email: str
    name: str | None = None
    picture: str | None = None


def build_client(settings: Settings | None = None) -> tuple[TestClient, Session]:
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


def test_auth_me_requires_bearer_token() -> None:
    client, _ = build_client()

    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required."


def test_auth_me_bootstraps_user_from_verified_firebase_identity(monkeypatch) -> None:
    client, session = build_client()

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

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["user"]["firebase_uid"] == "firebase-user-1"
    assert payload["user"]["email"] == "user@example.com"

    persisted_user = session.exec(select(User).where(User.firebase_uid == "firebase-user-1")).one()
    persisted_team = session.exec(select(AgentTeam).where(AgentTeam.user_id == persisted_user.id)).one()
    persisted_agent = session.exec(
        select(Agent)
        .join(AgentTeamAssignment, AgentTeamAssignment.agent_id == Agent.id)
        .where(Agent.user_id == persisted_user.id)
        .where(AgentTeamAssignment.agent_team_id == persisted_team.id)
    ).one()
    role_templates = session.exec(select(RoleTemplate)).all()

    assert persisted_user.display_name == "Sutra User"
    assert persisted_team.mode == "personal"
    assert persisted_agent.role_name == "Generalist"
    assert {template.key for template in role_templates} >= {
        "builder",
        "generalist",
        "planner",
        "researcher",
    }


def test_auth_me_does_not_duplicate_bootstrap_records(monkeypatch) -> None:
    client, session = build_client()

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

    first_response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer valid-token"},
    )
    second_response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert len(session.exec(select(User)).all()) == 1
    assert len(session.exec(select(AgentTeam)).all()) == 1
    assert len(session.exec(select(Agent)).all()) == 1


def test_auth_me_bootstraps_default_agent_runtime_when_configured(monkeypatch) -> None:
    client, session = build_client(
        Settings(
            app_env="test",
            database_url="sqlite://",
            runtime_provider="static_dev",
            dev_runtime_base_url="http://runtime.internal",
            dev_runtime_api_key="runtime-key",
        )
    )

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

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 200
    agent = session.exec(select(Agent)).one()
    lease = session.exec(select(RuntimeLease).where(RuntimeLease.agent_id == agent.id)).one()
    assert agent.status == "ready"
    assert lease.api_base_url == "http://runtime.internal"


def test_auth_me_supports_local_dev_auth_bypass() -> None:
    client, session = build_client(
        Settings(
            app_env="development",
            database_url="sqlite://",
            dev_auth_bypass_enabled=True,
        )
    )

    response = client.get("/api/auth/me")

    assert response.status_code == 200
    payload = response.json()
    assert payload["user"]["id"] == "00000000-0000-0000-0000-000000000000"
    assert payload["user"]["firebase_uid"] == "00000000-0000-0000-0000-000000000000"
    assert payload["user"]["email"] == "local-dev@sutra.local"

    persisted_user = session.get(User, UUID("00000000-0000-0000-0000-000000000000"))
    assert persisted_user is not None
    assert session.exec(select(AgentTeam).where(AgentTeam.user_id == persisted_user.id)).one()
    assert session.exec(select(Agent)).one()
