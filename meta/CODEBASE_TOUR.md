# Sutra Codebase Tour

This document is a practical tour of the codebase as it exists today.

It is not a product pitch and it is not a future-state architecture doc. It is meant to help an engineer understand:

- how the repo is organized
- what is actually implemented right now
- how requests move through the system
- which parts are foundational vs still scaffolding

## 1. What This Repo Is Building Right Now

Phase 1 is a managed, web-first wrapper around Hermes.

The product direction from [VISION.md](/Users/prithviraj/Desktop/Misc/sutra/meta/VISION.md) and [PHASE_1.md](/Users/prithviraj/Desktop/Misc/sutra/meta/roadmap/PHASE_1.md) is:

- non-technical users sign in with Google
- they get a default persistent agent with no setup
- they can also create a small team of role-based agents
- teams coordinate through a huddle, explicit task assignment, task updates, and a shared workspace
- generated output should live in a user-owned place, especially GitHub for code
- user secrets must not be leaked into LLM context

The repo is already past the “empty scaffold” stage. The main product loop is partially real:

- auth and first-sign-in bootstrap exist
- single-agent chat exists
- team creation exists
- huddles and explicit tasks exist
- inbox claim/run flows exist
- a background poller exists
- shared workspace visibility and writes exist
- GitHub export exists

The biggest gap is still infrastructure reality: the control plane is ahead of the real managed runtime layer. We have runtime lease scaffolding and provisioning seams, but not the full Firecracker-per-agent implementation yet.

## 2. Top-Level Repo Layout

At the top level:

- `backend/` holds the FastAPI control plane and Hermes wrapper logic
- `frontend/` holds the React web app
- `meta/` holds product docs, PRD, roadmap, and now this tour
- `AGENTS.md` defines repo-specific instructions for coding agents

Current top-level docs that matter most:

- [VISION.md](/Users/prithviraj/Desktop/Misc/sutra/meta/VISION.md)
- [PHASE_1.md](/Users/prithviraj/Desktop/Misc/sutra/meta/roadmap/PHASE_1.md)
- [PHASE_1_EXECUTION_PLAN.md](/Users/prithviraj/Desktop/Misc/sutra/meta/roadmap/PHASE_1_EXECUTION_PLAN.md)
- [phase_1_managed_hermes_wrapper.md](/Users/prithviraj/Desktop/Misc/sutra/meta/PRD/phase_1_managed_hermes_wrapper.md)

## 3. Backend Structure

The backend lives under [backend/sutra_backend](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend).

Think of it as five layers:

1. app/bootstrap
2. API routers
3. schemas
4. domain services
5. runtime adapters and persistence

### 3.1 App Entry and Lifecycle

Start with [main.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/main.py).

It:

- creates the FastAPI app
- creates the database engine on startup
- optionally starts the in-process inbox poller
- mounts the composed API router under `/api`
- exposes a basic `/healthz`

This file is intentionally small. It wires together the app rather than holding business logic.

### 3.2 Settings and Environment

[config.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/config.py) is the central settings layer.

It uses Pydantic settings and holds configuration for:

- database connection
- Firebase auth
- encryption key
- Hermes runtime API settings
- runtime provider selection
- GCP runtime fields
- GitHub OAuth/App settings
- frontend URL for redirects
- inbox poller intervals and lease settings
- runtime heartbeat freshness thresholds

This file is one of the best places to look if you want to understand what the system expects from infrastructure.

### 3.3 Database and Models

Persistence is defined in [models.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/models.py).

Important tables:

- `User`: Firebase-authenticated app user
- `Team`: a personal team or multi-role team owned by a user
- `RoleTemplate`: reusable role definitions such as planner or researcher
- `Agent`: a persistent agent record tied to a team
- `Conversation`: either a single-agent chat, team conversation, or huddle thread
- `Message`: stored conversation messages
- `ToolEvent`: tool lifecycle record placeholder
- `Artifact`: exported or generated durable outputs, including GitHub exports
- `SharedWorkspaceItem`: the shared team folder entry used for working memory
- `TeamTask`: explicit owned work assigned to an agent
- `TeamTaskUpdate`: audit trail for delegation, messaging, report-back, and completion
- `Secret`: encrypted user secret
- `GitHubConnection`: linked GitHub installation/account
- `AutomationJob`: scheduled work placeholder
- `RuntimeLease`: control-plane record for an agent runtime
- `PollerLease`: control-plane record for the background inbox poller

