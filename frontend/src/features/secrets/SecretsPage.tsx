import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useApiClient, useBackendSession } from "../auth/useSession";

export function SecretsPage() {
  const api = useApiClient();
  const session = useBackendSession();
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [value, setValue] = useState("");
  const [provider, setProvider] = useState("");

  const secrets = useQuery({
    queryKey: ["secrets", session.data?.user.id],
    queryFn: () => api.listSecrets(),
    enabled: !!session.data,
  });

  const createSecret = useMutation({
    mutationFn: () =>
      api.createSecret({
        body: {
          name: name.trim(),
          value: value.trim(),
          provider: provider.trim() || undefined,
          scope: "user",
        },
      }),
    onSuccess: async () => {
      setName("");
      setValue("");
      setProvider("");
      await queryClient.invalidateQueries({ queryKey: ["secrets", session.data?.user.id] });
    },
  });

  const deleteSecret = useMutation({
    mutationFn: (secretId: string) =>
      api.removeSecret({
        params: {
          path: {
            secret_id: secretId,
          },
        },
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["secrets", session.data?.user.id] });
    },
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim() || !value.trim()) {
      return;
    }
    void createSecret.mutateAsync();
  }

  return (
    <main className="mx-auto min-h-screen max-w-5xl px-6 pb-24 pt-20">
      <header className="flex items-end justify-between gap-6">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.22em] text-muted">Secret Vault</p>
          <h1 className="mt-4 text-5xl leading-tight">Keep provider credentials out of runtime files.</h1>
        </div>
        <Link className="text-sm text-muted transition-colors hover:text-primary" to="/">
          Return to Hub
        </Link>
      </header>

      <section className="mt-14 grid gap-10 lg:grid-cols-[420px_1fr]">
        <form className="aura-border rounded-lg bg-surface p-5" onSubmit={handleSubmit}>
          <p className="font-mono text-xs uppercase tracking-[0.18em] text-muted">Add Secret</p>
          <div className="mt-6 space-y-4">
            <label className="block">
              <span className="text-xs uppercase tracking-[0.18em] text-muted">Name</span>
              <input
                className="mt-2 w-full rounded border border-border bg-background px-3 py-3 text-sm text-text outline-none"
                placeholder="GITHUB_TOKEN"
                value={name}
                onChange={(event) => setName(event.target.value)}
              />
            </label>
            <label className="block">
              <span className="text-xs uppercase tracking-[0.18em] text-muted">Provider</span>
              <input
                className="mt-2 w-full rounded border border-border bg-background px-3 py-3 text-sm text-text outline-none"
                placeholder="github"
                value={provider}
                onChange={(event) => setProvider(event.target.value)}
              />
            </label>
            <label className="block">
              <span className="text-xs uppercase tracking-[0.18em] text-muted">Secret Value</span>
              <textarea
                className="mt-2 min-h-32 w-full rounded border border-border bg-background px-3 py-3 text-sm text-text outline-none"
                placeholder="Paste the credential value. It is encrypted server-side and only injected into an agent run when requested."
                value={value}
                onChange={(event) => setValue(event.target.value)}
              />
            </label>
          </div>
          <button className="btn-primary mt-6" type="submit">
            Save Secret
          </button>
        </form>

        <section>
          <p className="font-mono text-xs uppercase tracking-[0.18em] text-muted">Stored Secrets</p>
          <div className="mt-6 divide-y divide-border rounded border border-border bg-background">
            {(secrets.data?.items ?? []).length === 0 ? (
              <div className="px-5 py-8 text-sm text-muted">
                No secrets stored yet. Add credentials here and attach them to agent runs without persisting them into `HERMES_HOME`.
              </div>
            ) : (
              secrets.data?.items.map((secret) => (
                <div className="flex items-center justify-between gap-6 px-5 py-4" key={secret.id}>
                  <div>
                    <p className="text-sm text-primary">{secret.name}</p>
                    <p className="mt-1 text-xs uppercase tracking-[0.18em] text-muted">
                      {secret.provider ?? "custom"} · {secret.scope}
                    </p>
                  </div>
                  <button
                    className="text-sm text-muted transition-colors hover:text-primary"
                    onClick={() => void deleteSecret.mutateAsync(secret.id)}
                    type="button"
                  >
                    Delete
                  </button>
                </div>
              ))
            )}
          </div>
        </section>
      </section>
    </main>
  );
}
