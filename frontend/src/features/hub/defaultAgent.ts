import type { Agent, Team } from "../../lib/api";

export function pickDefaultAgent(
  agents: Agent[],
  teams: Team[],
): Agent | null {
  if (agents.length === 0) {
    return null;
  }

  const personalTeamIds = new Set(
    teams.filter((team) => team.mode === "personal").map((team) => team.id),
  );

  return (
    agents.find((agent) => personalTeamIds.has(agent.team_id)) ??
    agents.find((agent) => agent.status === "ready") ??
    agents[0]
  );
}
