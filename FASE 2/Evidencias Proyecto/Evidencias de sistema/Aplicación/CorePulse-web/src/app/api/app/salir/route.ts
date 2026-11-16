import { NextResponse, type NextRequest } from "next/server";
import { limitar } from "@/lib/app/limite";
import { anon } from "@/lib/supabase/anon";

// Cierra la sesión de este equipo (revoca su token).
export async function POST(request: NextRequest) {
  const limite = await limitar(request, "LIMITE_APP");
  if (limite) return limite;
  const token = (request.headers.get("authorization") ?? "").replace(/^Bearer\s+/i, "");
  if (!/^[0-9a-f]{64}$/.test(token)) return NextResponse.json({ ok: false }, { status: 401 });
  const { error } = await anon().rpc("revocar_token_app", { token });
  return NextResponse.json({ ok: !error }, { status: error ? 502 : 200 });
}
