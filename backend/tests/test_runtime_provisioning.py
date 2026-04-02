from __future__ import annotations

from uuid import uuid4

from sqlalchemy import inspect
from sqlmodel import Session, SQLModel, select

from sutra_backend.config import Settings
from sutra_backend.db import create_database_engine
from sutra_backend.models import Agent, AgentTeam, RoleTemplate, RuntimeLease, User
from sutra_backend.runtime.errors import RuntimeNotReadyError
from sutra_backend.runtime.honcho import (
    build_honcho_agent_peer_name,
    build_honcho_user_peer_name,
    build_honcho_workspace_id,
    build_runtime_honcho_config,
)
from sutra_backend.runtime.managed_env import build_managed_runtime_env
from sutra_backend.runtime.provisioning import (
    GcpFirecrackerRuntimeProvisioner,
    ServiceAccountFileGoogleAccessTokenProvider,
    ensure_agent_runtime_lease,
    restart_agent_runtime_lease,
)


def _gcp_disk(name: str):
    return type(
        "Disk",
        (),
        {
            "name": name,
            "status": "READY",
            "source_link": (
                "https://compute.googleapis.com/compute/v1/projects/"
                f"sutra-project/zones/us-central1-a/disks/{name}"
            ),
        },
    )()


def _gcp_instance(
    name: str,
    network_ip: str = "10.0.0.8",
    external_ip: str | None = None,
):
    return type(
        "Instance",
        (),
        {
            "name": name,
            "status": "RUNNING",
            "network_ip": network_ip,
            "external_ip": external_ip,
        },
    )()


def _patch_gcp_host_runtime(
    monkeypatch,
    *,
    provisioned_host_ip: str = "10.0.0.8",
    provisioned_microvm_state: str = "running",
) -> None:
    monkeypatch.setattr(
        "sutra_backend.runtime.provisioning.GcpFirecrackerHostClient.provision_microvm",
        lambda self, *, payload: type(
            "Microvm",
            (),
            {
                "microvm_id": str(payload["microvm_id"]),
                "state": provisioned_microvm_state,
                "proxy_base_url": (
                    f"http://{provisioned_host_ip}:8787/"
                    f"microvms/{payload['microvm_id']}/proxy/"
                ),
            },
        )(),
    )
    monkeypatch.setattr(
        "sutra_backend.runtime.provisioning.GcpFirecrackerRuntimeProvisioner._wait_for_host_api",
        lambda self, host_api_base_url: None,
    )


def _patch_gcp_host_runtime_restart(
    monkeypatch,
    *,
    restarted_host_ip: str = "10.0.0.12",
    restarted_microvm_state: str = "running",
) -> None:
    monkeypatch.setattr(
        "sutra_backend.runtime.provisioning.GcpFirecrackerRuntimeProvisioner._wait_for_host_api",
        lambda self, host_api_base_url: None,
    )
    monkeypatch.setattr(
        "sutra_backend.runtime.provisioning.GcpFirecrackerHostClient.restart_microvm_with_payload",
        lambda self, *, microvm_id, payload: type(
            "Microvm",
            (),
            {
                "microvm_id": microvm_id,
                "state": restarted_microvm_state,
                "proxy_base_url": (
                    f"http://{restarted_host_ip}:8787/"
                    f"microvms/{microvm_id}/proxy/"
                ),
            },
        )(),
    )


def test_runtime_provisioner_creates_local_dev_lease_when_missing() -> None:
    engine = create_database_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        user = User(firebase_uid="firebase-user-1", email="user@example.com")
        role_template = RoleTemplate(
            key="generalist",
            name="Generalist",
            default_system_prompt="Default agent.",
        )
        session.add(user)
        session.add(role_template)
        session.commit()
        session.refresh(user)
        session.refresh(role_template)

        team = AgentTeam(user_id=user.id, name="My Workspace", mode="personal")
        session.add(team)
        session.commit()
        session.refresh(team)

        agent = Agent(
            user_id=user.id,
            role_template_id=role_template.id,
            name="Default Agent",
            role_name="Generalist",
        )
        session.add(agent)
        session.commit()
        session.refresh(agent)

        lease = ensure_agent_runtime_lease(
            session,
            agent=agent,
            settings=Settings(
                app_env="test",
                database_url="sqlite://",
                runtime_provider="static_dev",
                dev_runtime_base_url="http://runtime.internal",
                dev_runtime_api_key="runtime-key",
            ),
        )

        assert lease.state == "running"
        assert lease.api_base_url == "http://runtime.internal"
        assert lease.vm_id.startswith("local-dev-")
        assert lease.started_at is not None
        assert lease.last_heartbeat_at is not None
        session.refresh(agent)
        assert agent.status == "ready"
        assert agent.hermes_home_uri == f"local://agents/{agent.id}/hermes-home"
        assert agent.private_volume_uri == f"local://agents/{agent.id}/private-volume"
        assert session.exec(select(RuntimeLease)).one().agent_id == agent.id


