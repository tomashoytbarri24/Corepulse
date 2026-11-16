"use server";

import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { leerSolicitud, urlVuelta } from "./solicitud";

const desdeForm = (fd: FormData) =>
  leerSolicitud({ puerto: String(fd.get("puerto") ?? ""), estado: String(fd.get("estado") ?? ""), reto: String(fd.get("reto") ?? "") });

export async function autorizarApp(fd: FormData) {
  const s = desdeForm(fd);
  if (!s) redirect("/app/conectar");
  const supabase = await createClient();
  const { data, error } = await supabase.rpc("crear_codigo_app", { reto: s.reto });
  if (error || typeof data !== "string") {
    console.error("[app] crear_codigo_app", error?.message);
    redirect(urlVuelta(s, { error: "servidor" }));
  }
  redirect(urlVuelta(s, { codigo: data }));
}

export async function cancelarApp(fd: FormData) {
  const s = desdeForm(fd);
  if (!s) redirect("/");
  redirect(urlVuelta(s, { error: "cancelado" }));
}

// Vuelve a «Mi cuenta» con ?equipo=desconectado o ?equipo=error para mostrar el resultado.
export async function desconectarEquipo(fd: FormData) {
  const id = String(fd.get("id") ?? "");
  if (!/^[0-9a-f-]{36}$/.test(id)) redirect("/cuenta?equipo=error");
  const supabase = await createClient();
  const { data, error } = await supabase.from("sesiones_app").update({ revocada: true }).eq("id", id).select("id");
  if (error) console.error("[app] desconectar equipo", error.message);
  redirect(`/cuenta?equipo=${!error && data?.length ? "desconectado" : "error"}`);
}
