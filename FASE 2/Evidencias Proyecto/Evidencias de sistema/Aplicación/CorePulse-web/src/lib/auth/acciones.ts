"use server";

import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { siteUrl } from "@/lib/supabase/env";
import { rutaSegura } from "./rutas";

export type Estado = { error?: string; ok?: string; campos?: Record<string, string> };

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function traducir(codigo: string | undefined, mensaje: string) {
  switch (codigo) {
    case "invalid_credentials":
      return "Email o contraseña incorrectos.";
    case "email_not_confirmed":
      return "Confirma tu email antes de iniciar sesión. Revisa tu bandeja de entrada.";
    case "user_already_exists":
    case "email_exists":
      return "Ya existe una cuenta con ese email.";
    case "weak_password":
      return "La contraseña es demasiado débil. Usa al menos 8 caracteres, con letras y números.";
    case "same_password":
      return "La nueva contraseña debe ser distinta de la actual.";
    case "over_email_send_rate_limit":
    case "over_request_rate_limit":
      return "Demasiados intentos. Espera unos minutos y vuelve a probar.";
    case "signup_disabled":
      return "El registro está desactivado por ahora.";
    default:
      console.error("[auth]", codigo, mensaje);
      return "No se pudo completar la operación. Inténtalo de nuevo.";
  }
}

const texto = (fd: FormData, k: string) => String(fd.get(k) ?? "").trim();

export async function iniciarSesion(_: Estado, fd: FormData): Promise<Estado> {
  const email = texto(fd, "email").toLowerCase();
  const password = String(fd.get("password") ?? "");
  if (!EMAIL.test(email) || !password) return { error: "Escribe tu email y tu contraseña.", campos: { email } };

  const supabase = await createClient();
  const { error } = await supabase.auth.signInWithPassword({ email, password });
  if (error) return { error: traducir(error.code, error.message), campos: { email } };

  redirect(rutaSegura(fd.get("siguiente")));
}

export async function registrarse(_: Estado, fd: FormData): Promise<Estado> {
  const nombre = texto(fd, "nombre").slice(0, 80);
  const email = texto(fd, "email").toLowerCase();
  const password = String(fd.get("password") ?? "");
  const campos = { nombre, email };
  const siguiente = rutaSegura(fd.get("siguiente"));
  if (!nombre) return { error: "Escribe tu nombre.", campos };
  if (!EMAIL.test(email)) return { error: "Escribe un email válido.", campos };
  if (password.length < 8) return { error: "La contraseña debe tener al menos 8 caracteres.", campos };
  if (fd.get("acepto") !== "on") return { error: "Debes aceptar los términos y la política de privacidad.", campos };

  const supabase = await createClient();
  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    options: { data: { nombre }, emailRedirectTo: `${siteUrl()}/auth/callback?siguiente=${encodeURIComponent(siguiente)}` },
  });
  if (error) return { error: traducir(error.code, error.message), campos };

  // Con confirmación de email activada no hay sesión hasta que confirme.
  if (data.session) {
    redirect(siguiente);
  }
  return { ok: `Te enviamos un email a ${email}. Abre el enlace para activar tu cuenta.` };
}

export async function recuperar(_: Estado, fd: FormData): Promise<Estado> {
  const email = texto(fd, "email").toLowerCase();
  if (!EMAIL.test(email)) return { error: "Escribe un email válido.", campos: { email } };
  const supabase = await createClient();
  const { error } = await supabase.auth.resetPasswordForEmail(email, {
    redirectTo: `${siteUrl()}/auth/callback?siguiente=/cuenta/contrasena`,
  });
  if (error && (error.code === "over_email_send_rate_limit" || error.code === "over_request_rate_limit")) {
    return { error: traducir(error.code, error.message), campos: { email } };
  }
  // Mismo mensaje exista o no la cuenta, para no revelar qué emails están registrados.
  return { ok: "Si hay una cuenta con ese email, recibirás un enlace para elegir una nueva contraseña." };
}

export async function cambiarContrasena(_: Estado, fd: FormData): Promise<Estado> {
  const password = String(fd.get("password") ?? "");
  const repetir = String(fd.get("repetir") ?? "");
  if (password.length < 8) return { error: "La contraseña debe tener al menos 8 caracteres." };
  if (password !== repetir) return { error: "Las contraseñas no coinciden." };
  const supabase = await createClient();
  const { error } = await supabase.auth.updateUser({ password });
  if (error) return { error: traducir(error.code, error.message) };
  return { ok: "Contraseña actualizada." };
}

export async function actualizarNombre(_: Estado, fd: FormData): Promise<Estado> {
  const nombre = texto(fd, "nombre").slice(0, 80);
  if (!nombre) return { error: "El nombre no puede quedar vacío." };
  const supabase = await createClient();
  const { data } = await supabase.auth.getClaims();
  const id = data?.claims?.sub;
  if (!id) redirect("/login?siguiente=/cuenta");
  const { error } = await supabase.from("perfiles").update({ nombre }).eq("id", id);
  if (error) return { error: traducir(undefined, error.message) };
  return { ok: "Nombre guardado." };
}

export async function cerrarSesion() {
  const supabase = await createClient();
  await supabase.auth.signOut();
  redirect("/");
}
