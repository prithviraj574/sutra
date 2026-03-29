from __future__ import annotations

from fastapi.testclient import TestClient

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
