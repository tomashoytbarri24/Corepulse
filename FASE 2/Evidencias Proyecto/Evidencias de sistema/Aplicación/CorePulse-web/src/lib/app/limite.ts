import "server-only";
import { getCloudflareContext } from "@opennextjs/cloudflare";
import { NextResponse, type NextRequest } from "next/server";

// Límite de peticiones por IP con el Rate Limiting de Cloudflare (bindings en wrangler.jsonc).
// En `npm run dev` sin bindings no se limita nada.
type Limitador = { limit(opciones: { key: string }): Promise<{ success: boolean }> };

export async function limitar(request: NextRequest, binding: "LIMITE_APP_TOKEN" | "LIMITE_APP") {
  let limitador: Limitador | undefined;
  try {
    limitador = (getCloudflareContext().env as unknown as Record<string, Limitador | undefined>)[binding];
  } catch {
    return null;
  }
  if (!limitador) return null;
  const ip = request.headers.get("cf-connecting-ip") ?? request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ?? "desconocida";
  const { success } = await limitador.limit({ key: ip }).catch(() => ({ success: true }));
  return success ? null : NextResponse.json({ error: "demasiadas_peticiones" }, { status: 429, headers: { "Retry-After": "60" } });
}