def test_runtime_provisioner_reuses_existing_lease() -> None:
    engine = create_database_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        user = User(firebase_uid="firebase-user-1", email="user@example.com")
        role_template = RoleTemplate(
            key="generalist",
            name="Generalist",
            default_system_prompt="Default agent.",
        )
        session.add(user)
        session.add(role_template)
        session.commit()
        session.refresh(user)
        session.refresh(role_template)

        team = AgentTeam(user_id=user.id, name="My Workspace", mode="personal")
        session.add(team)
        session.commit()
        session.refresh(team)

        agent = Agent(
            user_id=user.id,
            role_template_id=role_template.id,
            name="Default Agent",
            role_name="Generalist",
        )
        session.add(agent)
        session.commit()
        session.refresh(agent)

        existing_lease = RuntimeLease(
            agent_id=agent.id,
            vm_id=f"local-dev-{str(agent.id)[:8]}",
            state="running",
            api_base_url="http://existing-runtime.internal",
        )
        session.add(existing_lease)
        session.commit()

        lease = ensure_agent_runtime_lease(
            session,
            agent=agent,
            settings=Settings(
                app_env="test",
                database_url="sqlite://",
                runtime_provider="static_dev",
                dev_runtime_base_url="http://runtime.internal",
                dev_runtime_api_key="runtime-key",
            ),
        )

        assert lease.vm_id == existing_lease.vm_id
        assert lease.api_base_url == "http://runtime.internal"
        assert lease.started_at is not None
        assert lease.last_heartbeat_at is not None


def test_runtime_provisioner_replaces_existing_lease_when_provider_changes(monkeypatch) -> None:
    engine = create_database_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    monkeypatch.setattr(
        "sutra_backend.runtime.provisioning.GcpStorageClient.ensure_prefix",
        lambda self, *, bucket, prefix: None,
    )
    monkeypatch.setattr(
        "sutra_backend.runtime.provisioning.GcpComputeEngineClient.get_instance",
        lambda self, *, name: _gcp_instance(name, "10.0.0.8", "34.118.10.8"),
    )
    monkeypatch.setattr(
        "sutra_backend.runtime.provisioning.GcpComputeEngineClient.get_disk",
        lambda self, *, name: _gcp_disk(name),
    )
    monkeypatch.setattr(
        "sutra_backend.runtime.provisioning.GcpFirecrackerRuntimeProvisioner._wait_for_instance",
        lambda self, compute_client, *, name: _gcp_instance(name, "10.0.0.8", "34.118.10.8"),
    )
    _patch_gcp_host_runtime(monkeypatch, provisioned_host_ip="34.118.10.8")

    with Session(engine) as session:
        user = User(firebase_uid="firebase-user-1", email="user@example.com")
        role_template = RoleTemplate(
            key="generalist",
            name="Generalist",
            default_system_prompt="Default agent.",
        )
        session.add(user)
        session.add(role_template)
        session.commit()
        session.refresh(user)
        session.refresh(role_template)

        team = AgentTeam(user_id=user.id, name="My Workspace", mode="personal")
        session.add(team)
        session.commit()
        session.refresh(team)

        agent = Agent(
            user_id=user.id,
            role_template_id=role_template.id,
            name="Default Agent",
            role_name="Generalist",
        )
        session.add(agent)
        session.commit()
        session.refresh(agent)

        existing_lease = RuntimeLease(
            agent_id=agent.id,
            vm_id=f"local-dev-{str(agent.id)[:8]}",
            state="running",
            api_base_url="http://127.0.0.1:8642",
        )
        session.add(existing_lease)
        session.commit()

        lease = ensure_agent_runtime_lease(
            session,
            agent=agent,
            settings=Settings(
                app_env="test",
                database_url="sqlite://",
                runtime_provider="gcp_firecracker",
                dev_runtime_api_key="runtime-key",
                gcs_bucket_name="sutra-runtime",
                gcp_project_id="sutra-project",
                gcp_compute_zone="us-central1-a",
                gcp_runtime_source_image="sutra-runtime-image",
                gcp_runtime_source_image_project="sutra-images",
                gcp_runtime_access_token="token",
            ),
        )

        assert lease.vm_id.startswith("agent-")
        assert lease.vm_id != existing_lease.vm_id
        assert lease.api_base_url.endswith(f"/microvms/{lease.vm_id}/proxy/")
        assert session.exec(select(RuntimeLease)).one().id == lease.id


