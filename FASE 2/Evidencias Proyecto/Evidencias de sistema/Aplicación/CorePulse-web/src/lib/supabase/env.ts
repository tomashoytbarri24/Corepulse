// Variables públicas de Supabase (seguras en el navegador; la seguridad la da RLS).
export function supabaseEnv() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
  if (!url || !key) {
    throw new Error(
      "Faltan NEXT_PUBLIC_SUPABASE_URL y NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY. Cópialas de Supabase → Project Settings → API a .env.local (o a las variables de Cloudflare: Settings → Variables and Secrets, y Build → Variables).",
    );
  }
  return { url, key };
}

function urlValida(valor: string | undefined) {
  if (!valor) return null;
  try {
    const u = new URL(valor.trim());
    return u.protocol === "https:" || u.protocol === "http:" ? u.origin : null;
  } catch {
    return null;
  }
}

let avisado = false;

// Dirección pública de la web, usada en los enlaces de los emails de Supabase.
// NEXT_PUBLIC_SITE_URL (p. ej. https://corepulse.cl) o, en local, http://localhost:3000.
export function siteUrl() {
  const propia = urlValida(process.env.NEXT_PUBLIC_SITE_URL);
  if (!propia && process.env.NEXT_PUBLIC_SITE_URL && !avisado) {
    avisado = true;
    console.warn("[CorePulse] NEXT_PUBLIC_SITE_URL no es una dirección válida (debe ser https://...).");
  }
  return propia ?? "http://localhost:3000";
}
