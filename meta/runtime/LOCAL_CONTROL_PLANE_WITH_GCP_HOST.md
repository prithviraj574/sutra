# Local Control Plane With GCP Runtime Host

This is the supported Phase 1 developer topology for personal testing:

- `frontend` runs locally
- `sutra_backend` runs locally
- Hermes runtimes live on a GCP Compute VM that hosts the Sutra runtime manager
- local control-plane traffic reaches the host through an IAP tunnel on `127.0.0.1:8787`

The browser never talks to Hermes directly. The request path is always:

`browser -> sutra_backend -> GCP runtime host -> agent microVM`

Current live dev instance:

- GCP project: `project-3130b11c-429f-49aa-88e`
- zone: `us-central1-a`
- host VM: `sutra-firecracker-host`
- state disk: `sutra-firecracker-host-data`
- host API tunnel target: `http://127.0.0.1:8787`
- Firebase project: `validay-78f8d`

## Backend env shape

Set the backend to use the hosted runtime provider:

```bash
SUTRA_RUNTIME_PROVIDER=gcp_firecracker
SUTRA_FRONTEND_URL=http://localhost:5173
GCP_PROJECT_ID=...
GCP_COMPUTE_ZONE=...
GCS_BUCKET_NAME=...
GCP_SERVICE_ACCOUNT_JSON=...
GCP_RUNTIME_HOST_INSTANCE_NAME=sutra-firecracker-host
GCP_RUNTIME_HOST_API_PORT=8787
GCP_RUNTIME_SOURCE_IMAGE=...
GCP_RUNTIME_SOURCE_IMAGE_PROJECT=...
GCP_RUNTIME_HERMES_BUNDLE_URI=gs://.../runtime-bundles/hermes-agent-dev.tar.gz
```

For the current live dev host, keep:

```bash
GCP_RUNTIME_FIRECRACKER_EXECUTE=false
```

That exercises the host-manager contract, private-path isolation, host proxy path, and local-control-plane-to-GCP-host flow while running Hermes as a per-agent host process.

When the host image, kernel, and rootfs are ready for real guest launch, set:

```bash
GCP_RUNTIME_FIRECRACKER_EXECUTE=true
```

## Runtime isolation rules

- every agent gets its own private root under the host state mount
- every agent gets its own `HERMES_HOME`
- every agent gets its own private volume path
- agents never mount another agent's private root
- the team shared workspace is the only allowed cross-agent file surface

## Operational helpers

Use the runtime scripts under `scripts/runtime/`:

- `start_host_tunnel.sh`
- `start_local_backend.sh`
- `start_local_frontend.sh`
- `provision_agent_runtime.sh`
- `verify_agent_runtime.sh`
- `restart_agent_runtime.sh`
- `teardown_agent_runtime.sh`
- `host_isolation_check.sh`

Recommended local startup order:

1. `./scripts/runtime/start_host_tunnel.sh`
2. `./scripts/runtime/start_local_backend.sh`
3. `./scripts/runtime/start_local_frontend.sh`

The workspace also contains local config files for this topology:

- backend env: `.context/local/backend.env`
- frontend env: `frontend/.env.local`
