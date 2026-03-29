import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";

import { type Agent, type AgentResponsePayload, type ChatMessage } from "../../lib/api";
import { useApiClient, useBackendSession } from "../auth/useSession";

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
  const [searchParams, setSearchParams] = useSearchParams();
  const [draft, setDraft] = useState(searchParams.get("prompt") ?? "");
  const [conversationId, setConversationId] = useState<string | undefined>(undefined);
  const [messages, setMessages] = useState<LocalChatMessage[]>([]);

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
  const provisionRuntime = useMutation({
    mutationFn: () => api.provisionAgentRuntime(agentId),
  });
  const persistedMessages = useQuery({
    queryKey: ["conversation-messages", activeConversationId],
    queryFn: () => api.listConversationMessages(activeConversationId!),
    enabled: !!activeConversationId,
  });

  useEffect(() => {
    if (!persistedMessages.data) {
      return;
    }
    setMessages(mapPersistedMessages(persistedMessages.data.items));
  }, [persistedMessages.data]);

  const responseMutation = useMutation({
    mutationFn: (prompt: string) =>
      api.createAgentResponse(agentId, {
        input: prompt,
        conversation_id: activeConversationId,
      }),
    onSuccess: (response, prompt) => {
      setConversationId(response.conversation_id);
      setMessages((current) => [...current, ...toChatMessages(response, prompt)]);
    },
  });

  useEffect(() => {
    const initialPrompt = searchParams.get("prompt");
    if (!initialPrompt || responseMutation.isPending || messages.length > 0) {
      return;
    }

    void responseMutation.mutateAsync(initialPrompt);
    searchParams.delete("prompt");
    setSearchParams(searchParams, { replace: true });
  }, [messages.length, responseMutation, searchParams, setSearchParams]);

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
              <div className="mt-10 flex flex-1 items-center justify-center rounded border border-dashed border-border px-10">
                <div className="max-w-md text-center">
                  <p className="font-serif text-3xl text-primary">Awaiting artifact generation...</p>
                  <p className="mt-4 text-sm leading-7 text-muted">
                    This pane is ready for the next phase where Sutra will stream artifacts, previews, and shared workspace outputs beside the conversation.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
