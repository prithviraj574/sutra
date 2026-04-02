from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from tempfile import NamedTemporaryFile
from uuid import UUID

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, select

from sutra_backend.auth import dependencies as auth_dependencies
from sutra_backend.config import Settings
from sutra_backend.db import create_database_engine, get_session
from sutra_backend.main import create_app
from sutra_backend.models import Agent, AgentTeam, SharedWorkspaceItem, TeamTask, utcnow
from sutra_backend.runtime.client import HermesResponse
from sutra_backend.services import team_runtime as team_runtime_service


@dataclass(frozen=True)
class FakeIdentity:
    uid: str
    email: str
    name: str | None = None
    picture: str | None = None


def build_client(
    settings: Settings,
    *,
    raise_server_exceptions: bool = True,
) -> tuple[TestClient, Session]:
    database_file = NamedTemporaryFile(suffix=".db")
    engine = create_database_engine(f"sqlite:///{database_file.name}")
    SQLModel.metadata.create_all(engine)
    session = Session(engine)

    app = create_app(settings)

    def override_get_session() -> Session:
        return session

    app.dependency_overrides[get_session] = override_get_session
    app.state._database_file = database_file
    return TestClient(app, raise_server_exceptions=raise_server_exceptions), session


def authenticate(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(
        auth_dependencies,
        "verify_firebase_token",
        lambda _: FakeIdentity(uid="firebase-user-1", email="user@example.com"),
    )
    response = client.get("/api/auth/me", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 200


def test_team_response_runs_each_agent_and_writes_workspace_summary(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        runtime_provider="static_dev",
        dev_runtime_base_url="http://runtime.internal",
        dev_runtime_api_key="runtime-key",
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
    team = session.exec(select(AgentTeam).where(AgentTeam.id == UUID(team_id))).one()

    response_ids = iter(["resp_planner", "resp_researcher"])

    async def fake_create_response(self, request, *, request_env=None):
        response_id = next(response_ids)
        if response_id == "resp_planner":
            assert "User request" in str(request.input)
            return HermesResponse(
                response_id=response_id,
                output_text="Plan the launch sequence.",
                raw_response={"id": response_id, "output": []},
            )
        assert "Plan the launch sequence." in str(request.input)
        return HermesResponse(
            response_id=response_id,
            output_text="Research competitors and comparable products.",
            raw_response={"id": response_id, "output": []},
        )

    monkeypatch.setattr(
        team_runtime_service.HermesRuntimeClient,
        "create_response",
        fake_create_response,
    )

    response = client.post(
        f"/api/teams/{team.id}/responses",
        headers={"Authorization": "Bearer valid-token"},
        json={"input": "Prepare a product launch brief."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert [item["role_name"] for item in payload["outputs"]] == ["Planner", "Researcher"]
    workspace_item = session.exec(
        select(SharedWorkspaceItem).where(SharedWorkspaceItem.path.like("conversations/%/team-summary.md"))
    ).one()
    assert workspace_item.team_id == team.id
    assert workspace_item.path.startswith("conversations/")
    assert "Prepare a product launch brief." in (workspace_item.content_text or "")
    assert "Plan the launch sequence." in (workspace_item.content_text or "")


def test_workspace_item_route_can_create_manual_shared_note(monkeypatch) -> None:
    client, session = build_client(Settings(app_env="test", database_url="sqlite://"))
    authenticate(client, monkeypatch)

    team_response = client.post(
        "/api/teams",
        headers={"Authorization": "Bearer valid-token"},
        json={
            "name": "Launch Crew",
            "agents": [{"role_template_key": "planner"}],
        },
    )
    team_id = team_response.json()["team"]["id"]

    response = client.post(
        f"/api/teams/{team_id}/workspace/items",
        headers={"Authorization": "Bearer valid-token"},
        json={
            "path": "briefs/launch-plan.md",
            "content_text": "# Launch Plan",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["item"]["path"] == "briefs/launch-plan.md"
    assert payload["item"]["content_text"] == "# Launch Plan"


def test_team_huddle_creates_owned_tasks_and_shared_plan(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        runtime_provider="static_dev",
        dev_runtime_base_url="http://runtime.internal",
        dev_runtime_api_key="runtime-key",
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

    response_ids = iter(["huddle_planner", "huddle_researcher"])

    async def fake_create_response(self, request, *, request_env=None):
        response_id = next(response_ids)
        if response_id == "huddle_planner":
            return HermesResponse(
                response_id=response_id,
                output_text="Define the launch plan, key milestones, and final deliverable structure.",
                raw_response={"id": response_id, "output": []},
            )
        return HermesResponse(
            response_id=response_id,
            output_text="Research the market, competitors, and user concerns that should shape the brief.",
            raw_response={"id": response_id, "output": []},
        )

    monkeypatch.setattr(
        team_runtime_service.HermesRuntimeClient,
        "create_response",
        fake_create_response,
    )

    response = client.post(
        f"/api/teams/{team_id}/huddles",
        headers={"Authorization": "Bearer valid-token"},
        json={"input": "Prepare a product launch brief."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["outputs"]) == 2
    assert len(payload["tasks"]) == 2
    assert all(item["status"] == "open" for item in payload["tasks"])
    assert payload["workspace_item_id"] is not None

    tasks = session.exec(select(TeamTask).order_by(TeamTask.created_at.asc())).all()
    assert len(tasks) == 2
    assert {task.title for task in tasks} == {"Planner Task", "Researcher Task"}
    assert all(task.status == "open" for task in tasks)

    workspace_item = session.exec(
        select(SharedWorkspaceItem).where(SharedWorkspaceItem.path.like("huddles/%"))
    ).one()
    assert workspace_item.path.startswith("huddles/")
    assert "Prepare a product launch brief." in (workspace_item.content_text or "")
    assert "Define the launch plan" in (workspace_item.content_text or "")

    tasks_response = client.get(
        f"/api/teams/{team_id}/tasks",
        headers={"Authorization": "Bearer valid-token"},
    )
    assert tasks_response.status_code == 200
    tasks_payload = tasks_response.json()
    assert len(tasks_payload["items"]) == 2


def test_team_response_uses_open_huddle_tasks_and_marks_them_completed(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        runtime_provider="static_dev",
        dev_runtime_base_url="http://runtime.internal",
        dev_runtime_api_key="runtime-key",
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
    team = session.exec(select(AgentTeam).where(AgentTeam.id == UUID(team_id))).one()

    huddle_ids = iter(["huddle_planner", "huddle_researcher"])

    async def fake_huddle_response(self, request, *, request_env=None):
        response_id = next(huddle_ids)
        if response_id == "huddle_planner":
            return HermesResponse(
                response_id=response_id,
                output_text="Define the launch milestones and final brief outline.",
                raw_response={"id": response_id, "output": []},
            )
        return HermesResponse(
            response_id=response_id,
            output_text="Research competitors and collect user pain points for the brief.",
            raw_response={"id": response_id, "output": []},
        )

    monkeypatch.setattr(
        team_runtime_service.HermesRuntimeClient,
        "create_response",
        fake_huddle_response,
    )

    huddle_response = client.post(
        f"/api/teams/{team.id}/huddles",
        headers={"Authorization": "Bearer valid-token"},
        json={"input": "Prepare a product launch brief."},
    )
    assert huddle_response.status_code == 200

    execution_ids = iter(["run_planner", "run_researcher"])

    async def fake_execution_response(self, request, *, request_env=None):
        response_id = next(execution_ids)
        if response_id == "run_planner":
            assert "Assigned task" in str(request.input)
            assert "launch milestones and final brief outline" in str(request.input)
            return HermesResponse(
                response_id=response_id,
                output_text="Planned the launch brief structure and milestones.",
                raw_response={"id": response_id, "output": []},
            )
        assert "Assigned task" in str(request.input)
        assert "competitors and collect user pain points" in str(request.input)
        return HermesResponse(
            response_id=response_id,
            output_text="Collected competitor notes and user pain points.",
            raw_response={"id": response_id, "output": []},
        )

    monkeypatch.setattr(
        team_runtime_service.HermesRuntimeClient,
        "create_response",
        fake_execution_response,
    )

    response = client.post(
        f"/api/teams/{team.id}/responses",
        headers={"Authorization": "Bearer valid-token"},
        json={"input": "Execute the agreed launch brief plan."},
    )
    assert response.status_code == 200

    tasks = session.exec(select(TeamTask).where(TeamTask.team_id == team.id)).all()
    assert len(tasks) == 2
    assert all(task.status == "completed" for task in tasks)


def test_team_response_releases_claimed_tasks_after_runtime_failure(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        runtime_provider="static_dev",
        dev_runtime_base_url="http://runtime.internal",
        dev_runtime_api_key="runtime-key",
    )
    client, session = build_client(settings, raise_server_exceptions=False)
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
    team = session.exec(select(AgentTeam).where(AgentTeam.id == UUID(team_id))).one()

    huddle_ids = iter(["huddle_planner", "huddle_researcher"])

    async def fake_huddle_response(self, request, *, request_env=None):
        response_id = next(huddle_ids)
        if response_id == "huddle_planner":
            return HermesResponse(
                response_id=response_id,
                output_text="Define the launch milestones and final brief outline.",
                raw_response={"id": response_id, "output": []},
            )
        return HermesResponse(
            response_id=response_id,
            output_text="Research competitors and collect user pain points for the brief.",
            raw_response={"id": response_id, "output": []},
        )

    monkeypatch.setattr(
        team_runtime_service.HermesRuntimeClient,
        "create_response",
        fake_huddle_response,
    )

    huddle_response = client.post(
        f"/api/teams/{team.id}/huddles",
        headers={"Authorization": "Bearer valid-token"},
        json={"input": "Prepare a product launch brief."},
    )
    assert huddle_response.status_code == 200

    execution_ids = iter(["run_planner", "run_researcher"])

    async def failing_execution_response(self, request, *, request_env=None):
        response_id = next(execution_ids)
        if response_id == "run_planner":
            return HermesResponse(
                response_id=response_id,
                output_text="Planned the launch brief structure and milestones.",
                raw_response={"id": response_id, "output": []},
            )
        raise RuntimeError("runtime failed")

    monkeypatch.setattr(
        team_runtime_service.HermesRuntimeClient,
        "create_response",
        failing_execution_response,
    )

    response = client.post(
        f"/api/teams/{team.id}/responses",
        headers={"Authorization": "Bearer valid-token"},
        json={"input": "Execute the agreed launch brief plan."},
    )
    assert response.status_code == 500

    tasks = session.exec(
        select(TeamTask)
        .where(TeamTask.team_id == team.id)
        .order_by(TeamTask.created_at.asc())
    ).all()
    assert len(tasks) == 2
    assert [task.status for task in tasks] == ["completed", "open"]
    assert all(task.claim_token is None for task in tasks)

    retry_ids = iter(["retry_planner", "retry_researcher"])

    async def retry_execution_response(self, request, *, request_env=None):
        response_id = next(retry_ids)
        return HermesResponse(
            response_id=response_id,
            output_text=f"Recovered with {response_id}.",
            raw_response={"id": response_id, "output": []},
        )

    monkeypatch.setattr(
        team_runtime_service.HermesRuntimeClient,
        "create_response",
        retry_execution_response,
    )

    retry_response = client.post(
        f"/api/teams/{team.id}/responses",
        headers={"Authorization": "Bearer valid-token"},
        json={"input": "Execute the agreed launch brief plan."},
    )
    assert retry_response.status_code == 200


def test_team_response_writes_per_agent_outputs_into_workspace(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        runtime_provider="static_dev",
        dev_runtime_base_url="http://runtime.internal",
        dev_runtime_api_key="runtime-key",
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
    team = session.exec(select(AgentTeam).where(AgentTeam.id == UUID(team_id))).one()

    huddle_ids = iter(["huddle_planner", "huddle_researcher"])

    async def fake_huddle_response(self, request, *, request_env=None):
        response_id = next(huddle_ids)
        if response_id == "huddle_planner":
            return HermesResponse(
                response_id=response_id,
                output_text="Define the launch milestones and final brief outline.",
                raw_response={"id": response_id, "output": []},
            )
        return HermesResponse(
            response_id=response_id,
            output_text="Research competitors and collect user pain points for the brief.",
            raw_response={"id": response_id, "output": []},
        )

    monkeypatch.setattr(
        team_runtime_service.HermesRuntimeClient,
        "create_response",
        fake_huddle_response,
    )

    huddle_response = client.post(
        f"/api/teams/{team.id}/huddles",
        headers={"Authorization": "Bearer valid-token"},
        json={"input": "Prepare a product launch brief."},
    )
    assert huddle_response.status_code == 200

    execution_ids = iter(["run_planner", "run_researcher"])

    async def fake_execution_response(self, request, *, request_env=None):
        response_id = next(execution_ids)
        if response_id == "run_planner":
            return HermesResponse(
                response_id=response_id,
                output_text="Planned the launch brief structure and milestones.",
                raw_response={"id": response_id, "output": []},
            )
        return HermesResponse(
            response_id=response_id,
            output_text="Collected competitor notes and user pain points.",
            raw_response={"id": response_id, "output": []},
        )

    monkeypatch.setattr(
        team_runtime_service.HermesRuntimeClient,
        "create_response",
        fake_execution_response,
    )

    response = client.post(
        f"/api/teams/{team.id}/responses",
        headers={"Authorization": "Bearer valid-token"},
        json={"input": "Execute the agreed launch brief plan."},
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["generated_items"]) == 2

    tasks = session.exec(select(TeamTask).where(TeamTask.team_id == team.id)).all()
    task_ids = {str(task.id) for task in tasks}
    workspace_items = session.exec(
        select(SharedWorkspaceItem).where(SharedWorkspaceItem.team_id == team.id)
    ).all()
    task_output_items = [item for item in workspace_items if item.path.startswith("tasks/")]
    assert len(task_output_items) == 2
    assert {item.path.split("/")[1] for item in task_output_items} == task_ids
    assert any("Planned the launch brief structure and milestones." in (item.content_text or "") for item in task_output_items)
    assert any("Collected competitor notes and user pain points." in (item.content_text or "") for item in task_output_items)
    assert {item["id"] for item in payload["generated_items"]} == {str(item.id) for item in task_output_items}


def test_team_response_prioritizes_previous_conversation_outputs_in_workspace_context(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        runtime_provider="static_dev",
        dev_runtime_base_url="http://runtime.internal",
        dev_runtime_api_key="runtime-key",
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
    team = session.exec(select(AgentTeam).where(AgentTeam.id == UUID(team_id))).one()

    huddle_ids = iter(["huddle_planner", "huddle_researcher"])

    async def fake_huddle_response(self, request, *, request_env=None):
        response_id = next(huddle_ids)
        if response_id == "huddle_planner":
            return HermesResponse(
                response_id=response_id,
                output_text="Define the launch milestones and final brief outline.",
                raw_response={"id": response_id, "output": []},
            )
        return HermesResponse(
            response_id=response_id,
            output_text="Research competitors and collect user pain points for the brief.",
            raw_response={"id": response_id, "output": []},
        )

    monkeypatch.setattr(
        team_runtime_service.HermesRuntimeClient,
        "create_response",
        fake_huddle_response,
    )

    huddle_response = client.post(
        f"/api/teams/{team.id}/huddles",
        headers={"Authorization": "Bearer valid-token"},
        json={"input": "Prepare a product launch brief."},
    )
    assert huddle_response.status_code == 200

    initial_execution_ids = iter(["run_planner_initial", "run_researcher_initial"])

    async def fake_initial_execution_response(self, request, *, request_env=None):
        response_id = next(initial_execution_ids)
        if response_id == "run_planner_initial":
            return HermesResponse(
                response_id=response_id,
                output_text="Planned the launch brief structure and milestones.",
                raw_response={"id": response_id, "output": []},
            )
        return HermesResponse(
            response_id=response_id,
            output_text="Collected competitor notes and user pain points.",
            raw_response={"id": response_id, "output": []},
        )

    monkeypatch.setattr(
        team_runtime_service.HermesRuntimeClient,
        "create_response",
        fake_initial_execution_response,
    )

    first_run = client.post(
        f"/api/teams/{team.id}/responses",
        headers={"Authorization": "Bearer valid-token"},
        json={"input": "Execute the agreed launch brief plan."},
    )
    assert first_run.status_code == 200
    conversation_id = first_run.json()["conversation_id"]
    task_ids = {
        task.title: str(task.id)
        for task in session.exec(select(TeamTask).where(TeamTask.team_id == team.id)).all()
    }

    followup_execution_ids = iter(["run_planner_followup", "run_researcher_followup"])

    async def fake_followup_execution_response(self, request, *, request_env=None):
        response_id = next(followup_execution_ids)
        request_input = str(request.input)
        assert "Recent shared workspace context:" in request_input
        assert f"tasks/{task_ids['Planner Task']}/output.md" in request_input
        assert "Planned the launch brief structure and milestones." in request_input
        assert f"tasks/{task_ids['Researcher Task']}/output.md" in request_input
        assert "Collected competitor notes and user pain points." in request_input
        return HermesResponse(
            response_id=response_id,
            output_text=f"Follow-up output from {response_id}.",
            raw_response={"id": response_id, "output": []},
        )

    monkeypatch.setattr(
        team_runtime_service.HermesRuntimeClient,
        "create_response",
        fake_followup_execution_response,
    )

    second_run = client.post(
        f"/api/teams/{team.id}/responses",
        headers={"Authorization": "Bearer valid-token"},
        json={
            "input": "Refine the launch brief using the outputs already in the workspace.",
            "conversation_id": conversation_id,
        },
    )
    assert second_run.status_code == 200


def test_agent_inbox_lists_assigned_tasks(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        runtime_provider="static_dev",
        dev_runtime_base_url="http://runtime.internal",
        dev_runtime_api_key="runtime-key",
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
    payload = create_team_response.json()
    team_id = payload["team"]["id"]
    planner_agent_id = payload["agents"][0]["id"]

    response_ids = iter(["huddle_planner", "huddle_researcher"])

    async def fake_create_response(self, request, *, request_env=None):
        response_id = next(response_ids)
        if response_id == "huddle_planner":
            return HermesResponse(
                response_id=response_id,
                output_text="Define the launch milestones and final brief outline.",
                raw_response={"id": response_id, "output": []},
            )
        return HermesResponse(
            response_id=response_id,
            output_text="Research competitors and collect user pain points for the brief.",
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

    inbox_response = client.get(
        f"/api/agents/{planner_agent_id}/inbox",
        headers={"Authorization": "Bearer valid-token"},
    )
    assert inbox_response.status_code == 200
    inbox_payload = inbox_response.json()
    assert len(inbox_payload["items"]) == 1
    assert inbox_payload["items"][0]["title"] == "Planner Task"
    assert inbox_payload["items"][0]["status"] == "open"


def test_team_response_claims_tasks_before_agent_execution(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        runtime_provider="static_dev",
        dev_runtime_base_url="http://runtime.internal",
        dev_runtime_api_key="runtime-key",
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
    team = session.exec(select(AgentTeam).where(AgentTeam.id == UUID(team_id))).one()

    huddle_ids = iter(["huddle_planner", "huddle_researcher"])

    async def fake_huddle_response(self, request, *, request_env=None):
        response_id = next(huddle_ids)
        if response_id == "huddle_planner":
            return HermesResponse(
                response_id=response_id,
                output_text="Define the launch milestones and final brief outline.",
                raw_response={"id": response_id, "output": []},
            )
        return HermesResponse(
            response_id=response_id,
            output_text="Research competitors and collect user pain points for the brief.",
            raw_response={"id": response_id, "output": []},
        )

    monkeypatch.setattr(
        team_runtime_service.HermesRuntimeClient,
        "create_response",
        fake_huddle_response,
    )

    huddle_response = client.post(
        f"/api/teams/{team.id}/huddles",
        headers={"Authorization": "Bearer valid-token"},
        json={"input": "Prepare a product launch brief."},
    )
    assert huddle_response.status_code == 200

    execution_ids = iter(["run_planner", "run_researcher"])

    async def fake_execution_response(self, request, *, request_env=None):
        response_id = next(execution_ids)
        if response_id == "run_planner":
            task = session.exec(
                select(TeamTask).where(TeamTask.title == "Planner Task")
            ).one()
            assert task.status == "claimed"
            assert task.claim_token is not None
            assert task.claim_expires_at is not None
            return HermesResponse(
                response_id=response_id,
                output_text="Planned the launch brief structure and milestones.",
                raw_response={"id": response_id, "output": []},
            )
        task = session.exec(
            select(TeamTask).where(TeamTask.title == "Researcher Task")
        ).one()
        assert task.status == "claimed"
        assert task.claim_token is not None
        assert task.claim_expires_at is not None
        return HermesResponse(
            response_id=response_id,
            output_text="Collected competitor notes and user pain points.",
            raw_response={"id": response_id, "output": []},
        )

    monkeypatch.setattr(
        team_runtime_service.HermesRuntimeClient,
        "create_response",
        fake_execution_response,
    )

    response = client.post(
        f"/api/teams/{team.id}/responses",
        headers={"Authorization": "Bearer valid-token"},
        json={"input": "Execute the agreed launch brief plan."},
    )
    assert response.status_code == 200

    planner_task = session.exec(select(TeamTask).where(TeamTask.title == "Planner Task")).one()
    updates_response = client.get(
        f"/api/tasks/{planner_task.id}/updates",
        headers={"Authorization": "Bearer valid-token"},
    )
    assert updates_response.status_code == 200
    updates_payload = updates_response.json()
    assert updates_payload["items"][-1]["event_type"] == "completed"


def test_task_can_be_delegated_with_audit_trail(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        runtime_provider="static_dev",
        dev_runtime_base_url="http://runtime.internal",
        dev_runtime_api_key="runtime-key",
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
    payload = create_team_response.json()
    team_id = payload["team"]["id"]
    researcher_agent_id = payload["agents"][1]["id"]

    response_ids = iter(["huddle_planner", "huddle_researcher"])

    async def fake_create_response(self, request, *, request_env=None):
        response_id = next(response_ids)
        if response_id == "huddle_planner":
            return HermesResponse(
                response_id=response_id,
                output_text="Define the launch milestones and final brief outline.",
                raw_response={"id": response_id, "output": []},
            )
        return HermesResponse(
            response_id=response_id,
            output_text="Research competitors and collect user pain points for the brief.",
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

    planner_task = session.exec(select(TeamTask).where(TeamTask.title == "Planner Task")).one()
    delegate_response = client.post(
        f"/api/tasks/{planner_task.id}/delegate",
        headers={"Authorization": "Bearer valid-token"},
        json={
            "assigned_agent_id": researcher_agent_id,
            "note": "Researcher should own the market-facing launch plan synthesis.",
        },
    )
    assert delegate_response.status_code == 200
    delegate_payload = delegate_response.json()
    assert delegate_payload["task"]["assigned_agent_id"] == researcher_agent_id
    assert delegate_payload["task"]["status"] == "open"

    session.refresh(planner_task)
    assert str(planner_task.assigned_agent_id) == researcher_agent_id
    assert planner_task.claim_token is None

    updates_response = client.get(
        f"/api/tasks/{planner_task.id}/updates",
        headers={"Authorization": "Bearer valid-token"},
    )
    assert updates_response.status_code == 200
    updates_payload = updates_response.json()
    assert updates_payload["items"][-1]["event_type"] == "delegated"
    assert "market-facing launch plan synthesis" in updates_payload["items"][-1]["content"]


def test_team_response_includes_huddle_plan_and_shared_workspace_context(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        runtime_provider="static_dev",
        dev_runtime_base_url="http://runtime.internal",
        dev_runtime_api_key="runtime-key",
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
    team = session.exec(select(AgentTeam).where(AgentTeam.id == UUID(team_id))).one()

    huddle_ids = iter(["huddle_planner", "huddle_researcher"])

    async def fake_huddle_response(self, request, *, request_env=None):
        response_id = next(huddle_ids)
        if response_id == "huddle_planner":
            return HermesResponse(
                response_id=response_id,
                output_text="Define the launch milestones and final brief outline.",
                raw_response={"id": response_id, "output": []},
            )
        return HermesResponse(
            response_id=response_id,
            output_text="Research competitors and collect user pain points for the brief.",
            raw_response={"id": response_id, "output": []},
        )

    monkeypatch.setattr(
        team_runtime_service.HermesRuntimeClient,
        "create_response",
        fake_huddle_response,
    )

    huddle_response = client.post(
        f"/api/teams/{team.id}/huddles",
        headers={"Authorization": "Bearer valid-token"},
        json={"input": "Prepare a product launch brief."},
    )
    assert huddle_response.status_code == 200

    note_response = client.post(
        f"/api/teams/{team.id}/workspace/items",
        headers={"Authorization": "Bearer valid-token"},
        json={
            "path": "notes/context.md",
            "content_text": "Shared note about the target audience and launch constraints.",
        },
    )
    assert note_response.status_code == 201

    execution_ids = iter(["run_planner", "run_researcher"])

    async def fake_execution_response(self, request, *, request_env=None):
        response_id = next(execution_ids)
        request_input = str(request.input)
        assert "Shared plan:" in request_input
        assert "Define the launch milestones and final brief outline." in request_input
        assert "Recent shared workspace context:" in request_input
        assert "notes/context.md" in request_input
        assert "Shared note about the target audience and launch constraints." in request_input
        if response_id == "run_planner":
            return HermesResponse(
                response_id=response_id,
                output_text="Planned the launch brief structure and milestones.",
                raw_response={"id": response_id, "output": []},
            )
        return HermesResponse(
            response_id=response_id,
            output_text="Collected competitor notes and user pain points.",
            raw_response={"id": response_id, "output": []},
        )

    monkeypatch.setattr(
        team_runtime_service.HermesRuntimeClient,
        "create_response",
        fake_execution_response,
    )

    response = client.post(
        f"/api/teams/{team.id}/responses",
        headers={"Authorization": "Bearer valid-token"},
        json={"input": "Execute the agreed launch brief plan."},
    )
    assert response.status_code == 200


def test_task_report_sets_in_progress_and_is_listed(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        runtime_provider="static_dev",
        dev_runtime_base_url="http://runtime.internal",
        dev_runtime_api_key="runtime-key",
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
    payload = create_team_response.json()
    team_id = payload["team"]["id"]
    planner_agent_id = payload["agents"][0]["id"]

    response_ids = iter(["huddle_planner", "huddle_researcher"])

    async def fake_create_response(self, request, *, request_env=None):
        response_id = next(response_ids)
        if response_id == "huddle_planner":
            return HermesResponse(
                response_id=response_id,
                output_text="Define the launch milestones and final brief outline.",
                raw_response={"id": response_id, "output": []},
            )
        return HermesResponse(
            response_id=response_id,
            output_text="Research competitors and collect user pain points for the brief.",
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

    planner_task = session.exec(select(TeamTask).where(TeamTask.title == "Planner Task")).one()
    report_response = client.post(
        f"/api/tasks/{planner_task.id}/reports",
        headers={"Authorization": "Bearer valid-token"},
        json={
            "agent_id": planner_agent_id,
            "content": "Started outlining the launch milestones and final structure.",
        },
    )
    assert report_response.status_code == 201
    report_payload = report_response.json()
    assert report_payload["task"]["status"] == "in_progress"

    session.refresh(planner_task)
    assert planner_task.status == "in_progress"

    updates_response = client.get(
        f"/api/tasks/{planner_task.id}/updates",
        headers={"Authorization": "Bearer valid-token"},
    )
    assert updates_response.status_code == 200
    updates_payload = updates_response.json()
    assert updates_payload["items"][-1]["event_type"] == "reported"
    assert "Started outlining the launch milestones" in updates_payload["items"][-1]["content"]


def test_task_can_receive_inter_agent_message(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        runtime_provider="static_dev",
        dev_runtime_base_url="http://runtime.internal",
        dev_runtime_api_key="runtime-key",
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
    payload = create_team_response.json()
    team_id = payload["team"]["id"]
    researcher_agent_id = payload["agents"][1]["id"]

    response_ids = iter(["huddle_planner", "huddle_researcher"])

    async def fake_create_response(self, request, *, request_env=None):
        response_id = next(response_ids)
        if response_id == "huddle_planner":
            return HermesResponse(
                response_id=response_id,
                output_text="Define the launch milestones and final brief outline.",
                raw_response={"id": response_id, "output": []},
            )
        return HermesResponse(
            response_id=response_id,
            output_text="Research competitors and collect user pain points for the brief.",
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

    planner_task = session.exec(select(TeamTask).where(TeamTask.title == "Planner Task")).one()
    message_response = client.post(
        f"/api/tasks/{planner_task.id}/messages",
        headers={"Authorization": "Bearer valid-token"},
        json={
            "agent_id": researcher_agent_id,
            "content": "Researcher here: please include two competitor references in the outline.",
        },
    )
    assert message_response.status_code == 201
    message_payload = message_response.json()
    assert message_payload["task"]["id"] == str(planner_task.id)

    updates_response = client.get(
        f"/api/tasks/{planner_task.id}/updates",
        headers={"Authorization": "Bearer valid-token"},
    )
    assert updates_response.status_code == 200
    updates_payload = updates_response.json()
    assert updates_payload["items"][-1]["event_type"] == "message"
    assert "competitor references" in updates_payload["items"][-1]["content"]


def test_agent_can_claim_next_inbox_task_and_complete_it(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        runtime_provider="static_dev",
        dev_runtime_base_url="http://runtime.internal",
        dev_runtime_api_key="runtime-key",
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
    payload = create_team_response.json()
    team_id = payload["team"]["id"]
    planner_agent_id = payload["agents"][0]["id"]

    response_ids = iter(["huddle_planner", "huddle_researcher"])

    async def fake_create_response(self, request, *, request_env=None):
        response_id = next(response_ids)
        if response_id == "huddle_planner":
            return HermesResponse(
                response_id=response_id,
                output_text="Define the launch milestones and final brief outline.",
                raw_response={"id": response_id, "output": []},
            )
        return HermesResponse(
            response_id=response_id,
            output_text="Research competitors and collect user pain points for the brief.",
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

    claim_response = client.post(
        f"/api/agents/{planner_agent_id}/inbox/claim-next",
        headers={"Authorization": "Bearer valid-token"},
    )
    assert claim_response.status_code == 200
    claim_payload = claim_response.json()
    assert claim_payload["task"] is not None
    assert claim_payload["task"]["status"] == "claimed"
    assert claim_payload["task"]["claim_token"] is not None

    task_id = claim_payload["task"]["id"]
    claim_token = claim_payload["task"]["claim_token"]
    complete_response = client.post(
        f"/api/tasks/{task_id}/complete",
        headers={"Authorization": "Bearer valid-token"},
        json={
            "agent_id": planner_agent_id,
            "claim_token": claim_token,
            "content": "Completed the launch outline and milestones.",
        },
    )
    assert complete_response.status_code == 200
    complete_payload = complete_response.json()
    assert complete_payload["task"]["status"] == "completed"

    updates_response = client.get(
        f"/api/tasks/{task_id}/updates",
        headers={"Authorization": "Bearer valid-token"},
    )
    assert updates_response.status_code == 200
    updates_payload = updates_response.json()
    assert updates_payload["items"][-2]["event_type"] == "claimed"
    assert updates_payload["items"][-1]["event_type"] == "completed"


def test_agent_can_run_next_inbox_task_through_runtime(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        runtime_provider="static_dev",
        dev_runtime_base_url="http://runtime.internal",
        dev_runtime_api_key="runtime-key",
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
    payload = create_team_response.json()
    team_id = payload["team"]["id"]
    planner_agent_id = payload["agents"][0]["id"]

    response_ids = iter(["huddle_planner", "huddle_researcher", "runtime_planner"])

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
        assert "Assigned task" in str(request.input)
        assert "Define the launch milestones and final brief outline." in str(request.input)
        return HermesResponse(
            response_id=response_id,
            output_text="Completed the launch outline through the runtime loop.",
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

    run_response = client.post(
        f"/api/agents/{planner_agent_id}/inbox/run-next",
        headers={"Authorization": "Bearer valid-token"},
    )
    assert run_response.status_code == 200
    run_payload = run_response.json()
    assert run_payload["task"]["status"] == "completed"
    assert run_payload["response_id"] == "runtime_planner"
    assert "runtime loop" in run_payload["output_text"]
    assert run_payload["workspace_item_id"] is not None

    workspace_item = session.exec(
        select(SharedWorkspaceItem).where(SharedWorkspaceItem.id == UUID(run_payload["workspace_item_id"]))
    ).one()
    assert workspace_item.path == f"tasks/{run_payload['task']['id']}/output.md"
    assert "Planner Task" in (workspace_item.content_text or "")
    assert "runtime loop" in (workspace_item.content_text or "")

    updates_response = client.get(
        f"/api/tasks/{run_payload['task']['id']}/updates",
        headers={"Authorization": "Bearer valid-token"},
    )
    assert updates_response.status_code == 200
    updates_payload = updates_response.json()
    assert updates_payload["items"][-2]["event_type"] == "claimed"
    assert updates_payload["items"][-1]["event_type"] == "completed"


def test_running_inbox_task_includes_plan_updates_and_workspace_context(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        runtime_provider="static_dev",
        dev_runtime_base_url="http://runtime.internal",
        dev_runtime_api_key="runtime-key",
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
    payload = create_team_response.json()
    team_id = payload["team"]["id"]
    planner_agent_id = payload["agents"][0]["id"]

    response_ids = iter(["huddle_planner", "huddle_researcher"])

    async def fake_huddle_response(self, request, *, request_env=None):
        response_id = next(response_ids)
        if response_id == "huddle_planner":
            return HermesResponse(
                response_id=response_id,
                output_text="Define the launch milestones and final brief outline.",
                raw_response={"id": response_id, "output": []},
            )
        return HermesResponse(
            response_id=response_id,
            output_text="Research competitors and collect user pain points for the brief.",
            raw_response={"id": response_id, "output": []},
        )

    monkeypatch.setattr(
        team_runtime_service.HermesRuntimeClient,
        "create_response",
        fake_huddle_response,
    )

    huddle_response = client.post(
        f"/api/teams/{team_id}/huddles",
        headers={"Authorization": "Bearer valid-token"},
        json={"input": "Prepare a product launch brief."},
    )
    assert huddle_response.status_code == 200
    planner_task_id = huddle_response.json()["tasks"][0]["id"]

    report_response = client.post(
        f"/api/tasks/{planner_task_id}/reports",
        headers={"Authorization": "Bearer valid-token"},
        json={
            "content": "Need competitor examples before finalizing the structure.",
            "agent_id": planner_agent_id,
        },
    )
    assert report_response.status_code == 201

    note_response = client.post(
        f"/api/teams/{team_id}/workspace/items",
        headers={"Authorization": "Bearer valid-token"},
        json={
            "path": "notes/research.md",
            "content_text": "Existing research note with two strong competitor examples.",
        },
    )
    assert note_response.status_code == 201

    async def fake_inbox_response(self, request, *, request_env=None):
        request_input = str(request.input)
        assert "Shared plan:" in request_input
        assert "Define the launch milestones and final brief outline." in request_input
        assert "Task updates so far:" in request_input
        assert "Need competitor examples before finalizing the structure." in request_input
        assert "Recent shared workspace context:" in request_input
        assert "notes/research.md" in request_input
        assert "Existing research note with two strong competitor examples." in request_input
        return HermesResponse(
            response_id="inbox_planner",
            output_text="Completed the launch structure using the plan and shared research.",
            raw_response={"id": "inbox_planner", "output": []},
        )

    monkeypatch.setattr(
        team_runtime_service.HermesRuntimeClient,
        "create_response",
        fake_inbox_response,
    )

    run_response = client.post(
        f"/api/agents/{planner_agent_id}/inbox/run-next",
        headers={"Authorization": "Bearer valid-token"},
    )
    assert run_response.status_code == 200
    assert run_response.json()["task"]["status"] == "completed"


def test_team_inbox_cycle_runs_pending_tasks_across_agents(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        runtime_provider="static_dev",
        dev_runtime_base_url="http://runtime.internal",
        dev_runtime_api_key="runtime-key",
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
    payload = create_team_response.json()
    team_id = payload["team"]["id"]

    response_ids = iter(
        [
            "huddle_planner",
            "huddle_researcher",
            "cycle_planner",
            "cycle_researcher",
        ]
    )

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
        if response_id == "cycle_planner":
            return HermesResponse(
                response_id=response_id,
                output_text="Completed the planner task inside the inbox cycle.",
                raw_response={"id": response_id, "output": []},
            )
        return HermesResponse(
            response_id=response_id,
            output_text="Completed the researcher task inside the inbox cycle.",
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

    cycle_response = client.post(
        f"/api/teams/{team_id}/inbox/run-cycle",
        headers={"Authorization": "Bearer valid-token"},
    )
    assert cycle_response.status_code == 200
    cycle_payload = cycle_response.json()
    assert cycle_payload["executed_count"] == 2
    assert len(cycle_payload["results"]) == 2
    assert cycle_payload["results"][0]["response_id"] == "cycle_planner"
    assert cycle_payload["results"][1]["response_id"] == "cycle_researcher"

    tasks = session.exec(select(TeamTask).where(TeamTask.team_id == UUID(team_id))).all()
    assert len(tasks) == 2
    assert all(task.status == "completed" for task in tasks)


def test_team_task_listing_reopens_expired_claims(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        runtime_provider="static_dev",
        dev_runtime_base_url="http://runtime.internal",
        dev_runtime_api_key="runtime-key",
    )
    client, session = build_client(settings)
    authenticate(client, monkeypatch)

    create_team_response = client.post(
        "/api/teams",
        headers={"Authorization": "Bearer valid-token"},
        json={
            "name": "Launch Crew",
            "agents": [{"role_template_key": "planner"}],
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

    task = session.exec(select(TeamTask).where(TeamTask.team_id == UUID(team_id))).one()
    task.status = "claimed"
    task.claim_token = "expired-claim"
    task.claimed_at = utcnow() - timedelta(minutes=10)
    task.claim_expires_at = utcnow() - timedelta(minutes=5)
    session.add(task)
    session.commit()

    response = client.get(
        f"/api/teams/{team_id}/tasks",
        headers={"Authorization": "Bearer valid-token"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["status"] == "open"
    assert payload["items"][0]["claim_token"] is None

    updates_response = client.get(
        f"/api/tasks/{task.id}/updates",
        headers={"Authorization": "Bearer valid-token"},
    )
    assert updates_response.status_code == 200
    assert updates_response.json()["items"][-1]["event_type"] == "reopened"
