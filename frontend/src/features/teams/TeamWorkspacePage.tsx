import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, Navigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { Agent, Artifact, AutomationJob, SharedWorkspaceItem, Team } from "../../lib/api";
import { useApiClient, useBackendSession } from "../auth/useSession";

function TeamWorkspaceInner({ teamId }: { teamId: string }) {
  const api = useApiClient();
  const session = useBackendSession();
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState("");
  const [selectedItemId, setSelectedItemId] = useState<string | undefined>(undefined);
  const [selectedTaskId, setSelectedTaskId] = useState<string | undefined>(undefined);
  const [latestGeneratedItemIds, setLatestGeneratedItemIds] = useState<string[]>([]);
  const [selectedRepository, setSelectedRepository] = useState("");
  const [exportPath, setExportPath] = useState("app/team-summary.md");
  const [commitMessage, setCommitMessage] = useState("Export team summary");
  const [pickupAgentId, setPickupAgentId] = useState("");
  const [delegateTargetAgentId, setDelegateTargetAgentId] = useState("");
  const [delegateNote, setDelegateNote] = useState("");
  const [messageAgentId, setMessageAgentId] = useState("");
  const [messageNote, setMessageNote] = useState("");
  const [completionNote, setCompletionNote] = useState("");
  const [selectedSecretIds, setSelectedSecretIds] = useState<string[]>([]);
  const [streamError, setStreamError] = useState<string | null>(null);
  const [jobName, setJobName] = useState("");
  const [jobSchedule, setJobSchedule] = useState("0 9 * * 1");
  const [jobPrompt, setJobPrompt] = useState("");

  const teams = useQuery({
    queryKey: ["teams", session.data?.user.id],
    queryFn: () => api.listTeams(),
    enabled: !!session.data,
  });
  const team = useMemo<Team | null>(
    () => teams.data?.items.find((entry) => entry.id === teamId) ?? null,
    [teamId, teams.data?.items],
  );
  const workspace = useQuery({
    queryKey: ["team-workspace", teamId],
    queryFn: () => api.readTeamWorkspace(teamId),
    enabled: !!team,
  });
  const teamArtifacts = useQuery({
    queryKey: ["team-artifacts", teamId],
    queryFn: () => api.listTeamArtifacts(teamId),
    enabled: !!team,
  });
  const automationJobs = useQuery({
    queryKey: ["automation-jobs", teamId],
    queryFn: () => api.listAutomationJobs({ teamId }),
    enabled: !!team,
  });
  const teamConversations = useQuery({
    queryKey: ["team-conversations", teamId],
    queryFn: () => api.listTeamConversations(teamId),
    enabled: !!team,
  });
  const agents = useQuery({
    queryKey: ["agents", session.data?.user.id],
    queryFn: () => api.listAgents(),
    enabled: !!session.data,
  });
  const teamTasks = useQuery({
    queryKey: ["team-tasks", teamId],
    queryFn: () => api.listTeamTasks(teamId),
    enabled: !!team,
  });
  const taskUpdates = useQuery({
    queryKey: ["task-updates", selectedTaskId],
    queryFn: () => api.listTaskUpdates(selectedTaskId!),
    enabled: !!selectedTaskId,
  });
  const githubConnection = useQuery({
    queryKey: ["github-connection", session.data?.user.id],
    queryFn: () => api.readGitHubConnection(),
    enabled: !!session.data,
    retry: false,
  });
  const pollerStatus = useQuery({
    queryKey: ["system-poller"],
    queryFn: () => api.readPollerStatus(),
    enabled: !!session.data,
    retry: false,
    refetchInterval: 15000,
  });
  const runtimeStatus = useQuery({
    queryKey: ["agent-runtime", pickupAgentId],
    queryFn: () => api.readAgentRuntime(pickupAgentId),
    enabled: !!pickupAgentId,
    retry: false,
    refetchInterval: 15000,
  });
  const provisionRuntime = useMutation({
    mutationFn: () => api.provisionAgentRuntime(pickupAgentId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["agent-runtime", pickupAgentId] });
    },
  });
  const githubRepositories = useQuery({
    queryKey: ["github-repositories", session.data?.user.id],
    queryFn: () => api.listGitHubRepositories(),
    enabled: !!githubConnection.data?.connection,
    retry: false,
  });
  const secrets = useQuery({
    queryKey: ["secrets", session.data?.user.id],
    queryFn: () => api.listSecrets(),
    enabled: !!session.data,
  });
  const verifyRuntime = useMutation({
    mutationFn: () => api.verifyAgentRuntime(pickupAgentId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["agent-runtime", pickupAgentId] });
    },
  });
  const restartRuntime = useMutation({
    mutationFn: () => api.restartAgentRuntime(pickupAgentId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["agent-runtime", pickupAgentId] });
    },
  });

  useEffect(() => {
    if (!workspace.data?.items.length || selectedItemId) {
      return;
    }
    setSelectedItemId(workspace.data.items[0].id);
  }, [selectedItemId, workspace.data?.items]);

  useEffect(() => {
    if (!teamTasks.data?.items.length || selectedTaskId) {
      return;
    }
    setSelectedTaskId(teamTasks.data.items[0].id);
  }, [selectedTaskId, teamTasks.data?.items]);

  useEffect(() => {
    if (!githubRepositories.data?.items.length || selectedRepository) {
      return;
    }
    setSelectedRepository(githubRepositories.data.items[0].full_name);
  }, [githubRepositories.data?.items, selectedRepository]);

  useEffect(() => {
    const activeConversationId = teamConversations.data?.items[0]?.id;
    if (!activeConversationId) {
      return;
    }

    let cancelled = false;
    let closeStream = () => {};
    setStreamError(null);

    void api
      .streamConversationEvents(activeConversationId, {
        onEvent: (event) => {
          if (cancelled) {
            return;
          }
          if (event.type === "workspace.item_created") {
            const itemId = String(event.payload.item_id ?? "");
            if (itemId) {
              setLatestGeneratedItemIds((current) =>
                current.includes(itemId) ? current : [itemId, ...current].slice(0, 4),
              );
              setSelectedItemId(itemId);
            }
            void queryClient.invalidateQueries({ queryKey: ["team-workspace", teamId] });
            return;
          }
          if (event.type === "task.updated") {
            void queryClient.invalidateQueries({ queryKey: ["team-tasks", teamId] });
            void queryClient.invalidateQueries({ queryKey: ["task-updates"] });
            return;
          }
          if (event.type === "runtime.state_changed") {
            void queryClient.invalidateQueries({ queryKey: ["agent-runtime", pickupAgentId] });
          }
        },
        onError: (error) => {
          if (!cancelled) {
            setStreamError(error.message);
          }
        },
      })
      .then((subscription) => {
        if (cancelled) {
          subscription.close();
          return;
        }
        closeStream = subscription.close;
      });

    return () => {
      cancelled = true;
      closeStream();
    };
  }, [api, pickupAgentId, queryClient, teamConversations.data?.items, teamId]);

  const selectedItem = useMemo<SharedWorkspaceItem | null>(
    () => workspace.data?.items.find((item) => item.id === selectedItemId) ?? null,
    [selectedItemId, workspace.data?.items],
  );
  const teamAgents = useMemo<Agent[]>(
    () => (agents.data?.items ?? []).filter((agent) => agent.team_id === teamId),
    [agents.data?.items, teamId],
  );
  const selectedTask = useMemo(
    () => teamTasks.data?.items.find((task) => task.id === selectedTaskId) ?? null,
    [selectedTaskId, teamTasks.data?.items],
  );
  const githubExports = useMemo<Artifact[]>(
    () => (teamArtifacts.data?.items ?? []).filter((item) => item.kind === "github_export"),
    [teamArtifacts.data?.items],
  );
  const latestGeneratedItems = useMemo<SharedWorkspaceItem[]>(
    () =>
      latestGeneratedItemIds
        .map((id) => workspace.data?.items.find((item) => item.id === id) ?? null)
        .filter((item): item is SharedWorkspaceItem => item !== null),
    [latestGeneratedItemIds, workspace.data?.items],
  );

  useEffect(() => {
    if (!selectedItem || exportPath !== "app/team-summary.md") {
      return;
    }
    if (selectedItem.kind === "file") {
      setExportPath(`app/${selectedItem.path.replace(/^\/+/, "")}`);
    }
  }, [exportPath, selectedItem]);

  useEffect(() => {
    if (!selectedTask || delegateTargetAgentId) {
      return;
    }
    const fallbackAgent =
      teamAgents.find((agent) => agent.id !== selectedTask.assigned_agent_id) ??
      teamAgents.find((agent) => agent.id === selectedTask.assigned_agent_id);
    if (fallbackAgent) {
      setDelegateTargetAgentId(fallbackAgent.id);
    }
  }, [delegateTargetAgentId, selectedTask, teamAgents]);

  useEffect(() => {
    if (!selectedTask || messageAgentId) {
      return;
    }
    const fallbackAgent =
      teamAgents.find((agent) => agent.id !== selectedTask.assigned_agent_id) ??
      teamAgents.find((agent) => agent.id === selectedTask.assigned_agent_id);
    if (fallbackAgent) {
      setMessageAgentId(fallbackAgent.id);
    }
  }, [messageAgentId, selectedTask, teamAgents]);

  useEffect(() => {
    if (!teamAgents.length || pickupAgentId) {
      return;
    }
    setPickupAgentId(teamAgents[0].id);
  }, [pickupAgentId, teamAgents]);
  const runHuddle = useMutation({
    mutationFn: () =>
      api.createTeamHuddle(teamId, {
        input: draft.trim(),
        secret_ids: selectedSecretIds,
      }),
    onSuccess: async (payload) => {
      setDraft("");
      setLatestGeneratedItemIds([]);
      setSelectedItemId(payload.workspace_item_id ?? undefined);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["team-workspace", teamId] }),
        queryClient.invalidateQueries({ queryKey: ["team-conversations", teamId] }),
        queryClient.invalidateQueries({ queryKey: ["team-tasks", teamId] }),
      ]);
    },
  });

  const runTeam = useMutation({
    mutationFn: () =>
      api.createTeamResponse(teamId, {
        input: draft.trim(),
        conversation_id: teamConversations.data?.items[0]?.id,
        secret_ids: selectedSecretIds,
      }),
    onSuccess: async (payload) => {
      setDraft("");
      const generatedIds = payload.generated_items.map((item) => item.id);
      setLatestGeneratedItemIds(generatedIds);
      setSelectedItemId(generatedIds[0] ?? payload.workspace_item_id ?? undefined);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["team-workspace", teamId] }),
        queryClient.invalidateQueries({ queryKey: ["team-conversations", teamId] }),
        queryClient.invalidateQueries({ queryKey: ["team-tasks", teamId] }),
      ]);
    },
  });

  const exportMutation = useMutation({
    mutationFn: () =>
      api.exportWorkspaceItemToGitHub(teamId, selectedItemId!, {
        repository_full_name: selectedRepository,
        path: exportPath.trim(),
        commit_message: commitMessage.trim(),
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["team-artifacts", teamId] });
    },
  });

  const delegateTask = useMutation({
    mutationFn: () =>
      api.delegateTask(selectedTaskId!, {
        assigned_agent_id: delegateTargetAgentId,
        note: delegateNote.trim() || undefined,
      }),
    onSuccess: async () => {
      setDelegateNote("");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["team-tasks", teamId] }),
        queryClient.invalidateQueries({ queryKey: ["task-updates"] }),
      ]);
    },
  });

  const postTaskMessage = useMutation({
    mutationFn: () =>
      api.createTaskMessage(selectedTaskId!, {
        agent_id: messageAgentId || undefined,
        content: messageNote.trim(),
      }),
    onSuccess: async () => {
      setMessageNote("");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["team-tasks", teamId] }),
        queryClient.invalidateQueries({ queryKey: ["task-updates"] }),
      ]);
    },
  });

  const pickupNextTask = useMutation({
    mutationFn: () => api.claimNextInboxTask(pickupAgentId),
    onSuccess: async (payload) => {
      if (payload.task) {
        setSelectedTaskId(payload.task.id);
      }
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["team-tasks", teamId] }),
        queryClient.invalidateQueries({ queryKey: ["task-updates"] }),
      ]);
    },
  });

  const runNextInboxTask = useMutation({
    mutationFn: () => api.runNextInboxTask(pickupAgentId),
    onSuccess: async (payload) => {
      if (payload.task) {
        setSelectedTaskId(payload.task.id);
      }
      if (payload.workspace_item_id) {
        setLatestGeneratedItemIds([payload.workspace_item_id]);
        setSelectedItemId(payload.workspace_item_id);
      }
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["team-tasks", teamId] }),
        queryClient.invalidateQueries({ queryKey: ["task-updates"] }),
        queryClient.invalidateQueries({ queryKey: ["team-workspace", teamId] }),
      ]);
    },
  });

  const runInboxCycle = useMutation({
    mutationFn: () => api.runTeamInboxCycle(teamId),
    onSuccess: async (payload) => {
      const firstTaskId = payload.results.find((item) => item.task?.id)?.task?.id;
      const workspaceItemIds = payload.results
        .map((item) => item.workspace_item_id)
        .filter((item): item is string => !!item);
      const firstWorkspaceItemId = workspaceItemIds[0];
      if (firstTaskId) {
        setSelectedTaskId(firstTaskId);
      }
      if (firstWorkspaceItemId) {
        setLatestGeneratedItemIds(workspaceItemIds);
        setSelectedItemId(firstWorkspaceItemId);
      }
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["team-tasks", teamId] }),
        queryClient.invalidateQueries({ queryKey: ["task-updates"] }),
        queryClient.invalidateQueries({ queryKey: ["team-workspace", teamId] }),
      ]);
    },
  });

  const completeSelectedTask = useMutation({
    mutationFn: () =>
      api.completeTask(selectedTaskId!, {
        agent_id: selectedTask?.assigned_agent_id,
        claim_token: selectedTask?.claim_token ?? undefined,
        content: completionNote.trim(),
      }),
    onSuccess: async () => {
      setCompletionNote("");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["team-tasks", teamId] }),
        queryClient.invalidateQueries({ queryKey: ["task-updates"] }),
      ]);
    },
  });
  const createAutomationJob = useMutation({
    mutationFn: () =>
      api.createAutomationJob({
        team_id: teamId,
        name: jobName.trim(),
        schedule: jobSchedule.trim(),
        prompt: jobPrompt.trim(),
      }),
    onSuccess: async () => {
      setJobName("");
      setJobPrompt("");
      await queryClient.invalidateQueries({ queryKey: ["automation-jobs", teamId] });
    },
  });
  const updateAutomationJob = useMutation({
    mutationFn: ({ jobId, enabled }: { jobId: string; enabled: boolean }) =>
      api.updateAutomationJob(jobId, { enabled }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["automation-jobs", teamId] });
    },
  });
  const runAutomationJob = useMutation({
    mutationFn: (jobId: string) => api.runAutomationJob(jobId),
    onSuccess: async (payload) => {
      if (payload.workspace_item_id) {
        setLatestGeneratedItemIds((current) =>
          current.includes(payload.workspace_item_id!)
            ? current
            : [payload.workspace_item_id!, ...current].slice(0, 4),
        );
        setSelectedItemId(payload.workspace_item_id);
      }
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["automation-jobs", teamId] }),
        queryClient.invalidateQueries({ queryKey: ["team-workspace", teamId] }),
        queryClient.invalidateQueries({ queryKey: ["team-conversations", teamId] }),
        queryClient.invalidateQueries({ queryKey: ["team-tasks", teamId] }),
      ]);
    },
  });

  function handleRunTeam(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft.trim()) {
      return;
    }
    void runTeam.mutateAsync();
  }

  function handleRunHuddle() {
    if (!draft.trim()) {
      return;
    }
    void runHuddle.mutateAsync();
  }

  function handleExport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedItemId || !selectedRepository || !exportPath.trim() || !commitMessage.trim()) {
      return;
    }
    void exportMutation.mutateAsync();
  }

  function handleDelegateTask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedTaskId || !delegateTargetAgentId) {
      return;
    }
    void delegateTask.mutateAsync();
  }

  function handlePostTaskMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedTaskId || !messageNote.trim()) {
      return;
    }
    void postTaskMessage.mutateAsync();
  }

  function handlePickupNextTask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!pickupAgentId) {
      return;
    }
    void pickupNextTask.mutateAsync();
  }

  function handleCompleteTask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedTaskId || !completionNote.trim()) {
      return;
    }
    void completeSelectedTask.mutateAsync();
  }

  function toggleSecret(secretId: string) {
    setSelectedSecretIds((current) =>
      current.includes(secretId)
        ? current.filter((id) => id !== secretId)
        : [...current, secretId],
    );
  }

  function handleCreateAutomationJob(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!jobName.trim() || !jobSchedule.trim() || !jobPrompt.trim()) {
      return;
    }
    void createAutomationJob.mutateAsync();
  }

  const teamAutomationJobs = useMemo<AutomationJob[]>(
    () => automationJobs.data?.items ?? [],
    [automationJobs.data?.items],
  );

  return (
    <main className="mx-auto min-h-screen max-w-6xl px-6 pb-24 pt-20">
      <header className="flex items-end justify-between gap-6">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.22em] text-muted">Team Workspace</p>
          <h1 className="mt-4 text-5xl leading-tight">{team?.name ?? "Team"}</h1>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-muted">
            Run a coordinated team pass, keep the result in the shared workspace, and export the final artifact into GitHub.
          </p>
        </div>
        <Link className="text-sm text-muted transition-colors hover:text-primary" to="/">
          Return to Hub
        </Link>
      </header>

      <div className="mt-14 grid gap-8 lg:grid-cols-[1.05fr_0.95fr]">
        <section className="space-y-8">
          <form className="aura-border rounded-lg bg-surface p-5" onSubmit={handleRunTeam}>
            <p className="font-mono text-xs uppercase tracking-[0.18em] text-muted">Team Prompt</p>
            <textarea
              className="mt-5 min-h-40 w-full rounded border border-border bg-background px-4 py-4 text-sm leading-7 text-text outline-none"
              placeholder="Ask the team to huddle on a plan or execute an already aligned task..."
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
            />
            <div className="mt-4">
              <p className="text-xs uppercase tracking-[0.18em] text-muted">Secrets For This Run</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {(secrets.data?.items ?? []).map((secret) => {
                  const selected = selectedSecretIds.includes(secret.id);
                  return (
                    <button
                      className={`rounded border px-2 py-1 text-xs transition-colors ${
                        selected
                          ? "border-primary bg-background text-primary"
                          : "border-border bg-background text-muted hover:border-primary"
                      }`}
                      key={secret.id}
                      onClick={() => toggleSecret(secret.id)}
                      type="button"
                    >
                      {secret.name}
                    </button>
                  );
                })}
                {(secrets.data?.items ?? []).length === 0 ? (
                  <span className="text-xs text-muted">No stored secrets selected.</span>
                ) : null}
              </div>
            </div>
            {runHuddle.error ? <p className="mt-4 text-sm text-primary">{runHuddle.error.message}</p> : null}
            {runTeam.error ? <p className="mt-4 text-sm text-primary">{runTeam.error.message}</p> : null}
            {streamError ? <p className="mt-4 text-sm text-primary">{streamError}</p> : null}
            <div className="mt-5 flex flex-wrap gap-3">
              <button
                className="btn-secondary"
                type="button"
                disabled={runHuddle.isPending}
                onClick={handleRunHuddle}
              >
                {runHuddle.isPending ? "Running Huddle..." : "Run Huddle"}
              </button>
              <button className="btn-primary" type="submit" disabled={runTeam.isPending}>
                {runTeam.isPending ? "Running Team..." : "Run Team"}
              </button>
            </div>
            <p className="mt-4 text-sm text-muted">
              Huddle first to align the team and create explicit owned tasks. Run Team after that to execute the plan.
            </p>
          </form>

          {latestGeneratedItems.length > 0 ? (
            <section className="rounded-lg border border-border bg-background p-5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="font-mono text-xs uppercase tracking-[0.18em] text-muted">Latest Run Outputs</p>
                  <p className="mt-3 text-sm leading-7 text-muted">
                    These files were generated by the most recent coordinated run. Open one to inspect or export it.
                  </p>
                </div>
                <span className="rounded-full border border-border px-3 py-1 text-xs uppercase tracking-[0.16em] text-muted">
                  {latestGeneratedItems.length} file{latestGeneratedItems.length === 1 ? "" : "s"}
                </span>
              </div>
              <div className="mt-5 flex flex-wrap gap-3">
                {latestGeneratedItems.map((item) => (
                  <button
                    className={`rounded border px-3 py-2 text-left text-sm transition-colors ${
                      item.id === selectedItemId
                        ? "border-primary bg-surface text-primary"
                        : "border-border bg-surface text-text hover:border-primary"
                    }`}
                    key={item.id}
                    onClick={() => setSelectedItemId(item.id)}
                    type="button"
                  >
                    {item.path}
                  </button>
                ))}
              </div>
            </section>
          ) : null}

          <section className="rounded-lg border border-border bg-background p-5">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="font-mono text-xs uppercase tracking-[0.18em] text-muted">Scheduler Status</p>
                <p className="mt-3 text-sm leading-7 text-text">
                  {pollerStatus.data?.enabled
                    ? pollerStatus.data.is_active
                      ? "The background inbox poller is active and can keep advancing queued team work."
                      : "The background inbox poller is enabled but currently idle or waiting for its lease."
                    : "The background inbox poller is disabled in this environment."}
                </p>
              </div>
              <div className="rounded-full border border-border px-3 py-1 text-xs uppercase tracking-[0.16em] text-muted">
                {pollerStatus.data?.enabled ? (pollerStatus.data.is_active ? "Active" : "Idle") : "Disabled"}
              </div>
            </div>
            {pollerStatus.data?.lease ? (
              <div className="mt-5 grid gap-3 sm:grid-cols-2">
                <div className="rounded border border-border bg-surface px-4 py-3">
                  <p className="text-xs uppercase tracking-[0.18em] text-muted">Last Sweep</p>
                  <p className="mt-2 text-sm text-text">
                    {pollerStatus.data.lease.last_sweep_completed_at
                      ? new Date(pollerStatus.data.lease.last_sweep_completed_at).toLocaleString()
                      : "No completed sweep yet"}
                  </p>
                </div>
                <div className="rounded border border-border bg-surface px-4 py-3">
                  <p className="text-xs uppercase tracking-[0.18em] text-muted">Sweep Capacity</p>
                  <p className="mt-2 text-sm text-text">
                    {pollerStatus.data.lease.last_executed_count} executed last sweep · max{" "}
                    {pollerStatus.data.max_tasks_per_sweep} per cycle
                  </p>
                </div>
              </div>
            ) : null}
            {pollerStatus.error ? (
              <p className="mt-4 text-sm text-primary">{pollerStatus.error.message}</p>
            ) : null}
          </section>

          <section className="rounded-lg border border-border bg-background p-5">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="font-mono text-xs uppercase tracking-[0.18em] text-muted">Automations</p>
                <p className="mt-3 text-sm leading-7 text-muted">
                  Save repeatable team prompts, keep them disabled until you trust them, and run them on demand while the background scheduler matures.
                </p>
              </div>
              <span className="rounded-full border border-border px-3 py-1 text-xs uppercase tracking-[0.16em] text-muted">
                {teamAutomationJobs.length} job{teamAutomationJobs.length === 1 ? "" : "s"}
              </span>
            </div>
            <form className="mt-5 space-y-4" onSubmit={handleCreateAutomationJob}>
              <input
                className="w-full rounded border border-border bg-surface px-3 py-3 text-sm text-text outline-none"
                placeholder="Weekly Team Review"
                value={jobName}
                onChange={(event) => setJobName(event.target.value)}
              />
              <input
                className="w-full rounded border border-border bg-surface px-3 py-3 text-sm text-text outline-none"
                placeholder="0 9 * * 1"
                value={jobSchedule}
                onChange={(event) => setJobSchedule(event.target.value)}
              />
              <textarea
                className="min-h-24 w-full rounded border border-border bg-surface px-3 py-3 text-sm leading-7 text-text outline-none"
                placeholder="Review the shared workspace, summarize priorities, and flag blocked tasks."
                value={jobPrompt}
                onChange={(event) => setJobPrompt(event.target.value)}
              />
              {createAutomationJob.error ? (
                <p className="text-sm text-primary">{createAutomationJob.error.message}</p>
              ) : null}
              <button className="btn-secondary" disabled={createAutomationJob.isPending} type="submit">
                {createAutomationJob.isPending ? "Saving..." : "Create Automation"}
              </button>
            </form>
            <div className="mt-5 space-y-3">
              {teamAutomationJobs.map((job) => (
                <div className="rounded border border-border bg-surface px-4 py-4" key={job.id}>
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div className="min-w-0 flex-1">
                      <p className="text-sm text-primary">{job.name}</p>
                      <p className="mt-1 text-xs uppercase tracking-[0.18em] text-muted">
                        {job.schedule} · {job.enabled ? "enabled" : "disabled"}
                      </p>
                      <p className="mt-3 text-sm leading-7 text-text">{job.prompt}</p>
                      <p className="mt-2 text-xs text-muted">
                        Last run {job.last_run_at ? new Date(job.last_run_at).toLocaleString() : "not yet run"}
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <button
                        className="btn-secondary"
                        disabled={updateAutomationJob.isPending}
                        onClick={() =>
                          void updateAutomationJob.mutateAsync({
                            jobId: job.id,
                            enabled: !job.enabled,
                          })
                        }
                        type="button"
                      >
                        {job.enabled ? "Disable" : "Enable"}
                      </button>
                      <button
                        className="btn-primary"
                        disabled={!job.enabled || runAutomationJob.isPending}
                        onClick={() => void runAutomationJob.mutateAsync(job.id)}
                        type="button"
                      >
                        {runAutomationJob.isPending ? "Running..." : "Run Now"}
                      </button>
                    </div>
                  </div>
                </div>
              ))}
              {teamAutomationJobs.length === 0 ? (
                <div className="rounded border border-border bg-surface px-4 py-4 text-sm text-muted">
                  No team automations yet. Save one once your repeated team workflow is stable enough to replay.
                </div>
              ) : null}
              {updateAutomationJob.error ? (
                <p className="text-sm text-primary">{updateAutomationJob.error.message}</p>
              ) : null}
              {runAutomationJob.error ? (
                <p className="text-sm text-primary">{runAutomationJob.error.message}</p>
              ) : null}
              {runAutomationJob.data?.output_text ? (
                <div className="rounded border border-border bg-surface px-4 py-3 text-sm text-text">
                  {runAutomationJob.data.output_text}
                </div>
              ) : null}
            </div>
          </section>

          <section className="rounded-lg border border-border bg-background">
            <div className="border-b border-border px-5 py-4">
              <p className="font-mono text-xs uppercase tracking-[0.18em] text-muted">Shared Workspace</p>
            </div>
            <div className="divide-y divide-border">
              {(workspace.data?.items ?? []).map((item) => {
                const selected = item.id === selectedItemId;
                return (
                  <button
                    className={`flex w-full items-start justify-between gap-6 px-5 py-4 text-left transition-colors ${
                      selected ? "bg-surface" : "hover:bg-surface/60"
                    }`}
                    key={item.id}
                    onClick={() => setSelectedItemId(item.id)}
                    type="button"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="text-sm text-primary">{item.path}</p>
                      <p className="mt-1 text-xs uppercase tracking-[0.18em] text-muted">{item.kind}</p>
                    </div>
                    <p className="text-xs text-muted">{item.size_bytes ?? 0} bytes</p>
                  </button>
                );
              })}
              {(workspace.data?.items ?? []).length === 0 ? (
                <div className="px-5 py-6 text-sm text-muted">
                  The workspace is ready. Run a team prompt to generate the first shared output.
                </div>
              ) : null}
            </div>
          </section>

          <section className="rounded-lg border border-border bg-background">
            <div className="border-b border-border px-5 py-4">
              <p className="font-mono text-xs uppercase tracking-[0.18em] text-muted">Assigned Tasks</p>
            </div>
            <form className="border-b border-border px-5 py-4" onSubmit={handlePickupNextTask}>
              <p className="text-xs uppercase tracking-[0.18em] text-muted">Agent Inbox Pickup</p>
              {pickupAgentId ? (
                <div className="mt-3 rounded border border-border bg-surface px-4 py-3">
                  <p className="text-xs uppercase tracking-[0.18em] text-muted">Selected Agent Runtime</p>
                  {runtimeStatus.data?.lease ? (
                    <>
                      <p className="mt-2 text-sm text-text">
                        {runtimeStatus.data.lease.readiness_stage} · {runtimeStatus.data.lease.readiness_reason}
                      </p>
                      <p className="mt-2 text-xs text-muted">
                        State: {runtimeStatus.data.lease.state} · Provider {runtimeStatus.data.lease.provider} · Heartbeat{" "}
                        {runtimeStatus.data.lease.heartbeat_fresh ? "fresh" : "stale"}
                      </p>
                      <p className="mt-2 text-xs text-muted">
                        Isolation {runtimeStatus.data.lease.isolation_ok ? "verified" : "pending"} · {runtimeStatus.data.lease.isolation_reason}
                      </p>
                      {runtimeStatus.data.lease.host_vm_id ? (
                        <p className="mt-2 text-xs text-muted">
                          Host {runtimeStatus.data.lease.host_vm_id}
                        </p>
                      ) : null}
                      {verifyRuntime.error ? (
                        <p className="mt-2 text-xs text-primary">{verifyRuntime.error.message}</p>
                      ) : null}
                      {restartRuntime.error ? (
                        <p className="mt-2 text-xs text-primary">{restartRuntime.error.message}</p>
                      ) : null}
                    </>
                  ) : runtimeStatus.error ? (
                    <p className="mt-2 text-sm text-primary">{runtimeStatus.error.message}</p>
                  ) : (
                    <p className="mt-2 text-sm text-muted">Loading runtime status...</p>
                  )}
                </div>
              ) : null}
              <div className="mt-3 flex flex-wrap gap-3">
                <select
                  className="min-w-56 rounded border border-border bg-surface px-3 py-3 text-sm text-text outline-none"
                  value={pickupAgentId}
                  onChange={(event) => setPickupAgentId(event.target.value)}
                >
                  {teamAgents.map((agent) => (
                    <option key={agent.id} value={agent.id}>
                      {agent.name} · {agent.role_name}
                    </option>
                  ))}
                </select>
                <button className="btn-secondary" disabled={!pickupAgentId || pickupNextTask.isPending} type="submit">
                  {pickupNextTask.isPending ? "Picking Up..." : "Pick Up Next Task"}
                </button>
                <button
                  className="btn-secondary"
                  disabled={!pickupAgentId || provisionRuntime.isPending}
                  onClick={() => void provisionRuntime.mutateAsync()}
                  type="button"
                >
                  {provisionRuntime.isPending ? "Provisioning..." : "Provision Runtime"}
                </button>
                <button
                  className="btn-secondary"
                  disabled={!pickupAgentId || verifyRuntime.isPending}
                  onClick={() => void verifyRuntime.mutateAsync()}
                  type="button"
                >
                  {verifyRuntime.isPending ? "Verifying..." : "Verify Runtime"}
                </button>
                <button
                  className="btn-secondary"
                  disabled={!pickupAgentId || restartRuntime.isPending}
                  onClick={() => void restartRuntime.mutateAsync()}
                  type="button"
                >
                  {restartRuntime.isPending ? "Restarting..." : "Restart Runtime"}
                </button>
                <button
                  className="btn-primary"
                  disabled={!pickupAgentId || runNextInboxTask.isPending}
                  onClick={() => void runNextInboxTask.mutateAsync()}
                  type="button"
                >
                  {runNextInboxTask.isPending ? "Running..." : "Run Next With Runtime"}
                </button>
                <button
                  className="btn-secondary"
                  disabled={runInboxCycle.isPending}
                  onClick={() => void runInboxCycle.mutateAsync()}
                  type="button"
                >
                  {runInboxCycle.isPending ? "Cycling..." : "Run Inbox Cycle"}
                </button>
              </div>
              {pickupNextTask.error ? <p className="mt-3 text-sm text-primary">{pickupNextTask.error.message}</p> : null}
              {provisionRuntime.error ? <p className="mt-3 text-sm text-primary">{provisionRuntime.error.message}</p> : null}
              {runNextInboxTask.error ? <p className="mt-3 text-sm text-primary">{runNextInboxTask.error.message}</p> : null}
              {runInboxCycle.error ? <p className="mt-3 text-sm text-primary">{runInboxCycle.error.message}</p> : null}
              {runNextInboxTask.data?.output_text ? (
                <p className="mt-3 text-sm text-muted">{runNextInboxTask.data.output_text}</p>
              ) : null}
              {runInboxCycle.data ? (
                <div className="mt-3 rounded border border-border bg-surface px-4 py-3">
                  <p className="text-xs uppercase tracking-[0.18em] text-muted">
                    Cycle executed {runInboxCycle.data.executed_count} task
                    {runInboxCycle.data.executed_count === 1 ? "" : "s"}.
                  </p>
                  {(runInboxCycle.data.results ?? [])
                    .filter((item) => item.response_id)
                    .map((item) => (
                      <p className="mt-2 text-sm text-text" key={`${item.agent_id}-${item.response_id}`}>
                        {item.output_text}
                      </p>
                    ))}
                </div>
              ) : null}
            </form>
            <div className="divide-y divide-border">
              {(team?.mode === "team" ? teamTasks.data?.items : [])?.map((task) => (
                <button
                  className={`block w-full px-5 py-4 text-left transition-colors ${
                    task.id === selectedTaskId ? "bg-surface" : "hover:bg-surface/60"
                  }`}
                  key={task.id}
                  onClick={() => setSelectedTaskId(task.id)}
                  type="button"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0 flex-1">
                      <p className="text-sm text-primary">{task.title}</p>
                      <p className="mt-1 text-xs uppercase tracking-[0.18em] text-muted">
                        {task.status}
                      </p>
                      {task.claim_expires_at ? (
                        <p className="mt-2 text-xs text-muted">
                          Lease active until {new Date(task.claim_expires_at).toLocaleTimeString()}.
                        </p>
                      ) : null}
                      {task.completed_at ? (
                        <p className="mt-2 text-xs text-muted">
                          Completed at {new Date(task.completed_at).toLocaleTimeString()}.
                        </p>
                      ) : null}
                    </div>
                  </div>
                  <p className="mt-3 text-sm leading-7 text-text">{task.instruction}</p>
                </button>
              ))}
              {(teamTasks.data?.items ?? []).length === 0 ? (
                <div className="px-5 py-6 text-sm text-muted">
                  Run a huddle to create explicit owned tasks for the team.
                </div>
              ) : null}
            </div>
          </section>
        </section>

        <section className="space-y-8">
          <div className="aura-border rounded-lg bg-surface p-5">
            <p className="font-mono text-xs uppercase tracking-[0.18em] text-muted">Workspace Preview</p>
            <div className="mt-5 min-h-72 rounded border border-border bg-background px-4 py-4">
              {selectedItem?.content_text ? (
                <pre className="whitespace-pre-wrap text-sm leading-7 text-text">{selectedItem.content_text}</pre>
              ) : (
                <p className="text-sm text-muted">Select a workspace item to preview it here.</p>
              )}
            </div>
          </div>

          <section className="rounded-lg border border-border bg-background p-5">
            <p className="font-mono text-xs uppercase tracking-[0.18em] text-muted">Task Details</p>
            {selectedTask ? (
              <>
                <div className="mt-5 rounded border border-border bg-surface px-4 py-4">
                  <p className="text-sm text-primary">{selectedTask.title}</p>
                  <p className="mt-2 text-sm leading-7 text-text">{selectedTask.instruction}</p>
                </div>

                <form className="mt-5 space-y-4" onSubmit={handleDelegateTask}>
                  <label className="block">
                    <span className="text-xs uppercase tracking-[0.18em] text-muted">Delegate To</span>
                    <select
                      className="mt-2 w-full rounded border border-border bg-surface px-3 py-3 text-sm text-text outline-none"
                      value={delegateTargetAgentId}
                      onChange={(event) => setDelegateTargetAgentId(event.target.value)}
                    >
                      {teamAgents.map((agent) => (
                        <option key={agent.id} value={agent.id}>
                          {agent.name} · {agent.role_name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="block">
                    <span className="text-xs uppercase tracking-[0.18em] text-muted">Delegation Note</span>
                    <textarea
                      className="mt-2 min-h-24 w-full rounded border border-border bg-surface px-3 py-3 text-sm leading-7 text-text outline-none"
                      placeholder="Explain why this task should move or what the new owner should focus on..."
                      value={delegateNote}
                      onChange={(event) => setDelegateNote(event.target.value)}
                    />
                  </label>
                  {delegateTask.error ? (
                    <p className="text-sm text-primary">{delegateTask.error.message}</p>
                  ) : null}
                  <button
                    className="btn-secondary"
                    disabled={!delegateTargetAgentId || delegateTask.isPending}
                    type="submit"
                  >
                    {delegateTask.isPending ? "Delegating..." : "Delegate Task"}
                  </button>
                </form>

                <form className="mt-5 space-y-4" onSubmit={handlePostTaskMessage}>
                  <label className="block">
                    <span className="text-xs uppercase tracking-[0.18em] text-muted">Message From</span>
                    <select
                      className="mt-2 w-full rounded border border-border bg-surface px-3 py-3 text-sm text-text outline-none"
                      value={messageAgentId}
                      onChange={(event) => setMessageAgentId(event.target.value)}
                    >
                      {teamAgents.map((agent) => (
                        <option key={agent.id} value={agent.id}>
                          {agent.name} ({agent.role_name})
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="block">
                    <span className="text-xs uppercase tracking-[0.18em] text-muted">Team Message</span>
                    <textarea
                      className="mt-2 min-h-24 w-full rounded border border-border bg-surface px-3 py-3 text-sm leading-7 text-text outline-none"
                      placeholder="Send a note that the assigned agent should see before continuing..."
                      value={messageNote}
                      onChange={(event) => setMessageNote(event.target.value)}
                    />
                  </label>
                  {postTaskMessage.error ? (
                    <p className="text-sm text-primary">{postTaskMessage.error.message}</p>
                  ) : null}
                  <button
                    className="btn-secondary"
                    disabled={!messageNote.trim() || postTaskMessage.isPending}
                    type="submit"
                  >
                    {postTaskMessage.isPending ? "Posting..." : "Post Team Message"}
                  </button>
                </form>

                <div className="mt-6 rounded border border-border bg-surface">
                  <div className="border-b border-border px-4 py-3">
                    <p className="font-mono text-xs uppercase tracking-[0.18em] text-muted">Task Updates</p>
                  </div>
                  <div className="divide-y divide-border">
                    {(taskUpdates.data?.items ?? []).map((update) => (
                      <div className="px-4 py-4" key={update.id}>
                        <p className="text-xs uppercase tracking-[0.18em] text-muted">
                          {update.event_type}
                        </p>
                        <p className="mt-2 text-sm leading-7 text-text">{update.content}</p>
                      </div>
                    ))}
                    {(taskUpdates.data?.items ?? []).length === 0 ? (
                      <div className="px-4 py-4 text-sm text-muted">
                        No task updates yet. Delegation, team messages, report-backs, and completions will appear here.
                      </div>
                    ) : null}
                  </div>
                </div>

                <form className="mt-5 space-y-4" onSubmit={handleCompleteTask}>
                  <label className="block">
                    <span className="text-xs uppercase tracking-[0.18em] text-muted">Completion Note</span>
                    <textarea
                      className="mt-2 min-h-24 w-full rounded border border-border bg-surface px-3 py-3 text-sm leading-7 text-text outline-none"
                      placeholder="Summarize what was finished so the team has a durable report-back."
                      value={completionNote}
                      onChange={(event) => setCompletionNote(event.target.value)}
                    />
                  </label>
                  {completeSelectedTask.error ? (
                    <p className="text-sm text-primary">{completeSelectedTask.error.message}</p>
                  ) : null}
                  <button
                    className="btn-primary"
                    disabled={!completionNote.trim() || completeSelectedTask.isPending}
                    type="submit"
                  >
                    {completeSelectedTask.isPending ? "Completing..." : "Complete Task"}
                  </button>
                </form>
              </>
            ) : (
              <p className="mt-5 text-sm text-muted">
                Select a task to inspect its delegation history and updates.
              </p>
            )}
          </section>

          <form className="rounded-lg border border-border bg-background p-5" onSubmit={handleExport}>
            <p className="font-mono text-xs uppercase tracking-[0.18em] text-muted">GitHub Export</p>
            {!githubConnection.data?.connection ? (
              <p className="mt-4 text-sm text-muted">
                Connect GitHub from the Hub before exporting a workspace item.
              </p>
            ) : (
              <>
                <div className="mt-5 space-y-4">
                  <label className="block">
                    <span className="text-xs uppercase tracking-[0.18em] text-muted">Repository</span>
                    <select
                      className="mt-2 w-full rounded border border-border bg-surface px-3 py-3 text-sm text-text outline-none"
                      value={selectedRepository}
                      onChange={(event) => setSelectedRepository(event.target.value)}
                    >
                      {(githubRepositories.data?.items ?? []).map((repository) => (
                        <option key={repository.full_name} value={repository.full_name}>
                          {repository.full_name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="block">
                    <span className="text-xs uppercase tracking-[0.18em] text-muted">Destination Path</span>
                    <input
                      className="mt-2 w-full rounded border border-border bg-surface px-3 py-3 text-sm text-text outline-none"
                      value={exportPath}
                      onChange={(event) => setExportPath(event.target.value)}
                    />
                  </label>
                  <label className="block">
                    <span className="text-xs uppercase tracking-[0.18em] text-muted">Commit Message</span>
                    <input
                      className="mt-2 w-full rounded border border-border bg-surface px-3 py-3 text-sm text-text outline-none"
                      value={commitMessage}
                      onChange={(event) => setCommitMessage(event.target.value)}
                    />
                  </label>
                </div>
                {exportMutation.error ? (
                  <p className="mt-4 text-sm text-primary">{exportMutation.error.message}</p>
                ) : null}
                {exportMutation.data ? (
                  <div className="mt-4 rounded border border-border bg-surface px-4 py-3 text-sm text-text">
                    <p>
                      Exported to {exportMutation.data.repository_full_name} at {exportPath}.
                    </p>
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
                <button className="btn-primary mt-5" type="submit" disabled={!selectedItemId || exportMutation.isPending}>
                  {exportMutation.isPending ? "Exporting..." : "Export To GitHub"}
                </button>
              </>
            )}
          </form>

          <section className="rounded-lg border border-border bg-background p-5">
            <p className="font-mono text-xs uppercase tracking-[0.18em] text-muted">Export History</p>
            {githubExports.length ? (
              <div className="mt-5 space-y-3">
                {githubExports.slice(0, 5).map((artifact) => (
                  <div className="rounded border border-border bg-surface px-4 py-3" key={artifact.id}>
                    <p className="text-sm text-primary">{artifact.github_repo ?? artifact.name}</p>
                    <p className="mt-1 text-xs uppercase tracking-[0.18em] text-muted">
                      {artifact.github_branch ?? "main"} · {artifact.github_sha?.slice(0, 7) ?? "pending"}
                    </p>
                    <div className="mt-2 flex flex-wrap gap-4 text-sm">
                      {artifact.preview_uri ? (
                        <a
                          className="text-primary underline-offset-4 hover:underline"
                          href={artifact.preview_uri}
                          rel="noreferrer"
                          target="_blank"
                        >
                          Open file
                        </a>
                      ) : null}
                      {artifact.github_repo && artifact.github_sha ? (
                        <a
                          className="text-primary underline-offset-4 hover:underline"
                          href={`https://github.com/${artifact.github_repo}/commit/${artifact.github_sha}`}
                          rel="noreferrer"
                          target="_blank"
                        >
                          Open commit
                        </a>
                      ) : null}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="mt-4 text-sm text-muted">
                Export a workspace item to GitHub and the latest commits will appear here.
              </p>
            )}
          </section>
        </section>
      </div>
    </main>
  );
}

export function TeamWorkspacePage() {
  const params = useParams();
  if (!params.teamId) {
    return <Navigate replace to="/" />;
  }
  return <TeamWorkspaceInner teamId={params.teamId} />;
}
