import { NextResponse, type NextRequest } from "next/server";
import { limitar } from "@/lib/app/limite";
import { anon } from "@/lib/supabase/anon";

export const dynamic = "force-dynamic";

// Perfil del usuario dueño del token (Authorization: Bearer <token>).
export async function GET(request: NextRequest) {
  const limite = await limitar(request, "LIMITE_APP");
  if (limite) return limite;
  const token = (request.headers.get("authorization") ?? "").replace(/^Bearer\s+/i, "");
  if (!/^[0-9a-f]{64}$/.test(token)) return NextResponse.json({ error: "sin_token" }, { status: 401 });
  const { data, error } = await anon().rpc("perfil_app", { token });
  if (error) return NextResponse.json({ error: "servidor" }, { status: 502 });
  const perfil = Array.isArray(data) ? data[0] : null;
  if (!perfil) return NextResponse.json({ error: "token_invalido" }, { status: 401 });
  return NextResponse.json({ perfil }, { headers: { "Cache-Control": "no-store" } });
}
