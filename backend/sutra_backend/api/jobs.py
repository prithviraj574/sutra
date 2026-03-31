from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from sutra_backend.auth.dependencies import get_current_user
from sutra_backend.config import Settings, get_app_settings
from sutra_backend.db import get_session
from sutra_backend.models import User
from sutra_backend.runtime.errors import RuntimeNotReadyError
from sutra_backend.schemas.catalog import SharedWorkspaceItemRead
from sutra_backend.schemas.jobs import (
    AutomationJobCreateRequest,
    AutomationJobListResponse,
    AutomationJobRead,
    AutomationJobResponse,
    AutomationJobRunResponse,
    AutomationJobUpdateRequest,
)
from sutra_backend.services.jobs import (
    AutomationJobError,
    create_job,
    list_jobs,
    run_job,
    update_job,
)
from sutra_backend.services.runtime import AgentNotFoundError


jobs_router = APIRouter()


@jobs_router.get("/jobs", tags=["jobs"], response_model=AutomationJobListResponse)
def get_jobs(
    team_id: UUID | None = Query(default=None),
    agent_id: UUID | None = Query(default=None),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> AutomationJobListResponse:
    try:
        jobs = list_jobs(session, user=user, team_id=team_id, agent_id=agent_id)
    except (AutomationJobError, AgentNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return AutomationJobListResponse(
        items=[AutomationJobRead.model_validate(job, from_attributes=True) for job in jobs]
    )


@jobs_router.post("/jobs", tags=["jobs"], response_model=AutomationJobResponse, status_code=status.HTTP_201_CREATED)
def post_job(
    payload: AutomationJobCreateRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> AutomationJobResponse:
    try:
        job = create_job(
            session,
            user=user,
            name=payload.name,
            schedule=payload.schedule,
            prompt=payload.prompt,
            team_id=payload.team_id,
            agent_id=payload.agent_id,
            enabled=payload.enabled,
        )
    except (AutomationJobError, AgentNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return AutomationJobResponse(job=AutomationJobRead.model_validate(job, from_attributes=True))


@jobs_router.patch("/jobs/{job_id}", tags=["jobs"], response_model=AutomationJobResponse)
def patch_job(
    job_id: UUID,
    payload: AutomationJobUpdateRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> AutomationJobResponse:
    try:
        job = update_job(
            session,
            user=user,
            job_id=job_id,
            name=payload.name,
            schedule=payload.schedule,
            prompt=payload.prompt,
            enabled=payload.enabled,
        )
    except (AutomationJobError, AgentNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return AutomationJobResponse(job=AutomationJobRead.model_validate(job, from_attributes=True))


@jobs_router.post("/jobs/{job_id}/run", tags=["jobs"], response_model=AutomationJobRunResponse)
async def post_run_job(
    job_id: UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_app_settings),
) -> AutomationJobRunResponse:
    try:
        result = await run_job(
            session,
            user=user,
            job_id=job_id,
            settings=settings,
        )
    except (AutomationJobError, AgentNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeNotReadyError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return AutomationJobRunResponse(
        job=AutomationJobRead.model_validate(result.job, from_attributes=True),
        conversation_id=result.conversation_id,
        response_id=result.response_id,
        output_text=result.output_text,
        workspace_item_id=result.workspace_item_id,
        generated_items=[
            SharedWorkspaceItemRead.model_validate(item, from_attributes=True)
            for item in result.generated_items
        ],
    )
