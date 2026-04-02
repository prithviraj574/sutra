from __future__ import annotations

from enum import StrEnum


class TeamMode(StrEnum):
    PERSONAL = "personal"
    TEAM = "team"


class ToolProfile(StrEnum):
    FULL_WEB = "full_web"


class AgentStatus(StrEnum):
    PROVISIONING = "provisioning"
    READY = "ready"
    RUNNING = "running"
    RUNTIME_UNREACHABLE = "runtime_unreachable"


class RuntimeKind(StrEnum):
    FIRECRACKER = "firecracker"


class ConversationMode(StrEnum):
    AGENT = "agent"
    TEAM = "team"
    TEAM_HUDDLE = "team_huddle"
    TEAM_MEMBER = "team_member"


class ConversationStatus(StrEnum):
    ACTIVE = "active"


class MessageActorType(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ToolEventType(StrEnum):
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"


class ArtifactKind(StrEnum):
    DOCUMENT = "document"
    GITHUB_EXPORT = "github_export"


class WorkspaceItemKind(StrEnum):
    FILE = "file"
    DIRECTORY = "directory"


class TeamTaskStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLAIMED = "claimed"
    COMPLETED = "completed"


class TeamTaskSource(StrEnum):
    HUDDLE = "huddle"


class TeamTaskUpdateType(StrEnum):
    REPORTED = "reported"
    MESSAGE = "message"
    COMPLETED = "completed"
    DELEGATED = "delegated"
    CLAIMED = "claimed"
    RELEASED = "released"
    REOPENED = "reopened"


class SecretScope(StrEnum):
    USER = "user"
    TEAM = "team"
    AGENT = "agent"


class GitHubAccountType(StrEnum):
    USER = "user"
    ORGANIZATION = "organization"


class RuntimeLeaseState(StrEnum):
    PROVISIONING = "provisioning"
    RUNNING = "running"
    UNREACHABLE = "unreachable"


class PollerLeaseState(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
