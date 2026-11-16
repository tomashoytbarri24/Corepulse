-- CorePulse Web · Inicio de sesión de la app de escritorio a través de la web.
--
-- Flujo (como GitHub Desktop o Spotify):
--   1. La app genera un «verificador» secreto y envía a la web solo su huella SHA-256 («reto»).
--   2. El usuario autoriza en la web → crear_codigo_app() devuelve un código de un solo uso (2 min).
--   3. La web redirige al navegador a http://127.0.0.1:<puerto>/callback de la app con ese código.
--   4. La app canjea código + verificador → canjear_codigo_app() crea una sesión de equipo.
--   5. La app usa ese token para perfil_app() y lo revoca con revocar_token_app().
-- En la base solo se guardan huellas SHA-256: ni códigos ni tokens en claro.

create extension if not exists pgcrypto with schema extensions;

create table if not exists public.codigos_app (
  hash text primary key,
  usuario uuid not null references auth.users (id) on delete cascade,
  reto text not null check (reto ~ '^[0-9a-f]{64}$'),
  vence timestamptz not null default now() + interval '2 minutes',
  usado boolean not null default false
);
alter table public.codigos_app enable row level security;
revoke all on public.codigos_app from anon, authenticated;

create table if not exists public.sesiones_app (
  id uuid primary key default gen_random_uuid(),
  usuario uuid not null references auth.users (id) on delete cascade,
  hash text not null unique,
  creada timestamptz not null default now(),
  ultimo_uso timestamptz not null default now(),
  revocada boolean not null default false
);
alter table public.sesiones_app enable row level security;

-- El usuario ve y desconecta sus propios equipos (sin acceso a la huella del token).
drop policy if exists "ver mis equipos" on public.sesiones_app;
create policy "ver mis equipos" on public.sesiones_app for select to authenticated using ((select auth.uid()) = usuario);
drop policy if exists "desconectar mis equipos" on public.sesiones_app;
create policy "desconectar mis equipos" on public.sesiones_app for update to authenticated
  using ((select auth.uid()) = usuario) with check ((select auth.uid()) = usuario);
revoke all on public.sesiones_app from anon, authenticated;
grant select (id, creada, ultimo_uso, revocada) on public.sesiones_app to authenticated;
grant update (revocada) on public.sesiones_app to authenticated;

-- 2 · Código de un solo uso para el usuario con sesión en la web.
create or replace function public.crear_codigo_app(reto text)
returns text
language plpgsql
security definer
set search_path = ''
as $$
declare
  uid uuid := auth.uid();
  codigo text;
begin
  if uid is null then
    raise exception 'Se necesita una sesión iniciada' using errcode = '28000';
  end if;
  if reto is null or reto !~ '^[0-9a-f]{64}$' then
    raise exception 'Reto no válido' using errcode = '22023';
  end if;
  delete from public.codigos_app where vence < now() or usado;
  codigo := encode(extensions.gen_random_bytes(32), 'hex');
  insert into public.codigos_app (hash, usuario, reto)
  values (encode(extensions.digest(codigo, 'sha256'), 'hex'), uid, reto);
  return codigo;
end;
$$;

-- 4 · Canje: el código se gasta aunque el verificador sea incorrecto (no admite reintentos).
create or replace function public.canjear_codigo_app(codigo text, verificador text)
returns text
language plpgsql
security definer
set search_path = ''
as $$
declare
  fila public.codigos_app;
  token text;
begin
  if codigo is null or verificador is null or length(codigo) > 128 or length(verificador) > 256 then
    return null;
  end if;
  update public.codigos_app set usado = true
  where hash = encode(extensions.digest(codigo, 'sha256'), 'hex') and not usado and vence > now()
  returning * into fila;
  if not found then
    return null;
  end if;
  if fila.reto <> encode(extensions.digest(verificador, 'sha256'), 'hex') then
    return null;
  end if;
  token := encode(extensions.gen_random_bytes(32), 'hex');
  insert into public.sesiones_app (usuario, hash) values (fila.usuario, encode(extensions.digest(token, 'sha256'), 'hex'));
  return token;
end;
$$;

-- 5 · Perfil para la app (email, nombre y plan) a partir de su token.
create or replace function public.perfil_app(token text)
returns table (email text, nombre text, plan text, plan_vence timestamptz)
language plpgsql
security definer
set search_path = ''
as $$
declare
  uid uuid;
begin
  if token is null or length(token) > 128 then
    return;
  end if;
  update public.sesiones_app set ultimo_uso = now()
  where hash = encode(extensions.digest(token, 'sha256'), 'hex') and not revocada
  returning usuario into uid;
  if uid is null then
    return;
  end if;
  return query
    select u.email::text, p.nombre, p.plan, p.plan_vence
    from auth.users u join public.perfiles p on p.id = u.id
    where u.id = uid;
end;
$$;

create or replace function public.revocar_token_app(token text)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
begin
  if token is null or length(token) > 128 then
    return false;
  end if;
  update public.sesiones_app set revocada = true
  where hash = encode(extensions.digest(token, 'sha256'), 'hex') and not revocada;
  return found;
end;
$$;

revoke execute on function public.crear_codigo_app(text) from public, anon;
grant execute on function public.crear_codigo_app(text) to authenticated;
revoke execute on function public.canjear_codigo_app(text, text), public.perfil_app(text), public.revocar_token_app(text) from public;
grant execute on function public.canjear_codigo_app(text, text), public.perfil_app(text), public.revocar_token_app(text) to anon, authenticated;
