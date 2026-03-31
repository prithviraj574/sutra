from __future__ import annotations

from functools import lru_cache
from pathlib import Path

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
    gcp_service_account_json: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GCP_SERVICE_ACCOUNT_JSON", "GCS_SERVICE_ACCOUNT_JSON"),
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
    gcp_runtime_host_instance_name: str = Field(
        default="sutra-firecracker-host",
        validation_alias=AliasChoices("GCP_RUNTIME_HOST_INSTANCE_NAME"),
    )
    gcp_runtime_host_api_port: int = Field(
        default=8787,
        validation_alias=AliasChoices("GCP_RUNTIME_HOST_API_PORT"),
    )
    gcp_runtime_host_api_override_base_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GCP_RUNTIME_HOST_API_OVERRIDE_BASE_URL"),
    )
    gcp_runtime_host_api_bind_host: str = Field(
        default="0.0.0.0",
        validation_alias=AliasChoices("GCP_RUNTIME_HOST_API_BIND_HOST"),
    )
    gcp_runtime_boot_disk_size_gb: int = Field(
        default=20,
        validation_alias=AliasChoices("GCP_RUNTIME_BOOT_DISK_SIZE_GB"),
    )
    gcp_runtime_state_disk_size_gb: int = Field(
        default=50,
        validation_alias=AliasChoices("GCP_RUNTIME_STATE_DISK_SIZE_GB"),
    )
    gcp_runtime_state_disk_type: str = Field(
        default="pd-balanced",
        validation_alias=AliasChoices("GCP_RUNTIME_STATE_DISK_TYPE"),
    )
    gcp_runtime_source_image: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GCP_RUNTIME_SOURCE_IMAGE"),
    )
    gcp_runtime_source_image_family: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GCP_RUNTIME_SOURCE_IMAGE_FAMILY"),
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
    gcp_runtime_assign_public_ip: bool = Field(
        default=True,
        validation_alias=AliasChoices("GCP_RUNTIME_ASSIGN_PUBLIC_IP"),
    )
    gcp_runtime_use_public_ip: bool = Field(
        default=True,
        validation_alias=AliasChoices("GCP_RUNTIME_USE_PUBLIC_IP"),
    )
    gcp_runtime_service_account_email: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GCP_RUNTIME_SERVICE_ACCOUNT_EMAIL"),
    )
    gcp_runtime_port: int = Field(
        default=8642,
        validation_alias=AliasChoices("GCP_RUNTIME_PORT"),
    )
    gcp_runtime_state_mount_path: str = Field(
        default="/mnt/sutra/state",
        validation_alias=AliasChoices("GCP_RUNTIME_STATE_MOUNT_PATH"),
    )
    gcp_runtime_agent_root_path: str = Field(
        default="/mnt/sutra/state/agents",
        validation_alias=AliasChoices("GCP_RUNTIME_AGENT_ROOT_PATH"),
    )
    gcp_runtime_shared_workspace_root_path: str = Field(
        default="/mnt/sutra/shared-workspaces",
        validation_alias=AliasChoices("GCP_RUNTIME_SHARED_WORKSPACE_ROOT_PATH"),
    )
    gcp_runtime_hermes_home_path: str = Field(
        default="/mnt/sutra/state/hermes-home",
        validation_alias=AliasChoices("GCP_RUNTIME_HERMES_HOME_PATH"),
    )
    gcp_runtime_private_volume_path: str = Field(
        default="/mnt/sutra/state/private-volume",
        validation_alias=AliasChoices("GCP_RUNTIME_PRIVATE_VOLUME_PATH"),
    )
    gcp_runtime_shared_workspace_path: str = Field(
        default="/mnt/sutra/shared-workspace",
        validation_alias=AliasChoices("GCP_RUNTIME_SHARED_WORKSPACE_PATH"),
    )
    gcp_runtime_api_bind_host: str = Field(
        default="0.0.0.0",
        validation_alias=AliasChoices("GCP_RUNTIME_API_BIND_HOST"),
    )
    gcp_runtime_hermes_workdir: str = Field(
        default="/opt/hermes-agent",
        validation_alias=AliasChoices("GCP_RUNTIME_HERMES_WORKDIR"),
    )
    gcp_runtime_python_venv_path: str = Field(
        default="/opt/sutra-runtime-venv",
        validation_alias=AliasChoices("GCP_RUNTIME_PYTHON_VENV_PATH"),
    )
    gcp_runtime_gateway_command: str = Field(
        default="python -m gateway.run",
        validation_alias=AliasChoices("GCP_RUNTIME_GATEWAY_COMMAND"),
    )
    gcp_runtime_firecracker_binary_path: str = Field(
        default="/usr/local/bin/firecracker",
        validation_alias=AliasChoices("GCP_RUNTIME_FIRECRACKER_BINARY_PATH"),
    )
    gcp_runtime_jailer_binary_path: str = Field(
        default="/usr/local/bin/jailer",
        validation_alias=AliasChoices("GCP_RUNTIME_JAILER_BINARY_PATH"),
    )
    gcp_runtime_firecracker_kernel_path: str = Field(
        default="/opt/sutra-firecracker/vmlinux.bin",
        validation_alias=AliasChoices("GCP_RUNTIME_FIRECRACKER_KERNEL_PATH"),
    )
    gcp_runtime_firecracker_rootfs_path: str = Field(
        default="/opt/sutra-firecracker/rootfs.ext4",
        validation_alias=AliasChoices("GCP_RUNTIME_FIRECRACKER_ROOTFS_PATH"),
    )
    gcp_runtime_firecracker_execute: bool = Field(
        default=False,
        validation_alias=AliasChoices("GCP_RUNTIME_FIRECRACKER_EXECUTE"),
    )
    gcp_runtime_host_microvm_base_port: int = Field(
        default=10080,
        validation_alias=AliasChoices("GCP_RUNTIME_HOST_MICROVM_BASE_PORT"),
    )
    gcp_runtime_hermes_bundle_uri: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GCP_RUNTIME_HERMES_BUNDLE_URI"),
    )
    gcp_runtime_access_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GCP_RUNTIME_ACCESS_TOKEN"),
    )
    github_client_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GITHUB_CLIENT_ID"),
    )
    github_client_secret: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GITHUB_CLIENT_SECRET"),
    )
    github_app_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GITHUB_APP_ID"),
    )
    github_app_private_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GITHUB_APP_PRIVATE_KEY"),
    )
    frontend_url: str = Field(
        default="http://localhost:5173",
        validation_alias=AliasChoices("SUTRA_FRONTEND_URL", "FRONTEND_URL"),
    )
    inbox_poller_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("SUTRA_INBOX_POLLER_ENABLED"),
    )
    inbox_poller_interval_seconds: int = Field(
        default=30,
        validation_alias=AliasChoices("SUTRA_INBOX_POLLER_INTERVAL_SECONDS"),
    )
    inbox_poller_lease_seconds: int = Field(
        default=60,
        validation_alias=AliasChoices("SUTRA_INBOX_POLLER_LEASE_SECONDS"),
    )
    inbox_poller_max_tasks_per_sweep: int = Field(
        default=4,
        validation_alias=AliasChoices("SUTRA_INBOX_POLLER_MAX_TASKS_PER_SWEEP"),
    )
    runtime_heartbeat_stale_seconds: int = Field(
        default=300,
        validation_alias=AliasChoices("SUTRA_RUNTIME_HEARTBEAT_STALE_SECONDS"),
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_app_settings(request: Request) -> Settings:
    settings = getattr(request.app.state, "settings", None)
    if isinstance(settings, Settings):
        return settings
    return get_settings()


BACKEND_ROOT = Path(__file__).resolve().parents[1]
