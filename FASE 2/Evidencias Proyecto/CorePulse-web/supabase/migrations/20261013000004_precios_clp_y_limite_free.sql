-- CorePulse Web · Precios en pesos chilenos y plan Free limitado a 2 usos por función.
-- Se puede ejecutar varias veces.

update public.planes set moneda = 'CLP', precio_mensual = 0, precio_anual = 0,
  descripcion = 'Prueba todas las funciones: 2 usos de cada una.'
where slug = 'free';

update public.planes set moneda = 'CLP', precio_mensual = 4990, precio_anual = 39990,
  descripcion = 'Todas las funciones, sin límites de uso.'
where slug = 'pro';

-- En Free, cualquier función se puede usar 2 veces; en Pro, sin límite.
update public.plan_caracteristicas set free = '"2 usos"', pro = '"Ilimitado"';

update public.ajustes set valor = jsonb_set(valor, '{nota}', '"2 usos por función"'), actualizado = now()
where clave = 'precios';

update public.ajustes set valor = jsonb_set(valor, '{cierreTexto}', '"Prueba cada función gratis 2 veces. Pro cuando quieras usarlas sin límite."'), actualizado = now()
where clave = 'inicio';

update public.preguntas set respuesta = 'No caduca, pero en el plan Free cada función se puede usar 2 veces. Con Pro el uso es ilimitado.'
where seccion = 'precios' and pregunta = '¿La versión gratuita caduca?';

-- Hacer hueco en la posición 2 solo la primera vez.
update public.preguntas set orden = orden + 1
where seccion = 'precios' and orden >= 2
  and not exists (select 1 from public.preguntas where pregunta = '¿Qué cuenta como un uso?');

insert into public.preguntas (seccion, pregunta, respuesta, orden)
select 'precios', '¿Qué cuenta como un uso?', 'Cada vez que ejecutas una función (por ejemplo, una limpieza, aplicar un tweak o un diagnóstico) cuenta como un uso. Al llegar a 2 en una función, puedes pasar a Pro para seguir usándola.', 2
where not exists (select 1 from public.preguntas where pregunta = '¿Qué cuenta como un uso?');
