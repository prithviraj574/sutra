# Sutra Phase 1 Execution Plan

Status: Approved and in execution  
Execution State: Milestone 1 in progress  
Last Updated: 2026-03-30  
Primary Reference: [`meta/PRD/phase_1_managed_hermes_wrapper.md`](/Users/prithviraj/Desktop/Misc/sutra/meta/PRD/phase_1_managed_hermes_wrapper.md)

## Current Progress

Execution mode for this plan:

- execute consecutive tasks continuously without waiting for review between normal implementation slices
- use checkpoints only for verification, not as pause points
- stop only for true blockers, destructive-risk decisions, or hidden-cost choices that materially change scope
- batch coherent multi-file milestones when the path is clear, then verify them aggressively before moving on

Completed in the first execution pass:

- backend Python workspace scaffolded under `backend/`
- FastAPI app factory and health routes created
- Pydantic settings layer added
- SQLModel Phase 1 entity set added
- Alembic configured against SQLModel metadata
- initial Alembic migration generated
- pytest suite added, including a local Postgres-backed persistence test
- Firebase-backed auth bootstrap route added
- first-sign-in bootstrap now seeds role templates, a personal team, and a default agent
- Sutra-owned Hermes runtime client added with `/v1/responses` as the default path and `/v1/chat/completions` fallback
- authenticated agent response API added with local-dev runtime lease fallback and conversation persistence
- authenticated catalog APIs added for listing teams and agents
- runtime lease creation is now behind a provider seam with `static_dev` and future `gcp_firecracker` strategies
- authenticated conversation read APIs added for agent conversation lists and persisted message history
- encrypted secret vault APIs added for owned secret create/list/delete flows
- owned secrets can now be decrypted server-side and injected into agent runs as transient runtime env
- GitHub connection groundwork exists, but Phase 1 still needs a complete user-owned code path from connected account to repo commit
- backend env example now documents required GitHub OAuth/App variables and frontend Hub exposes GitHub connection state plus connect redirect
- React + TypeScript frontend scaffold added with Firebase auth handoff, Hub, and Chat Canvas shell
- frontend verification is working with `npm test` and `npm run build`
- Secret Vault UI added to the React app and wired to backend APIs
- runtime env policy added to keep request-time secrets out of persisted VM-readable env files
- managed runtime work is still in lease-scaffolding stage; real Firecracker lifecycle, runtime health reconciliation, and persistent volume behavior are not complete yet
- role templates are now exposed through the backend and the web app can create a real multi-agent team with distinct roles
- shared team workspace visibility now exists as a first product surface through team workspace APIs and Hub previews
- teams can now run a coordinated multi-agent response that writes a shared summary into the team workspace
- a first GitHub-owned output path now exists: workspace text can be exported into a connected GitHub repository through the backend
- runtime bootstrap correctness tightened: default agents now seed in `provisioning`, runtime lease metadata now uses formal SQL naming conventions, and running leases stamp `started_at` consistently across providers
- teams can now run a dedicated huddle that writes a shared plan into the workspace and creates explicit owned per-agent tasks
- normal team execution now consumes open task assignments so agents act on aligned work instead of only a shared top-level prompt
- agents now have a first inbox surface through assigned team tasks, and team execution claims tasks with a lease before running them
- task coordination now has a basic audit trail: tasks can be delegated, can accumulate report-back updates, and record completion updates for later review in the UI
- the inbox now supports pull-based work pickup: an agent can claim its next assigned task from the queue and complete it through the task action APIs instead of only waiting for control-plane orchestration
- the runtime path can now execute inbox work directly: an agent can run its next task through Hermes, write completion updates, and return a task-scoped result without a separate team-run wrapper
- the backend now has a scheduler-style inbox cycle primitive: one cycle can sweep a team and run the next claimable task for each agent through Hermes, which is the foundation for a future persistent background poller
- the backend API surface has been refactored out of the monolithic `backend/sutra_backend/api/routes.py` file into domain-specific routers, which should keep the next Phase 1 slices from collapsing back into one oversized module
- an opt-in background inbox poller now exists at app startup: when enabled, it periodically sweeps queued team work using the existing inbox cycle service
- the background inbox poller is now Postgres-backed at the coordination layer: it uses a persisted lease row, bounded sweep capacity, and heartbeat/checkpoint metadata so only one control-plane instance should actively sweep at a time
- poller status is now visible through a backend system route and a small Team Workspace scheduler card so users can tell whether queued team work should be moving automatically
- expired claimed tasks are now reopened automatically when the team inbox is read or swept, which reduces the risk of a single failed run leaving team work stuck in a claimed state
- runtime leases now return an explicit readiness summary instead of only raw lease fields, and the Team Workspace shows readiness for the selected agent runtime before users trigger inbox execution
- the control plane now has a first runtime health-reconciliation pass: stale or degraded runtime leases are probed before being treated as request-ready, and unreachable runtimes are marked explicitly instead of silently trusting stale lease metadata
- first sign-in now tries to provision the default agent runtime when the environment is configured for it, which moves the onboarding path closer to the actual Phase 1 zero-setup promise
- the GitHub-owned output path is now more product-complete: exports return real file/commit destinations, team artifacts can be listed through the control plane, and the Team Workspace shows recent GitHub export history instead of treating export as a one-off backend action
- team execution now consumes the structures we created for alignment: huddle plans, task updates, and recent shared-workspace context are fed back into team and inbox runs so agents act with the shared plan in view instead of only a narrow assignment string
- inbox runtime execution now writes a durable task result back into the shared workspace and the Team Workspace UI follows that artifact automatically, which keeps the shared folder central to team coordination rather than a passive side panel
- task-scoped team messaging now exists on top of the task-update model, so teammates can leave lightweight inter-agent notes on assigned work without replacing huddles and owned tasks as the main coordination structure
- team responses now persist per-agent outputs into the shared workspace in addition to the rolled-up team summary, which makes the shared folder a truer working memory for later runs and exports
- team response APIs now return the generated workspace files explicitly, and follow-up team runs prioritize recent task outputs from the same team context so durable workspace artifacts feed the next run more intentionally
- the single-agent chat surface now prioritizes the current conversation’s generated workspace files and keeps export defaults aligned with the selected output, which makes the ownership path clearer from chat instead of only from the team workspace
- Hermes session continuity is now more explicit in the control plane: single-agent, team, huddle, and inbox runs send stable conversation keys to Hermes `/v1/responses` instead of relying only on ad hoc request chaining, so backend-driven conversations are less stateless than before
- the GCP runtime path now defines an explicit persistent agent-state contract: each agent gets a deterministic state disk, mount paths for `HERMES_HOME` and private volume, and startup-script metadata that mounts persistent storage without writing secrets into runtime-readable env files
- the GCP runtime startup contract now goes one step further: provisioning metadata includes a concrete host bootstrap flow that mounts the persistent state disk, sets `HERMES_HOME` on the mounted filesystem, enables the Hermes API server, and launches `gateway.run` as a managed system service instead of leaving VM boot behavior implicit
- local runtime provisioning can now authenticate to GCP with the checked-in service account file instead of requiring only metadata-server auth or a manually pasted access token, which makes local control-plane-to-GCP testing realistic
- Compute Engine API has been enabled in the current GCP project and a pinned Hermes runtime source bundle has been uploaded to GCS for host bootstrap, so the next infra step can move from cloud-prep into actual tiny-host provisioning

