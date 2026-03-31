from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import shlex
import time
from typing import Protocol
from urllib.parse import quote

import httpx
from sqlmodel import Session, select

from sutra_backend.config import BACKEND_ROOT, Settings
from sutra_backend.models import Agent, RuntimeLease, Team, utcnow
from sutra_backend.runtime.errors import RuntimeNotReadyError


class RuntimeProvisioner(Protocol):
    def ensure_lease(self, session: Session, *, agent: Agent) -> RuntimeLease:
        """Return a ready or provisioned runtime lease for the given agent."""


class GoogleAccessTokenProvider(Protocol):
    def get_access_token(self) -> str:
        """Return a bearer token that can call Google Cloud APIs."""


@dataclass(frozen=True)
class StaticGoogleAccessTokenProvider:
    access_token: str

    def get_access_token(self) -> str:
        return self.access_token


class MetadataGoogleAccessTokenProvider:
    _METADATA_URL = (
        "http://metadata.google.internal/computeMetadata/v1/instance/"
        "service-accounts/default/token"
    )

    def get_access_token(self) -> str:
        response = httpx.get(
            self._METADATA_URL,
            headers={"Metadata-Flavor": "Google"},
            timeout=5.0,
        )
        response.raise_for_status()
        payload = response.json()
        access_token = payload.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise RuntimeNotReadyError("Metadata server did not return a GCP access token.")
        return access_token


