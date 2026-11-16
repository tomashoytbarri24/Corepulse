"use client";

import Link from "next/link";
import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";
import Icon from "@/components/Icon";
import { Reveal, TiltCard } from "@/components/motion/Reveal";
import type { Caracteristica, Plan } from "@/lib/contenido";

const ISO = /^[A-Z]{3}$/;
// Con un código ISO (CLP, USD…) se usa el formato oficial de esa moneda; si no, número simple.
const fmt = (n: number, moneda: string) =>
  ISO.test(moneda)
    ? new Intl.NumberFormat(moneda === "CLP" ? "es-CL" : "es", { style: "currency", currency: moneda }).format(n)
    : n.toLocaleString("es", { minimumFractionDigits: n % 1 ? 2 : 0, maximumFractionDigits: 2 });

function Cell({ value }: { value: boolean | string }) {
  if (value === true) return <Icon name="check" className="h-5 w-5 text-accent" />;
  if (value === false) return <Icon name="dash" className="h-5 w-5 text-white/25" />;
  return <span className="text-sm text-ink/90">{value}</span>;
}

function Precio({ plan, yearly, nota }: { plan: Plan; yearly: boolean; nota: string }) {
  const gratis = plan.precio_mensual === 0 && plan.precio_anual === 0;
  const price = yearly ? plan.precio_anual : plan.precio_mensual;
  const iso = ISO.test(plan.moneda);
  return (
    <>
      <div className="mt-8 flex items-baseline gap-2">
        {!iso && <span className="text-6xl font-semibold tracking-[-0.05em]">{plan.moneda}</span>}
        <AnimatePresence mode="popLayout" initial={false}>
          <motion.span
            key={gratis ? "0" : `${yearly}-${price}`}
            initial={{ y: 30, opacity: 0, filter: "blur(6px)" }}
            animate={{ y: 0, opacity: 1, filter: "blur(0px)", transitionEnd: { filter: "none" } }}
            exit={{ y: -30, opacity: 0, filter: "blur(6px)" }}
            transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
            className="text-6xl font-semibold tracking-[-0.05em]"
          >
            {fmt(gratis ? 0 : price, plan.moneda)}
          </motion.span>
        </AnimatePresence>
        {iso && <span className="text-sm font-medium text-muted">{plan.moneda}</span>}
      </div>
      <p className="mt-1 text-sm text-muted">
        {gratis
          ? nota
          : yearly
            ? `al año · equivale a ${iso ? "" : `${plan.moneda} `}${fmt(iso ? Math.round(plan.precio_anual / 12) : Math.round((plan.precio_anual / 12) * 100) / 100, plan.moneda)}/mes`
            : "al mes · cancela cuando quieras"}
      </p>
    </>
  );
}

export default function PricingTable({ planes, caracteristicas, nota }: { planes: Plan[]; caracteristicas: Caracteristica[]; nota: string }) {
  const [yearly, setYearly] = useState(true);
  const pagos = planes.filter((p) => p.precio_mensual > 0 && p.precio_anual > 0);
  const saving = pagos.length ? Math.max(...pagos.map((p) => Math.round((1 - p.precio_anual / (p.precio_mensual * 12)) * 100))) : 0;

  return (
    <div className="mx-auto max-w-5xl px-6">
      {pagos.length > 0 && (
        <Reveal className="flex justify-center">
          <div role="group" aria-label="Periodo de facturación" className="relative flex rounded-full border border-white/10 bg-white/[0.03] p-1">
            {[
              { id: false, label: "Mensual" },
              { id: true, label: saving > 0 ? `Anual · −${saving}%` : "Anual" },
            ].map((opt) => (
              <button
                key={String(opt.id)}
                onClick={() => setYearly(opt.id)}
                aria-pressed={yearly === opt.id}
                className={`relative z-10 rounded-full px-5 py-2 text-sm transition-colors ${yearly === opt.id ? "text-bg" : "text-muted hover:text-ink"}`}
              >
                {yearly === opt.id && (
                  <motion.span layoutId="billing-pill" className="absolute inset-0 -z-10 rounded-full bg-ink" transition={{ type: "spring", stiffness: 420, damping: 34 }} />
                )}
                {opt.label}
              </button>
            ))}
          </div>
        </Reveal>
      )}

      <div className={`mt-12 grid gap-5 ${planes.length > 1 ? "md:grid-cols-2" : ""}`}>
        {planes.map((plan, i) => (
          <Reveal key={plan.slug} delay={i * 0.1}>
            {plan.destacado ? (
              <div className="relative h-full rounded-3xl p-px [background:linear-gradient(140deg,#4EDDC8,#17B9F7_45%,#B756EA)]">
                <TiltCard className="h-full rounded-[23px] bg-[#0f1219] p-9">
                  <div className="flex items-center justify-between">
                    <h2 className="text-lg font-semibold">{plan.nombre}</h2>
                    {plan.etiqueta && <span className="rounded-full bg-accent/15 px-3 py-1 text-xs font-medium text-accent">{plan.etiqueta}</span>}
                  </div>
                  <p className="mt-1 text-sm text-muted">{plan.descripcion}</p>
                  <Precio plan={plan} yearly={yearly} nota={nota} />
                  <Link href={plan.boton_enlace} className="mt-8 block rounded-full bg-ink py-3 text-center text-[15px] font-medium text-bg transition-transform duration-300 hover:scale-[1.02] active:scale-95">
                    {plan.boton_texto}
                  </Link>
                </TiltCard>
              </div>
            ) : (
              <TiltCard className="h-full rounded-3xl border border-white/[0.08] bg-panel/70 p-9">
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold">{plan.nombre}</h2>
                  {plan.etiqueta && <span className="rounded-full bg-white/10 px-3 py-1 text-xs text-muted">{plan.etiqueta}</span>}
                </div>
                <p className="mt-1 text-sm text-muted">{plan.descripcion}</p>
                <Precio plan={plan} yearly={yearly} nota={nota} />
                <Link href={plan.boton_enlace} className="mt-8 block rounded-full border border-white/15 py-3 text-center text-[15px] transition-colors hover:border-accent hover:text-accent">
                  {plan.boton_texto}
                </Link>
              </TiltCard>
            )}
          </Reveal>
        ))}
      </div>

      {caracteristicas.length > 0 && (
        <Reveal delay={0.1}>
          <div className="mt-16 overflow-hidden rounded-3xl border border-white/[0.08]">
            <table className="w-full text-left">
              <caption className="sr-only">Comparativa de planes</caption>
              <thead className="bg-white/[0.03] text-xs uppercase tracking-[0.14em] text-muted">
                <tr>
                  <th scope="col" className="px-6 py-4 font-medium">Función</th>
                  <th scope="col" className="w-28 px-4 py-4 font-medium sm:w-44">Free</th>
                  <th scope="col" className="w-28 px-4 py-4 font-medium text-accent sm:w-52">Pro</th>
                </tr>
              </thead>
              <tbody>
                {caracteristicas.map((row, i) => (
                  <motion.tr
                    key={row.id}
                    initial={{ opacity: 0, x: -12 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: i * 0.04, duration: 0.5 }}
                    className="border-t border-white/[0.06]"
                  >
                    <th scope="row" className="px-6 py-4 text-sm font-normal text-ink/90">{row.caracteristica}</th>
                    <td className="px-4 py-4"><Cell value={row.free} /></td>
                    <td className="px-4 py-4"><Cell value={row.pro} /></td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        </Reveal>
      )}
    </div>
  );
}
