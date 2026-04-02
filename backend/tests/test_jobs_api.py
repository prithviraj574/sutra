from __future__ import annotations

from dataclasses import dataclass
from tempfile import NamedTemporaryFile
from uuid import UUID

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, select

from sutra_backend.auth import dependencies as auth_dependencies
from sutra_backend.config import Settings
from sutra_backend.db import create_database_engine, get_session
from sutra_backend.main import create_app
from sutra_backend.models import Agent, AgentTeam, AutomationJob
from sutra_backend.runtime.client import HermesResponse


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


def test_jobs_api_can_create_list_update_and_run_agent_job(monkeypatch) -> None:
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
    team = session.exec(select(AgentTeam).where(AgentTeam.mode == "personal")).one()

    async def fake_create_response(self, request, *, request_env=None):
        return HermesResponse(
            response_id="job-response-1",
            output_text="Automation job output",
            raw_response={"id": "job-response-1", "output": []},
        )

    monkeypatch.setattr(
        "sutra_backend.services.runtime.HermesRuntimeClient.create_response",
        fake_create_response,
    )

    create_response = client.post(
        "/api/jobs",
        headers={"Authorization": "Bearer valid-token"},
        json={
            "name": "Daily Agent Check-in",
            "schedule": "0 9 * * *",
            "prompt": "Summarize what changed since yesterday.",
            "agent_id": str(agent.id),
            "agent_team_id": str(team.id),
        },
    )
    assert create_response.status_code == 201
    job_id = create_response.json()["job"]["id"]
    assert create_response.json()["job"]["agent_team_id"] == str(team.id)

    list_response = client.get(
        f"/api/jobs?agent_id={agent.id}&agent_team_id={team.id}",
        headers={"Authorization": "Bearer valid-token"},
    )
    assert list_response.status_code == 200
    assert len(list_response.json()["items"]) == 1
    assert list_response.json()["items"][0]["name"] == "Daily Agent Check-in"

    update_response = client.patch(
        f"/api/jobs/{job_id}",
        headers={"Authorization": "Bearer valid-token"},
        json={"enabled": False, "schedule": "0 10 * * *"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["job"]["enabled"] is False
    assert update_response.json()["job"]["schedule"] == "0 10 * * *"

    disabled_run_response = client.post(
        f"/api/jobs/{job_id}/run",
        headers={"Authorization": "Bearer valid-token"},
    )
    assert disabled_run_response.status_code == 400
    assert disabled_run_response.json()["detail"] == "Automation job is disabled."

    enable_response = client.patch(
        f"/api/jobs/{job_id}",
        headers={"Authorization": "Bearer valid-token"},
        json={"enabled": True},
    )
    assert enable_response.status_code == 200

    run_response = client.post(
        f"/api/jobs/{job_id}/run",
        headers={"Authorization": "Bearer valid-token"},
    )
    assert run_response.status_code == 200
    payload = run_response.json()
    assert payload["output_text"] == "Automation job output"
    assert payload["conversation_id"] is not None
    assert payload["workspace_item_id"] is not None
    assert payload["job"]["last_run_at"] is not None

    persisted_job = session.get(AutomationJob, UUID(job_id))
    assert persisted_job is not None
    assert persisted_job.last_run_at is not None
    assert persisted_job.agent_team_id == team.id


def test_jobs_api_rejects_team_scoped_job_for_non_member_agent(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        runtime_provider="static_dev",
        dev_runtime_base_url="http://runtime.internal",
        dev_runtime_api_key="runtime-key",
    )
    client, session = build_client(settings)
    authenticate_default_user(client, monkeypatch)
    owned_agent = session.exec(select(Agent)).one()
    foreign_team = AgentTeam(user_id=owned_agent.user_id, name="Focused Crew", mode="team")
    session.add(foreign_team)
    session.commit()
    session.refresh(foreign_team)

    response = client.post(
        "/api/jobs",
        headers={"Authorization": "Bearer valid-token"},
        json={
            "name": "Out-of-band review",
            "schedule": "0 9 * * 1",
            "prompt": "Check in with the team.",
            "agent_id": str(owned_agent.id),
            "agent_team_id": str(foreign_team.id),
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Automation job agent must belong to the selected team."
