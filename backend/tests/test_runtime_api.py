from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from tempfile import NamedTemporaryFile

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, select

from sutra_backend.auth import dependencies as auth_dependencies
from sutra_backend.config import Settings
from sutra_backend.db import create_database_engine, get_session
from sutra_backend.main import create_app
from sutra_backend.models import Agent, RuntimeLease, Team, utcnow
from sutra_backend.runtime.client import RuntimeHealthProbe


@dataclass(frozen=True)
class FakeIdentity:
    uid: str
    email: str
    name: str | None = None
    picture: str | None = None


def build_client(settings: Settings) -> tuple[TestClient, Session]:
    database_file = NamedTemporaryFile(suffix=".db")
    engine = create_database_engine(f"sqlite:///{database_file.name}")
    SQLModel.metadata.create_all(engine)
    session = Session(engine)

    app = create_app(settings)

    def override_get_session() -> Session:
        return session

    app.dependency_overrides[get_session] = override_get_session
    app.state._database_file = database_file
    return TestClient(app), session


def authenticate_default_user(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(
        auth_dependencies,
        "verify_firebase_token",
        lambda _: FakeIdentity(
            uid="firebase-user-1",
            email="user@example.com",
            name="Sutra User",
            picture="https://example.com/avatar.png",
        ),
    )

    response = client.get("/api/auth/me", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 200


def test_runtime_provision_route_creates_and_returns_agent_lease(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        runtime_provider="static_dev",
        dev_runtime_base_url="http://runtime.internal",
        dev_runtime_api_key="runtime-key",
    )
    client, session = build_client(settings)
    authenticate_default_user(client, monkeypatch)
    agent = session.exec(select(Agent)).one()

    provision_response = client.post(
        f"/api/agents/{agent.id}/runtime/provision",
        headers={"Authorization": "Bearer valid-token"},
    )
    lease_response = client.get(
        f"/api/agents/{agent.id}/runtime",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert provision_response.status_code == 200
    assert lease_response.status_code == 200
    assert provision_response.json()["lease"]["api_base_url"] == "http://runtime.internal"
    assert provision_response.json()["lease"]["provider"] == "static_dev"
    assert provision_response.json()["lease"]["ready"] is True
    assert provision_response.json()["lease"]["heartbeat_fresh"] is True
    assert provision_response.json()["lease"]["readiness_stage"] == "api_reachable"
    assert provision_response.json()["lease"]["isolation_ok"] is True
    assert lease_response.json()["lease"]["agent_id"] == str(agent.id)


def test_runtime_provision_route_replaces_provider_mismatched_lease(monkeypatch) -> None:
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
    )
    client, session = build_client(settings)
    monkeypatch.setattr(
        "sutra_backend.runtime.provisioning.GcpStorageClient.ensure_prefix",
        lambda self, *, bucket, prefix: None,
    )
    monkeypatch.setattr(
        "sutra_backend.runtime.provisioning.GcpComputeEngineClient.get_instance",
        lambda self, *, name: type(
            "Instance",
            (),
            {"name": name, "status": "RUNNING", "network_ip": "10.0.0.8", "external_ip": "34.118.10.8"},
        )(),
    )
    monkeypatch.setattr(
        "sutra_backend.runtime.provisioning.GcpComputeEngineClient.get_disk",
        lambda self, *, name: type(
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
            {"name": name, "status": "RUNNING", "network_ip": "10.0.0.8", "external_ip": "34.118.10.8"},
        )(),
    )
    monkeypatch.setattr(
        "sutra_backend.runtime.provisioning.GcpFirecrackerRuntimeProvisioner._wait_for_host_api",
        lambda self, host_api_base_url: None,
    )
    monkeypatch.setattr(
        "sutra_backend.runtime.provisioning.GcpFirecrackerHostClient.provision_microvm",
        lambda self, *, payload: type(
            "Microvm",
            (),
            {
                "microvm_id": str(payload["microvm_id"]),
                "state": "running",
                "proxy_base_url": (
                    f"http://34.118.10.8:8787/microvms/{payload['microvm_id']}/proxy/"
                ),
            },
        )(),
    )
    authenticate_default_user(client, monkeypatch)
    agent = session.exec(select(Agent)).one()
    existing_lease = session.exec(select(RuntimeLease).where(RuntimeLease.agent_id == agent.id)).one()
    session.delete(existing_lease)
    session.commit()

    stale_lease = RuntimeLease(
        agent_id=agent.id,
        vm_id=f"local-dev-{str(agent.id)[:8]}",
        state="running",
        api_base_url="http://127.0.0.1:8642",
    )
    session.add(stale_lease)
    session.commit()

    response = client.post(
        f"/api/agents/{agent.id}/runtime/provision",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 200
    payload = response.json()["lease"]
    assert payload["provider"] == "gcp_firecracker"
    assert payload["vm_id"].startswith("agent-")
    assert payload["vm_id"] != stale_lease.vm_id
    session.refresh(agent)
    lease = session.exec(select(RuntimeLease).where(RuntimeLease.agent_id == agent.id)).one()
    assert lease.id != stale_lease.id


def test_runtime_route_recovers_static_dev_runtime_when_endpoint_is_missing(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        runtime_provider="static_dev",
        dev_runtime_base_url="http://runtime.internal",
        dev_runtime_api_key="runtime-key",
        runtime_heartbeat_stale_seconds=300,
    )
    client, session = build_client(settings)
    authenticate_default_user(client, monkeypatch)
    agent = session.exec(select(Agent)).one()

    provision_response = client.post(
        f"/api/agents/{agent.id}/runtime/provision",
        headers={"Authorization": "Bearer valid-token"},
    )
    assert provision_response.status_code == 200

    lease = session.exec(select(RuntimeLease).where(RuntimeLease.agent_id == agent.id)).one()
    lease.api_base_url = None
    session.add(lease)
    session.commit()

    response = client.get(
        f"/api/agents/{agent.id}/runtime",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 200
    payload = response.json()["lease"]
    assert payload["ready"] is True
    assert payload["readiness_stage"] == "api_reachable"
    assert payload["readiness_reason"] == "Runtime is ready for requests."
    assert payload["api_base_url"] == "http://runtime.internal"


def test_runtime_route_reconciles_stale_runtime_health(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        runtime_provider="static_dev",
        dev_runtime_base_url="http://runtime.internal",
        dev_runtime_api_key="runtime-key",
        runtime_heartbeat_stale_seconds=1,
    )
    client, session = build_client(settings)
    authenticate_default_user(client, monkeypatch)
    agent = session.exec(select(Agent)).one()

    provision_response = client.post(
        f"/api/agents/{agent.id}/runtime/provision",
        headers={"Authorization": "Bearer valid-token"},
    )
    assert provision_response.status_code == 200

    lease = session.exec(select(RuntimeLease).where(RuntimeLease.agent_id == agent.id)).one()
    lease.last_heartbeat_at = utcnow() - timedelta(minutes=10)
    session.add(lease)
    session.commit()

    monkeypatch.setattr(
        "sutra_backend.services.runtime_leases.probe_runtime_health",
        lambda *args, **kwargs: RuntimeHealthProbe(
            reachable=False,
            status_code=None,
            checked_url="http://runtime.internal/health",
            detail="Runtime probe failed: connection refused.",
        ),
    )

    response = client.get(
        f"/api/agents/{agent.id}/runtime",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 200
    payload = response.json()["lease"]
    assert payload["ready"] is False
    assert payload["provider"] == "static_dev"
    assert payload["readiness_stage"] == "unreachable"
    assert payload["readiness_reason"] == "Runtime probe failed: connection refused."
    assert payload["probe_checked_url"] == "http://runtime.internal/health"
    assert payload["isolation_ok"] is True

    session.refresh(lease)
    assert lease.state == "unreachable"


def test_runtime_route_updates_stale_static_dev_base_url_before_probe(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        runtime_provider="static_dev",
        dev_runtime_base_url="http://runtime.internal",
        dev_runtime_api_key="runtime-key",
        runtime_heartbeat_stale_seconds=1,
    )
    client, session = build_client(settings)
    authenticate_default_user(client, monkeypatch)
    agent = session.exec(select(Agent)).one()

    provision_response = client.post(
        f"/api/agents/{agent.id}/runtime/provision",
        headers={"Authorization": "Bearer valid-token"},
    )
    assert provision_response.status_code == 200

    lease = session.exec(select(RuntimeLease).where(RuntimeLease.agent_id == agent.id)).one()
    lease.api_base_url = "http://stale-runtime.internal"
    lease.last_heartbeat_at = utcnow() - timedelta(minutes=10)
    lease.state = "running"
    session.add(lease)
    session.commit()

    monkeypatch.setattr(
        "sutra_backend.services.runtime_leases.probe_runtime_health",
        lambda *args, **kwargs: RuntimeHealthProbe(
            reachable=True,
            status_code=200,
            checked_url="http://runtime.internal/health",
            detail="Runtime probe succeeded.",
        ),
    )

    response = client.get(
        f"/api/agents/{agent.id}/runtime",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 200
    payload = response.json()["lease"]
    assert payload["ready"] is True
    assert payload["provider"] == "static_dev"
    assert payload["readiness_stage"] == "api_reachable"
    assert payload["probe_checked_url"] == "http://runtime.internal/health"

    session.refresh(lease)
    assert lease.api_base_url == "http://runtime.internal"


def test_runtime_route_replaces_provider_mismatched_lease_when_static_dev_is_active(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        runtime_provider="static_dev",
        dev_runtime_base_url="http://runtime.internal",
        dev_runtime_api_key="runtime-key",
    )
    client, session = build_client(settings)
    authenticate_default_user(client, monkeypatch)
    agent = session.exec(select(Agent)).one()

    existing_lease = session.exec(select(RuntimeLease).where(RuntimeLease.agent_id == agent.id)).one()
    session.delete(existing_lease)
    session.commit()

    stale_lease = RuntimeLease(
        agent_id=agent.id,
        vm_id=f"agent-{str(agent.id).replace('-', '')[:20]}",
        state="unreachable",
        api_base_url="http://127.0.0.1:8789/microvms/stale/proxy/",
        host_vm_id="sutra-firecracker-host",
        host_api_base_url="http://127.0.0.1:8789",
    )
    session.add(stale_lease)
    session.commit()

    response = client.get(
        f"/api/agents/{agent.id}/runtime",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 200
    payload = response.json()["lease"]
    assert payload["provider"] == "static_dev"
    assert payload["ready"] is True
    assert payload["api_base_url"] == "http://runtime.internal"
    assert payload["host_vm_id"] is None

    lease = session.exec(select(RuntimeLease).where(RuntimeLease.agent_id == agent.id)).one()
    assert lease.id != stale_lease.id
    assert lease.vm_id.startswith("local-dev-")
    assert lease.api_base_url == "http://runtime.internal"


def test_runtime_verify_route_probes_responses_and_reports_isolation(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        runtime_provider="static_dev",
        dev_runtime_base_url="http://runtime.internal",
        dev_runtime_api_key="runtime-key",
    )
    client, session = build_client(settings)
    authenticate_default_user(client, monkeypatch)
    agent = session.exec(select(Agent)).one()

    provision_response = client.post(
        f"/api/agents/{agent.id}/runtime/provision",
        headers={"Authorization": "Bearer valid-token"},
    )
    assert provision_response.status_code == 200

    async def fake_create_response(self, request, *, request_env=None):
        return {"ignored": True}

    monkeypatch.setattr(
        "sutra_backend.services.runtime_leases.HermesRuntimeClient.create_response",
        fake_create_response,
    )

    response = client.post(
        f"/api/agents/{agent.id}/runtime/verify",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 200
    payload = response.json()["lease"]
    assert payload["provider"] == "static_dev"
    assert payload["readiness_stage"] == "responses_ready"
    assert payload["probe_checked_url"] == "http://runtime.internal/v1/responses"
    assert payload["probe_detail"] == "Runtime accepted a verification response request."
    assert payload["isolation_ok"] is True


def test_runtime_restart_route_recovers_existing_lease(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        runtime_provider="static_dev",
        dev_runtime_base_url="http://runtime.internal",
        dev_runtime_api_key="runtime-key",
    )
    client, session = build_client(settings)
    authenticate_default_user(client, monkeypatch)
    agent = session.exec(select(Agent)).one()

    provision_response = client.post(
        f"/api/agents/{agent.id}/runtime/provision",
        headers={"Authorization": "Bearer valid-token"},
    )
    assert provision_response.status_code == 200

    lease = session.exec(select(RuntimeLease).where(RuntimeLease.agent_id == agent.id)).one()
    lease.state = "unreachable"
    lease.last_heartbeat_at = None
    session.add(lease)
    session.commit()

    response = client.post(
        f"/api/agents/{agent.id}/runtime/restart",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 200
    payload = response.json()["lease"]
    assert payload["state"] == "running"
    assert payload["provider"] == "static_dev"
    assert payload["ready"] is True
    assert payload["readiness_stage"] == "api_reachable"
    assert payload["isolation_ok"] is True

    session.refresh(lease)
    assert lease.state == "running"
    assert lease.last_heartbeat_at is not None


def test_runtime_route_reports_isolation_failure_when_sibling_storage_collides(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        runtime_provider="static_dev",
        dev_runtime_base_url="http://runtime.internal",
        dev_runtime_api_key="runtime-key",
    )
    client, session = build_client(settings)
    authenticate_default_user(client, monkeypatch)
    agent = session.exec(select(Agent)).one()

    provision_response = client.post(
        f"/api/agents/{agent.id}/runtime/provision",
        headers={"Authorization": "Bearer valid-token"},
    )
    assert provision_response.status_code == 200

    team = session.get(Team, agent.team_id)
    assert team is not None
    sibling = Agent(
        team_id=team.id,
        name="Sibling Agent",
        role_name="Researcher",
        hermes_home_uri=f"local://agents/{agent.id}/different-hermes-home",
        private_volume_uri=f"local://agents/{agent.id}/private-volume",
    )
    session.add(sibling)
    session.commit()

    response = client.get(
        f"/api/agents/{agent.id}/runtime",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 200
    payload = response.json()["lease"]
    assert payload["isolation_ok"] is False
    assert payload["isolation_reason"] == "Agent private volume URI collides with another agent."


def test_runtime_route_reports_not_provisioned_when_lease_has_not_been_created(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite://",
        runtime_provider="static_dev",
    )
    client, session = build_client(settings)
    authenticate_default_user(client, monkeypatch)
    agent = session.exec(select(Agent)).one()

    response = client.get(
        f"/api/agents/{agent.id}/runtime",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 200
    payload = response.json()["lease"]
    assert payload["ready"] is False
    assert payload["readiness_stage"] == "not_provisioned"
    assert payload["readiness_reason"] == "Runtime is still provisioning."
    assert payload["probe_detail"] == "Runtime has not been provisioned yet."