def test_runtime_provisioner_restarts_existing_local_dev_lease() -> None:
    engine = create_database_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        user = User(firebase_uid="firebase-user-1", email="user@example.com")
        role_template = RoleTemplate(
            key="generalist",
            name="Generalist",
            default_system_prompt="Default agent.",
        )
        session.add(user)
        session.add(role_template)
        session.commit()
        session.refresh(user)
        session.refresh(role_template)

        team = AgentTeam(user_id=user.id, name="My Workspace", mode="personal")
        session.add(team)
        session.commit()
        session.refresh(team)

        agent = Agent(
            user_id=user.id,
            role_template_id=role_template.id,
            name="Default Agent",
            role_name="Generalist",
        )
        session.add(agent)
        session.commit()
        session.refresh(agent)

        lease = RuntimeLease(
            agent_id=agent.id,
            vm_id="local-dev-agent",
            state="unreachable",
            api_base_url="http://old-runtime.internal",
        )
        session.add(lease)
        session.commit()
        session.refresh(lease)

        restarted = restart_agent_runtime_lease(
            session,
            agent=agent,
            settings=Settings(
                app_env="test",
                database_url="sqlite://",
                runtime_provider="static_dev",
                dev_runtime_base_url="http://runtime.internal",
                dev_runtime_api_key="runtime-key",
            ),
        )

        assert restarted.id == lease.id
        assert restarted.state == "running"
        assert restarted.api_base_url == "http://runtime.internal"
        assert restarted.started_at is not None
        assert restarted.last_heartbeat_at is not None
        session.refresh(agent)
        assert agent.status == "ready"
        assert agent.hermes_home_uri == f"local://agents/{agent.id}/hermes-home"
        assert agent.private_volume_uri == f"local://agents/{agent.id}/private-volume"


def test_runtime_provisioner_can_surface_unconfigured_gcp_provider() -> None:
    engine = create_database_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        user = User(firebase_uid="firebase-user-1", email="user@example.com")
        role_template = RoleTemplate(
            key="generalist",
            name="Generalist",
            default_system_prompt="Default agent.",
        )
        session.add(user)
        session.add(role_template)
        session.commit()
        session.refresh(user)
        session.refresh(role_template)

        team = AgentTeam(user_id=user.id, name="My Workspace", mode="personal")
        session.add(team)
        session.commit()
        session.refresh(team)

        agent = Agent(
            user_id=user.id,
            role_template_id=role_template.id,
            name="Default Agent",
            role_name="Generalist",
        )
        session.add(agent)
        session.commit()
        session.refresh(agent)

        try:
            ensure_agent_runtime_lease(
                session,
                agent=agent,
                settings=Settings(
                    app_env="test",
                    database_url="sqlite://",
                    runtime_provider="gcp_firecracker",
                ),
            )
        except RuntimeNotReadyError as exc:
            assert "not configured" in str(exc)
        else:
            raise AssertionError("Expected a runtime provisioning error.")


def test_gcp_runtime_provisioner_prefers_service_account_file_when_configured() -> None:
    provisioner = GcpFirecrackerRuntimeProvisioner(
        Settings(
            app_env="test",
            database_url="sqlite://",
            runtime_provider="gcp_firecracker",
            gcp_service_account_json="gcs-service-account.json",
        )
    )

    token_provider = provisioner._build_token_provider()

    assert isinstance(token_provider, ServiceAccountFileGoogleAccessTokenProvider)
    assert token_provider.service_account_json == "gcs-service-account.json"


