import * as React from "react";
import { cn } from "@/lib/utils";

const STATUS_CLASS: Record<string, string> = {
  ready: "bg-emerald-100 text-emerald-800 border-emerald-200",
  degraded: "bg-amber-100 text-amber-800 border-amber-200",
  generating: "bg-blue-100 text-blue-800 border-blue-200",
  failed: "bg-red-100 text-red-800 border-red-200",
  pending: "bg-slate-100 text-slate-800 border-slate-200",
};

export function StatusBadge({ status }: { status: string }) {
  const cls = STATUS_CLASS[status] ?? "bg-muted text-muted-foreground border-border";
  return (
    <span className={cn("inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium capitalize", cls)}>
      {status}
    </span>
  );
}
