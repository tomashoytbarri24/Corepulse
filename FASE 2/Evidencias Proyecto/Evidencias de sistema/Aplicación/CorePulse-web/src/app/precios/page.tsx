import type { Metadata } from "next";
import PageHeader from "@/components/PageHeader";
import PricingTable from "@/components/PricingTable";
import { Reveal } from "@/components/motion/Reveal";
import { getCaracteristicas, getPaginaPrecios, getPlanes, getPreguntas } from "@/lib/contenido";

export const dynamic = "force-dynamic";

export async function generateMetadata(): Promise<Metadata> {
  const p = await getPaginaPrecios();
  return { title: p.etiqueta, description: p.texto };
}

export default async function Precios() {
  const [pagina, planes, caracteristicas, faq] = await Promise.all([getPaginaPrecios(), getPlanes(), getCaracteristicas(), getPreguntas("precios")]);
  return (
    <>
      <PageHeader kicker={pagina.etiqueta} title={pagina.titulo} text={pagina.texto} />
      <PricingTable planes={planes} caracteristicas={caracteristicas} nota={pagina.nota} />
      {faq.length > 0 && (
        <section className="mx-auto max-w-3xl px-6 py-32">
          <Reveal>
            <h2 className="text-3xl font-semibold tracking-[-0.03em] md:text-4xl">Preguntas frecuentes</h2>
          </Reveal>
          <div className="mt-10 divide-y divide-white/[0.07] border-y border-white/[0.07]">
            {faq.map((f, i) => (
              <Reveal key={f.id} delay={i * 0.05}>
                <details className="group py-6">
                  <summary className="flex cursor-pointer list-none items-center justify-between gap-6 text-lg">
                    {f.pregunta}
                    <span className="text-2xl text-muted transition-transform duration-300 group-open:rotate-45">+</span>
                  </summary>
                  <p className="mt-3 leading-relaxed text-muted">{f.respuesta}</p>
                </details>
              </Reveal>
            ))}
          </div>
        </section>
      )}
    </>
  );
}
