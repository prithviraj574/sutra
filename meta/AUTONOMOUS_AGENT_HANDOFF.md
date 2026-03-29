# Sutra Autonomous Agent Handoff

Status: Active execution handoff  
Last Updated: 2026-03-28  
Audience: Another autonomous coding agent with filesystem access

## 0. Start Here

Before making any implementation decision, read these first:

- [meta/VISION.md](/Users/prithviraj/Desktop/Misc/sutra/meta/VISION.md)
- [meta/roadmap/PHASE_1.md](/Users/prithviraj/Desktop/Misc/sutra/meta/roadmap/PHASE_1.md)
- [meta/PRD/phase_1_managed_hermes_wrapper.md](/Users/prithviraj/Desktop/Misc/sutra/meta/PRD/phase_1_managed_hermes_wrapper.md)
- [meta/roadmap/PHASE_1_EXECUTION_PLAN.md](/Users/prithviraj/Desktop/Misc/sutra/meta/roadmap/PHASE_1_EXECUTION_PLAN.md)

The repo-level instruction is simple:

- understand why the product exists before changing how it works
- Phase 1 is about making Hermes usable for non-technical users through a managed web product
- do not pause execution between normal implementation slices

## 1. What This Project Is

Sutra is a managed, multi-tenant, web-first wrapper around Hermes Agent.

The product goal is not to expose Hermes directly. The goal is to provide:

- Google sign-in and zero-setup onboarding
- persistent personal agents and persistent teams
- one runtime per persistent agent
- shared workspace across team agents
- secure secret vaulting with transient runtime injection
- GitHub ownership paths
- calm React-based web UX over a FastAPI control plane

Primary product references:

- [meta/VISION.md](/Users/prithviraj/Desktop/Misc/sutra/meta/VISION.md)
- [meta/roadmap/PHASE_1.md](/Users/prithviraj/Desktop/Misc/sutra/meta/roadmap/PHASE_1.md)
- [meta/PRD/phase_1_managed_hermes_wrapper.md](/Users/prithviraj/Desktop/Misc/sutra/meta/PRD/phase_1_managed_hermes_wrapper.md)
- [meta/roadmap/PHASE_1_EXECUTION_PLAN.md](/Users/prithviraj/Desktop/Misc/sutra/meta/roadmap/PHASE_1_EXECUTION_PLAN.md)

## 2. Execution Mode

This project is being executed continuously.

Do not stop between normal implementation slices just to ask for permission or a checkpoint.

Only stop for:

- true blockers
- destructive-risk operations
- hidden-cost or architecture decisions that materially change scope

Otherwise:

- implement the next consecutive slice
- run verification
- update the roadmap honestly
- continue

## 3. Hard Constraints and Non-Negotiables

### 3.1 Hermes and runtime integration

- Hermes should remain an upstream runtime submodule with minimal or no changes.
- The primary runtime protocol is Hermes `POST /v1/responses`.
- `POST /v1/chat/completions` is compatibility fallback only.
- Do not expose Hermes directly to the browser.
- Sutra backend owns auth, tenancy, policy, runtime orchestration, and telemetry.

### 3.2 Secret handling

This is critical:

- Do not persist user secrets into runtime-readable files such as `HERMES_HOME/.env`.
- User-provided secrets must be decrypted server-side only when needed.
- Agent runs receive secrets as transient request-time env only.
- Secrets must not be returned in API payloads, UI state, or logs.

Relevant files:

- [backend/sutra_backend/runtime/env_policy.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/runtime/env_policy.py)
- [backend/sutra_backend/services/secrets.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/services/secrets.py)
- [backend/sutra_backend/services/runtime.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/services/runtime.py)

### 3.3 Stack decisions

- Web UI: React + TypeScript
- Backend API: FastAPI
- Validation/settings: Pydantic
- Persistence: SQLModel
- Migrations: Alembic generated from SQLModel metadata

## 4. Current Implemented State

## 4.1 Backend

Backend root:

- [backend/sutra_backend](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend)

Implemented:

- FastAPI app factory and core routes
- Pydantic settings
- SQLModel Phase 1 entities
- Alembic baseline migration
- Firebase-backed auth dependency
- automatic first-sign-in bootstrap:
  - default role templates
  - personal team
  - default agent
- runtime client wrapper for Hermes
- provider seam for runtime lease provisioning
- persisted conversation write path
- persisted conversation read path
- secret vault CRUD
- transient secret injection into agent runs
- runtime lease read/provision endpoints

Key backend files:

- App/API:
  - [backend/sutra_backend/main.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/main.py)
  - [backend/sutra_backend/api/routes.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/api/routes.py)
