import type { Metadata } from "next";
import AuthShell from "@/components/auth/AuthShell";
import { FormRecuperar } from "@/components/auth/Formularios";

export const metadata: Metadata = { title: "Recuperar contraseña", robots: { index: false } };

export default function Recuperar() {
  return (
    <AuthShell titulo="Recuperar contraseña" texto="Te enviaremos un enlace para elegir una nueva.">
      <FormRecuperar />
    </AuthShell>
  );
}
