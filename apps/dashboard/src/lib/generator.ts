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
  created_at: string;
  updated_at: string;
};

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`Generator ${path} ${r.status}: ${text}`);
  }
  return (await r.json()) as T;
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
export async function createBlueprint(prompt: string, useLlm = true) {
  return req<Record<string, unknown>>("/blueprints", {
    method: "POST",
    body: JSON.stringify({ prompt, use_llm: useLlm }),
  });
}
export async function createApp(prompt: string, useLlm = true) {
  return req<{
    slug: string;
    name: string;
    url: string;
    schema: string;
    heal_ok: boolean;
    heal_attempts: Array<{ attempt: number; ok: boolean; output: string }>;
    deployment: { backend: string; url?: string; error?: string } | null;
  }>("/apps", {
    method: "POST",
    body: JSON.stringify({ prompt, use_llm: useLlm }),
  });
}
export async function deleteApp(slug: string) {
  return req(`/apps/${slug}`, { method: "DELETE" });
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
