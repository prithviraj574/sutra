from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import time
from typing import Protocol
from urllib.parse import quote

import httpx
from sqlmodel import Session, select

from sutra_backend.config import Settings
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
class GcpComputeInstance:
    name: str
    status: str
    network_ip: str | None


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

        hermes_home_uri = self._agent_hermes_home_uri(agent)
        private_volume_uri = self._agent_private_volume_uri(agent)
        storage_client.ensure_prefix(
            bucket=self.settings.gcs_bucket_name or "",
            prefix=self._uri_prefix(hermes_home_uri),
        )
        storage_client.ensure_prefix(
            bucket=self.settings.gcs_bucket_name or "",
            prefix=self._uri_prefix(private_volume_uri),
        )

        instance_name = self._agent_instance_name(agent)
        instance = compute_client.get_instance(name=instance_name)
        if instance is None:
            compute_client.create_instance(
                body=self._build_instance_body(
                    session=session,
                    agent=agent,
                    instance_name=instance_name,
                    hermes_home_uri=hermes_home_uri,
                    private_volume_uri=private_volume_uri,
                )
            )
            instance = self._wait_for_instance(compute_client, name=instance_name)

        state = instance.status.lower()
        started_at: datetime | None = utcnow() if state == "running" else None
        api_base_url = self._build_api_base_url(instance)

        agent.hermes_home_uri = hermes_home_uri
        agent.private_volume_uri = private_volume_uri
        agent.status = "ready" if state == "running" else "provisioning"
        session.add(agent)

        lease = RuntimeLease(
            agent_id=agent.id,
            vm_id=instance.name,
            state=state,
            api_base_url=api_base_url,
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
                ("GCP_RUNTIME_SOURCE_IMAGE", self.settings.gcp_runtime_source_image),
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

    def _build_token_provider(self) -> GoogleAccessTokenProvider:
        if self.settings.gcp_runtime_access_token:
            return StaticGoogleAccessTokenProvider(self.settings.gcp_runtime_access_token)
        return MetadataGoogleAccessTokenProvider()

    def _agent_instance_name(self, agent: Agent) -> str:
        return f"sutra-agent-{str(agent.id).replace('-', '')[:20]}"

    def _agent_hermes_home_uri(self, agent: Agent) -> str:
        return f"gs://{self.settings.gcs_bucket_name}/agents/{agent.id}/hermes-home"

    def _agent_private_volume_uri(self, agent: Agent) -> str:
        return f"gs://{self.settings.gcs_bucket_name}/agents/{agent.id}/private-volume"

    def _uri_prefix(self, uri: str) -> str:
        prefix = f"gs://{self.settings.gcs_bucket_name}/"
        if not uri.startswith(prefix):
            raise RuntimeNotReadyError(f"Unsupported GCS URI: {uri}")
        return uri.removeprefix(prefix).rstrip("/")

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

    def _build_instance_body(
        self,
        *,
        session: Session,
        agent: Agent,
        instance_name: str,
        hermes_home_uri: str,
        private_volume_uri: str,
    ) -> dict[str, object]:
        metadata_items = [
            {"key": "sutra-agent-id", "value": str(agent.id)},
            {"key": "sutra-team-id", "value": str(agent.team_id)},
            {"key": "sutra-runtime-provider", "value": "gcp_firecracker"},
            {"key": "sutra-hermes-home-uri", "value": hermes_home_uri},
            {"key": "sutra-private-volume-uri", "value": private_volume_uri},
            {
                "key": "sutra-runtime-api-key",
                "value": self.settings.runtime_api_key or self.settings.dev_runtime_api_key or "",
            },
            {"key": "sutra-runtime-port", "value": str(self.settings.gcp_runtime_port)},
        ]
        shared_workspace_uri = self._load_team_shared_workspace_uri(session, agent)
        if shared_workspace_uri:
            metadata_items.append(
                {"key": "sutra-shared-workspace-uri", "value": shared_workspace_uri}
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
                    "initializeParams": {
                        "sourceImage": (
                            "projects/"
                            f"{self.settings.gcp_runtime_source_image_project}/global/images/"
                            f"{self.settings.gcp_runtime_source_image}"
                        ),
                        "diskSizeGb": str(self.settings.gcp_runtime_boot_disk_size_gb),
                    },
                }
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
            session.add(existing_lease)
            session.commit()
            session.refresh(existing_lease)
        return existing_lease

    provisioner = get_runtime_provisioner(settings)
    return provisioner.ensure_lease(session, agent=agent)
