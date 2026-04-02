from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import timedelta, timezone
from uuid import UUID, uuid4
from re import sub as re_sub

from sqlmodel import Session, select

from sutra_backend.config import Settings
from sutra_backend.models import (
    Agent,
    AgentTeam,
    Conversation,
    Message,
    RoleTemplate,
    SharedWorkspaceItem,
    TeamTask,
    TeamTaskUpdate,
    User,
    utcnow,
)
from sutra_backend.runtime.client import HermesRuntimeClient, ResponsesRequest
from sutra_backend.runtime.errors import RuntimeNotReadyError
from sutra_backend.runtime.provisioning import ensure_agent_runtime_lease
from sutra_backend.services.agent_teams import (
    get_owned_agent as find_owned_agent,
    get_owned_team as find_owned_team,
    get_team_assignment,
    list_team_agents,
)
from sutra_backend.services.runtime import AgentNotFoundError, build_runtime_target
from sutra_backend.services.runtime_leases import reconcile_runtime_lease
from sutra_backend.services.secrets import resolve_secret_env
from sutra_backend.services.teams import upsert_workspace_item

TASK_CLAIM_LEASE_SECONDS = 300
WORKSPACE_CONTEXT_ITEM_LIMIT = 3
WORKSPACE_CONTEXT_CHARS = 600
HUDDLE_PLAN_CONTEXT_CHARS = 1200


@dataclass(frozen=True)
class TeamMemberResponse:
    agent: Agent
    response_id: str
    output_text: str


@dataclass(frozen=True)
class TeamResponseResult:
    conversation: Conversation
    outputs: list[TeamMemberResponse]
    workspace_item_id: UUID | None
    generated_items: list[SharedWorkspaceItem]


@dataclass(frozen=True)
class TeamHuddleResult:
    conversation: Conversation
    outputs: list[TeamMemberResponse]
    tasks: list[TeamTask]
    workspace_item_id: UUID | None


@dataclass(frozen=True)
class AgentInboxRunResult:
    task: TeamTask | None
    conversation: Conversation | None
    response_id: str | None
    output_text: str | None
    workspace_item_id: UUID | None


@dataclass(frozen=True)
class TeamInboxCycleResult:
    agent: Agent
    task: TeamTask | None
    conversation: Conversation | None
    response_id: str | None
    output_text: str | None
    workspace_item_id: UUID | None


class TeamTaskClaimError(RuntimeError):
    """Raised when a task cannot be safely claimed for execution."""


class TeamTaskActionError(RuntimeError):
    """Raised when a task action cannot be completed safely."""


def _build_team_runtime_conversation_name(
    *,
    mode: str,
    conversation: Conversation,
    agent: Agent,
    task: TeamTask | None = None,
) -> str:
    if task is not None:
        return f"{mode}:team:{conversation.agent_team_id}:task:{task.id}:agent:{agent.id}"
    return f"{mode}:team:{conversation.agent_team_id}:conversation:{conversation.id}:agent:{agent.id}"


def _serialize_user_input(raw_input: str | list[dict[str, object]]) -> str:
    if isinstance(raw_input, str):
        return raw_input
    return json.dumps(raw_input, separators=(",", ":"), sort_keys=True)


def _truncate_context(text: str, *, limit: int) -> str:
    normalized = text.strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[: max(limit - 16, 0)].rstrip() + "\n...[truncated]"


def get_owned_team(session: Session, *, team_id: UUID, user: User) -> AgentTeam:
    team = find_owned_team(session, team_id=team_id, user=user)
    if team is None:
        raise AgentNotFoundError("Team not found.")
    return team


def get_or_create_team_conversation(
    session: Session,
    *,
    team: AgentTeam,
    conversation_id: UUID | None,
) -> Conversation:
    if conversation_id is not None:
        conversation = session.exec(
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .where(Conversation.agent_team_id == team.id)
            .where(Conversation.mode == "team")
        ).first()
        if conversation is None:
            raise AgentNotFoundError("Conversation not found.")
        return conversation

    conversation = Conversation(agent_team_id=team.id, mode="team")
    session.add(conversation)
    session.commit()
    session.refresh(conversation)
    return conversation


def get_or_create_team_huddle_conversation(
    session: Session,
    *,
    team: AgentTeam,
    conversation_id: UUID | None,
) -> Conversation:
    if conversation_id is not None:
        conversation = session.exec(
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .where(Conversation.agent_team_id == team.id)
            .where(Conversation.mode == "team_huddle")
        ).first()
        if conversation is None:
            raise AgentNotFoundError("Huddle not found.")
        return conversation

    conversation = Conversation(agent_team_id=team.id, mode="team_huddle")
    session.add(conversation)
    session.commit()
    session.refresh(conversation)
    return conversation


def list_team_tasks(
    session: Session,
    *,
    user: User,
    team_id: UUID,
) -> list[TeamTask]:
    team = get_owned_team(session, team_id=team_id, user=user)
    recover_expired_team_task_claims(session, user=user, team_id=team.id)
    return session.exec(
        select(TeamTask)
        .where(TeamTask.team_id == team.id)
        .order_by(TeamTask.status.asc(), TeamTask.created_at.desc())
    ).all()


def list_agent_inbox_tasks(
    session: Session,
    *,
    user: User,
    agent_id: UUID,
) -> list[TeamTask]:
    agent = find_owned_agent(session, agent_id=agent_id, user=user)
    if agent is None:
        raise AgentNotFoundError("Agent not found.")

    assigned_tasks = session.exec(
        select(TeamTask)
        .where(TeamTask.assigned_agent_id == agent.id)
        .order_by(TeamTask.created_at.asc())
    ).all()
    for team_id in {task.team_id for task in assigned_tasks}:
        recover_expired_team_task_claims(session, user=user, team_id=team_id)

    return session.exec(
        select(TeamTask)
        .where(TeamTask.assigned_agent_id == agent.id)
        .order_by(TeamTask.status.asc(), TeamTask.created_at.desc())
    ).all()


