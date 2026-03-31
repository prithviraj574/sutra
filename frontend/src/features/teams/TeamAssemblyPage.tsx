import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { RoleTemplate } from "../../lib/api";
import { useApiClient, useBackendSession } from "../auth/useSession";

const DEFAULT_ROLE_KEYS = ["planner", "researcher", "builder"];

function getInitialSelection(templates: RoleTemplate[]): string[] {
  const preferred = DEFAULT_ROLE_KEYS.filter((key) =>
    templates.some((template) => template.key === key),
  );
  if (preferred.length > 0) {
    return preferred;
  }
  return templates.slice(0, 3).map((template) => template.key);
}

export function TeamAssemblyPage() {
  const api = useApiClient();
  const session = useBackendSession();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [name, setName] = useState("Launch Crew");
  const [description, setDescription] = useState(
    "A focused cross-functional team for research, planning, and execution.",
  );
  const [selectedKeys, setSelectedKeys] = useState<string[]>([]);

  const templates = useQuery({
    queryKey: ["role-templates", session.data?.user.id],
    queryFn: () => api.listRoleTemplates(),
    enabled: !!session.data,
  });

  useEffect(() => {
    if (!templates.data?.items.length || selectedKeys.length > 0) {
      return;
    }
    setSelectedKeys(getInitialSelection(templates.data.items));
  }, [selectedKeys.length, templates.data?.items]);

  const selectedTemplates = useMemo(
    () =>
      (templates.data?.items ?? []).filter((template) =>
        selectedKeys.includes(template.key),
      ),
    [selectedKeys, templates.data?.items],
  );

  const createTeam = useMutation({
    mutationFn: () =>
      api.createTeam({
        name: name.trim(),
        description: description.trim() || undefined,
        agents: selectedKeys.map((key) => ({ role_template_key: key })),
      }),
    onSuccess: async (payload) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["teams", session.data?.user.id] }),
        queryClient.invalidateQueries({ queryKey: ["agents", session.data?.user.id] }),
      ]);
      navigate(`/?teamCreated=1&teamId=${payload.team.id}`, { replace: true });
    },
  });

  function toggleRole(key: string) {
    setSelectedKeys((current) =>
      current.includes(key)
        ? current.filter((entry) => entry !== key)
        : [...current, key],
    );
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim() || selectedKeys.length === 0) {
      return;
    }
    void createTeam.mutateAsync();
  }

  return (
    <main className="mx-auto min-h-screen max-w-5xl px-6 pb-24 pt-20">
      <header className="flex items-end justify-between gap-6">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.22em] text-muted">Agent Assembly</p>
          <h1 className="mt-4 text-5xl leading-tight">Create a role-based team.</h1>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-muted">
            Start with a small, distinct crew. Phase 1 is about giving one user a practical team that can plan, research, and build together.
          </p>
        </div>
        <Link className="text-sm text-muted transition-colors hover:text-primary" to="/">
          Return to Hub
        </Link>
      </header>

      <form className="mt-14 grid gap-10 lg:grid-cols-[420px_1fr]" onSubmit={handleSubmit}>
        <section className="aura-border rounded-lg bg-surface p-5">
          <p className="font-mono text-xs uppercase tracking-[0.18em] text-muted">Team Setup</p>
          <div className="mt-6 space-y-4">
            <label className="block">
              <span className="text-xs uppercase tracking-[0.18em] text-muted">Team Name</span>
              <input
                className="mt-2 w-full rounded border border-border bg-background px-3 py-3 text-sm text-text outline-none"
                value={name}
                onChange={(event) => setName(event.target.value)}
              />
            </label>
            <label className="block">
              <span className="text-xs uppercase tracking-[0.18em] text-muted">Mission</span>
              <textarea
                className="mt-2 min-h-28 w-full rounded border border-border bg-background px-3 py-3 text-sm text-text outline-none"
                value={description}
                onChange={(event) => setDescription(event.target.value)}
              />
            </label>
          </div>

          <div className="mt-8 rounded border border-border bg-background px-4 py-4">
            <p className="font-mono text-xs uppercase tracking-[0.18em] text-muted">Selected Roles</p>
            {selectedTemplates.length > 0 ? (
              <div className="mt-3 flex flex-wrap gap-2">
                {selectedTemplates.map((template) => (
                  <span className="rounded border border-border px-2 py-1 text-xs text-primary" key={template.key}>
                    {template.name}
                  </span>
                ))}
              </div>
            ) : (
              <p className="mt-3 text-sm text-muted">Select at least one distinct role.</p>
            )}
          </div>

          {createTeam.error ? (
            <p className="mt-4 text-sm text-primary">{createTeam.error.message}</p>
          ) : null}

          <button className="btn-primary mt-8" type="submit" disabled={createTeam.isPending}>
            {createTeam.isPending ? "Creating Team..." : "Create Team"}
          </button>
        </section>

        <section>
          <p className="font-mono text-xs uppercase tracking-[0.18em] text-muted">Role Templates</p>
          <div className="mt-6 grid gap-4">
            {(templates.data?.items ?? []).map((template) => {
              const selected = selectedKeys.includes(template.key);
              return (
                <button
                  className={`text-left rounded-lg border p-5 transition-colors ${
                    selected
                      ? "aura-border bg-surface"
                      : "border-border bg-background hover:bg-surface"
                  }`}
                  key={template.key}
                  onClick={() => toggleRole(template.key)}
                  type="button"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-base text-primary">{template.name}</p>
                      <p className="mt-2 text-sm leading-7 text-muted">
                        {template.description}
                      </p>
                    </div>
                    <span className="text-xs uppercase tracking-[0.18em] text-muted">
                      {selected ? "Selected" : "Add"}
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        </section>
      </form>
    </main>
  );
}
