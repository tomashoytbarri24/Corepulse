// Solo se permite volver a rutas internas («/cuenta»), nunca a otro dominio.
// Los navegadores ignoran tabuladores y saltos de línea en las URLs («/\t/otro.com» = «//otro.com»),
// así que se rechaza cualquier carácter de control o barra invertida.
export function rutaSegura(valor: unknown, porDefecto = "/cuenta") {
  const ruta = typeof valor === "string" ? valor : "";
  if (!ruta.startsWith("/") || ruta.startsWith("//") || /[\x00-\x1f\x7f\\]/.test(ruta)) return porDefecto;
  try {
    const base = "http://interno.invalid";
    return new URL(ruta, base).origin === base ? ruta : porDefecto;
  } catch {
    return porDefecto;
  }
}
