import type { EmailOtpType } from "@supabase/supabase-js";
import { NextResponse, type NextRequest } from "next/server";
import { leerSolicitud, urlVuelta } from "@/lib/app/solicitud";
import { rutaSegura } from "@/lib/auth/rutas";
import { createClient } from "@/lib/supabase/server";
import { siteUrl } from "@/lib/supabase/env";

// Destino de los enlaces de los emails (confirmar cuenta, recuperar contraseña).
export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const siguiente = rutaSegura(searchParams.get("siguiente"));
  const code = searchParams.get("code");
  const tokenHash = searchParams.get("token_hash");
  const type = searchParams.get("type") as EmailOtpType | null;
  const supabase = await createClient();

  let ok = false;
  if (code) {
    ok = !(await supabase.auth.exchangeCodeForSession(code)).error;
  } else if (tokenHash && type) {
    ok = !(await supabase.auth.verifyOtp({ type, token_hash: tokenHash })).error;
  }
  if (!ok) return NextResponse.redirect(`${siteUrl()}/auth/error`);

  // Registro iniciado desde la app de escritorio: al confirmar el email se autoriza
  // el equipo y se vuelve directo a la app. Solo ocurre con un enlace de confirmación
  // válido de Supabase (no se puede fabricar); en el resto de casos se pide «Autorizar».
  if (siguiente.startsWith("/app/conectar?")) {
    const app = leerSolicitud(Object.fromEntries(new URLSearchParams(siguiente.slice("/app/conectar?".length))));
    if (app) {
      const { data: codigo, error } = await supabase.rpc("crear_codigo_app", { reto: app.reto });
      if (!error && typeof codigo === "string") return NextResponse.redirect(urlVuelta(app, { codigo }));
    }
  }
  return NextResponse.redirect(`${siteUrl()}${siguiente}`);
}
