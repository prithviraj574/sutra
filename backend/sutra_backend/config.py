from __future__ import annotations

from functools import lru_cache

from fastapi import Request
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = "Sutra API"
    app_env: str = Field(
        default="development",
        validation_alias=AliasChoices("APP_ENV", "SUTRA_ENV"),
    )
    debug: bool = Field(
        default=False,
        validation_alias=AliasChoices("DEBUG", "FASTAPI_DEBUG"),
    )
    database_url: str = Field(
        default="postgresql+psycopg://postgres@127.0.0.1:5432/sutra",
        validation_alias=AliasChoices("DATABASE_URL", "POSTGRES_URL"),
    )
    firebase_project_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("FIREBASE_PROJECT_ID"),
    )
    firebase_service_account_json: str | None = Field(
        default=None,
        validation_alias=AliasChoices("FIREBASE_SERVICE_ACCOUNT_JSON"),
    )
    gcs_bucket_name: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GCS_BUCKET_NAME"),
    )
    master_encryption_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("MASTER_ENCRYPTION_KEY"),
    )
    hermes_api_route_timeout_seconds: int = Field(
        default=900,
        validation_alias=AliasChoices(
            "HERMES_API_ROUTE_TIMEOUT_SECONDS",
            "RUNTIME_REQUEST_TIMEOUT_SECONDS",
        ),
    )
    runtime_provider: str = Field(
        default="static_dev",
        validation_alias=AliasChoices("SUTRA_RUNTIME_PROVIDER"),
    )
    runtime_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "SUTRA_RUNTIME_API_KEY",
            "SUTRA_DEV_RUNTIME_API_KEY",
        ),
    )
    dev_runtime_base_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SUTRA_DEV_RUNTIME_BASE_URL"),
    )
    dev_runtime_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SUTRA_DEV_RUNTIME_API_KEY"),
    )
    gcp_project_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GCP_PROJECT_ID"),
    )
    gcp_compute_zone: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GCP_COMPUTE_ZONE"),
    )
    gcp_runtime_machine_type: str = Field(
        default="e2-small",
        validation_alias=AliasChoices("GCP_RUNTIME_MACHINE_TYPE"),
    )
    gcp_runtime_boot_disk_size_gb: int = Field(
        default=20,
        validation_alias=AliasChoices("GCP_RUNTIME_BOOT_DISK_SIZE_GB"),
    )
    gcp_runtime_source_image: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GCP_RUNTIME_SOURCE_IMAGE"),
    )
    gcp_runtime_source_image_project: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GCP_RUNTIME_SOURCE_IMAGE_PROJECT"),
    )
    gcp_runtime_network: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GCP_RUNTIME_NETWORK"),
    )
    gcp_runtime_subnetwork: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GCP_RUNTIME_SUBNETWORK"),
    )
    gcp_runtime_service_account_email: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GCP_RUNTIME_SERVICE_ACCOUNT_EMAIL"),
    )
    gcp_runtime_port: int = Field(
        default=8642,
        validation_alias=AliasChoices("GCP_RUNTIME_PORT"),
    )
    gcp_runtime_access_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GCP_RUNTIME_ACCESS_TOKEN"),
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_app_settings(request: Request) -> Settings:
    settings = getattr(request.app.state, "settings", None)
    if isinstance(settings, Settings):
        return settings
    return get_settings()
