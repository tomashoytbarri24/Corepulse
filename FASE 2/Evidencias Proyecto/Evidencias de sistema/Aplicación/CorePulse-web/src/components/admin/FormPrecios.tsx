"use client";

import { useActionState } from "react";
import { darAdmin, guardarPrecios } from "@/lib/admin/acciones";
import type { Estado } from "@/lib/auth/acciones";
import { Campo, Enviar, Mensaje } from "@/components/auth/Campos";

type PlanPrecio = { slug: string; nombre: string; moneda: string; precio_mensual: number; precio_anual: number };

const inicial: Estado = {};

export function FormPrecios({ planes }: { planes: PlanPrecio[] }) {
  const [estado, accion] = useActionState(guardarPrecios, inicial);
  return (
    <form action={accion} className="space-y-5">
      {planes.map((p) => (
        <fieldset key={p.slug} className="rounded-2xl border border-white/[0.08] bg-white/[0.02] p-5">
          <input type="hidden" name="slug" value={p.slug} />
          <legend className="px-1 font-medium">{p.nombre}</legend>
          <div className="grid gap-4 sm:grid-cols-2">
            <Campo label={`Mensual (${p.moneda})`} name={`mensual:${p.slug}`} type="number" defaultValue={String(p.precio_mensual)} />
            <Campo label={`Anual (${p.moneda})`} name={`anual:${p.slug}`} type="number" defaultValue={String(p.precio_anual)} />
          </div>
        </fieldset>
      ))}
      <Mensaje estado={estado} />
      <Enviar>Guardar precios</Enviar>
    </form>
  );
}

export function FormDarAdmin() {
  const [estado, accion] = useActionState(darAdmin, inicial);
  return (
    <form action={accion} className="space-y-3">
      <Campo label="Email de la cuenta" name="email" type="email" autoComplete="off" defaultValue={estado.campos?.email} />
      <Mensaje estado={estado} />
      <Enviar>Dar admin</Enviar>
    </form>
  );
}