Next on the critical path:

- keep tightening the core Phase 1 loop: onboarding -> agent chat -> persisted history -> GitHub-owned output
- fix user-facing flow gaps before adding new surface area
- keep making the GitHub-owned output loop feel complete from the web app, especially for single-agent flows and clearer end-to-end demos
- deepen inter-agent coordination beyond sequential orchestration so teams can delegate and converge more naturally
- extend the inbox model beyond user-driven task actions so agents can actively pick up, delegate, and report on tasks without the control plane simulating every step
- tighten how shared workspace artifacts feed subsequent agent runs so the team folder behaves more like durable working memory than only a file browser
- move from on-demand inbox execution endpoints toward a persistent background poller or scheduler per agent runtime
- keep the backend poller as the Phase 1 scheduler of record, but continue hardening it with better stuck-task recovery and readiness telemetry before deciding whether to move it into a dedicated worker
- complete runtime bootstrap and stronger runtime health reconciliation so newly provisioned managed agents become request-ready automatically without relying only on lease metadata
- push the runtime reconciliation path beyond HTTP reachability into real managed-runtime readiness once the GCP/Firecracker host layer exists
- turn the new persistent state-disk and mount contract into a fully live hosted runtime path by actually bootstrapping Hermes on that mounted filesystem and proving memory survives restart
- exercise the new host bootstrap on a real low-capacity GCP runtime instance, then verify that a restarted agent still preserves Hermes-side response chain state and filesystem contents
- keep the first real runtime host judicious: one tiny dev instance, explicit cleanup path, and only enough uptime to prove mounted-state and Hermes-session persistence
- deepen agent-to-agent coordination from task context into cleaner inter-agent messaging semantics, but keep huddles plus owned tasks as the primary control structure

