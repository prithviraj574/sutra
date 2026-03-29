export type SessionUser = {
  id: string;
  firebase_uid: string;
  email: string;
  display_name?: string | null;
  photo_url?: string | null;
  created_at: string;
  updated_at: string;
};

export type SessionPayload = {
  user: SessionUser;
};

export type Team = {
  id: string;
  user_id: string;
  name: string;
  description?: string | null;
  mode: string;
  shared_workspace_uri?: string | null;
  created_at: string;
  updated_at: string;
};

export type Agent = {
  id: string;
  team_id: string;
  role_template_id?: string | null;
  name: string;
  role_name: string;
  status: string;
  runtime_kind: string;
  hermes_home_uri?: string | null;
  private_volume_uri?: string | null;
  shared_workspace_enabled: boolean;
  created_at: string;
  updated_at: string;
};

export type TeamListPayload = { items: Team[] };
export type AgentListPayload = { items: Agent[] };

export type RuntimeLease = {
  id: string;
  agent_id: string;
  vm_id: string;
  state: string;
  api_base_url?: string | null;
  last_heartbeat_at?: string | null;
  started_at?: string | null;
  created_at: string;
  updated_at: string;
};

export type RuntimeLeasePayload = {
  lease: RuntimeLease;
};

export type Secret = {
  id: string;
  user_id: string;
  team_id?: string | null;
  agent_id?: string | null;
  name: string;
  provider?: string | null;
  scope: string;
  last_used_at?: string | null;
  created_at: string;
  updated_at: string;
};

export type SecretListPayload = {
  items: Secret[];
};

export type SecretCreateInput = {
  name: string;
  value: string;
  provider?: string;
  scope?: string;
};

export type SecretCreatePayload = {
  secret: Secret;
};

export type SecretDeletePayload = {
  id: string;
  deleted: boolean;
};

export type AgentResponseInput = {
  input: string;
  conversation_id?: string;
};

export type AgentResponsePayload = {
  conversation_id: string;
  response_id: string;
  output_text: string;
  raw_response: Record<string, unknown>;
};

export type Conversation = {
  id: string;
  team_id?: string | null;
  agent_id?: string | null;
  mode: string;
  latest_response_id?: string | null;
  status: string;
  created_at: string;
  updated_at: string;
};

export type ChatMessage = {
  id: string;
  conversation_id: string;
  actor_type: "user" | "assistant" | string;
  actor_id?: string | null;
  content: string;
  response_chain_id?: string | null;
  created_at: string;
  updated_at: string;
};

export type ConversationListPayload = { items: Conversation[] };
export type MessageListPayload = { items: ChatMessage[] };

type ApiClientOptions = {
  baseUrl: string;
  getAccessToken: () => Promise<string | null>;
  fetcher?: typeof fetch;
};

export function createApiClient(options: ApiClientOptions) {
  const fetcher = options.fetcher ?? fetch;

  async function request<T>(path: string, init?: RequestInit): Promise<T> {
    const token = await options.getAccessToken();
    const headers = new Headers(init?.headers);
    headers.set("Content-Type", "application/json");
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }

    const response = await fetcher(`${options.baseUrl}${path}`, {
      ...init,
      headers,
    });

    if (!response.ok) {
      const body = await response.json().catch(() => null);
      const detail =
        body && typeof body === "object" && "detail" in body
          ? String((body as { detail: unknown }).detail)
          : `Request failed with ${response.status}`;
      throw new Error(detail);
    }

    return (await response.json()) as T;
  }

  return {
    readSession: () => request<SessionPayload>("/api/auth/me"),
    listTeams: () => request<TeamListPayload>("/api/teams"),
    listAgents: () => request<AgentListPayload>("/api/agents"),
    readAgentRuntime: (agentId: string) =>
      request<RuntimeLeasePayload>(`/api/agents/${agentId}/runtime`),
    provisionAgentRuntime: (agentId: string) =>
      request<RuntimeLeasePayload>(`/api/agents/${agentId}/runtime/provision`, {
        method: "POST",
      }),
    listSecrets: () => request<SecretListPayload>("/api/secrets"),
    createSecret: (payload: SecretCreateInput) =>
      request<SecretCreatePayload>("/api/secrets", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    deleteSecret: (secretId: string) =>
      request<SecretDeletePayload>(`/api/secrets/${secretId}`, {
        method: "DELETE",
      }),
    listAgentConversations: (agentId: string) =>
      request<ConversationListPayload>(`/api/agents/${agentId}/conversations`),
    listConversationMessages: (conversationId: string) =>
      request<MessageListPayload>(`/api/conversations/${conversationId}/messages`),
    createAgentResponse: (agentId: string, payload: AgentResponseInput) =>
      request<AgentResponsePayload>(`/api/agents/${agentId}/responses`, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
  };
}
