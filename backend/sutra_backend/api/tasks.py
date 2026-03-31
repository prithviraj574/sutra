from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from sutra_backend.auth.dependencies import get_current_user
from sutra_backend.db import get_session
from sutra_backend.models import User
from sutra_backend.schemas.team_runtime import (
    TeamTaskCompleteRequest,
    TeamTaskDelegateRequest,
    TeamTaskMessageRequest,
    TeamTaskMutationResponse,
    TeamTaskRead,
    TeamTaskReportRequest,
    TeamTaskUpdateListResponse,
    TeamTaskUpdateRead,
)
from sutra_backend.services.runtime import AgentNotFoundError
from sutra_backend.services.team_runtime import (
    TeamTaskActionError,
    complete_task,
    create_task_message,
    create_task_report,
    delegate_task,
    list_task_updates,
)


tasks_router = APIRouter()


@tasks_router.get("/tasks/{task_id}/updates", tags=["tasks"], response_model=TeamTaskUpdateListResponse)
def get_task_updates(
    task_id: UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> TeamTaskUpdateListResponse:
    try:
        updates = list_task_updates(session, user=user, task_id=task_id)
    except AgentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return TeamTaskUpdateListResponse(
        items=[TeamTaskUpdateRead.model_validate(item, from_attributes=True) for item in updates]
    )


@tasks_router.post("/tasks/{task_id}/delegate", tags=["tasks"], response_model=TeamTaskMutationResponse)
def post_task_delegate(
    task_id: UUID,
    payload: TeamTaskDelegateRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> TeamTaskMutationResponse:
    try:
        task = delegate_task(
            session,
            user=user,
            task_id=task_id,
            assigned_agent_id=payload.assigned_agent_id,
            note=payload.note,
        )
    except AgentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TeamTaskActionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return TeamTaskMutationResponse(task=TeamTaskRead.model_validate(task, from_attributes=True))


@tasks_router.post(
    "/tasks/{task_id}/reports",
    tags=["tasks"],
    response_model=TeamTaskMutationResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_task_report(
    task_id: UUID,
    payload: TeamTaskReportRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> TeamTaskMutationResponse:
    try:
        task = create_task_report(
            session,
            user=user,
            task_id=task_id,
            content=payload.content,
            agent_id=payload.agent_id,
        )
    except AgentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TeamTaskActionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return TeamTaskMutationResponse(task=TeamTaskRead.model_validate(task, from_attributes=True))


@tasks_router.post(
    "/tasks/{task_id}/messages",
    tags=["tasks"],
    response_model=TeamTaskMutationResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_task_message(
    task_id: UUID,
    payload: TeamTaskMessageRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> TeamTaskMutationResponse:
    try:
        task = create_task_message(
            session,
            user=user,
            task_id=task_id,
            content=payload.content,
            agent_id=payload.agent_id,
        )
    except AgentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TeamTaskActionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return TeamTaskMutationResponse(task=TeamTaskRead.model_validate(task, from_attributes=True))


@tasks_router.post("/tasks/{task_id}/complete", tags=["tasks"], response_model=TeamTaskMutationResponse)
def post_task_complete(
    task_id: UUID,
    payload: TeamTaskCompleteRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> TeamTaskMutationResponse:
    try:
        task = complete_task(
            session,
            user=user,
            task_id=task_id,
            content=payload.content,
            agent_id=payload.agent_id,
            claim_token=payload.claim_token,
        )
    except AgentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TeamTaskActionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return TeamTaskMutationResponse(task=TeamTaskRead.model_validate(task, from_attributes=True))
