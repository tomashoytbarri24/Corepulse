"use client";

import Image from "next/image";
import Link from "next/link";
import { motion, useReducedMotion, useScroll, useSpring, useTransform } from "motion/react";
import { useRef } from "react";
import { StaggerWords } from "@/components/motion/Reveal";
import type { Inicio, Sitio } from "@/lib/contenido";

const ease = [0.22, 1, 0.36, 1] as const;

export default function Hero({ inicio, sitio, imagenUrl }: { inicio: Inicio; sitio: Pick<Sitio, "version" | "compatibilidad">; imagenUrl: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const reduce = useReducedMotion();
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end start"] });
  const smooth = useSpring(scrollYProgress, { stiffness: 90, damping: 24, mass: 0.4 });

  // La pantalla llega inclinada y se endereza al bajar, como en apple.com.
  const rotateX = useTransform(smooth, [0, 0.45], [reduce ? 0 : 24, 0]);
  const scale = useTransform(smooth, [0, 0.45], [reduce ? 1 : 0.86, 1]);
  const y = useTransform(smooth, [0, 0.45], [0, -40]);
  const textOpacity = useTransform(smooth, [0, 0.25], [1, 0]);
  const textY = useTransform(smooth, [0, 0.25], [0, -60]);
  const glow = useTransform(smooth, [0, 0.45], [0.35, 0.8]);

  return (
    <section ref={ref} className="relative overflow-hidden pb-24 pt-36 md:pt-44">
      {/* Aurora de fondo */}
      <div aria-hidden className="pointer-events-none absolute inset-0">
        <div className="animate-aurora absolute -top-40 left-1/2 h-[620px] w-[920px] -translate-x-1/2 rounded-full bg-[radial-gradient(closest-side,rgba(78,221,200,0.22),transparent)]" />
        <div className="animate-aurora absolute -top-10 left-[12%] h-[420px] w-[520px] rounded-full bg-[radial-gradient(closest-side,rgba(183,86,234,0.18),transparent)] [animation-delay:-6s]" />
        <div className="animate-aurora absolute top-20 right-[8%] h-[380px] w-[480px] rounded-full bg-[radial-gradient(closest-side,rgba(23,185,247,0.16),transparent)] [animation-delay:-3s]" />
      </div>

      <motion.div style={{ opacity: textOpacity, y: textY }} className="relative mx-auto max-w-5xl px-6 text-center">
        <motion.div
          initial={{ opacity: 0, y: 12, filter: "blur(6px)" }}
          animate={{ opacity: 1, y: 0, filter: "blur(0px)", transitionEnd: { filter: "none" } }}
          transition={{ duration: 0.9, ease }}
          className="mx-auto inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3.5 py-1.5 text-xs text-muted backdrop-blur"
        >
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent opacity-60" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-accent" />
          </span>
          {sitio.version} · {sitio.compatibilidad}
        </motion.div>

        <h1 className="mt-7 text-[clamp(2.75rem,8vw,6.5rem)] font-semibold leading-[0.98] tracking-[-0.045em]">
          <StaggerWords text={inicio.titulo1} delay={0.1} />
          <br />
          <StaggerWords text={inicio.titulo2} className="text-gradient" delay={0.3} />
        </h1>

        <motion.p
          initial={{ opacity: 0, y: 16, filter: "blur(8px)" }}
          animate={{ opacity: 1, y: 0, filter: "blur(0px)", transitionEnd: { filter: "none" } }}
          transition={{ duration: 1.1, ease, delay: 0.7 }}
          className="mx-auto mt-7 max-w-2xl text-lg leading-relaxed text-muted md:text-xl"
        >
          {inicio.subtitulo}
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, ease, delay: 0.9 }}
          className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row"
        >
          <Link
            href="/descargar"
            className="group relative overflow-hidden rounded-full bg-ink px-7 py-3.5 text-[15px] font-medium text-bg transition-transform duration-300 hover:scale-[1.03] active:scale-95"
          >
            <span className="relative z-10">Descargar gratis</span>
            <span className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/60 to-transparent transition-transform duration-700 group-hover:translate-x-full" />
          </Link>
          <Link href="/funciones" className="group flex items-center gap-1.5 rounded-full px-6 py-3.5 text-[15px] text-accent">
            Ver funciones
            <span className="transition-transform duration-300 group-hover:translate-x-1">→</span>
          </Link>
        </motion.div>
      </motion.div>

      <div className="relative mx-auto mt-16 max-w-6xl px-4 [perspective:1600px] md:mt-20">
        <motion.div
          initial={{ opacity: 0, y: 80 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1.4, ease, delay: 0.5 }}
        >
          <motion.div style={{ rotateX, scale, y, transformOrigin: "50% 0%" }} className="relative will-change-transform">
            <motion.div style={{ opacity: glow }} aria-hidden className="absolute -inset-x-10 -inset-y-6 -z-10 rounded-[40px] bg-[radial-gradient(60%_60%_at_50%_40%,rgba(78,221,200,0.35),rgba(183,86,234,0.15)_50%,transparent_75%)]" />
            <Image
              src={imagenUrl}
              alt={inicio.imagenAlt}
              width={1800}
              height={1069}
              priority
              className="w-full rounded-[18px] border border-white/10 shadow-[0_40px_120px_-20px_rgba(0,0,0,0.8)]"
            />
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}