def test_runtime_provisioner_creates_gcp_firecracker_lease_and_agent_storage(
    monkeypatch,
) -> None:
    engine = create_database_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    created_prefixes: list[tuple[str, str]] = []
    created_instance_bodies: list[dict[str, object]] = []
    created_disks: list[tuple[str, int, str]] = []

    def fake_ensure_prefix(self, *, bucket: str, prefix: str) -> None:
        created_prefixes.append((bucket, prefix))

    def fake_get_instance(self, *, name: str):
        return None

    def fake_create_instance(self, *, body: dict[str, object]) -> None:
        created_instance_bodies.append(body)

    def fake_get_disk(self, *, name: str):
        return None

    def fake_create_disk(self, *, name: str, size_gb: int, disk_type: str) -> None:
        created_disks.append((name, size_gb, disk_type))

    monkeypatch.setattr(
        "sutra_backend.runtime.provisioning.GcpStorageClient.ensure_prefix",
        fake_ensure_prefix,
    )
    monkeypatch.setattr(
        "sutra_backend.runtime.provisioning.GcpComputeEngineClient.get_instance",
        fake_get_instance,
    )
    monkeypatch.setattr(
        "sutra_backend.runtime.provisioning.GcpComputeEngineClient.get_disk",
        fake_get_disk,
    )
    monkeypatch.setattr(
        "sutra_backend.runtime.provisioning.GcpComputeEngineClient.create_disk",
        fake_create_disk,
    )
    monkeypatch.setattr(
        "sutra_backend.runtime.provisioning.GcpComputeEngineClient.create_instance",
        fake_create_instance,
    )
    monkeypatch.setattr(
        "sutra_backend.runtime.provisioning.GcpFirecrackerRuntimeProvisioner._wait_for_disk",
        lambda self, compute_client, *, name: _gcp_disk(name),
    )
    monkeypatch.setattr(
        "sutra_backend.runtime.provisioning.GcpFirecrackerRuntimeProvisioner._wait_for_instance",
        lambda self, compute_client, *, name: _gcp_instance(
            name,
            "10.0.0.8",
            "34.118.10.8",
        ),
    )
    _patch_gcp_host_runtime(monkeypatch, provisioned_host_ip="34.118.10.8")

    with Session(engine) as session:
        user = User(firebase_uid="firebase-user-1", email="user@example.com")
        role_template = RoleTemplate(
            key="generalist",
            name="Generalist",
            default_system_prompt="Default agent.",
        )
        session.add(user)
        session.add(role_template)
        session.commit()
        session.refresh(user)
        session.refresh(role_template)

        team = AgentTeam(
            user_id=user.id,
            name="My Workspace",
            mode="personal",
            shared_workspace_uri=f"gs://sutra-runtime/teams/{user.id}/workspace",
        )
        session.add(team)
        session.commit()
        session.refresh(team)

        agent = Agent(
            user_id=user.id,
            role_template_id=role_template.id,
            name="Default Agent",
            role_name="Generalist",
        )
        session.add(agent)
        session.commit()
        session.refresh(agent)

        lease = ensure_agent_runtime_lease(
            session,
            agent=agent,
            settings=Settings(
                app_env="test",
                database_url="sqlite://",
                runtime_provider="gcp_firecracker",
                dev_runtime_api_key="runtime-key",
                gcs_bucket_name="sutra-runtime",
                gcp_project_id="sutra-project",
                gcp_compute_zone="us-central1-a",
                gcp_runtime_source_image="sutra-runtime-image",
                gcp_runtime_source_image_project="sutra-images",
                gcp_runtime_access_token="token",
                honcho_api_key="honcho-key",
            ),
        )

        session.refresh(agent)

        assert lease.state == "running"
        assert lease.api_base_url == f"http://34.118.10.8:8787/microvms/agent-{str(agent.id).replace('-', '')[:20]}/proxy/"
        assert lease.vm_id == f"agent-{str(agent.id).replace('-', '')[:20]}"
        assert lease.host_vm_id == "sutra-firecracker-host"
        assert lease.host_api_base_url == "http://34.118.10.8:8787"
        assert lease.started_at is not None
        assert lease.last_heartbeat_at is not None
        assert agent.status == "ready"
        assert agent.hermes_home_uri == f"gs://sutra-runtime/agents/{agent.id}/hermes-home"
        assert agent.private_volume_uri == f"gs://sutra-runtime/agents/{agent.id}/private-volume"
        assert created_prefixes == [
            ("sutra-runtime", f"agents/{agent.id}/hermes-home"),
            ("sutra-runtime", f"agents/{agent.id}/private-volume"),
        ]
        assert created_disks == [("sutra-firecracker-host-data", 50, "pd-balanced")]
        assert len(created_instance_bodies) == 1
        disks = created_instance_bodies[0]["disks"]
        assert len(disks) == 2
        assert disks[1]["autoDelete"] is False
        assert disks[1]["deviceName"] == "sutra-host-data"
        metadata_items = created_instance_bodies[0]["metadata"]["items"]
        assert {"key": "sutra-runtime-provider", "value": "gcp_firecracker"} in metadata_items
        assert {"key": "sutra-runtime-api-key", "value": "runtime-key"} in metadata_items
        assert {
            "key": "sutra-state-disk-name",
            "value": "sutra-firecracker-host-data",
        } in metadata_items
        assert {"key": "sutra-host-api-port", "value": "8787"} in metadata_items
        assert {"key": "sutra-runtime-host-api-bind-host", "value": "0.0.0.0"} in metadata_items
        assert {"key": "sutra-agent-root-path", "value": "/mnt/sutra/state/agents"} in metadata_items
        assert {
            "key": "sutra-shared-workspace-root-path",
            "value": "/mnt/sutra/shared-workspaces",
        } in metadata_items
        assert {"key": "sutra-runtime-hermes-workdir", "value": "/opt/hermes-agent"} in metadata_items
        startup_script_entry = next(
            item for item in metadata_items if item["key"] == "startup-script"
        )
        assert "mkfs.ext4 -F" in startup_script_entry["value"]
        assert "/mnt/sutra/state/agents" in startup_script_entry["value"]
        assert "/mnt/sutra/state/microvms" in startup_script_entry["value"]
        assert "/mnt/sutra/shared-workspaces" in startup_script_entry["value"]
        assert "GCP_RUNTIME_HOST_API_PORT=8787" in startup_script_entry["value"]
        assert "GCP_RUNTIME_FIRECRACKER_EXECUTE=false" in startup_script_entry["value"]
        assert "uvicorn sutra_backend.runtime.firecracker_host_service:app" in startup_script_entry["value"]
        assert "systemctl restart sutra-firecracker-host.service" in startup_script_entry["value"]
        assert "runuser -u sutra-runtime --preserve-environment" in startup_script_entry["value"]
        assert "test ! -L /mnt/sutra/state/agents" in startup_script_entry["value"]
        assert "test ! -L /mnt/sutra/shared-workspaces" in startup_script_entry["value"]
        assert ".hermes/.env" not in startup_script_entry["value"]