def _get_owned_agent(
    session: Session,
    *,
    agent_id: UUID,
    user: User,
) -> Agent:
    agent = find_owned_agent(session, agent_id=agent_id, user=user)
    if agent is None:
        raise AgentNotFoundError("Agent not found.")
    return agent


def _get_owned_task(
    session: Session,
    *,
    task_id: UUID,
    user: User,
) -> TeamTask:
    task = session.exec(
        select(TeamTask)
        .join(AgentTeam, AgentTeam.id == TeamTask.team_id)
        .where(TeamTask.id == task_id)
        .where(AgentTeam.user_id == user.id)
    ).first()
    if task is None:
        raise AgentNotFoundError("Task not found.")
    return task


def list_task_updates(
    session: Session,
    *,
    user: User,
    task_id: UUID,
) -> list[TeamTaskUpdate]:
    task = _get_owned_task(session, task_id=task_id, user=user)
    return session.exec(
        select(TeamTaskUpdate)
        .where(TeamTaskUpdate.task_id == task.id)
        .order_by(TeamTaskUpdate.created_at.asc())
    ).all()


def _load_team_agents_and_templates(
    session: Session,
    *,
    team: AgentTeam,
) -> tuple[list[Agent], dict[UUID, RoleTemplate]]:
    agents = list_team_agents(session, team_id=team.id)
    if not agents:
        raise AgentNotFoundError("Team does not have any agents.")

    templates = session.exec(
        select(RoleTemplate).where(
            RoleTemplate.id.in_(
                [agent.role_template_id for agent in agents if agent.role_template_id is not None]
            )
        )
    ).all()
    return agents, {template.id: template for template in templates}


def _load_role_template_for_agent(
    session: Session,
    *,
    agent: Agent,
) -> RoleTemplate | None:
    if agent.role_template_id is None:
        return None
    return session.exec(
        select(RoleTemplate).where(RoleTemplate.id == agent.role_template_id)
    ).first()


def _build_agent_huddle_input(
    *,
    team: AgentTeam,
    user_input: str | list[dict[str, object]],
    prior_outputs: list[TeamMemberResponse],
) -> str:
    serialized_input = _serialize_user_input(user_input)
    if not prior_outputs:
        return (
            f"Team: {team.name}\n"
            f"Goal:\n{serialized_input}\n\n"
            "Respond with your role's proposed approach, what you need from teammates, "
            "and the concrete piece of work you should own."
        )

    prior_text = "\n\n".join(
        f"{item.agent.name} ({item.agent.role_name}):\n{item.output_text}"
        for item in prior_outputs
    )
    return (
        f"Team: {team.name}\n"
        f"Goal:\n{serialized_input}\n\n"
        f"Prior huddle notes:\n{prior_text}\n\n"
        "Add your role's plan, dependencies, and the concrete task you should own."
    )


def _build_agent_team_input(
    *,
    team: AgentTeam,
    user_input: str | list[dict[str, object]],
    prior_outputs: list[TeamMemberResponse],
    assigned_task: TeamTask | None,
    huddle_plan_text: str | None,
    workspace_items: list[SharedWorkspaceItem],
) -> str | list[dict[str, object]]:
    serialized_input = _serialize_user_input(user_input)
    sections = [
        f"Team: {team.name}",
        "",
        "User request:",
        serialized_input,
    ]
    if huddle_plan_text:
        sections.extend(
            [
                "",
                "Shared plan:",
                _truncate_context(huddle_plan_text, limit=HUDDLE_PLAN_CONTEXT_CHARS),
            ]
        )
    if assigned_task is not None:
        sections.extend(
            [
                "",
                "Assigned task:",
                assigned_task.instruction,
            ]
        )
    if workspace_items:
        sections.extend(
            [
                "",
                "Recent shared workspace context:",
                _format_workspace_context(workspace_items),
            ]
        )
    if prior_outputs:
        prior_text = "\n\n".join(
            f"{item.agent.name} ({item.agent.role_name}):\n{item.output_text}"
            for item in prior_outputs
        )
        sections.extend(
            [
                "",
                "Previous teammate outputs:",
                prior_text,
                "",
                "Build on the prior outputs from your role and complete your assigned task.",
            ]
        )
    elif assigned_task is not None:
        sections.extend(
            [
                "",
                "Complete your assigned task and produce output the shared workspace can keep.",
            ]
        )
    return "\n".join(sections)


def _build_agent_inbox_task_input(
    *,
    team: AgentTeam,
    task: TeamTask,
    updates: list[TeamTaskUpdate],
    update_agents: dict[UUID, Agent],
    huddle_plan_text: str | None,
    workspace_items: list[SharedWorkspaceItem],
) -> str:
    sections = [
        f"Team: {team.name}",
        "",
        f"Task: {task.title}",
        "",
        "Assigned task:",
        task.instruction,
    ]
    if huddle_plan_text:
        sections.extend(
            [
                "",
                "Shared plan:",
                _truncate_context(huddle_plan_text, limit=HUDDLE_PLAN_CONTEXT_CHARS),
            ]
        )
    if updates:
        update_text = "\n\n".join(
            _format_task_update(update, agents_by_id=update_agents) for update in updates
        )
        sections.extend(
            [
                "",
                "Task updates so far:",
                update_text,
            ]
        )
    if workspace_items:
        sections.extend(
            [
                "",
                "Recent shared workspace context:",
                _format_workspace_context(workspace_items),
            ]
        )
    sections.extend(
        [
            "",
            "Complete this inbox task and return a concrete result the team can keep.",
        ]
    )
    return "\n".join(sections)


