from __future__ import annotations

from dataclasses import dataclass
import json
from tempfile import NamedTemporaryFile
from uuid import UUID

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, select

from sutra_backend.auth import dependencies as auth_dependencies
from sutra_backend.config import Settings
from sutra_backend.db import create_database_engine, get_session
from sutra_backend.main import create_app
from sutra_backend.models import Agent, AgentTeam, Conversation, Message
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


def test_conversation_routes_return_persisted_history(monkeypatch) -> None:
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
    personal_team = session.exec(select(AgentTeam).where(AgentTeam.mode == "personal")).one()
    personal_team = session.exec(select(AgentTeam).where(AgentTeam.mode == "personal")).one()

    async def fake_create_response(self, request, *, request_env=None):
        return HermesResponse(
            response_id="resp_123",
            output_text="First assistant reply",
            raw_response={"id": "resp_123", "output": []},
        )

    monkeypatch.setattr(runtime_service.HermesRuntimeClient, "create_response", fake_create_response)

    create_response = client.post(
        f"/api/agents/{agent.id}/responses",
        headers={"Authorization": "Bearer valid-token"},
        json={"input": "Make a plan"},
    )

    assert create_response.status_code == 200
    conversation_id = create_response.json()["conversation_id"]

    conversations_response = client.get(
        f"/api/agents/{agent.id}/conversations",
        headers={"Authorization": "Bearer valid-token"},
    )
    messages_response = client.get(
        f"/api/conversations/{conversation_id}/messages",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert conversations_response.status_code == 200
    assert messages_response.status_code == 200

    conversations = conversations_response.json()["items"]
    messages = messages_response.json()["items"]

    assert len(conversations) == 1
    assert conversations[0]["id"] == conversation_id
    assert conversations[0]["mode"] == "agent"
    assert conversations[0]["latest_response_id"] == "resp_123"
    assert [message["actor_type"] for message in messages] == ["user", "assistant"]


def test_conversation_message_route_blocks_cross_tenant_access(monkeypatch) -> None:
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
    personal_team = session.exec(select(AgentTeam).where(AgentTeam.mode == "personal")).one()

    async def fake_create_response(self, request, *, request_env=None):
        return HermesResponse(
            response_id="resp_123",
            output_text="First assistant reply",
            raw_response={"id": "resp_123", "output": []},
        )

    monkeypatch.setattr(runtime_service.HermesRuntimeClient, "create_response", fake_create_response)

    create_response = client.post(
        f"/api/agents/{agent.id}/responses",
        headers={"Authorization": "Bearer valid-token"},
        json={"input": "Make a plan"},
    )
    conversation_id = create_response.json()["conversation_id"]

    foreign_conversation = session.exec(
        select(Conversation).where(Conversation.id == UUID(conversation_id))
    ).one()
    foreign_conversation.agent_team_id = None
    foreign_conversation.agent_id = None
    session.add(foreign_conversation)
    session.add(
        Message(
            conversation_id=foreign_conversation.id,
            actor_type="assistant",
            content="Hidden reply",
        )
    )
    session.commit()

    response = client.get(
        f"/api/conversations/{conversation_id}/messages",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 404


def test_conversation_stream_emits_runtime_message_and_workspace_events(monkeypatch) -> None:
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
    personal_team = session.exec(select(AgentTeam).where(AgentTeam.mode == "personal")).one()

    async def fake_create_response(self, request, *, request_env=None):
        return HermesResponse(
            response_id="resp_stream",
            output_text="Streamed assistant reply",
            raw_response={"id": "resp_stream", "output": []},
        )

    monkeypatch.setattr(runtime_service.HermesRuntimeClient, "create_response", fake_create_response)

    create_response = client.post(
        f"/api/agents/{agent.id}/responses",
        headers={"Authorization": "Bearer valid-token"},
        json={"input": "Stream this"},
    )
    assert create_response.status_code == 200
    conversation_id = create_response.json()["conversation_id"]

    with client.stream(
        "GET",
        f"/api/conversations/{conversation_id}/stream?max_events=5&idle_timeout_seconds=1",
        headers={"Authorization": "Bearer valid-token"},
    ) as response:
        assert response.status_code == 200
        payload_lines = [
            line.removeprefix("data: ")
            for line in response.iter_lines()
            if line.startswith("data: ")
        ]

    assert len(payload_lines) == 5
    event_types = [json.loads(line)["type"] for line in payload_lines]
    assert event_types == [
        "runtime.state_changed",
        "run.started",
        "assistant.message_delta",
        "run.completed",
        "workspace.item_created",
    ]
    runtime_payload = json.loads(payload_lines[0])["payload"]
    assert runtime_payload["provider"] == "static_dev"
    assert runtime_payload["isolation_ok"] is True
    workspace_payload = json.loads(payload_lines[-1])["payload"]
    assert workspace_payload["path"].startswith("conversations/")


def test_team_member_response_creates_team_context_conversation(monkeypatch) -> None:
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
    personal_team = session.exec(select(AgentTeam).where(AgentTeam.mode == "personal")).one()

    async def fake_create_response(self, request, *, request_env=None):
        return HermesResponse(
            response_id="resp_team_member",
            output_text="Team-context assistant reply",
            raw_response={"id": "resp_team_member", "output": []},
        )

    monkeypatch.setattr(runtime_service.HermesRuntimeClient, "create_response", fake_create_response)

    response = client.post(
        f"/api/teams/{personal_team.id}/agents/{agent.id}/responses",
        headers={"Authorization": "Bearer valid-token"},
        json={"input": "Review the shared plan and give your view."},
    )

    assert response.status_code == 200
    conversation = session.get(Conversation, UUID(response.json()["conversation_id"]))
    assert conversation is not None
    assert conversation.mode == "team_member"
    assert conversation.agent_team_id == personal_team.id