def test_runtime_provisioner_builds_per_user_honcho_config_for_microvm(
    monkeypatch,
) -> None:
    engine = create_database_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    captured_payloads: list[dict[str, object]] = []

    monkeypatch.setattr(
        "sutra_backend.runtime.provisioning.GcpStorageClient.ensure_prefix",
        lambda self, *, bucket, prefix: None,
    )
    monkeypatch.setattr(
        "sutra_backend.runtime.provisioning.GcpComputeEngineClient.get_instance",
        lambda self, *, name: None,
    )
    monkeypatch.setattr(
        "sutra_backend.runtime.provisioning.GcpComputeEngineClient.get_disk",
        lambda self, *, name: None,
    )
    monkeypatch.setattr(
        "sutra_backend.runtime.provisioning.GcpComputeEngineClient.create_disk",
        lambda self, *, name, size_gb, disk_type: None,
    )
    monkeypatch.setattr(
        "sutra_backend.runtime.provisioning.GcpComputeEngineClient.create_instance",
        lambda self, *, body: None,
    )
    monkeypatch.setattr(
        "sutra_backend.runtime.provisioning.GcpFirecrackerRuntimeProvisioner._wait_for_disk",
        lambda self, compute_client, *, name: _gcp_disk(name),
    )
    monkeypatch.setattr(
        "sutra_backend.runtime.provisioning.GcpFirecrackerRuntimeProvisioner._wait_for_instance",
        lambda self, compute_client, *, name: _gcp_instance(name, "10.0.0.9", "34.118.10.9"),
    )
    monkeypatch.setattr(
        "sutra_backend.runtime.provisioning.GcpFirecrackerRuntimeProvisioner._wait_for_host_api",
        lambda self, host_api_base_url: None,
    )
    monkeypatch.setattr(
        "sutra_backend.runtime.provisioning.GcpFirecrackerHostClient.provision_microvm",
        lambda self, *, payload: (
            captured_payloads.append(payload),
            type(
                "Microvm",
                (),
                {
                    "microvm_id": str(payload["microvm_id"]),
                    "state": "running",
                    "proxy_base_url": (
                        f"http://34.118.10.9:8787/microvms/{payload['microvm_id']}/proxy/"
                    ),
                },
            )(),
        )[1],
    )

    with Session(engine) as session:
        user = User(firebase_uid="firebase-user-9", email="honcho@example.com")
        role_template = RoleTemplate(
            key="generalist",
            name="Generalist",
            default_system_prompt="Default agent.",
        )
        session.add(user)
        session.add(role_template)
        session.commit()
        session.refresh(user)
        session.refresh(role_template)

        team = AgentTeam(user_id=user.id, name="My Workspace", mode="personal")
        session.add(team)
        session.commit()
        session.refresh(team)

        agent = Agent(
            user_id=user.id,
            role_template_id=role_template.id,
            name="Default Agent",
            role_name="Generalist",
        )
        session.add(agent)
        session.commit()
        session.refresh(agent)

        settings = Settings(
            app_env="test",
            database_url="sqlite://",
            runtime_provider="gcp_firecracker",
            dev_runtime_api_key="runtime-key",
            gcs_bucket_name="sutra-runtime",
            gcp_project_id="sutra-project",
            gcp_compute_zone="us-central1-a",
            gcp_runtime_source_image="sutra-runtime-image",
            gcp_runtime_source_image_project="sutra-images",
            gcp_runtime_access_token="token",
            honcho_api_key="honcho-key",
            minimax_api_key="minimax-key",
        )

        ensure_agent_runtime_lease(
            session,
            agent=agent,
            settings=settings,
        )

        assert len(captured_payloads) == 1
        honcho_config = captured_payloads[0]["honcho_config"]
        assert isinstance(honcho_config, dict)
        assert honcho_config["apiKey"] == "honcho-key"
        assert honcho_config["sessionStrategy"] == "per-session"
        assert captured_payloads[0]["runtime_env"] == {"MINIMAX_API_KEY": "minimax-key"}
        hermes_host = honcho_config["hosts"]["hermes"]
        assert hermes_host["workspace"] == build_honcho_workspace_id(user_id=user.id, settings=settings)
        assert hermes_host["peerName"] == build_honcho_user_peer_name(user_id=user.id)
        assert hermes_host["aiPeer"] == build_honcho_agent_peer_name(agent_id=agent.id)


