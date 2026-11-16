// Sube las imágenes de contenido/capturas al bucket «capturas» de Supabase Storage.
// Uso: npm run subir-capturas   (lee .env.local; necesita SUPABASE_SECRET_KEY, solo en tu equipo)
import { readdir, readFile } from "node:fs/promises";
import { extname, join } from "node:path";
import { createClient } from "@supabase/supabase-js";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
const secret = process.env.SUPABASE_SECRET_KEY;
if (!url || !secret) {
  console.error("Faltan NEXT_PUBLIC_SUPABASE_URL o SUPABASE_SECRET_KEY en .env.local");
  process.exit(1);
}

const tipos = { ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp", ".avif": "image/avif" };
const carpeta = "contenido/capturas";
const supabase = createClient(url, secret, { auth: { persistSession: false } });

let fallos = 0;
for (const archivo of (await readdir(carpeta)).sort()) {
  const tipo = tipos[extname(archivo).toLowerCase()];
  if (!tipo) continue;
  const { error } = await supabase.storage
    .from("capturas")
    .upload(archivo, await readFile(join(carpeta, archivo)), { contentType: tipo, upsert: true, cacheControl: "604800" });
  console.log(error ? `✗ ${archivo}: ${error.message}` : `✓ ${archivo}`);
  if (error) fallos++;
}
process.exit(fallos ? 1 : 0);
