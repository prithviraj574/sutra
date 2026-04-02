from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import timezone
from pathlib import PurePosixPath
from uuid import UUID

from sqlmodel import Session, select

from sutra_backend.config import Settings
from sutra_backend.models import Agent, RuntimeLease, Team, User, utcnow
from sutra_backend.runtime.client import (
    HermesRuntimeClient,
    ResponsesRequest,
    RuntimeHealthProbe,
    probe_runtime_health,
)
from sutra_backend.runtime.errors import RuntimeNotReadyError
from sutra_backend.runtime.firecracker_host import (
    build_agent_hermes_home_path,
    build_agent_private_volume_path,
    build_team_shared_workspace_path,
)
from sutra_backend.runtime.provisioning import (
    ensure_agent_runtime_lease,
    restart_agent_runtime_lease,
    sync_runtime_lease_with_settings,
)


@dataclass(frozen=True)
class RuntimeLeaseStatus:
    agent: Agent
    lease: RuntimeLease
    provider: str
    ready: bool
    heartbeat_fresh: bool
    readiness_stage: str
    readiness_reason: str
    probe_detail: str | None
    probe_checked_url: str | None
    isolation_ok: bool
    isolation_reason: str


def _normalize_datetime(value):
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _infer_runtime_provider(*, lease: RuntimeLease, settings: Settings) -> str:
    if lease.vm_id.startswith("local-dev-"):
        return "static_dev"
    return settings.runtime_provider


def _is_parent_or_same(parent: PurePosixPath, child: PurePosixPath) -> bool:
    return child == parent or parent in child.parents


def assess_agent_runtime_isolation(
    session: Session,
    *,
    agent: Agent,
    settings: Settings,
) -> tuple[bool, str]:
    sibling_agents = session.exec(
        select(Agent).where(Agent.team_id == agent.team_id).where(Agent.id != agent.id)
    ).all()

    if not agent.hermes_home_uri:
        return False, "Agent is missing a private HERMES_HOME URI."
    if not agent.private_volume_uri:
        return False, "Agent is missing a private volume URI."
    if agent.hermes_home_uri == agent.private_volume_uri:
        return False, "Agent HERMES_HOME and private volume must be distinct."

    for sibling in sibling_agents:
        if sibling.hermes_home_uri and sibling.hermes_home_uri == agent.hermes_home_uri:
            return False, "Agent HERMES_HOME URI collides with another agent."
        if sibling.private_volume_uri and sibling.private_volume_uri == agent.private_volume_uri:
            return False, "Agent private volume URI collides with another agent."
        if sibling.hermes_home_uri and sibling.hermes_home_uri == agent.private_volume_uri:
            return False, "Agent private volume URI collides with another agent's HERMES_HOME."
        if sibling.private_volume_uri and sibling.private_volume_uri == agent.hermes_home_uri:
            return False, "Agent HERMES_HOME URI collides with another agent's private volume."

    state_mount = PurePosixPath(settings.gcp_runtime_state_mount_path)
    agent_root = PurePosixPath(settings.gcp_runtime_agent_root_path)
    shared_workspace_root = PurePosixPath(settings.gcp_runtime_shared_workspace_root_path)
    hermes_home_path = PurePosixPath(build_agent_hermes_home_path(settings=settings, agent=agent))
    private_volume_path = PurePosixPath(
        build_agent_private_volume_path(settings=settings, agent=agent)
    )
    shared_workspace_path_raw = build_team_shared_workspace_path(settings=settings, agent=agent)

    if not _is_parent_or_same(state_mount, hermes_home_path):
        return False, "Agent HERMES_HOME path must live under the private state mount."
    if not _is_parent_or_same(state_mount, private_volume_path):
        return False, "Agent private volume path must live under the private state mount."
    if not _is_parent_or_same(agent_root, hermes_home_path):
        return False, "Agent HERMES_HOME path must live under the agent root."
    if not _is_parent_or_same(agent_root, private_volume_path):
        return False, "Agent private volume path must live under the agent root."
    if hermes_home_path == private_volume_path:
        return False, "Agent HERMES_HOME path and private volume path must be distinct."
    if shared_workspace_path_raw is not None:
        shared_workspace_path = PurePosixPath(shared_workspace_path_raw)
        if not _is_parent_or_same(shared_workspace_root, shared_workspace_path):
            return False, "Shared workspace path must live under the shared workspace root."
        if _is_parent_or_same(shared_workspace_path, hermes_home_path):
            return False, "Shared workspace path must not contain the private HERMES_HOME path."
        if _is_parent_or_same(shared_workspace_path, private_volume_path):
            return False, "Shared workspace path must not contain the private volume path."

    team = session.get(Team, agent.team_id)
    if team is not None and team.shared_workspace_uri:
        if team.shared_workspace_uri == agent.hermes_home_uri:
            return False, "Shared workspace URI must not equal the agent HERMES_HOME URI."
        if team.shared_workspace_uri == agent.private_volume_uri:
            return False, "Shared workspace URI must not equal the agent private volume URI."

    return True, "Agent private storage is isolated from sibling agents; only the shared workspace may be shared."


