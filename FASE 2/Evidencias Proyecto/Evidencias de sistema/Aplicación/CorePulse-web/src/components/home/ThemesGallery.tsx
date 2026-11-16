"use client";

import Image from "next/image";
import { motion, useScroll, useSpring, useTransform } from "motion/react";
import { useEffect, useRef, useState } from "react";

export type TemaGaleria = { name: string; image: string; accent: string };

// El scroll vertical mueve la galería en horizontal mientras la sección queda fija.
export default function ThemesGallery({ themes, etiqueta, titulo, subtitulo }: { themes: TemaGaleria[]; etiqueta: string; titulo: string; subtitulo: string }) {
  const ref = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end end"] });
  const smooth = useSpring(scrollYProgress, { stiffness: 100, damping: 28 });
  const track = useRef<HTMLDivElement>(null);
  const [distance, setDistance] = useState(0);
  useEffect(() => {
    // Recorrido exacto: lo que sobra de la fila respecto al ancho de la ventana.
    const measure = () => setDistance(Math.max(0, (track.current?.scrollWidth ?? 0) - window.innerWidth + 48));
    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, []);
  const x = useTransform(smooth, [0.05, 0.95], [0, -distance]);

  return (
    <section ref={ref} className="relative h-[320vh]">
      <div className="sticky top-0 flex h-screen flex-col justify-center overflow-hidden">
        <div className="mx-auto mb-12 w-full max-w-7xl px-6">
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-purple">{etiqueta}</p>
          <h2 className="mt-4 max-w-3xl text-4xl font-semibold leading-[1.05] tracking-[-0.035em] md:text-6xl">
            {titulo} <span className="text-muted">{subtitulo}</span>
          </h2>
        </div>
        <motion.div ref={track} style={{ x }} className="flex w-max gap-6 px-6 will-change-transform">
          {themes.map((t, i) => (
            <motion.figure
              key={t.name}
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.9, delay: i * 0.06, ease: [0.22, 1, 0.36, 1] }}
              className="group w-[78vw] shrink-0 md:w-[46vw]"
            >
              <div className="overflow-hidden rounded-[16px] border border-white/10">
                <Image
                  src={t.image}
                  alt={`CorePulse con el tema ${t.name}`}
                  width={1800}
                  height={1069}
                  sizes="(min-width: 768px) 46vw, 78vw"
                  className="w-full transition-transform duration-[1.2s] ease-[cubic-bezier(.22,1,.36,1)] group-hover:scale-[1.04]"
                />
              </div>
              <figcaption className="mt-4 flex items-center gap-2.5 text-sm text-muted">
                <span className="h-2.5 w-2.5 rounded-full" style={{ background: t.accent, boxShadow: `0 0 16px ${t.accent}` }} />
                {t.name}
              </figcaption>
            </motion.figure>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
