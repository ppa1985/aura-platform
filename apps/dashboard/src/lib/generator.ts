import { cookies } from "next/headers";

const BASE = process.env.GENERATOR_URL || "http://localhost:8000";

export type App = {
  id: number;
  slug: string;
  name: string;
  description: string | null;
  status: string;
  url_path: string | null;
  container_id: string | null;
  last_error: string | null;
  ai_enabled: boolean;
  git_pushed_url: string | null;
  created_at: string;
  updated_at: string;
};

export type CurrentUser = {
  id: number;
  email: string;
  verified: boolean;
  git_account: {
    provider: string;
    username: string;
    workspace_repo: string;
  } | null;
};

async function authHeaders(): Promise<Record<string, string>> {
  const c = await cookies();
  const session = c.get("aura_session");
  return session ? { Cookie: `aura_session=${session.value}` } : {};
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...(await authHeaders()),
      ...(init?.headers || {}),
    },
  });
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`Generator ${path} ${r.status}: ${text}`);
  }
  return (await r.json()) as T;
}

export async function getCurrentUser(): Promise<CurrentUser | null> {
  try {
    return await req<CurrentUser>("/auth/me");
  } catch {
    return null;
  }
}

export async function listApps(): Promise<App[]> {
  try {
    return await req<App[]>("/apps");
  } catch {
    return [];
  }
}
export async function getApp(slug: string): Promise<App | null> {
  try {
    return await req<App>(`/apps/${slug}`);
  } catch {
    return null;
  }
}
export async function healthGenerator() {
  try {
    return await req<{ status: string; ollama: boolean; mode: string; model: string }>(
      "/health"
    );
  } catch {
    return null;
  }
}
