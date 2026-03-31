from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import timezone
from uuid import UUID

from sqlmodel import Session, select

from sutra_backend.config import Settings
from sutra_backend.models import RuntimeLease, User, utcnow
from sutra_backend.runtime.client import RuntimeHealthProbe, probe_runtime_health
from sutra_backend.runtime.errors import RuntimeNotReadyError
from sutra_backend.runtime.provisioning import ensure_agent_runtime_lease


@dataclass(frozen=True)
class RuntimeLeaseStatus:
    lease: RuntimeLease
    ready: bool
    heartbeat_fresh: bool
    readiness_reason: str


def _normalize_datetime(value):
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def summarize_runtime_lease(
    *,
    lease: RuntimeLease,
    settings: Settings,
    health_detail: str | None = None,
) -> RuntimeLeaseStatus:
    now = _normalize_datetime(utcnow())
    heartbeat_at = _normalize_datetime(lease.last_heartbeat_at or lease.updated_at or lease.started_at)
    heartbeat_fresh = False
    if heartbeat_at is not None:
        heartbeat_fresh = (
            now - heartbeat_at
        ).total_seconds() <= max(1, settings.runtime_heartbeat_stale_seconds)

    if lease.state == "unreachable":
        ready = False
        readiness_reason = health_detail or "Runtime API is not reachable yet."
    elif lease.state != "running":
        ready = False
        readiness_reason = "Runtime is still provisioning."
    elif not lease.api_base_url:
        ready = False
        readiness_reason = "Runtime does not have an internal API endpoint yet."
    elif not heartbeat_fresh:
        ready = False
        readiness_reason = "Runtime heartbeat is stale."
    else:
        ready = True
        readiness_reason = "Runtime is ready for requests."

    return RuntimeLeaseStatus(
        lease=lease,
        ready=ready,
        heartbeat_fresh=heartbeat_fresh,
        readiness_reason=readiness_reason,
    )


def reconcile_runtime_lease(
    session: Session,
    *,
    user: User,
    agent_id: UUID,
    settings: Settings,
    probe: Callable[..., RuntimeHealthProbe] | None = None,
) -> RuntimeLeaseStatus:
    from sutra_backend.services.runtime import AgentNotFoundError, build_runtime_target, get_owned_agent

    agent = get_owned_agent(session, agent_id=agent_id, user=user)
    lease = session.exec(select(RuntimeLease).where(RuntimeLease.agent_id == agent.id)).first()
    if lease is None:
        raise AgentNotFoundError("Runtime lease not found.")

    current = summarize_runtime_lease(lease=lease, settings=settings)
    if current.ready or lease.state not in {"running", "unreachable"} or not lease.api_base_url:
        return current

    probe_impl = probe or probe_runtime_health
    try:
        target = build_runtime_target(lease=lease, settings=settings)
    except RuntimeNotReadyError as exc:
        return summarize_runtime_lease(lease=lease, settings=settings, health_detail=str(exc))

    health = probe_impl(
        target,
        timeout_seconds=min(5.0, float(settings.hermes_api_route_timeout_seconds)),
    )
    now = utcnow()
    lease.last_heartbeat_at = now
    lease.updated_at = now
    if health.reachable:
        lease.state = "running"
        agent.status = "ready"
    else:
        lease.state = "unreachable"
        agent.status = "runtime_unreachable"
    session.add(lease)
    session.add(agent)
    session.commit()
    session.refresh(lease)

    return summarize_runtime_lease(
        lease=lease,
        settings=settings,
        health_detail=health.detail,
    )


def read_agent_runtime_lease(session: Session, *, user: User, agent_id: UUID) -> RuntimeLease:
    from sutra_backend.services.runtime import AgentNotFoundError, get_owned_agent

    agent = get_owned_agent(session, agent_id=agent_id, user=user)
    lease = session.exec(select(RuntimeLease).where(RuntimeLease.agent_id == agent.id)).first()
    if lease is None:
        raise AgentNotFoundError("Runtime lease not found.")
    return lease


def provision_agent_runtime_lease(
    session: Session,
    *,
    user: User,
    agent_id: UUID,
    settings: Settings,
) -> RuntimeLease:
    from sutra_backend.services.runtime import get_owned_agent

    agent = get_owned_agent(session, agent_id=agent_id, user=user)
    return ensure_agent_runtime_lease(session, agent=agent, settings=settings)