A useful mental model:

- `Conversation` and `Message` are the human-visible interaction history
- `TeamTask` and `TeamTaskUpdate` are the coordination spine for teams
- `SharedWorkspaceItem` is the team’s durable shared memory
- `RuntimeLease` is how the control plane reasons about whether an agent runtime should exist and whether it looks usable

### 3.4 API Router Layout

The API composition point is [routes.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/api/routes.py).

That file is intentionally thin now. The real routers are split by domain:

- [health.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/api/health.py)
- [auth_routes.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/api/auth_routes.py)
- [teams.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/api/teams.py)
- [agents.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/api/agents.py)
- [tasks.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/api/tasks.py)
- [conversations.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/api/conversations.py)
- [secrets.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/api/secrets.py)
- [runtime_routes.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/api/runtime_routes.py)
- [system.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/api/system.py)
- [github.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/api/github.py)
- [github_integration.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/api/github_integration.py)

This split is important because the codebase had started drifting toward a giant single router file before it was refactored back into domain boundaries.

### 3.5 Auth Layer

The auth code is in [auth/firebase.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/auth/firebase.py) and [auth/dependencies.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/auth/dependencies.py).

Current auth model:

- the frontend gets a Firebase identity token
- the backend verifies it
- first sign-in bootstraps local app data if needed
- the request then gets a current Sutra `User`

Bootstrap behavior lives in [services/bootstrap.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/services/bootstrap.py).

That bootstrap currently seeds:

- default role templates
- a personal team
- a default agent
- optional early runtime provisioning when config supports it

### 3.6 Runtime Adapter Layer

The runtime boundary is split into a few pieces:

- [runtime/client.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/runtime/client.py)
- [runtime/env_policy.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/runtime/env_policy.py)
- [runtime/errors.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/runtime/errors.py)
- [runtime/provisioning.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/runtime/provisioning.py)

What these do:

- `client.py` wraps Hermes API calls, especially `/v1/responses`
- `env_policy.py` enforces the rule that sensitive env is request-time only
- `errors.py` gives typed runtime failures
- `provisioning.py` is the provider seam for runtime lease creation and future infrastructure-backed provisioning

Important current reality:

- the code is structured as if a real managed runtime fleet exists
- the full Firecracker-per-agent implementation is not there yet
- the `gcp_firecracker` path is still closer to host/lease scaffolding than a fully proven runtime layer

So when reading runtime code, separate “control-plane shape” from “infra completeness.”

### 3.7 Backend Services

Most backend behavior lives in [services](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/services).

The important service modules are:

- [bootstrap.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/services/bootstrap.py)
- [conversations.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/services/conversations.py)
- [github_integration.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/services/github_integration.py)
- [inbox_poller.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/services/inbox_poller.py)
- [runtime.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/services/runtime.py)
- [runtime_leases.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/services/runtime_leases.py)
- [secrets.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/services/secrets.py)
- [team_runtime.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/services/team_runtime.py)
- [teams.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/services/teams.py)

High-level responsibilities:

- `runtime.py`: single-agent execution path
- `team_runtime.py`: huddles, team runs, inbox claims, delegation, task updates, team cycles
- `teams.py`: team creation and shared workspace write helpers
- `conversations.py`: conversation reads
- `secrets.py`: secret encryption, decryption, and transient env resolution
- `runtime_leases.py`: runtime readiness interpretation and reconciliation
- `inbox_poller.py`: background sweep loop for queued team tasks
- `github_integration.py`: repo listing and export-to-GitHub flows

If you want to understand “how the product behaves,” `team_runtime.py`, `runtime.py`, and `teams.py` are the three most important backend files.

### 3.8 Schemas

The API schemas live under [schemas](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/schemas).

These are straightforward request/response models grouped by domain:

- auth
- catalog
- conversations
- GitHub
- runtime
- runtime leases
- secrets
- system
- team runtime

They matter because the frontend is strongly shaped around these payloads.

## 4. Frontend Structure

The frontend lives under [frontend/src](/Users/prithviraj/Desktop/Misc/sutra/frontend/src).

