"use server";

import { refresh } from "next/cache";
import { redirect } from "next/navigation";
import type { Estado } from "@/lib/auth/acciones";
import { createClient } from "@/lib/supabase/server";

// Acepta «4990», «4.990» o «4 990»: solo pesos enteros, sin decimales.
function precio(valor: FormDataEntryValue | null) {
  const limpio = String(valor ?? "").replace(/[\s.]/g, "");
  if (!/^\d{1,9}$/.test(limpio)) return null;
  return Number(limpio);
}

export async function guardarPrecios(_: Estado, fd: FormData): Promise<Estado> {
  const supabase = await createClient();
  const { data } = await supabase.auth.getClaims();
  if (!data?.claims) redirect("/login?siguiente=/cuenta/admin");

  const slugs = fd.getAll("slug").map(String);
  const cambios = [];
  for (const slug of slugs) {
    const mensual = precio(fd.get(`mensual:${slug}`));
    const anual = precio(fd.get(`anual:${slug}`));
    if (mensual === null || anual === null) return { error: `Revisa los precios de «${slug}»: solo números enteros, sin decimales.` };
    cambios.push({ slug, mensual, anual });
  }

  // La base de datos solo deja escribir a los admins (política «admin edita precios»).
  for (const { slug, mensual, anual } of cambios) {
    const { data: filas, error } = await supabase
      .from("planes")
      .update({ precio_mensual: mensual, precio_anual: anual })
      .eq("slug", slug)
      .select("slug");
    if (error || !filas?.length) {
      console.error("[admin] guardar precios", slug, error?.message);
      return { error: "No se pudieron guardar los precios. Comprueba que tu cuenta sea admin." };
    }
  }
  return { ok: "Precios guardados. La web los mostrará en menos de un minuto." };
}

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export async function darAdmin(_: Estado, fd: FormData): Promise<Estado> {
  const email = String(fd.get("email") ?? "").trim().toLowerCase();
  if (!EMAIL.test(email)) return { error: "Escribe un email válido.", campos: { email } };

  const supabase = await createClient();
  const { data, error } = await supabase.rpc("dar_admin", { correo: email });
  if (error) {
    console.error("[admin] dar admin", error.message);
    return { error: "No se pudo dar admin. Comprueba que tu cuenta sea admin.", campos: { email } };
  }
  if (data === "no_existe") return { error: `No hay ninguna cuenta registrada con ${email}.`, campos: { email } };
  if (data === "ya_admin") return { ok: `${email} ya era admin.` };
  refresh();
  return { ok: `${email} ahora es admin.` };
}

// Vuelve a /cuenta/admin con ?admins=quitado o ?admins=error para mostrar el resultado.
export async function quitarAdmin(fd: FormData) {
  const id = String(fd.get("id") ?? "");
  if (!/^[0-9a-f-]{36}$/.test(id)) redirect("/cuenta/admin?admins=error");
  const supabase = await createClient();
  const { data, error } = await supabase.rpc("quitar_admin", { usuario: id });
  if (error) console.error("[admin] quitar admin", error.message);
  redirect(`/cuenta/admin?admins=${!error && data ? "quitado" : "error"}`);
}
