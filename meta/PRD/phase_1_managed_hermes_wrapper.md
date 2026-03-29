# Sutra Phase 1 PRD: Managed Hermes Wrapper

Status: Draft  
Owner: Sutra  
Phase: Phase 1 MVP / Closed Beta

## 1. Product Thesis

Sutra exists to turn Hermes from a powerful single-user agent runtime into a product that non-technical users can actually use every day from the web.

The product is not "another chat UI for an LLM." It is a managed, multi-tenant operating layer around Hermes that gives users:

- zero-setup onboarding
- persistent personal agents and agent teams
- private state and memory per agent
- shared collaboration spaces across teams
- full-capability execution from a safe hosted environment
- ownership of outputs through GitHub and downloadable artifacts

Sutra should feel calm, legible, and controlled on the surface while remaining extremely powerful underneath. The user should feel they are directing capable digital teammates, not poking at a black-box chatbot.

This PRD is grounded in:

- [`meta/VISION.md`](/Users/prithviraj/Desktop/Misc/sutra/meta/VISION.md)
- [`meta/roadmap/PHASE_1.md`](/Users/prithviraj/Desktop/Misc/sutra/meta/roadmap/PHASE_1.md)
- [`frontend/DESIGN.md`](/Users/prithviraj/Desktop/Misc/sutra/frontend/DESIGN.md)
- [`frontend/globals.css`](/Users/prithviraj/Desktop/Misc/sutra/frontend/globals.css)
- [`frontend/tailwind.config.js`](/Users/prithviraj/Desktop/Misc/sutra/frontend/tailwind.config.js)
- [`backend/hermes-agent/.plans/openai-api-server.md`](/Users/prithviraj/Desktop/Misc/sutra/backend/hermes-agent/.plans/openai-api-server.md)
- [`backend/hermes-agent/gateway/platforms/api_server.py`](/Users/prithviraj/Desktop/Misc/sutra/backend/hermes-agent/gateway/platforms/api_server.py)

## 2. Target User and Why Managed Hermes Matters

### Target user

Phase 1 is for a motivated but not deeply technical user who wants AI to complete real tasks without local setup. The first users can still be founder-operator types, but the experience must be usable by friends and family, not only by agent power users.

### User problem

Raw Hermes is powerful, but it assumes a user who can:

- run a CLI
- manage API keys
- configure terminal/browser/tool backends
- reason about safety tradeoffs
- understand local persistence and runtime state

That is not acceptable for Sutra Phase 1.

### Why managed Hermes

Sutra creates product value by owning everything Hermes leaves to the user:

- account creation and auth
- runtime provisioning
- secret management
- multi-tenancy
- web UX
- team orchestration
- storage and persistence
- policy, logging, and auditability
- GitHub ownership paths
- mobile-friendly observability

Hermes remains the runtime engine. Sutra is the managed operating layer.

## 3. Phase 1 Goals, Non-Goals, Success Metrics, and Exit Criteria

### Goals

- A user signs in with Google and has a usable default agent without manual setup.
- A user can create a persistent team of named role-based agents.
- Each agent has private state, memory, and a persistent runtime.
- Teams share a common workspace visible in the web UI.
- Users can see what agents are doing while they work.
- Users can connect GitHub and own generated code in their own repos.
- Users can store secrets securely and allow agents to use them without leaking them into model context.
- The product supports a full web-relevant Hermes capability surface by default.
- The web app works on desktop and mobile.

### Non-goals for Phase 1

- Supporting Hermes messaging platforms as user-facing product channels.
- Making Hermes config editing, slash commands, or raw `HERMES_HOME` part of the user-facing experience.
- Supporting arbitrary third-party plugins or arbitrary user-configured MCP servers.
- Promising generalized direct file upload as an MVP feature.
- Shipping voice, STT, TTS, or voice-channel experiences.
- Solving Phase 2 user-to-user A2A or peer network behavior.

### Success metrics

