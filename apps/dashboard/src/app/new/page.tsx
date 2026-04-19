"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Textarea } from "@/components/ui/input";

const DEMO_PROMPTS = [
  "Build me a Warehouse Management System with products, warehouses, inventory levels, and inbound/outbound shipments.",
  "Build me a Trade Assistant with real-time news analysis.",
  "Build me a CRM with customers, contacts, and deals.",
];

type BlueprintPreview = {
  name: string;
  slug: string;
  description: string;
  ai_enabled: boolean;
  entities: Array<{
    name: string;
    fields: Array<{ name: string; type: string }>;
    relations: Array<{ name: string; target: string }>;
  }>;
};

type GenResult = {
  slug: string;
  name: string;
  url: string;
  schema: string;
  heal_ok: boolean;
  heal_attempts: Array<{ attempt: number; ok: boolean; output: string }>;
  deployment: { backend: string; url?: string; error?: string } | null;
};

export default function NewAppPage() {
  const router = useRouter();
  const [prompt, setPrompt] = useState(DEMO_PROMPTS[0]);
  const [useLlm, setUseLlm] = useState(true);
  const [preview, setPreview] = useState<BlueprintPreview | null>(null);
  const [result, setResult] = useState<GenResult | null>(null);
  const [phase, setPhase] = useState<"idle" | "previewing" | "generating">("idle");
  const [error, setError] = useState<string | null>(null);

  async function doPreview() {
    setPhase("previewing");
    setError(null);
    try {
      const r = await fetch("/api/generator/blueprints", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, use_llm: useLlm }),
      });
      if (!r.ok) throw new Error(await r.text());
      setPreview((await r.json()) as BlueprintPreview);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setPhase("idle");
    }
  }

  async function doGenerate() {
    setPhase("generating");
    setError(null);
    try {
      const r = await fetch("/api/generator/apps", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, use_llm: useLlm }),
      });
      if (!r.ok) throw new Error(await r.text());
      const gen = (await r.json()) as GenResult;
      setResult(gen);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setPhase("idle");
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">New app</h1>
        <p className="text-muted-foreground">
          Describe the app. Aura produces a Blueprint, provisions a schema, writes a containerized
          Next.js app, runs self-healing, and deploys it.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Prompt</CardTitle>
          <CardDescription>Describe what you want to build.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} rows={5} />
          <div className="flex flex-wrap gap-2">
            {DEMO_PROMPTS.map((p) => (
              <button
                key={p}
                onClick={() => setPrompt(p)}
                className="rounded-full border border-border bg-muted px-3 py-1 text-xs hover:bg-background"
              >
                {p.slice(0, 60)}...
              </button>
            ))}
          </div>
          <label className="flex items-center gap-2 text-sm">
            <Input
              type="checkbox"
              checked={useLlm}
              onChange={(e) => setUseLlm(e.target.checked)}
              className="h-4 w-4"
            />
            Use Ollama to produce the Blueprint (slower; heuristic fallback otherwise)
          </label>
          <div className="flex gap-2">
            <Button onClick={doPreview} variant="outline" disabled={phase !== "idle"}>
              {phase === "previewing" ? "Producing Blueprint..." : "Preview Blueprint"}
            </Button>
            <Button onClick={doGenerate} variant="accent" disabled={phase !== "idle"}>
              {phase === "generating" ? "Generating..." : "Generate + Deploy"}
            </Button>
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
        </CardContent>
      </Card>

      {preview && !result && (
        <Card>
          <CardHeader>
            <CardTitle>{preview.name}</CardTitle>
            <CardDescription>
              slug <code className="font-mono">{preview.slug}</code>
              {preview.ai_enabled && <span className="ml-2 rounded bg-accent/10 px-1.5 py-0.5 text-accent">AI</span>}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="mb-4 text-sm text-muted-foreground">{preview.description}</p>
            <div className="space-y-3">
              {preview.entities.map((e) => (
                <div key={e.name} className="rounded-md border p-3">
                  <div className="font-medium">{e.name}</div>
                  <div className="mt-1 text-xs text-muted-foreground">
                    {e.fields.map((f) => `${f.name}: ${f.type}`).join(" · ")}
                  </div>
                  {e.relations.length > 0 && (
                    <div className="mt-1 text-xs text-muted-foreground">
                      relations: {e.relations.map((r) => `${r.name} → ${r.target}`).join(", ")}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {result && (
        <Card>
          <CardHeader>
            <CardTitle>{result.name} generated</CardTitle>
            <CardDescription>
              schema <code className="font-mono">{result.schema}</code>
              {" · "}self-heal {result.heal_ok ? "✓" : "degraded"}
              {" · "}deployment {result.deployment?.backend ?? "n/a"}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex gap-2">
              <a href={result.url} target="_blank" rel="noreferrer">
                <Button>Open {result.name}</Button>
              </a>
              <Button variant="outline" onClick={() => router.push(`/apps/${result.slug}`)}>
                Manage
              </Button>
            </div>
            {result.heal_attempts.length > 0 && (
              <details className="text-xs">
                <summary className="cursor-pointer">Self-healing attempts ({result.heal_attempts.length})</summary>
                <pre className="mt-2 overflow-auto rounded bg-muted p-2">
                  {JSON.stringify(result.heal_attempts, null, 2)}
                </pre>
              </details>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
