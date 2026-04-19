import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { healthGenerator, listApps } from "@/lib/generator";

export const dynamic = "force-dynamic";

export default async function SystemPage() {
  const [health, apps] = await Promise.all([healthGenerator(), listApps()]);
  const summary = apps.reduce<Record<string, number>>((acc, a) => {
    acc[a.status] = (acc[a.status] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">System</h1>
        <p className="text-muted-foreground">Aura control plane health and configuration.</p>
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Generator service</CardTitle>
            <CardDescription>FastAPI service responsible for Blueprint → Code → Deploy.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <div>Status: {health ? "online" : "offline"}</div>
            {health && (
              <>
                <div>Mode: <code className="font-mono">{health.mode}</code></div>
                <div>Model: <code className="font-mono">{health.model}</code></div>
                <div>Ollama reachable: {health.ollama ? "yes" : "no"}</div>
              </>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Apps by status</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            {Object.keys(summary).length === 0 ? (
              <div className="text-muted-foreground">No apps generated yet.</div>
            ) : (
              Object.entries(summary).map(([k, v]) => (
                <div key={k}>
                  {k}: <span className="font-medium">{v}</span>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
