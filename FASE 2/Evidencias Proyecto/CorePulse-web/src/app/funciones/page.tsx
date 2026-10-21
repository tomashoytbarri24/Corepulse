import type { Metadata } from "next";
import Image from "next/image";
import PageHeader from "@/components/PageHeader";
import { Reveal } from "@/components/motion/Reveal";
import ParallaxShot from "@/components/ParallaxShot";
import { getCabecera, getFunciones, imagen } from "@/lib/contenido";

export const dynamic = "force-dynamic";

export async function generateMetadata(): Promise<Metadata> {
  const c = await getCabecera("funciones");
  return { title: c.etiqueta, description: c.texto };
}

export default async function Funciones() {
  const [cabecera, modules] = await Promise.all([getCabecera("funciones"), getFunciones()]);
  return (
    <>
      <PageHeader kicker={cabecera.etiqueta} title={cabecera.titulo} text={cabecera.texto} />
      <nav aria-label="Módulos" className="sticky top-20 z-30 mx-auto mb-8 flex w-fit max-w-[92vw] gap-1 overflow-x-auto rounded-full border border-white/10 bg-[#0d0f15]/70 p-1 backdrop-blur-xl">
        {modules.map((m) => (
          <a key={m.slug} href={`#${m.slug}`} className="whitespace-nowrap rounded-full px-4 py-1.5 text-sm text-muted transition-colors hover:bg-white/[0.06] hover:text-ink">
            {m.etiqueta}
          </a>
        ))}
      </nav>
      {modules.map((m, i) => (
        <section key={m.slug} id={m.slug} className="scroll-mt-32 px-6 py-24 md:py-32">
          <div className={`mx-auto grid max-w-7xl items-center gap-12 lg:grid-cols-2 ${i % 2 ? "lg:[&>*:first-child]:order-2" : ""}`}>
            <div>
              <Reveal>
                <p className="text-sm font-semibold uppercase tracking-[0.16em]" style={{ color: m.color }}>{m.etiqueta}</p>
                <h2 className="mt-4 text-4xl font-semibold leading-[1.05] tracking-[-0.035em] md:text-5xl">{m.titulo}</h2>
              </Reveal>
              <ul className="mt-8 space-y-4">
                {m.puntos.map((p, j) => (
                  <Reveal key={p} delay={0.08 * j}>
                    <li className="flex gap-3 text-lg text-muted">
                      <span className="mt-2.5 h-1.5 w-1.5 shrink-0 rounded-full" style={{ background: m.color, boxShadow: `0 0 12px ${m.color}` }} />
                      {p}
                    </li>
                  </Reveal>
                ))}
              </ul>
            </div>
            <ParallaxShot>
              <Image src={imagen(m.imagen)} alt={m.titulo} width={1800} height={1069} sizes="(min-width: 1024px) 50vw, 100vw" className="w-full rounded-[16px] border border-white/10 shadow-[0_30px_90px_-20px_rgba(0,0,0,0.85)]" />
            </ParallaxShot>
          </div>
        </section>
      ))}
    </>
  );
}
