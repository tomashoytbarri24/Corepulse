import type { Metadata } from "next";
import Link from "next/link";
import AuthShell from "@/components/auth/AuthShell";

export const metadata: Metadata = { title: "Enlace no válido", robots: { index: false } };

export default function AuthError() {
  return (
    <AuthShell titulo="El enlace no es válido" texto="Puede que haya caducado o que ya se haya usado. Pide uno nuevo.">
      <div className="space-y-3">
        <Link href="/recuperar" className="block rounded-full bg-ink py-3.5 text-center text-[15px] font-medium text-bg">
          Recuperar contraseña
        </Link>
        <Link href="/login" className="block text-center text-sm text-muted hover:text-accent">
          Iniciar sesión
        </Link>
      </div>
    </AuthShell>
  );
}
