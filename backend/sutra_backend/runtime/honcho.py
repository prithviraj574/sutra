from __future__ import annotations

import os
from uuid import UUID

from sutra_backend.config import Settings


def resolve_honcho_api_key(settings: Settings) -> str | None:
    return (
        settings.honcho_api_key
        or os.environ.get("SUTRA_HONCHO_API_KEY")
        or os.environ.get("HONCHO_API_KEY")
    )


def resolve_honcho_base_url(settings: Settings) -> str | None:
    return (
        settings.honcho_base_url
        or os.environ.get("SUTRA_HONCHO_BASE_URL")
        or os.environ.get("HONCHO_BASE_URL")
    )


def honcho_enabled(settings: Settings) -> bool:
    return bool(resolve_honcho_api_key(settings) or resolve_honcho_base_url(settings))


def build_honcho_workspace_id(*, user_id: UUID, settings: Settings) -> str:
    return f"sutra:{settings.honcho_workspace_environment}:user:{user_id}"


def build_honcho_user_peer_name(*, user_id: UUID) -> str:
    return f"user-{user_id}"


def build_honcho_agent_peer_name(*, agent_id: UUID) -> str:
    return f"agent-{agent_id}"


def build_runtime_honcho_config(
    *,
    settings: Settings,
    user_id: UUID,
    agent_id: UUID,
) -> dict[str, object] | None:
    if not honcho_enabled(settings):
        return None

    api_key = resolve_honcho_api_key(settings)
    base_url = resolve_honcho_base_url(settings)
    config: dict[str, object] = {
        "enabled": True,
        "environment": settings.honcho_environment,
        "memoryMode": settings.honcho_memory_mode,
        "sessionStrategy": "per-session",
        "sessionPeerPrefix": False,
        "hosts": {
            "hermes": {
                "enabled": True,
                "workspace": build_honcho_workspace_id(user_id=user_id, settings=settings),
                "peerName": build_honcho_user_peer_name(user_id=user_id),
                "aiPeer": build_honcho_agent_peer_name(agent_id=agent_id),
                "memoryMode": settings.honcho_memory_mode,
                "sessionStrategy": "per-session",
                "saveMessages": True,
            }
        },
    }
    if api_key:
        config["apiKey"] = api_key
    if base_url:
        config["baseUrl"] = base_url
    return config
