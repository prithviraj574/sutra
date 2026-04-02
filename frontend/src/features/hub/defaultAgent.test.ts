import { describe, expect, it } from "vitest";

import type { Agent, Team } from "../../lib/api.generated";
import { pickDefaultAgent } from "./defaultAgent";

function buildTeam(overrides: Partial<Team>): Team {
  return {
    id: "team-1",
    user_id: "user-1",
    name: "Team",
    mode: "team",
    created_at: "2026-04-01T00:00:00Z",
    updated_at: "2026-04-01T00:00:00Z",
    ...overrides,
  };
}

function buildAgent(overrides: Partial<Agent>): Agent {
  return {
    id: "agent-1",
    user_id: "user-1",
    team_ids: ["team-1"],
    name: "Agent",
    role_name: "Generalist",
    status: "provisioning",
    runtime_kind: "firecracker",
    shared_workspace_enabled: true,
    created_at: "2026-04-01T00:00:00Z",
    updated_at: "2026-04-01T00:00:00Z",
    ...overrides,
  };
}

describe("pickDefaultAgent", () => {
  it("prefers the personal workspace agent", () => {
    const teams = [
      buildTeam({ id: "team-team", mode: "team" }),
      buildTeam({ id: "team-personal", mode: "personal" }),
    ];
    const agents = [
      buildAgent({ id: "agent-team", team_ids: ["team-team"], status: "ready" }),
      buildAgent({ id: "agent-personal", team_ids: ["team-personal"], status: "provisioning" }),
    ];

    expect(pickDefaultAgent(agents, teams)?.id).toBe("agent-personal");
  });

  it("falls back to a ready agent when no personal workspace exists", () => {
    const teams = [buildTeam({ id: "team-team", mode: "team" })];
    const agents = [
      buildAgent({ id: "agent-pending", team_ids: ["team-team"], status: "provisioning" }),
      buildAgent({ id: "agent-ready", team_ids: ["team-team"], status: "ready" }),
    ];

    expect(pickDefaultAgent(agents, teams)?.id).toBe("agent-ready");
  });
});
