from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlmodel import Session, select

from sutra_backend.config import Settings
from sutra_backend.models import Agent, AutomationJob, User, utcnow
from sutra_backend.schemas.runtime import AgentResponseCreateRequest
from sutra_backend.services.agent_teams import (
    get_owned_agent as find_owned_agent,
    get_owned_team,
    get_team_assignment,
    list_owned_agents,
)
from sutra_backend.services.runtime import AgentNotFoundError, run_agent_response


class AutomationJobError(RuntimeError):
    """Raised when an automation job cannot be safely created or executed."""


@dataclass(frozen=True)
class AutomationJobRunResult:
    job: AutomationJob
    conversation_id: UUID | None
    response_id: str | None
    output_text: str | None
    workspace_item_id: UUID | None
    generated_items: list


def _get_owned_agent(session: Session, *, user: User, agent_id: UUID) -> Agent:
    agent = find_owned_agent(session, agent_id=agent_id, user=user)
    if agent is None:
        raise AgentNotFoundError("Agent not found.")
    return agent


def get_owned_job(session: Session, *, user: User, job_id: UUID) -> AutomationJob:
    job = session.get(AutomationJob, job_id)
    if job is None:
        raise AutomationJobError("Automation job not found.")
    _get_owned_agent(session, user=user, agent_id=job.agent_id)
    if job.agent_team_id is not None:
        team = get_owned_team(session, team_id=job.agent_team_id, user=user)
        if team is None:
            raise AutomationJobError("Automation job team not found.")
        if get_team_assignment(session, team_id=team.id, agent_id=job.agent_id) is None:
            raise AutomationJobError("Automation job agent must belong to the selected team.")
    return job


def list_jobs(
    session: Session,
    *,
    user: User,
    agent_team_id: UUID | None = None,
    agent_id: UUID | None = None,
) -> list[AutomationJob]:
    statement = select(AutomationJob).order_by(AutomationJob.created_at.desc())
    if agent_id is not None:
        agent = _get_owned_agent(session, user=user, agent_id=agent_id)
        statement = statement.where(AutomationJob.agent_id == agent.id)
    else:
        owned_agent_ids = [agent.id for agent in list_owned_agents(session, user=user)]
        if not owned_agent_ids:
            return []
        statement = statement.where(AutomationJob.agent_id.in_(owned_agent_ids))
    if agent_team_id is not None:
        team = get_owned_team(session, team_id=agent_team_id, user=user)
        if team is None:
            raise AutomationJobError("Automation job team not found.")
        statement = statement.where(AutomationJob.agent_team_id == team.id)
    return session.exec(statement).all()


def create_job(
    session: Session,
    *,
    user: User,
    name: str,
    schedule: str,
    prompt: str,
    agent_id: UUID,
    agent_team_id: UUID | None,
    enabled: bool,
) -> AutomationJob:
    if not name.strip():
        raise AutomationJobError("Automation job name is required.")
    if not schedule.strip():
        raise AutomationJobError("Automation job schedule is required.")
    if not prompt.strip():
        raise AutomationJobError("Automation job prompt is required.")

    agent = _get_owned_agent(session, user=user, agent_id=agent_id)
    if agent_team_id is not None:
        team = get_owned_team(session, team_id=agent_team_id, user=user)
        if team is None:
            raise AutomationJobError("Automation job team not found.")
        if get_team_assignment(session, team_id=team.id, agent_id=agent.id) is None:
            raise AutomationJobError("Automation job agent must belong to the selected team.")

    job = AutomationJob(
        agent_id=agent.id,
        agent_team_id=agent_team_id,
        name=name.strip(),
        schedule=schedule.strip(),
        prompt=prompt.strip(),
        enabled=enabled,
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def update_job(
    session: Session,
    *,
    user: User,
    job_id: UUID,
    name: str | None,
    schedule: str | None,
    prompt: str | None,
    enabled: bool | None,
) -> AutomationJob:
    job = get_owned_job(session, user=user, job_id=job_id)
    if name is not None:
        if not name.strip():
            raise AutomationJobError("Automation job name is required.")
        job.name = name.strip()
    if schedule is not None:
        if not schedule.strip():
            raise AutomationJobError("Automation job schedule is required.")
        job.schedule = schedule.strip()
    if prompt is not None:
        if not prompt.strip():
            raise AutomationJobError("Automation job prompt is required.")
        job.prompt = prompt.strip()
    if enabled is not None:
        job.enabled = enabled
    job.updated_at = utcnow()
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


async def run_job(
    session: Session,
    *,
    user: User,
    job_id: UUID,
    settings: Settings,
) -> AutomationJobRunResult:
    job = get_owned_job(session, user=user, job_id=job_id)
    if not job.enabled:
        raise AutomationJobError("Automation job is disabled.")

    result = await run_agent_response(
        session,
        user=user,
        agent_id=job.agent_id,
        request=AgentResponseCreateRequest(
            input=job.prompt,
            metadata={
                "sutra_event": "automation_job_run",
                "automation_job_id": str(job.id),
                "sutra_agent_team_id": str(job.agent_team_id) if job.agent_team_id is not None else None,
            },
        ),
        conversation_id=None,
        settings=settings,
    )
    job.last_run_at = utcnow()
    job.updated_at = job.last_run_at
    session.add(job)
    session.commit()
    session.refresh(job)
    return AutomationJobRunResult(
        job=job,
        conversation_id=result.conversation.id,
        response_id=result.runtime_response.response_id,
        output_text=result.runtime_response.output_text,
        workspace_item_id=result.workspace_item_id,
        generated_items=[],
    )
