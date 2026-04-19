"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function NewSupplierPage() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true); setErr(null);
    const fd = new FormData(e.currentTarget);
    const body: Record<string, unknown> = {};
    fd.forEach((v, k) => { body[k] = v === "" ? null : v; });
    const r = await fetch("/api/supplier", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    setBusy(false);
    if (!r.ok) { setErr(await r.text()); return; }
    router.push("/supplier");
    router.refresh();
  }

  return (
    <div className="max-w-xl space-y-4">
      <h1 className="text-2xl font-semibold">New Supplier</h1>
      <form onSubmit={onSubmit} className="space-y-4">
        
        <div className="space-y-1.5">
          <Label htmlFor="name">name *</Label>
          
          <Input id="name" name="name" required />
          
        </div>
        
        <div className="space-y-1.5">
          <Label htmlFor="contact_email">contact_email</Label>
          
          <Input id="contact_email" name="contact_email"  />
          
        </div>
        
        <div className="space-y-1.5">
          <Label htmlFor="phone">phone</Label>
          
          <Input id="phone" name="phone"  />
          
        </div>
        
        
        {err && <p className="text-sm text-red-600">{err}</p>}
        <Button type="submit" disabled={busy}>{busy ? "Saving..." : "Create"}</Button>
      </form>
    </div>
  );
}