- Auth:
  - [backend/sutra_backend/auth/firebase.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/auth/firebase.py)
  - [backend/sutra_backend/auth/dependencies.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/auth/dependencies.py)
- Models/migrations:
  - [backend/sutra_backend/models.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/models.py)
  - [backend/alembic/versions/8e9091b03d62_initial_schema.py](/Users/prithviraj/Desktop/Misc/sutra/backend/alembic/versions/8e9091b03d62_initial_schema.py)
- Bootstrap/services:
  - [backend/sutra_backend/services/bootstrap.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/services/bootstrap.py)
  - [backend/sutra_backend/services/runtime.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/services/runtime.py)
  - [backend/sutra_backend/services/runtime_leases.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/services/runtime_leases.py)
  - [backend/sutra_backend/services/conversations.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/services/conversations.py)
  - [backend/sutra_backend/services/secrets.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/services/secrets.py)
- Runtime:
  - [backend/sutra_backend/runtime/client.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/runtime/client.py)
  - [backend/sutra_backend/runtime/provisioning.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/runtime/provisioning.py)
  - [backend/sutra_backend/runtime/errors.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/runtime/errors.py)

### Backend API surfaces currently present

- `GET /healthz`
- `GET /api/health`
- `GET /api/auth/me`
- `GET /api/teams`
- `GET /api/agents`
- `GET /api/agents/{agent_id}/runtime`
- `POST /api/agents/{agent_id}/runtime/provision`
- `POST /api/agents/{agent_id}/responses`
- `GET /api/agents/{agent_id}/conversations`
- `GET /api/conversations/{conversation_id}/messages`
- `GET /api/secrets`
- `POST /api/secrets`
- `DELETE /api/secrets/{secret_id}`

### Runtime behavior currently implemented

- `static_dev` runtime provider exists and provisions a synthetic lease backed by configured local runtime URL
- `gcp_firecracker` provider exists only as an explicit not-ready strategy
- the provider seam is real, but managed provisioning is not yet implemented

Important:

- the response route can accept `secret_ids`
- those secrets are decrypted server-side and passed to `HermesRuntimeClient.create_response(..., request_env=...)`
- request env is meant to stay transient

## 4.2 Frontend

Frontend root:

- [frontend](/Users/prithviraj/Desktop/Misc/sutra/frontend)

Implemented:

- Vite React + TypeScript app scaffold
- Firebase auth boundary
- backend session sync
- Hub page
- Chat Canvas shell
- Secret Vault page
- runtime status display in Hub and Chat
- API client covering session, teams, agents, runtime, conversations, messages, and secrets

Key frontend files:

- entry/router:
  - [frontend/src/main.tsx](/Users/prithviraj/Desktop/Misc/sutra/frontend/src/main.tsx)
  - [frontend/src/app/App.tsx](/Users/prithviraj/Desktop/Misc/sutra/frontend/src/app/App.tsx)
- auth/session:
  - [frontend/src/features/auth/AuthProvider.tsx](/Users/prithviraj/Desktop/Misc/sutra/frontend/src/features/auth/AuthProvider.tsx)
  - [frontend/src/features/auth/useSession.ts](/Users/prithviraj/Desktop/Misc/sutra/frontend/src/features/auth/useSession.ts)
  - [frontend/src/lib/firebase.ts](/Users/prithviraj/Desktop/Misc/sutra/frontend/src/lib/firebase.ts)
  - [frontend/src/lib/env.ts](/Users/prithviraj/Desktop/Misc/sutra/frontend/src/lib/env.ts)
- API client:
  - [frontend/src/lib/api.ts](/Users/prithviraj/Desktop/Misc/sutra/frontend/src/lib/api.ts)
- pages:
  - [frontend/src/features/hub/HubPage.tsx](/Users/prithviraj/Desktop/Misc/sutra/frontend/src/features/hub/HubPage.tsx)
  - [frontend/src/features/chat/ChatPage.tsx](/Users/prithviraj/Desktop/Misc/sutra/frontend/src/features/chat/ChatPage.tsx)
  - [frontend/src/features/secrets/SecretsPage.tsx](/Users/prithviraj/Desktop/Misc/sutra/frontend/src/features/secrets/SecretsPage.tsx)

Design system references:

- [frontend/DESIGN.md](/Users/prithviraj/Desktop/Misc/sutra/frontend/DESIGN.md)
- [frontend/globals.css](/Users/prithviraj/Desktop/Misc/sutra/frontend/globals.css)
- [frontend/tailwind.config.js](/Users/prithviraj/Desktop/Misc/sutra/frontend/tailwind.config.js)

