from __future__ import annotations

from fastapi import APIRouter, Depends

from sutra_backend.config import Settings, get_app_settings


health_router = APIRouter()


@health_router.get("/health", tags=["health"])
def healthcheck(settings: Settings = Depends(get_app_settings)) -> dict[str, str]:
    return {
        "status": "ok",
        "service": "sutra-backend",
        "app_env": settings.app_env,
    }
