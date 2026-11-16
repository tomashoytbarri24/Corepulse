import type { Metadata } from "next";
import { redirect } from "next/navigation";
import AuthShell from "@/components/auth/AuthShell";
import { FormLogin } from "@/components/auth/Formularios";
import { rutaSegura } from "@/lib/auth/rutas";
import { createClient } from "@/lib/supabase/server";

export const metadata: Metadata = { title: "Iniciar sesión", robots: { index: false } };

export default async function Login({ searchParams }: { searchParams: Promise<{ siguiente?: string }> }) {
  const siguiente = rutaSegura((await searchParams).siguiente);
  const supabase = await createClient();
  const { data } = await supabase.auth.getClaims();
  if (data?.claims) redirect(siguiente);
  return (
    <AuthShell titulo="Iniciar sesión" texto="Accede a tu cuenta de CorePulse.">
      <FormLogin siguiente={siguiente} />
    </AuthShell>
  );
}