## Purpose

This document converts the Phase 1 PRD into an execution-ready work plan.

It is intentionally implementation-oriented, but it does not start implementation. Its job is to:

- break Phase 1 into concrete workstreams
- define the recommended execution order
- identify dependencies and blockers early
- describe what has to exist before the next stage starts
- make infra, backend, frontend, runtime, security, and product delivery work visible as one coordinated program

This plan assumes:

- React + TypeScript for the web UI
- FastAPI for the backend API
- Pydantic for schemas and settings
- SQLModel for persistence models
- Alembic migrations generated from SQLModel metadata
- Hermes remains an upstream runtime submodule with minimal or no code changes

## Phase 1 Outcome We Are Executing Toward

By the end of Phase 1, Sutra should support:

- Google sign-in with automatic default-agent provisioning
- a web-first experience for chatting with a single persistent agent or a persistent team
- a team huddle step that aligns roles and writes an explicit shared plan before deeper execution
- one Firecracker microVM per persistent agent
- one private `HERMES_HOME` and persistent volume per agent
- a shared team workspace mounted across team agents
- full web-relevant Hermes power by default
- GitHub ownership of generated code
- encrypted secret vaulting with runtime env injection
- mobile-usable visibility into agent behavior and shared outputs
- explicit task assignment so each team agent can act on owned work, not just a shared top-level prompt

## Execution Principles

- Build vertical slices on top of a stable platform foundation.
- Do not expose Hermes directly to the browser.
- Treat Sutra control-plane concerns as first-class product work, not glue code.
- Preserve Hermes as an upstream runtime whenever possible.
- Favor reversible infrastructure and schema decisions early.
- Ship observability before scale.
- Keep beta scope broad in capability, but narrow in supported channels.

## Recommended Workstream Order

Execution should proceed in this order:

1. Program setup and repo bootstrap
2. Infra and platform foundation
3. Backend application foundation
4. Runtime orchestration and Hermes bridge
5. Frontend application foundation
6. Vertical feature slices
7. Security hardening and operational maturity
8. Beta launch preparation

Parallel work is possible, but runtime and product slices should not get far ahead of infra, auth, schema, and provisioning fundamentals.

## Workstream 0: Program Setup and Repo Bootstrap

### Objective

Turn the repo from a planning-only repo into an implementation-ready workspace.

### Tasks

- Freeze the current PRD as the execution baseline.
- Decide the initial monorepo layout for:
  - `backend/app` for FastAPI
  - `frontend/src` for the React app
  - `infra/` for provisioning and environment assets
  - `scripts/` for local dev and deployment helpers
- Define the local developer workflow:
  - how backend runs
  - how frontend runs
  - how migrations run
  - how tests run
  - how runtime emulation works locally before real infra exists
- Define environment file conventions:
  - local dev
  - staging
  - production
- Add a short architecture index document that maps PRD sections to implementation areas.

### Deliverables

- agreed repo layout
- local dev conventions
- environment naming conventions
- architecture index

### Exit criteria

- an engineer can open the repo and know where each system belongs
- execution order is unambiguous
- local vs staging vs production configuration boundaries are clear

## Workstream 1: Infra and Platform Foundation

### Objective

Provision the cloud foundation that makes multi-tenant persistent agents possible.

### Substream 1A: Cloud accounts and identity

#### Tasks

- Create or verify GCP project structure for Sutra.
- Create deployment service accounts for:
  - Cloud Run control plane
  - runtime provisioner
  - VM host management
  - GCS access
- Validate Firebase project and Google OAuth setup.
- Validate Neon Postgres provisioning and network access policy.
- Confirm GCS bucket structure for artifacts and runtime-adjacent blobs.

#### Deliverables

- GCP projects and service accounts
- Firebase auth project
- Neon database instance
- GCS bucket(s)

### Substream 1B: Runtime infrastructure

#### Tasks

- Design the Firecracker host strategy on GCP Compute Engine.
- Choose the VM host image, orchestration approach, and lifecycle control mechanism.
- Define how a new persistent agent gets:
  - a microVM
  - a private volume
  - a dedicated `HERMES_HOME`
  - access to the shared team workspace if applicable
- Define host-level networking and internal-only exposure for Hermes API server.
- Define start / stop / restart / health-check flows.
- Define how runtime leases and host capacity are tracked.

