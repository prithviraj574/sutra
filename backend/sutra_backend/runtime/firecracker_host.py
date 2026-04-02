from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from uuid import UUID

from sutra_backend.config import Settings
from sutra_backend.models import Agent


@dataclass(frozen=True)
class FirecrackerStoragePaths:
    private_root: str
    hermes_home_path: str
    private_volume_path: str
    shared_workspace_path: str | None


@dataclass(frozen=True)
class FirecrackerMicrovmSpec:
    microvm_id: str
    agent_id: str
    team_id: str
    runtime_port: int
    proxy_base_url: str
    runtime_api_url: str
    storage: FirecrackerStoragePaths

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)


def build_microvm_id(agent_id: UUID | str) -> str:
    return f"agent-{str(agent_id).replace('-', '')[:20]}"


def build_agent_private_root(*, settings: Settings, agent: Agent) -> str:
    return str(PurePosixPath(settings.gcp_runtime_agent_root_path) / str(agent.id))


def build_agent_hermes_home_path(*, settings: Settings, agent: Agent) -> str:
    return str(PurePosixPath(build_agent_private_root(settings=settings, agent=agent)) / "hermes-home")


def build_agent_private_volume_path(*, settings: Settings, agent: Agent) -> str:
    return str(PurePosixPath(build_agent_private_root(settings=settings, agent=agent)) / "private-volume")


def build_team_shared_workspace_path(*, settings: Settings, agent: Agent) -> str | None:
    del settings, agent
    return None


def build_runtime_proxy_base_url(*, host_api_base_url: str, microvm_id: str) -> str:
    return f"{host_api_base_url.rstrip('/')}/microvms/{microvm_id}/proxy/"


def build_microvm_runtime_port(*, settings: Settings, agent: Agent) -> int:
    digest = hashlib.sha1(str(agent.id).encode("utf-8")).hexdigest()
    slot = int(digest[:4], 16) % 2000
    return settings.gcp_runtime_host_microvm_base_port + slot


def build_firecracker_storage_paths(*, settings: Settings, agent: Agent) -> FirecrackerStoragePaths:
    return FirecrackerStoragePaths(
        private_root=build_agent_private_root(settings=settings, agent=agent),
        hermes_home_path=build_agent_hermes_home_path(settings=settings, agent=agent),
        private_volume_path=build_agent_private_volume_path(settings=settings, agent=agent),
        shared_workspace_path=build_team_shared_workspace_path(settings=settings, agent=agent),
    )


def build_firecracker_microvm_spec(
    *,
    settings: Settings,
    agent: Agent,
    host_api_base_url: str,
) -> FirecrackerMicrovmSpec:
    microvm_id = build_microvm_id(agent.id)
    runtime_port = build_microvm_runtime_port(settings=settings, agent=agent)
    return FirecrackerMicrovmSpec(
        microvm_id=microvm_id,
        agent_id=str(agent.id),
        team_id="none",
        runtime_port=runtime_port,
        proxy_base_url=build_runtime_proxy_base_url(
            host_api_base_url=host_api_base_url,
            microvm_id=microvm_id,
        ),
        runtime_api_url=f"http://127.0.0.1:{runtime_port}/",
        storage=build_firecracker_storage_paths(settings=settings, agent=agent),
    )


def build_firecracker_machine_config() -> dict[str, int | bool]:
    return {
        "vcpu_count": 2,
        "mem_size_mib": 2048,
        "smt": False,
    }


def build_firecracker_config(
    *,
    settings: Settings,
    spec: FirecrackerMicrovmSpec,
) -> dict[str, object]:
    return {
        "boot-source": {
            "kernel_image_path": settings.gcp_runtime_firecracker_kernel_path,
            "boot_args": (
                "console=ttyS0 reboot=k panic=1 pci=off "
                f"agent_id={spec.agent_id} team_id={spec.team_id}"
            ),
        },
        "drives": [
            {
                "drive_id": "rootfs",
                "path_on_host": settings.gcp_runtime_firecracker_rootfs_path,
                "is_root_device": True,
                "is_read_only": False,
            }
        ],
        "machine-config": build_firecracker_machine_config(),
        "metadata": {
            "microvm_id": spec.microvm_id,
            "agent_id": spec.agent_id,
            "team_id": spec.team_id,
            "runtime_port": spec.runtime_port,
            "hermes_home_path": spec.storage.hermes_home_path,
            "private_volume_path": spec.storage.private_volume_path,
            "shared_workspace_path": spec.storage.shared_workspace_path,
        },
    }


def build_firecracker_config_path(*, settings: Settings, spec: FirecrackerMicrovmSpec) -> str:
    return str(Path(settings.gcp_runtime_state_mount_path) / "microvms" / spec.microvm_id / "firecracker-config.json")