Think of it as:

- app shell and routing
- auth/session plumbing
- a typed API client
- feature pages

### 4.1 App Shell

Start with [main.tsx](/Users/prithviraj/Desktop/Misc/sutra/frontend/src/main.tsx) and [App.tsx](/Users/prithviraj/Desktop/Misc/sutra/frontend/src/app/App.tsx).

The current route map is small and product-focused:

- `/` -> Hub
- `/agents/:agentId` -> single-agent chat
- `/teams/new` -> team assembly
- `/teams/:teamId` -> team workspace
- `/secrets` -> secret vault

This is a good reflection of what the product currently is: a thin control-plane UI around agents, teams, and owned outputs.

### 4.2 Auth and Session

Auth/session code lives in:

- [AuthProvider.tsx](/Users/prithviraj/Desktop/Misc/sutra/frontend/src/features/auth/AuthProvider.tsx)
- [useSession.ts](/Users/prithviraj/Desktop/Misc/sutra/frontend/src/features/auth/useSession.ts)
- [firebase.ts](/Users/prithviraj/Desktop/Misc/sutra/frontend/src/lib/firebase.ts)

Current flow:

- sign in with Firebase on the client
- send identity token to backend requests
- backend resolves the authenticated Sutra user
- React Query queries then load the user’s teams, agents, conversations, and runtime state

### 4.3 API Client

[api.ts](/Users/prithviraj/Desktop/Misc/sutra/frontend/src/lib/api.ts) is the frontend’s typed backend client.

This file is important because it exposes the real product surface area:

- list teams and agents
- read conversations
- create agent responses
- create team huddles
- create team responses
- read workspace and artifacts
- claim/run inbox tasks
- delegate tasks
- post task messages
- read poller status
- manage secrets
- GitHub connect/list/export paths

If you want a quick inventory of what the backend currently exposes to the UI, this is the fastest frontend file to read.

### 4.4 Hub Page

[HubPage.tsx](/Users/prithviraj/Desktop/Misc/sutra/frontend/src/features/hub/HubPage.tsx) is the current landing dashboard after sign-in.

It pulls together:

- current teams
- current agents
- recent conversations
- GitHub connection state
- default agent runtime state
- workspace previews per team

It is effectively the control center for the current product.

### 4.5 Single-Agent Chat

[ChatPage.tsx](/Users/prithviraj/Desktop/Misc/sutra/frontend/src/features/chat/ChatPage.tsx) is the single-agent experience.

What it does today:

- loads an agent and its conversations
- sends a user prompt to the backend runtime path
- shows persisted history
- loads related workspace items and artifacts
- surfaces current-conversation generated files more prominently
- supports export of selected outputs to GitHub

Helper logic for chat-related workspace behavior is in:

- [workspace.ts](/Users/prithviraj/Desktop/Misc/sutra/frontend/src/features/chat/workspace.ts)
- [routes.ts](/Users/prithviraj/Desktop/Misc/sutra/frontend/src/features/chat/routes.ts)

### 4.6 Team Assembly

[TeamAssemblyPage.tsx](/Users/prithviraj/Desktop/Misc/sutra/frontend/src/features/teams/TeamAssemblyPage.tsx) is the flow for creating a team from role templates.

This is where the user shifts from a personal default agent into a multi-agent setup.

### 4.7 Team Workspace

[TeamWorkspacePage.tsx](/Users/prithviraj/Desktop/Misc/sutra/frontend/src/features/teams/TeamWorkspacePage.tsx) is the busiest page in the app right now.

This page currently acts as:

- team chat runner
- huddle launcher
- shared workspace browser
- task inbox UI
- task update log
- delegation surface
- task message surface
- inbox pickup/run controls
- poller status viewer
- GitHub export viewer

If the single-agent chat is the simplest vertical slice, the team workspace is the current center of product experimentation.

### 4.8 Secrets Page

[SecretsPage.tsx](/Users/prithviraj/Desktop/Misc/sutra/frontend/src/features/secrets/SecretsPage.tsx) is the UI for the encrypted secret vault.

It currently supports:

- create secret
- list secrets
- delete secret

It is intentionally small, but it backs one of the most important security constraints in the product.

