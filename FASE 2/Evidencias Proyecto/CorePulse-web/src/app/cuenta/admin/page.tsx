import type { Metadata } from "next";
import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { FormDarAdmin, FormPrecios } from "@/components/admin/FormPrecios";
import { Reveal } from "@/components/motion/Reveal";
import { quitarAdmin } from "@/lib/admin/acciones";
import { createClient } from "@/lib/supabase/server";

export const metadata: Metadata = { title: "Administración", robots: { index: false } };

type Admin = { id: string; email: string; nombre: string };

const AVISOS_ADMINS: Record<string, { texto: string; error: boolean }> = {
  quitado: { texto: "Se le quitó el admin a esa cuenta.", error: false },
  error: { texto: "No se pudo quitar el admin. Inténtalo de nuevo.", error: true },
};

export default async function Admin({ searchParams }: { searchParams: Promise<{ admins?: string | string[] }> }) {
  const { admins: avisoAdmins } = await searchParams;
  const aviso = typeof avisoAdmins === "string" && Object.hasOwn(AVISOS_ADMINS, avisoAdmins) ? AVISOS_ADMINS[avisoAdmins] : undefined;
  const supabase = await createClient();
  const { data } = await supabase.auth.getClaims();
  const claims = data?.claims;
  if (!claims) redirect("/login?siguiente=/cuenta/admin");

  const { data: perfil } = await supabase.from("perfiles").select("es_admin").eq("id", claims.sub).maybeSingle();
  if (!perfil?.es_admin) notFound();

  // Sin la caché pública: el admin ve siempre lo que hay en la base.
  const [{ data: planes }, { data: admins }] = await Promise.all([
    supabase.from("planes").select("slug, nombre, moneda, precio_mensual, precio_anual").order("orden"),
    supabase.rpc("lista_admins"),
  ]);

  return (
    <section className="mx-auto max-w-3xl px-6 pb-32 pt-36 md:pt-44">
      <Reveal>
        <p className="text-sm font-semibold uppercase tracking-[0.16em] text-accent">Administración</p>
        <h1 className="mt-3 text-4xl font-semibold tracking-[-0.04em] md:text-5xl">Precios</h1>
        <p className="mt-2 text-muted">En pesos enteros. Un plan con mensual y anual en 0 se muestra como gratis. Los cambios aparecen en /precios en menos de un minuto.</p>
      </Reveal>

      <Reveal delay={0.08}>
        <div className="mt-10 rounded-3xl border border-white/[0.08] bg-panel/70 p-6 md:p-8">
          <FormPrecios planes={(planes ?? []).map((p) => ({ ...p, precio_mensual: Number(p.precio_mensual), precio_anual: Number(p.precio_anual) }))} />
        </div>
      </Reveal>

      <Reveal delay={0.1}>
        <div className="mt-5 rounded-3xl border border-white/[0.08] bg-panel/70 p-6 md:p-8">
          <h2 className="text-2xl font-semibold tracking-[-0.03em]">Administradores</h2>
          <p className="mt-1 text-sm text-muted">Pueden cambiar los precios y dar o quitar admin. La persona tiene que haberse registrado antes en la web.</p>
          {aviso && (
            <p role="status" className={`mt-4 rounded-2xl border px-4 py-3 text-sm ${aviso.error ? "border-red-400/30 bg-red-500/10 text-red-200" : "border-accent/30 bg-accent/10 text-ink"}`}>
              {aviso.texto}
            </p>
          )}
          <ul className="mt-4 divide-y divide-white/[0.06]">
            {((admins ?? []) as Admin[]).map((a) => (
              <li key={a.id} className="flex items-center justify-between gap-4 py-3 text-sm">
                <span className="min-w-0 truncate">
                  {a.email}
                  {a.nombre && <span className="text-muted"> · {a.nombre}</span>}
                </span>
                {a.id === claims.sub ? (
                  <span className="shrink-0 text-xs text-muted">Tú</span>
                ) : (
                  <form action={quitarAdmin}>
                    <input type="hidden" name="id" value={a.id} />
                    <button className="shrink-0 rounded-full border border-white/15 px-4 py-1.5 text-xs transition-colors hover:border-red-400/50 hover:text-red-200">Quitar admin</button>
                  </form>
                )}
              </li>
            ))}
          </ul>
          <div className="mt-6">
            <FormDarAdmin />
          </div>
        </div>
      </Reveal>

      <p className="mt-6 text-center text-sm">
        <Link href="/cuenta" className="text-accent hover:underline">
          Volver a mi cuenta
        </Link>
      </p>
    </section>
  );
}
