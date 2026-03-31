from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlmodel import Session, select

from sutra_backend.models import Agent, Artifact, RoleTemplate, SharedWorkspaceItem, Team, User, utcnow
from sutra_backend.services.bootstrap import ensure_role_templates


class TeamServiceError(RuntimeError):
    """Raised when a requested team operation cannot be completed."""


@dataclass(frozen=True)
class TeamCreationSpec:
    role_template_key: str
    name: str | None = None


@dataclass(frozen=True)
class TeamCreationResult:
    team: Team
    agents: list[Agent]


@dataclass(frozen=True)
class TeamWorkspaceResult:
    team: Team
    items: list[SharedWorkspaceItem]


@dataclass(frozen=True)
class TeamArtifactResult:
    team: Team
    items: list[Artifact]


def list_role_templates(session: Session) -> list[RoleTemplate]:
    ensure_role_templates(session)
    return session.exec(select(RoleTemplate).order_by(RoleTemplate.name.asc())).all()


def create_team_with_agents(
    session: Session,
    *,
    user: User,
    name: str,
    description: str | None,
    agents: list[TeamCreationSpec],
) -> TeamCreationResult:
    ensure_role_templates(session)

    normalized_name = name.strip()
    if not normalized_name:
        raise TeamServiceError("Team name is required.")
    if not agents:
        raise TeamServiceError("At least one role is required to create a team.")

    requested_keys = [item.role_template_key.strip() for item in agents]
    if any(not key for key in requested_keys):
        raise TeamServiceError("Each team role must reference a valid role template key.")
    if len(set(requested_keys)) != len(requested_keys):
        raise TeamServiceError("Each team role must be distinct.")

    templates = session.exec(
        select(RoleTemplate).where(RoleTemplate.key.in_(requested_keys))
    ).all()
    templates_by_key = {template.key: template for template in templates}
    missing = [key for key in requested_keys if key not in templates_by_key]
    if missing:
        raise TeamServiceError(
            "Unknown role templates requested: " + ", ".join(sorted(missing))
        )

    team = Team(
        user_id=user.id,
        name=normalized_name,
        description=description.strip() if description else None,
        mode="team",
    )
    session.add(team)
    session.commit()
    session.refresh(team)

    team.shared_workspace_uri = f"workspace://teams/{team.id}"
    session.add(team)

    created_agents: list[Agent] = []
    for spec in agents:
        template = templates_by_key[spec.role_template_key]
        agent = Agent(
            team_id=team.id,
            role_template_id=template.id,
            name=(spec.name.strip() if spec.name else f"{template.name} Agent"),
            role_name=template.name,
            status="provisioning",
            shared_workspace_enabled=True,
        )
        session.add(agent)
        created_agents.append(agent)

    workspace_items = [
        SharedWorkspaceItem(
            team_id=team.id,
            path="README.md",
            kind="file",
            size_bytes=160,
        ),
        SharedWorkspaceItem(
            team_id=team.id,
            path="artifacts",
            kind="directory",
        ),
        SharedWorkspaceItem(
            team_id=team.id,
            path="research",
            kind="directory",
        ),
    ]
    for item in workspace_items:
        session.add(item)

    session.commit()
    session.refresh(team)
    for agent in created_agents:
        session.refresh(agent)

    return TeamCreationResult(team=team, agents=created_agents)


def read_team_workspace(
    session: Session,
    *,
    user: User,
    team_id: UUID,
) -> TeamWorkspaceResult:
    team = session.exec(
        select(Team).where(Team.id == team_id).where(Team.user_id == user.id)
    ).first()
    if team is None:
        raise TeamServiceError("Team not found.")

    items = session.exec(
        select(SharedWorkspaceItem)
        .where(SharedWorkspaceItem.team_id == team.id)
        .order_by(SharedWorkspaceItem.kind.asc(), SharedWorkspaceItem.path.asc())
    ).all()
    return TeamWorkspaceResult(team=team, items=items)


def list_team_artifacts(
    session: Session,
    *,
    user: User,
    team_id: UUID,
) -> TeamArtifactResult:
    team = session.exec(
        select(Team).where(Team.id == team_id).where(Team.user_id == user.id)
    ).first()
    if team is None:
        raise TeamServiceError("Team not found.")

    items = session.exec(
        select(Artifact)
        .where(Artifact.team_id == team.id)
        .order_by(Artifact.created_at.desc())
    ).all()
    return TeamArtifactResult(team=team, items=items)


def upsert_workspace_item(
    session: Session,
    *,
    user: User,
    team_id: UUID,
    path: str,
    kind: str,
    content_text: str | None,
    conversation_id: UUID | None = None,
    agent_id: UUID | None = None,
) -> SharedWorkspaceItem:
    team = session.exec(
        select(Team).where(Team.id == team_id).where(Team.user_id == user.id)
    ).first()
    if team is None:
        raise TeamServiceError("Team not found.")

    normalized_path = path.strip().strip("/")
    if not normalized_path:
        raise TeamServiceError("Workspace path is required.")

    item = session.exec(
        select(SharedWorkspaceItem)
        .where(SharedWorkspaceItem.team_id == team.id)
        .where(SharedWorkspaceItem.path == normalized_path)
    ).first()

    size_bytes = len(content_text.encode("utf-8")) if content_text is not None else None
    if item is None:
        item = SharedWorkspaceItem(
            team_id=team.id,
            path=normalized_path,
            kind=kind,
            content_text=content_text,
            size_bytes=size_bytes,
            conversation_id=conversation_id,
            agent_id=agent_id,
        )
        session.add(item)
    else:
        item.kind = kind
        item.content_text = content_text
        item.size_bytes = size_bytes
        item.conversation_id = conversation_id
        item.agent_id = agent_id
        item.updated_at = utcnow()
        session.add(item)

    session.commit()
    session.refresh(item)
    return item
