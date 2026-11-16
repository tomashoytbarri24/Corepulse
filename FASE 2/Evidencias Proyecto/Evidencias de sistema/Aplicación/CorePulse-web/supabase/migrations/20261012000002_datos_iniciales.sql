-- CorePulse Web · Contenido inicial (el que tenía la web escrito en el código).
-- Se puede ejecutar varias veces: no pisa lo que ya hayas editado.
-- PRECIOS PROVISIONALES: ajústalos en la tabla «planes» antes de lanzar.

insert into public.ajustes (clave, valor) values
('sitio', '{
  "nombre": "CorePulse",
  "lema": "Tu PC, en su mejor forma.",
  "descripcion": "CorePulse monitorea, diagnostica y optimiza Windows 10 y 11 con datos reales: salud del sistema, 78 tweaks reversibles, limpieza y modo juego.",
  "descripcionCorta": "Monitoreo, diagnóstico y optimización para Windows 10 y 11. Datos reales o N/A, nunca inventados.",
  "version": "Rebuild 059",
  "compatibilidad": "Windows 10 y 11",
  "enlaceDescarga": "",
  "emailSoporte": "",
  "imagenSocial": "summary.jpg",
  "avisoLegal": "Windows es una marca de Microsoft Corporation. CorePulse no está afiliado a Microsoft."
}'),
('inicio', '{
  "titulo1": "Tu PC,",
  "titulo2": "en su mejor forma.",
  "subtitulo": "Monitorea, diagnostica y optimiza Windows con datos reales. Sin cifras inventadas, sin magia: cada cambio se explica y se puede revertir.",
  "imagen": "summary.jpg",
  "imagenAlt": "Panel Resumen de CorePulse con rendimiento en tiempo real y estado del sistema",
  "marquesina": ["Steam", "Epic Games", "Riot Games", "EA app", "Microsoft Store", "Xbox", "Windows 11", "Windows 10"],
  "manifiesto": "La mayoría de los optimizadores prometen magia. CorePulse te muestra lo que realmente pasa en tu PC, te explica cada cambio antes de hacerlo y te deja deshacerlo cuando quieras.",
  "destacadosTitulo": "Pensado hasta el detalle.",
  "destacadosSubtitulo": "Sin ruido.",
  "temasEtiqueta": "Personalización",
  "temasTitulo": "Diez temas.",
  "temasSubtitulo": "Uno para cada setup.",
  "cierreTitulo1": "Dale a tu PC",
  "cierreTitulo2": "el pulso que merece.",
  "cierreTexto": "Gratis para siempre en su versión básica. Pro cuando quieras desbloquearlo todo."
}'),
('funciones', '{
  "etiqueta": "Funciones",
  "titulo": "Todo lo que tu PC necesita, en un solo lugar.",
  "texto": "Cada módulo trabaja con datos reales de Windows y te explica lo que hace antes de hacerlo."
}'),
('precios', '{
  "etiqueta": "Precios",
  "titulo": "Empieza gratis. Pasa a Pro cuando quieras.",
  "texto": "Sin trucos ni periodos de prueba que se cobran solos.",
  "nota": "Para siempre"
}'),
('descargar', '{
  "etiqueta": "Descargar",
  "titulo": "CorePulse para Windows.",
  "texto": "Gratis, con Pro opcional.",
  "avisoSinDescarga": "Estamos preparando un instalador firmado para que Windows lo reconozca como seguro.",
  "requisitos": [
    {"nombre": "Sistema", "valor": "Windows 10 u 11 de 64 bits"},
    {"nombre": "Procesador", "valor": "x64 (Intel o AMD)"},
    {"nombre": "Memoria", "valor": "4 GB de RAM o más"},
    {"nombre": "Espacio", "valor": "Unos 400 MB para la app y sus componentes"},
    {"nombre": "Internet", "valor": "Solo para la primera instalación y las portadas de juegos"}
  ],
  "pasos": [
    "Descarga el instalador y ábrelo.",
    "La primera vez, CorePulse prepara sus componentes en tu perfil de Windows (necesita Internet unos minutos).",
    "Listo: CorePulse queda en el menú Inicio y en la bandeja del sistema."
  ]
}'),
('novedades', '{
  "etiqueta": "Novedades",
  "titulo": "Siempre mejorando.",
  "texto": "Cada versión de CorePulse, explicada en simple."
}')
on conflict (clave) do nothing;

insert into public.planes (slug, nombre, descripcion, precio_mensual, precio_anual, moneda, destacado, etiqueta, boton_texto, boton_enlace, orden) values
('free', 'Free', 'Lo esencial para conocer y cuidar tu PC.', 0, 0, 'US$', false, null, 'Descargar gratis', '/descargar', 1),
('pro', 'Pro', 'Todas las funciones, sin límites.', 4.99, 39.99, 'US$', true, 'Recomendado', 'Obtener Pro', '/registro', 2)
on conflict (slug) do nothing;

