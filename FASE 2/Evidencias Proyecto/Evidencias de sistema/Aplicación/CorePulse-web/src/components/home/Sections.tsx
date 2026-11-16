"use client";

import Link from "next/link";
import { motion } from "motion/react";
import { Counter, Reveal, ScrollLitText, TiltCard } from "@/components/motion/Reveal";
import Icon from "@/components/Icon";
import type { Cifra, Destacado } from "@/lib/contenido";

export function Manifesto({ text }: { text: string }) {
  if (!text) return null;
  return (
    <section className="mx-auto max-w-5xl px-6 py-32 md:py-44">
      <ScrollLitText className="text-[clamp(1.9rem,4.4vw,3.6rem)] font-semibold leading-[1.12] tracking-[-0.03em]" text={text} />
    </section>
  );
}

export function Stats({ cifras }: { cifras: Cifra[] }) {
  if (!cifras.length) return null;
  return (
    <section className="mx-auto max-w-6xl px-6 py-24">
      <div className="grid grid-cols-2 gap-px overflow-hidden rounded-3xl border border-white/[0.06] bg-white/[0.06] md:grid-cols-4">
        {cifras.map((s, i) => (
          <Reveal key={s.id} delay={i * 0.08} className="bg-bg p-8 md:p-10">
            <Counter to={s.valor} suffix={s.sufijo} className="text-gradient text-6xl font-semibold tracking-[-0.05em] md:text-7xl" />
            <p className="mt-3 text-sm leading-relaxed text-muted">{s.etiqueta}</p>
          </Reveal>
        ))}
      </div>
    </section>
  );
}

export function Bento({ items, titulo, subtitulo }: { items: Destacado[]; titulo: string; subtitulo: string }) {
  if (!items.length) return null;
  return (
    <section className="mx-auto max-w-6xl px-6 py-24">
      <Reveal>
        <h2 className="max-w-3xl text-4xl font-semibold leading-[1.05] tracking-[-0.035em] md:text-6xl">
          {titulo} <span className="text-muted">{subtitulo}</span>
        </h2>
      </Reveal>
      <div className="mt-14 grid gap-4 md:grid-cols-3">
        {items.map((b, i) => (
          <Reveal key={b.id} delay={i * 0.06} className={b.ancho ? "md:col-span-2" : ""}>
            <TiltCard className="h-full rounded-3xl border border-white/[0.07] bg-gradient-to-b from-panel-2/80 to-panel/60 p-8">
              <div className="grid h-12 w-12 place-items-center rounded-2xl border border-white/10 bg-white/[0.04] text-accent">
                <Icon name={b.icono} className="h-6 w-6" />
              </div>
              <h3 className="mt-6 text-xl font-semibold tracking-tight">{b.titulo}</h3>
              <p className="mt-2 leading-relaxed text-muted">{b.texto}</p>
            </TiltCard>
          </Reveal>
        ))}
      </div>
    </section>
  );
}

export function Marquee({ items }: { items: string[] }) {
  if (!items.length) return null;
  return (
    <section aria-label="Compatibilidad" className="relative overflow-hidden border-y border-white/[0.06] py-8 [mask-image:linear-gradient(90deg,transparent,black_15%,black_85%,transparent)]">
      <div className="animate-marquee flex w-max gap-14">
        {[...items, ...items].map((s, i) => (
          <span key={i} aria-hidden={i >= items.length} className="text-2xl font-semibold tracking-tight text-white/25 md:text-3xl">
            {s}
          </span>
        ))}
      </div>
    </section>
  );
}

export function FinalCta({ titulo1, titulo2, texto }: { titulo1: string; titulo2: string; texto: string }) {
  return (
    <section className="relative overflow-hidden px-6 py-40 text-center">
      <motion.div
        aria-hidden
        className="absolute left-1/2 top-1/2 -z-10 h-[520px] w-[820px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[radial-gradient(closest-side,rgba(78,221,200,0.22),rgba(183,86,234,0.1)_60%,transparent)]"
        animate={{ scale: [1, 1.12, 1], opacity: [0.7, 1, 0.7] }}
        transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
      />
      <Reveal>
        <h2 className="mx-auto max-w-4xl text-[clamp(2.5rem,7vw,5.5rem)] font-semibold leading-[1] tracking-[-0.045em]">
          <span className="text-shine">{titulo1}</span>
          <br />
          <span className="text-gradient">{titulo2}</span>
        </h2>
      </Reveal>
      <Reveal delay={0.15}>
        <p className="mx-auto mt-6 max-w-xl text-lg text-muted">{texto}</p>
        <div className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <Link href="/descargar" className="rounded-full bg-ink px-7 py-3.5 text-[15px] font-medium text-bg transition-transform duration-300 hover:scale-[1.04] active:scale-95">
            Descargar gratis
          </Link>
          <Link href="/precios" className="rounded-full border border-white/15 px-7 py-3.5 text-[15px] transition-colors hover:border-accent hover:text-accent">
            Ver planes
          </Link>
        </div>
      </Reveal>
    </section>
  );
}
