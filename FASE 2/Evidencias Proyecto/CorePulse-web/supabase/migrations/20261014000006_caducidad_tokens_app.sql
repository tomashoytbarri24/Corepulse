-- CorePulse Web · Caducidad de los tokens de la app de escritorio.
-- Un token deja de valer si pasan 30 días sin usarse o 180 días desde que se conectó el equipo.
-- Al caducar, /api/app/yo responde 401 y la app vuelve a pedir «Iniciar sesión».
-- Se puede ejecutar varias veces.

-- Cada sesión guarda cuándo caduca como muy tarde (180 días desde que se creó).
alter table public.sesiones_app
  add column if not exists caduca timestamptz;
update public.sesiones_app set caduca = creada + interval '180 days' where caduca is null;
alter table public.sesiones_app
  alter column caduca set default now() + interval '180 days',
  alter column caduca set not null;

-- El usuario ve en «Mi cuenta» hasta cuándo vale cada equipo.
grant select (caduca) on public.sesiones_app to authenticated;

-- Sesión válida: no revocada, usada en los últimos 30 días y sin pasar su fecha de caducidad.
create or replace function public.sesion_app_vigente(s public.sesiones_app)
returns boolean
language sql
stable
set search_path = ''
as $$
  select not s.revocada and s.ultimo_uso > now() - interval '30 days' and s.caduca > now();
$$;

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
  update public.sesiones_app s set ultimo_uso = now()
  where s.hash = encode(extensions.digest(token, 'sha256'), 'hex') and public.sesion_app_vigente(s)
  returning s.usuario into uid;
  if uid is null then
    return;
  end if;
  return query
    select u.email::text, p.nombre, p.plan, p.plan_vence
    from auth.users u join public.perfiles p on p.id = u.id
    where u.id = uid;
end;
$$;

-- Al conectar un equipo nuevo se borran las sesiones caducadas o revocadas hace tiempo.
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
  delete from public.sesiones_app s
  where not public.sesion_app_vigente(s) and greatest(s.ultimo_uso, s.creada) < now() - interval '30 days';
  token := encode(extensions.gen_random_bytes(32), 'hex');
  insert into public.sesiones_app (usuario, hash) values (fila.usuario, encode(extensions.digest(token, 'sha256'), 'hex'));
  return token;
end;
$$;

revoke execute on function public.sesion_app_vigente(public.sesiones_app) from public, anon, authenticated;
revoke execute on function public.canjear_codigo_app(text, text), public.perfil_app(text) from public;
grant execute on function public.canjear_codigo_app(text, text), public.perfil_app(text) to anon, authenticated;
