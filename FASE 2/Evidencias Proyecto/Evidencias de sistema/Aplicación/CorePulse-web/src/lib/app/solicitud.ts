// Parámetros que envía la app de escritorio al abrir /app/conectar.
// La vuelta va SIEMPRE a 127.0.0.1 (el propio equipo): nunca a una dirección elegida por la URL.
export type Solicitud = { puerto: number; estado: string; reto: string };

export function leerSolicitud(p: Record<string, string | string[] | undefined>): Solicitud | null {
  const uno = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v) ?? "";
  const puerto = Number(uno(p.puerto));
  const estado = uno(p.estado);
  const reto = uno(p.reto);
  if (!Number.isInteger(puerto) || puerto < 1024 || puerto > 65535) return null;
  if (!/^[A-Za-z0-9_-]{16,128}$/.test(estado)) return null;
  if (!/^[0-9a-f]{64}$/.test(reto)) return null;
  return { puerto, estado, reto };
}

export function urlVuelta(s: Pick<Solicitud, "puerto" | "estado">, extra: Record<string, string>) {
  const q = new URLSearchParams({ ...extra, estado: s.estado });
  return `http://127.0.0.1:${s.puerto}/callback?${q}`;
}
