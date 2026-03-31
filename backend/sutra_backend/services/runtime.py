from __future__ import annotations

import json
from dataclasses import dataclass
from uuid import UUID

from sqlmodel import Session, select

from sutra_backend.config import Settings
from sutra_backend.models import Agent, Conversation, Message, RuntimeLease, Team, User, utcnow
from sutra_backend.runtime.client import HermesResponse, HermesRuntimeClient, HermesRuntimeTarget, ResponsesRequest
from sutra_backend.runtime.errors import RuntimeNotReadyError
from sutra_backend.runtime.provisioning import ensure_agent_runtime_lease
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
    return f"agent:{agent.id}:conversation:{conversation.id}"


def get_owned_agent(session: Session, *, agent_id: UUID, user: User) -> Agent:
    statement = (
        select(Agent)
        .join(Team, Team.id == Agent.team_id)
        .where(Agent.id == agent_id)
        .where(Team.user_id == user.id)
    )
    agent = session.exec(statement).first()
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
) -> Conversation:
    if conversation_id is not None:
        conversation = session.exec(
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .where(Conversation.agent_id == agent.id)
        ).first()
        if conversation is None:
            raise AgentNotFoundError("Conversation not found.")
        return conversation

    conversation = Conversation(team_id=agent.team_id, agent_id=agent.id, mode="single_agent")
    session.add(conversation)
    session.commit()
    session.refresh(conversation)
    return conversation


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
) -> AgentResponseResult:
    agent = get_owned_agent(session, agent_id=agent_id, user=user)
    ensure_agent_runtime_lease(session, agent=agent, settings=settings)
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
    runtime_response = await runtime_client.create_response(
        ResponsesRequest(
            input=request.input,
            instructions=request.instructions,
            previous_response_id=request.previous_response_id or None,
            conversation=runtime_conversation,
            store=request.store,
            model=request.model,
            metadata=request.metadata,
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
        team_id=agent.team_id,
        path=f"conversations/{conversation.id}.md",
        kind="file",
        content_text=(
            f"# Conversation {conversation.id}\n\n"
            f"## User\n\n{_serialize_user_input(request.input)}\n\n"
            f"## Assistant\n\n{runtime_response.output_text}\n"
        ),
        conversation_id=conversation.id,
        agent_id=agent.id,
    )

    return AgentResponseResult(
        conversation=conversation,
        runtime_response=runtime_response,
        workspace_item_id=workspace_item.id,
    )
