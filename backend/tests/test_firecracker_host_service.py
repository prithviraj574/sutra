from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from sutra_backend.config import Settings
from sutra_backend.models import Agent
from sutra_backend.runtime.firecracker_host import build_firecracker_microvm_spec
from sutra_backend.runtime.firecracker_host_service import app


def _settings(tmp_path: Path, *, firecracker_execute: bool = False) -> Settings:
    state_mount = tmp_path / "state"
    shared_root = tmp_path / "shared-workspaces"
    hermes_workdir = tmp_path / "hermes"
    hermes_workdir.mkdir(parents=True, exist_ok=True)
    return Settings(
        app_env="test",
        database_url="sqlite://",
        runtime_api_key="runtime-key",
        gcp_runtime_state_mount_path=str(state_mount),
        gcp_runtime_agent_root_path=str(state_mount / "agents"),
        gcp_runtime_shared_workspace_root_path=str(shared_root),
        gcp_runtime_hermes_workdir=str(hermes_workdir),
        gcp_runtime_firecracker_execute=firecracker_execute,
        gcp_runtime_firecracker_binary_path="/usr/local/bin/firecracker",
    )


def _provision_payload(settings: Settings) -> dict[str, object]:
    agent = Agent(user_id=uuid4(), name="Host Agent", role_name="Operator")
    spec = build_firecracker_microvm_spec(
        settings=settings,
        agent=agent,
        host_api_base_url="http://10.0.0.8:8787",
    )
    return {
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
        "honcho_config": {
            "enabled": True,
            "apiKey": "honcho-key",
            "sessionStrategy": "per-session",
            "hosts": {
                "hermes": {
                    "workspace": "sutra:prod:user:00000000-0000-0000-0000-000000000123",
                    "peerName": "user-00000000-0000-0000-0000-000000000123",
                    "aiPeer": f"agent-{spec.agent_id}",
                    "memoryMode": "hybrid",
                    "sessionStrategy": "per-session",
                    "saveMessages": True,
                }
            },
        },
        "runtime_env": {
            "MINIMAX_API_KEY": "managed-minimax-key",
            "FIRECRAWL_API_KEY": "managed-firecrawl-key",
        },
    }


