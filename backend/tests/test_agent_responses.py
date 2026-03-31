from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from tempfile import NamedTemporaryFile

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, select

from sutra_backend.auth import dependencies as auth_dependencies
from sutra_backend.config import Settings
from sutra_backend.db import create_database_engine, get_session
from sutra_backend.main import create_app
from sutra_backend.models import Agent, Conversation, Message, RuntimeLease, SharedWorkspaceItem
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


def test_agent_responses_route_runs_default_agent_and_persists_conversation(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        dev_runtime_base_url="http://runtime.internal",
        dev_runtime_api_key="runtime-key",
    )
    client, session = build_client(settings)
    authenticate_default_user(client, monkeypatch)

    agent = session.exec(select(Agent)).one()
    captured_requests: list[object] = []

    async def fake_create_response(self, request, *, request_env=None):
        captured_requests.append(request)
        return HermesResponse(
            response_id="resp_123",
            output_text="Here is the plan.",
            raw_response={"id": "resp_123", "output": []},
        )

    monkeypatch.setattr(runtime_service.HermesRuntimeClient, "create_response", fake_create_response)

    response = client.post(
        f"/api/agents/{agent.id}/responses",
        headers={"Authorization": "Bearer valid-token"},
        json={"input": "Make a plan"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["response_id"] == "resp_123"
    assert payload["output_text"] == "Here is the plan."
    assert payload["workspace_item_id"] is not None

    conversation = session.exec(select(Conversation)).one()
    messages = session.exec(select(Message)).all()
    lease = session.exec(select(RuntimeLease)).one()
    workspace_item = session.exec(select(SharedWorkspaceItem)).one()

    assert conversation.latest_response_id == "resp_123"
    assert len(messages) == 2
    assert messages[0].actor_type == "user"
    assert messages[1].actor_type == "assistant"
    assert lease.api_base_url == "http://runtime.internal"
    assert workspace_item.path == f"conversations/{conversation.id}.md"
    assert "Make a plan" in (workspace_item.content_text or "")
    assert "Here is the plan." in (workspace_item.content_text or "")
    assert len(captured_requests) == 1


def test_agent_responses_route_uses_previous_response_chain_for_existing_conversation(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        dev_runtime_base_url="http://runtime.internal",
        dev_runtime_api_key="runtime-key",
    )
    client, session = build_client(settings)
    authenticate_default_user(client, monkeypatch)

    agent = session.exec(select(Agent)).one()
    seen_previous_response_ids: list[str | None] = []
    seen_conversations: list[str | None] = []
    response_ids = iter(["resp_123", "resp_456"])

    async def fake_create_response(self, request, *, request_env=None):
        seen_previous_response_ids.append(request.previous_response_id)
        seen_conversations.append(request.conversation)
        response_id = next(response_ids)
        return HermesResponse(
            response_id=response_id,
            output_text=f"Reply for {response_id}",
            raw_response={"id": response_id, "output": []},
        )

    monkeypatch.setattr(runtime_service.HermesRuntimeClient, "create_response", fake_create_response)

    first_response = client.post(
        f"/api/agents/{agent.id}/responses",
        headers={"Authorization": "Bearer valid-token"},
        json={"input": "First"},
    )
    conversation_id = first_response.json()["conversation_id"]

    second_response = client.post(
        f"/api/agents/{agent.id}/responses",
        headers={"Authorization": "Bearer valid-token"},
        json={"input": "Second", "conversation_id": conversation_id},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert seen_previous_response_ids == [None, None]
    assert seen_conversations == [
        f"agent:{agent.id}:conversation:{conversation_id}",
        f"agent:{agent.id}:conversation:{conversation_id}",
    ]


def test_agent_responses_route_refreshes_conversation_updated_at(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        dev_runtime_base_url="http://runtime.internal",
        dev_runtime_api_key="runtime-key",
    )
    client, session = build_client(settings)
    authenticate_default_user(client, monkeypatch)

    agent = session.exec(select(Agent)).one()

    async def fake_create_response(self, request, *, request_env=None):
        return HermesResponse(
            response_id="resp_123",
            output_text="Updated thread.",
            raw_response={"id": "resp_123", "output": []},
        )

    monkeypatch.setattr(runtime_service.HermesRuntimeClient, "create_response", fake_create_response)

    first_response = client.post(
        f"/api/agents/{agent.id}/responses",
        headers={"Authorization": "Bearer valid-token"},
        json={"input": "First"},
    )
    assert first_response.status_code == 200

    conversation = session.exec(select(Conversation)).one()
    stale_updated_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
    conversation.updated_at = stale_updated_at
    session.add(conversation)
    session.commit()

    second_response = client.post(
        f"/api/agents/{agent.id}/responses",
        headers={"Authorization": "Bearer valid-token"},
        json={"input": "Second", "conversation_id": str(conversation.id)},
    )

    assert second_response.status_code == 200
    session.refresh(conversation)
    assert conversation.updated_at > stale_updated_at
