import Link from "next/link";
import { Sparkles, LayoutDashboard, Plus, Activity } from "lucide-react";

const NAV = [
  { name: "Generated apps", href: "/", Icon: LayoutDashboard },
  { name: "New app", href: "/new", Icon: Plus },
  { name: "System", href: "/system", Icon: Activity },
];

export function Nav() {
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
          <Link key={href} href={href} className="flex items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-muted">
            <Icon className="h-4 w-4" />
            {name}
          </Link>
        ))}
      </nav>
      <div className="mt-auto pt-6 text-xs text-muted-foreground">
        Aura generates containerized full-stack apps from a prompt.
      </div>
    </aside>
  );
}
