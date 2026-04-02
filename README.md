# Sutra (Phase 1)

Sutra is a chat-first control plane for persistent Hermes agents.

Current Phase 1 goal: a non-technical user can sign in, get a ready agent (or team), run work, and keep outputs in a shared workspace without CLI or API-key setup.

This README describes the project **as it exists today**.

## What Works Today

- Local frontend + local backend workflow
- Local dev auth bypass (`dev_bypass`) for E2E QA
- Single-agent chat through managed Hermes runtime API
- Team workspace with huddles, task assignment, inbox cycle, and automation jobs
- Runtime providers:
- `static_dev` (local Hermes runtime)
- `gcp_firecracker` (local control plane + GCP runtime host)
- Secret vault with request-time runtime env injection

## Repository Map

- `backend/` FastAPI control plane (auth, orchestration, persistence, runtime policy)
- `frontend/` React + Vite web app
- `scripts/runtime/` local and hosted runtime helper scripts
- `meta/` product docs, roadmap, runtime topology notes
- `backend/hermes-agent/` Hermes runtime submodule

## Prerequisites

- Python 3.12+
- Node 20+
- `uv` for Python dependency management
- `npm` for frontend
- Postgres (Neon or local Postgres)
- Firebase project (if using real auth instead of bypass)
- `gcloud` CLI (for hosted runtime topology or Cloud Run deploy)

## Configuration Files

- Backend env: `backend/.env` (required)
- Backend template: `backend/.env.example`
- Frontend local env: `frontend/.env.local`
- Frontend template: `frontend/.env.example`

Important: runtime scripts load `backend/.env` directly, so keep it as your source of truth.

---

## 1 Local Development (Frontend + Backend + Local Hermes)

Use this when you want everything on your laptop.

### A. Prepare env

Create `backend/.env` from `backend/.env.example` and set at least:

```bash
APP_ENV=development
POSTGRES_URL=postgresql://...
MASTER_ENCRYPTION_KEY=...
SUTRA_RUNTIME_PROVIDER=static_dev
SUTRA_RUNTIME_API_KEY=your_runtime_key
SUTRA_DEV_RUNTIME_BASE_URL=http://127.0.0.1:8642
SUTRA_DEV_AUTH_BYPASS=true
SUTRA_FRONTEND_URL=http://127.0.0.1:5173
```

Create `frontend/.env.local`:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8001
VITE_AUTH_MODE=dev_bypass
```

### B. Install dependencies

```bash
uv sync --project backend
cd frontend && npm install && cd ..
```

### C. Start services

```bash
bash scripts/runtime/start_local_runtime.sh
bash scripts/runtime/start_local_backend.sh
bash scripts/runtime/start_local_frontend.sh
```

### D. Verify

- Frontend: `http://127.0.0.1:5173`
- Backend health: `http://127.0.0.1:8001/healthz`
- Runtime models: `http://127.0.0.1:8642/v1/models`

---

## 2 Local Control Plane + Hermes on GCP Dev Host

Use this when frontend/backend run locally, but Hermes runtimes run on the GCP host.

Reference topology: `meta/runtime/LOCAL_CONTROL_PLANE_WITH_GCP_HOST.md`.

### A. Backend env shape

In `backend/.env`:

```bash
SUTRA_RUNTIME_PROVIDER=gcp_firecracker
SUTRA_RUNTIME_API_KEY=...
SUTRA_FRONTEND_URL=http://127.0.0.1:5173

GCS_BUCKET_NAME=...
GCP_SERVICE_ACCOUNT_JSON=...
GCP_PROJECT_ID=...
GCP_COMPUTE_ZONE=...
GCP_RUNTIME_HOST_INSTANCE_NAME=sutra-firecracker-host
GCP_RUNTIME_HOST_API_PORT=8787
GCP_RUNTIME_SOURCE_IMAGE_FAMILY=debian-12
GCP_RUNTIME_SOURCE_IMAGE_PROJECT=debian-cloud
GCP_RUNTIME_HERMES_BUNDLE_URI=gs://.../runtime-bundles/hermes-agent-dev.tar.gz

# Local tunnel override:
GCP_RUNTIME_HOST_API_OVERRIDE_BASE_URL=http://127.0.0.1:8787
```

For current dev-host contract testing (without real Firecracker guest launch):

```bash
GCP_RUNTIME_FIRECRACKER_EXECUTE=false
```

### B. Start order

```bash
bash scripts/runtime/start_host_tunnel.sh
bash scripts/runtime/start_local_backend.sh
bash scripts/runtime/start_local_frontend.sh
```

### C. Runtime checks

Use app UI or helper scripts:

```bash
SUTRA_BASE_URL=http://127.0.0.1:8001
SUTRA_BEARER_TOKEN=...
bash scripts/runtime/provision_agent_runtime.sh <agent-id>
bash scripts/runtime/verify_agent_runtime.sh <agent-id>
bash scripts/runtime/restart_agent_runtime.sh <agent-id>
```

---

## 3 Complete GCP Deployment (Current Baseline)

Today there is no single one-click deploy script for the whole stack. The supported shape is:

- frontend on Cloud Run
- backend on Cloud Run
- runtime host on GCE (`sutra-firecracker-host`)
- runtime state on persistent disk + GCS bundle/config artifacts

