import "server-only";
import { cache } from "react";
import { createClient as createSupabase } from "@supabase/supabase-js";
import { fetchConCache } from "./supabase/cache";
import { supabaseEnv } from "./supabase/env";

// Lectura del contenido público. Sin cookies; las consultas pasan por la caché de Cloudflare (ver supabase/cache.ts).

export type Sitio = {
  nombre: string;
  lema: string;
  descripcion: string;
  descripcionCorta: string;
  version: string;
  compatibilidad: string;
  enlaceDescarga: string;
  emailSoporte: string;
  imagenSocial: string;
  avisoLegal: string;
};
export type Inicio = {
  titulo1: string;
  titulo2: string;
  subtitulo: string;
  imagen: string;
  imagenAlt: string;
  marquesina: string[];
  manifiesto: string;
  destacadosTitulo: string;
  destacadosSubtitulo: string;
  temasEtiqueta: string;
  temasTitulo: string;
  temasSubtitulo: string;
  cierreTitulo1: string;
  cierreTitulo2: string;
  cierreTexto: string;
};
export type Cabecera = { etiqueta: string; titulo: string; texto?: string };
export type PaginaPrecios = Cabecera & { nota: string };
export type PaginaDescargar = Cabecera & {
  avisoSinDescarga: string;
  requisitos: { nombre: string; valor: string }[];
  pasos: string[];
};
export type Plan = {
  slug: string;
  nombre: string;
  descripcion: string;
  precio_mensual: number;
  precio_anual: number;
  moneda: string;
  destacado: boolean;
  etiqueta: string | null;
  boton_texto: string;
  boton_enlace: string;
};
export type Caracteristica = { id: number; caracteristica: string; free: boolean | string; pro: boolean | string };
export type Pregunta = { id: number; pregunta: string; respuesta: string };
export type Funcion = {
  slug: string;
  etiqueta: string;
  titulo: string;
  titulo_portada: string | null;
  texto_portada: string | null;
  puntos: string[];
  imagen: string;
  color: string;
  en_portada: boolean;
};
export type Destacado = { id: number; titulo: string; texto: string; icono: string; ancho: boolean };
export type Cifra = { id: number; valor: number; sufijo: string; etiqueta: string };
export type Tema = { id: number; nombre: string; imagen: string; color: string };
export type Version = {
  id: number;
  version: string;
  titulo: string;
  resumen: string | null;
  cambios: string[];
  enlace: string | null;
  publicado: string;
};
export type DocumentoLegal = { slug: string; titulo: string; actualizado: string; secciones: { titulo: string; texto: string }[] };

const db = cache(() => {
  const { url, key } = supabaseEnv();
  return createSupabase(url, key, {
    auth: { persistSession: false, autoRefreshToken: false },
    global: { fetch: fetchConCache(`${url}/rest/v1/`) },
  });
});

function check<T>(tabla: string, res: { data: T | null; error: { message: string } | null }): T {
  if (res.error) throw new Error(`Supabase (${tabla}): ${res.error.message}`);
  if (res.data === null) throw new Error(`Supabase (${tabla}): sin datos`);
  return res.data;
}

const ajustes = cache(async () => {
  const filas = check("ajustes", await db().from("ajustes").select("clave, valor"));
  return Object.fromEntries(filas.map((f) => [f.clave, f.valor])) as Record<string, unknown>;
});

async function ajuste<T>(clave: string): Promise<T> {
  const valor = (await ajustes())[clave];
  if (!valor) throw new Error(`Falta la fila «${clave}» en la tabla ajustes de Supabase.`);
  return valor as T;
}

export const getSitio = () => ajuste<Sitio>("sitio");
export const getInicio = () => ajuste<Inicio>("inicio");
export const getCabecera = (pagina: "funciones" | "novedades") => ajuste<Cabecera>(pagina);
export const getPaginaPrecios = () => ajuste<PaginaPrecios>("precios");
export const getPaginaDescargar = () => ajuste<PaginaDescargar>("descargar");

export const getPlanes = cache(async () =>
  check<Plan[]>("planes", await db().from("planes").select("*").eq("activo", true).order("orden")).map((p) => ({
    ...p,
    precio_mensual: Number(p.precio_mensual),
    precio_anual: Number(p.precio_anual),
  })),
);

export const getCaracteristicas = cache(async () =>
  check<Caracteristica[]>("plan_caracteristicas", await db().from("plan_caracteristicas").select("id, caracteristica, free, pro").order("orden")),
);

export const getPreguntas = cache(async (seccion: string) =>
  check<Pregunta[]>("preguntas", await db().from("preguntas").select("id, pregunta, respuesta").eq("seccion", seccion).order("orden")),
);

export const getFunciones = cache(async () =>
  check<Funcion[]>("funciones", await db().from("funciones").select("*").order("orden")),
);

export const getDestacados = cache(async () =>
  check<Destacado[]>("destacados", await db().from("destacados").select("*").order("orden")),
);

export const getCifras = cache(async () => check<Cifra[]>("cifras", await db().from("cifras").select("*").order("orden")));

export const getTemas = cache(async () => check<Tema[]>("temas", await db().from("temas").select("*").order("orden")));

export const getVersiones = cache(async () =>
  check<Version[]>("versiones", await db().from("versiones").select("*").order("publicado", { ascending: false }).order("id", { ascending: false })),
);

export const getDocumentoLegal = cache(async (slug: string) => {
  // Solo nombres posibles (p. ej. «terminos»): lo demás es 404 sin consultar la base.
  if (!/^[a-z0-9-]{1,64}$/.test(slug)) return null;
  const res = await db().from("documentos_legales").select("*").eq("slug", slug).maybeSingle();
  if (res.error) throw new Error(`Supabase (documentos_legales): ${res.error.message}`);
  return res.data as DocumentoLegal | null;
});

export const getSlugsLegales = cache(async () =>
  check<{ slug: string; titulo: string }[]>("documentos_legales", await db().from("documentos_legales").select("slug, titulo").order("slug")),
);

/** URL pública de una imagen del bucket «capturas» (o una URL completa tal cual). */
export function imagen(ruta: string) {
  if (/^https?:\/\//.test(ruta)) return ruta;
  return `${supabaseEnv().url}/storage/v1/object/public/capturas/${ruta.replace(/^\/+/, "")}`;
}
