import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/badge";
import { listApps, healthGenerator } from "@/lib/generator";

export const dynamic = "force-dynamic";

export default async function Home() {
  const [apps, health] = await Promise.all([listApps(), healthGenerator()]);

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Generated apps</h1>
          <p className="text-muted-foreground">
            {apps.length} app{apps.length === 1 ? "" : "s"} •{" "}
            {health
              ? `Generator online (${health.model}${health.ollama ? "" : ", Ollama down"})`
              : "Generator offline"}
          </p>
        </div>
        <Link href="/new">
          <Button variant="accent" size="lg">
            + New app
          </Button>
        </Link>
      </div>

      {apps.length === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>No apps yet</CardTitle>
            <CardDescription>
              Generate your first app from a natural-language prompt. Try the demo:
              <code className="ml-2 rounded bg-muted px-1.5 py-0.5 text-xs">
                Build me a Warehouse Management System with products, warehouses, inventory levels,
                and inbound/outbound shipments.
              </code>
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/new">
              <Button variant="accent">Generate a demo app</Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {apps.map((a) => (
            <Card key={a.slug}>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="truncate">{a.name}</CardTitle>
                  <StatusBadge status={a.status} />
                </div>
                <CardDescription className="line-clamp-2">{a.description}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="text-xs text-muted-foreground">
                  slug: <span className="font-mono">{a.slug}</span>
                </div>
                {a.ai_enabled && (
                  <div className="text-xs">
                    <span className="rounded bg-accent/10 px-1.5 py-0.5 text-accent">AI enabled</span>
                  </div>
                )}
                <div className="flex gap-2 pt-2">
                  <Link href={`/apps/${a.slug}`} className="flex-1">
                    <Button variant="outline" className="w-full">
                      Manage
                    </Button>
                  </Link>
                  {a.url_path && (
                    <a href={a.url_path} target="_blank" rel="noreferrer" className="flex-1">
                      <Button className="w-full">Open app</Button>
                    </a>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
