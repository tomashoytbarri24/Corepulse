-- CorePulse Web · Los admins pueden dar o quitar admin a otras cuentas por email desde /cuenta/admin.
-- Se puede ejecutar varias veces. Necesita …_administradores.sql.

-- Lista de admins (solo para admins). El email vive en auth.users, que la web no puede leer directamente.
create or replace function public.lista_admins()
returns table (id uuid, email text, nombre text)
language plpgsql
stable
security definer
set search_path = ''
as $$
begin
  if not public.soy_admin() then
    raise exception 'Solo los admins pueden ver esta lista' using errcode = '42501';
  end if;
  return query
    select p.id, u.email::text, p.nombre
    from public.perfiles p
    join auth.users u on u.id = p.id
    where p.es_admin
    order by u.email;
end;
$$;

-- Devuelve 'ok', 'ya_admin' o 'no_existe'.
create or replace function public.dar_admin(correo text)
returns text
language plpgsql
security definer
set search_path = ''
as $$
declare
  usuario uuid;
  ya boolean;
begin
  if not public.soy_admin() then
    raise exception 'Solo los admins pueden dar admin' using errcode = '42501';
  end if;
  select u.id into usuario from auth.users u where lower(u.email) = lower(trim(correo));
  if usuario is null then
    return 'no_existe';
  end if;
  select p.es_admin into ya from public.perfiles p where p.id = usuario;
  if ya then
    return 'ya_admin';
  end if;
  update public.perfiles set es_admin = true where id = usuario;
  return 'ok';
end;
$$;

-- Nadie puede quitarse admin a sí mismo: así siempre queda al menos un admin.
create or replace function public.quitar_admin(usuario uuid)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
begin
  if not public.soy_admin() then
    raise exception 'Solo los admins pueden quitar admin' using errcode = '42501';
  end if;
  if usuario = (select auth.uid()) then
    return false;
  end if;
  update public.perfiles set es_admin = false where id = usuario and es_admin;
  return found;
end;
$$;

revoke execute on function public.lista_admins() from public, anon;
revoke execute on function public.dar_admin(text) from public, anon;
revoke execute on function public.quitar_admin(uuid) from public, anon;
grant execute on function public.lista_admins() to authenticated;
grant execute on function public.dar_admin(text) to authenticated;
grant execute on function public.quitar_admin(uuid) to authenticated;
