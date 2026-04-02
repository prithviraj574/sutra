from __future__ import annotations

import json
import os
import signal
import subprocess
from pathlib import Path

import httpx
from fastapi import FastAPI, Header, HTTPException, Request, Response, status
from pydantic import BaseModel

from sutra_backend.config import Settings, get_settings
from sutra_backend.runtime.firecracker_host import (
    FirecrackerMicrovmSpec,
    FirecrackerStoragePaths,
    build_firecracker_config,
    build_firecracker_config_path,
)


class FirecrackerHostProvisionRequest(BaseModel):
    microvm_id: str
    agent_id: str
    team_id: str
    runtime_port: int
    proxy_base_url: str
    runtime_api_url: str
    storage: dict[str, str | None]
    honcho_config: dict[str, object] | None = None
    runtime_env: dict[str, str] | None = None


class FirecrackerHostRestartRequest(BaseModel):
    honcho_config: dict[str, object] | None = None
    runtime_env: dict[str, str] | None = None


class FirecrackerHostMicrovmRead(BaseModel):
    microvm_id: str
    state: str
    proxy_base_url: str
    runtime_api_url: str
    pid: int | None = None


def _state_root(settings: Settings) -> Path:
    return Path(settings.gcp_runtime_state_mount_path) / "microvms"


def _record_path(settings: Settings, microvm_id: str) -> Path:
    return _state_root(settings) / microvm_id / "record.json"


def _microvm_dir(settings: Settings, microvm_id: str) -> Path:
    return _state_root(settings) / microvm_id


def _config_path(settings: Settings, spec: FirecrackerMicrovmSpec) -> Path:
    return Path(build_firecracker_config_path(settings=settings, spec=spec))


def _api_socket_path(settings: Settings, microvm_id: str) -> Path:
    return _microvm_dir(settings, microvm_id) / "firecracker.sock"


def _read_record(settings: Settings, microvm_id: str) -> dict[str, object]:
    path = _record_path(settings, microvm_id)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="microVM not found.")
    return json.loads(path.read_text())


def _write_record(settings: Settings, microvm_id: str, payload: dict[str, object]) -> None:
    path = _record_path(settings, microvm_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True, indent=2))


def _runtime_api_key(settings: Settings) -> str:
    runtime_api_key = settings.runtime_api_key or settings.dev_runtime_api_key
    if not runtime_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Runtime API key is not configured on the host.",
        )
    return runtime_api_key


def _honcho_config_path(spec: FirecrackerMicrovmSpec) -> Path:
    return Path(spec.storage.hermes_home_path) / "honcho.json"


def _write_honcho_config(spec: FirecrackerMicrovmSpec, honcho_config: dict[str, object] | None) -> None:
    path = _honcho_config_path(spec)
    if honcho_config is None:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(honcho_config, sort_keys=True, indent=2))
    path.chmod(0o600)


def _authorize(settings: Settings, authorization: str | None) -> None:
    expected = f"Bearer {_runtime_api_key(settings)}"
    if authorization != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized.")


def _proxy_timeout_seconds(settings: Settings) -> float:
    # Give the host proxy a small cushion so the control plane timeout remains
    # the primary request deadline for long-running Hermes responses.
    return max(60.0, float(settings.hermes_api_route_timeout_seconds) + 5.0)


