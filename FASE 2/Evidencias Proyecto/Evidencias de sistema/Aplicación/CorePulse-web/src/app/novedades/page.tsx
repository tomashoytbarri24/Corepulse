import type { Metadata } from "next";
import PageHeader from "@/components/PageHeader";
import { Reveal } from "@/components/motion/Reveal";
import { getCabecera, getVersiones } from "@/lib/contenido";

export const dynamic = "force-dynamic";

export async function generateMetadata(): Promise<Metadata> {
  const c = await getCabecera("novedades");
  return { title: c.etiqueta, description: c.texto };
}

const fecha = (iso: string) => new Date(`${iso}T12:00:00Z`).toLocaleDateString("es", { day: "numeric", month: "long", year: "numeric" });

export default async function Novedades() {
  const [cabecera, releases] = await Promise.all([getCabecera("novedades"), getVersiones()]);
  return (
    <>
      <PageHeader kicker={cabecera.etiqueta} title={cabecera.titulo} text={cabecera.texto} />
      <section className="mx-auto max-w-3xl px-6 pb-32">
        {releases.length === 0 ? (
          <Reveal>
            <div className="rounded-2xl border border-white/10 bg-white/[0.02] px-8 py-12 text-center">
              <p className="text-lg font-medium">Pronto verás aquí cada actualización de CorePulse.</p>
              <p className="mt-2 text-muted">Cuando publiquemos una versión nueva, aparecerá en esta página con lo que cambió.</p>
            </div>
          </Reveal>
        ) : (
          <ol className="relative border-l border-white/10">
            {releases.map((r, i) => (
              <li key={r.id} className="relative pb-14 pl-10">
                <span className="absolute -left-[7px] top-1.5 h-3.5 w-3.5 rounded-full border-2 border-bg bg-accent shadow-[0_0_16px_#4EDDC8]" />
                <Reveal delay={i * 0.04}>
                  <p className="text-sm font-medium text-accent">
                    {r.version} <span className="text-muted">· {fecha(r.publicado)}</span>
                  </p>
                  <h2 className="mt-1 text-2xl font-semibold tracking-tight">{r.titulo}</h2>
                  {r.resumen && <p className="mt-3 leading-relaxed text-muted">{r.resumen}</p>}
                  {r.cambios.length > 0 && (
                    <ul className="mt-4 list-disc space-y-2 pl-5 text-muted marker:text-accent">
                      {r.cambios.map((it) => (
                        <li key={it}>{it}</li>
                      ))}
                    </ul>
                  )}
                  {r.enlace?.startsWith("https://github.com/") && (
                    <a href={r.enlace} target="_blank" rel="noopener noreferrer" className="mt-4 inline-block text-sm font-medium text-accent hover:underline">
                      Ver en GitHub →
                    </a>
                  )}
                </Reveal>
              </li>
            ))}
          </ol>
        )}
      </section>
    </>
  );
}
