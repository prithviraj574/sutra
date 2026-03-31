from __future__ import annotations

from dataclasses import dataclass
from tempfile import NamedTemporaryFile

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel

from sutra_backend.auth import dependencies as auth_dependencies
from sutra_backend.config import Settings
from sutra_backend.db import create_database_engine, get_session
from sutra_backend.main import create_app


@dataclass(frozen=True)
class FakeIdentity:
    uid: str
    email: str
    name: str | None = None
    picture: str | None = None


def build_client(settings: Settings) -> TestClient:
    database_file = NamedTemporaryFile(suffix=".db")
    engine = create_database_engine(f"sqlite:///{database_file.name}")
    SQLModel.metadata.create_all(engine)
    session = Session(engine)

    app = create_app(settings)

    def override_get_session() -> Session:
        return session

    app.dependency_overrides[get_session] = override_get_session
    app.state._database_file = database_file
    return TestClient(app)


def test_catalog_routes_return_bootstrapped_team_and_agent(monkeypatch) -> None:
    client = build_client(
        Settings(
            app_env="test",
            database_url="sqlite://",
        )
    )

    monkeypatch.setattr(
        auth_dependencies,
        "verify_firebase_token",
        lambda _: FakeIdentity(
            uid="firebase-user-1",
            email="user@example.com",
            name="Sutra User",
        ),
    )

    teams_response = client.get("/api/teams", headers={"Authorization": "Bearer valid-token"})
    agents_response = client.get("/api/agents", headers={"Authorization": "Bearer valid-token"})

    assert teams_response.status_code == 200
    assert agents_response.status_code == 200

    teams = teams_response.json()["items"]
    agents = agents_response.json()["items"]

    assert len(teams) == 1
    assert teams[0]["mode"] == "personal"
    assert len(agents) == 1
    assert agents[0]["role_name"] == "Generalist"


def test_role_templates_route_returns_seeded_templates(monkeypatch) -> None:
    client = build_client(
        Settings(
            app_env="test",
            database_url="sqlite://",
        )
    )

    monkeypatch.setattr(
        auth_dependencies,
        "verify_firebase_token",
        lambda _: FakeIdentity(uid="firebase-user-1", email="user@example.com"),
    )

    response = client.get("/api/role-templates", headers={"Authorization": "Bearer valid-token"})

    assert response.status_code == 200
    keys = [item["key"] for item in response.json()["items"]]
    assert keys == ["builder", "generalist", "planner", "researcher"]


def test_team_creation_route_creates_distinct_role_agents_and_workspace(monkeypatch) -> None:
    client = build_client(
        Settings(
            app_env="test",
            database_url="sqlite://",
        )
    )

    monkeypatch.setattr(
        auth_dependencies,
        "verify_firebase_token",
        lambda _: FakeIdentity(
            uid="firebase-user-1",
            email="user@example.com",
            name="Sutra User",
        ),
    )

    create_response = client.post(
        "/api/teams",
        headers={"Authorization": "Bearer valid-token"},
        json={
            "name": "Launch Crew",
            "description": "Cross-functional product team.",
            "agents": [
                {"role_template_key": "planner"},
                {"role_template_key": "researcher"},
                {"role_template_key": "builder"},
            ],
        },
    )

    assert create_response.status_code == 201
    payload = create_response.json()
    assert payload["team"]["mode"] == "team"
    assert payload["team"]["shared_workspace_uri"].startswith("workspace://teams/")
    assert [agent["role_name"] for agent in payload["agents"]] == [
        "Planner",
        "Researcher",
        "Builder",
    ]

    workspace_response = client.get(
        f"/api/teams/{payload['team']['id']}/workspace",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert workspace_response.status_code == 200
    workspace_payload = workspace_response.json()
    assert workspace_payload["team"]["id"] == payload["team"]["id"]
    assert [item["path"] for item in workspace_payload["items"]] == [
        "artifacts",
        "research",
        "README.md",
    ]


def test_team_creation_rejects_duplicate_role_templates(monkeypatch) -> None:
    client = build_client(
        Settings(
            app_env="test",
            database_url="sqlite://",
        )
    )

    monkeypatch.setattr(
        auth_dependencies,
        "verify_firebase_token",
        lambda _: FakeIdentity(uid="firebase-user-1", email="user@example.com"),
    )

    response = client.post(
        "/api/teams",
        headers={"Authorization": "Bearer valid-token"},
        json={
            "name": "Duplicate Crew",
            "agents": [
                {"role_template_key": "planner"},
                {"role_template_key": "planner"},
            ],
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Each team role must be distinct."
