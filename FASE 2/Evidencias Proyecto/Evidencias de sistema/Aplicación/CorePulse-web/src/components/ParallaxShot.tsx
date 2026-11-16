"use client";

import { motion, useScroll, useSpring, useTransform } from "motion/react";
import { useRef, type ReactNode } from "react";

// La captura flota en sentido contrario al scroll y gira levemente en 3D.
export default function ParallaxShot({ children }: { children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start end", "end start"] });
  const p = useSpring(scrollYProgress, { stiffness: 90, damping: 22 });
  const y = useTransform(p, [0, 1], [70, -70]);
  const rotateY = useTransform(p, [0, 0.5, 1], [-10, 0, 8]);
  const scale = useTransform(p, [0, 0.5, 1], [0.92, 1, 0.96]);
  const opacity = useTransform(p, [0, 0.2, 0.85, 1], [0, 1, 1, 0.4]);
  return (
    <div ref={ref} className="[perspective:1400px]">
      <motion.div style={{ y, rotateY, scale, opacity }} className="will-change-transform">{children}</motion.div>
    </div>
  );
}
