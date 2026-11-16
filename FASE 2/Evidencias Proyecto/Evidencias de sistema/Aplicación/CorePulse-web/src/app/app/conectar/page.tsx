import type { Metadata } from "next";
import { redirect } from "next/navigation";
import AuthShell from "@/components/auth/AuthShell";
import { autorizarApp, cancelarApp } from "@/lib/app/acciones";
import { leerSolicitud } from "@/lib/app/solicitud";
import { createClient } from "@/lib/supabase/server";

export const metadata: Metadata = { title: "Conectar CorePulse", robots: { index: false } };

// La app de escritorio abre esta página para que el usuario autorice el equipo.
export default async function Conectar({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const params = await searchParams;
  const s = leerSolicitud(params);
  if (!s) {
    return (
      <AuthShell titulo="Enlace incompleto" texto="Vuelve a pulsar «Iniciar sesión» en la app de CorePulse para empezar de nuevo." >
        <span />
      </AuthShell>
    );
  }

  const supabase = await createClient();
  const { data } = await supabase.auth.getClaims();
  if (!data?.claims) {
    const q = new URLSearchParams({ puerto: String(s.puerto), estado: s.estado, reto: s.reto });
    redirect(`/login?siguiente=${encodeURIComponent(`/app/conectar?${q}`)}`);
  }

  const campos = (
    <>
      <input type="hidden" name="puerto" value={s.puerto} />
      <input type="hidden" name="estado" value={s.estado} />
      <input type="hidden" name="reto" value={s.reto} />
    </>
  );
  return (
    <AuthShell titulo="Conectar CorePulse" texto="La app de este equipo podrá ver tu nombre, tu email y tu plan. Nunca verá tu contraseña.">
      <div className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm text-muted">
        Cuenta: <span className="text-ink">{String(data.claims.email ?? "")}</span>
      </div>
      <form action={autorizarApp} className="mt-6">
        {campos}
        <button className="w-full rounded-full bg-ink py-3.5 text-[15px] font-medium text-bg transition-transform duration-300 hover:scale-[1.02] active:scale-95">
          Autorizar este equipo
        </button>
      </form>
      <form action={cancelarApp} className="mt-3">
        {campos}
        <button className="w-full rounded-full py-3 text-sm text-muted transition-colors hover:text-ink">Cancelar</button>
      </form>
      <p className="mt-6 text-center text-xs text-muted">Solo autoriza si acabas de pulsar «Iniciar sesión» en CorePulse.</p>
    </AuthShell>
  );
}