def _build_agent_instructions(
    *,
    team: AgentTeam,
    role_template: RoleTemplate | None,
    override: str | None,
) -> str:
    parts = []
    if role_template is not None:
        parts.append(role_template.default_system_prompt)
    parts.append(
        f"You are collaborating as part of the Sutra team '{team.name}'. "
        "Stay within your role and produce actionable output that the shared workspace can keep."
    )
    if override:
        parts.append(override)
    return "\n\n".join(parts)


def _build_agent_huddle_instructions(
    *,
    team: AgentTeam,
    role_template: RoleTemplate | None,
    override: str | None,
) -> str:
    parts = []
    if role_template is not None:
        parts.append(role_template.default_system_prompt)
    parts.append(
        f"You are in a short planning huddle for the Sutra team '{team.name}'. "
        "Do not execute the task yet. Align on approach, dependencies, and your owned task."
    )
    if override:
        parts.append(override)
    return "\n\n".join(parts)


def _build_agent_inbox_instructions(
    *,
    team: AgentTeam,
    role_template: RoleTemplate | None,
) -> str:
    parts = []
    if role_template is not None:
        parts.append(role_template.default_system_prompt)
    parts.append(
        f"You are executing an inbox task for the Sutra team '{team.name}'. "
        "Use your role, complete the assignment, and produce a durable result."
    )
    return "\n\n".join(parts)


def _workspace_summary_path(conversation_id: UUID) -> str:
    return f"conversations/{conversation_id}/team-summary.md"


def _workspace_huddle_plan_path(conversation_id: UUID) -> str:
    return f"huddles/{conversation_id}/plan.md"


def _workspace_task_output_path(task_id: UUID) -> str:
    return f"tasks/{task_id}/output.md"


def _workspace_team_agent_output_path(
    conversation_id: UUID,
    *,
    agent: Agent,
) -> str:
    slug = re_sub(r"[^a-z0-9]+", "-", agent.role_name.lower()).strip("-") or "agent"
    return f"conversations/{conversation_id}/{slug}.md"


def _load_huddle_plan_item(
    session: Session,
    *,
    team: AgentTeam,
    conversation_id: UUID | None,
) -> SharedWorkspaceItem | None:
    statement = (
        select(SharedWorkspaceItem)
        .where(SharedWorkspaceItem.team_id == team.id)
        .where(SharedWorkspaceItem.kind == "file")
        .order_by(SharedWorkspaceItem.updated_at.desc())
    )
    if conversation_id is not None:
        statement = statement.where(SharedWorkspaceItem.path == _workspace_huddle_plan_path(conversation_id))
    else:
        statement = statement.where(SharedWorkspaceItem.path.like("huddles/%/plan.md"))
    return session.exec(statement).first()


def _load_recent_workspace_context(
    session: Session,
    *,
    team: AgentTeam,
    exclude_paths: set[str] | None = None,
    preferred_prefixes: list[str] | None = None,
    limit: int = WORKSPACE_CONTEXT_ITEM_LIMIT,
) -> list[SharedWorkspaceItem]:
    excluded = exclude_paths or set()
    items = session.exec(
        select(SharedWorkspaceItem)
        .where(SharedWorkspaceItem.team_id == team.id)
        .where(SharedWorkspaceItem.kind == "file")
        .where(SharedWorkspaceItem.content_text.is_not(None))
        .order_by(SharedWorkspaceItem.updated_at.desc())
    ).all()
    filtered = [item for item in items if item.content_text and item.path not in excluded]
    if not preferred_prefixes:
        return filtered[:limit]

    preferred: list[SharedWorkspaceItem] = []
    remaining: list[SharedWorkspaceItem] = []
    seen_item_ids: set[UUID] = set()
    for prefix in preferred_prefixes:
        for item in filtered:
            if item.id in seen_item_ids:
                continue
            if item.path.startswith(prefix):
                preferred.append(item)
                seen_item_ids.add(item.id)
    for item in filtered:
        if item.id in seen_item_ids:
            continue
        remaining.append(item)
    return (preferred + remaining)[:limit]


def _load_conversation_workspace_prefixes(
    session: Session,
    *,
    team: AgentTeam,
    conversation: Conversation,
) -> list[str]:
    prefixes: list[str] = []
    conversation_tasks = session.exec(
        select(TeamTask)
        .where(TeamTask.team_id == team.id)
        .where(TeamTask.conversation_id == conversation.id)
        .order_by(TeamTask.created_at.asc())
    ).all()
    recent_team_tasks = session.exec(
        select(TeamTask)
        .where(TeamTask.team_id == team.id)
        .order_by(TeamTask.updated_at.desc(), TeamTask.created_at.desc())
    ).all()
    task_ids = []
    seen_task_ids: set[UUID] = set()
    for task in [*conversation_tasks, *recent_team_tasks]:
        if task.id in seen_task_ids:
            continue
        seen_task_ids.add(task.id)
        task_ids.append(task.id)
    prefixes.extend(f"tasks/{task_id}/" for task_id in task_ids)
    prefixes.append(f"conversations/{conversation.id}/")
    return prefixes


