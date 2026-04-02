from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
import shlex
import time
from typing import Protocol
from urllib.parse import quote

import httpx
from sqlmodel import Session, select

from sutra_backend.config import BACKEND_ROOT, Settings
from sutra_backend.models import Agent, RuntimeLease, Team, utcnow
from sutra_backend.runtime.errors import RuntimeNotReadyError
from sutra_backend.runtime.firecracker_host import (
    build_agent_hermes_home_path,
    build_agent_private_volume_path,
    build_firecracker_microvm_spec,
    build_team_shared_workspace_path,
)
from sutra_backend.runtime.honcho import build_runtime_honcho_config
from sutra_backend.runtime.managed_env import build_managed_runtime_env


class RuntimeProvisioner(Protocol):
    def ensure_lease(self, session: Session, *, agent: Agent) -> RuntimeLease:
        """Return a ready or provisioned runtime lease for the given agent."""

    def restart_lease(
        self,
        session: Session,
        *,
        agent: Agent,
        lease: RuntimeLease,
    ) -> RuntimeLease:
        """Restart the runtime backing the given lease and persist the updated state."""


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
    external_ip: str | None


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
class GcpFirecrackerMicrovm:
    microvm_id: str
    state: str
    proxy_base_url: str


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
        external_ip = None
        for interface in payload.get("networkInterfaces", []):
            candidate = interface.get("networkIP")
            if isinstance(candidate, str) and candidate:
                network_ip = candidate
            for access_config in interface.get("accessConfigs", []):
                nat_ip = access_config.get("natIP")
                if isinstance(nat_ip, str) and nat_ip:
                    external_ip = nat_ip
                    break
            if network_ip and external_ip:
                break
        return GcpComputeInstance(
            name=str(payload["name"]),
            status=str(payload.get("status", "PROVISIONING")),
            network_ip=network_ip,
            external_ip=external_ip,
        )

    def create_instance(self, *, body: dict[str, object]) -> None:
        response = httpx.post(
            self._base_url(),
            headers=self._headers(),
            json=body,
            timeout=30.0,
        )
        response.raise_for_status()

    def reset_instance(self, *, name: str) -> None:
        response = httpx.post(
            f"{self._base_url()}/{name}/reset",
            headers=self._headers(),
            timeout=30.0,
        )
        response.raise_for_status()

    def start_instance(self, *, name: str) -> None:
        response = httpx.post(
            f"{self._base_url()}/{name}/start",
            headers=self._headers(),
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
class GcpFirecrackerHostClient:
    settings: Settings
    base_url: str

    def _headers(self) -> dict[str, str]:
        runtime_api_key = self.settings.runtime_api_key or self.settings.dev_runtime_api_key
        if not runtime_api_key:
            raise RuntimeNotReadyError("Runtime API key is not configured.")
        return {
            "Authorization": f"Bearer {runtime_api_key}",
            "Content-Type": "application/json",
        }

    def probe_health(self) -> None:
        response = httpx.get(
            f"{self.base_url.rstrip('/')}/healthz",
            headers=self._headers(),
            timeout=30.0,
        )
        response.raise_for_status()

    def provision_microvm(self, *, payload: dict[str, object]) -> GcpFirecrackerMicrovm:
        response = httpx.post(
            f"{self.base_url.rstrip('/')}/microvms/provision",
            headers=self._headers(),
            json=payload,
            timeout=60.0,
        )
        response.raise_for_status()
        result = response.json()
        return GcpFirecrackerMicrovm(
            microvm_id=str(result["microvm_id"]),
            state=str(result.get("state", "provisioning")),
            proxy_base_url=str(result["proxy_base_url"]),
        )

    def restart_microvm(self, *, microvm_id: str) -> GcpFirecrackerMicrovm:
        return self.restart_microvm_with_payload(microvm_id=microvm_id, payload=None)

    def restart_microvm_with_payload(
        self,
        *,
        microvm_id: str,
        payload: dict[str, object] | None,
    ) -> GcpFirecrackerMicrovm:
        response = httpx.post(
            f"{self.base_url.rstrip('/')}/microvms/{microvm_id}/restart",
            headers=self._headers(),
            json=payload,
            timeout=60.0,
        )
        response.raise_for_status()
        result = response.json()
        return GcpFirecrackerMicrovm(
            microvm_id=str(result["microvm_id"]),
            state=str(result.get("state", "provisioning")),
            proxy_base_url=str(result["proxy_base_url"]),
        )


@dataclass(frozen=True)
class StaticDevRuntimeProvisioner:
    settings: Settings

    def ensure_lease(self, session: Session, *, agent: Agent) -> RuntimeLease:
        if not self.settings.dev_runtime_base_url:
            raise RuntimeNotReadyError("Static dev runtime is not configured.")

        started_at = utcnow()
        agent.hermes_home_uri = f"local://agents/{agent.id}/hermes-home"
        agent.private_volume_uri = f"local://agents/{agent.id}/private-volume"
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

    def restart_lease(
        self,
        session: Session,
        *,
        agent: Agent,
        lease: RuntimeLease,
    ) -> RuntimeLease:
        if not self.settings.dev_runtime_base_url:
            raise RuntimeNotReadyError("Static dev runtime is not configured.")

        started_at = utcnow()
        agent.hermes_home_uri = agent.hermes_home_uri or f"local://agents/{agent.id}/hermes-home"
        agent.private_volume_uri = (
            agent.private_volume_uri or f"local://agents/{agent.id}/private-volume"
        )
        agent.status = "ready"
        lease.vm_id = lease.vm_id or f"local-dev-{str(agent.id)[:8]}"
        lease.state = "running"
        lease.api_base_url = self.settings.dev_runtime_base_url
        lease.started_at = started_at
        lease.last_heartbeat_at = started_at
        lease.updated_at = started_at
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
        instance, host_api_base_url = self._ensure_host_instance(compute_client)
        microvm = self._ensure_agent_microvm(
            session=session,
            agent=agent,
            host_api_base_url=host_api_base_url,
        )
        state = microvm.state.lower()
        started_at: datetime | None = utcnow() if state == "running" else None

        agent.hermes_home_uri = storage_spec.hermes_home_uri
        agent.private_volume_uri = storage_spec.private_volume_uri
        agent.status = "ready" if state == "running" else "provisioning"
        session.add(agent)

        lease = RuntimeLease(
            agent_id=agent.id,
            vm_id=microvm.microvm_id,
            host_vm_id=instance.name,
            host_api_base_url=host_api_base_url,
            state=state,
            api_base_url=microvm.proxy_base_url,
            last_heartbeat_at=started_at,
            started_at=started_at,
        )
        session.add(lease)
        session.commit()
        session.refresh(agent)
        session.refresh(lease)
        return lease

    def restart_lease(
        self,
        session: Session,
        *,
        agent: Agent,
        lease: RuntimeLease,
    ) -> RuntimeLease:
        self._validate_configuration()
        token_provider = self._build_token_provider()
        compute_client = GcpComputeEngineClient(self.settings, token_provider)
        storage_spec = self._build_storage_spec(agent)
        instance, host_api_base_url = self._ensure_host_instance(compute_client)
        microvm = self._restart_agent_microvm(
            session=session,
            agent=agent,
            lease=lease,
            host_api_base_url=host_api_base_url,
        )
        state = microvm.state.lower()
        started_at: datetime | None = utcnow() if state == "running" else None

        agent.hermes_home_uri = storage_spec.hermes_home_uri
        agent.private_volume_uri = storage_spec.private_volume_uri
        agent.status = "ready" if state == "running" else "provisioning"
        session.add(agent)

        lease.vm_id = microvm.microvm_id
        lease.host_vm_id = instance.name
        lease.host_api_base_url = host_api_base_url
        lease.state = state
        lease.api_base_url = microvm.proxy_base_url
        lease.started_at = started_at
        lease.last_heartbeat_at = started_at
        lease.updated_at = utcnow()
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
                ("GCP_RUNTIME_HOST_INSTANCE_NAME", self.settings.gcp_runtime_host_instance_name),
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

    def _host_instance_name(self) -> str:
        return self.settings.gcp_runtime_host_instance_name

    def _agent_hermes_home_uri(self, agent: Agent) -> str:
        return f"gs://{self.settings.gcs_bucket_name}/agents/{agent.id}/hermes-home"

    def _agent_private_volume_uri(self, agent: Agent) -> str:
        return f"gs://{self.settings.gcs_bucket_name}/agents/{agent.id}/private-volume"

    def _host_state_disk_name(self) -> str:
        return f"{self.settings.gcp_runtime_host_instance_name}-data"[:63]

    def _build_storage_spec(self, agent: Agent) -> AgentRuntimeStorageSpec:
        spec = AgentRuntimeStorageSpec(
            hermes_home_uri=self._agent_hermes_home_uri(agent),
            private_volume_uri=self._agent_private_volume_uri(agent),
            state_disk_name=self._host_state_disk_name(),
            state_disk_device_name="sutra-host-data",
            state_mount_path=self.settings.gcp_runtime_state_mount_path,
            hermes_home_path=build_agent_hermes_home_path(settings=self.settings, agent=agent),
            private_volume_path=build_agent_private_volume_path(settings=self.settings, agent=agent),
            shared_workspace_path=build_team_shared_workspace_path(
                settings=self.settings,
                agent=agent,
            ),
        )
        self._validate_storage_spec(spec)
        return spec

    def _validate_storage_spec(self, storage_spec: AgentRuntimeStorageSpec) -> None:
        state_mount = PurePosixPath(storage_spec.state_mount_path)
        agent_root = PurePosixPath(self.settings.gcp_runtime_agent_root_path)
        shared_root = PurePosixPath(self.settings.gcp_runtime_shared_workspace_root_path)
        hermes_home = PurePosixPath(storage_spec.hermes_home_path)
        private_volume = PurePosixPath(storage_spec.private_volume_path)

        if hermes_home == private_volume:
            raise RuntimeNotReadyError("Runtime HERMES_HOME path and private volume path must be distinct.")
        if state_mount not in hermes_home.parents and hermes_home != state_mount:
            raise RuntimeNotReadyError("Runtime HERMES_HOME path must live under the private state mount.")
        if state_mount not in private_volume.parents and private_volume != state_mount:
            raise RuntimeNotReadyError("Runtime private volume path must live under the private state mount.")
        if state_mount not in agent_root.parents and agent_root != state_mount:
            raise RuntimeNotReadyError("Agent root path must live under the private state mount.")
        if agent_root not in hermes_home.parents:
            raise RuntimeNotReadyError("Agent private paths must live under the agent root.")
        if agent_root not in private_volume.parents:
            raise RuntimeNotReadyError("Agent private volume must live under the agent root.")
        if storage_spec.shared_workspace_path is None:
            return

        shared_workspace = PurePosixPath(storage_spec.shared_workspace_path)
        if state_mount in shared_root.parents or shared_root == state_mount:
            raise RuntimeNotReadyError("Shared workspace path must not live under the private state mount.")
        if shared_workspace == hermes_home or shared_workspace == private_volume:
            raise RuntimeNotReadyError("Shared workspace path must be separate from private runtime paths.")
        if shared_root not in shared_workspace.parents and shared_workspace != shared_root:
            raise RuntimeNotReadyError("Shared workspace path must live under the shared workspace root.")
        if shared_workspace in hermes_home.parents or hermes_home in shared_workspace.parents:
            raise RuntimeNotReadyError("Shared workspace path must not overlap the private HERMES_HOME path.")
        if shared_workspace in private_volume.parents or private_volume in shared_workspace.parents:
            raise RuntimeNotReadyError("Shared workspace path must not overlap the private volume path.")

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

    def _build_backend_runtime_bundle_uri(self) -> str | None:
        hermes_bundle_uri = self.settings.gcp_runtime_hermes_bundle_uri
        if not hermes_bundle_uri:
            return None
        bucket, object_path = self._parse_gcs_uri(hermes_bundle_uri)
        bundle_path = Path(object_path)
        backend_object_path = str(bundle_path.with_name("sutra-backend-runtime.tar.gz"))
        return f"gs://{bucket}/{backend_object_path}"

    def _build_host_gateway_command(self, *, python_venv_path: str) -> str:
        gateway_command = self.settings.gcp_runtime_gateway_command.strip()
        if gateway_command in {"python -m gateway.run", "python3 -m gateway.run"}:
            return f"{python_venv_path}/bin/python -m gateway.run"
        return gateway_command

    def _wait_for_instance(
        self,
        compute_client: GcpComputeEngineClient,
        *,
        name: str,
    ) -> GcpComputeInstance:
        instance = None
        for _ in range(10):
            instance = compute_client.get_instance(name=name)
            if instance is not None and instance.network_ip:
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
        instance_name: str,
        state_disk: GcpPersistentDisk,
    ) -> dict[str, object]:
        metadata_items = [
            {"key": "sutra-runtime-provider", "value": "gcp_firecracker"},
            {
                "key": "sutra-runtime-api-key",
                "value": self.settings.runtime_api_key or self.settings.dev_runtime_api_key or "",
            },
            {"key": "sutra-host-api-port", "value": str(self.settings.gcp_runtime_host_api_port)},
            {"key": "sutra-state-disk-name", "value": self._host_state_disk_name()},
            {"key": "sutra-state-mount-path", "value": self.settings.gcp_runtime_state_mount_path},
            {"key": "sutra-agent-root-path", "value": self.settings.gcp_runtime_agent_root_path},
            {
                "key": "sutra-shared-workspace-root-path",
                "value": self.settings.gcp_runtime_shared_workspace_root_path,
            },
            {
                "key": "sutra-runtime-host-api-bind-host",
                "value": self.settings.gcp_runtime_host_api_bind_host,
            },
            {"key": "sutra-runtime-hermes-workdir", "value": self.settings.gcp_runtime_hermes_workdir},
            {"key": "sutra-runtime-python-venv-path", "value": self.settings.gcp_runtime_python_venv_path},
            {
                "key": "sutra-firecracker-kernel-path",
                "value": self.settings.gcp_runtime_firecracker_kernel_path,
            },
            {
                "key": "sutra-firecracker-rootfs-path",
                "value": self.settings.gcp_runtime_firecracker_rootfs_path,
            },
            {"key": "startup-script", "value": self._build_startup_script()},
        ]
        if self.settings.gcp_runtime_hermes_bundle_uri:
            metadata_items.append(
                {"key": "sutra-runtime-hermes-bundle-uri", "value": self.settings.gcp_runtime_hermes_bundle_uri}
            )

        network_interface: dict[str, object] = {}
        if self.settings.gcp_runtime_network:
            network_interface["network"] = self.settings.gcp_runtime_network
        if self.settings.gcp_runtime_subnetwork:
            network_interface["subnetwork"] = self.settings.gcp_runtime_subnetwork
        if self.settings.gcp_runtime_assign_public_ip:
            network_interface["accessConfigs"] = [{"name": "External NAT", "type": "ONE_TO_ONE_NAT"}]

        body: dict[str, object] = {
            "name": instance_name,
            "machineType": (
                f"zones/{self.settings.gcp_compute_zone}/machineTypes/"
                f"{self.settings.gcp_runtime_machine_type}"
            ),
            "labels": {
                "sutra-host": instance_name.replace("-", "")[:63],
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
                    "deviceName": "sutra-host-data",
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

    def _build_host_api_base_url(self, instance: GcpComputeInstance) -> str | None:
        if self.settings.gcp_runtime_host_api_override_base_url:
            return self.settings.gcp_runtime_host_api_override_base_url.rstrip("/")
        host = instance.network_ip
        if self.settings.gcp_runtime_use_public_ip and instance.external_ip:
            host = instance.external_ip
        if host is None:
            return None
        return f"http://{host}:{self.settings.gcp_runtime_host_api_port}"

    def _build_startup_script(self) -> str:
        runtime_api_key = self.settings.runtime_api_key or self.settings.dev_runtime_api_key or ""
        env_file = "/etc/sutra/runtime-host.env"
        launcher_path = "/usr/local/bin/sutra-start-firecracker-host"
        service_path = "/etc/systemd/system/sutra-firecracker-host.service"
        runtime_user = "sutra-runtime"
        gateway_workdir = self.settings.gcp_runtime_hermes_workdir
        bundle_uri = self.settings.gcp_runtime_hermes_bundle_uri
        backend_bundle_uri = self._build_backend_runtime_bundle_uri()
        python_venv_path = self.settings.gcp_runtime_python_venv_path
        host_gateway_command = self._build_host_gateway_command(python_venv_path=python_venv_path)
        backend_workdir = "/opt/sutra-backend"
        microvm_root = str(Path(self.settings.gcp_runtime_state_mount_path) / "microvms")

        lines = [
            "#!/bin/bash",
            "set -euxo pipefail",
            f"STATE_DEVICE=/dev/disk/by-id/google-sutra-host-data",
            f"STATE_MOUNT={self.settings.gcp_runtime_state_mount_path}",
            "mkdir -p \"$STATE_MOUNT\"",
            "if ! blkid \"$STATE_DEVICE\" >/dev/null 2>&1; then",
            "  mkfs.ext4 -F \"$STATE_DEVICE\"",
            "fi",
            "if ! grep -q \"$STATE_DEVICE $STATE_MOUNT \" /etc/fstab; then",
            "  echo \"$STATE_DEVICE $STATE_MOUNT ext4 defaults,nofail 0 2\" >> /etc/fstab",
            "fi",
            "mountpoint -q \"$STATE_MOUNT\" || mount \"$STATE_MOUNT\"",
            f"id -u {runtime_user} >/dev/null 2>&1 || useradd --system --create-home --home-dir /var/lib/{runtime_user} --shell /bin/bash {runtime_user}",
            f"mkdir -p {self.settings.gcp_runtime_agent_root_path}",
            f"mkdir -p {microvm_root}",
            f"mkdir -p {self.settings.gcp_runtime_shared_workspace_root_path}",
            "mkdir -p /etc/sutra",
            f"test ! -L {self.settings.gcp_runtime_agent_root_path}",
            f"test ! -L {microvm_root}",
            f"test ! -L {self.settings.gcp_runtime_shared_workspace_root_path}",
            f"chown -R {runtime_user}:{runtime_user} {self.settings.gcp_runtime_agent_root_path}",
            f"chown -R {runtime_user}:{runtime_user} {microvm_root}",
            f"chown -R {runtime_user}:{runtime_user} {self.settings.gcp_runtime_shared_workspace_root_path}",
            f"chmod 700 {self.settings.gcp_runtime_agent_root_path}",
            f"chmod 700 {microvm_root}",
            f"chmod 755 {self.settings.gcp_runtime_shared_workspace_root_path}",
        ]
        if bundle_uri and backend_bundle_uri:
            bundle_bucket, bundle_object = self._parse_gcs_uri(bundle_uri)
            bundle_download_url = (
                "https://storage.googleapis.com/storage/v1/b/"
                f"{bundle_bucket}/o/{quote(bundle_object, safe='')}?alt=media"
            )
            backend_bundle_bucket, backend_bundle_object = self._parse_gcs_uri(backend_bundle_uri)
            backend_bundle_download_url = (
                "https://storage.googleapis.com/storage/v1/b/"
                f"{backend_bundle_bucket}/o/{quote(backend_bundle_object, safe='')}?alt=media"
            )
            lines.extend(
                [
                    "export DEBIAN_FRONTEND=noninteractive",
                    "apt-get update",
                    "apt-get install -y python3 python3-venv python3-pip curl ca-certificates tar",
                    f"rm -rf {shlex.quote(gateway_workdir)}",
                    f"rm -rf {shlex.quote(backend_workdir)}",
                    f"mkdir -p {shlex.quote(str(Path(gateway_workdir).parent))}",
                    f"mkdir -p {shlex.quote(str(Path(backend_workdir).parent))}",
                    "METADATA_TOKEN=$(curl -sf -H 'Metadata-Flavor: Google' "
                    "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token "
                    "| python3 -c \"import sys, json; print(json.load(sys.stdin)['access_token'])\")",
                    "curl -sfL -H \"Authorization: Bearer ${METADATA_TOKEN}\" "
                    f"{shlex.quote(bundle_download_url)} -o /tmp/sutra-hermes-bundle.tar.gz",
                    "curl -sfL -H \"Authorization: Bearer ${METADATA_TOKEN}\" "
                    f"{shlex.quote(backend_bundle_download_url)} -o /tmp/sutra-backend-runtime.tar.gz",
                    f"tar -xzf /tmp/sutra-hermes-bundle.tar.gz -C {shlex.quote(str(Path(gateway_workdir).parent))}",
                    f"tar -xzf /tmp/sutra-backend-runtime.tar.gz -C {shlex.quote(str(Path(backend_workdir).parent))}",
                    f"python3 -m venv {shlex.quote(python_venv_path)}",
                    f"{shlex.quote(python_venv_path)}/bin/pip install --upgrade pip",
                    f"cd {shlex.quote(gateway_workdir)}",
                    f"{shlex.quote(python_venv_path)}/bin/pip install -r requirements.txt fastapi pydantic-settings uvicorn sqlmodel 'honcho-ai>=2.0.1,<3' 'anthropic>=0.39.0'",
                ]
            )
        lines.extend(
            [
                f"cat > {env_file} <<'EOF'",
                f"SUTRA_RUNTIME_API_KEY={runtime_api_key}",
                f"GCP_RUNTIME_STATE_MOUNT_PATH={self.settings.gcp_runtime_state_mount_path}",
                f"GCP_RUNTIME_AGENT_ROOT_PATH={self.settings.gcp_runtime_agent_root_path}",
                f"GCP_RUNTIME_SHARED_WORKSPACE_ROOT_PATH={self.settings.gcp_runtime_shared_workspace_root_path}",
                f"GCP_RUNTIME_HOST_API_BIND_HOST={self.settings.gcp_runtime_host_api_bind_host}",
                f"GCP_RUNTIME_HOST_API_PORT={self.settings.gcp_runtime_host_api_port}",
                f"GCP_RUNTIME_HERMES_WORKDIR={self.settings.gcp_runtime_hermes_workdir}",
                f"GCP_RUNTIME_GATEWAY_COMMAND={shlex.quote(host_gateway_command)}",
                f"GCP_RUNTIME_FIRECRACKER_EXECUTE={'true' if self.settings.gcp_runtime_firecracker_execute else 'false'}",
                f"PYTHONPATH={backend_workdir}:{gateway_workdir}",
                "EOF",
                f"chmod 600 {env_file}",
                f"cat > {launcher_path} <<'EOF'",
                "#!/bin/bash",
                "set -euo pipefail",
                f"set -a; source {env_file}; set +a",
                f"cd {shlex.quote(backend_workdir)}",
                (
                    "exec runuser -u "
                    f"{runtime_user} --preserve-environment -- bash -lc "
                    f"{shlex.quote(f'cd {backend_workdir} && exec {python_venv_path}/bin/uvicorn sutra_backend.runtime.firecracker_host_service:app --host {self.settings.gcp_runtime_host_api_bind_host} --port {self.settings.gcp_runtime_host_api_port}')}"
                ),
                "EOF",
                f"chmod 755 {launcher_path}",
                f"cat > {service_path} <<'EOF'",
                "[Unit]",
                "Description=Sutra Firecracker Host Manager",
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
                "systemctl enable sutra-firecracker-host.service",
                "systemctl restart sutra-firecracker-host.service",
            ]
        )
        return "\n".join(lines) + "\n"

    def _ensure_host_instance(
        self,
        compute_client: GcpComputeEngineClient,
    ) -> tuple[GcpComputeInstance, str]:
        state_disk = compute_client.get_disk(name=self._host_state_disk_name())
        if state_disk is None:
            compute_client.create_disk(
                name=self._host_state_disk_name(),
                size_gb=self.settings.gcp_runtime_state_disk_size_gb,
                disk_type=self.settings.gcp_runtime_state_disk_type,
            )
            state_disk = self._wait_for_disk(compute_client, name=self._host_state_disk_name())

        instance_name = self._host_instance_name()
        instance = compute_client.get_instance(name=instance_name)
        if instance is None:
            compute_client.create_instance(
                body=self._build_instance_body(
                    instance_name=instance_name,
                    state_disk=state_disk,
                )
            )
            instance = self._wait_for_instance(compute_client, name=instance_name)
        elif instance.status.upper() in {"TERMINATED", "STOPPED", "SUSPENDED"}:
            compute_client.start_instance(name=instance_name)
            instance = self._wait_for_instance(compute_client, name=instance_name)

        host_api_base_url = self._build_host_api_base_url(instance)
        if not host_api_base_url:
            raise RuntimeNotReadyError("Runtime host does not have a reachable API endpoint.")
        self._wait_for_host_api(host_api_base_url)
        return instance, host_api_base_url

    def _wait_for_host_api(self, host_api_base_url: str) -> None:
        host_client = GcpFirecrackerHostClient(
            settings=self.settings,
            base_url=host_api_base_url,
        )
        last_error: Exception | None = None
        for _ in range(10):
            try:
                host_client.probe_health()
                return
            except Exception as exc:  # pragma: no cover - exercised via tests with monkeypatch
                last_error = exc
                time.sleep(1)
        raise RuntimeNotReadyError(f"Runtime host API did not become ready: {last_error}")

    def _ensure_agent_microvm(
        self,
        *,
        session: Session,
        agent: Agent,
        host_api_base_url: str,
    ) -> GcpFirecrackerMicrovm:
        team = session.get(Team, agent.team_id)
        if team is None:
            raise RuntimeNotReadyError("Agent team is missing; cannot build Honcho workspace identity.")
        host_client = GcpFirecrackerHostClient(settings=self.settings, base_url=host_api_base_url)
        spec = build_firecracker_microvm_spec(
            settings=self.settings,
            agent=agent,
            host_api_base_url=host_api_base_url,
        )
        runtime_env = build_managed_runtime_env(self.settings)
        microvm = host_client.provision_microvm(payload={
            "microvm_id": spec.microvm_id,
            "agent_id": spec.agent_id,
            "team_id": spec.team_id,
            "runtime_port": spec.runtime_port,
            "proxy_base_url": spec.proxy_base_url,
            "runtime_api_url": spec.runtime_api_url,
            "storage": {
                "private_root": spec.storage.private_root,
                "hermes_home_path": spec.storage.hermes_home_path,
                "private_volume_path": spec.storage.private_volume_path,
                "shared_workspace_path": spec.storage.shared_workspace_path,
            },
            "honcho_config": build_runtime_honcho_config(
                settings=self.settings,
                user_id=team.user_id,
                agent_id=agent.id,
            ),
            "runtime_env": runtime_env or None,
        })
        return microvm

    def _restart_agent_microvm(
        self,
        *,
        session: Session,
        agent: Agent,
        lease: RuntimeLease,
        host_api_base_url: str,
    ) -> GcpFirecrackerMicrovm:
        team = session.get(Team, agent.team_id)
        if team is None:
            raise RuntimeNotReadyError("Agent team is missing; cannot build Honcho workspace identity.")
        host_client = GcpFirecrackerHostClient(settings=self.settings, base_url=host_api_base_url)
        microvm_id = lease.vm_id or build_firecracker_microvm_spec(
            settings=self.settings,
            agent=agent,
            host_api_base_url=host_api_base_url,
        ).microvm_id
        runtime_env = build_managed_runtime_env(self.settings)
        return host_client.restart_microvm_with_payload(
            microvm_id=microvm_id,
            payload={
                "honcho_config": build_runtime_honcho_config(
                    settings=self.settings,
                    user_id=team.user_id,
                    agent_id=agent.id,
                ),
                "runtime_env": runtime_env or None,
            },
        )


def get_runtime_provisioner(settings: Settings) -> RuntimeProvisioner:
    if settings.runtime_provider == "static_dev":
        return StaticDevRuntimeProvisioner(settings)
    if settings.runtime_provider == "gcp_firecracker":
        return GcpFirecrackerRuntimeProvisioner(settings)
    raise RuntimeNotReadyError(f"Unsupported runtime provider: {settings.runtime_provider}")


def _infer_lease_provider(lease: RuntimeLease) -> str:
    if lease.vm_id.startswith("local-dev-"):
        return "static_dev"
    return "gcp_firecracker"


def _provider_matches_existing_lease(*, lease: RuntimeLease, settings: Settings) -> bool:
    return _infer_lease_provider(lease) == settings.runtime_provider


def sync_runtime_lease_with_settings(*, lease: RuntimeLease, settings: Settings) -> bool:
    changed = False

    if _infer_lease_provider(lease) == "static_dev":
        desired_base_url = settings.dev_runtime_base_url
        if desired_base_url and lease.api_base_url != desired_base_url:
            lease.api_base_url = desired_base_url
            changed = True
        if lease.host_vm_id is not None:
            lease.host_vm_id = None
            changed = True
        if lease.host_api_base_url is not None:
            lease.host_api_base_url = None
            changed = True

    if changed:
        lease.updated_at = utcnow()

    return changed


def ensure_agent_runtime_lease(session: Session, *, agent: Agent, settings: Settings) -> RuntimeLease:
    existing_lease = session.exec(select(RuntimeLease).where(RuntimeLease.agent_id == agent.id)).first()
    if existing_lease is not None:
        if not _provider_matches_existing_lease(lease=existing_lease, settings=settings):
            session.delete(existing_lease)
            session.commit()
        else:
            sync_runtime_lease_with_settings(lease=existing_lease, settings=settings)
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


def restart_agent_runtime_lease(
    session: Session,
    *,
    agent: Agent,
    settings: Settings,
) -> RuntimeLease:
    existing_lease = session.exec(select(RuntimeLease).where(RuntimeLease.agent_id == agent.id)).first()
    provisioner = get_runtime_provisioner(settings)
    if existing_lease is None:
        return provisioner.ensure_lease(session, agent=agent)
    if not _provider_matches_existing_lease(lease=existing_lease, settings=settings):
        session.delete(existing_lease)
        session.commit()
        return provisioner.ensure_lease(session, agent=agent)
    return provisioner.restart_lease(session, agent=agent, lease=existing_lease)