- Time to first successful agent interaction: under 5 minutes from sign-in.
- Time to first default agent provision: under 2 minutes in normal conditions.
- At least one end-to-end coding workflow succeeds: prompt -> artifact -> GitHub commit.
- At least one end-to-end research workflow succeeds: prompt -> research -> document/artifact in shared workspace.
- At least one multi-agent workflow succeeds with visible delegation and collaboration.
- Users can interrupt, resume, and revisit sessions without losing trust in system state.

### Exit criteria

Phase 1 is complete when:

- zero-setup onboarding works
- persistent agents and teams work
- shared team workspace works
- secrets are not leaked to the LLM
- GitHub integration works
- mobile usability is acceptable
- at least one complete real workflow is demonstrated end to end

## 4. UX and Product Experience

## 4.1 Design system and visual direction

The UI will use React + TypeScript with the existing Tailwind-based design tokens and the "Ethereal Minimalism" direction already defined in the frontend docs.

Key visual decisions:

- Typography: `Newsreader`, `Satoshi`, `JetBrains Mono`
- Palette: warm pearl background, strict dark primary, soft surface colors, sunset aura gradient
- Shape: sharp 4px radius
- Depth: no standard shadows; use borders, surface contrast, and aura glow
- Motion: subtle status and activity transitions, not noisy animation

This is not a generic dashboard UI. The product should feel editorial, spacious, and precise.

## 4.2 Core screens

### Hub

Purpose:

- landing experience after sign-in
- overview of active agents, teams, recent sessions, and current runtime state

Must include:

- default "initialize session" entry point
- recent sessions list
- team and agent presence summary
- current runtime health summary
- quick path to create a team

### Chat Canvas

Purpose:

- primary interaction surface for a single agent or a full team

Must include:

- chat feed
- composer
- streaming assistant output
- tool activity timeline
- interrupt / retry controls
- right-side artifact or preview pane on desktop
- mobile tabbed experience between chat and artifact/canvas

### Agent Assembly

Purpose:

- create or edit persistent role-based agents inside a team

Must include:

- role template selection
- role name and description
- editable system prompt override
- tool profile selection
- shared workspace access visibility
- status of each runtime

### Artifact View

Purpose:

- focused, distraction-free environment for outputs generated by agents

Must include:

- rendered artifacts or file previews
- GitHub sync / deployment-adjacent actions
- provenance back to agent/session

## 4.3 Primary user flows

### Flow A: First-run onboarding

1. User signs in with Google via Firebase Auth.
2. Sutra creates a `User` record and provisions a default personal agent.
3. Sutra provisions a runtime lease, a persistent volume, and a dedicated `HERMES_HOME`.
4. User lands on Hub and sees the default agent already available.
5. User enters a prompt and moves into Chat Canvas.

### Flow B: Single-agent work

1. User chooses their default agent.
2. User sends a task.
3. Sutra backend forwards the task to that agent's Hermes API server.
4. UI streams assistant deltas and tool/runtime events.
5. Agent produces files, artifacts, or GitHub changes.
6. User inspects output in Artifact View or shared workspace.

### Flow C: Persistent team creation

1. User chooses "Create Team."
2. User selects a default team template or builds a custom one.
3. Sutra creates named persistent agents, one runtime per role.
4. A shared team workspace is provisioned and mounted for all team agents.
5. User can chat with one agent directly or the team as a whole.

### Flow D: Team execution

1. User sends a task to the team conversation.
2. Sutra routes the request to the designated lead/planner agent.
3. The lead agent can send work to other persistent agents through Sutra's orchestration layer.
4. Each agent executes in its own runtime with private state plus the shared workspace.
5. Inter-agent work, artifacts, and status updates are visible in the UI.

### Flow E: GitHub connection and coding output

1. User connects GitHub via GitHub App install flow.
2. User selects one or more target repos.
3. Sutra stores install metadata, not long-lived raw PATs.
4. When coding tasks run, Sutra injects short-lived GitHub credentials into the runtime.
5. Agent can create files, branch, commit, and push to the user-owned repo.

### Flow F: Secret vault

1. User adds a secret from the web UI.
2. Sutra encrypts it at rest in Neon using `MASTER_ENCRYPTION_KEY`.
3. User binds the secret to an agent, team, or task scope.
4. When the agent runs, the backend injects the secret into the runtime env only for the authorized run.
5. The raw secret never appears in model context, frontend logs, or persistent transcripts.

