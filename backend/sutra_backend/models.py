from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from enum import StrEnum

from sqlalchemy import Column, Enum as SAEnum, Index, MetaData, UniqueConstraint
from sqlmodel import Field, SQLModel

from sutra_backend.enums import (
    AgentStatus,
    ArtifactKind,
    ConversationMode,
    ConversationStatus,
    GitHubAccountType,
    MessageActorType,
    PollerLeaseState,
    RuntimeKind,
    RuntimeLeaseState,
    SecretScope,
    TeamMode,
    TeamTaskSource,
    TeamTaskStatus,
    TeamTaskUpdateType,
    ToolEventType,
    ToolProfile,
    WorkspaceItemKind,
)


SQLModel.metadata = MetaData(
    naming_convention={
        "ix": "ix_%(table_name)s_%(column_0_N_name)s",
        "uq": "uq_%(table_name)s_%(column_0_N_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)


def enum_field(enum_cls: type[StrEnum], *, default: StrEnum, index: bool = False) -> object:
    return Field(
        default=default,
        sa_column=Column(
            SAEnum(
                enum_cls,
                values_callable=lambda members: [member.value for member in members],
                native_enum=False,
                name=enum_cls.__name__.lower(),
            ),
            default=default,
            nullable=False,
            index=index,
        ),
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


class AgentTeam(TimestampedUUIDModel, table=True):
    __tablename__ = "teams"

    user_id: UUID = Field(foreign_key="users.id", index=True, nullable=False)
    name: str = Field(nullable=False)
    description: str | None = Field(default=None)
    mode: TeamMode = enum_field(TeamMode, default=TeamMode.PERSONAL, index=True)
    shared_workspace_uri: str | None = Field(default=None)


class RoleTemplate(TimestampedUUIDModel, table=True):
    __tablename__ = "role_templates"
    __table_args__ = (UniqueConstraint("key", name="uq_role_templates_key"),)

    key: str = Field(index=True, nullable=False)
    name: str = Field(nullable=False)
    description: str | None = Field(default=None)
    default_system_prompt: str = Field(nullable=False)
    default_tool_profile: ToolProfile = enum_field(ToolProfile, default=ToolProfile.FULL_WEB)


class Agent(TimestampedUUIDModel, table=True):
    __tablename__ = "agents"

    user_id: UUID = Field(foreign_key="users.id", index=True, nullable=False)
    role_template_id: UUID | None = Field(
        default=None,
        foreign_key="role_templates.id",
        index=True,
    )
    name: str = Field(nullable=False)
    role_name: str = Field(nullable=False)
    status: AgentStatus = enum_field(AgentStatus, default=AgentStatus.PROVISIONING, index=True)
    runtime_kind: RuntimeKind = enum_field(RuntimeKind, default=RuntimeKind.FIRECRACKER)
    hermes_home_uri: str | None = Field(default=None)
    private_volume_uri: str | None = Field(default=None)


class AgentTeamAssignment(TimestampedUUIDModel, table=True):
    __tablename__ = "agent_team_assignments"
    __table_args__ = (
        UniqueConstraint("agent_id", "agent_team_id", name="uq_agent_team_assignments_agent_team"),
    )

    agent_id: UUID = Field(foreign_key="agents.id", index=True, nullable=False)
    agent_team_id: UUID = Field(foreign_key="teams.id", index=True, nullable=False)
    shared_workspace_enabled: bool = Field(default=True, nullable=False)


class Conversation(TimestampedUUIDModel, table=True):
    __tablename__ = "conversations"

    agent_team_id: UUID | None = Field(default=None, foreign_key="teams.id", index=True)
    agent_id: UUID | None = Field(default=None, foreign_key="agents.id", index=True)
    mode: ConversationMode = enum_field(ConversationMode, default=ConversationMode.AGENT, index=True)
    latest_response_id: str | None = Field(default=None)
    status: ConversationStatus = enum_field(ConversationStatus, default=ConversationStatus.ACTIVE, index=True)


class Message(TimestampedUUIDModel, table=True):
    __tablename__ = "messages"

    conversation_id: UUID = Field(
        foreign_key="conversations.id",
        index=True,
        nullable=False,
    )
    actor_type: MessageActorType = enum_field(MessageActorType, default=MessageActorType.USER, index=True)
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
    event_type: ToolEventType = enum_field(ToolEventType, default=ToolEventType.STARTED, index=True)
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
    kind: ArtifactKind = enum_field(ArtifactKind, default=ArtifactKind.DOCUMENT, index=True)
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
    kind: WorkspaceItemKind = enum_field(WorkspaceItemKind, default=WorkspaceItemKind.FILE, index=True)
    size_bytes: int | None = Field(default=None)
    content_text: str | None = Field(default=None)
    conversation_id: UUID | None = Field(default=None, foreign_key="conversations.id", index=True)
    agent_id: UUID | None = Field(default=None, foreign_key="agents.id", index=True)


class TeamTask(TimestampedUUIDModel, table=True):
    __tablename__ = "team_tasks"

    team_id: UUID = Field(foreign_key="teams.id", index=True, nullable=False)
    conversation_id: UUID = Field(
        foreign_key="conversations.id",
        index=True,
        nullable=False,
    )
    assigned_agent_id: UUID = Field(
        foreign_key="agents.id",
        index=True,
        nullable=False,
    )
    title: str = Field(nullable=False)
    instruction: str = Field(nullable=False)
    status: TeamTaskStatus = enum_field(TeamTaskStatus, default=TeamTaskStatus.OPEN, index=True)
    source: TeamTaskSource = enum_field(TeamTaskSource, default=TeamTaskSource.HUDDLE, index=True)
    claim_token: str | None = Field(default=None, index=True)
    claimed_at: datetime | None = Field(default=None)
    claim_expires_at: datetime | None = Field(default=None, index=True)
    completed_at: datetime | None = Field(default=None)


class TeamTaskUpdate(TimestampedUUIDModel, table=True):
    __tablename__ = "team_task_updates"

    task_id: UUID = Field(foreign_key="team_tasks.id", index=True, nullable=False)
    team_id: UUID = Field(foreign_key="teams.id", index=True, nullable=False)
    agent_id: UUID | None = Field(default=None, foreign_key="agents.id", index=True)
    event_type: TeamTaskUpdateType = enum_field(
        TeamTaskUpdateType,
        default=TeamTaskUpdateType.REPORTED,
        index=True,
    )
    content: str = Field(nullable=False)


class Secret(TimestampedUUIDModel, table=True):
    __tablename__ = "secrets"

    user_id: UUID = Field(foreign_key="users.id", index=True, nullable=False)
    team_id: UUID | None = Field(default=None, foreign_key="teams.id", index=True)
    agent_id: UUID | None = Field(default=None, foreign_key="agents.id", index=True)
    name: str = Field(nullable=False)
    provider: str | None = Field(default=None)
    scope: SecretScope = enum_field(SecretScope, default=SecretScope.USER, index=True)
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
    account_type: GitHubAccountType = enum_field(GitHubAccountType, default=GitHubAccountType.USER)
    connected_at: datetime = Field(default_factory=utcnow, nullable=False)


class AutomationJob(TimestampedUUIDModel, table=True):
    __tablename__ = "automation_jobs"

    agent_id: UUID = Field(foreign_key="agents.id", index=True, nullable=False)
    agent_team_id: UUID | None = Field(default=None, foreign_key="teams.id", index=True)
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
    host_vm_id: str | None = Field(default=None, index=True)
    host_api_base_url: str | None = Field(default=None)
    state: RuntimeLeaseState = enum_field(
        RuntimeLeaseState,
        default=RuntimeLeaseState.PROVISIONING,
        index=True,
    )
    api_base_url: str | None = Field(default=None)
    last_heartbeat_at: datetime | None = Field(default=None)
    started_at: datetime | None = Field(default=None)


class PollerLease(TimestampedUUIDModel, table=True):
    __tablename__ = "poller_leases"
    __table_args__ = (
        UniqueConstraint("name", name="uq_poller_leases_name"),
    )

    name: str = Field(nullable=False, index=True)
    owner_id: str | None = Field(default=None, index=True)
    state: PollerLeaseState = enum_field(PollerLeaseState, default=PollerLeaseState.IDLE, index=True)
    last_heartbeat_at: datetime | None = Field(default=None)
    lease_expires_at: datetime | None = Field(default=None)
    last_sweep_started_at: datetime | None = Field(default=None)
    last_sweep_completed_at: datetime | None = Field(default=None)
    last_executed_count: int = Field(default=0, nullable=False)