def _format_workspace_context(items: list[SharedWorkspaceItem]) -> str:
    sections: list[str] = []
    for item in items:
        sections.extend(
            [
                f"{item.path}:",
                _truncate_context(item.content_text or "", limit=WORKSPACE_CONTEXT_CHARS),
            ]
        )
    return "\n\n".join(sections)


def _load_team_agent_map(
    session: Session,
    *,
    team: AgentTeam,
) -> dict[UUID, Agent]:
    agents = list_team_agents(session, team_id=team.id)
    return {agent.id: agent for agent in agents}


def _format_task_update(
    update: TeamTaskUpdate,
    *,
    agents_by_id: dict[UUID, Agent],
) -> str:
    event_label = update.event_type.replace("_", " ").title()
    if update.agent_id is not None:
        agent = agents_by_id.get(update.agent_id)
        if agent is not None:
            event_label = f"{event_label} ({agent.name})"
    return f"{event_label}:\n{update.content}"


def _build_workspace_summary(
    *,
    team: AgentTeam,
    user_input: str | list[dict[str, object]],
    outputs: list[TeamMemberResponse],
) -> str:
    request_text = _serialize_user_input(user_input)
    sections = [
        f"# {team.name} Team Summary",
        "",
        "## User Request",
        request_text,
        "",
        "## Agent Outputs",
    ]
    for output in outputs:
        sections.extend(
            [
                "",
                f"### {output.agent.name} ({output.agent.role_name})",
                output.output_text,
            ]
        )
    return "\n".join(sections).strip() + "\n"


def _build_workspace_huddle_plan(
    *,
    team: AgentTeam,
    user_input: str | list[dict[str, object]],
    outputs: list[TeamMemberResponse],
    tasks: list[TeamTask],
) -> str:
    request_text = _serialize_user_input(user_input)
    task_map = {task.assigned_agent_id: task for task in tasks}
    sections = [
        f"# {team.name} Huddle Plan",
        "",
        "## Goal",
        request_text,
        "",
        "## Alignment Notes",
    ]
    for output in outputs:
        sections.extend(
            [
                "",
                f"### {output.agent.name} ({output.agent.role_name})",
                output.output_text,
            ]
        )
        task = task_map.get(output.agent.id)
        if task is not None:
            sections.extend(
                [
                    "",
                    f"Assigned Task: {task.title}",
                    task.instruction,
                ]
            )
    return "\n".join(sections).strip() + "\n"


def _build_workspace_task_output(
    *,
    team: AgentTeam,
    agent: Agent,
    task: TeamTask,
    output_text: str,
) -> str:
    sections = [
        f"# {team.name} Task Output",
        "",
        f"## Agent",
        f"{agent.name} ({agent.role_name})",
        "",
        "## Task",
        task.title,
        "",
        "## Assignment",
        task.instruction,
        "",
        "## Result",
        output_text,
    ]
    return "\n".join(sections).strip() + "\n"


def _build_workspace_team_agent_output(
    *,
    team: AgentTeam,
    agent: Agent,
    user_input: str | list[dict[str, object]],
    assigned_task: TeamTask | None,
    output_text: str,
) -> str:
    sections = [
        f"# {team.name} Agent Output",
        "",
        "## Agent",
        f"{agent.name} ({agent.role_name})",
        "",
        "## User Request",
        _serialize_user_input(user_input),
    ]
    if assigned_task is not None:
        sections.extend(
            [
                "",
                "## Task",
                assigned_task.title,
                "",
                "## Assignment",
                assigned_task.instruction,
            ]
        )
    sections.extend(
        [
            "",
            "## Result",
            output_text,
        ]
    )
    return "\n".join(sections).strip() + "\n"


def _upsert_task_for_agent(
    session: Session,
    *,
    team: AgentTeam,
    conversation: Conversation,
    agent: Agent,
    instruction: str,
) -> TeamTask:
    title = f"{agent.role_name} Task"
    existing = session.exec(
        select(TeamTask)
        .where(TeamTask.team_id == team.id)
        .where(TeamTask.conversation_id == conversation.id)
        .where(TeamTask.assigned_agent_id == agent.id)
    ).first()
    if existing is None:
        task = TeamTask(
            team_id=team.id,
            conversation_id=conversation.id,
            assigned_agent_id=agent.id,
            title=title,
            instruction=instruction,
            status="open",
            source="huddle",
        )
        session.add(task)
        session.commit()
        session.refresh(task)
        return task

    existing.title = title
    existing.instruction = instruction
    existing.status = "open"
    existing.claim_token = None
    existing.claimed_at = None
    existing.claim_expires_at = None
    existing.completed_at = None
    existing.updated_at = utcnow()
    session.add(existing)
    session.commit()
    session.refresh(existing)
    return existing


def _append_task_update(
    session: Session,
    *,
    task: TeamTask,
    event_type: str,
    content: str,
    agent_id: UUID | None = None,
) -> TeamTaskUpdate:
    update = TeamTaskUpdate(
        task_id=task.id,
        team_id=task.team_id,
        agent_id=agent_id,
        event_type=event_type,
        content=content,
    )
    session.add(update)
    session.commit()
    session.refresh(update)
    return update


def _task_claim_expired(task: TeamTask, *, now) -> bool:
    if task.claim_expires_at is None:
        return False
    claim_expires_at = task.claim_expires_at
    if claim_expires_at.tzinfo is None:
        claim_expires_at = claim_expires_at.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return claim_expires_at <= now


def _reopen_expired_task_claim(
    session: Session,
    *,
    task: TeamTask,
    now,
    reason: str = "Task claim expired and the task returned to the inbox.",
) -> TeamTask:
    task.status = "open"
    task.claim_token = None
    task.claimed_at = None
    task.claim_expires_at = None
    task.updated_at = now
    session.add(task)
    session.commit()
    session.refresh(task)
    _append_task_update(
        session,
        task=task,
        event_type="reopened",
        content=reason,
        agent_id=task.assigned_agent_id,
    )
    return task