def _launch_process_microvm(
    settings: Settings,
    spec: FirecrackerMicrovmSpec,
    *,
    runtime_env: dict[str, str] | None = None,
) -> int:
    env = os.environ.copy()
    env.update(
        {
            "HERMES_HOME": spec.storage.hermes_home_path,
            "API_SERVER_ENABLED": "true",
            "API_SERVER_HOST": "127.0.0.1",
            "API_SERVER_PORT": str(spec.runtime_port),
            "API_SERVER_KEY": _runtime_api_key(settings),
        }
    )
    env.update(runtime_env or {})
    if spec.storage.shared_workspace_path:
        env["SUTRA_SHARED_WORKSPACE_PATH"] = spec.storage.shared_workspace_path
    command = settings.gcp_runtime_gateway_command
    process = subprocess.Popen(
        ["/bin/bash", "-lc", command],
        cwd=settings.gcp_runtime_hermes_workdir,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return process.pid


def _launch_firecracker_microvm(
    settings: Settings,
    spec: FirecrackerMicrovmSpec,
    *,
    config_path: Path,
) -> int:
    microvm_dir = _microvm_dir(settings, spec.microvm_id)
    microvm_dir.mkdir(parents=True, exist_ok=True)
    api_socket = _api_socket_path(settings, spec.microvm_id)
    if api_socket.exists():
        api_socket.unlink()
    stdout_path = microvm_dir / "firecracker.stdout.log"
    stderr_path = microvm_dir / "firecracker.stderr.log"
    with stdout_path.open("ab") as stdout_file, stderr_path.open("ab") as stderr_file:
        process = subprocess.Popen(
            [
                settings.gcp_runtime_firecracker_binary_path,
                "--api-sock",
                str(api_socket),
                "--config-file",
                str(config_path),
            ],
            stdout=stdout_file,
            stderr=stderr_file,
            start_new_session=True,
        )
    return process.pid


def _stop_process_microvm(pid: int | None) -> None:
    if pid is None:
        return
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        return


app = FastAPI(title="Sutra Firecracker Host")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "sutra-firecracker-host"}


@app.get("/microvms/{microvm_id}", response_model=FirecrackerHostMicrovmRead)
def get_microvm(
    microvm_id: str,
    authorization: str | None = Header(default=None),
) -> FirecrackerHostMicrovmRead:
    settings = get_settings()
    _authorize(settings, authorization)
    return FirecrackerHostMicrovmRead.model_validate(_read_record(settings, microvm_id))


@app.post("/microvms/provision", response_model=FirecrackerHostMicrovmRead)
def provision_microvm(
    payload: FirecrackerHostProvisionRequest,
    authorization: str | None = Header(default=None),
) -> FirecrackerHostMicrovmRead:
    settings = get_settings()
    _authorize(settings, authorization)

    spec = FirecrackerMicrovmSpec(
        microvm_id=payload.microvm_id,
        agent_id=payload.agent_id,
        team_id=payload.team_id,
        runtime_port=payload.runtime_port,
        proxy_base_url=payload.proxy_base_url,
        runtime_api_url=payload.runtime_api_url,
        storage=FirecrackerStoragePaths(
            private_root=str(payload.storage["private_root"]),
            hermes_home_path=str(payload.storage["hermes_home_path"]),
            private_volume_path=str(payload.storage["private_volume_path"]),
            shared_workspace_path=(
                str(payload.storage["shared_workspace_path"])
                if payload.storage.get("shared_workspace_path")
                else None
            ),
        ),
    )
    for path_value in (
        spec.storage.private_root,
        spec.storage.hermes_home_path,
        spec.storage.private_volume_path,
        spec.storage.shared_workspace_path,
    ):
        if not path_value:
            continue
        path = Path(path_value)
        path.mkdir(parents=True, exist_ok=True)
        if path_value != spec.storage.shared_workspace_path:
            path.chmod(0o700)

    config_path = _config_path(settings, spec)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(build_firecracker_config(settings=settings, spec=spec), indent=2))
    _write_honcho_config(spec, payload.honcho_config)

    pid: int | None = None
    launch_state = "configured"
    if settings.gcp_runtime_firecracker_execute:
        pid = _launch_firecracker_microvm(settings, spec, config_path=config_path)
        launch_state = "provisioning"
    else:
        pid = _launch_process_microvm(settings, spec, runtime_env=payload.runtime_env)
        launch_state = "running"

    record = {
        "microvm_id": spec.microvm_id,
        "agent_id": spec.agent_id,
        "team_id": spec.team_id,
        "state": launch_state,
        "proxy_base_url": spec.proxy_base_url,
        "runtime_api_url": spec.runtime_api_url,
        "storage": payload.storage,
        "honcho_config": payload.honcho_config,
        "runtime_env": payload.runtime_env,
        "config_path": str(config_path),
        "pid": pid,
    }
    _write_record(settings, spec.microvm_id, record)
    return FirecrackerHostMicrovmRead.model_validate(record)


