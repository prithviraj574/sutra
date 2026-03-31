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
        workspace_item_id: "workspace-item-1",
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
    expect(result.workspace_item_id).toBe("workspace-item-1");
  });

  it("reads the active github connection for the hub settings card", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        connection: {
          id: "github-connection-1",
          user_id: "user-1",
          installation_id: "1001",
          account_login: "octocat",
          account_type: "user",
          connected_at: "2026-03-28T00:00:00Z",
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

    const result = await api.readGitHubConnection();

    expect(fetcher).toHaveBeenCalledWith(
      "http://localhost:8000/api/auth/github/connection",
      expect.objectContaining({ headers: expect.any(Headers) }),
    );
    expect(result.connection?.account_login).toBe("octocat");
  });

  it("reads poller status for the team workspace scheduler card", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        enabled: true,
        interval_seconds: 30,
        lease_seconds: 60,
        max_tasks_per_sweep: 4,
        is_active: true,
        lease: {
          id: "lease-1",
          name: "inbox_poller",
          owner_id: "poller-owner",
          state: "idle",
          last_executed_count: 2,
          created_at: "2026-03-30T00:00:00Z",
          updated_at: "2026-03-30T00:00:00Z",
        },
      }),
    });

    const api = createApiClient({
      baseUrl: "http://localhost:8000",
      getAccessToken: async () => "token-123",
      fetcher,
    });

    const result = await api.readPollerStatus();

    expect(fetcher).toHaveBeenCalledWith(
      "http://localhost:8000/api/system/poller",
      expect.objectContaining({ headers: expect.any(Headers) }),
    );
    expect(result.lease?.owner_id).toBe("poller-owner");
    expect(result.max_tasks_per_sweep).toBe(4);
  });

  it("loads role templates and can create a team with selected roles", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          items: [
            {
              id: "role-1",
              key: "planner",
              name: "Planner",
              description: "Shapes work.",
              default_system_prompt: "Plan clearly.",
              default_tool_profile: "full_web",
              created_at: "2026-03-30T00:00:00Z",
              updated_at: "2026-03-30T00:00:00Z",
            },
          ],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          team: {
            id: "team-1",
            user_id: "user-1",
            name: "Launch Crew",
            description: "Cross-functional team",
            mode: "team",
            shared_workspace_uri: "workspace://teams/team-1",
            created_at: "2026-03-30T00:00:00Z",
            updated_at: "2026-03-30T00:00:00Z",
          },
          agents: [
            {
              id: "agent-1",
              team_id: "team-1",
              role_template_id: "role-1",
              name: "Planner Agent",
              role_name: "Planner",
              status: "provisioning",
              runtime_kind: "firecracker",
              shared_workspace_enabled: true,
              created_at: "2026-03-30T00:00:00Z",
              updated_at: "2026-03-30T00:00:00Z",
            },
          ],
        }),
      });

    const api = createApiClient({
      baseUrl: "http://localhost:8000",
      getAccessToken: async () => "token-123",
      fetcher,
    });

    const templates = await api.listRoleTemplates();
    const created = await api.createTeam({
      name: "Launch Crew",
      description: "Cross-functional team",
      agents: [{ role_template_key: "planner" }],
    });

    expect(templates.items[0].key).toBe("planner");
    expect(fetcher).toHaveBeenNthCalledWith(
      2,
      "http://localhost:8000/api/teams",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          name: "Launch Crew",
          description: "Cross-functional team",
          agents: [{ role_template_key: "planner" }],
        }),
      }),
    );
    expect(created.team.mode).toBe("team");
    expect(created.agents[0].role_name).toBe("Planner");
  });

  it("runs a team response and returns per-role outputs", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        conversation_id: "conversation-team-1",
        output_text: "Planner: Plan the launch.\n\nResearcher: Gather market context.",
        outputs: [
          {
            agent_id: "agent-1",
            agent_name: "Planner Agent",
            role_name: "Planner",
            response_id: "resp-planner",
            output_text: "Plan the launch.",
          },
          {
            agent_id: "agent-2",
            agent_name: "Researcher Agent",
            role_name: "Researcher",
            response_id: "resp-researcher",
            output_text: "Gather market context.",
          },
        ],
        workspace_item_id: "workspace-item-1",
      }),
    });

    const api = createApiClient({
      baseUrl: "http://localhost:8000",
      getAccessToken: async () => "token-123",
      fetcher,
    });

    const result = await api.createTeamResponse("team-1", {
      input: "Prepare a launch brief",
    });

    expect(fetcher).toHaveBeenCalledWith(
      "http://localhost:8000/api/teams/team-1/responses",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ input: "Prepare a launch brief" }),
      }),
    );
    expect(result.outputs).toHaveLength(2);
    expect(result.workspace_item_id).toBe("workspace-item-1");
  });

  it("runs a team huddle and returns explicit tasks", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          conversation_id: "conversation-huddle-1",
          output_text: "Planner: Define milestones.\n\nResearcher: Gather market context.",
          outputs: [
            {
              agent_id: "agent-1",
              agent_name: "Planner Agent",
              role_name: "Planner",
              response_id: "resp-huddle-planner",
              output_text: "Define milestones.",
            },
          ],
          tasks: [
            {
              id: "task-1",
              team_id: "team-1",
              conversation_id: "conversation-huddle-1",
              assigned_agent_id: "agent-1",
              title: "Planner Task",
              instruction: "Define milestones.",
              status: "open",
              created_at: "2026-03-30T00:00:00Z",
              updated_at: "2026-03-30T00:00:00Z",
            },
          ],
          workspace_item_id: "workspace-item-1",
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          items: [
            {
              id: "task-1",
              team_id: "team-1",
              conversation_id: "conversation-huddle-1",
              assigned_agent_id: "agent-1",
              title: "Planner Task",
              instruction: "Define milestones.",
              status: "open",
              created_at: "2026-03-30T00:00:00Z",
              updated_at: "2026-03-30T00:00:00Z",
            },
          ],
        }),
      });

    const api = createApiClient({
      baseUrl: "http://localhost:8000",
      getAccessToken: async () => "token-123",
      fetcher,
    });

    const huddle = await api.createTeamHuddle("team-1", {
      input: "Plan the launch brief",
    });
    const tasks = await api.listTeamTasks("team-1");

    expect(fetcher).toHaveBeenNthCalledWith(
      1,
      "http://localhost:8000/api/teams/team-1/huddles",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ input: "Plan the launch brief" }),
      }),
    );
    expect(fetcher).toHaveBeenNthCalledWith(
      2,
      "http://localhost:8000/api/teams/team-1/tasks",
      expect.objectContaining({ headers: expect.any(Headers) }),
    );
    expect(huddle.tasks[0].title).toBe("Planner Task");
    expect(tasks.items[0].status).toBe("open");
  });

  it("reads an agent inbox with claim metadata", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        items: [
          {
            id: "task-1",
            team_id: "team-1",
            conversation_id: "conversation-huddle-1",
            assigned_agent_id: "agent-1",
            title: "Planner Task",
            instruction: "Define milestones.",
            status: "claimed",
            source: "huddle",
            claim_token: "team-run:conversation-1:token",
            claimed_at: "2026-03-30T00:00:00Z",
            claim_expires_at: "2026-03-30T00:05:00Z",
            created_at: "2026-03-30T00:00:00Z",
            updated_at: "2026-03-30T00:00:00Z",
          },
        ],
      }),
    });

    const api = createApiClient({
      baseUrl: "http://localhost:8000",
      getAccessToken: async () => "token-123",
      fetcher,
    });

    const inbox = await api.listAgentInbox("agent-1");

    expect(fetcher).toHaveBeenCalledWith(
      "http://localhost:8000/api/agents/agent-1/inbox",
      expect.objectContaining({ headers: expect.any(Headers) }),
    );
    expect(inbox.items[0].status).toBe("claimed");
    expect(inbox.items[0].claim_expires_at).toBe("2026-03-30T00:05:00Z");
  });

  it("delegates a task and reads its updates", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          task: {
            id: "task-1",
            team_id: "team-1",
            conversation_id: "conversation-huddle-1",
            assigned_agent_id: "agent-2",
            title: "Planner Task",
            instruction: "Define milestones.",
            status: "open",
            source: "huddle",
            created_at: "2026-03-30T00:00:00Z",
            updated_at: "2026-03-30T00:00:00Z",
          },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          items: [
            {
              id: "update-1",
              task_id: "task-1",
              team_id: "team-1",
              agent_id: "agent-2",
              event_type: "delegated",
              content: "Researcher should own the synthesis.",
              created_at: "2026-03-30T00:00:00Z",
              updated_at: "2026-03-30T00:00:00Z",
            },
          ],
        }),
      });

    const api = createApiClient({
      baseUrl: "http://localhost:8000",
      getAccessToken: async () => "token-123",
      fetcher,
    });

    const delegated = await api.delegateTask("task-1", {
      assigned_agent_id: "agent-2",
      note: "Researcher should own the synthesis.",
    });
    const updates = await api.listTaskUpdates("task-1");

    expect(fetcher).toHaveBeenNthCalledWith(
      1,
      "http://localhost:8000/api/tasks/task-1/delegate",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          assigned_agent_id: "agent-2",
          note: "Researcher should own the synthesis.",
        }),
      }),
    );
    expect(fetcher).toHaveBeenNthCalledWith(
      2,
      "http://localhost:8000/api/tasks/task-1/updates",
      expect.objectContaining({ headers: expect.any(Headers) }),
    );
    expect(delegated.task.assigned_agent_id).toBe("agent-2");
    expect(updates.items[0].event_type).toBe("delegated");
  });

  it("claims the next inbox task and completes it", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          task: {
            id: "task-1",
            team_id: "team-1",
            conversation_id: "conversation-huddle-1",
            assigned_agent_id: "agent-1",
            title: "Planner Task",
            instruction: "Define milestones.",
            status: "claimed",
            source: "huddle",
            claim_token: "agent-inbox:agent-1:token",
            claimed_at: "2026-03-30T00:00:00Z",
            claim_expires_at: "2026-03-30T00:05:00Z",
            created_at: "2026-03-30T00:00:00Z",
            updated_at: "2026-03-30T00:00:00Z",
          },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          task: {
            id: "task-1",
            team_id: "team-1",
            conversation_id: "conversation-huddle-1",
            assigned_agent_id: "agent-1",
            title: "Planner Task",
            instruction: "Define milestones.",
            status: "completed",
            source: "huddle",
            created_at: "2026-03-30T00:00:00Z",
            updated_at: "2026-03-30T00:01:00Z",
          },
        }),
      });

    const api = createApiClient({
      baseUrl: "http://localhost:8000",
      getAccessToken: async () => "token-123",
      fetcher,
    });

    const claimed = await api.claimNextInboxTask("agent-1");
    const completed = await api.completeTask("task-1", {
      agent_id: "agent-1",
      claim_token: "agent-inbox:agent-1:token",
      content: "Completed the milestone outline.",
    });

    expect(fetcher).toHaveBeenNthCalledWith(
      1,
      "http://localhost:8000/api/agents/agent-1/inbox/claim-next",
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetcher).toHaveBeenNthCalledWith(
      2,
      "http://localhost:8000/api/tasks/task-1/complete",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          agent_id: "agent-1",
          claim_token: "agent-inbox:agent-1:token",
          content: "Completed the milestone outline.",
        }),
      }),
    );
    expect(claimed.task?.status).toBe("claimed");
    expect(completed.task.status).toBe("completed");
  });

  it("posts a task-scoped team message", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        task: {
          id: "task-1",
          team_id: "team-1",
          conversation_id: "conversation-huddle-1",
          assigned_agent_id: "agent-1",
          title: "Planner Task",
          instruction: "Define milestones.",
          status: "open",
          source: "huddle",
          created_at: "2026-03-30T00:00:00Z",
          updated_at: "2026-03-30T00:04:00Z",
        },
      }),
    });

    const api = createApiClient({
      baseUrl: "http://localhost:8000",
      getAccessToken: async () => "token-123",
      fetcher,
    });

    const result = await api.createTaskMessage("task-1", {
      agent_id: "agent-2",
      content: "Please add two competitor examples.",
    });

    expect(fetcher).toHaveBeenCalledWith(
      "http://localhost:8000/api/tasks/task-1/messages",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          agent_id: "agent-2",
          content: "Please add two competitor examples.",
        }),
      }),
    );
    expect(result.task.id).toBe("task-1");
  });

  it("runs the next inbox task through the runtime loop", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        task: {
          id: "task-1",
          team_id: "team-1",
          conversation_id: "conversation-agent-task-1",
          assigned_agent_id: "agent-1",
          title: "Planner Task",
          instruction: "Define milestones.",
          status: "completed",
          source: "huddle",
          created_at: "2026-03-30T00:00:00Z",
          updated_at: "2026-03-30T00:03:00Z",
        },
        conversation_id: "conversation-agent-task-1",
        response_id: "resp-runtime-1",
        output_text: "Completed the milestone outline through the runtime loop.",
        workspace_item_id: "workspace-item-1",
      }),
    });

    const api = createApiClient({
      baseUrl: "http://localhost:8000",
      getAccessToken: async () => "token-123",
      fetcher,
    });

    const result = await api.runNextInboxTask("agent-1");

    expect(fetcher).toHaveBeenCalledWith(
      "http://localhost:8000/api/agents/agent-1/inbox/run-next",
      expect.objectContaining({ method: "POST" }),
    );
    expect(result.task?.status).toBe("completed");
    expect(result.response_id).toBe("resp-runtime-1");
    expect(result.workspace_item_id).toBe("workspace-item-1");
  });

  it("runs a team inbox cycle", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        executed_count: 2,
        results: [
          {
            agent_id: "agent-1",
            task: {
              id: "task-1",
              team_id: "team-1",
              conversation_id: "conversation-agent-task-1",
              assigned_agent_id: "agent-1",
              title: "Planner Task",
              instruction: "Define milestones.",
              status: "completed",
              source: "huddle",
              created_at: "2026-03-30T00:00:00Z",
              updated_at: "2026-03-30T00:03:00Z",
            },
            conversation_id: "conversation-agent-task-1",
            response_id: "resp-cycle-1",
            output_text: "Planner completed the cycle task.",
            workspace_item_id: "workspace-item-1",
          },
          {
            agent_id: "agent-2",
            task: {
              id: "task-2",
              team_id: "team-1",
              conversation_id: "conversation-agent-task-2",
              assigned_agent_id: "agent-2",
              title: "Researcher Task",
              instruction: "Research competitors.",
              status: "completed",
              source: "huddle",
              created_at: "2026-03-30T00:00:00Z",
              updated_at: "2026-03-30T00:04:00Z",
            },
            conversation_id: "conversation-agent-task-2",
            response_id: "resp-cycle-2",
            output_text: "Researcher completed the cycle task.",
            workspace_item_id: "workspace-item-2",
          },
        ],
      }),
    });

    const api = createApiClient({
      baseUrl: "http://localhost:8000",
      getAccessToken: async () => "token-123",
      fetcher,
    });

    const result = await api.runTeamInboxCycle("team-1");

    expect(fetcher).toHaveBeenCalledWith(
      "http://localhost:8000/api/teams/team-1/inbox/run-cycle",
      expect.objectContaining({ method: "POST" }),
    );
    expect(result.executed_count).toBe(2);
    expect(result.results[1].response_id).toBe("resp-cycle-2");
    expect(result.results[0].workspace_item_id).toBe("workspace-item-1");
  });

  it("runs a team response and returns generated workspace items", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        conversation_id: "conversation-team-1",
        output_text: "Planner: Planned the launch brief.\n\nResearcher: Collected market notes.",
        outputs: [
          {
            agent_id: "agent-1",
            agent_name: "Planner Agent",
            role_name: "Planner",
            response_id: "resp-plan",
            output_text: "Planned the launch brief.",
          },
          {
            agent_id: "agent-2",
            agent_name: "Researcher Agent",
            role_name: "Researcher",
            response_id: "resp-research",
            output_text: "Collected market notes.",
          },
        ],
        workspace_item_id: "workspace-summary-1",
        generated_items: [
          {
            id: "workspace-item-1",
            team_id: "team-1",
            path: "tasks/task-1/output.md",
            kind: "file",
            content_text: "Planner output",
            conversation_id: "conversation-team-1",
            agent_id: "agent-1",
            created_at: "2026-03-30T00:00:00Z",
            updated_at: "2026-03-30T00:01:00Z",
          },
          {
            id: "workspace-item-2",
            team_id: "team-1",
            path: "tasks/task-2/output.md",
            kind: "file",
            content_text: "Researcher output",
            conversation_id: "conversation-team-1",
            agent_id: "agent-2",
            created_at: "2026-03-30T00:00:00Z",
            updated_at: "2026-03-30T00:01:30Z",
          },
        ],
      }),
    });

    const api = createApiClient({
      baseUrl: "http://localhost:8000",
      getAccessToken: async () => "token-123",
      fetcher,
    });

    const result = await api.createTeamResponse("team-1", {
      input: "Execute the agreed launch brief plan.",
    });

    expect(fetcher).toHaveBeenCalledWith(
      "http://localhost:8000/api/teams/team-1/responses",
      expect.objectContaining({ method: "POST" }),
    );
    expect(result.generated_items).toHaveLength(2);
    expect(result.generated_items[0].path).toBe("tasks/task-1/output.md");
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

  it("reads a team workspace preview for the hub", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        team: {
          id: "team-1",
          user_id: "user-1",
          name: "Launch Crew",
          mode: "team",
          created_at: "2026-03-30T00:00:00Z",
          updated_at: "2026-03-30T00:00:00Z",
        },
        items: [
          {
            id: "workspace-item-1",
            team_id: "team-1",
            path: "README.md",
            kind: "file",
            created_at: "2026-03-30T00:00:00Z",
            updated_at: "2026-03-30T00:00:00Z",
          },
        ],
      }),
    });

    const api = createApiClient({
      baseUrl: "http://localhost:8000",
      getAccessToken: async () => "token-123",
      fetcher,
    });

    const workspace = await api.readTeamWorkspace("team-1");

    expect(fetcher).toHaveBeenCalledWith(
      "http://localhost:8000/api/teams/team-1/workspace",
      expect.objectContaining({ headers: expect.any(Headers) }),
    );
    expect(workspace.items[0].path).toBe("README.md");
  });

  it("lists repositories and exports a workspace item to github", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          items: [
            {
              id: 1,
              name: "launch-repo",
              full_name: "octocat/launch-repo",
              default_branch: "main",
              private: true,
            },
          ],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          artifact_id: "artifact-1",
          artifact: {
            id: "artifact-1",
            team_id: "team-1",
            name: "team-summary.md",
            kind: "github_export",
            uri: "github://octocat/launch-repo/app/team-summary.md",
            preview_uri: "https://github.com/octocat/launch-repo/blob/main/app/team-summary.md",
            github_repo: "octocat/launch-repo",
            github_branch: "main",
            github_sha: "commit-sha-123",
            created_at: "2026-03-30T00:00:00Z",
            updated_at: "2026-03-30T00:00:00Z",
          },
          item: {
            id: "workspace-item-1",
            team_id: "team-1",
            path: "conversations/team-summary.md",
            kind: "file",
            content_text: "# Summary",
            created_at: "2026-03-30T00:00:00Z",
            updated_at: "2026-03-30T00:00:00Z",
          },
          repository_full_name: "octocat/launch-repo",
          branch: "main",
          commit_sha: "commit-sha-123",
          content_url: "https://github.com/octocat/launch-repo/blob/main/app/team-summary.md",
          commit_url: "https://github.com/octocat/launch-repo/commit/commit-sha-123",
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          items: [
            {
              id: "artifact-1",
              team_id: "team-1",
              name: "team-summary.md",
              kind: "github_export",
              uri: "github://octocat/launch-repo/app/team-summary.md",
              preview_uri: "https://github.com/octocat/launch-repo/blob/main/app/team-summary.md",
              github_repo: "octocat/launch-repo",
              github_branch: "main",
              github_sha: "commit-sha-123",
              created_at: "2026-03-30T00:00:00Z",
              updated_at: "2026-03-30T00:00:00Z",
            },
          ],
        }),
      });

    const api = createApiClient({
      baseUrl: "http://localhost:8000",
      getAccessToken: async () => "token-123",
      fetcher,
    });

    const repositories = await api.listGitHubRepositories();
    const exported = await api.exportWorkspaceItemToGitHub("team-1", "workspace-item-1", {
      repository_full_name: "octocat/launch-repo",
      path: "app/team-summary.md",
      commit_message: "Export team summary",
    });
    const artifacts = await api.listTeamArtifacts("team-1");

    expect(repositories.items[0].full_name).toBe("octocat/launch-repo");
    expect(fetcher).toHaveBeenNthCalledWith(
      2,
      "http://localhost:8000/api/github/teams/team-1/workspace/items/workspace-item-1/export",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          repository_full_name: "octocat/launch-repo",
          path: "app/team-summary.md",
          commit_message: "Export team summary",
        }),
      }),
    );
    expect(exported.commit_sha).toBe("commit-sha-123");
    expect(exported.commit_url).toBe("https://github.com/octocat/launch-repo/commit/commit-sha-123");
    expect(artifacts.items[0].github_repo).toBe("octocat/launch-repo");
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
