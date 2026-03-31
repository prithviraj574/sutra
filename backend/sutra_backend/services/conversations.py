from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlmodel import Session, select

from sutra_backend.models import Agent, Conversation, Message, SharedWorkspaceItem, Team, TeamTask, TeamTaskUpdate, User
from sutra_backend.services.runtime import AgentNotFoundError


def list_agent_conversations(session: Session, *, user: User, agent_id: UUID) -> list[Conversation]:
    owned_agent = session.exec(
        select(Agent)
        .join(Team, Team.id == Agent.team_id)
        .where(Agent.id == agent_id)
        .where(Team.user_id == user.id)
    ).first()
    if owned_agent is None:
        raise AgentNotFoundError("Agent not found.")

    return session.exec(
        select(Conversation)
        .where(Conversation.agent_id == agent_id)
        .order_by(Conversation.updated_at.desc())
    ).all()


def list_conversation_messages(session: Session, *, user: User, conversation_id: UUID) -> list[Message]:
    owned_conversation = get_owned_conversation(session, user=user, conversation_id=conversation_id)

    return session.exec(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    ).all()


def list_team_conversations(session: Session, *, user: User, team_id: UUID) -> list[Conversation]:
    owned_team = session.exec(
        select(Team)
        .where(Team.id == team_id)
        .where(Team.user_id == user.id)
    ).first()
    if owned_team is None:
        raise AgentNotFoundError("Team not found.")

    return session.exec(
        select(Conversation)
        .where(Conversation.team_id == team_id)
        .where(Conversation.mode == "team")
        .order_by(Conversation.updated_at.desc())
    ).all()


@dataclass(frozen=True)
class ConversationStreamSnapshot:
    conversation: Conversation
    messages: list[Message]
    workspace_items: list[SharedWorkspaceItem]
    task_updates: list[TeamTaskUpdate]


def get_owned_conversation(
    session: Session,
    *,
    user: User,
    conversation_id: UUID,
) -> Conversation:
    owned_conversation = session.exec(
        select(Conversation)
        .join(Team, Team.id == Conversation.team_id)
        .where(Conversation.id == conversation_id)
        .where(Team.user_id == user.id)
    ).first()
    if owned_conversation is None:
        raise AgentNotFoundError("Conversation not found.")
    return owned_conversation


def read_conversation_stream_snapshot(
    session: Session,
    *,
    user: User,
    conversation_id: UUID,
) -> ConversationStreamSnapshot:
    conversation = get_owned_conversation(session, user=user, conversation_id=conversation_id)
    messages = session.exec(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.asc())
    ).all()
    workspace_items = session.exec(
        select(SharedWorkspaceItem)
        .where(SharedWorkspaceItem.conversation_id == conversation.id)
        .order_by(SharedWorkspaceItem.created_at.asc())
    ).all()
    task_updates = session.exec(
        select(TeamTaskUpdate)
        .join(TeamTask, TeamTask.id == TeamTaskUpdate.task_id)
        .where(TeamTask.conversation_id == conversation.id)
        .order_by(TeamTaskUpdate.created_at.asc())
    ).all()
    return ConversationStreamSnapshot(
        conversation=conversation,
        messages=messages,
        workspace_items=workspace_items,
        task_updates=task_updates,
    )
