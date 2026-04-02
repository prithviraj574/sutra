from __future__ import annotations

from sutra_backend.db import normalize_database_url
from sutra_backend.config import get_settings


def test_settings_prefer_existing_postgres_alias(monkeypatch) -> None:
    monkeypatch.setenv("POSTGRES_URL", "postgresql://postgres@127.0.0.1:5432/sutra_test")
    monkeypatch.setenv("APP_ENV", "test")

    settings = get_settings()

    assert settings.database_url == "postgresql://postgres@127.0.0.1:5432/sutra_test"
    assert settings.app_env == "test"


def test_normalize_database_url_upgrades_plain_postgres_urls() -> None:
    assert normalize_database_url("postgresql://user:pass@db.example.com/sutra") == (
        "postgresql+psycopg://user:pass@db.example.com/sutra"
    )
    assert normalize_database_url("postgres://user:pass@db.example.com/sutra") == (
        "postgresql+psycopg://user:pass@db.example.com/sutra"
    )
    assert normalize_database_url("postgresql+psycopg://user:pass@db.example.com/sutra") == (
        "postgresql+psycopg://user:pass@db.example.com/sutra"
    )
