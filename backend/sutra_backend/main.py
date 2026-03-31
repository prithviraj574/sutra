from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlmodel import Session

from sutra_backend.api.routes import api_router
from sutra_backend.config import Settings, get_settings
from sutra_backend.db import create_database_engine
from sutra_backend.services.inbox_poller import InboxPoller


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine = create_database_engine(
            resolved_settings.database_url,
            echo=resolved_settings.debug,
        )
        app.state.database_engine = engine
        app.state.inbox_poller = InboxPoller(
            settings=resolved_settings,
            session_factory=lambda: Session(engine),
        )
        await app.state.inbox_poller.start()
        try:
            yield
        finally:
            await app.state.inbox_poller.stop()

    app = FastAPI(
        title=resolved_settings.app_name,
        debug=resolved_settings.debug,
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.include_router(api_router, prefix="/api")

    @app.get("/healthz", tags=["health"])
    def healthz() -> dict[str, str]:
        return {"status": "ok", "service": "sutra-backend"}

    return app


app = create_app()
