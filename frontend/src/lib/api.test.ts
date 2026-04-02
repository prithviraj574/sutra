import { describe, expect, it, vi } from "vitest";

import { createApiClient, requestData } from "./api.generated";

function jsonResponse(body: unknown, init?: ResponseInit) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: {
      "Content-Type": "application/json",
    },
    ...init,
  });
}

describe("api client", () => {
  it("injects bearer auth through middleware for JSON requests", async () => {
    const rawFetcher = vi.fn(async () =>
      jsonResponse({
        user: {
          id: "user-1",
          firebase_uid: "firebase-user-1",
          email: "user@example.com",
          created_at: "2026-04-01T00:00:00Z",
          updated_at: "2026-04-01T00:00:00Z",
        },
      }),
    );

    const api = createApiClient({
      baseUrl: "http://localhost:8001",
      getAccessToken: async () => "token-123",
      fetcher: rawFetcher as unknown as typeof fetch,
    });

    const result = await requestData(api.GET("/api/auth/me"));
    const request = rawFetcher.mock.calls.at(0)?.at(0);

    expect(request).toBeInstanceOf(Request);
    const typedRequest = request as unknown as Request;
    expect(typedRequest.url).toBe("http://localhost:8001/api/auth/me");
    expect(typedRequest.headers.get("Authorization")).toBe("Bearer token-123");
    expect(typedRequest.headers.get("Accept")).toBe("application/json");
    expect(result.user.email).toBe("user@example.com");
  });

  it("posts typed JSON bodies through openapi-fetch", async () => {
    const rawFetcher = vi.fn(async () =>
      jsonResponse({
        team: {
          id: "team-1",
          user_id: "user-1",
          name: "Launch Crew",
          description: "Cross-functional team",
          mode: "team",
          shared_workspace_uri: "workspace://teams/team-1",
          created_at: "2026-04-01T00:00:00Z",
          updated_at: "2026-04-01T00:00:00Z",
        },
        agents: [],
      }),
    );

    const api = createApiClient({
      baseUrl: "http://localhost:8001",
      getAccessToken: async () => "token-123",
      fetcher: rawFetcher as unknown as typeof fetch,
    });

    const result = await requestData(
      api.POST("/api/teams", {
        body: {
          name: "Launch Crew",
          description: "Cross-functional team",
          agents: [{ role_template_key: "planner" }],
        },
      }),
    );
    const request = rawFetcher.mock.calls.at(0)?.at(0);

    expect(request).toBeInstanceOf(Request);
    const typedRequest = request as unknown as Request;
    expect(typedRequest.method).toBe("POST");
    await expect(typedRequest.json()).resolves.toEqual({
      name: "Launch Crew",
      description: "Cross-functional team",
      agents: [{ role_template_key: "planner" }],
    });
    expect(result.team.name).toBe("Launch Crew");
  });

  it("unwraps API errors using backend detail", async () => {
    const rawFetcher = vi.fn(async () =>
      jsonResponse(
        {
          detail: "No active GitHub connection.",
        },
        {
          status: 404,
        },
      ),
    );

    const api = createApiClient({
      baseUrl: "http://localhost:8001",
      getAccessToken: async () => "token-123",
      fetcher: rawFetcher as unknown as typeof fetch,
    });

    await expect(requestData(api.GET("/api/auth/github/connection"))).rejects.toThrow(
      "No active GitHub connection.",
    );
  });

  it("streams conversation events with auth", async () => {
    const encoder = new TextEncoder();
    const rawFetcher = vi.fn(async () => {
      const body = new ReadableStream({
        start(controller) {
          controller.enqueue(
            encoder.encode(
              'data: {"event_id":"evt-1","type":"run.completed","conversation_id":"conv-1","timestamp":"2026-04-03T00:00:00Z","sequence":1,"payload":{}}\n\n',
            ),
          );
          controller.close();
        },
      });

      return new Response(body, {
        status: 200,
        headers: {
          "Content-Type": "text/event-stream",
        },
      });
    });

    const api = createApiClient({
      baseUrl: "http://localhost:8001",
      getAccessToken: async () => "token-123",
      fetcher: rawFetcher as unknown as typeof fetch,
    });

    const events: string[] = [];
    const subscription = await api.streamConversationEvents("conv-1", {
      onEvent: (event) => {
        events.push(event.type);
      },
    });

    await subscription.done;

    const streamUrl = rawFetcher.mock.calls.at(0)?.at(0);
    const streamInit = rawFetcher.mock.calls.at(0)?.at(1) as RequestInit | undefined;
    const headers = streamInit?.headers as Headers | undefined;
    expect(streamUrl).toBe("http://localhost:8001/api/conversations/conv-1/stream");
    expect(headers?.get("Authorization")).toBe("Bearer token-123");
    expect(headers?.get("Accept")).toBe("text/event-stream");
    expect(events).toEqual(["run.completed"]);
  });
});
