from __future__ import annotations

from pathlib import PurePosixPath
from uuid import uuid4

from sutra_backend.config import Settings
from sutra_backend.models import Agent
from sutra_backend.runtime.firecracker_host import build_firecracker_microvm_spec


def test_build_firecracker_microvm_spec_keeps_private_paths_isolated() -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        gcp_runtime_agent_root_path="/mnt/sutra/state/agents",
        gcp_runtime_shared_workspace_root_path="/mnt/sutra/shared-workspaces",
        gcp_runtime_host_microvm_base_port=10080,
    )
    agent = Agent(
        user_id=uuid4(),
        name="Research Agent",
        role_name="Researcher",
    )

    spec = build_firecracker_microvm_spec(
        settings=settings,
        agent=agent,
        host_api_base_url="http://10.0.0.8:8787",
    )

    assert spec.microvm_id == f"agent-{str(agent.id).replace('-', '')[:20]}"
    assert spec.proxy_base_url.endswith(f"/microvms/{spec.microvm_id}/proxy/")
    assert spec.runtime_api_url.startswith("http://127.0.0.1:")
    assert spec.storage.private_root == f"/mnt/sutra/state/agents/{agent.id}"
    assert spec.storage.hermes_home_path == f"/mnt/sutra/state/agents/{agent.id}/hermes-home"
    assert spec.storage.private_volume_path == f"/mnt/sutra/state/agents/{agent.id}/private-volume"
    assert spec.storage.shared_workspace_path is None
