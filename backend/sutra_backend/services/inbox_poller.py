from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from datetime import timedelta, timezone
from collections.abc import Callable
from uuid import uuid4

from sqlalchemy import or_, update
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from sutra_backend.config import Settings
from sutra_backend.models import PollerLease, Team, User, utcnow
from sutra_backend.services.team_runtime import run_team_inbox_cycle

POLL_LEASE_NAME = "inbox_poller"


@dataclass(frozen=True)
class InboxPollerStatus:
    enabled: bool
    interval_seconds: int
    lease_seconds: int
    max_tasks_per_sweep: int
    is_active: bool
    lease: PollerLease | None


def _get_or_create_poller_lease(session: Session, *, name: str = POLL_LEASE_NAME) -> PollerLease:
    lease = session.exec(select(PollerLease).where(PollerLease.name == name)).first()
    if lease is not None:
        return lease

    lease = PollerLease(name=name)
    session.add(lease)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
    lease = session.exec(select(PollerLease).where(PollerLease.name == name)).first()
    if lease is None:
        raise RuntimeError("Failed to initialize poller lease.")
    return lease


def _lease_is_active(lease: PollerLease | None, *, now=None) -> bool:
    if lease is None or lease.owner_id is None or lease.lease_expires_at is None:
        return False
    reference_time = now or utcnow()
    expires_at = lease.lease_expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if reference_time.tzinfo is None:
        reference_time = reference_time.replace(tzinfo=timezone.utc)
    return expires_at > reference_time


def read_inbox_poller_status(*, session: Session, settings: Settings) -> InboxPollerStatus:
    lease = session.exec(select(PollerLease).where(PollerLease.name == POLL_LEASE_NAME)).first()
    return InboxPollerStatus(
        enabled=settings.inbox_poller_enabled,
        interval_seconds=settings.inbox_poller_interval_seconds,
        lease_seconds=settings.inbox_poller_lease_seconds,
        max_tasks_per_sweep=settings.inbox_poller_max_tasks_per_sweep,
        is_active=_lease_is_active(lease),
        lease=lease,
    )


def _acquire_poller_lease(
    session: Session,
    *,
    owner_id: str,
    settings: Settings,
) -> tuple[bool, PollerLease]:
    _get_or_create_poller_lease(session)
    now = utcnow()
    lease_expires_at = now + timedelta(seconds=max(1, settings.inbox_poller_lease_seconds))
    result = session.exec(
        update(PollerLease)
        .where(PollerLease.name == POLL_LEASE_NAME)
        .where(
            or_(
                PollerLease.owner_id == owner_id,
                PollerLease.lease_expires_at.is_(None),
                PollerLease.lease_expires_at <= now,
            )
        )
        .values(
            owner_id=owner_id,
            state="running",
            last_heartbeat_at=now,
            lease_expires_at=lease_expires_at,
            last_sweep_started_at=now,
            updated_at=now,
        )
    )
    session.commit()
    lease = _get_or_create_poller_lease(session)
    acquired = bool(result.rowcount) and lease.owner_id == owner_id
    return acquired, lease


def _heartbeat_poller_lease(
    session: Session,
    *,
    owner_id: str,
    settings: Settings,
) -> PollerLease:
    now = utcnow()
    lease_expires_at = now + timedelta(seconds=max(1, settings.inbox_poller_lease_seconds))
    session.exec(
        update(PollerLease)
        .where(PollerLease.name == POLL_LEASE_NAME)
        .where(PollerLease.owner_id == owner_id)
        .values(
            state="running",
            last_heartbeat_at=now,
            lease_expires_at=lease_expires_at,
            updated_at=now,
        )
    )
    session.commit()
    return _get_or_create_poller_lease(session)


def _complete_poller_sweep(
    session: Session,
    *,
    owner_id: str,
    settings: Settings,
    executed_count: int,
) -> PollerLease:
    now = utcnow()
    lease_expires_at = now + timedelta(seconds=max(1, settings.inbox_poller_lease_seconds))
    session.exec(
        update(PollerLease)
        .where(PollerLease.name == POLL_LEASE_NAME)
        .where(PollerLease.owner_id == owner_id)
        .values(
            state="idle",
            last_heartbeat_at=now,
            lease_expires_at=lease_expires_at,
            last_sweep_completed_at=now,
            last_executed_count=executed_count,
            updated_at=now,
        )
    )
    session.commit()
    return _get_or_create_poller_lease(session)


async def run_inbox_poller_sweep(
    *,
    session: Session,
    settings: Settings,
    owner_id: str = "sutra-inbox-poller",
) -> int:
    acquired, _lease = _acquire_poller_lease(
        session,
        owner_id=owner_id,
        settings=settings,
    )
    if not acquired:
        return 0

    executed_count = 0
    max_tasks = max(1, settings.inbox_poller_max_tasks_per_sweep)
    teams = session.exec(select(Team).order_by(Team.created_at.asc())).all()
    for team in teams:
        if executed_count >= max_tasks:
            break
        user = session.exec(select(User).where(User.id == team.user_id)).first()
        if user is None:
            continue
        results = await run_team_inbox_cycle(
            session,
            user=user,
            team_id=team.id,
            settings=settings,
            max_tasks=max_tasks - executed_count,
        )
        executed_count += sum(1 for item in results if item.task is not None)
        _heartbeat_poller_lease(
            session,
            owner_id=owner_id,
            settings=settings,
        )
        if executed_count >= max_tasks:
            break
    _complete_poller_sweep(
        session,
        owner_id=owner_id,
        settings=settings,
        executed_count=executed_count,
    )
    return executed_count


class InboxPoller:
    def __init__(
        self,
        *,
        settings: Settings,
        session_factory: Callable[[], Session],
    ) -> None:
        self._settings = settings
        self._session_factory = session_factory
        self._task: asyncio.Task[None] | None = None
        self._owner_id = f"{os.getpid()}:{uuid4()}"

    async def start(self) -> None:
        if self._task is not None or not self._settings.inbox_poller_enabled:
            return
        self._task = asyncio.create_task(self._run_loop(), name="sutra-inbox-poller")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        finally:
            self._task = None

    async def run_once(self) -> int:
        with self._session_factory() as session:
            return await run_inbox_poller_sweep(
                session=session,
                settings=self._settings,
                owner_id=self._owner_id,
            )

    async def _run_loop(self) -> None:
        try:
            while True:
                await self.run_once()
                await asyncio.sleep(max(1, self._settings.inbox_poller_interval_seconds))
        except asyncio.CancelledError:
            raise
