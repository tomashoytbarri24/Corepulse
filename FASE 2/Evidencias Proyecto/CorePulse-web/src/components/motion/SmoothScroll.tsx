"use client";

import Lenis from "lenis";
import { cancelFrame, frame } from "motion/react";
import { useEffect } from "react";
import { usePathname } from "next/navigation";

// Desplazamiento con inercia, como en las páginas de producto de Apple.
export default function SmoothScroll() {
  const pathname = usePathname();

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const lenis = new Lenis({ duration: 1.15, easing: (t) => 1 - Math.pow(1 - t, 4), autoRaf: false });
    // Lenis avanza en el mismo bucle de fotogramas que Motion: el scroll y las animaciones
    // que dependen de él se calculan juntos, sin un fotograma de desfase entre ambos.
    const paso = ({ timestamp }: { timestamp: number }) => lenis.raf(timestamp);
    frame.update(paso, true);
    return () => {
      cancelFrame(paso);
      lenis.destroy();
    };
  }, []);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);

  return null;
}
