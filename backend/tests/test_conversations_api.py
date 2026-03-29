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
from sutra_backend.models import Agent, Conversation, Message
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
    foreign_conversation.team_id = None
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