## 5. Verification Status

### Backend

Current backend verification command:

```bash
cd backend
./.venv/bin/pytest -q
```

Latest known result:

- `25 passed`

Backend tests cover:

- app health
- settings
- SQLModel persistence
- auth bootstrap
- runtime client behavior
- runtime provisioning seam
- runtime APIs
- agent response persistence
- conversation read APIs
- secret vault CRUD
- transient secret injection

Test directory:

- [backend/tests](/Users/prithviraj/Desktop/Misc/sutra/backend/tests)

Important local test note:

- backend tests spin up a local temporary Postgres instance during pytest
- the fixture depends on local `initdb`, `pg_ctl`, and `createdb` binaries being available
- this is intentional so tests do not depend on a shared remote database

### Frontend

Current frontend verification commands:

```bash
cd frontend
npm test
npm run build
```

Latest known result:

- `npm test` passed
- `npm run build` passed

Frontend tests currently cover:

- API client request/response contracts in [frontend/src/lib/api.test.ts](/Users/prithviraj/Desktop/Misc/sutra/frontend/src/lib/api.test.ts)

Additional reliable compiler check:

```bash
cd frontend
./node_modules/.bin/tsc -b --pretty false
```

## 6. Current Repo State and Working Tree Notes

At the time of handoff, the repo is intentionally mid-execution.

Representative working tree state:

- `.env` is deleted in the working tree
- `.gitignore` is modified
- `.gitmodules` is modified
- `hermes-agent` has been moved to `backend/hermes-agent`
- `backend/`, `frontend/`, and `meta/` contain substantial new work

Meaning:

- do not use destructive cleanup commands
- do not assume the working tree is meant to be pristine
- do not revert unrelated changes you did not create
- if you need to inspect current state, use `git status` and read before acting

## 7. Required Environment Variables

Do not copy secret values into documents, commits, logs, or responses.

Known backend env names already present or expected:

- `MINIMAX_API_KEY`
- `FIRECRAWL_API_KEY`
- `HONCHO_API_KEY`
- `MASTER_ENCRYPTION_KEY`
- `POSTGRES_URL`
- `FIREBASE_SERVICE_ACCOUNT_JSON`
- `GCS_BUCKET_NAME`
- `GCS_SERVICE_ACCOUNT_JSON`

Additional expected/projected env names:

- `SUTRA_RUNTIME_PROVIDER`
- `SUTRA_DEV_RUNTIME_BASE_URL`
- `SUTRA_DEV_RUNTIME_API_KEY`
- `BROWSERBASE_API_KEY`
- `BROWSERBASE_PROJECT_ID`
- or `BROWSER_USE_API_KEY`
- primary LLM provider key such as `OPENROUTER_API_KEY`
- `GITHUB_APP_ID`
- `GITHUB_APP_PRIVATE_KEY`
- `GITHUB_WEBHOOK_SECRET`
- optional `FAL_KEY`
- optional `HONCHO_BASE_URL`

Frontend env names:

- `VITE_API_BASE_URL`
- `VITE_FIREBASE_API_KEY`
- `VITE_FIREBASE_AUTH_DOMAIN`
- `VITE_FIREBASE_PROJECT_ID`
- `VITE_FIREBASE_APP_ID`

Frontend env example:

- [frontend/.env.example](/Users/prithviraj/Desktop/Misc/sutra/frontend/.env.example)

## 8. Hermes Integration Notes

Hermes lives here:

- [backend/hermes-agent](/Users/prithviraj/Desktop/Misc/sutra/backend/hermes-agent)

Key files for interfacing:

- [backend/hermes-agent/.plans/openai-api-server.md](/Users/prithviraj/Desktop/Misc/sutra/backend/hermes-agent/.plans/openai-api-server.md)
- [backend/hermes-agent/gateway/platforms/api_server.py](/Users/prithviraj/Desktop/Misc/sutra/backend/hermes-agent/gateway/platforms/api_server.py)

Current Sutra assumption:

- use Hermes API server as the runtime contract
- default to `/v1/responses`
- preserve `/v1/chat/completions` as fallback
- do not require Hermes submodule edits for the current implemented slices

## 9. Important Implementation Decisions Already Made

### 9.1 Default workspace bootstrap

On first successful auth, the backend ensures:

- role templates exist
- a personal team exists
- a default agent exists

This behavior lives in:

- [backend/sutra_backend/services/bootstrap.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/services/bootstrap.py)

### 9.2 Runtime provisioning seam

Lease provisioning is no longer embedded inside the route logic. It is behind:

