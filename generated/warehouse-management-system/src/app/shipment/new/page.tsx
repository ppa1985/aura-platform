"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function NewShipmentPage() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true); setErr(null);
    const fd = new FormData(e.currentTarget);
    const body: Record<string, unknown> = {};
    fd.forEach((v, k) => { body[k] = v === "" ? null : v; });
    const r = await fetch("/api/shipment", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    setBusy(false);
    if (!r.ok) { setErr(await r.text()); return; }
    router.push("/shipment");
    router.refresh();
  }

  return (
    <div className="max-w-xl space-y-4">
      <h1 className="text-2xl font-semibold">New Shipment</h1>
      <form onSubmit={onSubmit} className="space-y-4">
        
        <div className="space-y-1.5">
          <Label htmlFor="reference">reference *</Label>
          
          <Input id="reference" name="reference" required />
          
        </div>
        
        <div className="space-y-1.5">
          <Label htmlFor="direction">direction *</Label>
          
          <Input id="direction" name="direction" required />
          
        </div>
        
        <div className="space-y-1.5">
          <Label htmlFor="status">status *</Label>
          
          <Input id="status" name="status" required />
          
        </div>
        
        <div className="space-y-1.5">
          <Label htmlFor="shipped_at">shipped_at</Label>
          
          <Input id="shipped_at" name="shipped_at"  />
          
        </div>
        
        
        <div className="space-y-1.5">
          <Label htmlFor="warehouse_id">warehouse (ID, required)</Label>
          <Input id="warehouse_id" name="warehouse_id" type="number" required />
        </div>
        
        <div className="space-y-1.5">
          <Label htmlFor="supplier_id">supplier (ID)</Label>
          <Input id="supplier_id" name="supplier_id" type="number"  />
        </div>
        
        {err && <p className="text-sm text-red-600">{err}</p>}
        <Button type="submit" disabled={busy}>{busy ? "Saving..." : "Create"}</Button>
      </form>
    </div>
  );
}