@app.post("/microvms/{microvm_id}/restart", response_model=FirecrackerHostMicrovmRead)
def restart_microvm(
    microvm_id: str,
    authorization: str | None = Header(default=None),
    payload: FirecrackerHostRestartRequest | None = None,
) -> FirecrackerHostMicrovmRead:
    settings = get_settings()
    _authorize(settings, authorization)
    record = _read_record(settings, microvm_id)
    _stop_process_microvm(record.get("pid"))  # type: ignore[arg-type]
    runtime_api_url = str(record["runtime_api_url"])
    runtime_port = int(runtime_api_url.rstrip("/").rsplit(":", 1)[1])
    proxy_base_url = str(record["proxy_base_url"])
    spec = FirecrackerMicrovmSpec(
        microvm_id=microvm_id,
        agent_id=str(record.get("agent_id", "unknown")),
        team_id=str(record.get("team_id", "unknown")),
        runtime_port=runtime_port,
        proxy_base_url=proxy_base_url,
        runtime_api_url=runtime_api_url,
        storage=FirecrackerStoragePaths(
            private_root=str(record.get("storage", {}).get("private_root", "")),
            hermes_home_path=str(record.get("storage", {}).get("hermes_home_path", "")),
            private_volume_path=str(record.get("storage", {}).get("private_volume_path", "")),
            shared_workspace_path=(
                str(record.get("storage", {}).get("shared_workspace_path"))
                if record.get("storage", {}).get("shared_workspace_path")
                else None
            ),
        ),
    )
    honcho_config = payload.honcho_config if payload is not None else record.get("honcho_config")
    runtime_env = payload.runtime_env if payload is not None else record.get("runtime_env")
    _write_honcho_config(spec, honcho_config if isinstance(honcho_config, dict) else None)
    config_path = Path(str(record.get("config_path") or _config_path(settings, spec)))
    if settings.gcp_runtime_firecracker_execute:
        record["pid"] = _launch_firecracker_microvm(settings, spec, config_path=config_path)
        record["state"] = "provisioning"
    else:
        record["pid"] = _launch_process_microvm(
            settings,
            spec,
            runtime_env=runtime_env if isinstance(runtime_env, dict) else None,
        )
        record["state"] = "running"
    record["honcho_config"] = honcho_config if isinstance(honcho_config, dict) else None
    record["runtime_env"] = runtime_env if isinstance(runtime_env, dict) else None
    _write_record(settings, microvm_id, record)
    return FirecrackerHostMicrovmRead.model_validate(record)


@app.api_route("/microvms/{microvm_id}/proxy/{path:path}", methods=["GET", "POST"])
async def proxy_microvm(
    microvm_id: str,
    path: str,
    request: Request,
    authorization: str | None = Header(default=None),
) -> Response:
    settings = get_settings()
    _authorize(settings, authorization)
    record = _read_record(settings, microvm_id)
    target_base = str(record["runtime_api_url"]).rstrip("/")
    target_url = f"{target_base}/{path.lstrip('/')}"
    body = await request.body()
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in {"host", "content-length"}
    }
    async with httpx.AsyncClient(timeout=_proxy_timeout_seconds(settings)) as client:
        response = await client.request(
            request.method,
            target_url,
            content=body,
            headers=headers,
        )
    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=dict(response.headers),
        media_type=response.headers.get("content-type"),
    )
