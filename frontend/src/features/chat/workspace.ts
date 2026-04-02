import type { SharedWorkspaceItem } from "../../lib/api.generated";

export function listAgentConversationWorkspaceItems(
  items: SharedWorkspaceItem[],
  {
    conversationId,
    agentId,
  }: {
    conversationId: string | undefined;
    agentId: string;
  },
): SharedWorkspaceItem[] {
  if (!conversationId) {
    return [];
  }

  return [...items]
    .filter((item) => item.conversation_id === conversationId && item.agent_id === agentId)
    .sort((left, right) => right.updated_at.localeCompare(left.updated_at));
}

export function buildWorkspaceExportPath(
  item: SharedWorkspaceItem | null | undefined,
  fallback = "app/agent-output.md",
): string {
  if (!item?.path) {
    return fallback;
  }
  return `app/${item.path.replace(/^\/+/, "")}`;
}
