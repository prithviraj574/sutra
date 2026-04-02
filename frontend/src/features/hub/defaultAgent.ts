import type { Agent, Team } from "../../lib/api.generated";

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
    agents.find((agent) => agent.team_ids.some((teamId) => personalTeamIds.has(teamId))) ??
    agents.find((agent) => agent.status === "ready") ??
    agents[0]
  );
}
