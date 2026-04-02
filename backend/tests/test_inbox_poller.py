from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from tempfile import NamedTemporaryFile
from uuid import UUID

import pytest
from sqlmodel import Session, SQLModel, select

from sutra_backend.auth import dependencies as auth_dependencies
from sutra_backend.config import Settings
from sutra_backend.db import create_database_engine
from sutra_backend.main import create_app
from sutra_backend.models import AgentTeam, PollerLease, TeamTask, utcnow
from sutra_backend.services import team_runtime as team_runtime_service
from sutra_backend.services.inbox_poller import read_inbox_poller_status, run_inbox_poller_sweep
from sutra_backend.runtime.client import HermesResponse
from fastapi.testclient import TestClient
from sutra_backend.db import get_session


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


def authenticate(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(
        auth_dependencies,
        "verify_firebase_token",
        lambda _: FakeIdentity(uid="firebase-user-1", email="user@example.com"),
    )
    response = client.get("/api/auth/me", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 200


@pytest.mark.anyio
async def test_inbox_poller_sweep_runs_pending_team_tasks(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        runtime_provider="static_dev",
        dev_runtime_base_url="http://runtime.internal",
        dev_runtime_api_key="runtime-key",
        inbox_poller_enabled=True,
        inbox_poller_max_tasks_per_sweep=4,
    )
    client, session = build_client(settings)
    authenticate(client, monkeypatch)

    create_team_response = client.post(
        "/api/teams",
        headers={"Authorization": "Bearer valid-token"},
        json={
            "name": "Launch Crew",
            "agents": [
                {"role_template_key": "planner"},
                {"role_template_key": "researcher"},
            ],
        },
    )
    assert create_team_response.status_code == 201
    team_id = create_team_response.json()["team"]["id"]

    response_ids = iter(["huddle_planner", "huddle_researcher", "poller_planner", "poller_researcher"])

    async def fake_create_response(self, request, *, request_env=None):
        response_id = next(response_ids)
        if response_id == "huddle_planner":
            return HermesResponse(
                response_id=response_id,
                output_text="Define the launch milestones and final brief outline.",
                raw_response={"id": response_id, "output": []},
            )
        if response_id == "huddle_researcher":
            return HermesResponse(
                response_id=response_id,
                output_text="Research competitors and collect user pain points for the brief.",
                raw_response={"id": response_id, "output": []},
            )
        if response_id == "poller_planner":
            return HermesResponse(
                response_id=response_id,
                output_text="Planner completed the task during the poller sweep.",
                raw_response={"id": response_id, "output": []},
            )
        return HermesResponse(
            response_id=response_id,
            output_text="Researcher completed the task during the poller sweep.",
            raw_response={"id": response_id, "output": []},
        )

    monkeypatch.setattr(
        team_runtime_service.HermesRuntimeClient,
        "create_response",
        fake_create_response,
    )

    huddle_response = client.post(
        f"/api/teams/{team_id}/huddles",
        headers={"Authorization": "Bearer valid-token"},
        json={"input": "Prepare a product launch brief."},
    )
    assert huddle_response.status_code == 200

    executed_count = await run_inbox_poller_sweep(
        session=session,
        settings=settings,
        owner_id="test-owner",
    )
    assert executed_count == 2

    team = session.exec(select(AgentTeam).where(AgentTeam.id == UUID(team_id))).one()
    tasks = session.exec(select(TeamTask).where(TeamTask.team_id == team.id)).all()
    assert len(tasks) == 2
    assert all(task.status == "completed" for task in tasks)
    status = read_inbox_poller_status(session=session, settings=settings)
    assert status.lease is not None
    assert status.lease.owner_id == "test-owner"
    assert status.lease.last_executed_count == 2
    assert status.is_active is True


@pytest.mark.anyio
async def test_inbox_poller_sweep_skips_when_other_owner_holds_active_lease(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        runtime_provider="static_dev",
        dev_runtime_base_url="http://runtime.internal",
        dev_runtime_api_key="runtime-key",
        inbox_poller_enabled=True,
    )
    client, session = build_client(settings)
    authenticate(client, monkeypatch)

    create_team_response = client.post(
        "/api/teams",
        headers={"Authorization": "Bearer valid-token"},
        json={
            "name": "Launch Crew",
            "agents": [
                {"role_template_key": "planner"},
            ],
        },
    )
    assert create_team_response.status_code == 201
    team_id = create_team_response.json()["team"]["id"]

    async def fake_create_response(self, request, *, request_env=None):
        return HermesResponse(
            response_id="huddle_planner",
            output_text="Define the launch milestones and final brief outline.",
            raw_response={"id": "huddle_planner", "output": []},
        )

    monkeypatch.setattr(
        team_runtime_service.HermesRuntimeClient,
        "create_response",
        fake_create_response,
    )

    huddle_response = client.post(
        f"/api/teams/{team_id}/huddles",
        headers={"Authorization": "Bearer valid-token"},
        json={"input": "Prepare a product launch brief."},
    )
    assert huddle_response.status_code == 200

    session.add(
        PollerLease(
            name="inbox_poller",
            owner_id="other-owner",
            state="running",
            lease_expires_at=utcnow() + timedelta(minutes=5),
        )
    )
    session.commit()

    executed_count = await run_inbox_poller_sweep(
        session=session,
        settings=settings,
        owner_id="test-owner",
    )
    assert executed_count == 0

    tasks = session.exec(select(TeamTask)).all()
    assert len(tasks) == 1
    assert tasks[0].status == "open"


@pytest.mark.anyio
async def test_inbox_poller_sweep_respects_max_tasks_per_sweep(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        runtime_provider="static_dev",
        dev_runtime_base_url="http://runtime.internal",
        dev_runtime_api_key="runtime-key",
        inbox_poller_enabled=True,
        inbox_poller_max_tasks_per_sweep=1,
    )
    client, session = build_client(settings)
    authenticate(client, monkeypatch)

    create_team_response = client.post(
        "/api/teams",
        headers={"Authorization": "Bearer valid-token"},
        json={
            "name": "Launch Crew",
            "agents": [
                {"role_template_key": "planner"},
                {"role_template_key": "researcher"},
            ],
        },
    )
    assert create_team_response.status_code == 201
    team_id = create_team_response.json()["team"]["id"]

    response_ids = iter(["huddle_planner", "huddle_researcher", "poller_planner"])

    async def fake_create_response(self, request, *, request_env=None):
        response_id = next(response_ids)
        if response_id == "huddle_planner":
            return HermesResponse(
                response_id=response_id,
                output_text="Define the launch milestones and final brief outline.",
                raw_response={"id": response_id, "output": []},
            )
        if response_id == "huddle_researcher":
            return HermesResponse(
                response_id=response_id,
                output_text="Research competitors and collect user pain points for the brief.",
                raw_response={"id": response_id, "output": []},
            )
        return HermesResponse(
            response_id=response_id,
            output_text="Planner completed the task during the poller sweep.",
            raw_response={"id": response_id, "output": []},
        )

    monkeypatch.setattr(
        team_runtime_service.HermesRuntimeClient,
        "create_response",
        fake_create_response,
    )

    huddle_response = client.post(
        f"/api/teams/{team_id}/huddles",
        headers={"Authorization": "Bearer valid-token"},
        json={"input": "Prepare a product launch brief."},
    )
    assert huddle_response.status_code == 200

    executed_count = await run_inbox_poller_sweep(
        session=session,
        settings=settings,
        owner_id="limited-owner",
    )
    assert executed_count == 1

    team = session.exec(select(AgentTeam).where(AgentTeam.id == UUID(team_id))).one()
    tasks = session.exec(select(TeamTask).where(TeamTask.team_id == team.id)).all()
    completed = [task for task in tasks if task.status == "completed"]
    open_tasks = [task for task in tasks if task.status == "open"]
    assert len(completed) == 1
    assert len(open_tasks) == 1

    status = read_inbox_poller_status(session=session, settings=settings)
    assert status.lease is not None
    assert status.lease.last_executed_count == 1