#### Deliverables

- Firecracker host architecture
- runtime provisioning flow
- agent volume model
- runtime health model

### Substream 1C: Shared services and secrets

#### Tasks

- Finalize required env and secret inventory.
- Add missing managed-provider credentials:
  - `BROWSERBASE_API_KEY`
  - `BROWSERBASE_PROJECT_ID`
  - or `BROWSER_USE_API_KEY`
  - primary LLM provider creds such as `OPENROUTER_API_KEY`
  - `GITHUB_APP_ID`
  - `GITHUB_APP_PRIVATE_KEY`
  - `GITHUB_WEBHOOK_SECRET`
  - optional `FAL_KEY`
  - optional `HONCHO_BASE_URL`
- Decide which secrets live in:
  - environment config
  - GCP secret manager or equivalent operational storage
  - encrypted user secret vault in Neon
- Define runtime bootstrap config generation per agent.

#### Deliverables

- full env inventory
- secret storage policy
- runtime config generation strategy

### Exit criteria

- staging infra can host the control plane
- a runtime host strategy exists and is documented
- secrets and provider dependencies are accounted for

## Workstream 2: Backend Application Foundation

### Objective

Create the FastAPI control plane that owns auth, tenancy, orchestration, streaming, and persistence.

### Substream 2A: Backend app skeleton

#### Tasks

- Scaffold the FastAPI app.
- Set up Pydantic settings models for environment configuration.
- Define the app package structure:
  - API routers
  - domain services
  - models
  - runtime adapters
  - integrations
  - background jobs
- Add health endpoints and environment validation.

#### Deliverables

- FastAPI app skeleton
- settings system
- base router structure

### Substream 2B: Persistence foundation

#### Tasks

- Define SQLModel models for the Phase 1 entities:
  - `User`
  - `Team`
  - `RoleTemplate`
  - `Agent`
  - `Conversation`
  - `Message`
  - `ToolEvent`
  - `Artifact`
  - `SharedWorkspaceItem`
  - `Secret`
  - `GitHubConnection`
  - `AutomationJob`
  - `RuntimeLease`
- Configure Alembic against SQLModel metadata.
- Generate the initial migration set from the SQLModel models.
- Set naming conventions for constraints and indexes to keep migration diffs stable.
- Add seed data strategy for role templates and system defaults.

#### Deliverables

- SQLModel entity layer
- initial Alembic migrations
- seed strategy

### Substream 2C: Auth and tenancy

#### Tasks

- Implement Firebase token verification in FastAPI.
- Map Firebase identity to Sutra `User` records.
- Define tenant ownership checks for teams, agents, conversations, secrets, jobs, and GitHub connections.
- Add backend auth middleware and ownership guards.

#### Deliverables

- auth integration
- identity-to-user mapping
- tenancy guardrails

### Substream 2D: API surface

#### Tasks

- Define Pydantic request/response schemas for:
  - auth/session
  - teams
  - agents
  - conversations
  - secrets
  - GitHub connect
  - jobs
  - workspace/artifacts
- Implement initial REST surfaces from the PRD.
- Define consistent error envelopes and status codes.

#### Deliverables

- stable API contracts
- documented backend surface

### Exit criteria

- backend boots in local dev and staging
- migrations run successfully
- auth works end to end
- core API contracts are defined and testable

## Workstream 3: Runtime Orchestration and Hermes Bridge

### Objective

Create the Sutra-owned layer that provisions persistent Hermes runtimes and safely translates Sutra requests into Hermes runtime calls.

### Substream 3A: Runtime bootstrap

#### Tasks

- Define how an agent runtime is created from backend state.
- Create the runtime bootstrap sequence:
  - allocate or assign host capacity
  - create agent-private volume
  - create shared workspace mount if needed
  - generate `HERMES_HOME`
  - generate runtime env vars
  - start Hermes with API server enabled internally only
- Define cleanup and reconciliation behavior for failed boots.

#### Deliverables

- runtime bootstrap spec
- provisioning and recovery logic spec

### Substream 3B: Hermes request adapter

#### Tasks

- Implement a backend adapter that calls Hermes `/v1/responses` as the primary protocol.
- Keep `/v1/chat/completions` as a compatibility path, but do not make it the normal product path.
- Define how Sutra conversation IDs map to Hermes response chains.
- Define how agent identity, role prompt, and ephemeral control-plane instructions are layered into each run.

#### Deliverables

- Hermes API adapter
- conversation chain mapping
- prompt layering strategy