## 5. Technical Stack Decisions

### Frontend

- React
- TypeScript
- Tailwind CSS with the existing design tokens

React is the required UI framework for Phase 1. The frontend should be implemented as a modern React application, not a server-rendered template stack.

### Backend API

- FastAPI
- Pydantic for request/response schemas and settings validation
- SQLModel for persistence models
- Alembic for schema migrations generated from SQLModel metadata

These are locked decisions for Phase 1. The backend should not use an ad hoc ORM layer or handwritten SQL as the primary persistence contract.

### Infra

- Firebase Auth for Google sign-in
- Neon Postgres as the primary database
- FastAPI service deployed on GCP Cloud Run
- Firecracker microVMs on GCP Compute Engine for runtime isolation
- Google Cloud Volumes for persistent agent storage
- GCS for artifact/blob storage where appropriate

## 6. System Architecture

Sutra has two major planes:

- control plane
- runtime plane

### 6.1 Control plane

The control plane is the Sutra product backend. It owns:

- auth
- tenancy
- API surface for the React app
- DB persistence
- GitHub integration state
- secret vault state
- runtime provisioning orchestration
- routing requests to agent runtimes
- stream fan-out to the web client
- audit and policy enforcement

This runs as the FastAPI backend.

### 6.2 Runtime plane

The runtime plane is made of persistent agent runtimes. Each persistent agent gets:

- one Firecracker microVM
- one dedicated `HERMES_HOME`
- one persistent volume for local Hermes state
- one API server process exposing Hermes internally
- optional mount to a shared team workspace

This keeps Hermes close to its existing single-user assumptions while letting Sutra scale multi-tenant behavior around it.

### 6.3 Shared workspace model

Each team gets a shared workspace mount that all member agents can read and write. This workspace is the canonical place for:

- shared documents
- generated specs
- code artifacts before GitHub sync
- intermediate files
- outputs that should be visible to the user

Each agent also keeps its own private Hermes state and memory.

## 7. Hermes Integration Contract

Hermes remains an upstream runtime dependency, not a heavily modified product core.

### 7.1 Required Hermes interface

Sutra will use Hermes' built-in API server in [`backend/hermes-agent/gateway/platforms/api_server.py`](/Users/prithviraj/Desktop/Misc/sutra/backend/hermes-agent/gateway/platforms/api_server.py).

### 7.2 Primary protocol choice

- Primary: `POST /v1/responses`
- Secondary compatibility: `POST /v1/chat/completions`

`/v1/responses` is the internal primary interface because it supports server-side conversation chaining and preserves tool-call history more cleanly for a managed product.

### 7.3 Browser exposure policy

The browser will never call Hermes directly.

The React app talks only to Sutra's FastAPI backend. The backend proxies to Hermes runtimes and enriches the stream with Sutra-owned state such as:

- runtime status
- agent identity
- inter-agent events
- artifact availability
- GitHub sync state
- policy and audit events

### 7.4 Runtime boot contract

Every persistent agent runtime must:

- have a unique `HERMES_HOME`
- enable Hermes API server on an internal bind only
- use a per-runtime `API_SERVER_KEY`
- disable Hermes messaging-platform surfaces
- mount the agent-private persistent volume
- mount the shared workspace if the agent belongs to a team
- receive Sutra-managed env vars and secrets at runtime

### 7.5 Team behavior

Persistent user-facing teams are a Sutra concept, not a Hermes native concept.

Sutra owns:

- team membership
- role definitions
- agent identity
- inter-agent message routing
- agent lifecycle
- shared workspace coordination

Hermes `delegate_task` remains enabled as an internal power feature inside an agent runtime, but it is not the product's team model.

## 8. Capability Keep / Skip Matrix

## 8.1 Keep in Phase 1

