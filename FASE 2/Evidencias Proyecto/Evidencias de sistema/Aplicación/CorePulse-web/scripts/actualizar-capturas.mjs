// Reemplaza capturas de la web en un solo paso.
//
// 1. Pon las capturas nuevas en contenido/capturas-nuevas/ con el mismo nombre que la que reemplazan
//    (cualquier formato): summary.png, health.png, tweaks.png, cleanup.png, themes.png,
//    tema_aurora.png, tema_violet.png, tema_ember.png, tema_sakura.png, tema_cyber.png.
// 2. npm run actualizar-capturas -- --prueba   → solo las prepara en contenido/capturas para revisarlas.
//    npm run actualizar-capturas               → las prepara, las sube a Supabase y cambia las tablas.
//
// Cada captura se recorta al tamaño de la web (1800×1068) y se guarda en WebP con un nombre nuevo
// (summary-20261015-1830.webp): las imágenes llevan 7 días de caché y con el mismo nombre los
// navegadores seguirían mostrando la vieja. La web muestra las nuevas en un máximo de 60 s.
import { readdir, readFile, rm } from "node:fs/promises";
import { extname, join } from "node:path";
import sharp from "sharp";
import { createClient } from "@supabase/supabase-js";

const ENTRADA = "contenido/capturas-nuevas";
const SALIDA = "contenido/capturas";
const ANCHO = 1800;
const ALTO = 1068;
const EXTENSIONES = new Set([".png", ".jpg", ".jpeg", ".webp", ".avif", ".bmp", ".tif", ".tiff"]);
const prueba = process.argv.includes("--prueba");

const ahora = new Date();
const dos = (n) => String(n).padStart(2, "0");
const version = `${ahora.getFullYear()}${dos(ahora.getMonth() + 1)}${dos(ahora.getDate())}-${dos(ahora.getHours())}${dos(ahora.getMinutes())}`;

// «summary.jpg», «summary-20261015-1830.webp» y «summary-20261015-1830-social.jpg» son la misma captura.
const base = (archivo) => archivo.replace(/\.[a-z0-9]+$/i, "").replace(/(-\d{8}(-\d{4})?)?(-social)?$/, "");

const archivos = (await readdir(ENTRADA).catch(() => [])).filter((a) => EXTENSIONES.has(extname(a).toLowerCase())).sort();
if (!archivos.length) {
  console.error(`No hay capturas en ${ENTRADA}/. Pon ahí las nuevas con el nombre de la que reemplazan (p. ej. summary.png).`);
  process.exit(1);
}

let supabase = null;
if (!prueba) {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const secret = process.env.SUPABASE_SECRET_KEY;
  if (!url || !secret) {
    console.error("Faltan NEXT_PUBLIC_SUPABASE_URL o SUPABASE_SECRET_KEY en .env.local (o usa --prueba para solo prepararlas).");
    process.exit(1);
  }
  supabase = createClient(url, secret, { auth: { persistSession: false } });
}

// 1 · Preparar
const nuevas = new Map(); // base → { archivo, social? }
const anteriores = (await readdir(SALIDA).catch(() => [])).filter((a) => EXTENSIONES.has(extname(a).toLowerCase()));
for (const original of archivos) {
  const nombre = base(original).toLowerCase();
  if (!/^[a-z0-9_]+$/.test(nombre)) {
    console.warn(`· ${original}: nombre no válido (usa letras, números y _), se omite.`);
    continue;
  }
  const imagen = sharp(join(ENTRADA, original)).rotate();
  const { width = 0, height = 0 } = await imagen.metadata();
  const proporcion = width / height / (ANCHO / ALTO);
  if (Math.abs(proporcion - 1) > 0.02) console.warn(`· ${original}: ${width}×${height} no tiene la proporción de la web; se recorta por el centro.`);
  if (width < ANCHO) console.warn(`· ${original}: mide ${width} px de ancho (menos de ${ANCHO}); se verá algo menos nítida.`);

  const archivo = `${nombre}-${version}.webp`;
  await imagen.clone().resize(ANCHO, ALTO, { fit: "cover" }).webp({ quality: 82, effort: 6 }).toFile(join(SALIDA, archivo));
  // Vista previa para redes (WhatsApp, X, LinkedIn…): JPEG de 1200×630.
  const social = `${nombre}-${version}-social.jpg`;
  await imagen.clone().resize(1200, 630, { fit: "cover", position: "top" }).jpeg({ quality: 85, mozjpeg: true }).toFile(join(SALIDA, social));
  nuevas.set(nombre, { archivo, social });
  console.log(`✓ ${original} → ${archivo}`);
}
if (!nuevas.size) process.exit(1);

