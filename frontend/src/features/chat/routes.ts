export type AgentChatRouteOptions = {
  conversationId?: string;
  prompt?: string;
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

  const query = params.toString();
  return query ? `/agents/${agentId}?${query}` : `/agents/${agentId}`;
}

export function readAgentChatParams(searchParams: URLSearchParams): AgentChatRouteOptions {
  const conversationId = searchParams.get("conversationId") ?? undefined;
  const prompt = searchParams.get("prompt") ?? undefined;
  return { conversationId, prompt };
}
