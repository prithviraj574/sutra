import { FormEvent, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { useAuth } from "../auth/AuthProvider";
import { useApiClient, useBackendSession } from "../auth/useSession";

function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
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
  const teams = useQuery({
    queryKey: ["teams", session.data?.user.id],
    queryFn: () => api.listTeams(),
    enabled: !!session.data,
  });
  const agents = useQuery({
    queryKey: ["agents", session.data?.user.id],
    queryFn: () => api.listAgents(),
    enabled: !!session.data,
  });
  const [prompt, setPrompt] = useState("");

  const defaultAgent = useMemo(() => agents.data?.items[0] ?? null, [agents.data?.items]);
  const runtime = useQuery({
    queryKey: ["agent-runtime", defaultAgent?.id],
    queryFn: () => api.readAgentRuntime(defaultAgent!.id),
    enabled: !!defaultAgent,
    retry: false,
  });
  const conversations = useQuery({
    queryKey: ["agent-conversations", defaultAgent?.id],
    queryFn: () => api.listAgentConversations(defaultAgent!.id),
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
            const msgs = await api.listConversationMessages(conv.id);
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

    navigate(`/agents/${defaultAgent.id}?prompt=${encodeURIComponent(prompt.trim())}`);
  }

  if (auth.loading || session.isLoading) {
    return <main className="mx-auto min-h-screen max-w-4xl px-6 py-24">Loading workspace...</main>;
  }

  if (!auth.firebaseEnabled) {
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
          <button className="btn-primary mt-10" onClick={() => void auth.signIn()}>
            Sign In With Google
          </button>
        </section>
      </main>
    );
  }

  return (
    <main className="mx-auto min-h-screen max-w-4xl px-6 pb-24 pt-28">
      <header className="flex items-start justify-between gap-6">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.22em] text-muted">Hub</p>
          <h1 className="mt-4 text-5xl leading-tight">Start from a single prompt.</h1>
        </div>
        <div className="flex items-center gap-5">
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

      <section className="mt-16">
        <div className="mb-4 flex items-center justify-between">
          <p className="font-mono text-xs uppercase tracking-[0.22em] text-muted">Workspace</p>
          {defaultAgent ? (
            <Link className="text-sm text-muted transition-colors hover:text-primary" to={`/agents/${defaultAgent.id}`}>
              Open default agent
            </Link>
          ) : null}
        </div>

        <div className="divide-y divide-border border-y border-border">
          {(teams.data?.items ?? []).map((team) => (
            <div className="flex min-h-16 items-center justify-between py-4" key={team.id}>
              <div>
                <p className="text-sm text-primary">{team.name}</p>
                <p className="mt-1 text-xs uppercase tracking-[0.18em] text-muted">{team.mode}</p>
              </div>
              <div className="text-right">
                <p className="text-xs text-muted">
                  {agents.data?.items.filter((agent) => agent.team_id === team.id).length ?? 0} agent
                </p>
                {defaultAgent && team.id === defaultAgent.team_id ? (
                  <p className="mt-1 text-xs uppercase tracking-[0.18em] text-muted">
                    Runtime {runtime.data?.lease.state ?? "not provisioned"}
                  </p>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      </section>

      {defaultAgent ? (
        <section className="mt-16">
          <div className="mb-4 flex items-center justify-between">
            <p className="font-mono text-xs uppercase tracking-[0.22em] text-muted">Recent Conversations</p>
            <Link
              className="text-sm text-muted transition-colors hover:text-primary"
              to="/chat"
            >
              New Chat
            </Link>
          </div>
          <div className="divide-y divide-border border-y border-border">
            {(conversations.data?.items ?? []).map((conv) => (
              <Link
                className="flex min-h-14 items-center justify-between py-4 transition-colors hover:bg-surface/50"
                to={`/chat?conversationId=${conv.id}`}
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
