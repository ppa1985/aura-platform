import Link from "next/link";
import { notFound } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/badge";
import { getApp } from "@/lib/generator";
import { DeleteAppButton } from "./delete-button";

export const dynamic = "force-dynamic";

type BlueprintShape = {
  name: string;
  slug: string;
  description: string;
  ai_enabled: boolean;
  entities: Array<{
    name: string;
    fields: Array<{ name: string; type: string }>;
    relations: Array<{ name: string; target: string }>;
  }>;
  pages: Array<{ type: string; title: string; entity?: string }>;
};

export default async function AppDetail({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const app = await getApp(slug);
  if (!app) notFound();

  const bp = (app as unknown as { blueprint?: BlueprintShape }).blueprint;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <Link href="/" className="text-sm text-muted-foreground hover:underline">
            ← Back to apps
          </Link>
          <h1 className="mt-1 text-3xl font-semibold tracking-tight">{app.name}</h1>
          <p className="text-muted-foreground">{app.description}</p>
          <div className="mt-2 flex gap-2">
            <StatusBadge status={app.status} />
            {app.ai_enabled && (
              <span className="rounded-full border border-accent/30 bg-accent/10 px-2 py-0.5 text-xs text-accent">AI</span>
            )}
          </div>
        </div>
        <div className="flex gap-2">
          {app.url_path && (
            <a href={app.url_path} target="_blank" rel="noreferrer">
              <Button>Open app</Button>
            </a>
          )}
          <DeleteAppButton slug={app.slug} />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Deployment</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <div>
              <span className="text-muted-foreground">slug:</span> <code className="font-mono">{app.slug}</code>
            </div>
            <div>
              <span className="text-muted-foreground">URL:</span>{" "}
              <code className="font-mono">{app.url_path ?? "—"}</code>
            </div>
            <div>
              <span className="text-muted-foreground">container:</span>{" "}
              <code className="font-mono">{app.container_id ?? "(none)"}</code>
            </div>
            <div>
              <span className="text-muted-foreground">created:</span> {new Date(app.created_at).toLocaleString()}
            </div>
          </CardContent>
        </Card>
        {app.last_error && (
          <Card>
            <CardHeader>
              <CardTitle>Last error</CardTitle>
              <CardDescription>Generator reported an issue while building this app.</CardDescription>
            </CardHeader>
            <CardContent>
              <pre className="overflow-auto rounded bg-muted p-2 text-xs">{app.last_error}</pre>
            </CardContent>
          </Card>
        )}
      </div>

      {bp && (
        <Card>
          <CardHeader>
            <CardTitle>Blueprint</CardTitle>
            <CardDescription>
              {bp.entities.length} entities · {bp.pages.length} pages
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {bp.entities.map((e) => (
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
    </div>
  );
}
