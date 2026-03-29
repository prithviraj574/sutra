from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from sqlmodel import select

from sutra_backend.auth.dependencies import get_current_user
from sutra_backend.config import Settings, get_app_settings
from sutra_backend.db import get_session
from sutra_backend.models import Agent, Team, User
from sutra_backend.runtime.errors import RuntimeNotReadyError
from sutra_backend.schemas.auth import AuthMeResponse, UserRead
from sutra_backend.schemas.catalog import AgentListResponse, AgentRead, TeamListResponse, TeamRead
from sutra_backend.schemas.conversations import ConversationListResponse, ConversationRead, MessageListResponse, MessageRead
from sutra_backend.schemas.runtime import AgentResponseCreateRequest, AgentResponseCreateResponse
from sutra_backend.schemas.runtime_leases import RuntimeLeaseRead, RuntimeLeaseResponse
from sutra_backend.schemas.secrets import SecretCreateRequest, SecretCreateResponse, SecretDeleteResponse, SecretListResponse, SecretRead
from sutra_backend.services.conversations import list_agent_conversations, list_conversation_messages
from sutra_backend.services.runtime_leases import provision_agent_runtime_lease, read_agent_runtime_lease
from sutra_backend.services.secrets import SecretVaultError, delete_user_secret, list_user_secrets, upsert_user_secret
from sutra_backend.services.runtime import AgentNotFoundError, run_agent_response

api_router = APIRouter()


@api_router.get("/health", tags=["health"])
def healthcheck(settings: Settings = Depends(get_app_settings)) -> dict[str, str]:
    return {
        "status": "ok",
        "service": "sutra-backend",
        "app_env": settings.app_env,
    }


@api_router.get("/auth/me", tags=["auth"], response_model=AuthMeResponse)
def read_current_user(user: User = Depends(get_current_user)) -> AuthMeResponse:
    return AuthMeResponse(user=UserRead.model_validate(user, from_attributes=True))


@api_router.get("/teams", tags=["teams"], response_model=TeamListResponse)
def list_teams(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> TeamListResponse:
    teams = session.exec(select(Team).where(Team.user_id == user.id)).all()
    return TeamListResponse(items=[TeamRead.model_validate(team, from_attributes=True) for team in teams])


@api_router.get("/agents", tags=["agents"], response_model=AgentListResponse)
def list_agents(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> AgentListResponse:
    statement = (
        select(Agent)
        .join(Team, Team.id == Agent.team_id)
        .where(Team.user_id == user.id)
    )
    agents = session.exec(statement).all()
    return AgentListResponse(items=[AgentRead.model_validate(agent, from_attributes=True) for agent in agents])


@api_router.get("/agents/{agent_id}/conversations", tags=["agents"], response_model=ConversationListResponse)
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


@api_router.get("/conversations/{conversation_id}/messages", tags=["conversations"], response_model=MessageListResponse)
def get_conversation_messages(
    conversation_id: UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> MessageListResponse:
    try:
        messages = list_conversation_messages(session, user=user, conversation_id=conversation_id)
    except AgentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return MessageListResponse(
        items=[MessageRead.model_validate(message, from_attributes=True) for message in messages]
    )


@api_router.get("/secrets", tags=["secrets"], response_model=SecretListResponse)
def list_secrets(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> SecretListResponse:
    secrets = list_user_secrets(session, user=user)
    return SecretListResponse(
        items=[SecretRead.model_validate(secret, from_attributes=True) for secret in secrets]
    )


@api_router.post("/secrets", tags=["secrets"], response_model=SecretCreateResponse, status_code=status.HTTP_201_CREATED)
def create_secret(
    payload: SecretCreateRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_app_settings),
) -> SecretCreateResponse:
    try:
        secret = upsert_user_secret(
            session,
            user=user,
            settings=settings,
            name=payload.name,
            value=payload.value,
            provider=payload.provider,
            scope=payload.scope,
            team_id=payload.team_id,
            agent_id=payload.agent_id,
        )
    except SecretVaultError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return SecretCreateResponse(secret=SecretRead.model_validate(secret, from_attributes=True))


@api_router.delete("/secrets/{secret_id}", tags=["secrets"], response_model=SecretDeleteResponse)
def remove_secret(
    secret_id: UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> SecretDeleteResponse:
    deleted = delete_user_secret(session, user=user, secret_id=secret_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Secret not found.")

    return SecretDeleteResponse(id=secret_id, deleted=True)


@api_router.get("/agents/{agent_id}/runtime", tags=["runtime"], response_model=RuntimeLeaseResponse)
def get_agent_runtime(
    agent_id: UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> RuntimeLeaseResponse:
    try:
        lease = read_agent_runtime_lease(session, user=user, agent_id=agent_id)
    except AgentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return RuntimeLeaseResponse(lease=RuntimeLeaseRead.model_validate(lease, from_attributes=True))


@api_router.post("/agents/{agent_id}/runtime/provision", tags=["runtime"], response_model=RuntimeLeaseResponse)
def provision_agent_runtime(
    agent_id: UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_app_settings),
) -> RuntimeLeaseResponse:
    try:
        lease = provision_agent_runtime_lease(
            session,
            user=user,
            agent_id=agent_id,
            settings=settings,
        )
    except AgentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RuntimeNotReadyError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return RuntimeLeaseResponse(lease=RuntimeLeaseRead.model_validate(lease, from_attributes=True))


@api_router.post(
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
    )
