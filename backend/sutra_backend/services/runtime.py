from __future__ import annotations

import json
from dataclasses import dataclass
from uuid import UUID

from sqlmodel import Session, select

from sutra_backend.config import Settings
from sutra_backend.models import Agent, Conversation, Message, RuntimeLease, User, utcnow
from sutra_backend.runtime.client import HermesResponse, HermesRuntimeClient, HermesRuntimeTarget, ResponsesRequest
from sutra_backend.runtime.errors import RuntimeNotReadyError
from sutra_backend.runtime.provisioning import ensure_agent_runtime_lease
from sutra_backend.services.agent_teams import (
    find_personal_team_for_agent,
    get_owned_agent as find_owned_agent,
    get_owned_team as find_owned_team,
    get_team_assignment,
)
from sutra_backend.services.runtime_leases import reconcile_runtime_lease
from sutra_backend.services.secrets import resolve_secret_env
from sutra_backend.services.teams import upsert_workspace_item


class AgentNotFoundError(RuntimeError):
    """Raised when the requested agent is missing or not owned by the user."""


@dataclass(frozen=True)
class AgentResponseResult:
    conversation: Conversation
    runtime_response: HermesResponse
    workspace_item_id: UUID | None


def build_agent_runtime_conversation_name(
    *,
    conversation: Conversation,
    agent: Agent,
) -> str:
    if conversation.mode == "team_member" and conversation.agent_team_id is not None:
        return f"team:{conversation.agent_team_id}:member:{agent.id}:conversation:{conversation.id}"
    if conversation.agent_team_id is not None:
        return (
            f"{conversation.mode}:team:{conversation.agent_team_id}:"
            f"conversation:{conversation.id}:agent:{agent.id}"
        )
    return f"agent:{agent.id}:conversation:{conversation.id}"


def get_owned_agent(session: Session, *, agent_id: UUID, user: User) -> Agent:
    agent = find_owned_agent(session, agent_id=agent_id, user=user)
    if agent is None:
        raise AgentNotFoundError("Agent not found.")
    return agent


def build_runtime_target(*, lease: RuntimeLease, settings: Settings) -> HermesRuntimeTarget:
    if not lease.api_base_url:
        raise RuntimeNotReadyError("Agent runtime does not have an API base URL.")
    runtime_api_key = settings.runtime_api_key or settings.dev_runtime_api_key
    if not runtime_api_key:
        raise RuntimeNotReadyError("Runtime API key is not configured.")

    return HermesRuntimeTarget(
        base_url=lease.api_base_url,
        api_key=runtime_api_key,
    )


def get_or_create_conversation(
    session: Session,
    *,
    agent: Agent,
    conversation_id: UUID | None,
    mode: str,
    agent_team_id: UUID | None,
) -> Conversation:
    if conversation_id is not None:
        conversation = session.exec(
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .where(Conversation.agent_id == agent.id)
            .where(Conversation.mode == mode)
        ).first()
        if conversation is None:
            raise AgentNotFoundError("Conversation not found.")
        if conversation.agent_team_id != agent_team_id:
            raise AgentNotFoundError("Conversation not found.")
        return conversation

    conversation = Conversation(
        agent_team_id=agent_team_id,
        agent_id=agent.id,
        mode=mode,
    )
    session.add(conversation)
    session.commit()
    session.refresh(conversation)
    return conversation


def _build_team_member_instructions(*, team_name: str, base: str | None) -> str:
    context = (
        f"You are responding as a member of the Sutra team '{team_name}'. "
        "This run may access the team's shared workspace when it helps produce a better answer."
    )
    if base:
        return f"{context}\n\n{base}"
    return context


def _serialize_user_input(raw_input: str | list[dict[str, object]]) -> str:
    if isinstance(raw_input, str):
        return raw_input
    return json.dumps(raw_input, separators=(",", ":"), sort_keys=True)


