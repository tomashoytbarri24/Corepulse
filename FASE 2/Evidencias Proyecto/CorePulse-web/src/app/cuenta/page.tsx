import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { FormNombre } from "@/components/auth/Formularios";
import { Reveal, TiltCard } from "@/components/motion/Reveal";
import { cerrarSesion } from "@/lib/auth/acciones";
import { desconectarEquipo } from "@/lib/app/acciones";
import { createClient } from "@/lib/supabase/server";

export const metadata: Metadata = { title: "Mi cuenta", robots: { index: false } };

const DIAS_SIN_USO = 30;
const DIA_MS = 24 * 60 * 60 * 1000;

// Mismas reglas que sesion_app_vigente() en la base: 30 días sin uso o pasada su fecha de caducidad.
async function equiposVigentes(supabase: Awaited<ReturnType<typeof createClient>>) {
  const ahora = Date.now();
  const { data } = await supabase
    .from("sesiones_app")
    .select("id, creada, ultimo_uso, caduca")
    .eq("revocada", false)
    .gt("ultimo_uso", new Date(ahora - DIAS_SIN_USO * DIA_MS).toISOString())
    .gt("caduca", new Date(ahora).toISOString())
    .order("ultimo_uso", { ascending: false });
  return (data ?? []).map((e) => ({
    ...e,
    caducaEl: new Date(Math.min(new Date(e.ultimo_uso).getTime() + DIAS_SIN_USO * DIA_MS, new Date(e.caduca).getTime())).toISOString(),
  }));
}

const AVISOS_EQUIPO: Record<string, { texto: string; error: boolean }> = {
  desconectado: { texto: "Equipo desconectado. La app de ese equipo tendrá que volver a iniciar sesión.", error: false },
  error: { texto: "No se pudo desconectar el equipo. Inténtalo de nuevo.", error: true },
};

