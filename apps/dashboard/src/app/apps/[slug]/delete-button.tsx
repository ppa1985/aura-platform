"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";

export function DeleteAppButton({ slug }: { slug: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  async function onDelete() {
    if (!confirm(`Delete ${slug}? This removes its schema and container.`)) return;
    setBusy(true);
    try {
      await fetch(`/api/generator/apps/${slug}`, { method: "DELETE" });
      router.push("/");
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <Button variant="destructive" onClick={onDelete} disabled={busy}>
      {busy ? "Deleting..." : "Delete"}
    </Button>
  );
}
