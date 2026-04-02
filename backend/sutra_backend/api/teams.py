from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from sutra_backend.api.github_integration import github_integration_router
from sutra_backend.auth.dependencies import get_current_user
from sutra_backend.config import Settings, get_app_settings
from sutra_backend.db import get_session
from sutra_backend.models import AgentTeam, User
from sutra_backend.runtime.errors import RuntimeNotReadyError
from sutra_backend.schemas.catalog import (
    AgentRead,
    ArtifactRead,
    RoleTemplateListResponse,
    RoleTemplateRead,
    SharedWorkspaceItemRead,
    TeamArtifactListResponse,
    TeamCreateRequest,
    TeamCreateResponse,
    TeamListResponse,
    TeamRead,
    TeamWorkspaceResponse,
    WorkspaceItemUpsertRequest,
    WorkspaceItemUpsertResponse,
)
from sutra_backend.schemas.conversations import TeamConversationListResponse, ConversationRead
from sutra_backend.schemas.runtime import AgentResponseCreateRequest, AgentResponseCreateResponse
from sutra_backend.schemas.team_runtime import (
    TeamHuddleCreateRequest,
    TeamHuddleCreateResponse,
    TeamInboxCycleItemRead,
    TeamInboxCycleResponse,
    TeamMemberResponseRead,
    TeamResponseCreateRequest,
    TeamResponseCreateResponse,
    TeamTaskListResponse,
    TeamTaskRead,
)
from sutra_backend.services.conversations import list_team_conversations
from sutra_backend.services.agent_teams import list_assignments_for_agents
from sutra_backend.services.runtime import AgentNotFoundError, run_agent_response
from sutra_backend.services.secrets import SecretVaultError
from sutra_backend.services.team_runtime import (
    TeamTaskActionError,
    TeamTaskClaimError,
    list_team_tasks,
    run_team_huddle,
    run_team_inbox_cycle,
    run_team_response,
)
from sutra_backend.services.teams import (
    TeamCreationSpec,
    TeamServiceError,
    create_team_with_agents,
    list_team_artifacts,
    list_role_templates,
    read_team_workspace,
    upsert_workspace_item,
)


teams_router = APIRouter()
teams_router.include_router(github_integration_router)


def _build_agent_read(agent, *, team_ids: list[UUID], shared_workspace_enabled: bool) -> AgentRead:
    return AgentRead(
        id=agent.id,
        user_id=agent.user_id,
        team_ids=team_ids,
        role_template_id=agent.role_template_id,
        name=agent.name,
        role_name=agent.role_name,
        status=agent.status,
        runtime_kind=agent.runtime_kind,
        hermes_home_uri=agent.hermes_home_uri,
        private_volume_uri=agent.private_volume_uri,
        shared_workspace_enabled=shared_workspace_enabled,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
    )


@teams_router.get("/teams", tags=["teams"], response_model=TeamListResponse)
def list_teams(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> TeamListResponse:
    teams = session.exec(select(AgentTeam).where(AgentTeam.user_id == user.id)).all()
    return TeamListResponse(items=[TeamRead.model_validate(team, from_attributes=True) for team in teams])


@teams_router.post("/teams", tags=["teams"], response_model=TeamCreateResponse, status_code=status.HTTP_201_CREATED)
def create_team(
    payload: TeamCreateRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_app_settings),
) -> TeamCreateResponse:
    try:
        result = create_team_with_agents(
            session,
            user=user,
            name=payload.name,
            description=payload.description,
            agents=[
                TeamCreationSpec(
                    role_template_key=agent.role_template_key,
                    name=agent.name,
                )
                for agent in payload.agents
            ],
            settings=settings,
        )
    except TeamServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    assignments_by_agent = list_assignments_for_agents(
        session,
        agent_ids=[agent.id for agent in result.agents],
    )
    return TeamCreateResponse(
        team=TeamRead.model_validate(result.team, from_attributes=True),
        agents=[
            _build_agent_read(
                agent,
                team_ids=[assignment.agent_team_id for assignment in assignments_by_agent.get(agent.id, [])],
                shared_workspace_enabled=any(
                    assignment.shared_workspace_enabled
                    for assignment in assignments_by_agent.get(agent.id, [])
                ),
            )
            for agent in result.agents
        ],
    )