def test_build_runtime_honcho_config_reads_api_key_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("HONCHO_API_KEY", "env-honcho-key")

    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        runtime_provider="gcp_firecracker",
        gcs_bucket_name="sutra-runtime",
        gcp_project_id="sutra-project",
        gcp_compute_zone="us-central1-a",
        gcp_runtime_source_image="sutra-runtime-image",
        gcp_runtime_source_image_project="sutra-images",
        gcp_runtime_access_token="token",
    )

    config = build_runtime_honcho_config(
        settings=settings,
        user_id=uuid4(),
        agent_id=uuid4(),
    )

    assert config is not None
    assert config["apiKey"] == "env-honcho-key"


def test_build_managed_runtime_env_reads_managed_provider_keys() -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        minimax_api_key="minimax-key",
        firecrawl_api_key="firecrawl-key",
        browserbase_api_key="browserbase-key",
        browserbase_project_id="browserbase-project",
    )

    assert build_managed_runtime_env(settings) == {
        "MINIMAX_API_KEY": "minimax-key",
        "FIRECRAWL_API_KEY": "firecrawl-key",
        "BROWSERBASE_API_KEY": "browserbase-key",
        "BROWSERBASE_PROJECT_ID": "browserbase-project",
    }


def test_runtime_provisioner_supports_image_family_and_runtime_bundle(monkeypatch) -> None:
    engine = create_database_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    created_instance_bodies: list[dict[str, object]] = []

    monkeypatch.setattr(
        "sutra_backend.runtime.provisioning.GcpStorageClient.ensure_prefix",
        lambda self, *, bucket, prefix: None,
    )
    monkeypatch.setattr(
        "sutra_backend.runtime.provisioning.GcpComputeEngineClient.get_instance",
        lambda self, *, name: None,
    )
    monkeypatch.setattr(
        "sutra_backend.runtime.provisioning.GcpComputeEngineClient.get_disk",
        lambda self, *, name: None,
    )
    monkeypatch.setattr(
        "sutra_backend.runtime.provisioning.GcpComputeEngineClient.create_disk",
        lambda self, *, name, size_gb, disk_type: None,
    )
    monkeypatch.setattr(
        "sutra_backend.runtime.provisioning.GcpComputeEngineClient.create_instance",
        lambda self, *, body: created_instance_bodies.append(body),
    )
    monkeypatch.setattr(
        "sutra_backend.runtime.provisioning.GcpFirecrackerRuntimeProvisioner._wait_for_disk",
        lambda self, compute_client, *, name: _gcp_disk(name),
    )
    monkeypatch.setattr(
        "sutra_backend.runtime.provisioning.GcpFirecrackerRuntimeProvisioner._wait_for_instance",
        lambda self, compute_client, *, name: _gcp_instance(name, "10.0.0.9", "34.118.10.9"),
    )
    _patch_gcp_host_runtime(monkeypatch, provisioned_host_ip="34.118.10.9")

    with Session(engine) as session:
        user = User(firebase_uid="firebase-user-2", email="bundle@example.com")
        role_template = RoleTemplate(
            key="researcher",
            name="Researcher",
            default_system_prompt="Research.",
        )
        session.add(user)
        session.add(role_template)
        session.commit()
        session.refresh(user)
        session.refresh(role_template)

        team = AgentTeam(user_id=user.id, name="Runtime Team", mode="personal")
        session.add(team)
        session.commit()
        session.refresh(team)

        agent = Agent(
            user_id=user.id,
            role_template_id=role_template.id,
            name="Runtime Agent",
            role_name="Researcher",
        )
        session.add(agent)
        session.commit()
        session.refresh(agent)

        ensure_agent_runtime_lease(
            session,
            agent=agent,
            settings=Settings(
                app_env="test",
                database_url="sqlite://",
                runtime_provider="gcp_firecracker",
                dev_runtime_api_key="runtime-key",
                gcs_bucket_name="sutra-runtime",
                gcp_project_id="sutra-project",
                gcp_compute_zone="us-central1-a",
                gcp_runtime_source_image_family="debian-12",
                gcp_runtime_source_image_project="debian-cloud",
                gcp_runtime_access_token="token",
                gcp_runtime_hermes_bundle_uri="gs://sutra-runtime/runtime-bundles/hermes-agent-dev.tar.gz",
            ),
        )

    assert len(created_instance_bodies) == 1
    init_params = created_instance_bodies[0]["disks"][0]["initializeParams"]
    assert init_params["sourceImageFamily"] == "debian-12"
    assert init_params["sourceImageProject"] == "debian-cloud"
    metadata_items = created_instance_bodies[0]["metadata"]["items"]
    assert {
        "key": "sutra-runtime-hermes-bundle-uri",
        "value": "gs://sutra-runtime/runtime-bundles/hermes-agent-dev.tar.gz",
    } in metadata_items
    startup_script_entry = next(
        item for item in metadata_items if item["key"] == "startup-script"
    )
    assert "apt-get install -y python3 python3-venv python3-pip curl ca-certificates tar" in startup_script_entry["value"]
    assert "sutra-hermes-bundle.tar.gz" in startup_script_entry["value"]
    assert "sutra-backend-runtime.tar.gz" in startup_script_entry["value"]
    assert "/opt/sutra-runtime-venv/bin/pip install -r requirements.txt fastapi pydantic-settings uvicorn sqlmodel 'honcho-ai>=2.0.1,<3' 'anthropic>=0.39.0'" in startup_script_entry["value"]
    assert "PYTHONPATH=/opt/sutra-backend:/opt/hermes-agent" in startup_script_entry["value"]
    assert "GCP_RUNTIME_GATEWAY_COMMAND='/opt/sutra-runtime-venv/bin/python -m gateway.run'" in startup_script_entry["value"]
    assert "uvicorn sutra_backend.runtime.firecracker_host_service:app" in startup_script_entry["value"]


