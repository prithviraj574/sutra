import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { type Agent, type AgentResponsePayload, type Artifact, type ChatMessage, type SharedWorkspaceItem } from "../../lib/api";
import { useApiClient, useBackendSession } from "../auth/useSession";
import { readAgentChatParams } from "./routes";
import { buildWorkspaceExportPath, listAgentConversationWorkspaceItems } from "./workspace";

type LocalChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

type ChatPageProps = {
  agentId: string;
};

function toChatMessages(response: AgentResponsePayload, prompt: string): LocalChatMessage[] {
  return [
    { id: `${response.response_id}:user`, role: "user", content: prompt },
    { id: `${response.response_id}:assistant`, role: "assistant", content: response.output_text },
  ];
}

function mapPersistedMessages(messages: ChatMessage[]): LocalChatMessage[] {
  return messages
    .filter((message) => message.actor_type === "user" || message.actor_type === "assistant")
    .map((message) => ({
      id: message.id,
      role: message.actor_type === "assistant" ? "assistant" : "user",
      content: message.content,
    }));
}

export function ChatPage({ agentId }: ChatPageProps) {
  const api = useApiClient();
  const session = useBackendSession();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const initialParams = readAgentChatParams(searchParams);
  const [draft, setDraft] = useState(initialParams.prompt ?? "");
  const [conversationId, setConversationId] = useState<string | undefined>(
    initialParams.conversationId,
  );
  const [messages, setMessages] = useState<LocalChatMessage[]>([]);
  const [selectedWorkspaceItemId, setSelectedWorkspaceItemId] = useState<string | undefined>(undefined);
  const [latestGeneratedItemIds, setLatestGeneratedItemIds] = useState<string[]>([]);
  const [selectedRepository, setSelectedRepository] = useState("");
  const [exportPath, setExportPath] = useState("app/agent-output.md");
  const [commitMessage, setCommitMessage] = useState("Export agent output");

  const agents = useQuery({
    queryKey: ["agents", session.data?.user.id],
    queryFn: () => api.listAgents(),
    enabled: !!session.data,
  });
  const agent = useMemo<Agent | null>(
    () => agents.data?.items.find((entry) => entry.id === agentId) ?? null,
    [agentId, agents.data?.items],
  );
  const conversations = useQuery({
    queryKey: ["agent-conversations", agentId],
    queryFn: () => api.listAgentConversations(agentId),
    enabled: !!agent,
  });
  const activeConversationId = conversationId ?? conversations.data?.items[0]?.id;
  const runtime = useQuery({
    queryKey: ["agent-runtime", agentId],
    queryFn: () => api.readAgentRuntime(agentId),
    retry: false,
  });
  const teamWorkspace = useQuery({
    queryKey: ["team-workspace", agent?.team_id],
    queryFn: () => api.readTeamWorkspace(agent!.team_id),
    enabled: !!agent?.team_id,
  });
  const teamArtifacts = useQuery({
    queryKey: ["team-artifacts", agent?.team_id],
    queryFn: () => api.listTeamArtifacts(agent!.team_id),
    enabled: !!agent?.team_id,
  });
  const githubConnection = useQuery({
    queryKey: ["github-connection", session.data?.user.id],
    queryFn: () => api.readGitHubConnection(),
    enabled: !!session.data,
    retry: false,
  });
  const githubRepositories = useQuery({
    queryKey: ["github-repositories", session.data?.user.id],
    queryFn: () => api.listGitHubRepositories(),
    enabled: !!githubConnection.data?.connection,
    retry: false,
  });
  const provisionRuntime = useMutation({
    mutationFn: () => api.provisionAgentRuntime(agentId),
  });
  const persistedMessages = useQuery({
    queryKey: ["conversation-messages", activeConversationId],
    queryFn: () => api.listConversationMessages(activeConversationId!),
    enabled: !!activeConversationId,
  });

  useEffect(() => {
    const { conversationId: requestedConversationId } = readAgentChatParams(searchParams);
    setConversationId(requestedConversationId);
  }, [searchParams]);

  useEffect(() => {
    if (!persistedMessages.data) {
      return;
    }
    setMessages(mapPersistedMessages(persistedMessages.data.items));
  }, [persistedMessages.data]);

  useEffect(() => {
    if (!githubRepositories.data?.items.length || selectedRepository) {
      return;
    }
    setSelectedRepository(githubRepositories.data.items[0].full_name);
  }, [githubRepositories.data?.items, selectedRepository]);

  const responseMutation = useMutation({
    mutationFn: (prompt: string) =>
      api.createAgentResponse(agentId, {
        input: prompt,
        conversation_id: activeConversationId,
      }),
    onSuccess: (response, prompt) => {
      setConversationId(response.conversation_id);
      if (response.workspace_item_id) {
        setLatestGeneratedItemIds([response.workspace_item_id]);
        setSelectedWorkspaceItemId(response.workspace_item_id);
      }
      setMessages((current) => [...current, ...toChatMessages(response, prompt)]);
      void queryClient.invalidateQueries({ queryKey: ["team-workspace", agent?.team_id] });
      void queryClient.invalidateQueries({ queryKey: ["team-artifacts", agent?.team_id] });
    },
  });

  const exportMutation = useMutation({
    mutationFn: () =>
      api.exportWorkspaceItemToGitHub(agent!.team_id, selectedWorkspaceItemId!, {
        repository_full_name: selectedRepository,
        path: exportPath.trim(),
        commit_message: commitMessage.trim(),
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["team-artifacts", agent?.team_id] });
    },
  });

  useEffect(() => {
    const { prompt: initialPrompt } = readAgentChatParams(searchParams);
    if (!initialPrompt || responseMutation.isPending || messages.length > 0) {
      return;
    }

    void responseMutation.mutateAsync(initialPrompt);
    const next = new URLSearchParams(searchParams);
    next.delete("prompt");
    setSearchParams(next, { replace: true });
  }, [messages.length, responseMutation, searchParams, setSearchParams]);

  useEffect(() => {
    if (!conversationId) {
      return;
    }

    const currentConversationId = searchParams.get("conversationId");
    if (currentConversationId === conversationId) {
      return;
    }

    const next = new URLSearchParams(searchParams);
    next.set("conversationId", conversationId);
    setSearchParams(next, { replace: true });
  }, [conversationId, searchParams, setSearchParams]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const prompt = draft.trim();
    if (!prompt) {
      return;
    }

    setDraft("");
    void (async () => {
      if (!runtime.data && !provisionRuntime.isPending) {
        try {
          await provisionRuntime.mutateAsync();
        } catch {
          // The response route can still provision as a fallback.
        }
      }
      await responseMutation.mutateAsync(prompt);
    })();
  }

  function handleExport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!agent?.team_id || !selectedWorkspaceItemId || !selectedRepository || !exportPath.trim() || !commitMessage.trim()) {
      return;
    }
    void exportMutation.mutateAsync();
  }

  const selectedWorkspaceItem = useMemo<SharedWorkspaceItem | null>(
    () => teamWorkspace.data?.items.find((item) => item.id === selectedWorkspaceItemId) ?? null,
    [selectedWorkspaceItemId, teamWorkspace.data?.items],
  );
  const conversationWorkspaceItems = useMemo<SharedWorkspaceItem[]>(
    () =>
      listAgentConversationWorkspaceItems(teamWorkspace.data?.items ?? [], {
        conversationId: activeConversationId,
        agentId,
      }),
    [activeConversationId, agentId, teamWorkspace.data?.items],
  );
  const latestGeneratedItems = useMemo<SharedWorkspaceItem[]>(
    () =>
      latestGeneratedItemIds
        .map((id) => teamWorkspace.data?.items.find((item) => item.id === id) ?? null)
        .filter((item): item is SharedWorkspaceItem => item !== null),
    [latestGeneratedItemIds, teamWorkspace.data?.items],
  );
  const githubExports = useMemo<Artifact[]>(
    () =>
      (teamArtifacts.data?.items ?? []).filter(
        (item) => item.kind === "github_export" && item.agent_id === agentId,
      ),
    [agentId, teamArtifacts.data?.items],
  );

  useEffect(() => {
    if (conversationWorkspaceItems.length > 0) {
      if (
        !selectedWorkspaceItem ||
        selectedWorkspaceItem.conversation_id !== activeConversationId ||
        selectedWorkspaceItem.agent_id !== agentId
      ) {
        setSelectedWorkspaceItemId(conversationWorkspaceItems[0].id);
      }
      return;
    }
    if (!selectedWorkspaceItem && teamWorkspace.data?.items.length) {
      setSelectedWorkspaceItemId(teamWorkspace.data.items[0].id);
    }
  }, [activeConversationId, agentId, conversationWorkspaceItems, selectedWorkspaceItem, teamWorkspace.data?.items]);

  useEffect(() => {
    if (!selectedWorkspaceItem) {
      return;
    }
    if (
      exportPath === "app/agent-output.md" ||
      exportPath.startsWith("app/conversations/") ||
      exportPath.startsWith("app/tasks/")
    ) {
      setExportPath(buildWorkspaceExportPath(selectedWorkspaceItem));
    }
  }, [exportPath, selectedWorkspaceItem]);

  return (
    <main className="min-h-screen bg-background">
      <div className="grid min-h-screen grid-cols-1 lg:grid-cols-[45%_55%]">
        <section className="border-b border-border px-6 py-8 lg:border-b-0 lg:border-r">
          <header className="mb-8 flex items-center justify-between">
            <div>
              <p className="font-mono text-xs uppercase tracking-[0.22em] text-muted">Chat Canvas</p>
              <h1 className="mt-3 text-3xl">{agent?.name ?? "Agent Session"}</h1>
            </div>
            <Link className="text-sm text-muted transition-colors hover:text-primary" to="/">
              Return to Hub
            </Link>
          </header>

          <div className="space-y-6 pb-32">
            {messages.length === 0 ? (
              <p className="text-sm text-muted">Prompt an agent to start a persisted conversation.</p>
            ) : null}

            {messages.map((message) => (
              <article
                className={message.role === "user" ? "ml-auto max-w-[85%] rounded bg-surface px-4 py-3" : "max-w-[85%]"}
                key={message.id}
              >
                <p className="text-sm leading-7 text-text">{message.content}</p>
              </article>
            ))}

            {responseMutation.isPending ? (
              <div className="relative max-w-[85%] rounded border border-border bg-background px-4 py-3">
                <div className="aura-glow absolute inset-x-4 top-2 h-8 rounded-full" />
                <p className="relative text-sm text-muted">Agent is thinking...</p>
              </div>
            ) : null}
          </div>

          <form className="fixed inset-x-0 bottom-0 border-t border-border bg-background/95 px-6 py-4 backdrop-blur lg:left-0 lg:right-[55%]" onSubmit={handleSubmit}>
            <div className="aura-border rounded-lg bg-surface p-3">
              <textarea
                className="min-h-28 w-full resize-none bg-transparent px-3 py-2 text-sm leading-7 text-text outline-none placeholder:text-muted"
                placeholder="Describe what you want Sutra to build next..."
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
              />
              <div className="mt-3 flex items-center justify-between px-3 pb-1">
                <div>
                  <p className="text-xs uppercase tracking-[0.18em] text-muted">{agent?.role_name ?? "Generalist"}</p>
                  <p className="mt-1 text-[11px] uppercase tracking-[0.18em] text-muted">
                    Runtime {runtime.data?.lease.state ?? "not provisioned"}
                  </p>
                </div>
                <button className="btn-primary" type="submit">
                  Send
                </button>
              </div>
            </div>
          </form>
        </section>

        <section className="relative hidden bg-surface lg:block">
          <div className="absolute inset-10">
            <div className="absolute inset-x-8 top-10 h-24 rounded-full aura-glow" />
            <div className="aura-border relative flex h-full flex-col rounded-lg bg-background/90 p-10">
              <p className="font-mono text-xs uppercase tracking-[0.22em] text-muted">Artifact Surface</p>
              <div className="mt-8 grid flex-1 grid-rows-[minmax(0,1fr)_auto_auto] gap-6">
                <div className="rounded border border-border bg-surface p-5">
                  <p className="font-mono text-xs uppercase tracking-[0.18em] text-muted">Workspace Output</p>
                  {latestGeneratedItems.length > 0 ? (
                    <div className="mt-4 flex flex-wrap gap-2">
                      {latestGeneratedItems.map((item) => (
                        <button
                          className={`rounded border px-3 py-2 text-left text-xs transition-colors ${
                            item.id === selectedWorkspaceItemId
                              ? "border-primary bg-background text-primary"
                              : "border-border bg-background text-text hover:border-primary"
                          }`}
                          key={item.id}
                          onClick={() => setSelectedWorkspaceItemId(item.id)}
                          type="button"
                        >
                          Latest: {item.path}
                        </button>
                      ))}
                    </div>
                  ) : conversationWorkspaceItems.length > 0 ? (
                    <div className="mt-4 flex flex-wrap gap-2">
                      {conversationWorkspaceItems.slice(0, 3).map((item) => (
                        <button
                          className={`rounded border px-3 py-2 text-left text-xs transition-colors ${
                            item.id === selectedWorkspaceItemId
                              ? "border-primary bg-background text-primary"
                              : "border-border bg-background text-text hover:border-primary"
                          }`}
                          key={item.id}
                          onClick={() => setSelectedWorkspaceItemId(item.id)}
                          type="button"
                        >
                          {item.path}
                        </button>
                      ))}
                    </div>
                  ) : null}
                  <div className="mt-4 min-h-64 rounded border border-border bg-background px-4 py-4">
                    {selectedWorkspaceItem?.content_text ? (
                      <pre className="whitespace-pre-wrap text-sm leading-7 text-text">
                        {selectedWorkspaceItem.content_text}
                      </pre>
                    ) : (
                      <p className="text-sm text-muted">
                        Send a prompt and Sutra will keep the latest agent output in the personal workspace here.
                      </p>
                    )}
                  </div>
                </div>

                <form className="rounded border border-border bg-surface p-5" onSubmit={handleExport}>
                  <p className="font-mono text-xs uppercase tracking-[0.18em] text-muted">GitHub Export</p>
                  {!githubConnection.data?.connection ? (
                    <p className="mt-4 text-sm text-muted">
                      Connect GitHub from the Hub before exporting this agent output.
                    </p>
                  ) : (
                    <>
                      <div className="mt-4 space-y-4">
                        <select
                          className="w-full rounded border border-border bg-background px-3 py-3 text-sm text-text outline-none"
                          value={selectedRepository}
                          onChange={(event) => setSelectedRepository(event.target.value)}
                        >
                          {(githubRepositories.data?.items ?? []).map((repository) => (
                            <option key={repository.full_name} value={repository.full_name}>
                              {repository.full_name}
                            </option>
                          ))}
                        </select>
                        <input
                          className="w-full rounded border border-border bg-background px-3 py-3 text-sm text-text outline-none"
                          value={exportPath}
                          onChange={(event) => setExportPath(event.target.value)}
                        />
                        <input
                          className="w-full rounded border border-border bg-background px-3 py-3 text-sm text-text outline-none"
                          value={commitMessage}
                          onChange={(event) => setCommitMessage(event.target.value)}
                        />
                      </div>
                      {exportMutation.error ? (
                        <p className="mt-4 text-sm text-primary">{exportMutation.error.message}</p>
                      ) : null}
                      {exportMutation.data ? (
                        <div className="mt-4 rounded border border-border bg-background px-4 py-3 text-sm text-text">
                          <p>Exported to {exportMutation.data.repository_full_name}.</p>
                          <div className="mt-2 flex flex-wrap gap-4">
                            <a
                              className="text-primary underline-offset-4 hover:underline"
                              href={exportMutation.data.content_url}
                              rel="noreferrer"
                              target="_blank"
                            >
                              View file
                            </a>
                            <a
                              className="text-primary underline-offset-4 hover:underline"
                              href={exportMutation.data.commit_url}
                              rel="noreferrer"
                              target="_blank"
                            >
                              View commit
                            </a>
                          </div>
                        </div>
                      ) : null}
                      <button className="btn-primary mt-5" type="submit" disabled={!selectedWorkspaceItemId || exportMutation.isPending}>
                        {exportMutation.isPending ? "Exporting..." : "Export Output"}
                      </button>
                    </>
                  )}
                </form>

                <div className="rounded border border-border bg-surface p-5">
                  <p className="font-mono text-xs uppercase tracking-[0.18em] text-muted">Recent Exports</p>
                  {githubExports.length ? (
                    <div className="mt-4 space-y-3">
                      {githubExports.slice(0, 3).map((artifact) => (
                        <div className="rounded border border-border bg-background px-4 py-3" key={artifact.id}>
                          <p className="text-sm text-primary">{artifact.github_repo ?? artifact.name}</p>
                          <p className="mt-1 text-xs uppercase tracking-[0.18em] text-muted">
                            {artifact.github_branch ?? "main"} · {artifact.github_sha?.slice(0, 7) ?? "pending"}
                          </p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="mt-4 text-sm text-muted">
                      Exported agent outputs will appear here so the ownership path is visible from chat.
                    </p>
                  )}
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
