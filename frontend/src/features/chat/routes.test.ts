import { describe, expect, it } from "vitest";

import { buildAgentChatHref, readAgentChatParams } from "./routes";

describe("agent chat routes", () => {
  it("builds the default agent chat path without query params", () => {
    expect(buildAgentChatHref("agent-1")).toBe("/agents/agent-1");
  });

  it("builds a chat path with prompt and conversation id", () => {
    expect(
      buildAgentChatHref("agent-1", {
        conversationId: "conversation-1",
        prompt: "Build a dashboard",
      }),
    ).toBe("/agents/agent-1?conversationId=conversation-1&prompt=Build+a+dashboard");
  });

  it("reads chat params from the current url", () => {
    const params = new URLSearchParams("conversationId=conversation-1&prompt=Build+a+dashboard");
    expect(readAgentChatParams(params)).toEqual({
      conversationId: "conversation-1",
      prompt: "Build a dashboard",
    });
  });
});
