from __future__ import annotations

from sqlmodel import Session, SQLModel, select

from sutra_backend.db import create_database_engine
from sutra_backend.models import (
    Agent,
    Artifact,
    AutomationJob,
    Conversation,
    GitHubConnection,
    Message,
    RoleTemplate,
    RuntimeLease,
    Secret,
    Team,
    ToolEvent,
    User,
)
from sutra_backend.services.bootstrap import ensure_personal_workspace


def test_core_phase_one_models_persist_to_postgres(postgres_database_url: str) -> None:
    engine = create_database_engine(postgres_database_url)
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        user = User(firebase_uid="firebase-user-1", email="user@example.com")
        session.add(user)
        session.commit()
        session.refresh(user)

        team = Team(user_id=user.id, name="Default Team", mode="team")
        role_template = RoleTemplate(
            key="planner",
            name="Planner",
            default_system_prompt="Plan and delegate work.",
        )
        session.add(team)
        session.add(role_template)
        session.commit()
        session.refresh(team)
        session.refresh(role_template)

        agent = Agent(
            team_id=team.id,
            role_template_id=role_template.id,
            name="Lead Agent",
            role_name="Planner",
            status="running",
            hermes_home_uri="gs://sutra-dev/agents/lead/hermes-home",
            private_volume_uri="projects/dev/volumes/lead",
        )
        session.add(agent)
        session.commit()
        session.refresh(agent)

        conversation = Conversation(team_id=team.id, agent_id=agent.id, mode="single_agent")
        session.add(conversation)
        session.commit()
        session.refresh(conversation)

        message = Message(
            conversation_id=conversation.id,
            actor_type="user",
            content="Build the initial scaffold",
            response_chain_id="resp_123",
        )
        session.add(message)
        session.commit()
        session.refresh(message)

        session.add(
            ToolEvent(
                conversation_id=conversation.id,
                agent_id=agent.id,
                message_id=message.id,
                tool_name="terminal",
                event_type="started",
            )
        )
        session.add(
            Artifact(
                team_id=team.id,
                conversation_id=conversation.id,
                agent_id=agent.id,
                name="scaffold.md",
                uri="gs://sutra-dev/artifacts/scaffold.md",
            )
        )
        session.add(
            Secret(
                user_id=user.id,
                team_id=team.id,
                agent_id=agent.id,
                name="GITHUB_TOKEN",
                provider="github",
                scope="agent",
                encrypted_value="ciphertext",
            )
        )
        session.add(
            GitHubConnection(
                user_id=user.id,
                installation_id="12345",
                account_login="octocat",
            )
        )
        session.add(
            AutomationJob(
                team_id=team.id,
                agent_id=agent.id,
                name="daily-sync",
                schedule="0 9 * * *",
                prompt="Summarize repo changes.",
            )
        )
        session.add(
            RuntimeLease(
                agent_id=agent.id,
                vm_id="vm-dev-001",
                state="running",
                api_base_url="http://10.0.0.5:8642",
            )
        )
        session.commit()

        persisted_agent = session.exec(select(Agent)).one()
        persisted_job = session.exec(select(AutomationJob)).one()

        assert persisted_agent.team_id == team.id
        assert persisted_job.agent_id == agent.id


def test_bootstrap_seeds_default_agent_in_provisioning_state() -> None:
    engine = create_database_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        user = User(firebase_uid="firebase-user-1", email="user@example.com")
        session.add(user)
        session.commit()
        session.refresh(user)

        _, agent = ensure_personal_workspace(session, user)

        assert agent.status == "provisioning"
