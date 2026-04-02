# E2E QA Notes

Status: Active  
Last Updated: 2026-04-02

## Scope

This log captures issues found during end-to-end QA so they are not lost while we focus on functional fixes first.

## Functional Bugs

- Fixed: static-dev runtime leases could keep a stale API base URL when the local runtime port changed, leaving chat and runtime cards permanently "unreachable" even after the runtime was healthy again.
- Fixed: runtime status routes could continue showing a stale provider lease from a previous environment (for example, an old GCP-style lease while the app was running in `static_dev`), which poisoned local QA until the user manually reprovisioned.
- Fixed: hub "new chat" flows could silently reuse the latest existing conversation instead of starting a fresh thread, which made the app feel nondeterministic and could leak old context into a supposedly new chat.
- Fixed: creating a new team could leave all team agents cold until the first user action hit runtime provisioning. Team creation now pre-provisions those runtimes when runtime settings are available so a new team is closer to "ready on arrival."
- Open: local `static_dev` team runs with Honcho enabled are still using the fallback Hermes Honcho identity (`workspace: hermes`, session `hermes-agent`) instead of an agent-scoped configuration. In practice this causes cross-agent memory bleed and role confusion during huddles, so local Honcho behavior is not a trustworthy proxy for the managed Firecracker path yet.
- Verified: the hosted-runtime topology now works end to end with local frontend/backend and Hermes on the GCP host. Personal-agent chat, hosted team creation, huddles, inbox-cycle execution, automation save, and automation run all completed successfully against `gcp_firecracker`.
- Open: hosted `Run Inbox Cycle` executes tasks in team-agent order and auto-completes each task after a single model response, even when the response is clearly blocked on an unmet prerequisite. In the QA run, the Researcher/Verifier task completed before the Builder/Writer task produced the note, which means the cycle can report success while the actual handoff semantics are still broken.
- Open: hosted automation runs inherit the same coordination flaw. A single automation run produced contradictory summaries because different agents reasoned over different execution moments of the same workflow, and the final team summary blended those inconsistent states instead of reconciling them.

## UX / UI Issues

- Runtime cards expose internal readiness states like `api_reachable` and `provisioning` directly. These are useful for developers, but they read as implementation jargon for non-technical users.
- The chat page initially renders a brief placeholder state (`Runtime status not loaded yet.`, `Provider UNKNOWN`, `RUNTIME NOT PROVISIONED`) before settling. Even when it self-corrects, the flicker makes the app feel less reliable.
- Missing `favicon.ico` still produces a browser 404 noise on every page load.
- The home screen loads in visible stages, with key sections appearing after the shell renders. Even when data arrives quickly, the page feels unstable before it settles.
- Team and workspace previews on the hub emphasize raw file paths like `README.md`, `artifacts/`, and `conversations/...md`, which is low-signal for non-technical users trying to understand what happened.
- Recent conversation previews can degrade to a generic `Conversation` label instead of showing a useful snippet or a clear task summary.
- Team creation currently defaults the name field to `Launch Crew`, which increases the risk of repetitive or confusing team naming if users move quickly through the form.
- Team huddles currently block for multiple minutes with a single `Running Huddle...` state and no per-agent progress, so the product feels frozen during one of its most important collaborative flows.
- Team task cards dump almost the full markdown instruction into a clickable card, which turns the task list into a wall of text instead of a scannable queue.
- `Run Inbox Cycle` is similarly opaque: it can spend several minutes in `Cycling...`, with partial task completion happening in the backend while the UI exposes no progress, no completed-count feedback, and no per-agent state changes.
- Intermittent Hermes retries (`Invalid API response: response.content is empty`) add extra latency to team runs, but the UI gives the user no hint that the system is retrying rather than fully stuck.
- Hosted team runs are still far too slow for a reassuring consumer product feel. The three-agent huddle, inbox cycle, automation run, and even `Verify Runtime` all behave like long-running jobs, but the UI mostly presents them as ordinary button clicks without progress, ETA, or agent-by-agent status.
- Automation run results are hard to parse. The page drops a large, unlabeled block of generated text into the main workspace area while also adding four new output files, which makes it unclear what just finished, what artifact is canonical, and what the user should read first.
- Hosted run output quality currently feels repetitive and over-explained. The automation summary repeated overlapping blocker analyses from multiple agents instead of synthesizing a crisp single answer, which will feel noisy and confusing to non-technical users.