| Capability | Keep | Notes |
|---|---|---|
| API server and streaming responses | Yes | Core runtime contract |
| Terminal and process execution | Yes | Full power by default |
| File editing and patching | Yes | Core coding workflow |
| Web search and extract | Yes | Core research workflow |
| Browser automation | Yes | Use managed cloud browser credentials |
| Vision | Yes | Web-relevant multimodal capability |
| Code execution | Yes | Keep available by default |
| Subagent delegation | Yes | Internal power feature |
| Persistent memory | Yes | Private per-agent memory |
| Session search | Yes | Important for continuity |
| Honcho | Optional | Enabled when configured |
| Cron / scheduled jobs | Yes | Web-managed automation surface |
| GitHub-backed coding workflows | Yes | Core output ownership path |

## 8.2 Skip or hide in Phase 1

| Capability | Decision | Reason |
|---|---|---|
| Telegram / Discord / Slack / Signal / WhatsApp / SMS / email / Matrix / DingTalk | Skip | Sutra is web-only out of the box |
| Home Assistant | Skip | Out of product scope |
| Webhook adapter as user-facing channel | Skip | Not part of initial user experience |
| Voice / STT / TTS | Skip | High complexity, not core to Phase 1 |
| Local Chrome CDP attachment | Skip | Not web-managed and not needed for beta |
| Arbitrary plugins | Skip | Security and product complexity risk |
| Arbitrary MCP server setup | Skip | Security, support, and scope risk |
| Raw slash commands and config editing | Hide | Product abstraction should own UX |
| Direct `HERMES_HOME` exposure | Hide | Product abstraction should own state |
| General direct file upload promise | Skip as MVP promise | Hermes API server does not natively support uploads |

### Clarification on "everything on"

"Everything on" in Phase 1 means all web-relevant Hermes power is enabled by default inside Sutra-managed runtimes. It does not mean every Hermes channel or ecosystem integration appears in the product UI.

## 9. Security, Privacy, and Secret Handling

### 9.1 Security boundary

Sutra's primary security boundary is:

- infrastructure isolation via one microVM per agent
- secret vault storage and scoped env injection
- controlled backend proxying
- per-user tenancy enforcement

The product must not rely on Hermes' local single-user trust assumptions as the main safety model.

### 9.2 Secret storage

Secrets are stored in Neon DB as encrypted payloads using `MASTER_ENCRYPTION_KEY`.

Secrets support at least these scopes:

- user-wide
- team-wide
- agent-specific
- task-specific override

### 9.3 Secret use policy

Secrets are:

- decrypted only server-side
- injected into runtime env only for authorized runs
- not sent to the model in raw form
- not shown in UI after creation
- redacted from logs and event payloads

### 9.4 Runtime safety

Because full-capability execution is enabled by default:

- every agent must run in its own isolated microVM
- runtime kill, restart, and health checks must be first-class operations
- all tool activity must be auditable
- command execution history and artifact provenance must be visible in the UI

### 9.5 PII and transcript handling

Sutra should preserve useful transcripts and event history, but never store raw sensitive values in the transcript model. Secret values and protected credential material must be excluded or redacted before persistence.

## 10. Data Model and Service Interfaces

## 10.1 Core entities

The backend will use SQLModel models for persistence and Pydantic models for API contracts.

Minimum Phase 1 entities:

### `User`

- `id`
- `firebase_uid`
- `email`
- `display_name`
- `photo_url`
- `created_at`

### `Team`

- `id`
- `user_id`
- `name`
- `description`
- `mode` (`personal`, `team`)
- `shared_workspace_uri`
- `created_at`

### `RoleTemplate`

- `id`
- `key`
- `name`
- `description`
- `default_system_prompt`
- `default_tool_profile`

### `Agent`

- `id`
- `team_id`
- `role_template_id`
- `name`
- `role_name`
- `status`
- `runtime_kind`
- `hermes_home_uri`
- `private_volume_uri`
- `shared_workspace_enabled`
- `created_at`

### `Conversation`

- `id`
- `team_id`
- `agent_id` nullable
- `mode` (`single_agent`, `team`)
- `latest_response_id`
- `status`
- `created_at`

### `Message`

- `id`
- `conversation_id`
- `actor_type` (`user`, `agent`, `system`)
- `actor_id`
- `content`
- `response_chain_id`
- `created_at`

