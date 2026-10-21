import type { NextRequest } from "next/server";
import { updateSession } from "@/lib/supabase/proxy";

export async function proxy(request: NextRequest) {
  return updateSession(request);
}

export const config = {
  // Solo rutas que usan la sesión; las páginas públicas quedan en caché.
  matcher: ["/cuenta/:path*", "/login", "/registro", "/recuperar", "/logout", "/auth/:path*", "/app/:path*"],
};
