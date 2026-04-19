import { redirect } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getCurrentUser } from "@/lib/generator";
import { GitAccountForm } from "./git-account-form";

export const dynamic = "force-dynamic";

export default async function ProfilePage() {
  const user = await getCurrentUser();
  if (!user) redirect("/login");

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">Profile</h1>
        <p className="text-muted-foreground">
          Signed in as <span className="font-medium text-foreground">{user.email}</span>
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Git workspace</CardTitle>
          <CardDescription>
            Link a GitHub or GitLab Personal Access Token so Aura pushes every app you generate to
            your workspace repo under <code className="font-mono">apps/&lt;slug&gt;/</code>.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <GitAccountForm initial={user.git_account} />
        </CardContent>
      </Card>
    </div>
  );
}
