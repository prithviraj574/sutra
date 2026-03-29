from __future__ import annotations

from dataclasses import dataclass
from tempfile import NamedTemporaryFile

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, select

from sutra_backend.auth import dependencies as auth_dependencies
from sutra_backend.config import Settings
from sutra_backend.db import create_database_engine, get_session
from sutra_backend.main import create_app
from sutra_backend.models import Secret


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


def test_secret_vault_encrypts_at_rest_and_hides_plaintext(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        master_encryption_key="6ef00a2158f3e62cb140cd506725497433c5debc49172fcd54b108a995dcb6ca",
    )
    client, session = build_client(settings)
    authenticate_default_user(client, monkeypatch)

    create_response = client.post(
        "/api/secrets",
        headers={"Authorization": "Bearer valid-token"},
        json={
            "name": "GITHUB_TOKEN",
            "value": "ghp_super_secret",
            "provider": "github",
            "scope": "user",
        },
    )

    assert create_response.status_code == 201
    payload = create_response.json()
    assert payload["secret"]["name"] == "GITHUB_TOKEN"
    assert "value" not in payload["secret"]

    persisted_secret = session.exec(select(Secret)).one()
    assert persisted_secret.encrypted_value != "ghp_super_secret"
    assert "ghp_super_secret" not in persisted_secret.encrypted_value

    list_response = client.get(
        "/api/secrets",
        headers={"Authorization": "Bearer valid-token"},
    )
    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["name"] == "GITHUB_TOKEN"


def test_secret_delete_removes_owned_secret(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        master_encryption_key="6ef00a2158f3e62cb140cd506725497433c5debc49172fcd54b108a995dcb6ca",
    )
    client, session = build_client(settings)
    authenticate_default_user(client, monkeypatch)

    create_response = client.post(
        "/api/secrets",
        headers={"Authorization": "Bearer valid-token"},
        json={
            "name": "FIRECRAWL_API_KEY",
            "value": "fc_secret_value",
            "provider": "firecrawl",
            "scope": "user",
        },
    )
    secret_id = create_response.json()["secret"]["id"]

    delete_response = client.delete(
        f"/api/secrets/{secret_id}",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert delete_response.status_code == 200
    assert session.exec(select(Secret)).all() == []
