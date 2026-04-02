export type AgentChatRouteOptions = {
  conversationId?: string;
  prompt?: string;
  newConversation?: boolean;
};

export function buildAgentChatHref(
  agentId: string,
  options: AgentChatRouteOptions = {},
): string {
  const params = new URLSearchParams();
  if (options.conversationId) {
    params.set("conversationId", options.conversationId);
  }
  if (options.prompt) {
    params.set("prompt", options.prompt);
  }
  if (options.newConversation) {
    params.set("new", "1");
  }

  const query = params.toString();
  return query ? `/agents/${agentId}?${query}` : `/agents/${agentId}`;
}

export function readAgentChatParams(searchParams: URLSearchParams): AgentChatRouteOptions {
  const conversationId = searchParams.get("conversationId") ?? undefined;
  const prompt = searchParams.get("prompt") ?? undefined;
  const newConversation = searchParams.get("new") === "1";
  return { conversationId, prompt, newConversation };
}