insert into public.plan_caracteristicas (caracteristica, free, pro, orden)
select * from (values
  ('Monitoreo en tiempo real de CPU, GPU, RAM y disco', 'true'::jsonb, 'true'::jsonb, 1),
  ('Centro de Salud: diagnóstico y lectura', 'true', 'true', 2),
  ('Recuperación y reparación de Windows', 'true', 'true', 3),
  ('Limpieza de sistema', '"Básica"', '"Completa + RAM profunda"', 4),
  ('Tweaks de Windows 11', '"Selección básica"', '"Los 78, reversibles"', 5),
  ('Temas', '"3"', '"10"', 6),
  ('Rendimiento: energía, juego activo y portadas', 'false', 'true', 7),
  ('Historial, tendencias y reportes', 'false', 'true', 8),
  ('CorePulse AI y Red avanzada (próximamente)', 'false', 'true', 9)
) as v(caracteristica, free, pro, orden)
where not exists (select 1 from public.plan_caracteristicas);

insert into public.preguntas (seccion, pregunta, respuesta, orden)
select * from (values
  ('precios', '¿La versión gratuita caduca?', 'No. CorePulse Free es gratis para siempre e incluye el monitoreo, el Centro de Salud y la reparación de Windows.', 1),
  ('precios', '¿Puedo cancelar Pro cuando quiera?', 'Sí. Si cancelas, conservas Pro hasta el final del periodo pagado y después vuelves a Free sin perder tus ajustes.', 2),
  ('precios', '¿En cuántos equipos puedo usar Pro?', 'La licencia está pensada para uso personal en tus propios equipos. Los detalles finales se publicarán con el lanzamiento de Pro.', 3),
  ('precios', '¿Qué pasa con los tweaks si dejo de pagar?', 'Nada se rompe: los cambios ya aplicados se quedan y siempre puedes restaurarlos.', 4)
) as v(seccion, pregunta, respuesta, orden)
where not exists (select 1 from public.preguntas);

insert into public.funciones (slug, etiqueta, titulo, titulo_portada, texto_portada, puntos, imagen, color, en_portada, orden) values
('monitoreo', 'Monitoreo', 'Rendimiento en tiempo real.', 'Todo tu equipo, en una mirada.',
 'CPU, GPU, RAM y disco en tiempo real. Si un sensor no está disponible, CorePulse lo dice: N/A, nunca un número inventado.',
 array['Gráfica en vivo de CPU y GPU', 'Uso de RAM y almacenamiento', 'Tiempo de sesión del sistema', 'Sensores sin confirmar se muestran como N/A'],
 'summary.jpg', '#4EDDC8', true, 1),
('salud', 'Centro de Salud', 'Un chequeo completo de Windows.', 'Diagnóstico que se entiende.',
 'Batería, almacenamiento, Windows, reparación DISM/SFC, puntos de restauración e historial de cambios. Cada estado viene con su evidencia.',
 array['Batería: capacidad, desgaste, ciclos y autonomía', 'Almacenamiento y estado de discos', 'Inicio, servicios, eventos y controladores', 'Reparación DISM/SFC y puntos de restauración'],
 'health.jpg', '#17B9F7', true, 2),
('tweaks', 'Tweaks', '78 ajustes que puedes deshacer.', '78 ajustes. Todos reversibles.',
 'Optimiza el Explorador, la privacidad y el rendimiento de Windows 11 con un clic, y vuelve atrás con otro. CorePulse verifica el registro antes y después.',
 array['Explorador, privacidad, rendimiento y apariencia', 'Verificación del registro al aplicar y restaurar', 'Avisos cuando un cambio requiere reiniciar el Explorador', 'Solo se ofrecen los compatibles con tu equipo'],
 'tweaks.jpg', '#B756EA', true, 3),
('limpieza', 'Limpieza', 'Libera espacio sin miedo.', 'Espacio y memoria, bajo tu control.',
 'Temporales, caché de Windows, Papelera y RAM. Primero analizas, después decides. Nada se borra sin tu confirmación.',
 array['Archivos temporales y caché de Windows', 'Papelera de reciclaje con confirmación', 'Limpieza de RAM standby o completa', 'Siempre analizas antes de borrar'],
 'cleanup.jpg', '#FFC269', true, 4),
('temas', 'Personalización', 'Diez temas, una identidad.', null, null,
 array['Aurora, Violet Neon, Ember, Glacier, Sakura y más', 'Se aplican al instante', 'Tu elección se recuerda', 'Bandeja del sistema para tenerlo siempre a mano'],
 'themes.jpg', '#CE7DFF', false, 5)
on conflict (slug) do nothing;