- [backend/sutra_backend/runtime/provisioning.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/runtime/provisioning.py)

Current strategies:

- `static_dev`
- `gcp_firecracker` placeholder/not-ready

### 9.3 Secret injection path

The current request-time secret flow is:

1. User stores secret via backend vault API
2. Secret is encrypted at rest in DB
3. Agent run receives `secret_ids`
4. Backend resolves and decrypts owned secrets
5. Backend passes them as transient `request_env` to runtime client

The key rule is:

- never persist these values into runtime files

## 10. Known Gaps and Next Best Tasks

These are the best next tasks in order.

### 10.1 Replace `static_dev` with real managed runtime orchestration

This is the highest-value backend next step.

Needed:

- implement real `gcp_firecracker` provisioning behavior behind the provider seam
- decide how runtime hosts are created, reused, and tracked
- define how per-agent volumes and `HERMES_HOME` are mounted
- move from synthetic leases to real managed leases

Suggested files to extend:

- [backend/sutra_backend/runtime/provisioning.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/runtime/provisioning.py)
- [backend/sutra_backend/services/runtime_leases.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/services/runtime_leases.py)
- [backend/sutra_backend/services/runtime.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/services/runtime.py)

### 10.2 Add constraint naming conventions and schema cleanup

The roadmap still calls this out. The DB foundation works, but naming conventions were not yet formalized in metadata for long-term migration stability.

### 10.3 Extend frontend beyond shell

Good next UI steps:

- show real conversation history navigation in Hub
- add runtime lease status actions in UI
- add secret selection UI in Chat before running a task
- render persisted messages from selected conversations more explicitly
- build Agent Assembly page

### 10.4 GitHub connection slice

The model exists, but real GitHub App flows are not implemented yet.

## 11. Suggested First 60 Minutes For The Next Agent

If you are taking over execution, this is the safest startup sequence:

1. Read [meta/VISION.md](/Users/prithviraj/Desktop/Misc/sutra/meta/VISION.md), [meta/roadmap/PHASE_1.md](/Users/prithviraj/Desktop/Misc/sutra/meta/roadmap/PHASE_1.md), and [meta/roadmap/PHASE_1_EXECUTION_PLAN.md](/Users/prithviraj/Desktop/Misc/sutra/meta/roadmap/PHASE_1_EXECUTION_PLAN.md).
2. Run `git status --short` and verify you understand the current working tree before editing.
3. Run backend verification with `cd backend && ./.venv/bin/pytest -q`.
4. Run frontend verification with `cd frontend && npm test && npm run build`.
5. Open [backend/sutra_backend/runtime/provisioning.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/runtime/provisioning.py), [backend/sutra_backend/services/runtime_leases.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/services/runtime_leases.py), and [backend/sutra_backend/services/runtime.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/services/runtime.py).
6. Continue with the real managed runtime provider path while preserving the currently working `static_dev` path as a fallback.

## 12. Open Decisions And Assumptions To Preserve

These are currently assumed unless the user explicitly changes them:

- React is the only first-class client surface for Phase 1
- FastAPI is the only backend API surface
- Hermes remains upstream with minimal or no direct modifications
- request-time secret injection is allowed, persisted runtime secret files are not
- GCP should be used conservatively because this is still a development-stage project
- checkpoints are for verification and roadmap updates, not permission pauses

## 13. Things To Avoid

- Do not leak raw secret values into docs, tests, logs, or responses.
- Do not revert unrelated repo changes you did not create.
- Do not modify Hermes submodule casually when a Sutra-owned wrapper layer can solve it.
- Do not persist request-time env into `HERMES_HOME/.env`.
- Do not pause for ordinary checkpoints once you have a safe next slice to implement.

## 14. Repo Commands

### Backend

Install and test:

```bash
cd backend
python3 -m venv .venv
./.venv/bin/pip install -e . --group dev
./.venv/bin/pytest -q
```

Run migrations:

```bash
cd backend
./.venv/bin/alembic upgrade head
```

### Frontend

Install:

```bash
cd frontend
npm install
```

Test:

```bash
cd frontend
npm test
```

Build:

```bash
cd frontend
npm run build
```

## 15. Final Handoff Summary

If you are taking over execution now, the shortest useful summary is:

- the backend foundation is real and verified
- the frontend scaffold is real and verified
- auth, bootstrap, runtime lease inspection/provision, agent response persistence, conversation reads, secret vault CRUD, and transient secret injection all exist
- the biggest remaining Phase 1 technical gap is real managed runtime provisioning behind the existing provider seam
- the next best move is to implement `gcp_firecracker` orchestration without breaking the current `static_dev` path
