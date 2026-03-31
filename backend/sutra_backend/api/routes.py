from __future__ import annotations

from fastapi import APIRouter

from sutra_backend.api.agents import agents_router
from sutra_backend.api.auth_routes import auth_router
from sutra_backend.api.conversations import conversations_router
from sutra_backend.api.health import health_router
from sutra_backend.api.runtime_routes import runtime_router
from sutra_backend.api.secrets import secrets_router
from sutra_backend.api.system import system_router
from sutra_backend.api.tasks import tasks_router
from sutra_backend.api.teams import teams_router


api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(teams_router)
api_router.include_router(agents_router)
api_router.include_router(tasks_router)
api_router.include_router(conversations_router)
api_router.include_router(secrets_router)
api_router.include_router(runtime_router)
api_router.include_router(system_router)