def recover_expired_team_task_claims(
    session: Session,
    *,
    user: User,
    team_id: UUID,
) -> list[TeamTask]:
    team = get_owned_team(session, team_id=team_id, user=user)
    now = utcnow()
    expired_tasks = session.exec(
        select(TeamTask)
        .where(TeamTask.team_id == team.id)
        .where(TeamTask.status == "claimed")
        .where(TeamTask.claim_expires_at.is_not(None))
        .order_by(TeamTask.created_at.asc())
    ).all()
    reopened: list[TeamTask] = []
    for task in expired_tasks:
        if _task_claim_expired(task, now=now):
            reopened.append(_reopen_expired_task_claim(session, task=task, now=now))
    return reopened


def _claim_task_for_execution(
    session: Session,
    *,
    task: TeamTask,
    claim_token: str,
    lease_seconds: int = TASK_CLAIM_LEASE_SECONDS,
    event_content: str | None = None,
) -> TeamTask:
    now = utcnow()
    if task.status == "completed":
        raise TeamTaskClaimError("Task is already completed.")
    if task.status == "claimed" and task.claim_token not in (None, claim_token):
        if not _task_claim_expired(task, now=now):
            raise TeamTaskClaimError("Task is already claimed by another run.")

    task.status = "claimed"
    task.claim_token = claim_token
    task.claimed_at = now
    task.claim_expires_at = now + timedelta(seconds=lease_seconds)
    task.updated_at = now
    session.add(task)
    session.commit()
    session.refresh(task)
    if event_content:
        _append_task_update(
            session,
            task=task,
            event_type="claimed",
            content=event_content,
            agent_id=task.assigned_agent_id,
        )
    return task


def _complete_task_claim(
    session: Session,
    *,
    task: TeamTask,
    claim_token: str,
    completion_content: str | None = None,
) -> TeamTask:
    if task.claim_token not in (None, claim_token):
        raise TeamTaskClaimError("Task claim is owned by another run.")

    now = utcnow()
    task.status = "completed"
    task.claim_token = None
    task.claimed_at = None
    task.claim_expires_at = None
    task.completed_at = now
    task.updated_at = now
    session.add(task)
    session.commit()
    session.refresh(task)
    if completion_content:
        _append_task_update(
            session,
            task=task,
            event_type="completed",
            content=completion_content,
            agent_id=task.assigned_agent_id,
        )
    return task


def _release_task_claim(
    session: Session,
    *,
    task: TeamTask,
    claim_token: str,
    reason: str,
) -> TeamTask:
    if task.claim_token != claim_token or task.status != "claimed":
        return task

    now = utcnow()
    task.status = "open"
    task.claim_token = None
    task.claimed_at = None
    task.claim_expires_at = None
    task.updated_at = now
    session.add(task)
    session.commit()
    session.refresh(task)
    _append_task_update(
        session,
        task=task,
        event_type="released",
        content=reason,
        agent_id=task.assigned_agent_id,
    )
    return task


def delegate_task(
    session: Session,
    *,
    user: User,
    task_id: UUID,
    assigned_agent_id: UUID,
    note: str | None,
) -> TeamTask:
    task = _get_owned_task(session, task_id=task_id, user=user)
    if task.status == "completed":
        raise TeamTaskActionError("Completed tasks cannot be delegated.")

    agent = session.get(Agent, assigned_agent_id)
    if agent is not None and get_team_assignment(session, team_id=task.team_id, agent_id=agent.id) is None:
        agent = None
    if agent is None:
        raise TeamTaskActionError("Assigned agent must belong to the same team.")

    task.assigned_agent_id = agent.id
    task.status = "open"
    task.claim_token = None
    task.claimed_at = None
    task.claim_expires_at = None
    task.updated_at = utcnow()
    session.add(task)
    session.commit()
    session.refresh(task)

    summary = note.strip() if note else f"Task delegated to {agent.name}."
    _append_task_update(
        session,
        task=task,
        event_type="delegated",
        content=summary,
        agent_id=agent.id,
    )
    return task


def create_task_report(
    session: Session,
    *,
    user: User,
    task_id: UUID,
    content: str,
    agent_id: UUID | None,
) -> TeamTask:
    task = _get_owned_task(session, task_id=task_id, user=user)
    if task.status == "completed":
        raise TeamTaskActionError("Completed tasks cannot accept new reports.")

    normalized_content = content.strip()
    if not normalized_content:
        raise TeamTaskActionError("Report content is required.")

    report_agent_id = agent_id
    if report_agent_id is not None:
        agent = session.get(Agent, report_agent_id)
        if agent is not None and get_team_assignment(session, team_id=task.team_id, agent_id=agent.id) is None:
            agent = None
        if agent is None:
            raise TeamTaskActionError("Report agent must belong to the same team.")

    if task.status == "open":
        task.status = "in_progress"
        task.updated_at = utcnow()
        session.add(task)
        session.commit()
        session.refresh(task)

    _append_task_update(
        session,
        task=task,
        event_type="reported",
        content=normalized_content,
        agent_id=report_agent_id,
    )
    return task