### A. Runtime host preconditions

- GCP project + zone configured
- Runtime host service account and permissions
- Runtime bundle uploaded to `GCP_RUNTIME_HERMES_BUNDLE_URI`
- `SUTRA_RUNTIME_API_KEY` set consistently between backend and host manager

### B. Deploy backend to Cloud Run

From repo root:

```bash
gcloud run deploy sutra-backend \
  --source backend \
  --region us-central1 \
  --allow-unauthenticated
```

Then set env vars (example):

```bash
gcloud run services update sutra-backend \
  --region us-central1 \
  --update-env-vars APP_ENV=production,SUTRA_RUNTIME_PROVIDER=gcp_firecracker,GCP_PROJECT_ID=...,GCP_COMPUTE_ZONE=...,GCS_BUCKET_NAME=...,SUTRA_RUNTIME_API_KEY=...
```

### C. Deploy frontend to Cloud Run

```bash
gcloud run deploy sutra-frontend \
  --source frontend \
  --region us-central1 \
  --allow-unauthenticated
```

Set `VITE_API_BASE_URL` to the backend service URL at build/deploy time.

### D. Post-deploy smoke checks

1. `GET /healthz` on backend
2. Sign in (or use dev bypass only in non-prod envs)
3. Ensure default agent is created on first auth
4. Provision + verify runtime for that agent
5. Send a chat prompt and confirm workspace artifact writes

---

## Architecture: Important Codepaths

### Backend entry and routing

- App factory/lifecycle: `backend/sutra_backend/main.py`
- Router composition: `backend/sutra_backend/api/routes.py`
- Runtime endpoints: `backend/sutra_backend/api/runtime_routes.py`
- Team endpoints: `backend/sutra_backend/api/teams.py`
- Agent chat endpoints: `backend/sutra_backend/api/agents.py`

### Auth and onboarding bootstrap

- Auth dependency + user resolution: `backend/sutra_backend/auth/dependencies.py`
- First-user workspace/agent seed: `backend/sutra_backend/services/bootstrap.py`

### Runtime orchestration

- Provider abstraction + lease provisioning: `backend/sutra_backend/runtime/provisioning.py`
- Runtime lease readiness reconciliation: `backend/sutra_backend/services/runtime_leases.py`
- Runtime HTTP client wrapper: `backend/sutra_backend/runtime/client.py`
- Host manager contract: `backend/sutra_backend/runtime/firecracker_host_service.py`

### Agent/team execution

- Single-agent run path: `backend/sutra_backend/services/runtime.py`
- Team huddle, tasking, inbox cycle: `backend/sutra_backend/services/team_runtime.py`
- Background inbox poller: `backend/sutra_backend/services/inbox_poller.py`

### Frontend composition

- App routes: `frontend/src/app/App.tsx`
- Hub: `frontend/src/features/hub/HubPage.tsx`
- Chat: `frontend/src/features/chat/ChatPage.tsx`
- Team workspace: `frontend/src/features/teams/TeamWorkspacePage.tsx`
- API client: `frontend/src/lib/api.ts`

---

## Data Flows (Current)

### 1 Authentication + first-use bootstrap

1. Frontend sends Firebase bearer token (or bypass mode identity).
2. Backend resolves user in `get_current_user`.
3. Backend calls `ensure_personal_workspace`.
4. Default role templates, personal team, and default agent are guaranteed.
5. Runtime lease can be provisioned depending on provider settings.

### 2 Single-agent response

1. Frontend calls `POST /api/agents/{agent_id}/responses`.
2. Backend reconciles runtime lease readiness.
3. Backend sends request to Hermes runtime `/v1/responses`.
4. Messages are persisted to `Conversation` + `Message`.
5. Workspace artifact is written at `conversations/<conversation-id>.md`.

### 3 Team huddle and inbox cycle

1. Huddle request creates coordinated role outputs and explicit tasks.
2. Tasks are stored with ownership and claim semantics.
3. Inbox cycle picks next task per agent and runs runtime response.
4. Task updates + completion are persisted.
5. Task outputs are written to shared workspace files.

### 4 Runtime provisioning (`static_dev` vs `gcp_firecracker`)

- `static_dev`: lease points to `SUTRA_DEV_RUNTIME_BASE_URL`.
- `gcp_firecracker`: backend ensures host VM, provisions/restarts microVM via host manager, then stores lease with proxy URL.
- Runtime readiness is continuously reconciled with heartbeat + probe status.

### 5 Secrets flow

1. Secrets are stored encrypted in backend persistence.
2. User picks secrets for a run.
3. Backend decrypts and injects as request-scoped runtime env headers.
4. Runtime uses values for that request without persisting plaintext into conversation context.

---

## Current Gaps / Notes

- Full production IaC pipeline is still evolving; deploy is currently scripted manually with `gcloud`.
- Hosted team orchestration is functional but still improving in dependency-aware execution and UX progress signaling.
- Keep `SUTRA_DEV_AUTH_BYPASS` off in production.

---

## Useful Commands

```bash
# Backend tests
uv run --project backend pytest -q

# Frontend tests
cd frontend && npm test

# Frontend production build
cd frontend && npm run build
```