@dataclass(frozen=True)
class ServiceAccountFileGoogleAccessTokenProvider:
    service_account_json: str

    def get_access_token(self) -> str:
        try:
            from google.auth.transport.requests import Request
            from google.oauth2 import service_account
        except ImportError as exc:  # pragma: no cover - dependency should exist via firebase-admin
            raise RuntimeNotReadyError(
                "google-auth is required for service-account based GCP runtime provisioning."
            ) from exc

        credential_path = Path(self.service_account_json).expanduser()
        if not credential_path.is_absolute():
            candidate = (BACKEND_ROOT / credential_path).resolve()
            if candidate.exists():
                credential_path = candidate
        if not credential_path.exists():
            raise RuntimeNotReadyError(
                f"GCP service account file does not exist: {self.service_account_json}"
            )

        credentials = service_account.Credentials.from_service_account_file(
            str(credential_path),
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        request = Request()
        credentials.refresh(request)
        token = credentials.token
        if not isinstance(token, str) or not token:
            raise RuntimeNotReadyError("Service account credentials did not yield a GCP access token.")
        return token


@dataclass(frozen=True)
class GcpComputeInstance:
    name: str
    status: str
    network_ip: str | None


@dataclass(frozen=True)
class GcpPersistentDisk:
    name: str
    status: str
    source_link: str


@dataclass(frozen=True)
class AgentRuntimeStorageSpec:
    hermes_home_uri: str
    private_volume_uri: str
    state_disk_name: str
    state_disk_device_name: str
    state_mount_path: str
    hermes_home_path: str
    private_volume_path: str
    shared_workspace_path: str | None


@dataclass(frozen=True)
class GcpComputeEngineClient:
    settings: Settings
    token_provider: GoogleAccessTokenProvider

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token_provider.get_access_token()}",
            "Content-Type": "application/json",
        }

    def _base_url(self) -> str:
        if not self.settings.gcp_project_id or not self.settings.gcp_compute_zone:
            raise RuntimeNotReadyError("GCP project and compute zone must be configured.")
        return (
            "https://compute.googleapis.com/compute/v1/projects/"
            f"{self.settings.gcp_project_id}/zones/{self.settings.gcp_compute_zone}/instances"
        )

    def _disk_base_url(self) -> str:
        if not self.settings.gcp_project_id or not self.settings.gcp_compute_zone:
            raise RuntimeNotReadyError("GCP project and compute zone must be configured.")
        return (
            "https://compute.googleapis.com/compute/v1/projects/"
            f"{self.settings.gcp_project_id}/zones/{self.settings.gcp_compute_zone}/disks"
        )

    def get_instance(self, *, name: str) -> GcpComputeInstance | None:
        response = httpx.get(
            f"{self._base_url()}/{name}",
            headers=self._headers(),
            timeout=30.0,
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        payload = response.json()
        network_ip = None
        for interface in payload.get("networkInterfaces", []):
            candidate = interface.get("networkIP")
            if isinstance(candidate, str) and candidate:
                network_ip = candidate
                break
        return GcpComputeInstance(
            name=str(payload["name"]),
            status=str(payload.get("status", "PROVISIONING")),
            network_ip=network_ip,
        )

    def create_instance(self, *, body: dict[str, object]) -> None:
        response = httpx.post(
            self._base_url(),
            headers=self._headers(),
            json=body,
            timeout=30.0,
        )
        response.raise_for_status()

    def get_disk(self, *, name: str) -> GcpPersistentDisk | None:
        response = httpx.get(
            f"{self._disk_base_url()}/{name}",
            headers=self._headers(),
            timeout=30.0,
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        payload = response.json()
        return GcpPersistentDisk(
            name=str(payload["name"]),
            status=str(payload.get("status", "CREATING")),
            source_link=str(payload["selfLink"]),
        )

    def create_disk(self, *, name: str, size_gb: int, disk_type: str) -> None:
        response = httpx.post(
            self._disk_base_url(),
            headers=self._headers(),
            json={
                "name": name,
                "sizeGb": str(size_gb),
                "type": f"zones/{self.settings.gcp_compute_zone}/diskTypes/{disk_type}",
            },
            timeout=30.0,
        )
        response.raise_for_status()


@dataclass(frozen=True)
class GcpStorageClient:
    settings: Settings
    token_provider: GoogleAccessTokenProvider

    def ensure_prefix(self, *, bucket: str, prefix: str) -> None:
        object_name = f"{prefix.rstrip('/')}/.keep"
        response = httpx.post(
            f"https://storage.googleapis.com/upload/storage/v1/b/{bucket}/o",
            headers={"Authorization": f"Bearer {self.token_provider.get_access_token()}"},
            params={"uploadType": "media", "name": object_name},
            content=b"",
            timeout=30.0,
        )
        response.raise_for_status()


@dataclass(frozen=True)
class StaticDevRuntimeProvisioner:
    settings: Settings

    def ensure_lease(self, session: Session, *, agent: Agent) -> RuntimeLease:
        if not self.settings.dev_runtime_base_url:
            raise RuntimeNotReadyError("Static dev runtime is not configured.")

        started_at = utcnow()
        lease = RuntimeLease(
            agent_id=agent.id,
            vm_id=f"local-dev-{str(agent.id)[:8]}",
            state="running",
            api_base_url=self.settings.dev_runtime_base_url,
            last_heartbeat_at=started_at,
            started_at=started_at,
        )
        agent.status = "ready"
        session.add(agent)
        session.add(lease)
        session.commit()
        session.refresh(agent)
        session.refresh(lease)
        return lease


@dataclass(frozen=True)
class GcpFirecrackerRuntimeProvisioner:
    settings: Settings

    def ensure_lease(self, session: Session, *, agent: Agent) -> RuntimeLease:
        self._validate_configuration()
        token_provider = self._build_token_provider()
        storage_client = GcpStorageClient(self.settings, token_provider)
        compute_client = GcpComputeEngineClient(self.settings, token_provider)
        storage_spec = self._build_storage_spec(agent)
        storage_client.ensure_prefix(
            bucket=self.settings.gcs_bucket_name or "",
            prefix=self._uri_prefix(storage_spec.hermes_home_uri),
        )
        storage_client.ensure_prefix(
            bucket=self.settings.gcs_bucket_name or "",
            prefix=self._uri_prefix(storage_spec.private_volume_uri),
        )

        state_disk = compute_client.get_disk(name=storage_spec.state_disk_name)
        if state_disk is None:
            compute_client.create_disk(
                name=storage_spec.state_disk_name,
                size_gb=self.settings.gcp_runtime_state_disk_size_gb,
                disk_type=self.settings.gcp_runtime_state_disk_type,
            )
            state_disk = self._wait_for_disk(compute_client, name=storage_spec.state_disk_name)

        instance_name = self._agent_instance_name(agent)
        instance = compute_client.get_instance(name=instance_name)
        if instance is None:
            compute_client.create_instance(
                body=self._build_instance_body(
                    session=session,
                    agent=agent,
                    instance_name=instance_name,
                    storage_spec=storage_spec,
                    state_disk=state_disk,
                )
            )
            instance = self._wait_for_instance(compute_client, name=instance_name)

        state = instance.status.lower()
        started_at: datetime | None = utcnow() if state == "running" else None
        api_base_url = self._build_api_base_url(instance)

        agent.hermes_home_uri = storage_spec.hermes_home_uri
        agent.private_volume_uri = storage_spec.private_volume_uri
        agent.status = "ready" if state == "running" else "provisioning"
        session.add(agent)

        lease = RuntimeLease(
            agent_id=agent.id,
            vm_id=instance.name,
            state=state,
            api_base_url=api_base_url,
            last_heartbeat_at=started_at,
            started_at=started_at,
        )
        session.add(lease)
        session.commit()
        session.refresh(agent)
        session.refresh(lease)
        return lease

    def _validate_configuration(self) -> None:
        runtime_api_key = self.settings.runtime_api_key or self.settings.dev_runtime_api_key
        missing = [
            name
            for name, value in (
                ("GCS_BUCKET_NAME", self.settings.gcs_bucket_name),
                ("GCP_PROJECT_ID", self.settings.gcp_project_id),
                ("GCP_COMPUTE_ZONE", self.settings.gcp_compute_zone),
                (
                    "GCP_RUNTIME_SOURCE_IMAGE_PROJECT",
                    self.settings.gcp_runtime_source_image_project,
                ),
                ("SUTRA_RUNTIME_API_KEY", runtime_api_key),
            )
            if not value
        ]
        if missing:
            raise RuntimeNotReadyError(
                "GCP Firecracker runtime is not configured. Missing: "
                + ", ".join(missing)
            )
        if not (self.settings.gcp_runtime_source_image or self.settings.gcp_runtime_source_image_family):
            raise RuntimeNotReadyError(
                "GCP Firecracker runtime is not configured. Missing: "
                "GCP_RUNTIME_SOURCE_IMAGE or GCP_RUNTIME_SOURCE_IMAGE_FAMILY"
            )

    def _build_token_provider(self) -> GoogleAccessTokenProvider:
        if self.settings.gcp_runtime_access_token:
            return StaticGoogleAccessTokenProvider(self.settings.gcp_runtime_access_token)
        if self.settings.gcp_service_account_json:
            return ServiceAccountFileGoogleAccessTokenProvider(
                self.settings.gcp_service_account_json
            )
        return MetadataGoogleAccessTokenProvider()

    def _agent_instance_name(self, agent: Agent) -> str:
        return f"sutra-agent-{str(agent.id).replace('-', '')[:20]}"

    def _agent_hermes_home_uri(self, agent: Agent) -> str:
        return f"gs://{self.settings.gcs_bucket_name}/agents/{agent.id}/hermes-home"

    def _agent_private_volume_uri(self, agent: Agent) -> str:
        return f"gs://{self.settings.gcs_bucket_name}/agents/{agent.id}/private-volume"

    def _agent_state_disk_name(self, agent: Agent) -> str:
        return f"sutra-agent-state-{str(agent.id).replace('-', '')[:20]}"

    def _build_storage_spec(self, agent: Agent) -> AgentRuntimeStorageSpec:
        shared_workspace_path = (
            self.settings.gcp_runtime_shared_workspace_path
            if agent.shared_workspace_enabled
            else None
        )
        return AgentRuntimeStorageSpec(
            hermes_home_uri=self._agent_hermes_home_uri(agent),
            private_volume_uri=self._agent_private_volume_uri(agent),
            state_disk_name=self._agent_state_disk_name(agent),
            state_disk_device_name="sutra-agent-state",
            state_mount_path=self.settings.gcp_runtime_state_mount_path,
            hermes_home_path=self.settings.gcp_runtime_hermes_home_path,
            private_volume_path=self.settings.gcp_runtime_private_volume_path,
            shared_workspace_path=shared_workspace_path,
        )

    def _uri_prefix(self, uri: str) -> str:
        prefix = f"gs://{self.settings.gcs_bucket_name}/"
        if not uri.startswith(prefix):
            raise RuntimeNotReadyError(f"Unsupported GCS URI: {uri}")
        return uri.removeprefix(prefix).rstrip("/")

    def _parse_gcs_uri(self, uri: str) -> tuple[str, str]:
        if not uri.startswith("gs://"):
            raise RuntimeNotReadyError(f"Unsupported GCS URI: {uri}")
        remainder = uri.removeprefix("gs://")
        if "/" not in remainder:
            raise RuntimeNotReadyError(f"GCS URI is missing an object path: {uri}")
        bucket, object_path = remainder.split("/", 1)
        return bucket, object_path

    def _source_image_initialize_params(self) -> dict[str, object]:
        if self.settings.gcp_runtime_source_image_family:
            return {
                "sourceImageFamily": self.settings.gcp_runtime_source_image_family,
                "sourceImageProject": self.settings.gcp_runtime_source_image_project,
                "diskSizeGb": str(self.settings.gcp_runtime_boot_disk_size_gb),
            }
        return {
            "sourceImage": (
                "projects/"
                f"{self.settings.gcp_runtime_source_image_project}/global/images/"
                f"{self.settings.gcp_runtime_source_image}"
            ),
            "diskSizeGb": str(self.settings.gcp_runtime_boot_disk_size_gb),
        }

    def _wait_for_instance(
        self,
        compute_client: GcpComputeEngineClient,
        *,
        name: str,
    ) -> GcpComputeInstance:
        instance = None
        for _ in range(5):
            instance = compute_client.get_instance(name=name)
            if instance is not None:
                return instance
            time.sleep(1)
        raise RuntimeNotReadyError("Provisioned GCP runtime instance did not appear in time.")

    def _wait_for_disk(
        self,
        compute_client: GcpComputeEngineClient,
        *,
        name: str,
    ) -> GcpPersistentDisk:
        disk = None
        for _ in range(5):
            disk = compute_client.get_disk(name=name)
            if disk is not None:
                return disk
            time.sleep(1)
        raise RuntimeNotReadyError("Provisioned GCP runtime disk did not appear in time.")

    def _build_instance_body(
        self,
        *,
        session: Session,
        agent: Agent,
        instance_name: str,
        storage_spec: AgentRuntimeStorageSpec,
        state_disk: GcpPersistentDisk,
    ) -> dict[str, object]:
        metadata_items = [
            {"key": "sutra-agent-id", "value": str(agent.id)},
            {"key": "sutra-team-id", "value": str(agent.team_id)},
            {"key": "sutra-runtime-provider", "value": "gcp_firecracker"},
            {"key": "sutra-hermes-home-uri", "value": storage_spec.hermes_home_uri},
            {"key": "sutra-private-volume-uri", "value": storage_spec.private_volume_uri},
            {
                "key": "sutra-runtime-api-key",
                "value": self.settings.runtime_api_key or self.settings.dev_runtime_api_key or "",
            },
            {"key": "sutra-runtime-port", "value": str(self.settings.gcp_runtime_port)},
            {"key": "sutra-state-disk-name", "value": storage_spec.state_disk_name},
            {"key": "sutra-state-mount-path", "value": storage_spec.state_mount_path},
            {"key": "sutra-hermes-home-path", "value": storage_spec.hermes_home_path},
            {"key": "sutra-private-volume-path", "value": storage_spec.private_volume_path},
            {"key": "sutra-runtime-api-bind-host", "value": self.settings.gcp_runtime_api_bind_host},
            {"key": "sutra-runtime-hermes-workdir", "value": self.settings.gcp_runtime_hermes_workdir},
            {"key": "sutra-runtime-python-venv-path", "value": self.settings.gcp_runtime_python_venv_path},
            {"key": "sutra-runtime-session-mode", "value": "responses_conversation"},
            {"key": "startup-script", "value": self._build_startup_script(storage_spec)},
        ]
        if self.settings.gcp_runtime_hermes_bundle_uri:
            metadata_items.append(
                {"key": "sutra-runtime-hermes-bundle-uri", "value": self.settings.gcp_runtime_hermes_bundle_uri}
            )
        shared_workspace_uri = self._load_team_shared_workspace_uri(session, agent)
        if shared_workspace_uri:
            metadata_items.append(
                {"key": "sutra-shared-workspace-uri", "value": shared_workspace_uri}
            )
        if storage_spec.shared_workspace_path:
            metadata_items.append(
                {"key": "sutra-shared-workspace-path", "value": storage_spec.shared_workspace_path}
            )

        network_interface: dict[str, object] = {}
        if self.settings.gcp_runtime_network:
            network_interface["network"] = self.settings.gcp_runtime_network
        if self.settings.gcp_runtime_subnetwork:
            network_interface["subnetwork"] = self.settings.gcp_runtime_subnetwork

        body: dict[str, object] = {
            "name": instance_name,
            "machineType": (
                f"zones/{self.settings.gcp_compute_zone}/machineTypes/"
                f"{self.settings.gcp_runtime_machine_type}"
            ),
            "labels": {
                "sutra-agent-id": str(agent.id).replace("-", "")[:63],
                "sutra-team-id": str(agent.team_id).replace("-", "")[:63],
                "sutra-runtime": "firecracker",
            },
            "disks": [
                {
                    "boot": True,
                    "autoDelete": True,
                    "initializeParams": self._source_image_initialize_params(),
                },
                {
                    "boot": False,
                    "autoDelete": False,
                    "deviceName": storage_spec.state_disk_device_name,
                    "source": state_disk.source_link,
                    "mode": "READ_WRITE",
                },
            ],
            "networkInterfaces": [network_interface],
            "metadata": {"items": metadata_items},
        }
        if self.settings.gcp_runtime_service_account_email:
            body["serviceAccounts"] = [
                {
                    "email": self.settings.gcp_runtime_service_account_email,
                    "scopes": [
                        "https://www.googleapis.com/auth/devstorage.read_write",
                        "https://www.googleapis.com/auth/logging.write",
                    ],
                }
            ]
        return body

    def _load_team_shared_workspace_uri(self, session: Session, agent: Agent) -> str | None:
        if not agent.shared_workspace_enabled:
            return None
        team = session.get(Team, agent.team_id)
        if team is None:
            return None
        return team.shared_workspace_uri

    def _build_api_base_url(self, instance: GcpComputeInstance) -> str | None:
        host = instance.network_ip
        if host is None:
            return None
        return f"http://{host}:{self.settings.gcp_runtime_port}"

    def _build_startup_script(self, storage_spec: AgentRuntimeStorageSpec) -> str:
        runtime_api_key = self.settings.runtime_api_key or self.settings.dev_runtime_api_key or ""
        env_file = "/etc/sutra/runtime.env"
        launcher_path = "/usr/local/bin/sutra-start-hermes-gateway"
        service_path = "/etc/systemd/system/sutra-hermes-gateway.service"
        runtime_user = "sutra-runtime"
        gateway_command = self.settings.gcp_runtime_gateway_command
        gateway_workdir = self.settings.gcp_runtime_hermes_workdir
        gateway_exec_command = gateway_command
        bundle_uri = self.settings.gcp_runtime_hermes_bundle_uri
        python_venv_path = self.settings.gcp_runtime_python_venv_path

        lines = [
            "#!/bin/bash",
            "set -euxo pipefail",
            f"STATE_DEVICE=/dev/disk/by-id/google-{storage_spec.state_disk_device_name}",
            f"STATE_MOUNT={storage_spec.state_mount_path}",
            "mkdir -p \"$STATE_MOUNT\"",
            "if ! blkid \"$STATE_DEVICE\" >/dev/null 2>&1; then",
            "  mkfs.ext4 -F \"$STATE_DEVICE\"",
            "fi",
            "if ! grep -q \"$STATE_DEVICE $STATE_MOUNT \" /etc/fstab; then",
            "  echo \"$STATE_DEVICE $STATE_MOUNT ext4 defaults,nofail 0 2\" >> /etc/fstab",
            "fi",
            "mountpoint -q \"$STATE_MOUNT\" || mount \"$STATE_MOUNT\"",
            f"id -u {runtime_user} >/dev/null 2>&1 || useradd --system --create-home --home-dir /var/lib/{runtime_user} --shell /bin/bash {runtime_user}",
            f"mkdir -p {storage_spec.hermes_home_path}",
            f"mkdir -p {storage_spec.private_volume_path}",
            "mkdir -p /etc/sutra",
            f"chown -R {runtime_user}:{runtime_user} {storage_spec.hermes_home_path}",
            f"chown -R {runtime_user}:{runtime_user} {storage_spec.private_volume_path}",
            f"chmod 700 {storage_spec.hermes_home_path}",
            f"chmod 700 {storage_spec.private_volume_path}",
        ]
        if storage_spec.shared_workspace_path:
            lines.extend(
                [
                    f"mkdir -p {storage_spec.shared_workspace_path}",
                    f"chown -R {runtime_user}:{runtime_user} {storage_spec.shared_workspace_path}",
                    f"chmod 755 {storage_spec.shared_workspace_path}",
                ]
            )
        if bundle_uri:
            bundle_bucket, bundle_object = self._parse_gcs_uri(bundle_uri)
            bundle_download_url = (
                "https://storage.googleapis.com/storage/v1/b/"
                f"{bundle_bucket}/o/{quote(bundle_object, safe='')}?alt=media"
            )
            lines.extend(
                [
                    "export DEBIAN_FRONTEND=noninteractive",
                    "apt-get update",
                    "apt-get install -y python3 python3-venv python3-pip curl ca-certificates tar",
                    f"rm -rf {shlex.quote(gateway_workdir)}",
                    f"mkdir -p {shlex.quote(str(Path(gateway_workdir).parent))}",
                    "METADATA_TOKEN=$(curl -sf -H 'Metadata-Flavor: Google' "
                    "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token "
                    "| python3 -c \"import sys, json; print(json.load(sys.stdin)['access_token'])\")",
                    "curl -sfL -H \"Authorization: Bearer ${METADATA_TOKEN}\" "
                    f"{shlex.quote(bundle_download_url)} -o /tmp/sutra-hermes-bundle.tar.gz",
                    f"tar -xzf /tmp/sutra-hermes-bundle.tar.gz -C {shlex.quote(str(Path(gateway_workdir).parent))}",
                    f"python3 -m venv {shlex.quote(python_venv_path)}",
                    f"{shlex.quote(python_venv_path)}/bin/pip install --upgrade pip",
                    f"cd {shlex.quote(gateway_workdir)}",
                    f"{shlex.quote(python_venv_path)}/bin/pip install -e .",
                ]
            )
            if gateway_command == "python -m gateway.run":
                gateway_exec_command = f"{python_venv_path}/bin/python -m gateway.run"
        lines.extend(
            [
                f"cat > {env_file} <<'EOF'",
                f"HERMES_HOME={storage_spec.hermes_home_path}",
                "API_SERVER_ENABLED=true",
                f"API_SERVER_HOST={self.settings.gcp_runtime_api_bind_host}",
                f"API_SERVER_PORT={self.settings.gcp_runtime_port}",
                f"API_SERVER_KEY={runtime_api_key}",
                "EOF",
                f"chmod 600 {env_file}",
                f"cat > {launcher_path} <<'EOF'",
                "#!/bin/bash",
                "set -euo pipefail",
                f"set -a; source {env_file}; set +a",
                f"cd {shlex.quote(gateway_workdir)}",
                (
                    "exec runuser -u "
                    f"{runtime_user} --preserve-environment -- bash -lc "
                    f"{shlex.quote(f'cd {gateway_workdir} && exec {gateway_exec_command}')}"
                ),
                "EOF",
                f"chmod 755 {launcher_path}",
                f"cat > {service_path} <<'EOF'",
                "[Unit]",
                "Description=Sutra Hermes API Gateway",
                "After=network-online.target",
                "Wants=network-online.target",
                "",
                "[Service]",
                "Type=simple",
                f"ExecStart={launcher_path}",
                "Restart=always",
                "RestartSec=5",
                "",
                "[Install]",
                "WantedBy=multi-user.target",
                "EOF",
                "systemctl daemon-reload",
                "systemctl enable sutra-hermes-gateway.service",
                "systemctl restart sutra-hermes-gateway.service",
            ]
        )
        return "\n".join(lines) + "\n"


def get_runtime_provisioner(settings: Settings) -> RuntimeProvisioner:
    if settings.runtime_provider == "static_dev":
        return StaticDevRuntimeProvisioner(settings)
    if settings.runtime_provider == "gcp_firecracker":
        return GcpFirecrackerRuntimeProvisioner(settings)
    raise RuntimeNotReadyError(f"Unsupported runtime provider: {settings.runtime_provider}")


def ensure_agent_runtime_lease(session: Session, *, agent: Agent, settings: Settings) -> RuntimeLease:
    existing_lease = session.exec(select(RuntimeLease).where(RuntimeLease.agent_id == agent.id)).first()
    if existing_lease is not None:
        if existing_lease.state == "running" and existing_lease.started_at is None:
            existing_lease.started_at = utcnow()
        if existing_lease.state == "running":
            existing_lease.last_heartbeat_at = utcnow()
            if agent.status != "ready":
                agent.status = "ready"
                session.add(agent)
            session.add(existing_lease)
            session.commit()
            session.refresh(existing_lease)
        return existing_lease

    provisioner = get_runtime_provisioner(settings)
    return provisioner.ensure_lease(session, agent=agent)
