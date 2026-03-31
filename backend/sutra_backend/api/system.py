from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from sutra_backend.auth.dependencies import get_current_user
from sutra_backend.config import Settings, get_app_settings
from sutra_backend.db import get_session
from sutra_backend.models import User
from sutra_backend.schemas.system import PollerLeaseRead, PollerStatusResponse
from sutra_backend.services.inbox_poller import read_inbox_poller_status


system_router = APIRouter()


@system_router.get("/system/poller", tags=["system"], response_model=PollerStatusResponse)
def get_poller_status(
    _user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_app_settings),
) -> PollerStatusResponse:
    status = read_inbox_poller_status(session=session, settings=settings)
    return PollerStatusResponse(
        enabled=status.enabled,
        interval_seconds=status.interval_seconds,
        lease_seconds=status.lease_seconds,
        max_tasks_per_sweep=status.max_tasks_per_sweep,
        is_active=status.is_active,
        lease=PollerLeaseRead.model_validate(status.lease, from_attributes=True)
        if status.lease is not None
        else None,
    )