@teams_router.get("/role-templates", tags=["teams"], response_model=RoleTemplateListResponse)
def get_role_templates(
    _user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> RoleTemplateListResponse:
    templates = list_role_templates(session)
    return RoleTemplateListResponse(
        items=[
            RoleTemplateRead.model_validate(template, from_attributes=True)
            for template in templates
        ]
    )


@teams_router.get("/teams/{team_id}/workspace", tags=["teams"], response_model=TeamWorkspaceResponse)
def get_team_workspace(
    team_id: UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> TeamWorkspaceResponse:
    try:
        result = read_team_workspace(session, user=user, team_id=team_id)
    except TeamServiceError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return TeamWorkspaceResponse(
        team=TeamRead.model_validate(result.team, from_attributes=True),
        items=[
            SharedWorkspaceItemRead.model_validate(item, from_attributes=True)
            for item in result.items
        ],
    )


@teams_router.get("/teams/{team_id}/artifacts", tags=["teams"], response_model=TeamArtifactListResponse)
def get_team_artifacts(
    team_id: UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> TeamArtifactListResponse:
    try:
        result = list_team_artifacts(session, user=user, team_id=team_id)
    except TeamServiceError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return TeamArtifactListResponse(
        items=[ArtifactRead.model_validate(item, from_attributes=True) for item in result.items]
    )


@teams_router.post(
    "/teams/{team_id}/workspace/items",
    tags=["teams"],
    response_model=WorkspaceItemUpsertResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_workspace_item(
    team_id: UUID,
    payload: WorkspaceItemUpsertRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> WorkspaceItemUpsertResponse:
    try:
        item = upsert_workspace_item(
            session,
            user=user,
            team_id=team_id,
            path=payload.path,
            kind=payload.kind,
            content_text=payload.content_text,
        )
    except TeamServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return WorkspaceItemUpsertResponse(
        item=SharedWorkspaceItemRead.model_validate(item, from_attributes=True)
    )


@teams_router.get("/teams/{team_id}/conversations", tags=["teams"], response_model=TeamConversationListResponse)
def get_team_conversations(
    team_id: UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> TeamConversationListResponse:
    try:
        conversations = list_team_conversations(session, user=user, team_id=team_id)
    except AgentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return TeamConversationListResponse(
        items=[ConversationRead.model_validate(conversation, from_attributes=True) for conversation in conversations]
    )


@teams_router.get("/teams/{team_id}/tasks", tags=["teams"], response_model=TeamTaskListResponse)
def get_team_tasks(
    team_id: UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> TeamTaskListResponse:
    try:
        tasks = list_team_tasks(session, user=user, team_id=team_id)
    except AgentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return TeamTaskListResponse(
        items=[TeamTaskRead.model_validate(task, from_attributes=True) for task in tasks]
    )


@teams_router.post("/teams/{team_id}/inbox/run-cycle", tags=["teams"], response_model=TeamInboxCycleResponse)
async def post_run_team_inbox_cycle(
    team_id: UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_app_settings),
) -> TeamInboxCycleResponse:
    try:
        results = await run_team_inbox_cycle(
            session,
            user=user,
            team_id=team_id,
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

    return TeamInboxCycleResponse(
        executed_count=sum(1 for item in results if item.task is not None),
        results=[
            TeamInboxCycleItemRead(
                agent_id=item.agent.id,
                task=TeamTaskRead.model_validate(item.task, from_attributes=True) if item.task is not None else None,
                conversation_id=item.conversation.id if item.conversation is not None else None,
                response_id=item.response_id,
                output_text=item.output_text,
                workspace_item_id=item.workspace_item_id,
            )
            for item in results
        ],
    )


@teams_router.post("/teams/{team_id}/huddles", tags=["teams"], response_model=TeamHuddleCreateResponse)
async def create_team_huddle(
    team_id: UUID,
    payload: TeamHuddleCreateRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_app_settings),
) -> TeamHuddleCreateResponse:
    try:
        result = await run_team_huddle(
            session,
            user=user,
            team_id=team_id,
            user_input=payload.input,
            conversation_id=payload.conversation_id,
            instructions=payload.instructions,
            secret_ids=payload.secret_ids,
            settings=settings,
        )
    except AgentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RuntimeNotReadyError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except SecretVaultError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return TeamHuddleCreateResponse(
        conversation_id=result.conversation.id,
        output_text="\n\n".join(
            f"{item.agent.role_name}: {item.output_text}" for item in result.outputs
        ),
        outputs=[
            TeamMemberResponseRead(
                agent_id=item.agent.id,
                agent_name=item.agent.name,
                role_name=item.agent.role_name,
                response_id=item.response_id,
                output_text=item.output_text,
            )
            for item in result.outputs
        ],
        tasks=[
            TeamTaskRead.model_validate(task, from_attributes=True)
            for task in result.tasks
        ],
        workspace_item_id=result.workspace_item_id,
    )


@teams_router.post(
    "/teams/{team_id}/agents/{agent_id}/responses",
    tags=["teams"],
    response_model=AgentResponseCreateResponse,
)
async def create_team_member_response(
    team_id: UUID,
    agent_id: UUID,
    payload: TeamResponseCreateRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_app_settings),
) -> AgentResponseCreateResponse:
    try:
        result = await run_agent_response(
            session,
            user=user,
            agent_id=agent_id,
            request=AgentResponseCreateRequest(
                input=payload.input,
                conversation_id=payload.conversation_id,
                instructions=payload.instructions,
                secret_ids=payload.secret_ids,
            ),
            conversation_id=payload.conversation_id,
            settings=settings,
            agent_team_id=team_id,
            conversation_mode="team_member",
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


@teams_router.post("/teams/{team_id}/responses", tags=["teams"], response_model=TeamResponseCreateResponse)
async def create_team_response(
    team_id: UUID,
    payload: TeamResponseCreateRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_app_settings),
) -> TeamResponseCreateResponse:
    try:
        result = await run_team_response(
            session,
            user=user,
            team_id=team_id,
            user_input=payload.input,
            conversation_id=payload.conversation_id,
            instructions=payload.instructions,
            secret_ids=payload.secret_ids,
            settings=settings,
        )
    except AgentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RuntimeNotReadyError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except SecretVaultError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except TeamTaskClaimError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return TeamResponseCreateResponse(
        conversation_id=result.conversation.id,
        output_text="\n\n".join(
            f"{item.agent.role_name}: {item.output_text}" for item in result.outputs
        ),
        outputs=[
            TeamMemberResponseRead(
                agent_id=item.agent.id,
                agent_name=item.agent.name,
                role_name=item.agent.role_name,
                response_id=item.response_id,
                output_text=item.output_text,
            )
            for item in result.outputs
        ],
        workspace_item_id=result.workspace_item_id,
        generated_items=[
            SharedWorkspaceItemRead.model_validate(item, from_attributes=True)
            for item in result.generated_items
        ],
    )