## 5. The Main Product Flows

The easiest way to understand the codebase is to trace the actual user flows.

### 5.1 First Sign-In and Bootstrap

Path:

1. user signs in with Firebase in the frontend
2. backend verifies the token
3. backend creates or loads a `User`
4. bootstrap seeds default role templates, a personal team, and a default agent
5. optional runtime provisioning is attempted if configured

Main files:

- [AuthProvider.tsx](/Users/prithviraj/Desktop/Misc/sutra/frontend/src/features/auth/AuthProvider.tsx)
- [useSession.ts](/Users/prithviraj/Desktop/Misc/sutra/frontend/src/features/auth/useSession.ts)
- [auth/dependencies.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/auth/dependencies.py)
- [services/bootstrap.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/services/bootstrap.py)

### 5.2 Single-Agent Chat Flow

Path:

1. user opens `/agents/:agentId`
2. frontend loads agent, conversations, runtime, workspace context, GitHub connection
3. user submits a prompt
4. backend resolves the agent and runtime target
5. transient secret env is injected if requested
6. Hermes `/v1/responses` is called
7. conversation and message records are persisted
8. generated outputs and artifacts are shown back in the chat surface

Main files:

- [ChatPage.tsx](/Users/prithviraj/Desktop/Misc/sutra/frontend/src/features/chat/ChatPage.tsx)
- [api.ts](/Users/prithviraj/Desktop/Misc/sutra/frontend/src/lib/api.ts)
- [api/agents.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/api/agents.py)
- [services/runtime.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/services/runtime.py)
- [runtime/client.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/runtime/client.py)

### 5.3 Team Huddle Flow

Path:

1. user opens a team page
2. user submits a goal to “run huddle”
3. backend creates or loads a `team_huddle` conversation
4. each team agent produces alignment output
5. backend writes a shared plan into the workspace
6. backend creates explicit `TeamTask` rows assigned to roles

Main files:

- [TeamWorkspacePage.tsx](/Users/prithviraj/Desktop/Misc/sutra/frontend/src/features/teams/TeamWorkspacePage.tsx)
- [api/teams.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/api/teams.py)
- [services/team_runtime.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/services/team_runtime.py)

This is one of the clearest places where the code is aligned with the roadmap. The team is not supposed to just “free-form vibe chat.” It is supposed to align first, then split work.

### 5.4 Team Execution Flow

Path:

1. user runs a team response
2. backend loads team, agents, templates, workspace context, huddle plan, and open tasks
3. each agent is run with role-specific context plus team context
4. per-agent outputs are persisted into the shared workspace
5. a rolled-up summary is also written into the workspace
6. returned payload includes generated workspace items so the UI can focus them immediately

This is why the shared workspace matters. It is not just a file browser; it is becoming the system’s durable team memory.

### 5.5 Team Task / Inbox Flow

Path:

1. huddles or team actions create `TeamTask` entries
2. tasks can be delegated or annotated with `TeamTaskUpdate`
3. an agent or UI can claim the next task
4. claimed tasks get a lease
5. execution writes updates and completion records
6. output can be written back into the shared workspace

Main backend code:

- [services/team_runtime.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/services/team_runtime.py)

This file now does a lot of team coordination work:

- task listing
- claim recovery
- task delegation
- task messaging
- task completion
- inbox run-next execution
- team inbox cycle execution

This is the current implementation of “explicit task assignment” from the roadmap.

### 5.6 Background Poller Flow

Path:

1. FastAPI starts
2. optional in-process `InboxPoller` starts
3. poller acquires a Postgres-backed `PollerLease`
4. poller sweeps teams for claimable work
5. each sweep can run a bounded amount of inbox work
6. heartbeat and last-sweep metadata are updated

Main files:

- [main.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/main.py)
- [services/inbox_poller.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/services/inbox_poller.py)
- [api/system.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/api/system.py)

Current product implication:

- the system can advance queued team work in the background
- this is still a control-plane poller, not a final runtime-native scheduler design

### 5.7 Secret Vault Flow

Path:

1. user stores a secret in the vault
2. backend encrypts it before persistence
3. when an agent run needs secrets, backend decrypts them server-side
4. secret values are passed as transient runtime env only for that run
5. secrets are not supposed to land in persisted runtime-readable env files or conversation context

