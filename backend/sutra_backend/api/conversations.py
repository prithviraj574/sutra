from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from sutra_backend.auth.dependencies import get_current_user
from sutra_backend.db import get_session
from sutra_backend.models import User
from sutra_backend.schemas.conversations import MessageListResponse, MessageRead
from sutra_backend.services.conversations import list_conversation_messages
from sutra_backend.services.runtime import AgentNotFoundError


conversations_router = APIRouter()


@conversations_router.get(
    "/conversations/{conversation_id}/messages",
    tags=["conversations"],
    response_model=MessageListResponse,
)
def get_conversation_messages(
    conversation_id: UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> MessageListResponse:
    try:
        messages = list_conversation_messages(session, user=user, conversation_id=conversation_id)
    except AgentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return MessageListResponse(
        items=[MessageRead.model_validate(message, from_attributes=True) for message in messages]
    )