def test_runtime_provisioner_restarts_gcp_microvm_without_changing_private_storage(
    monkeypatch,
) -> None:
    engine = create_database_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    monkeypatch.setattr(
        "sutra_backend.runtime.provisioning.GcpComputeEngineClient.get_instance",
        lambda self, *, name: _gcp_instance(name, "10.0.0.11", "34.118.10.11"),
    )
    monkeypatch.setattr(
        "sutra_backend.runtime.provisioning.GcpComputeEngineClient.get_disk",
        lambda self, *, name: _gcp_disk(name),
    )
    monkeypatch.setattr(
        "sutra_backend.runtime.provisioning.GcpFirecrackerRuntimeProvisioner._wait_for_instance",
        lambda self, compute_client, *, name: _gcp_instance(name, "10.0.0.12", "34.118.10.12"),
    )
    _patch_gcp_host_runtime_restart(monkeypatch, restarted_host_ip="34.118.10.12")

    with Session(engine) as session:
        user = User(firebase_uid="firebase-user-3", email="restart@example.com")
        role_template = RoleTemplate(
            key="executor",
            name="Executor",
            default_system_prompt="Execute.",
        )
        session.add(user)
        session.add(role_template)
        session.commit()
        session.refresh(user)
        session.refresh(role_template)

        team = AgentTeam(
            user_id=user.id,
            name="Restart Team",
            mode="personal",
            shared_workspace_uri=f"gs://sutra-runtime/teams/{user.id}/workspace",
        )
        session.add(team)
        session.commit()
        session.refresh(team)

        agent = Agent(
            user_id=user.id,
            role_template_id=role_template.id,
            name="Restart Agent",
            role_name="Executor",
        )
        session.add(agent)
        session.commit()
        session.refresh(agent)

        lease = RuntimeLease(
            agent_id=agent.id,
            vm_id=f"agent-{str(agent.id).replace('-', '')[:20]}",
            host_vm_id="sutra-firecracker-host",
            host_api_base_url="http://34.118.10.11:8787",
            state="unreachable",
            api_base_url=(
                f"http://34.118.10.11:8787/microvms/agent-{str(agent.id).replace('-', '')[:20]}/proxy/"
            ),
        )
        session.add(lease)
        session.commit()
        session.refresh(lease)

        restarted = restart_agent_runtime_lease(
            session,
            agent=agent,
            settings=Settings(
                app_env="test",
                database_url="sqlite://",
                runtime_provider="gcp_firecracker",
                dev_runtime_api_key="runtime-key",
                gcs_bucket_name="sutra-runtime",
                gcp_project_id="sutra-project",
                gcp_compute_zone="us-central1-a",
                gcp_runtime_source_image="sutra-runtime-image",
                gcp_runtime_source_image_project="sutra-images",
                gcp_runtime_access_token="token",
            ),
        )

        assert restarted.id == lease.id
        assert restarted.state == "running"
        assert restarted.host_vm_id == "sutra-firecracker-host"
        assert restarted.host_api_base_url == "http://34.118.10.11:8787"
        assert restarted.api_base_url == (
            f"http://34.118.10.12:8787/microvms/agent-{str(agent.id).replace('-', '')[:20]}/proxy/"
        )
        session.refresh(agent)
        assert agent.hermes_home_uri == f"gs://sutra-runtime/agents/{agent.id}/hermes-home"
        assert agent.private_volume_uri == f"gs://sutra-runtime/agents/{agent.id}/private-volume"


