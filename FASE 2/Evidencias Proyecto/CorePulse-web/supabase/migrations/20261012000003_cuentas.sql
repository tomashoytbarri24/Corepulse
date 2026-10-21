-- CorePulse Web · Cuentas de usuario.
-- Cada usuario de Supabase Auth tiene un perfil con su nombre y su plan.
-- El plan SOLO lo cambia el servidor (pagos) o tú desde el panel: el usuario no puede tocarlo.

create table if not exists public.perfiles (
  id uuid primary key references auth.users (id) on delete cascade,
  nombre text not null default '' check (char_length(nombre) <= 80),
  plan text not null default 'free' check (plan in ('free', 'pro')),
  plan_vence timestamptz,
  creado timestamptz not null default now()
);

alter table public.perfiles enable row level security;

drop policy if exists "ver mi perfil" on public.perfiles;
create policy "ver mi perfil" on public.perfiles
  for select to authenticated
  using ((select auth.uid()) = id);

drop policy if exists "editar mi perfil" on public.perfiles;
create policy "editar mi perfil" on public.perfiles
  for update to authenticated
  using ((select auth.uid()) = id)
  with check ((select auth.uid()) = id);

-- Solo la columna «nombre» es editable por el propio usuario.
revoke all on public.perfiles from anon, authenticated;
grant select on public.perfiles to authenticated;
grant update (nombre) on public.perfiles to authenticated;

-- Crear el perfil automáticamente al registrarse.
create or replace function public.crear_perfil()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.perfiles (id, nombre)
  values (new.id, left(coalesce(new.raw_user_meta_data ->> 'nombre', ''), 80))
  on conflict (id) do nothing;
  return new;
end;
$$;

revoke execute on function public.crear_perfil() from public, anon, authenticated;

drop trigger if exists al_crear_usuario on auth.users;
create trigger al_crear_usuario
  after insert on auth.users
  for each row execute function public.crear_perfil();

-- Perfiles para usuarios que ya existieran antes de esta migración.
insert into public.perfiles (id, nombre)
select id, left(coalesce(raw_user_meta_data ->> 'nombre', ''), 80) from auth.users
on conflict (id) do nothing;
