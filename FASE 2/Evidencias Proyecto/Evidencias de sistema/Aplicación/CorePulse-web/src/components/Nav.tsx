"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { AnimatePresence, motion, useMotionValueEvent, useScroll } from "motion/react";
import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { nav } from "@/lib/site";
import Logo from "./Logo";

export default function Nav() {
  const pathname = usePathname();
  const { scrollY } = useScroll();
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  useMotionValueEvent(scrollY, "change", (y) => setScrolled(y > 24));
  const [conSesion, setConSesion] = useState(false);
  useEffect(() => {
    // Solo para el enlace de la barra; la protección real está en el servidor.
    const supabase = createClient();
    supabase.auth.getSession().then(({ data }) => setConSesion(!!data.session));
    const { data } = supabase.auth.onAuthStateChange((_e, session) => setConSesion(!!session));
    return () => data.subscription.unsubscribe();
  }, []);
  const cuenta = conSesion ? { href: "/cuenta", label: "Mi cuenta" } : { href: "/login", label: "Iniciar sesión" };

  return (
    <header className="fixed inset-x-0 top-0 z-50 flex justify-center px-4 pt-3">
      <motion.nav
        initial={{ y: -40, opacity: 0 }}
        animate={{ y: 0, opacity: 1, maxWidth: scrolled ? 880 : 1180 }}
        transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
        className={`flex w-full items-center justify-between rounded-2xl border px-4 py-2.5 transition-[background,border-color,backdrop-filter] duration-500 ${
          scrolled ? "border-white/10 bg-[#0d0f15]/70 backdrop-blur-xl backdrop-saturate-150" : "border-transparent bg-transparent"
        }`}
      >
        <Link href="/" className="flex items-center gap-2" onClick={() => setOpen(false)}>
          <Logo className="h-7 w-7" />
          <span className="text-[15px] font-semibold tracking-tight">
            Core<span className="text-accent">Pulse</span>
          </span>
        </Link>

        <ul className="hidden items-center gap-1 md:flex">
          {nav.map((item) => {
            const active = pathname === item.href;
            return (
              <li key={item.href} className="relative">
                <Link
                  href={item.href}
                  className={`relative z-10 block rounded-xl px-3.5 py-1.5 text-[13px] transition-colors ${active ? "text-ink" : "text-muted hover:text-ink"}`}
                >
                  {item.label}
                </Link>
                {active && (
                  <motion.span layoutId="nav-pill" className="absolute inset-0 rounded-xl bg-white/[0.07]" transition={{ type: "spring", stiffness: 380, damping: 32 }} />
                )}
              </li>
            );
          })}
        </ul>

        <div className="flex items-center gap-2">
          <Link href={cuenta.href} className="hidden rounded-xl px-3 py-1.5 text-[13px] text-muted transition-colors hover:text-ink sm:block">
            {cuenta.label}
          </Link>
          <Link
            href="/descargar"
            className="rounded-xl bg-ink px-3.5 py-1.5 text-[13px] font-medium text-bg transition-transform duration-300 hover:scale-[1.04] active:scale-95"
          >
            Descargar
          </Link>
          <button
            aria-label={open ? "Cerrar menú" : "Abrir menú"}
            aria-expanded={open}
            onClick={() => setOpen((v) => !v)}
            className="grid h-9 w-9 place-items-center rounded-xl md:hidden"
          >
            <span className="relative block h-3 w-4">
              <motion.span animate={open ? { rotate: 45, y: 5 } : { rotate: 0, y: 0 }} className="absolute left-0 top-0 h-[1.5px] w-4 rounded bg-ink" />
              <motion.span animate={open ? { rotate: -45, y: -5 } : { rotate: 0, y: 0 }} className="absolute bottom-0 left-0 h-[1.5px] w-4 rounded bg-ink" />
            </span>
          </button>
        </div>
      </motion.nav>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -12, filter: "blur(8px)" }}
            animate={{ opacity: 1, y: 0, filter: "blur(0px)", transitionEnd: { filter: "none" } }}
            exit={{ opacity: 0, y: -12, filter: "blur(8px)" }}
            transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
            className="absolute inset-x-4 top-[68px] rounded-2xl border border-white/10 bg-[#0d0f15]/90 p-3 backdrop-blur-xl md:hidden"
          >
            {[...nav, cuenta].map((item, i) => (
              <motion.div key={item.href} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.05 * i }}>
                <Link href={item.href} onClick={() => setOpen(false)} className="block rounded-xl px-3 py-3 text-[15px] hover:bg-white/5">
                  {item.label}
                </Link>
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
