from __future__ import annotations

from datetime import timedelta
from tempfile import NamedTemporaryFile

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel

from sutra_backend.auth import dependencies as auth_dependencies
from sutra_backend.config import Settings
from sutra_backend.db import create_database_engine, get_session
from sutra_backend.main import create_app
from sutra_backend.models import PollerLease, utcnow


class FakeIdentity:
    def __init__(self, uid: str, email: str) -> None:
        self.uid = uid
        self.email = email
        self.name = None
        self.picture = None


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


def authenticate(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(
        auth_dependencies,
        "verify_firebase_token",
        lambda _: FakeIdentity(uid="firebase-user-1", email="user@example.com"),
    )
    response = client.get("/api/auth/me", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 200


def test_system_poller_status_reports_config_and_lease(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        inbox_poller_enabled=True,
        inbox_poller_interval_seconds=15,
        inbox_poller_lease_seconds=45,
        inbox_poller_max_tasks_per_sweep=3,
    )
    client, session = build_client(settings)
    authenticate(client, monkeypatch)

    lease = PollerLease(
        name="inbox_poller",
        owner_id="poller-owner",
        state="idle",
        last_heartbeat_at=utcnow(),
        lease_expires_at=utcnow() + timedelta(seconds=30),
        last_executed_count=2,
    )
    session.add(lease)
    session.commit()

    response = client.get(
        "/api/system/poller",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["enabled"] is True
    assert payload["interval_seconds"] == 15
    assert payload["lease_seconds"] == 45
    assert payload["max_tasks_per_sweep"] == 3
    assert payload["is_active"] is True
    assert payload["lease"]["owner_id"] == "poller-owner"
