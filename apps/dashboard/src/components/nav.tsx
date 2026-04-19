import Link from "next/link";
import { Sparkles, LayoutDashboard, Plus, Activity, User } from "lucide-react";
import { getCurrentUser } from "@/lib/generator";
import { LogoutButton } from "./logout-button";

const NAV = [
  { name: "Generated apps", href: "/", Icon: LayoutDashboard },
  { name: "New app", href: "/new", Icon: Plus },
  { name: "System", href: "/system", Icon: Activity },
  { name: "Profile", href: "/profile", Icon: User },
];

export async function Nav() {
  const user = await getCurrentUser();
  if (!user) return null;

  return (
    <aside className="hidden w-64 shrink-0 border-r bg-muted/30 p-6 md:flex md:flex-col">
      <Link href="/" className="mb-8 flex items-center gap-2">
        <Sparkles className="h-5 w-5 text-accent" />
        <div>
          <div className="text-xs uppercase tracking-wide text-muted-foreground">Aura</div>
          <div className="text-base font-semibold leading-tight">App Generation Platform</div>
        </div>
      </Link>
      <nav className="space-y-1">
        {NAV.map(({ name, href, Icon }) => (
          <Link
            key={href}
            href={href}
            className="flex items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-muted"
          >
            <Icon className="h-4 w-4" />
            {name}
          </Link>
        ))}
      </nav>
      <div className="mt-auto space-y-2 pt-6 text-xs text-muted-foreground">
        <div className="truncate">
          Signed in as{" "}
          <span className="font-medium text-foreground" title={user.email}>
            {user.email}
          </span>
        </div>
        <LogoutButton />
      </div>
    </aside>
  );
}