export default async function Cuenta({ searchParams }: { searchParams: Promise<{ equipo?: string | string[] }> }) {
  const { equipo } = await searchParams;
  const aviso = typeof equipo === "string" && Object.hasOwn(AVISOS_EQUIPO, equipo) ? AVISOS_EQUIPO[equipo] : undefined;
  const supabase = await createClient();
  const { data } = await supabase.auth.getClaims();
  const claims = data?.claims;
  if (!claims) redirect("/login?siguiente=/cuenta");

  const { data: perfil } = await supabase.from("perfiles").select("nombre, plan, plan_vence, creado").eq("id", claims.sub).maybeSingle();
  // Consulta aparte: si la migración de administradores aún no está aplicada, la cuenta sigue funcionando.
  const { data: admin } = await supabase.from("perfiles").select("es_admin").eq("id", claims.sub).maybeSingle();
  const equipos = await equiposVigentes(supabase);
  const fechaCorta = (iso: string) => new Date(iso).toLocaleDateString("es", { day: "numeric", month: "short", year: "numeric" });
  const pro = perfil?.plan === "pro";
  const vence = perfil?.plan_vence ? new Date(perfil.plan_vence).toLocaleDateString("es", { day: "numeric", month: "long", year: "numeric" }) : null;

  return (
    <section className="mx-auto max-w-4xl px-6 pb-32 pt-36 md:pt-44">
      <Reveal>
        <p className="text-sm font-semibold uppercase tracking-[0.16em] text-accent">Mi cuenta</p>
        <h1 className="mt-3 text-4xl font-semibold tracking-[-0.04em] md:text-5xl">Hola{perfil?.nombre ? `, ${perfil.nombre}` : ""}.</h1>
        <p className="mt-2 text-muted">{String(claims.email ?? "")}</p>
      </Reveal>

      <div className="mt-12 grid gap-5 md:grid-cols-2">
        <Reveal>
          <div className={pro ? "h-full rounded-3xl p-px [background:linear-gradient(140deg,#4EDDC8,#17B9F7_45%,#B756EA)]" : "h-full"}>
            <TiltCard className={`h-full rounded-3xl p-8 ${pro ? "bg-[#0f1219]" : "border border-white/[0.08] bg-panel/70"}`}>
              <h2 className="text-sm uppercase tracking-[0.14em] text-muted">Tu plan</h2>
              <p className={`mt-4 text-5xl font-semibold tracking-[-0.05em] ${pro ? "text-gradient" : ""}`}>{pro ? "Pro" : "Free"}</p>
              <p className="mt-2 text-sm text-muted">{pro ? (vence ? `Se renueva o vence el ${vence}.` : "Activo.") : "Prueba cada función gratis 2 veces."}</p>
              {!pro && (
                <Link href="/precios" className="mt-8 inline-block rounded-full bg-ink px-6 py-3 text-[15px] font-medium text-bg transition-transform duration-300 hover:scale-[1.03]">
                  Ver CorePulse Pro
                </Link>
              )}
            </TiltCard>
          </div>
        </Reveal>

        <Reveal delay={0.08}>
          <TiltCard className="h-full rounded-3xl border border-white/[0.08] bg-panel/70 p-8">
            <h2 className="text-sm uppercase tracking-[0.14em] text-muted">Perfil</h2>
            <div className="mt-5">
              <FormNombre nombre={perfil?.nombre ?? ""} />
            </div>
          </TiltCard>
        </Reveal>
      </div>

      <Reveal delay={0.1}>
        <div className="mt-5 rounded-3xl border border-white/[0.08] bg-panel/50 p-6">
          <h2 className="font-medium">Equipos con CorePulse</h2>
          <p className="text-sm text-muted">Equipos donde iniciaste sesión desde la app de escritorio. La sesión caduca tras {DIAS_SIN_USO} días sin usarse o a los 6 meses de conectarse; entonces la app vuelve a pedir que inicies sesión.</p>
          {aviso && (
            <p role="status" className={`mt-4 rounded-2xl border px-4 py-3 text-sm ${aviso.error ? "border-red-400/30 bg-red-500/10 text-red-200" : "border-accent/30 bg-accent/10 text-ink"}`}>
              {aviso.texto}
            </p>
          )}
          {equipos.length > 0 ? (
            <ul className="mt-4 divide-y divide-white/[0.06]">
              {equipos.map((e, i) => (
                <li key={e.id} className="flex items-center justify-between gap-4 py-3 text-sm">
                  <span>
                    Equipo {equipos.length - i} <span className="text-muted">· conectado el {fechaCorta(e.creada)} · último uso {fechaCorta(e.ultimo_uso)} · caduca el {fechaCorta(e.caducaEl)}</span>
                  </span>
                  <form action={desconectarEquipo}>
                    <input type="hidden" name="id" value={e.id} />
                    <button className="rounded-full border border-white/15 px-4 py-1.5 text-xs transition-colors hover:border-red-400/50 hover:text-red-200">Desconectar</button>
                  </form>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-4 text-sm text-muted">Todavía no has conectado ningún equipo. Pulsa «Iniciar sesión» en la app.</p>
          )}
        </div>
      </Reveal>

      {admin?.es_admin && (
        <Reveal delay={0.11}>
          <div className="mt-5 flex flex-col gap-3 rounded-3xl border border-accent/30 bg-accent/[0.06] p-6 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="font-medium">Administración</h2>
              <p className="text-sm text-muted">Tu cuenta es admin: puedes cambiar los precios y dar admin a otras cuentas.</p>
            </div>
            <Link href="/cuenta/admin" className="rounded-full bg-ink px-5 py-2.5 text-center text-sm font-medium text-bg transition-transform duration-300 hover:scale-[1.03]">
              Abrir administración
            </Link>
          </div>
        </Reveal>
      )}

      <Reveal delay={0.12}>
        <div className="mt-5 flex flex-col gap-3 rounded-3xl border border-white/[0.08] bg-panel/50 p-6 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="font-medium">Seguridad</h2>
            <p className="text-sm text-muted">Cambia tu contraseña o cierra la sesión en este navegador.</p>
          </div>
          <div className="flex gap-2">
            <Link href="/cuenta/contrasena" className="rounded-full border border-white/15 px-5 py-2.5 text-sm transition-colors hover:border-accent hover:text-accent">
              Cambiar contraseña
            </Link>
            <form action={cerrarSesion}>
              <button className="rounded-full border border-red-400/30 px-5 py-2.5 text-sm text-red-200 transition-colors hover:bg-red-500/10">Cerrar sesión</button>
            </form>
          </div>
        </div>
      </Reveal>
    </section>
  );
}
