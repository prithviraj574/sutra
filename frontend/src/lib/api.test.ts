import { describe, expect, it, vi } from "vitest";

import { createApiClient } from "./api";

describe("api client", () => {
  it("sends bearer auth when syncing the backend session", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        user: {
          id: "user_1",
          firebase_uid: "firebase-user-1",
          email: "user@example.com",
          created_at: "2026-03-28T00:00:00Z",
          updated_at: "2026-03-28T00:00:00Z",
        },
      }),
    });

    const api = createApiClient({
      baseUrl: "http://localhost:8000",
      getAccessToken: async () => "token-123",
      fetcher,
    });

    const result = await api.readSession();
    const firstCall = fetcher.mock.calls[0];
    const firstHeaders = firstCall?.[1]?.headers as Headers;

    expect(firstCall?.[0]).toBe("http://localhost:8000/api/auth/me");
    expect(firstHeaders.get("Authorization")).toBe("Bearer token-123");
    expect(result.user.email).toBe("user@example.com");
  });

  it("posts agent input and returns the persisted conversation payload", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        conversation_id: "conversation-1",
        response_id: "resp_123",
        output_text: "Hello from Sutra",
        raw_response: { id: "resp_123" },
      }),
    });

    const api = createApiClient({
      baseUrl: "http://localhost:8000",
      getAccessToken: async () => "token-123",
      fetcher,
    });

    const result = await api.createAgentResponse("agent-1", {
      input: "Build a dashboard",
    });

    expect(fetcher).toHaveBeenCalledWith(
      "http://localhost:8000/api/agents/agent-1/responses",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ input: "Build a dashboard" }),
      }),
    );
    expect(result.response_id).toBe("resp_123");
  });

  it("loads persisted conversation messages for the chat canvas", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        items: [
          {
            id: "message-1",
            conversation_id: "conversation-1",
            actor_type: "user",
            content: "Build a dashboard",
            created_at: "2026-03-28T00:00:00Z",
            updated_at: "2026-03-28T00:00:00Z",
          },
        ],
      }),
    });

    const api = createApiClient({
      baseUrl: "http://localhost:8000",
      getAccessToken: async () => "token-123",
      fetcher,
    });

    const result = await api.listConversationMessages("conversation-1");
    const firstCall = fetcher.mock.calls[0];
    const firstHeaders = firstCall?.[1]?.headers as Headers;

    expect(firstCall?.[0]).toBe("http://localhost:8000/api/conversations/conversation-1/messages");
    expect(firstHeaders.get("Authorization")).toBe("Bearer token-123");
    expect(result.items[0].content).toBe("Build a dashboard");
  });

  it("can provision and read an agent runtime lease", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          lease: {
            id: "lease-1",
            agent_id: "agent-1",
            vm_id: "local-dev-agent",
            state: "running",
            api_base_url: "http://runtime.internal",
            created_at: "2026-03-28T00:00:00Z",
            updated_at: "2026-03-28T00:00:00Z",
          },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          lease: {
            id: "lease-1",
            agent_id: "agent-1",
            vm_id: "local-dev-agent",
            state: "running",
            api_base_url: "http://runtime.internal",
            created_at: "2026-03-28T00:00:00Z",
            updated_at: "2026-03-28T00:00:00Z",
          },
        }),
      });

    const api = createApiClient({
      baseUrl: "http://localhost:8000",
      getAccessToken: async () => "token-123",
      fetcher,
    });

    const provisioned = await api.provisionAgentRuntime("agent-1");
    const runtime = await api.readAgentRuntime("agent-1");

    expect(fetcher).toHaveBeenNthCalledWith(
      1,
      "http://localhost:8000/api/agents/agent-1/runtime/provision",
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetcher).toHaveBeenNthCalledWith(
      2,
      "http://localhost:8000/api/agents/agent-1/runtime",
      expect.objectContaining({ headers: expect.any(Headers) }),
    );
    expect(provisioned.lease.state).toBe("running");
    expect(runtime.lease.vm_id).toBe("local-dev-agent");
  });

  it("can create, list, and delete secrets through the vault api", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          secret: {
            id: "secret-1",
            user_id: "user-1",
            name: "GITHUB_TOKEN",
            provider: "github",
            scope: "user",
            created_at: "2026-03-28T00:00:00Z",
            updated_at: "2026-03-28T00:00:00Z",
          },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          items: [
            {
              id: "secret-1",
              user_id: "user-1",
              name: "GITHUB_TOKEN",
              provider: "github",
              scope: "user",
              created_at: "2026-03-28T00:00:00Z",
              updated_at: "2026-03-28T00:00:00Z",
            },
          ],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          id: "secret-1",
          deleted: true,
        }),
      });

    const api = createApiClient({
      baseUrl: "http://localhost:8000",
      getAccessToken: async () => "token-123",
      fetcher,
    });

    const created = await api.createSecret({
      name: "GITHUB_TOKEN",
      value: "ghp_super_secret",
      provider: "github",
    });
    const listed = await api.listSecrets();
    const deleted = await api.deleteSecret("secret-1");

    expect(fetcher).toHaveBeenNthCalledWith(
      1,
      "http://localhost:8000/api/secrets",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          name: "GITHUB_TOKEN",
          value: "ghp_super_secret",
          provider: "github",
        }),
      }),
    );
    expect(created.secret.name).toBe("GITHUB_TOKEN");
    expect(listed.items).toHaveLength(1);
    expect(deleted.deleted).toBe(true);
  });
});