Main files:

- [services/secrets.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/services/secrets.py)
- [runtime/env_policy.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/runtime/env_policy.py)
- [api/secrets.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/api/secrets.py)
- [SecretsPage.tsx](/Users/prithviraj/Desktop/Misc/sutra/frontend/src/features/secrets/SecretsPage.tsx)

This rule is one of the repo’s most important safety constraints.

### 5.8 GitHub Export Flow

Path:

1. user connects GitHub
2. frontend can list repositories through the backend
3. user selects a workspace item or generated output
4. backend commits it into the selected user-owned repo
5. artifact history stores the export result
6. UI can show file URL and commit URL

Main files:

- [api/github.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/api/github.py)
- [api/github_integration.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/api/github_integration.py)
- [services/github_integration.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/services/github_integration.py)
- [ChatPage.tsx](/Users/prithviraj/Desktop/Misc/sutra/frontend/src/features/chat/ChatPage.tsx)
- [TeamWorkspacePage.tsx](/Users/prithviraj/Desktop/Misc/sutra/frontend/src/features/teams/TeamWorkspacePage.tsx)

This is the current answer to “the user should own the output.”

## 6. What Is Implemented vs What Is Still Scaffolding

### Real enough to build on

- Firebase-backed sign-in
- first-sign-in bootstrap
- typed FastAPI control plane
- SQLModel/Alembic persistence
- single-agent chat
- role-template-based team creation
- huddles
- explicit team task assignment
- task updates, delegation, and messages
- inbox claim/run flows
- background poller
- shared workspace writes and reads
- encrypted secret vault
- GitHub connection and export path
- mobile-conscious React UI structure

### Still transitional or incomplete

- real Firecracker-per-agent runtime lifecycle
- real per-agent persistent volume behavior on managed infra
- strong runtime readiness based on fully proven hosted Hermes reachability
- full real-time streaming UX for tool events and runtime activity
- true runtime-native autonomous polling instead of control-plane-led background work
- richer inter-agent communication semantics beyond task-scoped notes and delegation
- end-to-end polished artifact model beyond workspace text and GitHub export

The safest way to think about the current codebase is:

- product and control-plane behavior are materially real
- managed-runtime infrastructure is not fully real yet

## 7. Suggested Reading Order

If you are brand new to the repo, read in this order:

1. [VISION.md](/Users/prithviraj/Desktop/Misc/sutra/meta/VISION.md)
2. [PHASE_1.md](/Users/prithviraj/Desktop/Misc/sutra/meta/roadmap/PHASE_1.md)
3. [PHASE_1_EXECUTION_PLAN.md](/Users/prithviraj/Desktop/Misc/sutra/meta/roadmap/PHASE_1_EXECUTION_PLAN.md)
4. [models.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/models.py)
5. [main.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/main.py)
6. [config.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/config.py)
7. [services/runtime.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/services/runtime.py)
8. [services/team_runtime.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/services/team_runtime.py)
9. [services/inbox_poller.py](/Users/prithviraj/Desktop/Misc/sutra/backend/sutra_backend/services/inbox_poller.py)
10. [frontend/src/lib/api.ts](/Users/prithviraj/Desktop/Misc/sutra/frontend/src/lib/api.ts)
11. [HubPage.tsx](/Users/prithviraj/Desktop/Misc/sutra/frontend/src/features/hub/HubPage.tsx)
12. [ChatPage.tsx](/Users/prithviraj/Desktop/Misc/sutra/frontend/src/features/chat/ChatPage.tsx)
13. [TeamWorkspacePage.tsx](/Users/prithviraj/Desktop/Misc/sutra/frontend/src/features/teams/TeamWorkspacePage.tsx)

That path gives a good balance of product context, data model, backend execution, and UI behavior.

## 8. Current Architectural Summary in One Paragraph

Today, Sutra is a FastAPI control plane plus a React app that together manage persistent users, teams, agents, conversations, tasks, secrets, shared workspace items, runtime leases, and GitHub exports around Hermes; the strongest implemented product loop is now the control-plane layer for single-agent and team coordination, while the largest unfinished piece is the real hosted runtime infrastructure that should eventually give each agent a true isolated persistent Hermes environment.