def test_firecracker_host_service_provisions_process_microvm_and_writes_record(
    monkeypatch,
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    payload = _provision_payload(settings)

    monkeypatch.setattr(
        "sutra_backend.runtime.firecracker_host_service.get_settings",
        lambda: settings,
    )
    monkeypatch.setattr(
        "sutra_backend.runtime.firecracker_host_service._launch_process_microvm",
        lambda settings, spec, *, runtime_env=None: 4242,
    )

    client = TestClient(app)
    response = client.post(
        "/microvms/provision",
        headers={"Authorization": "Bearer runtime-key"},
        json=payload,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["microvm_id"] == payload["microvm_id"]
    assert body["state"] == "running"
    assert body["pid"] == 4242

    record_path = (
        Path(settings.gcp_runtime_state_mount_path)
        / "microvms"
        / str(payload["microvm_id"])
        / "record.json"
    )
    assert record_path.exists()
    record = json.loads(record_path.read_text())
    assert record["agent_id"] == payload["agent_id"]
    assert record["team_id"] == payload["team_id"]
    assert record["runtime_env"] == payload["runtime_env"]
    assert record["config_path"].endswith("firecracker-config.json")

    config_path = Path(str(record["config_path"]))
    assert config_path.exists()
    honcho_config_path = Path(str(payload["storage"]["hermes_home_path"])) / "honcho.json"
    assert honcho_config_path.exists()
    assert json.loads(honcho_config_path.read_text()) == payload["honcho_config"]

    for key in ("private_root", "hermes_home_path", "private_volume_path"):
        mode = Path(str(payload["storage"][key])).stat().st_mode & 0o777
        assert mode == 0o700
    assert payload["storage"]["shared_workspace_path"] is None


def test_firecracker_host_service_restart_preserves_microvm_identity(
    monkeypatch,
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    payload = _provision_payload(settings)
    stopped_pids: list[int | None] = []

    monkeypatch.setattr(
        "sutra_backend.runtime.firecracker_host_service.get_settings",
        lambda: settings,
    )
    monkeypatch.setattr(
        "sutra_backend.runtime.firecracker_host_service._launch_process_microvm",
        lambda settings, spec, *, runtime_env=None: 5151,
    )
    monkeypatch.setattr(
        "sutra_backend.runtime.firecracker_host_service._stop_process_microvm",
        lambda pid: stopped_pids.append(pid),
    )

    client = TestClient(app)
    provision_response = client.post(
        "/microvms/provision",
        headers={"Authorization": "Bearer runtime-key"},
        json=payload,
    )
    assert provision_response.status_code == 200

    restart_response = client.post(
        f"/microvms/{payload['microvm_id']}/restart",
        headers={"Authorization": "Bearer runtime-key"},
        json={
            "honcho_config": {
                "enabled": True,
                "apiKey": "updated-key",
                "hosts": {
                    "hermes": {
                        "workspace": "sutra:prod:user:override",
                        "peerName": "user-override",
                        "aiPeer": "agent-override",
                    }
                },
            }
        },
    )

    assert restart_response.status_code == 200
    body = restart_response.json()
    assert body["microvm_id"] == payload["microvm_id"]
    assert body["state"] == "running"
    assert body["pid"] == 5151
    assert stopped_pids == [5151]
    honcho_config_path = Path(str(payload["storage"]["hermes_home_path"])) / "honcho.json"
    assert json.loads(honcho_config_path.read_text())["apiKey"] == "updated-key"

    get_response = client.get(
        f"/microvms/{payload['microvm_id']}",
        headers={"Authorization": "Bearer runtime-key"},
    )
    assert get_response.status_code == 200
    assert get_response.json()["microvm_id"] == payload["microvm_id"]


def test_firecracker_host_service_uses_firecracker_launcher_when_enabled(
    monkeypatch,
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path, firecracker_execute=True)
    payload = _provision_payload(settings)

    monkeypatch.setattr(
        "sutra_backend.runtime.firecracker_host_service.get_settings",
        lambda: settings,
    )
    monkeypatch.setattr(
        "sutra_backend.runtime.firecracker_host_service._launch_firecracker_microvm",
        lambda settings, spec, *, config_path: 6262,
    )

    client = TestClient(app)
    response = client.post(
        "/microvms/provision",
        headers={"Authorization": "Bearer runtime-key"},
        json=payload,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "provisioning"
    assert body["pid"] == 6262


def test_firecracker_host_service_launches_runtime_with_managed_env(
    monkeypatch,
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    payload = _provision_payload(settings)
    captured_env: dict[str, str] = {}

    def _fake_popen(*args, **kwargs):
        nonlocal captured_env
        captured_env = dict(kwargs["env"])

        class _Process:
            pid = 7373

        return _Process()

    monkeypatch.setattr(
        "sutra_backend.runtime.firecracker_host_service.get_settings",
        lambda: settings,
    )
    monkeypatch.setattr(
        "sutra_backend.runtime.firecracker_host_service.subprocess.Popen",
        _fake_popen,
    )

    client = TestClient(app)
    response = client.post(
        "/microvms/provision",
        headers={"Authorization": "Bearer runtime-key"},
        json=payload,
    )

    assert response.status_code == 200
    assert captured_env["MINIMAX_API_KEY"] == "managed-minimax-key"
    assert captured_env["FIRECRAWL_API_KEY"] == "managed-firecrawl-key"
    assert captured_env["API_SERVER_KEY"] == "runtime-key"


def test_firecracker_host_proxy_uses_runtime_timeout_budget(
    monkeypatch,
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    settings.hermes_api_route_timeout_seconds = 180
    payload = _provision_payload(settings)
    observed: dict[str, object] = {}

    class _FakeResponse:
        def __init__(self) -> None:
            self.content = b'{"ok":true}'
            self.status_code = 200
            self.headers = {"content-type": "application/json"}

    class _FakeAsyncClient:
        def __init__(self, *, timeout: float) -> None:
            observed["timeout"] = timeout

        async def __aenter__(self) -> "_FakeAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def request(self, method: str, url: str, *, content: bytes, headers: dict[str, str]) -> _FakeResponse:
            observed["method"] = method
            observed["url"] = url
            observed["content"] = content
            observed["authorization"] = headers.get("authorization")
            return _FakeResponse()

    monkeypatch.setattr(
        "sutra_backend.runtime.firecracker_host_service.get_settings",
        lambda: settings,
    )
    monkeypatch.setattr(
        "sutra_backend.runtime.firecracker_host_service._launch_process_microvm",
        lambda settings, spec, *, runtime_env=None: 7373,
    )
    monkeypatch.setattr(
        "sutra_backend.runtime.firecracker_host_service.httpx.AsyncClient",
        _FakeAsyncClient,
    )

    client = TestClient(app)
    provision_response = client.post(
        "/microvms/provision",
        headers={"Authorization": "Bearer runtime-key"},
        json=payload,
    )
    assert provision_response.status_code == 200

    proxy_response = client.post(
        f"/microvms/{payload['microvm_id']}/proxy/v1/responses",
        headers={"Authorization": "Bearer runtime-key", "Content-Type": "application/json"},
        json={"input": "Say exactly ok"},
    )

    assert proxy_response.status_code == 200
    assert proxy_response.json() == {"ok": True}
    assert observed["timeout"] == 185.0
    assert observed["method"] == "POST"
    assert observed["url"] == str(payload["runtime_api_url"]).rstrip("/") + "/v1/responses"
    assert observed["authorization"] == "Bearer runtime-key"