### Substream 3C: Event streaming

#### Tasks

- Design the Sutra-owned streaming event envelope.
- Translate Hermes output into frontend-friendly events:
  - assistant delta
  - tool start
  - tool update
  - tool complete
  - runtime state
  - inter-agent handoff
  - artifact created
  - final completion
  - failure
- Decide whether browser streaming uses SSE or WebSocket at the Sutra layer.
- Add persistence strategy for event summaries vs full raw event history.

#### Deliverables

- streaming protocol
- event adapter
- event persistence policy

### Substream 3D: Runtime operations

#### Tasks

- Implement runtime health checks and heartbeats.
- Implement restart, stop, and resume behavior.
- Define idle behavior and capacity reclamation without losing persistent state.
- Define failure-handling paths for:
  - host unavailable
  - agent runtime crash
  - Hermes API server unavailable
  - volume mount failure

#### Deliverables

- runtime operations interface
- lease state machine
- failure-recovery logic

### Exit criteria

- backend can talk to a provisioned runtime reliably
- conversation requests can be routed to the right runtime
- runtime state and failure states are observable

## Workstream 4: Frontend Application Foundation

### Objective

Create the React application shell and reusable UI primitives that will host all Phase 1 workflows.

### Substream 4A: Frontend scaffold

#### Tasks

- Scaffold the React + TypeScript app.
- Choose and wire core frontend plumbing:
  - routing
  - remote data fetching
  - auth session management
  - streaming state handling
- Preserve the existing Tailwind tokens and design direction.
- Add base layout primitives and typography system.

#### Recommended assumptions

- Use a client-rendered React app.
- Use React Router for app routing.
- Use TanStack Query or equivalent for server-state management.
- Keep styling in Tailwind plus light component-level CSS where necessary.

### Substream 4B: Global application shell

#### Tasks

- Implement auth gate and signed-in shell.
- Implement Hub layout skeleton.
- Add responsive navigation model for desktop and mobile.
- Add app-wide error, loading, and empty states.

### Substream 4C: Shared UI components

#### Tasks

- Implement design-system-aligned primitives for:
  - buttons
  - inputs
  - cards
  - section headers
  - status indicators
  - lists
  - side panels
  - event timeline rows
  - message bubbles
  - code and artifact previews

### Exit criteria

- frontend boots locally
- design system is preserved
- app shell is ready for vertical slices

## Workstream 5: Vertical Feature Slices

### Objective

Build Phase 1 as user-visible slices rather than as disconnected subsystems.

## Slice 5A: Auth + onboarding + default agent

### Tasks

- Sign-in flow with Firebase
- first-user bootstrap
- default agent creation
- Hub entry state
- first chat launch path

### Exit criteria

- new user can sign in and talk to a default agent without setup

## Slice 5B: Single-agent chat canvas

### Tasks

- conversation creation
- streaming chat
- assistant text deltas
- tool activity timeline
- interrupt / retry / error handling
- artifact panel wiring

### Exit criteria

- a single persistent agent can complete tasks through the web UI

## Slice 5C: Persistent teams and agent assembly

### Tasks

- role templates
- team creation
- Agent Assembly UI
- persistent team-member runtimes
- team conversation routing
- inter-agent event rendering

### Exit criteria

- users can create and use a persistent multi-agent team

## Slice 5D: Shared workspace and artifacts

### Tasks

- shared workspace browser
- artifact listing and previews
- provenance links from conversations to outputs
- Artifact View page

### Exit criteria

- user can see and inspect outputs across conversations and agents

## Slice 5E: GitHub integration

### Tasks

- GitHub App setup
- GitHub install/connect UI
- repo selection
- backend install-token handling
- runtime credential injection
- repo-attachment model
- artifact-to-GitHub traceability

### Exit criteria

- agents can write code into user-owned GitHub repos

## Slice 5F: Secret vault

### Tasks

- secret create/list/delete UI
- encrypted storage in Neon
- scope binding
- backend secret injection policy
- redaction-safe event and transcript handling

### Exit criteria

- secrets can be used by agents without appearing in model context or UI logs

## Slice 5G: Automations / cron

### Tasks

- job create/edit/list/run UI
- backend job APIs
- runtime scheduling integration
- job result linking back into the web experience

### Exit criteria

- users can create and observe scheduled agent work from the web app

## Workstream 6: Security, Privacy, and Compliance Hardening

### Objective

Harden the system to the point where closed beta users can be invited safely.

### Tasks

