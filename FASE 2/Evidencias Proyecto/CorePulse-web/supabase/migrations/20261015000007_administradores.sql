-- CorePulse Web · Administradores: pueden cambiar los precios de los planes desde /cuenta/admin.
-- Se puede ejecutar varias veces.
--
-- Para hacer admin a una cuenta (solo desde el SQL Editor de Supabase):
--   update public.perfiles set es_admin = true
--   where id = (select id from auth.users where email = 'tu@email.com');

alter table public.perfiles add column if not exists es_admin boolean not null default false;

-- El usuario sigue pudiendo editar solo su «nombre» (ver …_cuentas.sql): no puede hacerse admin a sí mismo.

create or replace function public.soy_admin()
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select coalesce((select es_admin from public.perfiles where id = (select auth.uid())), false);
$$;

revoke execute on function public.soy_admin() from public, anon;
grant execute on function public.soy_admin() to authenticated;

-- Los admins pueden cambiar SOLO los precios; el resto de columnas de «planes» sigue siendo de solo lectura.
drop policy if exists "admin edita precios" on public.planes;
create policy "admin edita precios" on public.planes
  for update to authenticated
  using ((select public.soy_admin()))
  with check ((select public.soy_admin()));

grant update (precio_mensual, precio_anual) on public.planes to authenticated;

alter table public.planes drop constraint if exists precios_no_negativos;
alter table public.planes add constraint precios_no_negativos check (precio_mensual >= 0 and precio_anual >= 0);
