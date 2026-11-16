import type { MetadataRoute } from "next";
import { getSlugsLegales } from "@/lib/contenido";
import { siteUrl } from "@/lib/supabase/env";

export const dynamic = "force-dynamic";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const legales = (await getSlugsLegales()).map((l) => `/legal/${l.slug}`);
  const routes = ["", "/funciones", "/precios", "/descargar", "/novedades", ...legales];
  return routes.map((r) => ({ url: `${siteUrl()}${r}`, changeFrequency: "weekly", priority: r === "" ? 1 : 0.7 }));
}