def summarize_runtime_lease(
    *,
    agent: Agent,
    session: Session,
    lease: RuntimeLease,
    settings: Settings,
    health_detail: str | None = None,
    probe_checked_url: str | None = None,
    readiness_stage: str | None = None,
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

    if readiness_stage is None:
        if lease.state == "unreachable":
            readiness_stage = "unreachable"
        elif lease.state != "running" or not lease.api_base_url:
            readiness_stage = "provisioning"
        else:
            readiness_stage = "api_reachable"

    isolation_ok, isolation_reason = assess_agent_runtime_isolation(
        session,
        agent=agent,
        settings=settings,
    )

    return RuntimeLeaseStatus(
        agent=agent,
        lease=lease,
        provider=_infer_runtime_provider(lease=lease, settings=settings),
        ready=ready,
        heartbeat_fresh=heartbeat_fresh,
        readiness_stage=readiness_stage,
        readiness_reason=readiness_reason,
        probe_detail=health_detail,
        probe_checked_url=probe_checked_url,
        isolation_ok=isolation_ok,
        isolation_reason=isolation_reason,
    )


def summarize_unprovisioned_runtime(
    *,
    agent: Agent,
    session: Session,
    settings: Settings,
) -> RuntimeLeaseStatus:
    placeholder_lease = RuntimeLease(
        agent_id=agent.id,
        vm_id=f"pending-{str(agent.id)[:8]}",
        state="provisioning",
        api_base_url=None,
    )
    return summarize_runtime_lease(
        agent=agent,
        session=session,
        lease=placeholder_lease,
        settings=settings,
        readiness_stage="not_provisioned",
        health_detail="Runtime has not been provisioned yet.",
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
        return summarize_unprovisioned_runtime(agent=agent, session=session, settings=settings)
    lease_provider = "static_dev" if lease.vm_id.startswith("local-dev-") else "gcp_firecracker"
    if lease_provider != settings.runtime_provider:
        if settings.runtime_provider == "static_dev" and settings.dev_runtime_base_url:
            lease = ensure_agent_runtime_lease(session, agent=agent, settings=settings)
        else:
            return summarize_unprovisioned_runtime(agent=agent, session=session, settings=settings)
    if sync_runtime_lease_with_settings(lease=lease, settings=settings):
        session.add(lease)
        session.commit()
        session.refresh(lease)

    current = summarize_runtime_lease(
        agent=agent,
        session=session,
        lease=lease,
        settings=settings,
    )
    if current.ready or lease.state not in {"running", "unreachable"} or not lease.api_base_url:
        return current

    probe_impl = probe or probe_runtime_health
    try:
        target = build_runtime_target(lease=lease, settings=settings)
    except RuntimeNotReadyError as exc:
        return summarize_runtime_lease(
            agent=agent,
            session=session,
            lease=lease,
            settings=settings,
            health_detail=str(exc),
        )

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
        agent=agent,
        session=session,
        lease=lease,
        settings=settings,
        health_detail=health.detail,
        probe_checked_url=health.checked_url,
    )


async def verify_runtime_lease(
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

    base_status = reconcile_runtime_lease(
        session,
        user=user,
        agent_id=agent_id,
        settings=settings,
        probe=probe,
    )
    lease = base_status.lease
    if lease.state != "running" or not lease.api_base_url:
        return base_status

    try:
        target = build_runtime_target(lease=lease, settings=settings)
    except RuntimeNotReadyError as exc:
        return summarize_runtime_lease(
            agent=agent,
            session=session,
            lease=lease,
            settings=settings,
            health_detail=str(exc),
            readiness_stage="api_reachable",
        )

    runtime_client = HermesRuntimeClient(
        target=target,
        timeout_seconds=min(15, settings.hermes_api_route_timeout_seconds),
    )
    try:
        await runtime_client.create_response(
            ResponsesRequest(
                input="Reply with READY only.",
                conversation=f"sutra:runtime-verify:{agent.id}",
                store=False,
                metadata={"sutra_event": "runtime_verify"},
            )
        )
    except Exception as exc:
        return summarize_runtime_lease(
            agent=agent,
            session=session,
            lease=lease,
            settings=settings,
            health_detail=f"Runtime responses verification failed: {exc}",
            readiness_stage="api_reachable",
        )

    return summarize_runtime_lease(
        agent=agent,
        session=session,
        lease=lease,
        settings=settings,
        health_detail="Runtime accepted a verification response request.",
        probe_checked_url=f"{lease.api_base_url.rstrip('/')}/v1/responses",
        readiness_stage="responses_ready",
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


def restart_runtime_lease(
    session: Session,
    *,
    user: User,
    agent_id: UUID,
    settings: Settings,
) -> RuntimeLeaseStatus:
    from sutra_backend.services.runtime import get_owned_agent

    agent = get_owned_agent(session, agent_id=agent_id, user=user)
    lease = restart_agent_runtime_lease(session, agent=agent, settings=settings)
    return summarize_runtime_lease(
        agent=agent,
        session=session,
        lease=lease,
        settings=settings,
    )
