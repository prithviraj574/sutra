from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sqlmodel import Session, select

from sutra_backend.models import Agent, AgentTeam, AgentTeamAssignment, User


def get_owned_agent(session: Session, *, agent_id: UUID, user: User) -> Agent | None:
    return session.exec(
        select(Agent)
        .where(Agent.id == agent_id)
        .where(Agent.user_id == user.id)
    ).first()


def get_owned_team(session: Session, *, team_id: UUID, user: User) -> AgentTeam | None:
    return session.exec(
        select(AgentTeam)
        .where(AgentTeam.id == team_id)
        .where(AgentTeam.user_id == user.id)
    ).first()


def list_owned_agents(session: Session, *, user: User) -> list[Agent]:
    return session.exec(
        select(Agent)
        .where(Agent.user_id == user.id)
        .order_by(Agent.created_at.asc())
    ).all()


def list_team_agents(session: Session, *, team_id: UUID) -> list[Agent]:
    return session.exec(
        select(Agent)
        .join(AgentTeamAssignment, AgentTeamAssignment.agent_id == Agent.id)
        .where(AgentTeamAssignment.agent_team_id == team_id)
        .order_by(Agent.created_at.asc())
    ).all()


def get_team_assignment(
    session: Session,
    *,
    team_id: UUID,
    agent_id: UUID,
) -> AgentTeamAssignment | None:
    return session.exec(
        select(AgentTeamAssignment)
        .where(AgentTeamAssignment.agent_team_id == team_id)
        .where(AgentTeamAssignment.agent_id == agent_id)
    ).first()


def list_assignments_for_agents(
    session: Session,
    *,
    agent_ids: list[UUID],
) -> dict[UUID, list[AgentTeamAssignment]]:
    if not agent_ids:
        return {}
    assignments = session.exec(
        select(AgentTeamAssignment)
        .where(AgentTeamAssignment.agent_id.in_(agent_ids))
        .order_by(AgentTeamAssignment.created_at.asc())
    ).all()
    grouped: dict[UUID, list[AgentTeamAssignment]] = defaultdict(list)
    for assignment in assignments:
        grouped[assignment.agent_id].append(assignment)
    return dict(grouped)


def list_team_ids_for_agents(
    session: Session,
    *,
    agent_ids: list[UUID],
) -> dict[UUID, list[UUID]]:
    assignments_by_agent = list_assignments_for_agents(session, agent_ids=agent_ids)
    return {
        agent_id: [assignment.agent_team_id for assignment in assignments]
        for agent_id, assignments in assignments_by_agent.items()
    }


def find_personal_team_for_agent(
    session: Session,
    *,
    agent_id: UUID,
) -> AgentTeam | None:
    return session.exec(
        select(AgentTeam)
        .join(AgentTeamAssignment, AgentTeamAssignment.agent_team_id == AgentTeam.id)
        .where(AgentTeamAssignment.agent_id == agent_id)
        .where(AgentTeam.mode == "personal")
        .order_by(AgentTeam.created_at.asc())
    ).first()


def create_team_assignment(
    session: Session,
    *,
    team_id: UUID,
    agent_id: UUID,
    shared_workspace_enabled: bool = True,
) -> AgentTeamAssignment:
    assignment = AgentTeamAssignment(
        agent_team_id=team_id,
        agent_id=agent_id,
        shared_workspace_enabled=shared_workspace_enabled,
    )
    session.add(assignment)
    return assignment
