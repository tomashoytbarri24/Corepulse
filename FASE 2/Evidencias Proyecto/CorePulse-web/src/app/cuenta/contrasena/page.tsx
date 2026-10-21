import type { Metadata } from "next";
import Link from "next/link";
import AuthShell from "@/components/auth/AuthShell";
import { FormContrasena } from "@/components/auth/Formularios";

export const metadata: Metadata = { title: "Cambiar contraseña", robots: { index: false } };

export default function Contrasena() {
  return (
    <AuthShell titulo="Nueva contraseña" texto="Elige una contraseña de al menos 8 caracteres.">
      <FormContrasena />
      <p className="mt-6 text-center text-sm">
        <Link href="/cuenta" className="text-accent hover:underline">
          Volver a mi cuenta
        </Link>
      </p>
    </AuthShell>
  );
}