async def run_agent_response(
    session: Session,
    *,
    user: User,
    agent_id: UUID,
    request: ResponsesRequest,
    conversation_id: UUID | None,
    settings: Settings,
    agent_team_id: UUID | None = None,
    conversation_mode: str = "agent",
) -> AgentResponseResult:
    agent = get_owned_agent(session, agent_id=agent_id, user=user)
    team_name: str | None = None
    if agent_team_id is not None:
        team = find_owned_team(session, team_id=agent_team_id, user=user)
        if team is None:
            raise AgentNotFoundError("Team not found.")
        if get_team_assignment(session, team_id=team.id, agent_id=agent.id) is None:
            raise AgentNotFoundError("Agent is not part of the requested team.")
        team_name = team.name
    existing_lease = session.exec(select(RuntimeLease).where(RuntimeLease.agent_id == agent.id)).first()
    if existing_lease is None:
        if settings.runtime_provider == "static_dev":
            ensure_agent_runtime_lease(session, agent=agent, settings=settings)
        else:
            raise RuntimeNotReadyError(
                "Agent runtime is not provisioned yet. Provision the runtime before sending a prompt."
            )
    lease_status = reconcile_runtime_lease(
        session,
        user=user,
        agent_id=agent.id,
        settings=settings,
    )
    if not lease_status.ready:
        raise RuntimeNotReadyError(lease_status.readiness_reason)
    target = build_runtime_target(lease=lease_status.lease, settings=settings)
    conversation = get_or_create_conversation(
        session,
        agent=agent,
        conversation_id=conversation_id,
        mode=conversation_mode,
        agent_team_id=agent_team_id,
    )

    effective_previous_response_id = request.previous_response_id or conversation.latest_response_id
    runtime_conversation = (
        None
        if request.previous_response_id is not None
        else build_agent_runtime_conversation_name(conversation=conversation, agent=agent)
    )
    request_env = resolve_secret_env(
        session,
        user=user,
        settings=settings,
        secret_ids=request.secret_ids,
    )

    session.add(
        Message(
            conversation_id=conversation.id,
            actor_type="user",
            actor_id=user.id,
            content=_serialize_user_input(request.input),
            response_chain_id=effective_previous_response_id,
        )
    )
    session.commit()

    runtime_client = HermesRuntimeClient(
        target=target,
        timeout_seconds=settings.hermes_api_route_timeout_seconds,
    )
    runtime_metadata = dict(request.metadata)
    runtime_metadata.setdefault("sutra_conversation_mode", conversation.mode)
    if conversation.agent_team_id is not None:
        runtime_metadata.setdefault("sutra_agent_team_id", str(conversation.agent_team_id))
    runtime_response = await runtime_client.create_response(
        ResponsesRequest(
            input=request.input,
            instructions=(
                _build_team_member_instructions(team_name=team_name, base=request.instructions)
                if conversation.mode == "team_member" and team_name is not None
                else request.instructions
            ),
            previous_response_id=request.previous_response_id or None,
            conversation=runtime_conversation,
            store=request.store,
            model=request.model,
            metadata=runtime_metadata,
        ),
        request_env=request_env or None,
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
    conversation.latest_response_id = runtime_response.response_id
    conversation.updated_at = utcnow()
    session.add(conversation)
    session.commit()
    session.refresh(conversation)

    workspace_item = upsert_workspace_item(
        session,
        user=user,
        team_id=resolved_workspace_team.id,
        path=f"conversations/{conversation.id}.md",
        kind="file",
        content_text=(
            f"# Conversation {conversation.id}\n\n"
            f"## User\n\n{_serialize_user_input(request.input)}\n\n"
            f"## Assistant\n\n{runtime_response.output_text}\n"
        ),
        conversation_id=conversation.id,
        agent_id=agent.id,
    ) if (
        (resolved_workspace_team := (
            find_owned_team(session, team_id=conversation.agent_team_id, user=user)
            if conversation.agent_team_id is not None
            else find_personal_team_for_agent(session, agent_id=agent.id)
        )) is not None
    ) else None

    return AgentResponseResult(
        conversation=conversation,
        runtime_response=runtime_response,
        workspace_item_id=workspace_item.id if workspace_item is not None else None,
    )
