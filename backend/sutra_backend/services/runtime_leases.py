from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from sutra_backend.config import Settings
from sutra_backend.models import RuntimeLease, User
from sutra_backend.runtime.provisioning import ensure_agent_runtime_lease
from sutra_backend.services.runtime import AgentNotFoundError, get_owned_agent


def read_agent_runtime_lease(session: Session, *, user: User, agent_id: UUID) -> RuntimeLease:
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
    agent = get_owned_agent(session, agent_id=agent_id, user=user)
    return ensure_agent_runtime_lease(session, agent=agent, settings=settings)
