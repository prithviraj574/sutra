from __future__ import annotations

from fastapi import FastAPI

from sutra_backend.api.routes import api_router
from sutra_backend.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    app = FastAPI(
        title=resolved_settings.app_name,
        debug=resolved_settings.debug,
        version="0.1.0",
    )
    app.state.settings = resolved_settings
    app.include_router(api_router, prefix="/api")

    @app.get("/healthz", tags=["health"])
    def healthz() -> dict[str, str]:
        return {"status": "ok", "service": "sutra-backend"}

    return app


app = create_app()
