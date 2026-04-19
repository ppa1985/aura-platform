import { NextResponse } from "next/server";
import { ask } from "@/lib/ai";

export async function POST(req: Request) {
  const { prompt, system } = await req.json().catch(() => ({ prompt: "" }));
  if (!prompt) return NextResponse.json({ error: "prompt required" }, { status: 400 });
  try {
    const response = await ask(prompt, system);
    return NextResponse.json({ response });
  } catch (e) {
    return NextResponse.json({ error: (e as Error).message }, { status: 502 });
  }
}
