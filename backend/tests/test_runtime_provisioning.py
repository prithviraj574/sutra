from __future__ import annotations

from sqlalchemy import inspect
from sqlmodel import Session, SQLModel, select

from sutra_backend.config import Settings
from sutra_backend.db import create_database_engine
from sutra_backend.models import Agent, RoleTemplate, RuntimeLease, Team, User
from sutra_backend.runtime.errors import RuntimeNotReadyError
from sutra_backend.runtime.provisioning import ensure_agent_runtime_lease


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


def test_runtime_provisioner_creates_gcp_firecracker_lease_and_agent_storage(
    monkeypatch,
) -> None:
    engine = create_database_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    created_prefixes: list[tuple[str, str]] = []
    created_instance_bodies: list[dict[str, object]] = []

    def fake_ensure_prefix(self, *, bucket: str, prefix: str) -> None:
        created_prefixes.append((bucket, prefix))

    def fake_get_instance(self, *, name: str):
        return None

    def fake_create_instance(self, *, body: dict[str, object]) -> None:
        created_instance_bodies.append(body)

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
        "sutra_backend.runtime.provisioning.GcpComputeEngineClient.create_instance",
        fake_create_instance,
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
        assert agent.status == "ready"
        assert agent.hermes_home_uri == f"gs://sutra-runtime/agents/{agent.id}/hermes-home"
        assert agent.private_volume_uri == f"gs://sutra-runtime/agents/{agent.id}/private-volume"
        assert created_prefixes == [
            ("sutra-runtime", f"agents/{agent.id}/hermes-home"),
            ("sutra-runtime", f"agents/{agent.id}/private-volume"),
        ]
        assert len(created_instance_bodies) == 1
        metadata_items = created_instance_bodies[0]["metadata"]["items"]
        assert {"key": "sutra-runtime-provider", "value": "gcp_firecracker"} in metadata_items
        assert {"key": "sutra-runtime-api-key", "value": "runtime-key"} in metadata_items
        assert {
            "key": "sutra-shared-workspace-uri",
            "value": f"gs://sutra-runtime/teams/{user.id}/workspace",
        } in metadata_items


def test_runtime_lease_table_has_agent_state_composite_index() -> None:
    engine = create_database_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    indexes = inspect(engine).get_indexes("runtime_leases")

    assert any(
        index["name"] == "ix_runtime_leases_agent_id_state"
        and index["column_names"] == ["agent_id", "state"]
        for index in indexes
    )
