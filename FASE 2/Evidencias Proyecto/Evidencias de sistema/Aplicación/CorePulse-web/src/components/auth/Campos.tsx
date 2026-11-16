"use client";

import { AnimatePresence, motion } from "motion/react";
import { useFormStatus } from "react-dom";
import type { Estado } from "@/lib/auth/acciones";

export function Campo({
  label,
  name,
  type = "text",
  autoComplete,
  defaultValue,
  minLength,
  maxLength,
}: {
  label: string;
  name: string;
  type?: string;
  autoComplete?: string;
  defaultValue?: string;
  minLength?: number;
  maxLength?: number;
}) {
  return (
    <label className="block">
      <span className="text-sm text-muted">{label}</span>
      <input
        name={name}
        type={type}
        required
        autoComplete={autoComplete}
        defaultValue={defaultValue}
        minLength={minLength}
        maxLength={maxLength}
        className="mt-1.5 block w-full rounded-xl border border-white/10 bg-white/[0.04] px-4 py-3 text-[15px] text-ink outline-none transition-[border-color,box-shadow] duration-300 placeholder:text-white/30 focus:border-accent/70 focus:shadow-[0_0_0_4px_rgba(78,221,200,0.12)]"
      />
    </label>
  );
}

export function Enviar({ children }: { children: React.ReactNode }) {
  const { pending } = useFormStatus();
  return (
    <button
      type="submit"
      disabled={pending}
      className="relative mt-2 w-full overflow-hidden rounded-full bg-ink py-3.5 text-[15px] font-medium text-bg transition-transform duration-300 hover:scale-[1.02] active:scale-95 disabled:cursor-wait disabled:opacity-70"
    >
      <span className={pending ? "opacity-0" : ""}>{children}</span>
      {pending && (
        <span className="absolute inset-0 grid place-items-center">
          <span className="h-5 w-5 animate-spin rounded-full border-2 border-bg/30 border-t-bg" />
        </span>
      )}
    </button>
  );
}

export function Mensaje({ estado }: { estado: Estado }) {
  const texto = estado.error ?? estado.ok;
  return (
    <AnimatePresence mode="wait">
      {texto && (
        <motion.p
          key={texto}
          role={estado.error ? "alert" : "status"}
          initial={{ opacity: 0, y: -6, filter: "blur(4px)" }}
          animate={{ opacity: 1, y: 0, filter: "blur(0px)", transitionEnd: { filter: "none" } }}
          exit={{ opacity: 0 }}
          className={`rounded-xl border px-4 py-3 text-sm ${estado.error ? "border-red-400/30 bg-red-500/10 text-red-200" : "border-accent/30 bg-accent/10 text-accent"}`}
        >
          {texto}
        </motion.p>
      )}
    </AnimatePresence>
  );
}
