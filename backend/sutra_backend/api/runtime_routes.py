from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from sutra_backend.auth.dependencies import get_current_user
from sutra_backend.config import Settings, get_app_settings
from sutra_backend.db import get_session
from sutra_backend.models import Agent, User
from sutra_backend.runtime.errors import RuntimeNotReadyError
from sutra_backend.schemas.runtime_leases import RuntimeLeaseRead, RuntimeLeaseResponse
from sutra_backend.services.runtime import AgentNotFoundError
from sutra_backend.services.runtime_leases import (
    provision_agent_runtime_lease,
    reconcile_runtime_lease,
    restart_runtime_lease,
    summarize_runtime_lease,
    verify_runtime_lease,
)


runtime_router = APIRouter()


def _build_runtime_lease_response(status_summary) -> RuntimeLeaseResponse:
    return RuntimeLeaseResponse(
        lease=RuntimeLeaseRead.model_validate(
            {
                **status_summary.lease.model_dump(),
                "provider": status_summary.provider,
                "ready": status_summary.ready,
                "heartbeat_fresh": status_summary.heartbeat_fresh,
                "readiness_stage": status_summary.readiness_stage,
                "readiness_reason": status_summary.readiness_reason,
                "probe_detail": status_summary.probe_detail,
                "probe_checked_url": status_summary.probe_checked_url,
                "isolation_ok": status_summary.isolation_ok,
                "isolation_reason": status_summary.isolation_reason,
            }
        )
    )


@runtime_router.get("/agents/{agent_id}/runtime", tags=["runtime"], response_model=RuntimeLeaseResponse)
def get_agent_runtime(
    agent_id: UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_app_settings),
) -> RuntimeLeaseResponse:
    try:
        status_summary = reconcile_runtime_lease(
            session,
            user=user,
            agent_id=agent_id,
            settings=settings,
        )
    except AgentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return _build_runtime_lease_response(status_summary)


@runtime_router.post(
    "/agents/{agent_id}/runtime/provision",
    tags=["runtime"],
    response_model=RuntimeLeaseResponse,
)
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
        agent = session.get(Agent, lease.agent_id)
        if agent is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found.")
        status_summary = summarize_runtime_lease(
            agent=agent,
            session=session,
            lease=lease,
            settings=settings,
        )
    except AgentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RuntimeNotReadyError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return _build_runtime_lease_response(status_summary)


@runtime_router.post(
    "/agents/{agent_id}/runtime/verify",
    tags=["runtime"],
    response_model=RuntimeLeaseResponse,
)
async def verify_agent_runtime(
    agent_id: UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_app_settings),
) -> RuntimeLeaseResponse:
    try:
        status_summary = await verify_runtime_lease(
            session,
            user=user,
            agent_id=agent_id,
            settings=settings,
        )
    except AgentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RuntimeNotReadyError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return _build_runtime_lease_response(status_summary)


@runtime_router.post(
    "/agents/{agent_id}/runtime/restart",
    tags=["runtime"],
    response_model=RuntimeLeaseResponse,
)
def restart_agent_runtime(
    agent_id: UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_app_settings),
) -> RuntimeLeaseResponse:
    try:
        status_summary = restart_runtime_lease(
            session,
            user=user,
            agent_id=agent_id,
            settings=settings,
        )
    except AgentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RuntimeNotReadyError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return _build_runtime_lease_response(status_summary)
