import type { Metadata } from "next";
import { redirect } from "next/navigation";
import AuthShell from "@/components/auth/AuthShell";
import { FormRegistro } from "@/components/auth/Formularios";
import { rutaSegura } from "@/lib/auth/rutas";
import { createClient } from "@/lib/supabase/server";

export const metadata: Metadata = { title: "Crear cuenta", robots: { index: false } };

export default async function Registro({ searchParams }: { searchParams: Promise<{ siguiente?: string }> }) {
  const siguiente = rutaSegura((await searchParams).siguiente);
  const supabase = await createClient();
  const { data } = await supabase.auth.getClaims();
  if (data?.claims) redirect(siguiente);
  return (
    <AuthShell titulo="Crear cuenta" texto={siguiente.startsWith("/app/") ? "Al confirmar tu email volverás directo a la app de CorePulse." : "Gratis. Pasa a Pro cuando quieras."}>
      <FormRegistro siguiente={siguiente} />
    </AuthShell>
  );
}
