-- CorePulse · Base local para ejecutar las migraciones de Supabase en un PostgreSQL común.
--
-- En Supabase (nube o CLI) este script NO se usa: Supabase ya trae los roles, el esquema
-- auth (usuarios), el esquema storage (archivos) y el esquema extensions.
-- En un PostgreSQL normal (por ejemplo, el contenedor de docker-compose) esas piezas no
-- existen, así que aquí se crea una versión mínima con las mismas tablas y funciones que
-- usan las migraciones. Así los scripts de supabase/migraciones se ejecutan sin cambios.

-- Roles que usan las políticas de seguridad por fila (RLS).
do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'anon') then
    create role anon nologin;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'authenticated') then
    create role authenticated nologin;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'service_role') then
    create role service_role nologin bypassrls;
  end if;
end $$;

create schema if not exists extensions;
create schema if not exists auth;
create schema if not exists storage;

grant usage on schema public, extensions to anon, authenticated, service_role;

-- Usuarios (en Supabase los administra Supabase Auth).
create table if not exists auth.users (
  id uuid primary key default gen_random_uuid(),
  email text unique,
  raw_user_meta_data jsonb not null default '{}',
  created_at timestamptz not null default now()
);

-- Identificador del usuario que hace la consulta. En Supabase sale del token de sesión;
-- aquí se lee de la misma variable de configuración que usa Supabase.
create or replace function auth.uid() returns uuid
language sql stable
as $$
  select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid
$$;

grant usage on schema auth to anon, authenticated, service_role;
grant execute on function auth.uid() to anon, authenticated, service_role;

-- Almacenamiento de archivos (en Supabase lo administra Supabase Storage).
create table if not exists storage.buckets (
  id text primary key,
  name text not null,
  public boolean not null default false,
  created_at timestamptz not null default now()
);