def create_task_message(
    session: Session,
    *,
    user: User,
    task_id: UUID,
    content: str,
    agent_id: UUID | None,
) -> TeamTask:
    task = _get_owned_task(session, task_id=task_id, user=user)
    if task.status == "completed":
        raise TeamTaskActionError("Completed tasks cannot receive new messages.")

    normalized_content = content.strip()
    if not normalized_content:
        raise TeamTaskActionError("Message content is required.")

    message_agent_id = agent_id
    if message_agent_id is not None:
        agent = session.get(Agent, message_agent_id)
        if agent is not None and get_team_assignment(session, team_id=task.team_id, agent_id=agent.id) is None:
            agent = None
        if agent is None:
            raise TeamTaskActionError("Message agent must belong to the same team.")

    _append_task_update(
        session,
        task=task,
        event_type="message",
        content=normalized_content,
        agent_id=message_agent_id,
    )
    return task


def claim_next_agent_inbox_task(
    session: Session,
    *,
    user: User,
    agent_id: UUID,
) -> TeamTask | None:
    agent = _get_owned_agent(session, agent_id=agent_id, user=user)
    now = utcnow()
    tasks = session.exec(
        select(TeamTask)
        .where(TeamTask.assigned_agent_id == agent.id)
        .order_by(TeamTask.created_at.asc())
    ).all()

    for task in tasks:
        if task.status == "completed":
            continue
        if task.status == "claimed":
            if not _task_claim_expired(task, now=now):
                continue
            task = _reopen_expired_task_claim(
                session,
                task=task,
                now=now,
                reason=f"{agent.name}'s previous claim expired and the task returned to the inbox.",
            )
        return _claim_task_for_execution(
            session,
            task=task,
            claim_token=f"agent-inbox:{agent.id}:{uuid4()}",
            event_content=f"{agent.name} picked up the task from the inbox.",
        )
    return None


async def run_next_agent_inbox_task(
    session: Session,
    *,
    user: User,
    agent_id: UUID,
    settings: Settings,
) -> AgentInboxRunResult:
    agent = _get_owned_agent(session, agent_id=agent_id, user=user)
    task = claim_next_agent_inbox_task(session, user=user, agent_id=agent.id)
    if task is None:
        return AgentInboxRunResult(
            task=None,
            conversation=None,
            response_id=None,
            output_text=None,
            workspace_item_id=None,
        )

    team = get_owned_team(session, team_id=task.team_id, user=user)
    role_template = _load_role_template_for_agent(session, agent=agent)
    updates = list_task_updates(session, user=user, task_id=task.id)
    update_agents = _load_team_agent_map(session, team=team)
    huddle_plan = _load_huddle_plan_item(session, team=team, conversation_id=task.conversation_id)
    workspace_items = _load_recent_workspace_context(
        session,
        team=team,
        exclude_paths={huddle_plan.path} if huddle_plan is not None else None,
    )
    ensure_agent_runtime_lease(session, agent=agent, settings=settings)
    lease_status = reconcile_runtime_lease(
        session,
        user=user,
        agent_id=agent.id,
        settings=settings,
    )
    if not lease_status.ready:
        raise RuntimeNotReadyError(lease_status.readiness_reason)
    runtime_client = HermesRuntimeClient(
        target=build_runtime_target(lease=lease_status.lease, settings=settings),
        timeout_seconds=settings.hermes_api_route_timeout_seconds,
    )

    conversation = Conversation(agent_team_id=team.id, agent_id=agent.id, mode="team_member")
    session.add(conversation)
    session.commit()
    session.refresh(conversation)

    session.add(
        Message(
            conversation_id=conversation.id,
            actor_type="system",
            content=task.instruction,
        )
    )
    session.commit()

    try:
        runtime_response = await runtime_client.create_response(
            ResponsesRequest(
                input=_build_agent_inbox_task_input(
                    team=team,
                    task=task,
                    updates=updates,
                    update_agents=update_agents,
                    huddle_plan_text=huddle_plan.content_text if huddle_plan is not None else None,
                    workspace_items=workspace_items,
                ),
                instructions=_build_agent_inbox_instructions(
                    team=team,
                    role_template=role_template,
                ),
                conversation=_build_team_runtime_conversation_name(
                    mode="agent_task",
                    conversation=conversation,
                    agent=agent,
                    task=task,
                ),
            )
        )
    except Exception:
        _release_task_claim(
            session,
            task=task,
            claim_token=task.claim_token or "",
            reason="Inbox execution failed before completion; the task returned to the queue.",
        )
        raise

    session.add(
        Message(
            conversation_id=conversation.id,
            actor_type="assistant",
            actor_id=agent.id,
            content=runtime_response.output_text,
            response_chain_id=runtime_response.response_id,
        )
    )
    conversation.latest_response_id = runtime_response.response_id
    conversation.updated_at = utcnow()
    session.add(conversation)
    session.commit()
    session.refresh(conversation)

    workspace_item = upsert_workspace_item(
        session,
        user=user,
        team_id=team.id,
        path=_workspace_task_output_path(task.id),
        kind="file",
        content_text=_build_workspace_task_output(
            team=team,
            agent=agent,
            task=task,
            output_text=runtime_response.output_text,
        ),
        conversation_id=conversation.id,
        agent_id=agent.id,
    )

    task = complete_task(
        session,
        user=user,
        task_id=task.id,
        content=runtime_response.output_text,
        agent_id=agent.id,
        claim_token=task.claim_token,
    )

    return AgentInboxRunResult(
        task=task,
        conversation=conversation,
        response_id=runtime_response.response_id,
        output_text=runtime_response.output_text,
        workspace_item_id=workspace_item.id,
    )