### `ToolEvent`

- `id`
- `conversation_id`
- `agent_id`
- `message_id`
- `tool_name`
- `event_type`
- `summary`
- `payload_excerpt`
- `started_at`
- `ended_at`

### `Artifact`

- `id`
- `team_id`
- `conversation_id`
- `agent_id`
- `name`
- `kind`
- `uri`
- `mime_type`
- `preview_uri`
- `github_repo`
- `github_branch`
- `github_sha`
- `created_at`

### `SharedWorkspaceItem`

- `id`
- `team_id`
- `path`
- `kind`
- `size_bytes`
- `updated_at`

### `Secret`

- `id`
- `user_id`
- `team_id` nullable
- `agent_id` nullable
- `name`
- `provider`
- `scope`
- `encrypted_value`
- `last_used_at`
- `created_at`

### `GitHubConnection`

- `id`
- `user_id`
- `installation_id`
- `account_login`
- `account_type`
- `connected_at`

### `AutomationJob`

- `id`
- `team_id`
- `agent_id` nullable
- `name`
- `schedule`
- `prompt`
- `enabled`
- `last_run_at`
- `next_run_at`

### `RuntimeLease`

- `id`
- `agent_id`
- `vm_id`
- `state`
- `api_base_url`
- `last_heartbeat_at`
- `started_at`

## 10.2 API surface

The backend will be implemented in FastAPI. Request and response contracts must use Pydantic models. Persistence must use SQLModel. Database migrations must be managed by Alembic generated from SQLModel metadata.

Minimum backend surfaces:

### Auth and session

- `GET /api/me`
- `POST /api/auth/session`

### Teams and agents

- `GET /api/teams`
- `POST /api/teams`
- `GET /api/teams/{team_id}`
- `POST /api/teams/{team_id}/agents`
- `PATCH /api/agents/{agent_id}`
- `POST /api/agents/{agent_id}/restart`

### Conversations

- `GET /api/conversations`
- `POST /api/conversations`
- `GET /api/conversations/{conversation_id}`
- `POST /api/conversations/{conversation_id}/messages`
- `GET /api/conversations/{conversation_id}/stream`

### Artifacts and workspace

- `GET /api/teams/{team_id}/workspace`
- `GET /api/artifacts/{artifact_id}`

### Secrets

- `GET /api/secrets`
- `POST /api/secrets`
- `DELETE /api/secrets/{secret_id}`

### GitHub

- `POST /api/github/connect`
- `GET /api/github/repos`
- `POST /api/github/repos/{repo_id}/attach`

### Automations

- `GET /api/jobs`
- `POST /api/jobs`
- `PATCH /api/jobs/{job_id}`
- `POST /api/jobs/{job_id}/run`

## 10.3 Streaming contract

The browser-facing stream should emit a unified event envelope that can represent:

- assistant text deltas
- tool start / tool update / tool complete
- runtime state change
- agent-to-agent handoff
- artifact created / artifact updated
- final completion
- error

This stream is owned by Sutra, not Hermes. Hermes events are adapted into Sutra's stream contract.

## 11. Backend Implementation Requirements

The backend is explicitly:

- FastAPI for HTTP API
- Pydantic for schemas, validation, and settings
- SQLModel for ORM and persistence models
- Alembic for migrations

### Migration policy

- All persistent models are defined in SQLModel.
- Alembic is configured to autogenerate migrations from SQLModel metadata.
- Schema changes must land with migrations.
- Runtime boot should fail safely if required migrations are missing.

### Settings policy

- Environment-driven configuration should use Pydantic settings models.
- Secrets and env configuration should be validated at startup.
- The backend should distinguish between:
  - required platform env vars
  - optional integrations
  - per-runtime injected values

## 12. Required Environment Additions

Current backend env vars already present:

- `MINIMAX_API_KEY`
- `FIRECRAWL_API_KEY`
- `HONCHO_API_KEY`
- `MASTER_ENCRYPTION_KEY`
- `POSTGRES_URL`
- `FIREBASE_SERVICE_ACCOUNT_JSON`
- `GCS_BUCKET_NAME`
- `GCS_SERVICE_ACCOUNT_JSON`

