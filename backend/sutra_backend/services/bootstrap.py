from __future__ import annotations

from dataclasses import dataclass

from sqlmodel import Session, select

from sutra_backend.config import Settings
from sutra_backend.models import Agent, AgentTeam, AgentTeamAssignment, RoleTemplate, User
from sutra_backend.runtime.errors import RuntimeNotReadyError
from sutra_backend.runtime.provisioning import ensure_agent_runtime_lease
from sutra_backend.services.agent_teams import create_team_assignment


@dataclass(frozen=True)
class RoleTemplateSeed:
    key: str
    name: str
    description: str
    default_system_prompt: str
    default_tool_profile: str = "full_web"


DEFAULT_ROLE_TEMPLATES: tuple[RoleTemplateSeed, ...] = (
    RoleTemplateSeed(
        key="generalist",
        name="Generalist",
        description="Default day-to-day agent for product, research, and execution tasks.",
        default_system_prompt="Act as Sutra's default persistent generalist. Be practical, proactive, and execution-oriented.",
    ),
    RoleTemplateSeed(
        key="planner",
        name="Planner",
        description="Shapes work, breaks problems down, and coordinates agent teams.",
        default_system_prompt="Plan work clearly, de-risk execution, and delegate cleanly when multiple agents are available.",
    ),
    RoleTemplateSeed(
        key="researcher",
        name="Researcher",
        description="Investigates technical, product, and market questions with source discipline.",
        default_system_prompt="Research carefully, verify claims, and summarize findings with clear tradeoffs.",
    ),
    RoleTemplateSeed(
        key="builder",
        name="Builder",
        description="Implements and verifies product changes across code and runtime surfaces.",
        default_system_prompt="Build working product increments, verify outcomes, and keep momentum high.",
    ),
)


def ensure_role_templates(session: Session) -> dict[str, RoleTemplate]:
    templates_by_key = {
        template.key: template
        for template in session.exec(select(RoleTemplate)).all()
    }

    for seed in DEFAULT_ROLE_TEMPLATES:
        if seed.key in templates_by_key:
            continue

        template = RoleTemplate(
            key=seed.key,
            name=seed.name,
            description=seed.description,
            default_system_prompt=seed.default_system_prompt,
            default_tool_profile=seed.default_tool_profile,
        )
        session.add(template)
        templates_by_key[seed.key] = template

    session.commit()

    refreshed_templates = {
        template.key: template
        for template in session.exec(select(RoleTemplate)).all()
    }
    return refreshed_templates


def ensure_personal_workspace(
    session: Session,
    user: User,
    *,
    settings: Settings | None = None,
) -> tuple[AgentTeam, Agent]:
    templates_by_key = ensure_role_templates(session)
    default_template = templates_by_key["generalist"]

    team = session.exec(
        select(AgentTeam).where(AgentTeam.user_id == user.id).where(AgentTeam.mode == "personal")
    ).first()
    if team is None:
        team = AgentTeam(
            user_id=user.id,
            name="My Workspace",
            description="Default personal workspace for a single user and their persistent agents.",
            mode="personal",
        )
        session.add(team)
        session.commit()
        session.refresh(team)

    agent = session.exec(
        select(Agent)
        .join(AgentTeamAssignment, AgentTeamAssignment.agent_id == Agent.id)
        .where(Agent.user_id == user.id)
        .where(AgentTeamAssignment.agent_team_id == team.id)
    ).first()
    if agent is None:
        agent = Agent(
            user_id=user.id,
            role_template_id=default_template.id,
            name="Default Agent",
            role_name=default_template.name,
            status="provisioning",
        )
        session.add(agent)
        session.commit()
        session.refresh(agent)
        create_team_assignment(
            session,
            team_id=team.id,
            agent_id=agent.id,
            shared_workspace_enabled=True,
        )
        session.commit()
        if settings is not None:
            try:
                ensure_agent_runtime_lease(session, agent=agent, settings=settings)
            except RuntimeNotReadyError:
                session.refresh(agent)

    return team, agent