async def run_team_inbox_cycle(
    session: Session,
    *,
    user: User,
    team_id: UUID,
    settings: Settings,
    max_tasks: int | None = None,
) -> list[TeamInboxCycleResult]:
    team = get_owned_team(session, team_id=team_id, user=user)
    recover_expired_team_task_claims(session, user=user, team_id=team.id)
    agents, _templates = _load_team_agents_and_templates(session, team=team)

    results: list[TeamInboxCycleResult] = []
    executed_count = 0
    for agent in agents:
        if max_tasks is not None and executed_count >= max_tasks:
            break
        run_result = await run_next_agent_inbox_task(
            session,
            user=user,
            agent_id=agent.id,
            settings=settings,
        )
        results.append(
            TeamInboxCycleResult(
                agent=agent,
                task=run_result.task,
                conversation=run_result.conversation,
                response_id=run_result.response_id,
                output_text=run_result.output_text,
                workspace_item_id=run_result.workspace_item_id,
            )
        )
        if run_result.task is not None:
            executed_count += 1
    return results


def complete_task(
    session: Session,
    *,
    user: User,
    task_id: UUID,
    content: str,
    agent_id: UUID | None,
    claim_token: str | None,
) -> TeamTask:
    task = _get_owned_task(session, task_id=task_id, user=user)
    if task.status == "completed":
        raise TeamTaskActionError("Task is already completed.")

    normalized_content = content.strip()
    if not normalized_content:
        raise TeamTaskActionError("Completion content is required.")

    if agent_id is not None:
        agent = session.get(Agent, agent_id)
        if agent is not None and get_team_assignment(session, team_id=task.team_id, agent_id=agent.id) is None:
            agent = None
        if agent is None:
            raise TeamTaskActionError("Completion agent must belong to the same team.")
        if agent.id != task.assigned_agent_id:
            raise TeamTaskActionError("Only the assigned agent can complete this task.")

    token_to_use = claim_token or task.claim_token or f"manual-complete:{task.id}"
    return _complete_task_claim(
        session,
        task=task,
        claim_token=token_to_use,
        completion_content=normalized_content,
    )


def _load_latest_active_tasks_by_agent(
    session: Session,
    *,
    team: AgentTeam,
) -> dict[UUID, TeamTask]:
    tasks = session.exec(
        select(TeamTask)
        .where(TeamTask.team_id == team.id)
        .where(TeamTask.status.in_(["open", "claimed"]))
        .order_by(TeamTask.created_at.desc())
    ).all()
    tasks_by_agent: dict[UUID, TeamTask] = {}
    for task in tasks:
        tasks_by_agent.setdefault(task.assigned_agent_id, task)
    return tasks_by_agent


async def run_team_huddle(
    session: Session,
    *,
    user: User,
    team_id: UUID,
    user_input: str | list[dict[str, object]],
    conversation_id: UUID | None,
    instructions: str | None,
    secret_ids: list[UUID],
    settings: Settings,
) -> TeamHuddleResult:
    team = get_owned_team(session, team_id=team_id, user=user)
    agents, templates_by_id = _load_team_agents_and_templates(session, team=team)
    conversation = get_or_create_team_huddle_conversation(
        session,
        team=team,
        conversation_id=conversation_id,
    )
    request_env = resolve_secret_env(
        session,
        user=user,
        settings=settings,
        secret_ids=secret_ids,
    )

    session.add(
        Message(
            conversation_id=conversation.id,
            actor_type="user",
            actor_id=user.id,
            content=_serialize_user_input(user_input),
        )
    )
    session.commit()

    outputs: list[TeamMemberResponse] = []
    tasks: list[TeamTask] = []
    for agent in agents:
        ensure_agent_runtime_lease(session, agent=agent, settings=settings)
        lease_status = reconcile_runtime_lease(
            session,
            user=user,
            agent_id=agent.id,
            settings=settings,
        )
        if not lease_status.ready:
            raise RuntimeNotReadyError(lease_status.readiness_reason)
        runtime_client = HermesRuntimeClient(
            target=build_runtime_target(lease=lease_status.lease, settings=settings),
            timeout_seconds=settings.hermes_api_route_timeout_seconds,
        )
        role_template = templates_by_id.get(agent.role_template_id)
        runtime_response = await runtime_client.create_response(
            ResponsesRequest(
                input=_build_agent_huddle_input(
                    team=team,
                    user_input=user_input,
                    prior_outputs=outputs,
                ),
                instructions=_build_agent_huddle_instructions(
                    team=team,
                    role_template=role_template,
                    override=instructions,
                ),
                conversation=_build_team_runtime_conversation_name(
                    mode="team_huddle",
                    conversation=conversation,
                    agent=agent,
                ),
            ),
            request_env=request_env or None,
        )
        member_response = TeamMemberResponse(
            agent=agent,
            response_id=runtime_response.response_id,
            output_text=runtime_response.output_text,
        )
        outputs.append(member_response)
        session.add(
            Message(
                conversation_id=conversation.id,
                actor_type="assistant",
                actor_id=agent.id,
                content=runtime_response.output_text,
                response_chain_id=runtime_response.response_id,
            )
        )
        session.commit()
        tasks.append(
            _upsert_task_for_agent(
                session,
                team=team,
                conversation=conversation,
                agent=agent,
                instruction=runtime_response.output_text,
            )
        )

    plan_item = upsert_workspace_item(
        session,
        user=user,
        team_id=team.id,
        path=_workspace_huddle_plan_path(conversation.id),
        kind="file",
        content_text=_build_workspace_huddle_plan(
            team=team,
            user_input=user_input,
            outputs=outputs,
            tasks=tasks,
        ),
        conversation_id=conversation.id,
        agent_id=outputs[-1].agent.id if outputs else None,
    )
    conversation.latest_response_id = outputs[-1].response_id if outputs else None
    conversation.updated_at = utcnow()
    session.add(conversation)
    session.commit()
    session.refresh(conversation)

    return TeamHuddleResult(
        conversation=conversation,
        outputs=outputs,
        tasks=tasks,
        workspace_item_id=plan_item.id,
    )


