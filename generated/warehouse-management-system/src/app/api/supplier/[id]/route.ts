import { NextResponse } from "next/server";
import { query, SCHEMA } from "@/lib/db";

export async function GET(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const rows = await query(`SELECT * FROM "${SCHEMA}"."suppliers" WHERE id = $1`, [Number(id)]);
  if (!rows[0]) return NextResponse.json({ error: "not found" }, { status: 404 });
  return NextResponse.json(rows[0]);
}

export async function DELETE(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  await query(`DELETE FROM "${SCHEMA}"."suppliers" WHERE id = $1`, [Number(id)]);
  return NextResponse.json({ ok: true });
}
