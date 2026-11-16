import type { Metadata } from "next";
import Icon from "@/components/Icon";
import PageHeader from "@/components/PageHeader";
import { Reveal, TiltCard } from "@/components/motion/Reveal";
import { getPaginaDescargar, getSitio } from "@/lib/contenido";

export const dynamic = "force-dynamic";

export async function generateMetadata(): Promise<Metadata> {
  const p = await getPaginaDescargar();
  return { title: p.etiqueta, description: p.titulo };
}

export default async function Descargar() {
  const [pagina, sitio] = await Promise.all([getPaginaDescargar(), getSitio()]);
  const ready = /^https:\/\//.test(sitio.enlaceDescarga ?? "");
  return (
    <>
      <PageHeader kicker={pagina.etiqueta} title={pagina.titulo} text={`Versión ${sitio.version}. ${pagina.texto ?? ""}`} />
      <section className="mx-auto max-w-3xl px-6 pb-32">
        <Reveal>
          <TiltCard className="rounded-3xl border border-white/[0.08] bg-panel/70 p-10 text-center">
            <div className="mx-auto grid h-16 w-16 place-items-center rounded-2xl border border-white/10 bg-white/[0.04] text-cyan">
              <Icon name="windows" className="h-8 w-8" />
            </div>
            {ready ? (
              <a href={sitio.enlaceDescarga} className="mt-8 inline-block rounded-full bg-ink px-8 py-4 text-[15px] font-medium text-bg transition-transform duration-300 hover:scale-[1.04] active:scale-95">
                Descargar para Windows
              </a>
            ) : (
              <>
                <span aria-disabled className="mt-8 inline-block cursor-not-allowed rounded-full bg-white/10 px-8 py-4 text-[15px] font-medium text-muted">
                  Disponible muy pronto
                </span>
                <p className="mt-4 text-sm text-muted">{pagina.avisoSinDescarga}</p>
              </>
            )}
          </TiltCard>
        </Reveal>

        {pagina.requisitos?.length > 0 && (
          <Reveal delay={0.1}>
            <h2 className="mt-24 text-3xl font-semibold tracking-[-0.03em]">Requisitos</h2>
            <dl className="mt-8 divide-y divide-white/[0.07] border-y border-white/[0.07]">
              {pagina.requisitos.map((r) => (
                <div key={r.nombre} className="flex flex-col gap-1 py-5 sm:flex-row sm:justify-between">
                  <dt className="text-muted">{r.nombre}</dt>
                  <dd className="text-ink/90">{r.valor}</dd>
                </div>
              ))}
            </dl>
          </Reveal>
        )}

        {pagina.pasos?.length > 0 && (
          <Reveal delay={0.1}>
            <h2 className="mt-24 text-3xl font-semibold tracking-[-0.03em]">Instalación</h2>
            <ol className="mt-8 space-y-6">
              {pagina.pasos.map((step, i) => (
                <li key={step} className="flex gap-5">
                  <span className="text-gradient text-3xl font-semibold tracking-tight">{i + 1}</span>
                  <p className="pt-1.5 text-lg leading-relaxed text-muted">{step}</p>
                </li>
              ))}
            </ol>
          </Reveal>
        )}
      </section>
    </>
  );
}
