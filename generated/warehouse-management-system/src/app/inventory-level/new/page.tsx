"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function NewInventoryLevelPage() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true); setErr(null);
    const fd = new FormData(e.currentTarget);
    const body: Record<string, unknown> = {};
    fd.forEach((v, k) => { body[k] = v === "" ? null : v; });
    const r = await fetch("/api/inventory-level", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    setBusy(false);
    if (!r.ok) { setErr(await r.text()); return; }
    router.push("/inventory-level");
    router.refresh();
  }

  return (
    <div className="max-w-xl space-y-4">
      <h1 className="text-2xl font-semibold">New InventoryLevel</h1>
      <form onSubmit={onSubmit} className="space-y-4">
        
        <div className="space-y-1.5">
          <Label htmlFor="quantity">quantity *</Label>
          
          <Input id="quantity" name="quantity" required />
          
        </div>
        
        <div className="space-y-1.5">
          <Label htmlFor="min_quantity">min_quantity</Label>
          
          <Input id="min_quantity" name="min_quantity"  />
          
        </div>
        
        <div className="space-y-1.5">
          <Label htmlFor="reorder_point">reorder_point</Label>
          
          <Input id="reorder_point" name="reorder_point"  />
          
        </div>
        
        
        <div className="space-y-1.5">
          <Label htmlFor="product_id">product (ID, required)</Label>
          <Input id="product_id" name="product_id" type="number" required />
        </div>
        
        <div className="space-y-1.5">
          <Label htmlFor="warehouse_id">warehouse (ID, required)</Label>
          <Input id="warehouse_id" name="warehouse_id" type="number" required />
        </div>
        
        {err && <p className="text-sm text-red-600">{err}</p>}
        <Button type="submit" disabled={busy}>{busy ? "Saving..." : "Create"}</Button>
      </form>
    </div>
  );
}
