-- CorePulse Web · Novedades: se vacía la página y la tabla queda lista para recibir las versiones
-- publicadas en GitHub (Releases). Se puede ejecutar varias veces.
--
-- Cada Release de GitHub llega como una fila:
--   version   ← etiqueta (tag), p. ej. «v1.4.0»
--   titulo    ← nombre del Release
--   resumen   ← el texto del Release que no es una lista (una explicación corta)
--   cambios   ← cada línea «- …» del Release
--   enlace    ← página del Release (solo si el repositorio es público)
--   github_id ← id del Release: al editarlo en GitHub se actualiza la misma fila
-- Ver el README.md principal del repositorio (sección «Novedades desde GitHub»).

alter table public.versiones add column if not exists resumen text;
alter table public.versiones add column if not exists enlace text;
alter table public.versiones add column if not exists github_id bigint;
alter table public.versiones add column if not exists origen text not null default 'manual';

alter table public.versiones drop constraint if exists versiones_github_id_key;
alter table public.versiones add constraint versiones_github_id_key unique (github_id);

-- Vaciar las novedades antiguas (las escritas a mano). Las que vengan de GitHub se conservan.
delete from public.versiones where github_id is null;
