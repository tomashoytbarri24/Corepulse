"use client";

import Image from "next/image";
import { AnimatePresence, motion, useMotionValueEvent, useScroll, useSpring } from "motion/react";
import { useRef, useState } from "react";

export type Paso = { kicker: string; title: string; text: string; image: string; color: string };

export default function StickyFeatures({ steps }: { steps: Paso[] }) {
  const ref = useRef<HTMLElement>(null);
  const [active, setActive] = useState(0);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end end"] });
  const progress = useSpring(scrollYProgress, { stiffness: 120, damping: 30 });
  useMotionValueEvent(scrollYProgress, "change", (v) => {
    if (!steps.length) return;
    setActive(Math.min(steps.length - 1, Math.max(0, Math.floor(v * steps.length))));
  });

  if (!steps.length) return null;
  return (
    <section ref={ref} className="relative" style={{ height: `${steps.length * 100}vh` }}>
      <div className="sticky top-0 flex h-screen items-center overflow-hidden">
        <div className="mx-auto grid w-full max-w-7xl items-center gap-10 px-6 lg:grid-cols-[0.8fr_1.2fr]">
          <div className="relative">
            <div className="mb-8 flex gap-1.5">
              {steps.map((s, i) => (
                <div key={s.kicker} className="h-1 flex-1 overflow-hidden rounded-full bg-white/10">
                  <motion.div
                    className="h-full rounded-full"
                    style={{ background: s.color, transformOrigin: "0% 50%" }}
                    initial={{ scaleX: 0 }}
                    animate={{ scaleX: i <= active ? 1 : 0 }}
                    transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
                  />
                </div>
              ))}
            </div>
            <AnimatePresence mode="wait">
              <motion.div
                key={active}
                initial={{ opacity: 0, y: 30, filter: "blur(10px)" }}
                animate={{ opacity: 1, y: 0, filter: "blur(0px)", transitionEnd: { filter: "none" } }}
                exit={{ opacity: 0, y: -30, filter: "blur(10px)" }}
                transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
              >
                <p className="text-sm font-semibold uppercase tracking-[0.16em]" style={{ color: steps[active].color }}>
                  {steps[active].kicker}
                </p>
                <h2 className="mt-4 text-4xl font-semibold leading-[1.05] tracking-[-0.035em] md:text-6xl">{steps[active].title}</h2>
                <p className="mt-6 max-w-md text-lg leading-relaxed text-muted">{steps[active].text}</p>
              </motion.div>
            </AnimatePresence>
          </div>

          <div className="relative aspect-[1800/1069] w-full">
            {/* Un halo por paso: cambiar de color es un fundido de opacidad (sin repintar cada fotograma). */}
            {steps.map((s, i) => (
              <motion.div
                key={s.kicker}
                aria-hidden
                className="absolute -inset-16 -z-10 rounded-[40px]"
                style={{ background: `radial-gradient(50% 50% at 50% 50%, ${s.color}33, transparent 75%)` }}
                initial={false}
                animate={{ opacity: i === active ? 1 : 0 }}
                transition={{ duration: 0.8 }}
              />
            ))}
            {/* Todas las capturas quedan montadas y decodificadas: cambiar de paso es solo un fundido.
                Sin desenfoque: sobre una captura tan grande era lo que más tirones daba al hacer scroll. */}
            {steps.map((s, i) => (
              <motion.div
                key={s.image}
                className="absolute inset-0"
                aria-hidden={i !== active}
                initial={false}
                animate={
                  i === active
                    ? { opacity: 1, scale: [1.04, 1] }
                    : { opacity: 0, scale: 0.97 }
                }
                transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
              >
                <Image
                  src={s.image}
                  alt={i === active ? s.title : ""}
                  fill
                  loading="eager"
                  sizes="(min-width: 1024px) 60vw, 100vw"
                  className="rounded-[16px] border border-white/10 object-cover shadow-[0_30px_100px_-20px_rgba(0,0,0,0.85)]"
                />
              </motion.div>
            ))}
          </div>
        </div>
        <motion.div aria-hidden className="absolute bottom-0 left-0 h-px w-full origin-left bg-gradient-to-r from-accent via-cyan to-purple" style={{ scaleX: progress }} />
      </div>
    </section>
  );
}
