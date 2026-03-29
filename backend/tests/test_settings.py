from __future__ import annotations

from sutra_backend.config import get_settings


def test_settings_prefer_existing_postgres_alias(monkeypatch) -> None:
    monkeypatch.setenv("POSTGRES_URL", "postgresql+psycopg://postgres@127.0.0.1:5432/sutra_test")
    monkeypatch.setenv("APP_ENV", "test")

    settings = get_settings()

    assert settings.database_url == "postgresql+psycopg://postgres@127.0.0.1:5432/sutra_test"
    assert settings.app_env == "test"
