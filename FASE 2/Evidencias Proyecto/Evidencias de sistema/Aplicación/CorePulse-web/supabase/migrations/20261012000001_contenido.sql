-- CorePulse Web · Estructura del contenido público.
-- Todo lo que muestra la web se edita aquí (Table Editor de Supabase).
-- Lectura pública; escritura solo desde el panel de Supabase o con la clave secreta.

-- Textos generales por página, en JSON (clave → objeto).
create table if not exists public.ajustes (
  clave text primary key,
  valor jsonb not null,
  actualizado timestamptz not null default now()
);

create table if not exists public.planes (
  slug text primary key,
  nombre text not null,
  descripcion text not null default '',
  precio_mensual numeric(10, 2) not null default 0,
  precio_anual numeric(10, 2) not null default 0,
  moneda text not null default 'US$',
  destacado boolean not null default false,
  etiqueta text,
  boton_texto text not null,
  boton_enlace text not null,
  orden int not null default 0,
  activo boolean not null default true
);

-- Comparativa Free/Pro. free/pro: true, false o un texto corto («Básica», «3»…).
create table if not exists public.plan_caracteristicas (
  id bigint generated always as identity primary key,
  caracteristica text not null,
  free jsonb not null default 'false',
  pro jsonb not null default 'true',
  orden int not null default 0
);

create table if not exists public.preguntas (
  id bigint generated always as identity primary key,
  seccion text not null default 'precios',
  pregunta text not null,
  respuesta text not null,
  orden int not null default 0
);

-- Módulos de la app (página Funciones y sección fija de la portada).
create table if not exists public.funciones (
  slug text primary key,
  etiqueta text not null,
  titulo text not null,
  titulo_portada text,
  texto_portada text,
  puntos text[] not null default '{}',
  imagen text not null,
  color text not null default '#4EDDC8',
  en_portada boolean not null default false,
  orden int not null default 0
);

-- Tarjetas «Pensado hasta el detalle» de la portada.
create table if not exists public.destacados (
  id bigint generated always as identity primary key,
  titulo text not null,
  texto text not null,
  icono text not null default 'bolt',
  ancho boolean not null default false,
  orden int not null default 0
);

create table if not exists public.cifras (
  id bigint generated always as identity primary key,
  valor int not null,
  sufijo text not null default '',
  etiqueta text not null,
  orden int not null default 0
);

create table if not exists public.temas (
  id bigint generated always as identity primary key,
  nombre text not null,
  imagen text not null,
  color text not null,
  orden int not null default 0
);

create table if not exists public.versiones (
  id bigint generated always as identity primary key,
  version text not null,
  titulo text not null,
  cambios text[] not null default '{}',
  publicado date not null default current_date
);

-- secciones: [{"titulo": "...", "texto": "..."}]
create table if not exists public.documentos_legales (
  slug text primary key,
  titulo text not null,
  actualizado text not null default '',
  secciones jsonb not null default '[]'
);

-- Seguridad: cualquiera puede leer; nadie puede escribir desde la web.
do $$
declare t text;
begin
  foreach t in array array['ajustes','planes','plan_caracteristicas','preguntas','funciones','destacados','cifras','temas','versiones','documentos_legales']
  loop
    execute format('alter table public.%I enable row level security', t);
    execute format('drop policy if exists "lectura publica" on public.%I', t);
    execute format('create policy "lectura publica" on public.%I for select to anon, authenticated using (true)', t);
    execute format('grant select on public.%I to anon, authenticated', t);
  end loop;
end $$;

-- Las capturas viven en Storage, en un bucket público de solo lectura.
insert into storage.buckets (id, name, public)
values ('capturas', 'capturas', true)
on conflict (id) do nothing;
