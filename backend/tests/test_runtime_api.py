from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from tempfile import NamedTemporaryFile

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, select

from sutra_backend.auth import dependencies as auth_dependencies
from sutra_backend.config import Settings
from sutra_backend.db import create_database_engine, get_session
from sutra_backend.main import create_app
from sutra_backend.models import Agent, RuntimeLease, utcnow
from sutra_backend.runtime.client import RuntimeHealthProbe


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


def test_runtime_provision_route_creates_and_returns_agent_lease(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        runtime_provider="static_dev",
        dev_runtime_base_url="http://runtime.internal",
        dev_runtime_api_key="runtime-key",
    )
    client, session = build_client(settings)
    authenticate_default_user(client, monkeypatch)
    agent = session.exec(select(Agent)).one()

    provision_response = client.post(
        f"/api/agents/{agent.id}/runtime/provision",
        headers={"Authorization": "Bearer valid-token"},
    )
    lease_response = client.get(
        f"/api/agents/{agent.id}/runtime",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert provision_response.status_code == 200
    assert lease_response.status_code == 200
    assert provision_response.json()["lease"]["api_base_url"] == "http://runtime.internal"
    assert provision_response.json()["lease"]["ready"] is True
    assert provision_response.json()["lease"]["heartbeat_fresh"] is True
    assert lease_response.json()["lease"]["agent_id"] == str(agent.id)


def test_runtime_route_reports_non_ready_runtime_when_endpoint_missing(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        runtime_provider="static_dev",
        dev_runtime_base_url="http://runtime.internal",
        dev_runtime_api_key="runtime-key",
        runtime_heartbeat_stale_seconds=300,
    )
    client, session = build_client(settings)
    authenticate_default_user(client, monkeypatch)
    agent = session.exec(select(Agent)).one()

    provision_response = client.post(
        f"/api/agents/{agent.id}/runtime/provision",
        headers={"Authorization": "Bearer valid-token"},
    )
    assert provision_response.status_code == 200

    lease = session.exec(select(RuntimeLease).where(RuntimeLease.agent_id == agent.id)).one()
    lease.api_base_url = None
    session.add(lease)
    session.commit()

    response = client.get(
        f"/api/agents/{agent.id}/runtime",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 200
    payload = response.json()["lease"]
    assert payload["ready"] is False
    assert payload["readiness_reason"] == "Runtime does not have an internal API endpoint yet."


def test_runtime_route_reconciles_stale_runtime_health(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        runtime_provider="static_dev",
        dev_runtime_base_url="http://runtime.internal",
        dev_runtime_api_key="runtime-key",
        runtime_heartbeat_stale_seconds=1,
    )
    client, session = build_client(settings)
    authenticate_default_user(client, monkeypatch)
    agent = session.exec(select(Agent)).one()

    provision_response = client.post(
        f"/api/agents/{agent.id}/runtime/provision",
        headers={"Authorization": "Bearer valid-token"},
    )
    assert provision_response.status_code == 200

    lease = session.exec(select(RuntimeLease).where(RuntimeLease.agent_id == agent.id)).one()
    lease.last_heartbeat_at = utcnow() - timedelta(minutes=10)
    session.add(lease)
    session.commit()

    monkeypatch.setattr(
        "sutra_backend.services.runtime_leases.probe_runtime_health",
        lambda *args, **kwargs: RuntimeHealthProbe(
            reachable=False,
            status_code=None,
            checked_url="http://runtime.internal/health",
            detail="Runtime probe failed: connection refused.",
        ),
    )

    response = client.get(
        f"/api/agents/{agent.id}/runtime",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 200
    payload = response.json()["lease"]
    assert payload["ready"] is False
    assert payload["readiness_reason"] == "Runtime probe failed: connection refused."

    session.refresh(lease)
    assert lease.state == "unreachable"


def test_runtime_route_returns_404_when_lease_has_not_been_provisioned(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        runtime_provider="static_dev",
    )
    client, session = build_client(settings)
    authenticate_default_user(client, monkeypatch)
    agent = session.exec(select(Agent)).one()

    response = client.get(
        f"/api/agents/{agent.id}/runtime",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 404
