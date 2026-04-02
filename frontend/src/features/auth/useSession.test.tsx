import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useBackendSession } from "./useSession";

const { readSession, createApiClient, useAuth } = vi.hoisted(() => {
  const readSession = vi.fn();
  return {
    readSession,
    createApiClient: vi.fn(() => ({ readSession })),
    useAuth: vi.fn(),
  };
});

vi.mock("../../lib/api", () => ({
  createApiClient,
}));

vi.mock("../../lib/env", () => ({
  readFrontendEnv: () => ({
    apiBaseUrl: "http://localhost:8001",
    authMode: "firebase",
    firebaseConfig: null,
  }),
}));

vi.mock("./AuthProvider", () => ({
  useAuth: () => useAuth(),
}));

function SessionProbe() {
  const session = useBackendSession();
  return <div>{session.data?.user.email ?? session.status}</div>;
}

describe("useBackendSession", () => {
  beforeEach(() => {
    readSession.mockReset();
    createApiClient.mockClear();
    useAuth.mockReset();
  });

  it("re-syncs the backend session when the firebase token changes", async () => {
    const authState = {
      firebaseEnabled: true,
      loading: false,
      authError: null,
      tokenVersion: 1,
      user: { uid: "firebase-user-1" },
      getAccessToken: vi.fn(async () => "token-123"),
      signIn: vi.fn(),
      signOutUser: vi.fn(),
    };

    readSession.mockResolvedValue({
      user: {
        id: "user-1",
        firebase_uid: "firebase-user-1",
        email: "user@example.com",
        created_at: "2026-04-01T00:00:00Z",
        updated_at: "2026-04-01T00:00:00Z",
      },
    });
    useAuth.mockImplementation(() => authState);

    const queryClient = new QueryClient();
    const view = render(
      <QueryClientProvider client={queryClient}>
        <SessionProbe />
      </QueryClientProvider>,
    );

    await screen.findByText("user@example.com");
    expect(readSession).toHaveBeenCalledTimes(1);

    authState.tokenVersion = 2;
    view.rerender(
      <QueryClientProvider client={queryClient}>
        <SessionProbe />
      </QueryClientProvider>,
    );

    await waitFor(() => expect(readSession).toHaveBeenCalledTimes(2));
  });
});
