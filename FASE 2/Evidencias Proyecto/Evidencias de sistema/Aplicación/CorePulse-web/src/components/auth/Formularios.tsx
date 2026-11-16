"use client";

import Link from "next/link";
import { useActionState } from "react";
import { actualizarNombre, cambiarContrasena, iniciarSesion, recuperar, registrarse, type Estado } from "@/lib/auth/acciones";
import { Campo, Enviar, Mensaje } from "./Campos";

const inicial: Estado = {};

export function FormLogin({ siguiente }: { siguiente: string }) {
  const [estado, accion] = useActionState(iniciarSesion, inicial);
  return (
    <form action={accion} className="space-y-4">
      <input type="hidden" name="siguiente" value={siguiente} />
      <Campo label="Email" name="email" type="email" autoComplete="email" defaultValue={estado.campos?.email} />
      <Campo label="Contraseña" name="password" type="password" autoComplete="current-password" />
      <div className="flex justify-end">
        <Link href="/recuperar" className="text-sm text-muted transition-colors hover:text-accent">
          ¿Olvidaste tu contraseña?
        </Link>
      </div>
      <Mensaje estado={estado} />
      <Enviar>Iniciar sesión</Enviar>
      <p className="pt-2 text-center text-sm text-muted">
        ¿No tienes cuenta?{" "}
        <Link href={siguiente === "/cuenta" ? "/registro" : `/registro?siguiente=${encodeURIComponent(siguiente)}`} className="text-accent hover:underline">
          Crear cuenta
        </Link>
      </p>
    </form>
  );
}

export function FormRegistro({ siguiente }: { siguiente: string }) {
  const [estado, accion] = useActionState(registrarse, inicial);
  if (estado.ok) return <Mensaje estado={estado} />;
  return (
    <form action={accion} className="space-y-4">
      <input type="hidden" name="siguiente" value={siguiente} />
      <Campo label="Nombre" name="nombre" autoComplete="name" maxLength={80} defaultValue={estado.campos?.nombre} />
      <Campo label="Email" name="email" type="email" autoComplete="email" defaultValue={estado.campos?.email} />
      <Campo label="Contraseña (mínimo 8 caracteres)" name="password" type="password" autoComplete="new-password" minLength={8} />
      <label className="flex items-start gap-3 text-sm text-muted">
        <input type="checkbox" name="acepto" required className="mt-0.5 h-4 w-4 accent-[#4EDDC8]" />
        <span>
          Acepto los{" "}
          <Link href="/legal/terminos" className="text-accent hover:underline">
            términos de uso
          </Link>{" "}
          y la{" "}
          <Link href="/legal/privacidad" className="text-accent hover:underline">
            política de privacidad
          </Link>
          .
        </span>
      </label>
      <Mensaje estado={estado} />
      <Enviar>Crear cuenta</Enviar>
      <p className="pt-2 text-center text-sm text-muted">
        ¿Ya tienes cuenta?{" "}
        <Link href={siguiente === "/cuenta" ? "/login" : `/login?siguiente=${encodeURIComponent(siguiente)}`} className="text-accent hover:underline">
          Iniciar sesión
        </Link>
      </p>
    </form>
  );
}

export function FormRecuperar() {
  const [estado, accion] = useActionState(recuperar, inicial);
  if (estado.ok) return <Mensaje estado={estado} />;
  return (
    <form action={accion} className="space-y-4">
      <Campo label="Email" name="email" type="email" autoComplete="email" defaultValue={estado.campos?.email} />
      <Mensaje estado={estado} />
      <Enviar>Enviar enlace</Enviar>
      <p className="pt-2 text-center text-sm text-muted">
        <Link href="/login" className="text-accent hover:underline">
          Volver a iniciar sesión
        </Link>
      </p>
    </form>
  );
}

export function FormContrasena() {
  const [estado, accion] = useActionState(cambiarContrasena, inicial);
  return (
    <form action={accion} className="space-y-4">
      <Campo label="Nueva contraseña" name="password" type="password" autoComplete="new-password" minLength={8} />
      <Campo label="Repite la contraseña" name="repetir" type="password" autoComplete="new-password" minLength={8} />
      <Mensaje estado={estado} />
      <Enviar>Guardar contraseña</Enviar>
    </form>
  );
}

export function FormNombre({ nombre }: { nombre: string }) {
  const [estado, accion] = useActionState(actualizarNombre, inicial);
  return (
    <form action={accion} className="space-y-3">
      <Campo label="Nombre" name="nombre" autoComplete="name" maxLength={80} defaultValue={nombre} />
      <Mensaje estado={estado} />
      <Enviar>Guardar nombre</Enviar>
    </form>
  );
}