async def run_team_response(
    session: Session,
    *,
    user: User,
    team_id: UUID,
    user_input: str | list[dict[str, object]],
    conversation_id: UUID | None,
    instructions: str | None,
    secret_ids: list[UUID],
    settings: Settings,
) -> TeamResponseResult:
    team = get_owned_team(session, team_id=team_id, user=user)
    agents, templates_by_id = _load_team_agents_and_templates(session, team=team)

    conversation = get_or_create_team_conversation(
        session,
        team=team,
        conversation_id=conversation_id,
    )
    request_env = resolve_secret_env(
        session,
        user=user,
        settings=settings,
        secret_ids=secret_ids,
    )
    tasks_by_agent = _load_latest_active_tasks_by_agent(session, team=team)
    run_claim_token = f"team-run:{conversation.id}:{uuid4()}"

    session.add(
        Message(
            conversation_id=conversation.id,
            actor_type="user",
            actor_id=user.id,
            content=_serialize_user_input(user_input),
        )
    )
    session.commit()

    outputs: list[TeamMemberResponse] = []
    generated_items: list[SharedWorkspaceItem] = []
    claimed_tasks: list[TeamTask] = []
    try:
        for agent in agents:
            ensure_agent_runtime_lease(session, agent=agent, settings=settings)
            lease_status = reconcile_runtime_lease(
                session,
                user=user,
                agent_id=agent.id,
                settings=settings,
            )
            if not lease_status.ready:
                raise RuntimeNotReadyError(lease_status.readiness_reason)
            runtime_client = HermesRuntimeClient(
                target=build_runtime_target(lease=lease_status.lease, settings=settings),
                timeout_seconds=settings.hermes_api_route_timeout_seconds,
            )
            role_template = templates_by_id.get(agent.role_template_id)
            assigned_task = tasks_by_agent.get(agent.id)
            if assigned_task is not None:
                assigned_task = _claim_task_for_execution(
                    session,
                    task=assigned_task,
                    claim_token=run_claim_token,
                )
                claimed_tasks.append(assigned_task)
            huddle_plan = _load_huddle_plan_item(
                session,
                team=team,
                conversation_id=assigned_task.conversation_id if assigned_task is not None else None,
            )
            workspace_items = _load_recent_workspace_context(
                session,
                team=team,
                exclude_paths={huddle_plan.path} if huddle_plan is not None else None,
                preferred_prefixes=_load_conversation_workspace_prefixes(
                    session,
                    team=team,
                    conversation=conversation,
                ),
            )
            runtime_response = await runtime_client.create_response(
                ResponsesRequest(
                    input=_build_agent_team_input(
                        team=team,
                        user_input=user_input,
                        prior_outputs=outputs,
                        assigned_task=assigned_task,
                        huddle_plan_text=huddle_plan.content_text if huddle_plan is not None else None,
                        workspace_items=workspace_items,
                    ),
                    instructions=_build_agent_instructions(
                        team=team,
                        role_template=role_template,
                        override=instructions,
                    ),
                    conversation=_build_team_runtime_conversation_name(
                        mode="team",
                        conversation=conversation,
                        agent=agent,
                        task=assigned_task,
                    ),
                ),
                request_env=request_env or None,
            )
            outputs.append(
                TeamMemberResponse(
                    agent=agent,
                    response_id=runtime_response.response_id,
                    output_text=runtime_response.output_text,
                )
            )
            session.add(
                Message(
                    conversation_id=conversation.id,
                    actor_type="assistant",
                    actor_id=agent.id,
                    content=runtime_response.output_text,
                    response_chain_id=runtime_response.response_id,
                )
            )
            output_item = upsert_workspace_item(
                session,
                user=user,
                team_id=team.id,
                path=_workspace_task_output_path(assigned_task.id)
                if assigned_task is not None
                else _workspace_team_agent_output_path(conversation.id, agent=agent),
                kind="file",
                content_text=_build_workspace_team_agent_output(
                    team=team,
                    agent=agent,
                    user_input=user_input,
                    assigned_task=assigned_task,
                    output_text=runtime_response.output_text,
                ),
                conversation_id=conversation.id,
                agent_id=agent.id,
            )
            generated_items.append(output_item)
            if assigned_task is not None:
                _complete_task_claim(
                    session,
                    task=assigned_task,
                    claim_token=run_claim_token,
                    completion_content=runtime_response.output_text,
                )
            else:
                session.commit()
    except Exception:
        for claimed_task in claimed_tasks:
            _release_task_claim(
                session,
                task=claimed_task,
                claim_token=run_claim_token,
                reason="Team execution failed before completion; the task returned to the queue.",
            )
        raise

    summary_item = upsert_workspace_item(
        session,
        user=user,
        team_id=team.id,
        path=_workspace_summary_path(conversation.id),
        kind="file",
        content_text=_build_workspace_summary(team=team, user_input=user_input, outputs=outputs),
        conversation_id=conversation.id,
        agent_id=outputs[-1].agent.id if outputs else None,
    )
    conversation.latest_response_id = outputs[-1].response_id if outputs else None
    conversation.updated_at = utcnow()
    session.add(conversation)
    session.commit()
    session.refresh(conversation)

    return TeamResponseResult(
        conversation=conversation,
        outputs=outputs,
        workspace_item_id=summary_item.id,
        generated_items=generated_items,
    )
