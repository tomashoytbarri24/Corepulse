import type { Metadata } from "next";
import Link from "next/link";
import AuthShell from "@/components/auth/AuthShell";
import { cerrarSesion } from "@/lib/auth/acciones";
import { createClient } from "@/lib/supabase/server";

export const metadata: Metadata = { title: "Cerrar sesión", robots: { index: false } };

// La app de escritorio abre esta ruta desde su menú de cuenta.
export default async function Logout() {
  const supabase = await createClient();
  const { data } = await supabase.auth.getClaims();
  if (!data?.claims) {
    return (
      <AuthShell titulo="No hay sesión iniciada" texto="Ya estás fuera de tu cuenta en este navegador.">
        <Link href="/login" className="block rounded-full bg-ink py-3.5 text-center text-[15px] font-medium text-bg">
          Iniciar sesión
        </Link>
      </AuthShell>
    );
  }
  return (
    <AuthShell titulo="¿Cerrar sesión?" texto={`Saldrás de ${String(data.claims.email ?? "tu cuenta")} en este navegador.`}>
      <form action={cerrarSesion}>
        <button className="w-full rounded-full bg-ink py-3.5 text-[15px] font-medium text-bg transition-transform duration-300 hover:scale-[1.02] active:scale-95">Cerrar sesión</button>
      </form>
      <Link href="/cuenta" className="mt-4 block text-center text-sm text-muted hover:text-accent">
        Cancelar
      </Link>
    </AuthShell>
  );
}
