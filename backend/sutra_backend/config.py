from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from uuid import UUID

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

    app_name: str = Field(
        default="Sutra API",
        description="Display name for the FastAPI application.",
    )
    app_env: str = Field(
        default="development",
        validation_alias=AliasChoices("APP_ENV", "SUTRA_ENV"),
        description="Logical environment name (`development`, `staging`, `production`).",
    )
    debug: bool = Field(
        default=False,
        validation_alias=AliasChoices("DEBUG", "FASTAPI_DEBUG"),
        description="Enable verbose debug behavior in the API process.",
    )
    database_url: str = Field(
        default="postgresql://postgres@127.0.0.1:5432/sutra",
        validation_alias=AliasChoices("POSTGRES_URL"),
        description="Primary Postgres connection string used by SQLModel/SQLAlchemy.",
    )
    firebase_project_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("FIREBASE_PROJECT_ID"),
        description="Firebase project id used to validate incoming Firebase auth tokens.",
    )
    firebase_service_account_json: str | None = Field(
        default=None,
        validation_alias=AliasChoices("FIREBASE_SERVICE_ACCOUNT_JSON"),
        description="Path to Firebase service-account JSON used by backend token verification.",
    )
    dev_auth_bypass_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("SUTRA_DEV_AUTH_BYPASS"),
        description="Enable local development auth bypass (disabled automatically in production).",
    )
    dev_auth_bypass_user_id: UUID = Field(
        default=UUID("00000000-0000-0000-0000-000000000000"),
        validation_alias=AliasChoices("SUTRA_DEV_AUTH_BYPASS_USER_ID"),
        description="Stable user id used when auth bypass mode is enabled.",
    )
    dev_auth_bypass_email: str = Field(
        default="local-dev@sutra.local",
        validation_alias=AliasChoices("SUTRA_DEV_AUTH_BYPASS_EMAIL"),
        description="Email for the seeded bypass user in local development mode.",
    )
    dev_auth_bypass_display_name: str = Field(
        default="Local Dev User",
        validation_alias=AliasChoices("SUTRA_DEV_AUTH_BYPASS_DISPLAY_NAME"),
        description="Display name for the seeded bypass user in local development mode.",
    )
    gcs_bucket_name: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GCS_BUCKET_NAME"),
        description="GCS bucket used for runtime bundles and runtime-adjacent persisted objects.",
    )
    gcp_service_account_json: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GCP_SERVICE_ACCOUNT_JSON", "GCS_SERVICE_ACCOUNT_JSON"),
        description="Path to a GCP service-account JSON file used by runtime provisioning calls.",
    )
    master_encryption_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("MASTER_ENCRYPTION_KEY"),
        description="Application master key used for encrypting user secrets at rest.",
    )
    hermes_api_route_timeout_seconds: int = Field(
        default=900,
        validation_alias=AliasChoices(
            "HERMES_API_ROUTE_TIMEOUT_SECONDS",
            "RUNTIME_REQUEST_TIMEOUT_SECONDS",
        ),
        description="HTTP timeout in seconds for requests sent from control plane to Hermes runtime APIs.",
    )
    runtime_provider: str = Field(
        default="static_dev",
        validation_alias=AliasChoices("SUTRA_RUNTIME_PROVIDER"),
        description="Runtime backend selector (`static_dev` or `gcp_firecracker`).",
    )
    runtime_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "SUTRA_RUNTIME_API_KEY",
            "SUTRA_DEV_RUNTIME_API_KEY",
        ),
        description="Bearer key used by sutra_backend when calling runtime host/runtime APIs.",
    )
    honcho_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SUTRA_HONCHO_API_KEY", "HONCHO_API_KEY"),
        description="API key for Honcho memory service integration.",
    )
    honcho_base_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SUTRA_HONCHO_BASE_URL", "HONCHO_BASE_URL"),
        description="Optional Honcho API base URL override (defaults to Honcho cloud endpoint).",
    )
    honcho_environment: str = Field(
        default="production",
        validation_alias=AliasChoices("SUTRA_HONCHO_ENVIRONMENT", "HONCHO_ENVIRONMENT"),
        description="Honcho environment label to isolate memory by deployment environment.",
    )
    honcho_memory_mode: str = Field(
        default="hybrid",
        validation_alias=AliasChoices("SUTRA_HONCHO_MEMORY_MODE"),
        description="Hermes memory strategy when Honcho is enabled (`hybrid`, etc.).",
    )
    honcho_workspace_environment: str = Field(
        default="prod",
        validation_alias=AliasChoices("SUTRA_HONCHO_WORKSPACE_ENVIRONMENT"),
        description="Environment segment used when composing Honcho workspace identifiers.",
    )
    openrouter_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENROUTER_API_KEY"),
        description="OpenRouter API key forwarded to managed runtimes.",
    )
    openai_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_API_KEY"),
        description="OpenAI API key forwarded to managed runtimes.",
    )
    openai_base_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_BASE_URL"),
        description="Optional OpenAI-compatible base URL override for managed runtimes.",
    )
    openai_model: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_MODEL"),
        description="Default OpenAI model identifier for managed runtimes.",
    )
    hermes_model: str | None = Field(
        default=None,
        validation_alias=AliasChoices("HERMES_MODEL"),
        description="Default Hermes model override passed into runtime environment.",
    )
    llm_model: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LLM_MODEL"),
        description="Generic model fallback variable passed into runtime environment.",
    )
    anthropic_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("ANTHROPIC_API_KEY"),
        description="Anthropic API key forwarded to managed runtimes.",
    )
    anthropic_base_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("ANTHROPIC_BASE_URL"),
        description="Optional Anthropic base URL override for managed runtimes.",
    )
    minimax_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("MINIMAX_API_KEY"),
        description="MiniMax API key forwarded to managed runtimes.",
    )
    minimax_cn_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("MINIMAX_CN_API_KEY"),
        description="MiniMax China-region API key forwarded to managed runtimes.",
    )
    minimax_base_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("MINIMAX_BASE_URL"),
        description="Optional MiniMax base URL override for managed runtimes.",
    )
    minimax_cn_base_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("MINIMAX_CN_BASE_URL"),
        description="Optional MiniMax CN base URL override for managed runtimes.",
    )
    browserbase_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("BROWSERBASE_API_KEY"),
        description="Browserbase API key forwarded to managed runtimes.",
    )
    browserbase_project_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("BROWSERBASE_PROJECT_ID"),
        description="Browserbase project id forwarded to managed runtimes.",
    )
    browser_use_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("BROWSER_USE_API_KEY"),
        description="Browser-use API key forwarded to managed runtimes.",
    )
    firecrawl_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("FIRECRAWL_API_KEY"),
        description="Firecrawl API key forwarded to managed runtimes.",
    )
    dev_runtime_base_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SUTRA_DEV_RUNTIME_BASE_URL"),
        description="Base URL of local Hermes runtime when using `static_dev` provider.",
    )
    dev_runtime_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SUTRA_DEV_RUNTIME_API_KEY"),
        description="Legacy/dev alias for runtime API key used in local runtime mode.",
    )
    gcp_project_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GCP_PROJECT_ID"),
        description="GCP project id used for Compute Engine and related API calls.",
    )
    gcp_compute_zone: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GCP_COMPUTE_ZONE"),
        description="GCP zone containing the runtime host VM and state disk.",
    )
    gcp_runtime_machine_type: str = Field(
        default="e2-small",
        validation_alias=AliasChoices("GCP_RUNTIME_MACHINE_TYPE"),
        description="Compute Engine machine type for the runtime host VM.",
    )
    gcp_runtime_host_instance_name: str = Field(
        default="sutra-firecracker-host",
        validation_alias=AliasChoices("GCP_RUNTIME_HOST_INSTANCE_NAME"),
        description="Name of the runtime host VM that runs the Sutra host manager.",
    )
    gcp_runtime_host_api_port: int = Field(
        default=8787,
        validation_alias=AliasChoices("GCP_RUNTIME_HOST_API_PORT"),
        description="Port exposed by the runtime host manager API.",
    )
    gcp_runtime_host_api_override_base_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GCP_RUNTIME_HOST_API_OVERRIDE_BASE_URL"),
        description="Optional local override for host API base URL (for tunnel-based local testing).",
    )
    gcp_runtime_host_api_bind_host: str = Field(
        default="0.0.0.0",
        validation_alias=AliasChoices("GCP_RUNTIME_HOST_API_BIND_HOST"),
        description="Bind host/interface for runtime host manager API process.",
    )
    gcp_runtime_boot_disk_size_gb: int = Field(
        default=20,
        validation_alias=AliasChoices("GCP_RUNTIME_BOOT_DISK_SIZE_GB"),
        description="Boot disk size in GB for the runtime host VM.",
    )
    gcp_runtime_state_disk_size_gb: int = Field(
        default=50,
        validation_alias=AliasChoices("GCP_RUNTIME_STATE_DISK_SIZE_GB"),
        description="Persistent state disk size in GB used by hosted Hermes runtimes.",
    )
    gcp_runtime_state_disk_type: str = Field(
        default="pd-balanced",
        validation_alias=AliasChoices("GCP_RUNTIME_STATE_DISK_TYPE"),
        description="Disk type for runtime state disk (for example `pd-balanced`).",
    )
    gcp_runtime_source_image: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GCP_RUNTIME_SOURCE_IMAGE"),
        description="Explicit source image name used to create the runtime host VM.",
    )
    gcp_runtime_source_image_family: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GCP_RUNTIME_SOURCE_IMAGE_FAMILY"),
        description="Source image family used to create the runtime host VM.",
    )
    gcp_runtime_source_image_project: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GCP_RUNTIME_SOURCE_IMAGE_PROJECT"),
        description="Project that owns the source image or image family.",
    )
    gcp_runtime_network: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GCP_RUNTIME_NETWORK"),
        description="Optional VPC network name for the runtime host VM.",
    )
    gcp_runtime_subnetwork: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GCP_RUNTIME_SUBNETWORK"),
        description="Optional subnetwork name for the runtime host VM.",
    )
    gcp_runtime_assign_public_ip: bool = Field(
        default=True,
        validation_alias=AliasChoices("GCP_RUNTIME_ASSIGN_PUBLIC_IP"),
        description="Whether newly created runtime host VM instances should receive a public IP.",
    )
    gcp_runtime_use_public_ip: bool = Field(
        default=True,
        validation_alias=AliasChoices("GCP_RUNTIME_USE_PUBLIC_IP"),
        description="Whether control plane should prefer host public IP for runtime API calls.",
    )
    gcp_runtime_service_account_email: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GCP_RUNTIME_SERVICE_ACCOUNT_EMAIL"),
        description="Optional service account email attached to the runtime host VM.",
    )
    gcp_runtime_port: int = Field(
        default=8642,
        validation_alias=AliasChoices("GCP_RUNTIME_PORT"),
        description="Port used by Hermes API server process inside managed runtime environment.",
    )
    gcp_runtime_state_mount_path: str = Field(
        default="/mnt/sutra/state",
        validation_alias=AliasChoices("GCP_RUNTIME_STATE_MOUNT_PATH"),
        description="Mount path for host private state disk.",
    )
    gcp_runtime_agent_root_path: str = Field(
        default="/mnt/sutra/state/agents",
        validation_alias=AliasChoices("GCP_RUNTIME_AGENT_ROOT_PATH"),
        description="Root folder under state mount containing per-agent private directories.",
    )
    gcp_runtime_shared_workspace_root_path: str = Field(
        default="/mnt/sutra/shared-workspaces",
        validation_alias=AliasChoices("GCP_RUNTIME_SHARED_WORKSPACE_ROOT_PATH"),
        description="Root folder for team-shared workspace mounts (must be outside private state root).",
    )
    gcp_runtime_hermes_home_path: str = Field(
        default="/mnt/sutra/state/hermes-home",
        validation_alias=AliasChoices("GCP_RUNTIME_HERMES_HOME_PATH"),
        description="Default Hermes home path for single-runtime host process modes.",
    )
    gcp_runtime_private_volume_path: str = Field(
        default="/mnt/sutra/state/private-volume",
        validation_alias=AliasChoices("GCP_RUNTIME_PRIVATE_VOLUME_PATH"),
        description="Default private volume path for single-runtime host process modes.",
    )
    gcp_runtime_shared_workspace_path: str = Field(
        default="/mnt/sutra/shared-workspace",
        validation_alias=AliasChoices("GCP_RUNTIME_SHARED_WORKSPACE_PATH"),
        description="Default shared workspace path for single-runtime host process modes.",
    )
    gcp_runtime_api_bind_host: str = Field(
        default="0.0.0.0",
        validation_alias=AliasChoices("GCP_RUNTIME_API_BIND_HOST"),
        description="Bind host/interface used by Hermes API process in managed runtime.",
    )
    gcp_runtime_hermes_workdir: str = Field(
        default="/opt/hermes-agent",
        validation_alias=AliasChoices("GCP_RUNTIME_HERMES_WORKDIR"),
        description="Working directory on host where Hermes submodule/bundle is unpacked.",
    )
    gcp_runtime_python_venv_path: str = Field(
        default="/opt/sutra-runtime-venv",
        validation_alias=AliasChoices("GCP_RUNTIME_PYTHON_VENV_PATH"),
        description="Path to Python virtual environment used by runtime host and Hermes runtime commands.",
    )
    gcp_runtime_gateway_command: str = Field(
        default="python -m gateway.run",
        validation_alias=AliasChoices("GCP_RUNTIME_GATEWAY_COMMAND"),
        description="Command used to start Hermes gateway/API server process.",
    )
    gcp_runtime_firecracker_binary_path: str = Field(
        default="/usr/local/bin/firecracker",
        validation_alias=AliasChoices("GCP_RUNTIME_FIRECRACKER_BINARY_PATH"),
        description="Absolute path to Firecracker binary on runtime host.",
    )
    gcp_runtime_jailer_binary_path: str = Field(
        default="/usr/local/bin/jailer",
        validation_alias=AliasChoices("GCP_RUNTIME_JAILER_BINARY_PATH"),
        description="Absolute path to Firecracker jailer binary on runtime host.",
    )
    gcp_runtime_firecracker_kernel_path: str = Field(
        default="/opt/sutra-firecracker/vmlinux.bin",
        validation_alias=AliasChoices("GCP_RUNTIME_FIRECRACKER_KERNEL_PATH"),
        description="Kernel image path used when launching Firecracker microVMs.",
    )
    gcp_runtime_firecracker_rootfs_path: str = Field(
        default="/opt/sutra-firecracker/rootfs.ext4",
        validation_alias=AliasChoices("GCP_RUNTIME_FIRECRACKER_ROOTFS_PATH"),
        description="Root filesystem image path used when launching Firecracker microVMs.",
    )
    gcp_runtime_firecracker_execute: bool = Field(
        default=False,
        validation_alias=AliasChoices("GCP_RUNTIME_FIRECRACKER_EXECUTE"),
        description="Toggle between host-process runtime mode and real Firecracker microVM execution.",
    )
    gcp_runtime_host_microvm_base_port: int = Field(
        default=10080,
        validation_alias=AliasChoices("GCP_RUNTIME_HOST_MICROVM_BASE_PORT"),
        description="Base port for per-agent runtime proxy ports on runtime host.",
    )
    gcp_runtime_hermes_bundle_uri: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GCP_RUNTIME_HERMES_BUNDLE_URI"),
        description="GCS URI for Hermes runtime bundle copied to host during provisioning.",
    )
    gcp_runtime_access_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GCP_RUNTIME_ACCESS_TOKEN"),
        description="Optional static GCP bearer token override for Compute/GCS API calls.",
    )
    github_client_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GITHUB_CLIENT_ID"),
        description="GitHub OAuth app client id used for user account connection flow.",
    )
    github_client_secret: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GITHUB_CLIENT_SECRET"),
        description="GitHub OAuth app client secret used for token exchange.",
    )
    github_app_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GITHUB_APP_ID"),
        description="GitHub App id used for repository install and export features.",
    )
    github_app_private_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GITHUB_APP_PRIVATE_KEY"),
        description="GitHub App private key PEM string used to mint installation tokens.",
    )
    frontend_url: str = Field(
        default="http://localhost:5173",
        validation_alias=AliasChoices("SUTRA_FRONTEND_URL", "FRONTEND_URL"),
        description="Frontend base URL used in redirects and CORS-sensitive auth flows.",
    )
    inbox_poller_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("SUTRA_INBOX_POLLER_ENABLED"),
        description="Enable background inbox poller loop on backend startup.",
    )
    inbox_poller_interval_seconds: int = Field(
        default=30,
        validation_alias=AliasChoices("SUTRA_INBOX_POLLER_INTERVAL_SECONDS"),
        description="Sleep interval in seconds between inbox poller sweeps.",
    )
    inbox_poller_lease_seconds: int = Field(
        default=60,
        validation_alias=AliasChoices("SUTRA_INBOX_POLLER_LEASE_SECONDS"),
        description="Lease TTL in seconds for exclusive inbox poller ownership.",
    )
    inbox_poller_max_tasks_per_sweep: int = Field(
        default=4,
        validation_alias=AliasChoices("SUTRA_INBOX_POLLER_MAX_TASKS_PER_SWEEP"),
        description="Maximum number of inbox tasks the poller executes per sweep.",
    )
    runtime_heartbeat_stale_seconds: int = Field(
        default=300,
        validation_alias=AliasChoices("SUTRA_RUNTIME_HEARTBEAT_STALE_SECONDS"),
        description="Threshold in seconds before a runtime heartbeat is treated as stale.",
    )

    @property
    def dev_auth_bypass_active(self) -> bool:
        return self.dev_auth_bypass_enabled and self.app_env.lower() != "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_app_settings(request: Request) -> Settings:
    settings = getattr(request.app.state, "settings", None)
    if isinstance(settings, Settings):
        return settings
    return get_settings()


BACKEND_ROOT = Path(__file__).resolve().parents[1]
