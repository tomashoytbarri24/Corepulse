import "server-only";
import { getCloudflareContext } from "@opennextjs/cloudflare";

// Caché de las lecturas del contenido público en la Cache API de Cloudflare (por centro de datos).
// - Durante FRESCO_S se responde desde la caché sin llamar a Supabase.
// - Después se vuelve a pedir a Supabase; si Supabase falla, se sirve la última copia
//   (hasta RESPALDO_S) para que la web no se caiga.
// En local (`npm run dev`) y en *.workers.dev no hay Cache API: se consulta Supabase siempre.
const FRESCO_S = 60;
const RESPALDO_S = 7 * 24 * 60 * 60;
const GUARDADO = "x-corepulse-guardado";

type CacheCloudflare = Cache & { default?: Cache };

function cacheCloudflare(): Cache | null {
  const c = (globalThis as { caches?: CacheStorage }).caches as unknown as CacheCloudflare | undefined;
  return c?.default ?? null;
}

function enSegundoPlano(promesa: Promise<unknown>) {
  try {
    getCloudflareContext().ctx.waitUntil(promesa);
  } catch {
    void promesa;
  }
}

export function fetchConCache(soloPrefijo: string): typeof fetch {
  return async (input, init) => {
    const peticion = new Request(input, init);
    const cache = cacheCloudflare();
    if (!cache || peticion.method !== "GET" || !peticion.url.startsWith(soloPrefijo)) return fetch(peticion);

    // Accept y Prefer cambian la forma de la respuesta de PostgREST (p. ej. una fila o una lista).
    const variante = `${peticion.headers.get("accept") ?? ""}|${peticion.headers.get("prefer") ?? ""}`;
    const clave = new Request(`${peticion.url}${peticion.url.includes("?") ? "&" : "?"}__cache=${encodeURIComponent(variante)}`);
    const copia = await cache.match(clave).catch(() => undefined);
    const edad = copia ? (Date.now() - Number(copia.headers.get(GUARDADO))) / 1000 : Infinity;
    if (copia && edad < FRESCO_S) return copia;

    let respuesta: Response;
    try {
      respuesta = await fetch(peticion);
    } catch (error) {
      if (copia) return copia;
      throw error;
    }
    if (respuesta.status >= 500 && copia) return copia;
    if (!respuesta.ok) return respuesta;

    const guardar = new Response(respuesta.clone().body, respuesta);
    guardar.headers.set(GUARDADO, String(Date.now()));
    guardar.headers.set("Cache-Control", `public, max-age=${RESPALDO_S}`);
    guardar.headers.delete("Set-Cookie");
    enSegundoPlano(cache.put(clave, guardar).catch(() => {}));
    return respuesta;
  };
}
