import type { NextConfig } from "next";
import { initOpenNextCloudflareForDev } from "@opennextjs/cloudflare";

const dev = process.env.NODE_ENV === "development";

function origen(url: string | undefined) {
  try {
    return url ? new URL(url).origin : "";
  } catch {
    return "";
  }
}
const supabase = origen(process.env.NEXT_PUBLIC_SUPABASE_URL);

// Política de contenido (sin nonces, como recomienda la guía de Next para páginas sin proxy).
// - Supabase: imágenes de Storage y la sesión del navegador (Nav).
// - Cloudflare Web Analytics, por si se activa en el panel.
// - form-action incluye 127.0.0.1: «Autorizar este equipo» vuelve a la app de escritorio.
const csp = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${dev ? " 'unsafe-eval'" : ""} https://static.cloudflareinsights.com`,
  "style-src 'self' 'unsafe-inline'",
  `img-src 'self' data: blob: ${supabase}`,
  "font-src 'self'",
  `connect-src 'self' ${supabase} https://cloudflareinsights.com`,
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self' http://127.0.0.1:*",
  "frame-ancestors 'none'",
  ...(dev ? [] : ["upgrade-insecure-requests"]),
]
  .map((d) => d.replace(/\s+/g, " ").trim())
  .join("; ");

const cabeceras = [
  { key: "Content-Security-Policy", value: csp },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=(), usb=()" },
  { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
  ...(dev ? [] : [{ key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains" }]),
];

const nextConfig: NextConfig = {
  // Cloudflare Workers no ejecuta el optimizador de imágenes de Next: las capturas
  // se sirven tal cual desde Supabase Storage (ya van comprimidas).
  images: { unoptimized: true },
  poweredByHeader: false,
  async headers() {
    return [{ source: "/(.*)", headers: cabeceras }];
  },
};

export default nextConfig;

// Permite usar las variables de Cloudflare también con `npm run dev`.
initOpenNextCloudflareForDev();
