"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type GitAccount = { provider: string; username: string; workspace_repo: string };

export function GitAccountForm({ initial }: { initial: GitAccount | null }) {
  const router = useRouter();
  const [provider, setProvider] = useState<"github" | "gitlab">(
    (initial?.provider as "github" | "gitlab") || "github"
  );
  const [token, setToken] = useState("");
  const [repo, setRepo] = useState(initial?.workspace_repo || "");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setStatus(null);
    try {
      const r = await fetch("/api/generator/git-accounts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider, token, workspace_repo: repo }),
      });
      if (!r.ok) {
        const body = await r.json().catch(() => ({}));
        throw new Error(body.detail || r.statusText);
      }
      setStatus("Git account linked. New generations will be pushed here.");
      setToken("");
      router.refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function disconnect() {
    setLoading(true);
    setError(null);
    setStatus(null);
    try {
      const r = await fetch("/api/generator/git-accounts/me", { method: "DELETE" });
      if (!r.ok) throw new Error(r.statusText);
      setStatus("Disconnected.");
      setRepo("");
      router.refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={save} className="space-y-4">
      {initial && (
        <div className="rounded-md border border-border bg-muted/40 p-3 text-sm">
          Currently linked: <span className="font-medium">{initial.provider}</span> —{" "}
          <span className="font-mono">{initial.username}</span>, workspace repo{" "}
          <span className="font-mono">{initial.workspace_repo}</span>
        </div>
      )}

      <div className="space-y-1">
        <label className="text-sm font-medium">Provider</label>
        <div className="flex gap-4">
          {(["github", "gitlab"] as const).map((p) => (
            <label key={p} className="flex items-center gap-2 text-sm">
              <Input
                type="radio"
                name="provider"
                value={p}
                checked={provider === p}
                onChange={() => setProvider(p)}
                className="h-4 w-4"
              />
              {p === "github" ? "GitHub" : "GitLab"}
            </label>
          ))}
        </div>
      </div>

      <div className="space-y-1">
        <label className="text-sm font-medium" htmlFor="repo">
          Workspace repo (owner/repo)
        </label>
        <Input
          id="repo"
          required
          placeholder="yourname/aura-workspace"
          value={repo}
          onChange={(e) => setRepo(e.target.value)}
        />
        <p className="text-xs text-muted-foreground">
          You must create this repo yourself first. Each generated app is pushed to{" "}
          <code className="font-mono">apps/&lt;slug&gt;/</code> inside it.
        </p>
      </div>

      <div className="space-y-1">
        <label className="text-sm font-medium" htmlFor="token">
          Personal Access Token
        </label>
        <Input
          id="token"
          type="password"
          required={!initial}
          placeholder={initial ? "••••• (leave blank to keep existing)" : "ghp_... / glpat-..."}
          value={token}
          onChange={(e) => setToken(e.target.value)}
        />
        <p className="text-xs text-muted-foreground">
          GitHub: needs <code>repo</code> scope. GitLab: needs{" "}
          <code>api</code> + <code>write_repository</code>. Stored encrypted.
        </p>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}
      {status && <p className="text-sm text-green-700">{status}</p>}

      <div className="flex gap-2">
        <Button type="submit" variant="accent" disabled={loading || (!token && !initial)}>
          {loading ? "Saving..." : initial ? "Update" : "Link account"}
        </Button>
        {initial && (
          <Button type="button" variant="outline" onClick={disconnect} disabled={loading}>
            Disconnect
          </Button>
        )}
      </div>
    </form>
  );
}