insert into public.destacados (titulo, texto, icono, ancho, orden)
select * from (values
  ('Modo juego inteligente', 'Detecta el juego activo de Steam, Epic, Riot, EA y Xbox, con su portada oficial y el tiempo de sesión.', 'gamepad', true, 1),
  ('Alertas térmicas', 'Avisos cuando la temperatura o la RAM se salen de lo normal.', 'thermo', false, 2),
  ('Reparación de Windows', 'DISM y SFC guiados, con confirmación y registro de cada paso.', 'wrench', false, 3),
  ('Planes de energía', 'Cambia el plan de energía y vuelve al original con un clic.', 'bolt', false, 4),
  ('Privacidad por diseño', 'Sin telemetría oculta. Lo único que sale de tu PC es el nombre público de un juego para buscar su portada.', 'lock', true, 5)
) as v(titulo, texto, icono, ancho, orden)
where not exists (select 1 from public.destacados);

insert into public.cifras (valor, sufijo, etiqueta, orden)
select * from (values
  (78, '', 'tweaks reversibles para Windows 11', 1),
  (10, '', 'temas para personalizar la app', 2),
  (5, '', 'tiendas de juegos reconocidas', 3),
  (0, '', 'datos inventados. Real o N/A.', 4)
) as v(valor, sufijo, etiqueta, orden)
where not exists (select 1 from public.cifras);

insert into public.temas (nombre, imagen, color, orden)
select * from (values
  ('CorePulse', 'summary.jpg', '#4EDDC8', 1),
  ('Aurora', 'tema_aurora.jpg', '#53EBC4', 2),
  ('Violet Neon', 'tema_violet.jpg', '#CE7DFF', 3),
  ('Ember Tech', 'tema_ember.jpg', '#FFC269', 4),
  ('Sakura', 'tema_sakura.jpg', '#FFA0C9', 5),
  ('Cyber Matrix', 'tema_cyber.jpg', '#64F3A4', 6)
) as v(nombre, imagen, color, orden)
where not exists (select 1 from public.temas);

-- Novedades: ya no hay datos iniciales; llegan desde GitHub (ver …_novedades_github.sql y el README.md principal del repositorio (sección «Novedades desde GitHub»)).

insert into public.documentos_legales (slug, titulo, actualizado, secciones) values
('terminos', 'Términos de uso', 'Borrador · octubre de 2026', '[
  {"titulo": "Uso del software", "texto": "CorePulse se ofrece para uso personal en equipos con Windows 10 u 11. Puedes instalarlo en los equipos que te pertenecen o que administras."},
  {"titulo": "Cambios en el sistema", "texto": "Las funciones que modifican Windows (tweaks, limpieza, planes de energía, reparación) solo se ejecutan con tu confirmación. Te recomendamos crear un punto de restauración antes de cambios importantes."},
  {"titulo": "Plan Pro", "texto": "El plan Pro se renueva automáticamente según el periodo elegido hasta que lo canceles. Al cancelar, mantienes Pro hasta el final del periodo pagado."},
  {"titulo": "Limitación de responsabilidad", "texto": "CorePulse se proporciona «tal cual». Hacemos todo lo posible para que cada cambio sea reversible, pero no podemos garantizar el resultado en todas las configuraciones de hardware y software."}
]'),
('privacidad', 'Política de privacidad', 'Borrador · octubre de 2026', '[
  {"titulo": "Qué datos usa la app", "texto": "CorePulse lee información de tu equipo (uso de CPU, RAM, discos, batería, juegos en ejecución) para mostrártela. Esa información se procesa en tu PC y no se envía a nuestros servidores."},
  {"titulo": "Portadas de juegos", "texto": "Para mostrar la portada de un juego, CorePulse puede enviar solo el nombre público del juego o su identificador de Steam a la tienda correspondiente. Nunca se envían rutas, procesos ni datos de hardware."},
  {"titulo": "Cuenta", "texto": "Si creas una cuenta, guardamos tu email, tu nombre y tu plan para gestionar el acceso a Pro. Puedes pedir que eliminemos tu cuenta en cualquier momento."},
  {"titulo": "Analítica de la web", "texto": "Esta web usa analítica sin cookies que no identifica a personas concretas. La sesión de tu cuenta usa cookies estrictamente necesarias."}
]'),
('reembolsos', 'Política de reembolsos', 'Borrador · octubre de 2026', '[
  {"titulo": "Garantía", "texto": "Si Pro no es lo que esperabas, puedes pedir el reembolso dentro de los 14 días posteriores a tu primera compra."},
  {"titulo": "Cómo solicitarlo", "texto": "Escríbenos desde el email de tu cuenta indicando la fecha de compra. Procesamos los reembolsos con el mismo medio de pago."},
  {"titulo": "Renovaciones", "texto": "Las renovaciones pueden reembolsarse si se solicitan dentro de los 7 días siguientes al cobro y no se usó Pro en ese periodo."}
]')
on conflict (slug) do nothing;