// La vista previa social solo se guarda para la captura que la usa (se decide abajo).
const socialesUsadas = new Set();
const creadas = new Set([...nuevas.values()].flatMap((n) => [n.archivo, n.social]));

if (prueba) {
  for (const { social } of nuevas.values()) await rm(join(SALIDA, social));
  console.log(`\nPreparadas en ${SALIDA}/ (junto a las actuales). Revísalas y, si están bien, ejecuta: npm run actualizar-capturas`);
  process.exit(0);
}

// 2 · Cambiar las tablas (qué archivo nuevo va en cada fila)
const cambios = [];
for (const tabla of ["funciones", "temas"]) {
  const clave = tabla === "funciones" ? "slug" : "id";
  const { data, error } = await supabase.from(tabla).select(`${clave}, imagen`);
  if (error) throw new Error(`${tabla}: ${error.message}`);
  for (const fila of data) {
    const nueva = nuevas.get(base(fila.imagen).toLowerCase());
    if (nueva) cambios.push({ tabla, clave, valor: fila[clave], antes: fila.imagen, despues: nueva.archivo });
  }
}
const { data: ajustes, error: errorAjustes } = await supabase.from("ajustes").select("clave, valor").in("clave", ["inicio", "sitio"]);
if (errorAjustes) throw new Error(`ajustes: ${errorAjustes.message}`);
const ajustesNuevos = [];
for (const { clave, valor } of ajustes) {
  const campo = clave === "inicio" ? "imagen" : "imagenSocial";
  const actual = valor?.[campo];
  const nueva = actual && nuevas.get(base(actual).toLowerCase());
  if (!nueva) continue;
  const despues = campo === "imagenSocial" ? nueva.social : nueva.archivo;
  if (campo === "imagenSocial") socialesUsadas.add(nueva.social);
  ajustesNuevos.push({ clave, valor: { ...valor, [campo]: despues }, antes: actual, despues });
}
for (const { social } of nuevas.values()) if (!socialesUsadas.has(social)) await rm(join(SALIDA, social));

// 3 · Subir (antes de tocar las tablas, para que la web nunca apunte a un archivo que no existe)
const subir = [...[...nuevas.values()].map((n) => n.archivo), ...socialesUsadas];
for (const archivo of subir) {
  const tipo = archivo.endsWith(".jpg") ? "image/jpeg" : "image/webp";
  const { error } = await supabase.storage
    .from("capturas")
    .upload(archivo, await readFile(join(SALIDA, archivo)), { contentType: tipo, upsert: true, cacheControl: "604800" });
  if (error) {
    console.error(`✗ subir ${archivo}: ${error.message}. No se cambió ninguna tabla.`);
    process.exit(1);
  }
  console.log(`↑ ${archivo}`);
}

// 4 · Aplicar
let fallos = 0;
for (const c of cambios) {
  const { error } = await supabase.from(c.tabla).update({ imagen: c.despues }).eq(c.clave, c.valor);
  console.log(error ? `✗ ${c.tabla} ${c.valor}: ${error.message}` : `✓ ${c.tabla} ${c.valor}: ${c.antes} → ${c.despues}`);
  if (error) fallos++;
}
for (const a of ajustesNuevos) {
  const { error } = await supabase.from("ajustes").update({ valor: a.valor, actualizado: new Date().toISOString() }).eq("clave", a.clave);
  console.log(error ? `✗ ajustes ${a.clave}: ${error.message}` : `✓ ajustes ${a.clave}: ${a.antes} → ${a.despues}`);
  if (error) fallos++;
}
const sinUso = [...nuevas.keys()].filter(
  (n) => !cambios.some((c) => base(c.despues) === n) && !ajustesNuevos.some((a) => base(a.despues) === n),
);
if (sinUso.length) console.warn(`· Subidas pero sin ninguna fila que las use: ${sinUso.join(", ")}`);

// Las versiones anteriores de estas capturas ya no se usan: fuera de la carpeta (siguen en el historial de git
// y en Supabase Storage).
if (!fallos) {
  for (const viejo of anteriores) {
    if (!creadas.has(viejo) && nuevas.has(base(viejo).toLowerCase())) await rm(join(SALIDA, viejo));
  }
}
console.log(fallos ? `\nTerminado con ${fallos} errores.` : "\nListo: la web mostrará las capturas nuevas en un máximo de 60 segundos.");
process.exit(fallos ? 1 : 0);
