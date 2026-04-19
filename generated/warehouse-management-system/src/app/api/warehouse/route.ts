import { NextResponse } from "next/server";
import { z } from "zod";
import { query, SCHEMA } from "@/lib/db";

const ItemSchema = z.object({
  name: z.string(),
  code: z.string(),
  address: z.string().optional().nullable(),
  
  
});

export async function GET() {
  const rows = await query(`SELECT * FROM "${SCHEMA}"."warehouses" ORDER BY id DESC LIMIT 200`);
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
  const sql = `INSERT INTO "${SCHEMA}"."warehouses" (${cols.map((c) => `"${c}"`).join(",")}) VALUES (${vals.join(",")}) RETURNING *`;
  const rows = await query(sql, params);
  return NextResponse.json(rows[0], { status: 201 });
}
