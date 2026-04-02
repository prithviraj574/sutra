import { FormEvent, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "../auth/AuthProvider";
import { useApiClient, useBackendSession } from "../auth/useSession";
import { readFrontendEnv } from "../../lib/env";
import { parseApiDate } from "../../lib/dates";
import { buildAgentChatHref } from "../chat/routes";
import { pickDefaultAgent } from "./defaultAgent";

function formatRelativeTime(dateString: string): string {
  const date = parseApiDate(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

export function HubPage() {
  const navigate = useNavigate();
  const auth = useAuth();
  const api = useApiClient();
  const session = useBackendSession();
  const queryClient = useQueryClient();
  const frontendEnv = useMemo(() => readFrontendEnv(), []);
  const [searchParams, setSearchParams] = useSearchParams();
  const teams = useQuery({
    queryKey: ["teams", session.data?.user.id],
    queryFn: () => api.listTeams(),
    enabled: !!session.data,
  });
  const githubConnection = useQuery({
    queryKey: ["github-connection", session.data?.user.id],
    queryFn: () => api.readGithubConnection(),
    enabled: !!session.data,
    retry: false,
  });
  const agents = useQuery({
    queryKey: ["agents", session.data?.user.id],
    queryFn: () => api.listAgents(),
    enabled: !!session.data,
  });
  const normalizedAgents = useMemo(
    () =>
      (agents.data?.items ?? []).map((entry) => ({
        ...entry,
        team_ids: entry.team_ids ?? [],
      })),
    [agents.data?.items],
  );
  const workspaces = useQuery<Record<string, { path: string; kind: string }[]>>({
    queryKey: ["team-workspaces", teams.data?.items.map((team) => team.id).join(",")],
    queryFn: async () => {
      const entries = await Promise.all(
        (teams.data?.items ?? []).map(async (team) => {
          const workspace = await api.getTeamWorkspace({
            params: {
              path: {
                team_id: team.id,
              },
            },
          });
          return [
            team.id,
            workspace.items.map((item) => ({ path: item.path, kind: item.kind })),
          ] as const;
        }),
      );
      return Object.fromEntries(entries);
    },
    enabled: !!teams.data?.items.length,
  });
  const [prompt, setPrompt] = useState("");

  const defaultAgent = useMemo(
    () => pickDefaultAgent(normalizedAgents, teams.data?.items ?? []),
    [normalizedAgents, teams.data?.items],
  );
  const runtime = useQuery({
    queryKey: ["agent-runtime", defaultAgent?.id],
    queryFn: () =>
      api.getAgentRuntime({
        params: {
          path: {
            agent_id: defaultAgent!.id,
          },
        },
      }),
    enabled: !!defaultAgent,
    retry: false,
  });
  const provisionRuntime = useMutation({
    mutationFn: () =>
      api.provisionAgentRuntime({
        params: {
          path: {
            agent_id: defaultAgent!.id,
          },
        },
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["agent-runtime", defaultAgent?.id] });
    },
  });
  const verifyRuntime = useMutation({
    mutationFn: () =>
      api.verifyAgentRuntime({
        params: {
          path: {
            agent_id: defaultAgent!.id,
          },
        },
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["agent-runtime", defaultAgent?.id] });
    },
  });
  const restartRuntime = useMutation({
    mutationFn: () =>
      api.restartAgentRuntime({
        params: {
          path: {
            agent_id: defaultAgent!.id,
          },
        },
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["agent-runtime", defaultAgent?.id] });
    },
  });
  const conversations = useQuery({
    queryKey: ["agent-conversations", defaultAgent?.id],
    queryFn: () =>
      api.getAgentConversations({
        params: {
          path: {
            agent_id: defaultAgent!.id,
          },
        },
      }),
    enabled: !!defaultAgent,
  });
  const conversationMessages = useQuery<Record<string, string>>({
    queryKey: ["conversation-preview-messages", defaultAgent?.id],
    queryFn: async () => {
      if (!conversations.data?.items.length) return {};
      const previews: Record<string, string> = {};
      // Fetch last message for each conversation (limit to 5 for performance)
      const recent = conversations.data.items.slice(0, 5);
      await Promise.all(
        recent.map(async (conv) => {
          try {
            const msgs = await api.getConversationMessages({
              params: {
                path: {
                  conversation_id: conv.id,
                },
              },
            });
            const last = msgs.items[msgs.items.length - 1];
            if (last) {
              previews[conv.id] = last.content.slice(0, 80) + (last.content.length > 80 ? "..." : "");
            }
          } catch {
            // ignore
          }
        })
      );
      return previews;
    },
    enabled: !!defaultAgent && !!(conversations.data?.items.length),
  });

  function handleStart(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!defaultAgent || !prompt.trim()) {
      return;
    }

    navigate(
      buildAgentChatHref(defaultAgent.id, {
        prompt: prompt.trim(),
        newConversation: true,
      }),
    );
  }

  function handleConnectGitHub() {
    window.location.assign(`${frontendEnv.apiBaseUrl}/api/auth/github`);
  }

  if (auth.loading || session.isLoading) {
    return <main className="mx-auto min-h-screen max-w-4xl px-6 py-24">Loading workspace...</main>;
  }

  if (auth.authMode === "firebase" && !auth.firebaseEnabled) {
    return (
      <main className="mx-auto flex min-h-screen max-w-4xl items-center px-6 py-24">
        <div className="aura-border w-full rounded-lg bg-surface p-8">
          <p className="font-serif text-3xl text-primary">Sutra needs Firebase web config.</p>
          <p className="mt-4 max-w-2xl text-sm text-muted">
            Add the `VITE_FIREBASE_*` values in [frontend/.env.example](/Users/prithviraj/Desktop/Misc/sutra/frontend/.env.example)
            so Google sign-in can hand off a token to the FastAPI backend.
          </p>
        </div>
      </main>
    );
  }

  if (!auth.user) {
    return (
      <main className="mx-auto flex min-h-screen max-w-4xl items-center px-6 py-24">
        <section className="w-full">
          <p className="font-mono text-xs uppercase tracking-[0.22em] text-muted">Sutra</p>
          <h1 className="mt-6 max-w-3xl text-5xl leading-tight">
            Orchestrate persistent agents in a calm, single-threaded workspace.
          </h1>
          <p className="mt-6 max-w-2xl text-base leading-7 text-muted">
            Sign in with Google to provision your default workspace, sync it with the backend, and continue directly into the chat canvas.
          </p>
          {auth.authError ? (
            <p className="mt-6 max-w-2xl rounded border border-border bg-surface px-4 py-3 text-sm text-primary">
              {auth.authError}
            </p>
          ) : null}
          <button className="btn-primary mt-10" onClick={() => void auth.signIn()}>
            Sign In With Google
          </button>
        </section>
      </main>
    );
  }

  const githubStatus = searchParams.get("github");
  const teamCreated = searchParams.get("teamCreated");

  return (
    <main className="mx-auto min-h-screen max-w-4xl px-6 pb-24 pt-28">
      {githubStatus === "connected" ? (
        <div className="aura-border mb-8 rounded-lg bg-surface px-4 py-3 text-sm text-primary">
          GitHub is connected. Sutra can now use your installation for repo-backed workflows.
        </div>
      ) : null}
      {githubStatus === "error" ? (
        <div className="mb-8 rounded-lg border border-border bg-surface px-4 py-3 text-sm text-primary">
          GitHub connection did not complete. Please try again.
        </div>
      ) : null}
      {teamCreated === "1" ? (
        <div className="aura-border mb-8 rounded-lg bg-surface px-4 py-3 text-sm text-primary">
          Team created. Your new role-based workspace is ready.
        </div>
      ) : null}
      {session.error ? (
        <div className="mb-8 rounded-lg border border-border bg-surface px-4 py-3 text-sm text-primary">
          Backend session sync failed: {session.error.message}
        </div>
      ) : null}
      {auth.authMode === "dev_bypass" ? (
        <div className="aura-border mb-8 rounded-lg bg-surface px-4 py-3 text-sm text-primary">
          Local dev auth bypass is active. Sutra is using the seeded local user instead of Google sign-in.
        </div>
      ) : null}
      <header className="flex items-start justify-between gap-6">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.22em] text-muted">Hub</p>
          <h1 className="mt-4 text-5xl leading-tight">Start from a single prompt.</h1>
        </div>
        <div className="flex items-center gap-5">
          <Link className="text-sm text-muted transition-colors hover:text-primary" to="/teams/new">
            Create Team
          </Link>
          <Link className="text-sm text-muted transition-colors hover:text-primary" to="/secrets">
            Secret Vault
          </Link>
          <button className="text-sm text-muted transition-colors hover:text-primary" onClick={() => void auth.signOutUser()}>
            Sign out
          </button>
        </div>
      </header>

      <form className="aura-border mt-14 rounded-lg bg-surface p-3" onSubmit={handleStart}>
        <label className="sr-only" htmlFor="hub-prompt">
          Initialize session
        </label>
        <input
          id="hub-prompt"
          className="w-full bg-transparent px-4 py-4 font-serif text-2xl text-primary outline-none placeholder:text-muted"
          placeholder="+ Initialize Session"
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
        />
      </form>

      {defaultAgent ? (
        <section className="mt-8 rounded-lg border border-border bg-surface px-5 py-4">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="font-mono text-xs uppercase tracking-[0.18em] text-muted">Default Runtime</p>
              <p className="mt-2 text-sm text-primary">
                {runtime.data?.lease.readiness_stage ?? "provisioning"} · {runtime.data?.lease.readiness_reason ?? "Runtime status unavailable."}
              </p>
              <p className="mt-1 text-xs uppercase tracking-[0.18em] text-muted">
                Provider {runtime.data?.lease.provider ?? defaultAgent.runtime_kind} · Isolation {runtime.data?.lease.isolation_ok ? "verified" : "pending"}
              </p>
              {runtime.data?.lease.host_vm_id ? (
                <p className="mt-1 text-xs uppercase tracking-[0.18em] text-muted">
                  Host {runtime.data.lease.host_vm_id}
                </p>
              ) : null}
              {provisionRuntime.error ? (
                <p className="mt-2 text-xs text-primary">{provisionRuntime.error.message}</p>
              ) : null}
              {verifyRuntime.error ? (
                <p className="mt-2 text-xs text-primary">{verifyRuntime.error.message}</p>
              ) : null}
              {restartRuntime.error ? (
                <p className="mt-2 text-xs text-primary">{restartRuntime.error.message}</p>
              ) : null}
            </div>
            <button
              className="btn-secondary"
              disabled={provisionRuntime.isPending || !defaultAgent}
              onClick={() => void provisionRuntime.mutateAsync()}
              type="button"
            >
              {provisionRuntime.isPending ? "Provisioning..." : "Provision Runtime"}
            </button>
            <button
              className="btn-secondary"
              disabled={verifyRuntime.isPending || !defaultAgent}
              onClick={() => void verifyRuntime.mutateAsync()}
              type="button"
            >
              {verifyRuntime.isPending ? "Verifying..." : "Verify Runtime"}
            </button>
            <button
              className="btn-secondary"
              disabled={restartRuntime.isPending || !defaultAgent}
              onClick={() => void restartRuntime.mutateAsync()}
              type="button"
            >
              {restartRuntime.isPending ? "Restarting..." : "Restart Runtime"}
            </button>
          </div>
        </section>
      ) : null}

      <section className="mt-16">
        <div className="mb-4 flex items-center justify-between">
          <p className="font-mono text-xs uppercase tracking-[0.22em] text-muted">Workspace</p>
          {defaultAgent ? (
              <Link className="text-sm text-muted transition-colors hover:text-primary" to={buildAgentChatHref(defaultAgent.id)}>
                Open default agent
              </Link>
          ) : null}
        </div>

        <div className="divide-y divide-border border-y border-border">
          {(teams.data?.items ?? []).map((team) => (
            <div className="flex min-h-16 items-center justify-between py-4" key={team.id}>
              <div className="min-w-0 flex-1">
                <p className="text-sm text-primary">{team.name}</p>
                <p className="mt-1 text-xs uppercase tracking-[0.18em] text-muted">{team.mode}</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {agents.data?.items
                    .map((agent) => ({ ...agent, team_ids: agent.team_ids ?? [] }))
                    .filter((agent) => agent.team_ids.includes(team.id))
                    .map((agent) => (
                      <span
                        className="rounded border border-border px-2 py-1 text-[11px] uppercase tracking-[0.14em] text-muted"
                        key={agent.id}
                      >
                        {agent.role_name}
                      </span>
                    ))}
                </div>
                <div className="mt-2 flex flex-wrap gap-2">
                  {(workspaces.data?.[team.id] ?? []).slice(0, 3).map((item) => (
                    <span className="text-xs text-muted" key={`${team.id}:${item.path}`}>
                      {item.kind === "directory" ? `${item.path}/` : item.path}
                    </span>
                  ))}
                  {(workspaces.data?.[team.id] ?? []).length === 0 ? (
                    <span className="text-xs text-muted">Workspace is ready for shared outputs.</span>
                  ) : null}
                </div>
              </div>
              <div className="text-right">
                <p className="text-xs text-muted">
                  {normalizedAgents.filter((agent) => agent.team_ids.includes(team.id)).length ?? 0} agent
                </p>
                {defaultAgent && defaultAgent.team_ids.includes(team.id) && team.mode === "personal" ? (
                  <p className="mt-1 text-xs uppercase tracking-[0.18em] text-muted">
                    Runtime {runtime.data?.lease.readiness_stage ?? runtime.data?.lease.state ?? "not provisioned"}
                  </p>
                ) : null}
                {team.mode === "team" ? (
                  <Link
                    className="mt-2 inline-block text-xs uppercase tracking-[0.18em] text-muted transition-colors hover:text-primary"
                    to={`/teams/${team.id}`}
                  >
                    Open
                  </Link>
                ) : normalizedAgents.find((agent) => agent.team_ids.includes(team.id)) ? (
                  <Link
                    className="mt-2 inline-block text-xs uppercase tracking-[0.18em] text-muted transition-colors hover:text-primary"
                    to={buildAgentChatHref(
                      normalizedAgents.find((agent) => agent.team_ids.includes(team.id))!.id,
                    )}
                  >
                    Open
                  </Link>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-16">
        <div className="mb-4 flex items-center justify-between">
          <p className="font-mono text-xs uppercase tracking-[0.22em] text-muted">Connections</p>
        </div>
        <div className="aura-border rounded-lg bg-surface p-6">
          <div className="flex items-start justify-between gap-6">
            <div>
              <p className="text-sm text-primary">GitHub</p>
              {githubConnection.data?.connection ? (
                <p className="mt-2 text-sm text-muted">
                  Connected as {githubConnection.data.connection.account_login} ({githubConnection.data.connection.account_type})
                </p>
              ) : (
                <p className="mt-2 max-w-xl text-sm text-muted">
                  Connect GitHub so generated code can be committed into a repo you control.
                </p>
              )}
            </div>
            {githubConnection.data?.connection ? (
              <span className="text-xs uppercase tracking-[0.18em] text-muted">Connected</span>
            ) : (
              <button className="btn-primary" type="button" onClick={handleConnectGitHub}>
                Connect GitHub
              </button>
            )}
          </div>
        </div>
      </section>

      {defaultAgent ? (
        <section className="mt-16">
          <div className="mb-4 flex items-center justify-between">
            <p className="font-mono text-xs uppercase tracking-[0.22em] text-muted">Recent Conversations</p>
            <Link
              className="text-sm text-muted transition-colors hover:text-primary"
              to={buildAgentChatHref(defaultAgent.id, { newConversation: true })}
            >
              New Chat
            </Link>
          </div>
          <div className="divide-y divide-border border-y border-border">
            {(conversations.data?.items ?? []).map((conv) => (
              <Link
                className="flex min-h-14 items-center justify-between py-4 transition-colors hover:bg-surface/50"
                to={buildAgentChatHref(defaultAgent.id, { conversationId: conv.id })}
                key={conv.id}
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-primary truncate">
                    {conversationMessages.data?.[conv.id] ?? "Conversation"}
                  </p>
                  <p className="mt-1 text-xs text-muted">
                    {conv.mode} &middot; {formatRelativeTime(conv.updated_at)}
                  </p>
                </div>
              </Link>
            ))}
            {(conversations.data?.items ?? []).length === 0 ? (
              <div className="py-6 text-center">
                <p className="text-sm text-muted">No conversations yet. Start a new chat to begin.</p>
              </div>
            ) : null}
          </div>
        </section>
      ) : null}
    </main>
  );
}