def test_runtime_provisioner_does_not_attach_a_default_shared_workspace_path() -> None:
    provisioner = GcpFirecrackerRuntimeProvisioner(
        Settings(
            app_env="test",
            database_url="sqlite://",
            runtime_provider="gcp_firecracker",
            gcs_bucket_name="sutra-runtime",
            gcp_project_id="sutra-project",
            gcp_compute_zone="us-central1-a",
            gcp_runtime_source_image_project="sutra-images",
            gcp_runtime_source_image="sutra-runtime-image",
            dev_runtime_api_key="runtime-key",
            gcp_runtime_state_mount_path="/mnt/sutra/state",
            gcp_runtime_agent_root_path="/mnt/sutra/state/agents",
            gcp_runtime_shared_workspace_root_path="/mnt/sutra/state/shared",
        )
    )

    agent = Agent(user_id=uuid4(), name="Agent", role_name="Role")
    storage_spec = provisioner._build_storage_spec(agent)
    assert storage_spec.shared_workspace_path is None


def test_runtime_provisioner_prefers_host_api_override_base_url() -> None:
    provisioner = GcpFirecrackerRuntimeProvisioner(
        Settings(
            app_env="test",
            database_url="sqlite://",
            runtime_provider="gcp_firecracker",
            gcp_runtime_host_api_override_base_url="http://127.0.0.1:8787/",
        )
    )

    base_url = provisioner._build_host_api_base_url(
        _gcp_instance("sutra-firecracker-host", "10.0.0.8", "34.118.10.8")
    )

    assert base_url == "http://127.0.0.1:8787"


def test_runtime_lease_table_has_agent_state_composite_index() -> None:
    engine = create_database_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    indexes = inspect(engine).get_indexes("runtime_leases")

    assert any(
        index["name"] == "ix_runtime_leases_agent_id_state"
        and index["column_names"] == ["agent_id", "state"]
        for index in indexes
    )
