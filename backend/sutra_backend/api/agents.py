from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from sutra_backend.auth.dependencies import get_current_user
from sutra_backend.config import Settings, get_app_settings
from sutra_backend.db import get_session
from sutra_backend.models import Agent, Team, User
from sutra_backend.runtime.errors import RuntimeNotReadyError
from sutra_backend.schemas.catalog import AgentListResponse, AgentRead
from sutra_backend.schemas.conversations import ConversationListResponse, ConversationRead
from sutra_backend.schemas.runtime import AgentResponseCreateRequest, AgentResponseCreateResponse
from sutra_backend.schemas.team_runtime import AgentInboxClaimResponse, AgentInboxRunResponse, TeamTaskListResponse, TeamTaskRead
from sutra_backend.services.conversations import list_agent_conversations
from sutra_backend.services.runtime import AgentNotFoundError, run_agent_response
from sutra_backend.services.secrets import SecretVaultError
from sutra_backend.services.team_runtime import (
    TeamTaskActionError,
    TeamTaskClaimError,
    claim_next_agent_inbox_task,
    list_agent_inbox_tasks,
    run_next_agent_inbox_task,
)


agents_router = APIRouter()


@agents_router.get("/agents", tags=["agents"], response_model=AgentListResponse)
def list_agents(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> AgentListResponse:
    statement = (
        select(Agent)
        .join(Team, Team.id == Agent.team_id)
        .where(Team.user_id == user.id)
        .order_by(Team.mode.asc(), Team.created_at.asc(), Agent.created_at.asc())
    )
    agents = session.exec(statement).all()
    return AgentListResponse(items=[AgentRead.model_validate(agent, from_attributes=True) for agent in agents])


@agents_router.get("/agents/{agent_id}/conversations", tags=["agents"], response_model=ConversationListResponse)
def get_agent_conversations(
    agent_id: UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ConversationListResponse:
    try:
        conversations = list_agent_conversations(session, user=user, agent_id=agent_id)
    except AgentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return ConversationListResponse(
        items=[ConversationRead.model_validate(conversation, from_attributes=True) for conversation in conversations]
    )


@agents_router.get("/agents/{agent_id}/inbox", tags=["agents"], response_model=TeamTaskListResponse)
def get_agent_inbox(
    agent_id: UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> TeamTaskListResponse:
    try:
        tasks = list_agent_inbox_tasks(session, user=user, agent_id=agent_id)
    except AgentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return TeamTaskListResponse(
        items=[TeamTaskRead.model_validate(task, from_attributes=True) for task in tasks]
    )


@agents_router.post("/agents/{agent_id}/inbox/claim-next", tags=["agents"], response_model=AgentInboxClaimResponse)
def post_claim_next_inbox_task(
    agent_id: UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> AgentInboxClaimResponse:
    try:
        task = claim_next_agent_inbox_task(session, user=user, agent_id=agent_id)
    except AgentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TeamTaskClaimError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return AgentInboxClaimResponse(
        task=TeamTaskRead.model_validate(task, from_attributes=True) if task is not None else None
    )


@agents_router.post("/agents/{agent_id}/inbox/run-next", tags=["agents"], response_model=AgentInboxRunResponse)
async def post_run_next_inbox_task(
    agent_id: UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_app_settings),
) -> AgentInboxRunResponse:
    try:
        result = await run_next_agent_inbox_task(
            session,
            user=user,
            agent_id=agent_id,
            settings=settings,
        )
    except AgentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RuntimeNotReadyError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except TeamTaskActionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except TeamTaskClaimError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return AgentInboxRunResponse(
        task=TeamTaskRead.model_validate(result.task, from_attributes=True) if result.task is not None else None,
        conversation_id=result.conversation.id if result.conversation is not None else None,
        response_id=result.response_id,
        output_text=result.output_text,
        workspace_item_id=result.workspace_item_id,
    )


@agents_router.post(
    "/agents/{agent_id}/responses",
    tags=["agents"],
    response_model=AgentResponseCreateResponse,
)
async def create_agent_response(
    agent_id: UUID,
    payload: AgentResponseCreateRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_app_settings),
) -> AgentResponseCreateResponse:
    try:
        result = await run_agent_response(
            session,
            user=user,
            agent_id=agent_id,
            request=payload,
            conversation_id=payload.conversation_id,
            settings=settings,
        )
    except AgentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RuntimeNotReadyError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except SecretVaultError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return AgentResponseCreateResponse(
        conversation_id=result.conversation.id,
        response_id=result.runtime_response.response_id,
        output_text=result.runtime_response.output_text,
        raw_response=result.runtime_response.raw_response,
        workspace_item_id=result.workspace_item_id,
    )
