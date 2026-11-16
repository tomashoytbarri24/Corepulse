// Chequeo de salud: responde sin tocar la base de datos.
export const dynamic = "force-dynamic";

export function GET() {
  return Response.json({ ok: true });
}
