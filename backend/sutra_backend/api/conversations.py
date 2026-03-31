from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from sutra_backend.auth.dependencies import get_current_user
from sutra_backend.db import get_session
from sutra_backend.models import User
from sutra_backend.schemas.conversations import ConversationStreamEvent, MessageListResponse, MessageRead
from sutra_backend.services.conversations import list_conversation_messages, read_conversation_stream_snapshot
from sutra_backend.services.runtime import get_owned_agent
from sutra_backend.services.runtime_leases import reconcile_runtime_lease
from sutra_backend.config import Settings, get_app_settings
from sutra_backend.services.runtime import AgentNotFoundError


conversations_router = APIRouter()


def _format_sse_event(event: ConversationStreamEvent) -> str:
    return "\n".join(
        [
            f"id: {event.event_id}",
            f"event: {event.type}",
            f"data: {event.model_dump_json()}",
            "",
        ]
    ) + "\n"


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


@conversations_router.get(
    "/conversations/{conversation_id}/stream",
    tags=["conversations"],
)
async def stream_conversation_events(
    conversation_id: UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_app_settings),
    max_events: int | None = Query(default=None, ge=1),
    poll_interval_seconds: float = Query(default=0.5, ge=0.1, le=5.0),
    idle_timeout_seconds: float = Query(default=15.0, ge=1.0, le=60.0),
) -> StreamingResponse:
    try:
        initial_snapshot = read_conversation_stream_snapshot(session, user=user, conversation_id=conversation_id)
    except AgentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    async def event_generator():
        emitted = 0
        sequence = 0
        last_activity_at = datetime.now(UTC)
        seen_message_ids: set[UUID] = set()
        seen_workspace_item_ids: set[UUID] = set()
        seen_task_update_ids: set[UUID] = set()
        runtime_sent = False

        while True:
            snapshot = read_conversation_stream_snapshot(session, user=user, conversation_id=conversation_id)
            events: list[ConversationStreamEvent] = []

            if snapshot.conversation.agent_id and not runtime_sent:
                try:
                    runtime_status = reconcile_runtime_lease(
                        session,
                        user=user,
                        agent_id=snapshot.conversation.agent_id,
                        settings=settings,
                    )
                    sequence += 1
                    events.append(
                        ConversationStreamEvent(
                            event_id=f"{conversation_id}:runtime:{sequence}",
                            type="runtime.state_changed",
                            conversation_id=snapshot.conversation.id,
                            agent_id=snapshot.conversation.agent_id,
                            timestamp=datetime.now(UTC),
                            sequence=sequence,
                            payload={
                                "state": runtime_status.lease.state,
                                "provider": runtime_status.provider,
                                "ready": runtime_status.ready,
                                "readiness_stage": runtime_status.readiness_stage,
                                "readiness_reason": runtime_status.readiness_reason,
                                "isolation_ok": runtime_status.isolation_ok,
                                "isolation_reason": runtime_status.isolation_reason,
                            },
                        )
                    )
                except AgentNotFoundError:
                    pass
                runtime_sent = True

            for message in snapshot.messages:
                if message.id in seen_message_ids:
                    continue
                seen_message_ids.add(message.id)
                if message.actor_type == "user":
                    sequence += 1
                    events.append(
                        ConversationStreamEvent(
                            event_id=f"{conversation_id}:run-started:{sequence}",
                            type="run.started",
                            conversation_id=snapshot.conversation.id,
                            agent_id=snapshot.conversation.agent_id,
                            timestamp=message.created_at,
                            sequence=sequence,
                            payload={
                                "message_id": str(message.id),
                                "actor_type": message.actor_type,
                            },
                        )
                    )
                    continue
                if message.actor_type == "assistant":
                    sequence += 1
                    events.append(
                        ConversationStreamEvent(
                            event_id=f"{conversation_id}:assistant:{sequence}",
                            type="assistant.message_delta",
                            conversation_id=snapshot.conversation.id,
                            agent_id=snapshot.conversation.agent_id,
                            timestamp=message.created_at,
                            sequence=sequence,
                            payload={
                                "message_id": str(message.id),
                                "text": message.content,
                                "response_chain_id": message.response_chain_id,
                            },
                        )
                    )
                    sequence += 1
                    events.append(
                        ConversationStreamEvent(
                            event_id=f"{conversation_id}:run-completed:{sequence}",
                            type="run.completed",
                            conversation_id=snapshot.conversation.id,
                            agent_id=snapshot.conversation.agent_id,
                            timestamp=message.updated_at,
                            sequence=sequence,
                            payload={
                                "message_id": str(message.id),
                                "response_chain_id": message.response_chain_id,
                            },
                        )
                    )

            for item in snapshot.workspace_items:
                if item.id in seen_workspace_item_ids:
                    continue
                seen_workspace_item_ids.add(item.id)
                sequence += 1
                events.append(
                    ConversationStreamEvent(
                        event_id=f"{conversation_id}:workspace:{sequence}",
                        type="workspace.item_created",
                        conversation_id=snapshot.conversation.id,
                        agent_id=item.agent_id,
                        timestamp=item.created_at,
                        sequence=sequence,
                        payload={
                            "item_id": str(item.id),
                            "path": item.path,
                            "kind": item.kind,
                        },
                    )
                )

            for update in snapshot.task_updates:
                if update.id in seen_task_update_ids:
                    continue
                seen_task_update_ids.add(update.id)
                sequence += 1
                events.append(
                    ConversationStreamEvent(
                        event_id=f"{conversation_id}:task:{sequence}",
                        type="task.updated",
                        conversation_id=snapshot.conversation.id,
                        agent_id=update.agent_id,
                        timestamp=update.created_at,
                        sequence=sequence,
                        payload={
                            "task_id": str(update.task_id),
                            "update_id": str(update.id),
                            "event_type": update.event_type,
                            "content": update.content,
                        },
                    )
                )

            if events:
                last_activity_at = datetime.now(UTC)
                for event in events:
                    yield _format_sse_event(event)
                    emitted += 1
                    if max_events is not None and emitted >= max_events:
                        return
            elif (datetime.now(UTC) - last_activity_at).total_seconds() >= idle_timeout_seconds:
                sequence += 1
                yield _format_sse_event(
                    ConversationStreamEvent(
                        event_id=f"{conversation_id}:stream-idle:{sequence}",
                        type="stream.idle",
                        conversation_id=initial_snapshot.conversation.id,
                        agent_id=initial_snapshot.conversation.agent_id,
                        timestamp=datetime.now(UTC),
                        sequence=sequence,
                        payload={"idle_timeout_seconds": idle_timeout_seconds},
                    )
                )
                return

            await asyncio.sleep(poll_interval_seconds)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
