from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import Index, MetaData, UniqueConstraint
from sqlmodel import Field, SQLModel


SQLModel.metadata = MetaData(
    naming_convention={
        "ix": "ix_%(table_name)s_%(column_0_N_name)s",
        "uq": "uq_%(table_name)s_%(column_0_N_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampedUUIDModel(SQLModel):
    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    created_at: datetime = Field(default_factory=utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=utcnow, nullable=False)


class User(TimestampedUUIDModel, table=True):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("firebase_uid", name="uq_users_firebase_uid"),)

    firebase_uid: str = Field(index=True, nullable=False)
    email: str = Field(index=True, nullable=False)
    display_name: str | None = Field(default=None)
    photo_url: str | None = Field(default=None)


class Team(TimestampedUUIDModel, table=True):
    __tablename__ = "teams"

    user_id: UUID = Field(foreign_key="users.id", index=True, nullable=False)
    name: str = Field(nullable=False)
    description: str | None = Field(default=None)
    mode: str = Field(default="personal", index=True, nullable=False)
    shared_workspace_uri: str | None = Field(default=None)


class RoleTemplate(TimestampedUUIDModel, table=True):
    __tablename__ = "role_templates"
    __table_args__ = (UniqueConstraint("key", name="uq_role_templates_key"),)

    key: str = Field(index=True, nullable=False)
    name: str = Field(nullable=False)
    description: str | None = Field(default=None)
    default_system_prompt: str = Field(nullable=False)
    default_tool_profile: str = Field(default="full_web", nullable=False)


class Agent(TimestampedUUIDModel, table=True):
    __tablename__ = "agents"

    team_id: UUID = Field(foreign_key="teams.id", index=True, nullable=False)
    role_template_id: UUID | None = Field(
        default=None,
        foreign_key="role_templates.id",
        index=True,
    )
    name: str = Field(nullable=False)
    role_name: str = Field(nullable=False)
    status: str = Field(default="provisioning", index=True, nullable=False)
    runtime_kind: str = Field(default="firecracker", nullable=False)
    hermes_home_uri: str | None = Field(default=None)
    private_volume_uri: str | None = Field(default=None)
    shared_workspace_enabled: bool = Field(default=True, nullable=False)


class Conversation(TimestampedUUIDModel, table=True):
    __tablename__ = "conversations"

    team_id: UUID | None = Field(default=None, foreign_key="teams.id", index=True)
    agent_id: UUID | None = Field(default=None, foreign_key="agents.id", index=True)
    mode: str = Field(default="single_agent", index=True, nullable=False)
    latest_response_id: str | None = Field(default=None)
    status: str = Field(default="active", index=True, nullable=False)


class Message(TimestampedUUIDModel, table=True):
    __tablename__ = "messages"

    conversation_id: UUID = Field(
        foreign_key="conversations.id",
        index=True,
        nullable=False,
    )
    actor_type: str = Field(default="user", index=True, nullable=False)
    actor_id: UUID | None = Field(default=None, index=True)
    content: str = Field(nullable=False)
    response_chain_id: str | None = Field(default=None, index=True)


class ToolEvent(TimestampedUUIDModel, table=True):
    __tablename__ = "tool_events"

    conversation_id: UUID = Field(
        foreign_key="conversations.id",
        index=True,
        nullable=False,
    )
    agent_id: UUID | None = Field(default=None, foreign_key="agents.id", index=True)
    message_id: UUID | None = Field(default=None, foreign_key="messages.id", index=True)
    tool_name: str = Field(index=True, nullable=False)
    event_type: str = Field(index=True, nullable=False)
    summary: str | None = Field(default=None)
    payload_excerpt: str | None = Field(default=None)
    started_at: datetime | None = Field(default=None)
    ended_at: datetime | None = Field(default=None)


class Artifact(TimestampedUUIDModel, table=True):
    __tablename__ = "artifacts"

    team_id: UUID | None = Field(default=None, foreign_key="teams.id", index=True)
    conversation_id: UUID | None = Field(
        default=None,
        foreign_key="conversations.id",
        index=True,
    )
    agent_id: UUID | None = Field(default=None, foreign_key="agents.id", index=True)
    name: str = Field(nullable=False)
    kind: str = Field(default="document", index=True, nullable=False)
    uri: str = Field(nullable=False)
    mime_type: str | None = Field(default=None)
    preview_uri: str | None = Field(default=None)
    github_repo: str | None = Field(default=None)
    github_branch: str | None = Field(default=None)
    github_sha: str | None = Field(default=None)


class SharedWorkspaceItem(TimestampedUUIDModel, table=True):
    __tablename__ = "shared_workspace_items"

    team_id: UUID = Field(foreign_key="teams.id", index=True, nullable=False)
    path: str = Field(nullable=False)
    kind: str = Field(default="file", index=True, nullable=False)
    size_bytes: int | None = Field(default=None)


class Secret(TimestampedUUIDModel, table=True):
    __tablename__ = "secrets"

    user_id: UUID = Field(foreign_key="users.id", index=True, nullable=False)
    team_id: UUID | None = Field(default=None, foreign_key="teams.id", index=True)
    agent_id: UUID | None = Field(default=None, foreign_key="agents.id", index=True)
    name: str = Field(nullable=False)
    provider: str | None = Field(default=None)
    scope: str = Field(default="user", index=True, nullable=False)
    encrypted_value: str = Field(nullable=False)
    last_used_at: datetime | None = Field(default=None)


class GitHubConnection(TimestampedUUIDModel, table=True):
    __tablename__ = "github_connections"
    __table_args__ = (
        UniqueConstraint(
            "installation_id",
            name="uq_github_connections_installation_id",
        ),
    )

    user_id: UUID = Field(foreign_key="users.id", index=True, nullable=False)
    installation_id: str = Field(nullable=False)
    account_login: str = Field(nullable=False)
    account_type: str = Field(default="user", nullable=False)
    connected_at: datetime = Field(default_factory=utcnow, nullable=False)


class AutomationJob(TimestampedUUIDModel, table=True):
    __tablename__ = "automation_jobs"

    team_id: UUID | None = Field(default=None, foreign_key="teams.id", index=True)
    agent_id: UUID | None = Field(default=None, foreign_key="agents.id", index=True)
    name: str = Field(nullable=False)
    schedule: str = Field(nullable=False)
    prompt: str = Field(nullable=False)
    enabled: bool = Field(default=True, nullable=False)
    last_run_at: datetime | None = Field(default=None)
    next_run_at: datetime | None = Field(default=None)


class RuntimeLease(TimestampedUUIDModel, table=True):
    __tablename__ = "runtime_leases"
    __table_args__ = (
        UniqueConstraint("agent_id", name="uq_runtime_leases_agent_id"),
        Index("ix_runtime_leases_agent_id_state", "agent_id", "state"),
    )

    agent_id: UUID = Field(foreign_key="agents.id", index=True, nullable=False)
    vm_id: str = Field(nullable=False)
    state: str = Field(default="provisioning", index=True, nullable=False)
    api_base_url: str | None = Field(default=None)
    last_heartbeat_at: datetime | None = Field(default=None)
    started_at: datetime | None = Field(default=None)
