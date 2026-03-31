from __future__ import annotations

from sqlalchemy import inspect
from sqlmodel import Session, SQLModel, select

from sutra_backend.config import Settings
from sutra_backend.db import create_database_engine
from sutra_backend.models import Agent, RoleTemplate, RuntimeLease, Team, User
from sutra_backend.runtime.errors import RuntimeNotReadyError
from sutra_backend.runtime.provisioning import (
    GcpFirecrackerRuntimeProvisioner,
    ServiceAccountFileGoogleAccessTokenProvider,
    ensure_agent_runtime_lease,
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

        team = Team(user_id=user.id, name="My Workspace", mode="personal")
        session.add(team)
        session.commit()
        session.refresh(team)

        agent = Agent(
            team_id=team.id,
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

        team = Team(user_id=user.id, name="My Workspace", mode="personal")
        session.add(team)
        session.commit()
        session.refresh(team)

        agent = Agent(
            team_id=team.id,
            role_template_id=role_template.id,
            name="Default Agent",
            role_name="Generalist",
        )
        session.add(agent)
        session.commit()
        session.refresh(agent)

        existing_lease = RuntimeLease(
            agent_id=agent.id,
            vm_id="vm-existing",
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

        assert lease.vm_id == "vm-existing"
        assert lease.api_base_url == "http://existing-runtime.internal"
        assert lease.started_at is not None
        assert lease.last_heartbeat_at is not None


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

        team = Team(user_id=user.id, name="My Workspace", mode="personal")
        session.add(team)
        session.commit()
        session.refresh(team)

        agent = Agent(
            team_id=team.id,
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

    def fake_wait_for_instance(self, compute_client, *, name: str):
        return self  # pragma: no cover

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
        lambda self, compute_client, *, name: type(
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
        )(),
    )
    monkeypatch.setattr(
        "sutra_backend.runtime.provisioning.GcpFirecrackerRuntimeProvisioner._wait_for_instance",
        lambda self, compute_client, *, name: type(
            "Instance",
            (),
            {
                "name": name,
                "status": "RUNNING",
                "network_ip": "10.0.0.8",
            },
        )(),
    )

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

        team = Team(
            user_id=user.id,
            name="My Workspace",
            mode="personal",
            shared_workspace_uri=f"gs://sutra-runtime/teams/{user.id}/workspace",
        )
        session.add(team)
        session.commit()
        session.refresh(team)

        agent = Agent(
            team_id=team.id,
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
            ),
        )

        session.refresh(agent)

        assert lease.state == "running"
        assert lease.api_base_url == "http://10.0.0.8:8642"
        assert lease.vm_id.startswith("sutra-agent-")
        assert lease.started_at is not None
        assert lease.last_heartbeat_at is not None
        assert agent.status == "ready"
        assert agent.hermes_home_uri == f"gs://sutra-runtime/agents/{agent.id}/hermes-home"
        assert agent.private_volume_uri == f"gs://sutra-runtime/agents/{agent.id}/private-volume"
        assert created_prefixes == [
            ("sutra-runtime", f"agents/{agent.id}/hermes-home"),
            ("sutra-runtime", f"agents/{agent.id}/private-volume"),
        ]
        assert created_disks == [
            (f"sutra-agent-state-{str(agent.id).replace('-', '')[:20]}", 50, "pd-balanced")
        ]
        assert len(created_instance_bodies) == 1
        disks = created_instance_bodies[0]["disks"]
        assert len(disks) == 2
        assert disks[1]["autoDelete"] is False
        assert disks[1]["deviceName"] == "sutra-agent-state"
        metadata_items = created_instance_bodies[0]["metadata"]["items"]
        assert {"key": "sutra-runtime-provider", "value": "gcp_firecracker"} in metadata_items
        assert {"key": "sutra-runtime-api-key", "value": "runtime-key"} in metadata_items
        assert {
            "key": "sutra-state-disk-name",
            "value": f"sutra-agent-state-{str(agent.id).replace('-', '')[:20]}",
        } in metadata_items
        assert {"key": "sutra-runtime-api-bind-host", "value": "0.0.0.0"} in metadata_items
        assert {"key": "sutra-runtime-hermes-workdir", "value": "/opt/hermes-agent"} in metadata_items
        assert {"key": "sutra-runtime-session-mode", "value": "responses_conversation"} in metadata_items
        startup_script_entry = next(
            item for item in metadata_items if item["key"] == "startup-script"
        )
        assert "mkfs.ext4 -F" in startup_script_entry["value"]
        assert "/mnt/sutra/state/hermes-home" in startup_script_entry["value"]
        assert "/mnt/sutra/state/private-volume" in startup_script_entry["value"]
        assert "API_SERVER_ENABLED=true" in startup_script_entry["value"]
        assert "API_SERVER_HOST=0.0.0.0" in startup_script_entry["value"]
        assert "python -m gateway.run" in startup_script_entry["value"]
        assert "systemctl restart sutra-hermes-gateway.service" in startup_script_entry["value"]
        assert "runuser -u sutra-runtime --preserve-environment" in startup_script_entry["value"]
        assert ".hermes/.env" not in startup_script_entry["value"]
        assert {
            "key": "sutra-shared-workspace-uri",
            "value": f"gs://sutra-runtime/teams/{user.id}/workspace",
        } in metadata_items


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
        lambda self, compute_client, *, name: type(
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
        )(),
    )
    monkeypatch.setattr(
        "sutra_backend.runtime.provisioning.GcpFirecrackerRuntimeProvisioner._wait_for_instance",
        lambda self, compute_client, *, name: type(
            "Instance",
            (),
            {
                "name": name,
                "status": "RUNNING",
                "network_ip": "10.0.0.9",
            },
        )(),
    )

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

        team = Team(user_id=user.id, name="Runtime Team", mode="personal")
        session.add(team)
        session.commit()
        session.refresh(team)

        agent = Agent(
            team_id=team.id,
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
    assert "/opt/sutra-runtime-venv/bin/pip install -e ." in startup_script_entry["value"]
    assert "/opt/sutra-runtime-venv/bin/python -m gateway.run" in startup_script_entry["value"]


def test_runtime_lease_table_has_agent_state_composite_index() -> None:
    engine = create_database_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    indexes = inspect(engine).get_indexes("runtime_leases")

    assert any(
        index["name"] == "ix_runtime_leases_agent_id_state"
        and index["column_names"] == ["agent_id", "state"]
        for index in indexes
    )
