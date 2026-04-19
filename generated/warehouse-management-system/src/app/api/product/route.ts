import { NextResponse } from "next/server";
import { z } from "zod";
import { query, SCHEMA } from "@/lib/db";

const ItemSchema = z.object({
  name: z.string(),
  sku: z.string(),
  description: z.string().optional().nullable(),
  unit_price: z.coerce.number().optional().nullable(),
  
  supplier_id: z.coerce.number().int().optional().nullable(),
  
});

export async function GET() {
  const rows = await query(`SELECT * FROM "${SCHEMA}"."products" ORDER BY id DESC LIMIT 200`);
  return NextResponse.json(rows);
}

export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));
  const parsed = ItemSchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json({ error: parsed.error.flatten() }, { status: 400 });
  }
  const data = parsed.data as Record<string, unknown>;
  const cols = Object.keys(data);
  const vals = cols.map((_, i) => `$${i + 1}`);
  const params = cols.map((c) => (data as Record<string, unknown>)[c]);
  const sql = `INSERT INTO "${SCHEMA}"."products" (${cols.map((c) => `"${c}"`).join(",")}) VALUES (${vals.join(",")}) RETURNING *`;
  const rows = await query(sql, params);
  return NextResponse.json(rows[0], { status: 201 });
}
