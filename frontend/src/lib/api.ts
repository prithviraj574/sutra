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

export type RoleTemplate = {
  id: string;
  key: string;
  name: string;
  description?: string | null;
  default_system_prompt: string;
  default_tool_profile: string;
  created_at: string;
  updated_at: string;
};

export type RoleTemplateListPayload = {
  items: RoleTemplate[];
};

export type TeamCreateInput = {
  name: string;
  description?: string;
  agents: Array<{
    role_template_key: string;
    name?: string;
  }>;
};

export type TeamCreatePayload = {
  team: Team;
  agents: Agent[];
};

export type RuntimeLease = {
  id: string;
  agent_id: string;
  vm_id: string;
  state: string;
  api_base_url?: string | null;
  last_heartbeat_at?: string | null;
  started_at?: string | null;
  ready: boolean;
  heartbeat_fresh: boolean;
  readiness_reason: string;
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

export type PollerLease = {
  id: string;
  name: string;
  owner_id?: string | null;
  state: string;
  last_heartbeat_at?: string | null;
  lease_expires_at?: string | null;
  last_sweep_started_at?: string | null;
  last_sweep_completed_at?: string | null;
  last_executed_count: number;
  created_at: string;
  updated_at: string;
};

export type PollerStatusPayload = {
  enabled: boolean;
  interval_seconds: number;
  lease_seconds: number;
  max_tasks_per_sweep: number;
  is_active: boolean;
  lease?: PollerLease | null;
};

export type GitHubConnection = {
  id: string;
  user_id: string;
  installation_id: string;
  account_login: string;
  account_type: string;
  connected_at: string;
  created_at: string;
  updated_at: string;
};

export type GitHubConnectionStatusPayload = {
  connection: GitHubConnection | null;
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
  workspace_item_id?: string | null;
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
export type TeamConversationListPayload = { items: Conversation[] };

export type SharedWorkspaceItem = {
  id: string;
  team_id: string;
  path: string;
  kind: string;
  size_bytes?: number | null;
  content_text?: string | null;
  conversation_id?: string | null;
  agent_id?: string | null;
  created_at: string;
  updated_at: string;
};

export type TeamWorkspacePayload = {
  team: Team;
  items: SharedWorkspaceItem[];
};

export type Artifact = {
  id: string;
  team_id?: string | null;
  conversation_id?: string | null;
  agent_id?: string | null;
  name: string;
  kind: string;
  uri: string;
  mime_type?: string | null;
  preview_uri?: string | null;
  github_repo?: string | null;
  github_branch?: string | null;
  github_sha?: string | null;
  created_at: string;
  updated_at: string;
};

export type TeamArtifactListPayload = {
  items: Artifact[];
};

export type WorkspaceItemCreateInput = {
  path: string;
  kind?: string;
  content_text?: string;
};

export type WorkspaceItemCreatePayload = {
  item: SharedWorkspaceItem;
};

export type TeamMemberResponse = {
  agent_id: string;
  agent_name: string;
  role_name: string;
  response_id: string;
  output_text: string;
};

export type TeamTask = {
  id: string;
  team_id: string;
  conversation_id: string;
  assigned_agent_id: string;
  title: string;
  instruction: string;
  status: string;
  source: string;
  claim_token?: string | null;
  claimed_at?: string | null;
  claim_expires_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
};

export type TeamTaskListPayload = {
  items: TeamTask[];
};

export type TeamTaskUpdate = {
  id: string;
  task_id: string;
  team_id: string;
  agent_id?: string | null;
  event_type: string;
  content: string;
  created_at: string;
  updated_at: string;
};

export type TeamTaskUpdateListPayload = {
  items: TeamTaskUpdate[];
};

export type TeamTaskMutationPayload = {
  task: TeamTask;
};

export type AgentInboxClaimPayload = {
  task?: TeamTask | null;
};

export type AgentInboxRunPayload = {
  task?: TeamTask | null;
  conversation_id?: string | null;
  response_id?: string | null;
  output_text?: string | null;
  workspace_item_id?: string | null;
};

export type TeamInboxCycleItem = {
  agent_id: string;
  task?: TeamTask | null;
  conversation_id?: string | null;
  response_id?: string | null;
  output_text?: string | null;
  workspace_item_id?: string | null;
};

export type TeamInboxCyclePayload = {
  executed_count: number;
  results: TeamInboxCycleItem[];
};

export type TeamTaskDelegateInput = {
  assigned_agent_id: string;
  note?: string;
};

export type TeamTaskReportInput = {
  content: string;
  agent_id?: string;
};

export type TeamTaskMessageInput = {
  content: string;
  agent_id?: string;
};

export type TeamTaskCompleteInput = {
  content: string;
  agent_id?: string;
  claim_token?: string;
};

export type TeamResponseInput = {
  input: string;
  conversation_id?: string;
};

export type TeamResponsePayload = {
  conversation_id: string;
  output_text: string;
  outputs: TeamMemberResponse[];
  workspace_item_id?: string | null;
  generated_items: SharedWorkspaceItem[];
};

export type TeamHuddleInput = {
  input: string;
  conversation_id?: string;
};

export type TeamHuddlePayload = {
  conversation_id: string;
  output_text: string;
  outputs: TeamMemberResponse[];
  tasks: TeamTask[];
  workspace_item_id?: string | null;
};

export type GitHubRepository = {
  id: number;
  name: string;
  full_name: string;
  default_branch: string;
  private: boolean;
};

export type GitHubRepositoryListPayload = {
  items: GitHubRepository[];
};

export type GitHubExportInput = {
  repository_full_name: string;
  path: string;
  branch?: string;
  commit_message: string;
};

export type GitHubExportPayload = {
  artifact_id: string;
  artifact: Artifact;
  item: SharedWorkspaceItem;
  repository_full_name: string;
  branch: string;
  commit_sha: string;
  content_url: string;
  commit_url: string;
};

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
    readPollerStatus: () => request<PollerStatusPayload>("/api/system/poller"),
    readGitHubConnection: () => request<GitHubConnectionStatusPayload>("/api/auth/github/connection"),
    listGitHubRepositories: () => request<GitHubRepositoryListPayload>("/api/github/repositories"),
    listRoleTemplates: () => request<RoleTemplateListPayload>("/api/role-templates"),
    listTeams: () => request<TeamListPayload>("/api/teams"),
    createTeam: (payload: TeamCreateInput) =>
      request<TeamCreatePayload>("/api/teams", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    listAgents: () => request<AgentListPayload>("/api/agents"),
    readTeamWorkspace: (teamId: string) =>
      request<TeamWorkspacePayload>(`/api/teams/${teamId}/workspace`),
    listTeamArtifacts: (teamId: string) =>
      request<TeamArtifactListPayload>(`/api/teams/${teamId}/artifacts`),
    createWorkspaceItem: (teamId: string, payload: WorkspaceItemCreateInput) =>
      request<WorkspaceItemCreatePayload>(`/api/teams/${teamId}/workspace/items`, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    listTeamConversations: (teamId: string) =>
      request<TeamConversationListPayload>(`/api/teams/${teamId}/conversations`),
    listTeamTasks: (teamId: string) =>
      request<TeamTaskListPayload>(`/api/teams/${teamId}/tasks`),
    listAgentInbox: (agentId: string) =>
      request<TeamTaskListPayload>(`/api/agents/${agentId}/inbox`),
    claimNextInboxTask: (agentId: string) =>
      request<AgentInboxClaimPayload>(`/api/agents/${agentId}/inbox/claim-next`, {
        method: "POST",
      }),
    runNextInboxTask: (agentId: string) =>
      request<AgentInboxRunPayload>(`/api/agents/${agentId}/inbox/run-next`, {
        method: "POST",
      }),
    runTeamInboxCycle: (teamId: string) =>
      request<TeamInboxCyclePayload>(`/api/teams/${teamId}/inbox/run-cycle`, {
        method: "POST",
      }),
    listTaskUpdates: (taskId: string) =>
      request<TeamTaskUpdateListPayload>(`/api/tasks/${taskId}/updates`),
    delegateTask: (taskId: string, payload: TeamTaskDelegateInput) =>
      request<TeamTaskMutationPayload>(`/api/tasks/${taskId}/delegate`, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    createTaskReport: (taskId: string, payload: TeamTaskReportInput) =>
      request<TeamTaskMutationPayload>(`/api/tasks/${taskId}/reports`, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    createTaskMessage: (taskId: string, payload: TeamTaskMessageInput) =>
      request<TeamTaskMutationPayload>(`/api/tasks/${taskId}/messages`, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    completeTask: (taskId: string, payload: TeamTaskCompleteInput) =>
      request<TeamTaskMutationPayload>(`/api/tasks/${taskId}/complete`, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    createTeamHuddle: (teamId: string, payload: TeamHuddleInput) =>
      request<TeamHuddlePayload>(`/api/teams/${teamId}/huddles`, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    createTeamResponse: (teamId: string, payload: TeamResponseInput) =>
      request<TeamResponsePayload>(`/api/teams/${teamId}/responses`, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    exportWorkspaceItemToGitHub: (
      teamId: string,
      itemId: string,
      payload: GitHubExportInput,
    ) =>
      request<GitHubExportPayload>(
        `/api/github/teams/${teamId}/workspace/items/${itemId}/export`,
        {
          method: "POST",
          body: JSON.stringify(payload),
        },
      ),
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