Additional Phase 1 env vars required:

- `BROWSERBASE_API_KEY`
- `BROWSERBASE_PROJECT_ID`
- or `BROWSER_USE_API_KEY`
- one primary managed LLM credential set such as `OPENROUTER_API_KEY`
- `GITHUB_APP_ID`
- `GITHUB_APP_PRIVATE_KEY`
- `GITHUB_WEBHOOK_SECRET`

Optional env vars:

- `FAL_KEY` if image generation is surfaced in product UI
- `HONCHO_BASE_URL` if self-hosted Honcho is preferred

## 13. Delivery Phases Inside Phase 1

### Phase 1A: Platform foundation

- React web shell
- FastAPI backend
- Firebase auth
- SQLModel data model
- Alembic migrations
- runtime provisioner
- default single-agent onboarding

### Phase 1B: Core agent product

- Chat Canvas
- streaming events
- artifact panel
- shared workspace browser
- runtime restart / interrupt

### Phase 1C: Persistent teams

- Agent Assembly
- team templates
- persistent multi-agent orchestration
- inter-agent event visibility

### Phase 1D: Ownership and secrets

- secret vault
- GitHub App integration
- repo attachment and push workflows

### Phase 1E: Automation and hardening

- cron/automation UI
- audit and provenance improvements
- mobile polish
- closed beta hardening

## 14. Risks and Dependencies

### Risks

- Hermes API server does not natively support direct uploads, which limits MVP upload promises.
- Persistent named multi-agent orchestration is a Sutra-owned feature, not a Hermes primitive.
- Full-power runtimes increase operational and security complexity.
- Firecracker lifecycle management adds infrastructure complexity.
- Browser automation requires vendor credentials and may create cost volatility.
- GitHub write access must be handled with extreme care.

### Dependencies

- Firebase Auth
- Neon Postgres
- GCP Cloud Run
- GCP Compute Engine with Firecracker
- Cloud Volumes
- GCS
- Hermes upstream submodule
- primary managed LLM provider
- Browserbase or Browser Use
- GitHub App
- Firecrawl
- optional Honcho

## 15. Open Operational Assumptions

- Hermes stays upstream and is not deeply forked.
- Any Hermes modifications are optional and limited to observability or upload ergonomics.
- GitHub App is the default integration model, not PAT-first.
- Sutra-owned orchestration is responsible for persistent team semantics.
- Each agent runtime keeps its own private Hermes state forever unless explicitly deleted.
- Shared workspace state persists independently from private agent memory.

## 16. Acceptance Test Plan

### Core onboarding

- New user signs in with Google and sees a ready default agent without setup steps.
- Default agent can answer, use tools, and persist state across restart.

### Persistent teams

- User creates a 3-role team.
- Each role has a dedicated runtime and private memory.
- Team members can read/write the shared workspace.
- Team activity is visible in the UI.

### Coding workflow

- User connects GitHub.
- User asks the team to create or modify code.
- Agent writes files, commits, and pushes to a user-owned repo.
- Result is visible in Artifact View and in GitHub.

### Secret safety

- User adds a secret.
- Agent uses it in a task.
- Raw value never appears in model context, logs, transcript, or UI.

### Streaming and control

- Browser, terminal, and code-execution tasks stream progress live.
- User can interrupt a running task.
- Runtime can be restarted without losing private state.

### Automation

- User creates a scheduled job from the web UI.
- Job runs in a fresh session.
- Output is returned to the web UI and linked to the originating agent/team.

### Mobile

- User can review chats, agent state, and artifacts from mobile.
- Chat and artifact panels remain usable in the mobile layout.

## 17. Final Product Statement

Phase 1 Sutra is a React web application backed by a FastAPI control plane that turns Hermes into a managed multi-tenant cloud product. It gives users persistent personal agents and persistent agent teams, full web-relevant power by default, secure secret handling, GitHub ownership of outputs, and a calm, legible interface that makes powerful autonomous work feel trustworthy and usable.
