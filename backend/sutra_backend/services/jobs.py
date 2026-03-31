from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlmodel import Session, select

from sutra_backend.config import Settings
from sutra_backend.models import Agent, AutomationJob, Team, User, utcnow
from sutra_backend.schemas.runtime import AgentResponseCreateRequest
from sutra_backend.services.runtime import AgentNotFoundError, run_agent_response
from sutra_backend.services.team_runtime import TeamResponseResult, get_owned_team, run_team_response


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
    agent = session.exec(
        select(Agent)
        .join(Team, Team.id == Agent.team_id)
        .where(Agent.id == agent_id)
        .where(Team.user_id == user.id)
    ).first()
    if agent is None:
        raise AgentNotFoundError("Agent not found.")
    return agent


def get_owned_job(session: Session, *, user: User, job_id: UUID) -> AutomationJob:
    job = session.get(AutomationJob, job_id)
    if job is None:
        raise AutomationJobError("Automation job not found.")
    if job.team_id is not None:
        get_owned_team(session, team_id=job.team_id, user=user)
    elif job.agent_id is not None:
        _get_owned_agent(session, user=user, agent_id=job.agent_id)
    else:
        raise AutomationJobError("Automation job does not belong to an owned team or agent.")
    return job


def list_jobs(
    session: Session,
    *,
    user: User,
    team_id: UUID | None = None,
    agent_id: UUID | None = None,
) -> list[AutomationJob]:
    statement = select(AutomationJob).order_by(AutomationJob.created_at.desc())
    if team_id is not None:
        team = get_owned_team(session, team_id=team_id, user=user)
        statement = statement.where(AutomationJob.team_id == team.id)
    else:
        team_ids = [team.id for team in session.exec(select(Team).where(Team.user_id == user.id)).all()]
        if not team_ids:
            return []
        statement = statement.where(AutomationJob.team_id.in_(team_ids))
    if agent_id is not None:
        agent = _get_owned_agent(session, user=user, agent_id=agent_id)
        statement = statement.where(AutomationJob.agent_id == agent.id)
    return session.exec(statement).all()


def create_job(
    session: Session,
    *,
    user: User,
    name: str,
    schedule: str,
    prompt: str,
    team_id: UUID | None,
    agent_id: UUID | None,
    enabled: bool,
) -> AutomationJob:
    if not name.strip():
        raise AutomationJobError("Automation job name is required.")
    if not schedule.strip():
        raise AutomationJobError("Automation job schedule is required.")
    if not prompt.strip():
        raise AutomationJobError("Automation job prompt is required.")
    if team_id is None and agent_id is None:
        raise AutomationJobError("Automation job must target a team or an agent.")

    team: Team | None = None
    agent: Agent | None = None
    if team_id is not None:
        team = get_owned_team(session, team_id=team_id, user=user)
    if agent_id is not None:
        agent = _get_owned_agent(session, user=user, agent_id=agent_id)
        if team is None:
            team = session.get(Team, agent.team_id)
        elif agent.team_id != team.id:
            raise AutomationJobError("Automation job agent must belong to the selected team.")

    job = AutomationJob(
        team_id=team.id if team is not None else None,
        agent_id=agent.id if agent is not None else None,
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

    if job.agent_id is not None:
        result = await run_agent_response(
            session,
            user=user,
            agent_id=job.agent_id,
            request=AgentResponseCreateRequest(
                input=job.prompt,
                metadata={
                    "sutra_event": "automation_job_run",
                    "automation_job_id": str(job.id),
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

    if job.team_id is None:
        raise AutomationJobError("Automation job does not target a team or agent.")

    team_result: TeamResponseResult = await run_team_response(
        session,
        user=user,
        team_id=job.team_id,
        user_input=job.prompt,
        conversation_id=None,
        instructions=None,
        secret_ids=[],
        settings=settings,
    )
    job.last_run_at = utcnow()
    job.updated_at = job.last_run_at
    session.add(job)
    session.commit()
    session.refresh(job)
    return AutomationJobRunResult(
        job=job,
        conversation_id=team_result.conversation.id,
        response_id=team_result.outputs[-1].response_id if team_result.outputs else None,
        output_text="\n\n".join(output.output_text for output in team_result.outputs),
        workspace_item_id=team_result.workspace_item_id,
        generated_items=team_result.generated_items,
    )
