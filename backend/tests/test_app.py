from __future__ import annotations

from dataclasses import dataclass

from fastapi.testclient import TestClient

from sutra_backend.config import Settings
from sutra_backend.main import create_app


def test_healthcheck_reports_service_status(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")

    client = TestClient(create_app())

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "sutra-backend",
        "app_env": "test",
    }


def test_root_healthz_is_available() -> None:
    client = TestClient(create_app())

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_app_starts_and_stops_inbox_poller_when_enabled(monkeypatch) -> None:
    events: list[str] = []

    @dataclass
    class FakePoller:
        settings: object
        session_factory: object

        async def start(self) -> None:
            events.append("start")

        async def stop(self) -> None:
            events.append("stop")

    monkeypatch.setattr("sutra_backend.main.InboxPoller", FakePoller)

    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        inbox_poller_enabled=True,
    )

    with TestClient(create_app(settings)):
        pass

    assert events == ["start", "stop"]
