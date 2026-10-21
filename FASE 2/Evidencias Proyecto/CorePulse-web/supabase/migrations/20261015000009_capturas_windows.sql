-- CorePulse Web · Capturas nuevas tomadas en Windows (con todas las métricas).
-- ANTES de ejecutar este SQL, sube las imágenes: npm run subir-capturas
-- (si no, la web apuntaría a archivos que aún no están en Storage).
-- Nombres nuevos con versión (20261015-0153): las imágenes llevan 7 días de caché y con el
-- mismo nombre los navegadores seguirían mostrando las antiguas. Se puede ejecutar varias veces.

-- Nombre de la captura sin versión ni extensión: «summary.jpg» y «summary-20261015-0153.webp» → «summary».
create or replace function pg_temp.captura(archivo text) returns text language sql immutable as $$
  select regexp_replace(archivo, '(-\d{8}(-\d{4})?)?(-social)?\.[a-z0-9]+$', '', 'i')
$$;

update public.funciones set imagen = pg_temp.captura(imagen) || '-20261015-0153.webp'
where pg_temp.captura(imagen) in ('summary', 'health', 'tweaks', 'cleanup', 'themes');

update public.temas set imagen = pg_temp.captura(imagen) || '-20261015-0153.webp'
where pg_temp.captura(imagen) in ('summary', 'tema_aurora', 'tema_violet', 'tema_ember', 'tema_sakura', 'tema_cyber');

update public.ajustes
set valor = jsonb_set(valor, '{imagen}', to_jsonb(pg_temp.captura(valor ->> 'imagen') || '-20261015-0153.webp')), actualizado = now()
where clave = 'inicio' and pg_temp.captura(valor ->> 'imagen') = 'summary';

-- Vista previa al compartir el enlace (WhatsApp, X, LinkedIn…): JPEG de 1200×630.
update public.ajustes
set valor = jsonb_set(valor, '{imagenSocial}', '"summary-20261015-0153-social.jpg"'), actualizado = now()
where clave = 'sitio' and pg_temp.captura(valor ->> 'imagenSocial') = 'summary';

-- Comprobación: todas las imágenes deberían terminar en -20261015-0153.webp (y la social en -social.jpg).
select 'funciones' as tabla, slug as fila, imagen from public.funciones
union all select 'temas', nombre, imagen from public.temas
union all select 'ajustes', clave, coalesce(valor ->> 'imagen', valor ->> 'imagenSocial') from public.ajustes where clave in ('inicio', 'sitio')
order by 1, 2;