- enforce backend-only proxying to Hermes
- finalize secret encryption and rotation policy
- finalize redaction strategy for:
  - logs
  - tool events
  - transcripts
  - API errors
- implement runtime-level access controls
- implement API rate limiting
- implement audit trails for:
  - secret usage
  - GitHub actions
  - runtime lifecycle actions
- define network egress policy for runtimes if needed
- define incident/debug playbooks

### Exit criteria

- security-sensitive actions are auditable
- secret handling is verified
- runtime isolation assumptions are tested, not just documented

## Workstream 7: Testing and Quality Gates

### Objective

Put reliable verification around a system that spans product, infra, orchestration, and external providers.

### Test layers

#### Backend

- unit tests for services and validators
- API contract tests
- auth and tenancy tests
- migration tests

#### Runtime orchestration

- provisioning tests
- health-check tests
- runtime restart and recovery tests
- secret injection tests
- GitHub token injection tests

#### Frontend

- component tests
- auth flow tests
- conversation streaming tests
- mobile layout tests

#### End-to-end

- new user onboarding
- default agent task
- team creation and use
- shared workspace visibility
- GitHub-backed coding workflow
- secret-safe external integration task
- scheduled job workflow

### Exit criteria

- every major product promise has at least one automated or scripted verification path
- staging behaves close enough to production to be trusted for beta sign-off

## Workstream 8: Observability and Operations

### Objective

Make the system diagnosable before scale or beta.

### Tasks

- centralized backend logging
- runtime host logging
- per-agent runtime health metrics
- stream/event error tracking
- provisioning success/failure dashboards
- GitHub integration error reporting
- browser-provider failure reporting
- cron job success/failure tracking

### Exit criteria

- on-call debugging for runtime failures is realistic
- provisioning and task failures are visible without SSHing blindly into hosts

## Workstream 9: Closed Beta Launch Readiness

### Objective

Finish the minimum operational and product work needed to onboard the first real users.

### Tasks

- create a staging-to-production promotion checklist
- finalize seeded role templates
- finalize onboarding copy
- finalize support/debug instructions
- finalize backup and restore policy for:
  - Postgres
  - runtime volumes
  - artifacts
- prepare a closed beta invite process
- define beta usage limits if needed

### Exit criteria

- a real user can be onboarded safely
- the team can diagnose failures quickly
- recovery paths exist for data and runtime failures

## Cross-Workstream Dependencies

### Must happen before most product work

- infra and secret inventory
- backend app skeleton
- SQLModel models and migrations
- auth integration

### Must happen before real chat UX is finished

- Hermes bridge
- streaming adapter
- runtime bootstrap

### Must happen before coding workflows

- shared workspace model
- GitHub App integration
- runtime credential injection

### Must happen before beta

- secret redaction verification
- runtime restart and recovery verification
- observability
- E2E validation of the core user journeys

## Suggested Milestones

### Milestone 1: Execution foundation

- repo layout
- FastAPI skeleton
- React skeleton
- SQLModel entities
- Alembic baseline
- Firebase auth verification

### Milestone 2: Runtime bridge

- one runtime provisioned
- backend can talk to Hermes `/v1/responses`
- browser can see streamed assistant output

### Milestone 3: Single-agent MVP

- onboarding
- Hub
- Chat Canvas
- artifact panel

### Milestone 4: Persistent team MVP

- Agent Assembly
- multiple runtimes
- shared workspace
- team conversation orchestration

### Milestone 5: Ownership and safety

- secret vault
- GitHub App
- repo workflows
- audit trail foundations

### Milestone 6: Automation and beta hardening

- cron UI and APIs
- mobile polish
- observability
- launch checklist complete

## Known Open Decisions to Confirm During Review

These do not block writing code later, but they should be explicitly signed off before implementation starts:

- exact runtime host orchestration strategy for Firecracker on GCP
- frontend bundling/deployment shape under Cloud Run
- whether browser streaming to the web client uses SSE or WebSockets
- exact local-development emulation path for agent runtimes before full infra exists
- whether image generation is in the first beta surface or only runtime-capable but UI-hidden
- whether Honcho is enabled in staging from day one or added later

## First Implementation Batch After Review

Once this plan is approved, the recommended first implementation batch is:

1. repo bootstrap and backend/frontend scaffolds
2. SQLModel entities and Alembic setup
3. Firebase auth verification in FastAPI
4. basic React shell and auth flow
5. runtime bootstrap stub plus local dev adapter
6. Hermes `/v1/responses` backend adapter

No work beyond this plan should begin until the review is complete.
