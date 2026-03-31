import { describe, expect, it } from "vitest";

import type { SharedWorkspaceItem } from "../../lib/api";
import { buildWorkspaceExportPath, listAgentConversationWorkspaceItems } from "./workspace";

const items: SharedWorkspaceItem[] = [
  {
    id: "item-1",
    team_id: "team-1",
    path: "conversations/conversation-1.md",
    kind: "file",
    content_text: "Older output",
    conversation_id: "conversation-1",
    agent_id: "agent-1",
    created_at: "2026-03-31T09:00:00Z",
    updated_at: "2026-03-31T09:01:00Z",
  },
  {
    id: "item-2",
    team_id: "team-1",
    path: "conversations/conversation-1-followup.md",
    kind: "file",
    content_text: "Latest output",
    conversation_id: "conversation-1",
    agent_id: "agent-1",
    created_at: "2026-03-31T09:02:00Z",
    updated_at: "2026-03-31T09:03:00Z",
  },
  {
    id: "item-3",
    team_id: "team-1",
    path: "conversations/conversation-1-other-agent.md",
    kind: "file",
    content_text: "Another agent output",
    conversation_id: "conversation-1",
    agent_id: "agent-2",
    created_at: "2026-03-31T09:02:00Z",
    updated_at: "2026-03-31T09:04:00Z",
  },
];

describe("chat workspace helpers", () => {
  it("lists current conversation items for the selected agent in newest-first order", () => {
    expect(
      listAgentConversationWorkspaceItems(items, {
        conversationId: "conversation-1",
        agentId: "agent-1",
      }).map((item) => item.id),
    ).toEqual(["item-2", "item-1"]);
  });

  it("returns an export path derived from the workspace item path", () => {
    expect(buildWorkspaceExportPath(items[0])).toBe("app/conversations/conversation-1.md");
    expect(buildWorkspaceExportPath(undefined)).toBe("app/agent-output.md");
  });
});
