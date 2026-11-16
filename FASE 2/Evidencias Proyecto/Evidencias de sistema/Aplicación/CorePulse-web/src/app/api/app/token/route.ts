import { NextResponse, type NextRequest } from "next/server";
import { limitar } from "@/lib/app/limite";
import { anon } from "@/lib/supabase/anon";

// La app canjea el código de un solo uso + su verificador por un token de equipo.
export async function POST(request: NextRequest) {
  const limite = await limitar(request, "LIMITE_APP_TOKEN");
  if (limite) return limite;
  const body = await request.json().catch(() => null);
  const codigo = typeof body?.codigo === "string" ? body.codigo : "";
  const verificador = typeof body?.verificador === "string" ? body.verificador : "";
  if (!/^[0-9a-f]{64}$/.test(codigo) || !/^[A-Za-z0-9_-]{43,128}$/.test(verificador)) {
    return NextResponse.json({ error: "solicitud_invalida" }, { status: 400 });
  }
  const db = anon();
  const { data: token, error } = await db.rpc("canjear_codigo_app", { codigo, verificador });
  if (error) return NextResponse.json({ error: "servidor" }, { status: 502 });
  if (typeof token !== "string") return NextResponse.json({ error: "codigo_invalido" }, { status: 401 });
  const { data: perfil } = await db.rpc("perfil_app", { token });
  return NextResponse.json({ token, perfil: Array.isArray(perfil) ? (perfil[0] ?? null) : null }, { headers: { "Cache-Control": "no-store" } });
}
