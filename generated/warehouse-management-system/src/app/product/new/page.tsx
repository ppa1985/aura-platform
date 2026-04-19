"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function NewProductPage() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true); setErr(null);
    const fd = new FormData(e.currentTarget);
    const body: Record<string, unknown> = {};
    fd.forEach((v, k) => { body[k] = v === "" ? null : v; });
    const r = await fetch("/api/product", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    setBusy(false);
    if (!r.ok) { setErr(await r.text()); return; }
    router.push("/product");
    router.refresh();
  }

  return (
    <div className="max-w-xl space-y-4">
      <h1 className="text-2xl font-semibold">New Product</h1>
      <form onSubmit={onSubmit} className="space-y-4">
        
        <div className="space-y-1.5">
          <Label htmlFor="name">name *</Label>
          
          <Input id="name" name="name" required />
          
        </div>
        
        <div className="space-y-1.5">
          <Label htmlFor="sku">sku *</Label>
          
          <Input id="sku" name="sku" required />
          
        </div>
        
        <div className="space-y-1.5">
          <Label htmlFor="description">description</Label>
          
          <Textarea id="description" name="description"  />
          
        </div>
        
        <div className="space-y-1.5">
          <Label htmlFor="unit_price">unit_price</Label>
          
          <Input id="unit_price" name="unit_price"  />
          
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
