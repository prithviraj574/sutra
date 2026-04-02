import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { TeamAssemblyPage } from "./TeamAssemblyPage";

const navigateMock = vi.fn();
const api = {
  getRoleTemplates: vi.fn(),
  createTeam: vi.fn(),
};

vi.mock("../auth/useSession", () => ({
  useApiClient: () => api,
  useBackendSession: () => ({
    data: { user: { id: "user-1" } },
  }),
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => navigateMock,
  };
});

describe("TeamAssemblyPage", () => {
  beforeEach(() => {
    navigateMock.mockReset();
    api.getRoleTemplates.mockReset();
    api.createTeam.mockReset();
  });

  it("navigates to the hub after a successful team create", async () => {
    api.getRoleTemplates.mockResolvedValue({
      items: [
        {
          id: "role-planner",
          key: "planner",
          name: "Planner",
          description: "Plans the work.",
          default_system_prompt: "",
          default_tool_profile: "full_web",
          created_at: "2026-04-01T00:00:00Z",
          updated_at: "2026-04-01T00:00:00Z",
        },
        {
          id: "role-researcher",
          key: "researcher",
          name: "Researcher",
          description: "Researches the work.",
          default_system_prompt: "",
          default_tool_profile: "full_web",
          created_at: "2026-04-01T00:00:00Z",
          updated_at: "2026-04-01T00:00:00Z",
        },
        {
          id: "role-builder",
          key: "builder",
          name: "Builder",
          description: "Builds the work.",
          default_system_prompt: "",
          default_tool_profile: "full_web",
          created_at: "2026-04-01T00:00:00Z",
          updated_at: "2026-04-01T00:00:00Z",
        },
      ],
    });
    api.createTeam.mockResolvedValue({
      team: { id: "team-123" },
      agents: [],
    });

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <TeamAssemblyPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await screen.findByText("Planner");

    fireEvent.click(screen.getByRole("button", { name: "Create Team" }));

    await waitFor(() => {
      expect(api.getRoleTemplates).toHaveBeenCalledWith();
      expect(api.createTeam).toHaveBeenCalledWith({
        body: {
          name: "Launch Crew",
          description: "A focused cross-functional team for research, planning, and execution.",
          agents: [
            { role_template_key: "planner" },
            { role_template_key: "researcher" },
            { role_template_key: "builder" },
          ],
        },
      });
      expect(navigateMock).toHaveBeenCalledWith("/?teamCreated=1&teamId=team-123", {
        replace: true,
      });
    });
  });
});
