## REBUILD 146 — Identidad AMD y tipo de almacenamiento (19-10-2026)

- Base: REBUILD 145 completa; se conserva el TXT original de reglas y todos los módulos existentes.
- ui/Glyph.qml: el icono AMD muestra el logotipo completo (letras de marca y flecha). El SSD conserva el contorno M.2 para NVMe; se añaden siluetas separadas para disco mecánico y SSD SATA, además de un icono neutro cuando Windows no comunica el tipo.
- ui/Overview.qml y ui/HealthPage.qml: el icono y la etiqueta de almacenamiento se derivan de los datos MediaType y BusType publicados por Windows. Se reconocen también los valores numéricos de bus SATA (11) y NVMe (17); si falta evidencia se usa el icono genérico.
- ui/Overview.qml y ui/HealthPage.qml: el almacenamiento vuelve a violeta fijo (#A66BD6). RAM, CPU/GPU, sensores, informes y demás colores quedan sin cambios.
- Sin nuevas dependencias ni módulos Python. Main.qml y Glyph.qml compilan con el runtime de PySide6 y se crean las cinco formas (AMD, HDD, SATA, NVMe y genérica). No se ejecutaron pruebas automáticas ni se abrió la ventana; la revisión visual en Windows queda pendiente.

---

## REBUILD 145 — Logotipos de hardware revisados (19-10-2026)

- **Base:** REBUILD 144 completa. Se conservan sus mejoras de navegación, reportes independientes, Liquid Glass y funciones existentes.
- ui/Glyph.qml: AMD usa su símbolo de flecha de marca; RAM muestra un módulo DIMM con cuatro chips y contactos; SSD muestra una placa M.2 con chips y muesca de conexión.
- Se conservan los colores fijos de RAM y SSD y las reglas de color de CPU/GPU. Sin cambios de sensores, diagnósticos, benchmark, controladores ni informes.
- No se agregan dependencias ni archivos. **QML:** Main.qml y Glyph.qml cargan sin errores con el runtime PySide6. No se ejecutaron pruebas automáticas ni se mostró la ventana; revisión visual pendiente.

---
## REBUILD 144 — Navegación, hardware e informes independientes (19-10-2026)

- **Base:** REBUILD 143 completo. Se respetan íntegramente las reglas de versiones y se conserva `Reglas para crear Versiones nuevas.txt` sin cambios.
- `ui/Overview.qml`: Salud del sistema y Alertas ahora son tarjetas navegables hacia sus módulos correspondientes. RAM conserva el indicador rojo cuando está crítica; sus colores normales pasan a cian. Almacenamiento cambia a ámbar.
- `ui/Glyph.qml`, `ui/MetricLine.qml`, `ui/ComponentDetail.qml`: distintivo AMD más legible, iconos de memoria DIMM y SSD renovados, con colores consistentes en Resumen y ficha de RAM. Los colores identificativos de CPU/GPU y los estados existentes se conservan.
- `ui/BenchmarkPage.qml` y `ui/Main.qml`: acceso directo a la carpeta común de reportes desde ambas pantallas.
- `core/health/report.py`: el diagnóstico completado genera su propio PDF `CorePulse_Diagnostico_*.pdf`, usa solo la instantánea diagnóstica y no incluye puntuaciones ni resultados de benchmark. Se puede regenerar y abrir de forma independiente.
- `ui/Main.qml`: el botón Abrir PDF de Diagnóstico abre únicamente su reporte dedicado, nunca el último informe general o de benchmark. Cabecera actualizada a REBUILD 144.
- No se agregan dependencias ni módulos Python. **No se ejecutaron pruebas automáticas ni se verificó visualmente la aplicación**; esa comprobación requiere abrirla en Windows.

---

## REBUILD 143 — Diagnóstico integrado al Liquid Glass global (19-10-2026)

- **Base:** ZIP íntegro REBUILD 142, sin eliminar ningún módulo. Se revisaron previamente `Reglas para crear Versiones nuevas.txt` y este historial, preservando literalmente el TXT de reglas.
- **Problema observado en el video de la V142:** al terminar «Iniciar diagnóstico», el bloque principal aún tiene un borde amarillo sólido y los indicadores individuales parecen tarjetas gris plomo apiladas; estas superficies residían en `ui/Main.qml` y quedaron fuera de la conversión global de V142.
- `ui/Main.qml`: se sustituyeron únicamente los tres contenedores informativos de diagnóstico por `GlassPanel`: resumen del resultado, filas de indicadores y bloque de análisis CorePulse AI. Se atenúa el contorno de estado y se retienen los colores de prioridad y advertencia en textos y bordes sutiles; los botones Crear PDF, Repetir diagnóstico, enlaces YouTube y acciones IA no cambian.
- `ui/GlassPanel.qml`: incorpora la propiedad opcional `nested` (falso por defecto). En las filas anidadas de Diagnóstico aplica solo 1,5 % de material sobre el vidrio exterior, con borde tenue, evitando el efecto de apilamiento que producía placas grises. Las demás tarjetas de todas las pestañas conservan exactamente el material global V142.
- `ui/Main.qml`: cabecera y título actualizados a REBUILD 143.
- **Sin modificaciones** de motores Python, diagnóstico real y sus umbrales, telemetría, cobertura REAL_OR_NA, CorePulse AI/Worker, Windows, limpieza RAM, Benchmark, RTSS, diseño de Resumen, menús ni modales sólidos.
- **Verificación:** 316 pruebas Python aprobadas, exactamente los mismos 40 fallos históricos de V142 y 0 regresiones nuevas; 61/61 pruebas del Worker cloud aprobadas; sintaxis Python verificada; proyecto completo de 74 archivos y reglas originales idénticas. Vista final en Windows/PySide6 pendiente; no se requiere deploy cloud.

## REBUILD 142 — Liquid Glass unificado en todas las pestañas (18-10-2026)

- **Base:** REBUILD 141 completa. Se revisaron las reglas obligatorias y el historial. Se conserva intacto el comportamiento de sensores, diagnóstico, benchmark, red, IA, Tweaks, RTSS y de Windows.
- **Problema confirmado en video:** Resumen tenía vidrio adaptativo, pero las tarjetas de Red avanzada y otros módulos continuaban con superficies opacas/grisáceas. Cambiar solo `ThemeManager.palette` no era suficiente por las superficies locales declaradas como `Rectangle`.
- **Solución:** nuevo `ui/GlassPanel.qml` con el mismo degradado tenuemente translúcido de Resumen (7 % / 6,5 % / 7 % sobre `bgStart/bgMid/bgEnd`, borde a 7,5 %), sin líneas artificiales de reflejo de 1 px. `Overview.qml` y `StatTile.qml` ahora usan también esta definición común, en lugar de duplicar materiales.
- **Cobertura:** más de 100 tarjetas principales y secundarias de `HealthPage`, `CleanupPage`, `NetworkPage`, `BenchmarkPage`, `OverlayPage`, `AIPage`, `TweaksPage`, `ThemesPage`, `ComponentDetail`, `DriversPage`, `InsightsPage`, `ReportsPage`, `StartupPage` y `Main` convertidas al componente único. Incluye tarjetas de métricas, resultados, controles de salud, listados y secciones expandibles.
- **Excepciones conscientes:** se mantienen intactos fondos de botones, barras de progreso, iconos, indicadores, componentes de vista previa, modales de confirmación y las ventanas que necesitan superficies opacas por legibilidad. El diseño de Resumen se conserva visualmente.
- `main.py`: `panelBorder` global pasa del antiguo blanco de 9,4 % a un blanco de 7,5 % (`#13FFFFFF`) para igualar el contorno de `GlassPanel` en pantallas que todavía consumen `page.edge`; se conserva `panelOpaque` para diálogos y no se alteran los colores de acción.
- **Cabecera:** REBUILD 142. Se actualizan los contratos de diseño a esta nueva arquitectura de tarjetas; el resto del conjunto de pruebas puede contener contratos históricos obsoletos que no corresponden a versiones actuales.
- **Prueba pendiente:** inspección visual bajo Windows/PySide6 en el equipo del usuario y revisión de distintas paletas en las pantallas.

## REBUILD 141 — Liquid Glass global sin líneas grises (19-10-2026)

- **Base:** carpeta íntegra REBUILD 140. Se conservaron archivos, módulos y reglas del proyecto.
- **Motivo:** el usuario confirmó mejora general, pero detectó líneas grises extrañas en bordes y pidió que el nuevo material de tarjetas se aplicara de forma global, no solo en partes puntuales.
- `main.py`: el sistema de superficies se centraliza más en la paleta del tema. `panel='#0AFFFFFF'`, `panelHover='#14FFFFFF'`, `panelRaised='#12FFFFFF'` y `panelBorder='#18FFFFFF'` dejan atrás el borde gris derivado del tema, manteniendo legibilidad y una integración más uniforme con el fondo. `panelOpaque` queda intacto para menús y capas que siguen necesitando mayor solidez.
- `ui/Overview.qml`: el componente local `GlassCard` elimina las tiras de reflejo de 1 px (superior, lateral y borde inferior de acento) que en Windows podían percibirse como líneas grises raras. Se conserva el mismo degradado translúcido sobre el fondo global.
- `ui/StatTile.qml`: las cuatro tarjetas inferiores adoptan la misma limpieza de borde; solo queda el contorno suave y el realce por hover/acento.
- `ui/Main.qml`: indicador visual actualizado a **Rebuild 141**.
- **Resultado esperado:** el cambio visual de tarjetas se propaga a muchas más pantallas que consumen la paleta global (`panel`, `panelRaised`, `panelBorder`) sin alterar sensores, IA, benchmark, limpieza ni navegación.

## REBUILD 140 — Liquid Glass adaptativo sin placas grises (19-10-2026)

- **Base:** ZIP íntegro REBUILD 139 LIQUID GLASS SUAVE. Se consultaron `Reglas para crear Versiones nuevas.txt` y este historial antes de hacer cambios; no se eliminó ni duplicó código funcional.
- **Causa y corrección:** los degradados blancos con 9,5–10 % de opacidad y la franja superior de 28–34 % de altura aclaraban el panel como un bloque gris y creaban un corte horizontal. Se eliminan las franjas; el relleno conserva el degradado de la ventana usando solo un velo del 6,5–7 % basado en los colores de fondo del tema. Reflejos de apenas 1 px sobre bordes superiores/laterales e inferiores, sin nuevas placas opacas.
- `ui/Overview.qml`: una definición local `GlassCard` comparte el acabado de los dos paneles superiores, con iconos de encabezado y contador sin el gris sólido `panelRaised`. Gráfico y contenidos intactos.
- `ui/StatTile.qml`: las cuatro tarjetas inferiores usan el mismo degradado tenue y reflejos de borde; se mantiene el hover de Alertas/Lecturas, señales, textos y controles de reinicio.
- `main.py`: el velo de las tarjetas generales baja a 3,1 % blanco (`panel=#08FFFFFF`) y hover a 7,1 % (`#12FFFFFF`); **panelOpaque**, **panelRaised** y botones permanecen sólidos.
- `ui/Main.qml`: título REBUILD 140. No se introducen dependencias, nuevas páginas ni nuevos archivos Python; no cambia sidebar, fondo único, ventanas, módulos ni fuentes de datos REAL_OR_NA.
- **Verificación:** comparación de árbol con V139, sintaxis Python y pruebas de regresión estáticas. Renderizado Qt/Windows visual pendiente de validación en el equipo del usuario. **Reversión:** conservar ZIP V139.

## REBUILD 139 — Liquid glass suave e integrado (19-10-2026)

- **Base:** REBUILD 138 íntegra. Se conserva toda la lógica funcional, reglas REAL_OR_NA, IA cloud, detección de juegos, energía, sensores y estructura del proyecto.
- `ui/Overview.qml`: las dos tarjetas grandes del Resumen pasan de una superficie plana a una capa translúcida con degradado blanco suave y brillo superior ligero, para que el fondo del tema se vea a través de la tarjeta sin que esta se vuelva gris o ploma.
- `ui/StatTile.qml`: las cuatro tarjetas inferiores adoptan el mismo lenguaje visual “liquid glass”, con hover apenas más luminoso y bordes discretos.
- `ui/Main.qml`: indicador visual actualizado a Rebuild 139.
- **Sin cambios en:** lógica de sensores, worker cloud, CorePulse AI, diagnósticos, benchmark, fullscreen, sidebar estructural, títulos de módulos, ni controles críticos.

## REBUILD 139 — Tarjetas de cristal neutro y gráfico sin franja artificial (18-10-2026)

- **Base:** ZIP REBUILD 137 íntegro. Reglas obligatorias e historial leídos antes de cambiar archivos. La captura Windows mostró tinte violeta extraño en superficies y un rectángulo claro en el borde izquierdo del gráfico.
- `main.py`: se elimina `_gradient_lift_surface` obsoleta; `panel='#10FFFFFF'` y `panelHover='#1CFFFFFF'` usan blanco neutro con solo 6,3 %/11 % de opacidad para conservar y aclarar mínimamente **el degradado real situado detrás de cada tarjeta**, independientemente de paleta o posición. No se agrega un color de relleno de `bgMid`, `accent` ni negro. Diálogos, botones y superficies elevadas se mantienen sólidos.
- `ui/HistoryChart.qml`: se elimina exclusivamente el relleno Canvas `fade` que generaba una franja de 28 px desde el cambio a superficies translúcidas. El recorte del área y las líneas originales se preservan. Un texto discreto informa la cantidad de muestras realmente existentes mientras se acumulan las primeras 30, sin interpolar períodos que todavía no se midieron.
- `ui/Main.qml`: etiqueta de versión 138. `tests/test_rebuild.py`: reemplazar pruebas visuales obsoletas de V137 por pruebas de las superficies neutras y del trazado sin franja; actualizar el indicador histórico para tests aplicables.
- **Sin cambios:** geometría, sidebar/divisor, GPU/CPU monitor, historial, energía, juegos, IA, Worker, cuotas, permisos, cuentas, otras páginas, requisitos. `Reglas para crear Versiones nuevas.txt` byte-identical.
- **Validación:** 316 pruebas Python PASS / 37 fallos heredados exactamente iguales a V137 (315 PASS), sin regresiones nuevas. Worker Cloud 61/61 PASS. Verificación visual PySide6/Windows pendiente. **Reversión:** ZIP completo V137. No necesita deploy Cloudflare.

## REBUILD 137 — Tarjetas luminosas adaptadas al fondo real (18-10-2026)

- **Base:** V136 íntegra. Se leyeron las reglas originales y este historial antes de modificar el proyecto. La captura Windows de V136 mostró que `#30000000` (capa negra) apagaba en exceso el gradiente bajo las tarjetas. Rechazamos también repetir el velo saturado al 63 % de V135.
- `main.py`: `_gradient_lift_surface(bgMid)` calcula un reflejo de baja opacidad con los canales aclarados **del fondo del tema**, no de un acento ni de un gris fijo; alfa 0x28 = 15,7 % para tarjetas y 0x34 = 20,4 % en hover. El degradado de la ventana sigue aportando al menos 84 %/79 % del resultado, dependiendo del estado. Las 15 paletas incluyen la base CorePulse.
- `ui/StatTile.qml`: hover de tarjetas conserva el tinte suave del **fondo** (`panelHover`) sin pasar a superficie sólida; `ui/Main.qml` únicamente incrementa el indicador a REBUILD 137.
- **Sin cambios en:** barra lateral/divisor, geometría y disposición, telemetría REAL_OR_NA, estado de cuenta, CorePulse AI, portadas/energía automática, motores y Worker Cloudflare. `panelOpaque`, paneles elevados, controles, ventanas modales y bordes permanecen sin cambios. Ningún módulo Python nuevo ni dependencias.
- **Validación:** 315 pruebas Python PASS y los mismos 37 fallos históricos de V136 (comparación por nombre, ninguna regresión nueva); Worker Cloud 61/61 PASS; prueba visual real Windows/PySide6 pendiente. **Reversión:** ZIP REBUILD 136; no requiere despliegue Cloudflare.

## REBUILD 136 — Tarjetas que dejan ver el fondo real (18-10-2026)

- **Motivo y base:** REBUILD 135 completa. La captura en Windows confirmó que la mezcla de fondo + acento al 63 % generaba placas verde petróleo demasiado uniformes. Se respetaron las reglas obligatorias y se conserva el TXT idéntico.
- `main.py`: se elimina `_glass_surface_color`, ya obsoleta. La clave `palette.panel` pasa a `#30000000` (18,8 % negro, 81,2 % transparente); se superpone de forma natural al degradado global continuo en la posición real de cada tarjeta. No se derivan tintes a partir del acento ni se imponen colores sólidos, y la interfaz sigue adaptándose al cambio de tema en vivo. Nueva `palette.panelOpaque` conserva el color panel original para diálogos flotantes.
- `ui/Main.qml`, `ui/Overview.qml`, `ui/CleanupPage.qml`: solo se aíslan los fondos de menú de cuenta y modales en `panelOpaque` para mantener legibilidad; el resto de tarjetas transparentes reutiliza `palette.panel`. `ui/StatTile.qml`: el hover usa acento al 10 % en lugar de placa elevada gris. Versión en encabezado V136.
- `tests/test_rebuild.py`: pruebas antiguas específicas del tintado V135 quedan sustituidas por contratos actuales de transparencia, compositing para paletas, modales sólidos, preservación del gradiente y conexión dinámica.
- **No alterado:** tamaño/orden de la interfaz, sidebar, divisor, otras funciones, base Cloudflare, precios/permisos, energía automática ni normas REAL_OR_NA. No se agregan archivos ni dependencias. Prueba visual definitiva con Windows/PySide6 pendiente.
- **Reversión:** ZIP original REBUILD 135. No se requiere despliegue Cloudflare.

## REBUILD 135 — Tarjetas de cristal tintado por tema, sin relleno gris plomo (18-10-2026)

- **Motivo:** la prueba visual de V134 mostró que 91 % de opacidad con base gris seguía pareciendo plomo. Se corrige la causa cromática y la transparencia real, en vez de añadir capas visuales.
- **Base:** V134 completa; `Reglas para crear Versiones nuevas.txt` leído y preservado. Mantiene degradado único en toda la ventana y separador dinámico del sidebar sin roces.
- `main.py`: `_glass_surface_color(bgEnd, accent)` prepara el relleno `#A0RRGGBB` (63 % de opacidad). Se combinan fondo inferior del tema (74 %) y acento actual (26 %), eliminando el gris como color base. Una sola fuente de color alimenta las tarjetas de las páginas existentes. Los demás colores y el catálogo original de 14 temas se conservan.
- `ui/Main.qml`: solo versión de pantalla a 135. No se cambian posiciones, tamaños, geometría, bordes, botones ni reglas del sistema.
- `tests/test_rebuild.py`: actualizar la comprobación visual histórica V134, ahora obsoleta, y probar alfa/tintado, colores diferentes según tema y reutilización de `palette.panel` en pantallas.
- **Validación local:** 315 pruebas Python aprobadas y los mismos 37 fallos heredados de V134 (comparados por nombre, sin regresiones); cloud 61/61 PASS. Integridad ZIP verificada. PySide6/QML real y la apariencia final requieren prueba en Windows. No requiere redesplegar Cloudflare, cambios de cuentas ni compras.

## REBUILD 134 — Separador con margen y tarjetas suavemente translúcidas (18-10-2026)

- **Base:** REBUILD 133 completa; reglas del TXT y el historial consultados. Fondo único y divisorio dinámico por tema preservados.
- `ui/Main.qml`: margen adicional a las opciones principales, «Más módulos», módulos extra y botón colapsar, evitando que el halo de 8 px toque sus superficies. Sin modificar la posición ni anchura del divisor; conserva línea de 1 px y `accent` del tema en directo. Etiqueta REBUILD 134.
- `main.py`: únicamente el color `panel` expuesto en `ThemeManager.palette` es RGBA (`#E8RRGGBB` = 91 % opacidad). Con ello, las tarjetas en todas las páginas dejan asomar un poco el fondo general; la capa de texto, iconos y trazados no se altera, y `panelRaised` sigue sólido para botones/superficies elevadas. Los colores RGB originales de las 14 paletas siguen en el catálogo sin cambios.
- Sin nuevas dependencias ni módulos. No se cambia monitoreo, historial, FPS, energía, juegos, permisos o servicio de IA. No requiere `wrangler deploy`.
- **Pruebas:** 313 Python PASS y los mismos 37 fallos históricos de V133 (311 PASS, 37 FAIL); 61/61 pruebas Cloud PASS. Comparación por nombre: 0 regresiones nuevas. QML/Windows visual pendiente. Reversión con ZIP V133 completo.

## REBUILD 133 — Divisor del sidebar con acento dinámico de cada paleta (18-10-2026)

- **Base:** ZIP REBUILD 132 completo. Se leyeron reglas e historial y se conserva exactamente el archivo de reglas original.
- **Solicitud visual:** aumentar discretamente la visibilidad del divisor y que adopte el color dominante del tema, no cian en todas las paletas. El divisor usa `window.activeTheme.accent` (la paleta cambia por `themeManager.changed`) y se actualiza sin reiniciar.
- **Estética:** 1 px con degradado de opacidad (máximo 0,27) y una aura difuminada de 8 px (máximo 0,075), desapareciendo en extremos. Sidebar y espacio de trabajo siguen compartiendo un único fondo sin placas ni bordes fuertes.
- **Ámbito:** `ui/Main.qml`, tests visuales estáticos `tests/test_rebuild.py`, documentación y este historial. No se modifica backend, perfiles, IA, planes de energía ni otros módulos.
- **Pruebas:** Python 311 PASS / 37 fallos históricos idénticos a V132 (310 PASS / 37 fallos), sin regresiones nuevas. Worker Cloud 61/61 PASS. Compilación sintáctica Python y ZIP verificados; evaluación visual QML en Windows/PySide6 pendiente. Reversión: ZIP REBUILD 132 íntegro.

## REBUILD 132 — Divisor suave sidebar/contenido (18-10-2026)

- **Base:** REBUILD 131 íntegra, confirmada visualmente por el usuario. Reglas originales consultadas y conservadas literalmente; se mantiene el degradado `bgStart` → `bgMid` → `bgEnd` único para toda la ventana.
- **Cambio exclusivo de estética:** superposición en el extremo derecho del sidebar: línea vertical de 1 px con extremos transparentes más aura cian translúcida de 6 px. Intensidad decreciente al bajar; tonos del tema actual mediante `window.activeTheme.cyan`.
- **No crea una placa de navegación ni altera geometría:** divisor ornamental, sin `MouseArea` y anclado al sidebar para acompañar expansión/colapso y las distintas resoluciones.
- **Componentes sin cambios:** CorePulse AI/Cloudflare, autenticación, sensores REAL_OR_NA, Benchmark, Rendimiento, portadas, Autoenergía, Tweaks, Health, navegación, otras pantallas y persistencia. No se requiere desplegar el Worker.
- **Archivos:** solo `ui/Main.qml`, pruebas del contrato visual existente (`tests/test_rebuild.py`), `README.md` y `versiones/HISTORIAL.md`. No se agregan módulos ni dependencias de producción.
- **Pruebas:** Python 310 PASS / 37 fallos heredados (V131: 308 PASS / los mismos 37 fallos; sin regresiones); pruebas del Worker 61/61 PASS. Dos contratos nuevos del divisor PASS. Sintaxis Qt/QML verificada mediante contratos estáticos; prueba visual en Windows/PySide6 pendiente. Reversión: ZIP completo REBUILD 131.

## REBUILD 131 — Sidebar integrado en el degradado del fondo general (18-10-2026)

- **Base:** REBUILD 130 completa. Reglas e historial consultados; no se cambia el TXT obligatorio, módulos ni dependencias.
- **Corrección de interpretación visual:** V130 había pintado el sidebar con el mismo color que las tarjetas (`panel`), cuando se había solicitado integrarlo en la **capa de fondo general**. En V131 su superficie es transparente y deja ver el mismo degradado `bgStart` → `bgMid` → `bgEnd` de `background` en toda la altura y en todas las paletas. No se copia el degradado a un segundo objeto ni se desalinean paradas de color.
- **Sin divisiones duras:** se elimina el separador vertical de un píxel. Selección, hover y borde del elemento activo son sutiles superposiciones cian translúcidas; la estructura, categorías y navegación no cambian.
- **Ámbito mínimo:** se modifica `ui/Main.qml` y se actualizan dos pruebas de contrato del estilo obsoleto V130, `README.md` e historial. Sin cambios en sensores, tarjeta de juego, autoenergía, CorePulse AI, Cloudflare, cuenta ni telemetría.
- **Verificación:** 308 pruebas Python PASS y 37 fallos históricos exactamente iguales a V130; 0 regresiones nuevas. Cloud 61/61 PASS. ZIP completo íntegro; apariencia pendiente de confirmar en Windows/PySide6. Reversión: ZIP íntegro REBUILD 130.

## REBUILD 130 — Sidebar con la misma estética de los paneles (18-10-2026)

- **Base:** ZIP completo REBUILD 129. Se leyeron `Reglas para crear Versiones nuevas.txt` y `versiones/HISTORIAL.md`; el archivo de reglas se mantiene intacto. Ningún módulo Python nuevo.
- **Unificación visual:** el sidebar adopta `panel` y `panelBorder` como los paneles del contenido. Los elementos activos usan `panelRaised` con un borde tenue y mantienen la franja cian; el hover utiliza una versión suavemente más clara de `panel`, sin bordes. Títulos e iconos inactivos responden a `muted` del tema en lugar de colores rígidos.
- **Mismo comportamiento:** navegación, colapsado, arrastre nativo, tooltips, temas, CorePulse AI Cloud, sensores, monitoreo de juegos, portadas y restauración de energía no se modifican. Solo `ui/Main.qml`, documentación, historial y pruebas de contrato existentes.
- **Sin infraestructura:** no despliegue de Cloudflare ni instalación de servicios; Worker V126 y cliente V128/V129 sin cambios.
- **Validación:** 308 pruebas Python aprobadas y exactamente los 37 fallos históricos de V129 (306 aprobadas / 37 fallos), ninguna regresión nueva; 61/61 cloud. Dos pruebas específicas del sidebar pasan. Pendiente validación visual Windows (sin PySide6 en este entorno). Revertir con ZIP REBUILD 129.

## REBUILD 129 — Tarjeta completa y energía reversible por juego (18-10-2026)

- **Base:** REBUILD 128 íntegra; leídas reglas obligatorias e historial completo. Se mantiene la API `ai.corepulse.cl`, cuenta, consentimientos, sensores, RTTSS, Tweaks, historial y módulos ajenos a Rendimiento.
- **Limpieza visual solicitada:** se quitan el bloque superior «Rendimiento y estabilidad» y la tarjeta «Estabilidad de CPU y RAM», botón de prueba y modal QML. La página Rendimiento permanece accesible y mantiene tarjeta de juego, Game Boost, planes y telemetría térmica.
- **Portada de juego:** se distingue la portada ancha verificada del icono de exe; el fallback sigue mostrando la **tarjeta completa** con identidad, estado, origen y tiempo, sin simular una portada oficial. La conversión de arte descargado usa archivos separados de lectura y escritura para evitar bloqueos en Windows. Solo se consulta arte remoto cuando el usuario visualiza Rendimiento, no por el monitoreo de juegos para energía.
- **Autoenergía:** al arrancar CorePulse se inicia observación compartida de procesos detectados, sin depender de tener abierta la pestaña. El cambio automático busca ÚNICAMENTE planes existentes: Ultimate/«Máximo rendimiento» y luego High/«Alto rendimiento», con validación `powercfg`; si falta o se deniega no inventa el cambio. Guarda respaldo separado de planes manuales y restaura al cerrar último juego, apagar la automatización o salir de la app. Se evita falso cierre por una detección vacía aislada. Si Windows cambió de plan manualmente, NO se sobrescribe. Tras cierre abrupto, el respaldo permite restaurar al siguiente arranque; sin la app abierta no existe observación del juego.
- **Control y privacidad:** preferencia autoenergía activa de inicio y desactivable en Rendimiento; no requiere permisos de administrador ni manda procesos/sensores a Internet. Game Boost y su permiso siguen separados. No se crean nuevos planes, cambios de voltaje, overclock, opciones BIOS o prioridad Realtime.
- **Archivos:** `core/health/performance.py`, `main.py`, `ui/HealthPage.qml`, `ui/Main.qml`, pruebas existentes, README e historial. No módulos Python de producción nuevos. TXT de reglas sin modificar.
- **Pruebas:** 306 Python passed, 37 fallos previos idénticos a V128; cloud 61/61 JS passed. Verificación QML en Windows y reacción de planes `powercfg` reales pendiente. Revertir con el ZIP V128 completo.
- **Cloudflare:** ninguna modificación: NO desplegar Worker. CorePulse AI permanece como en V128 y se pausa su evolución en esta versión.

## REBUILD 128 — Reconexión segura sin configuración (18-10-2026)

- **Base:** REBUILD 127 íntegra, conexión automática confirmada por el usuario en Windows. Se preservan las reglas originales, módulos Windows, autenticación, RAG, sensores, REAL_OR_NA, consentimientos y API Cloudflare desplegada (Worker V126).
- **Reconexión sin intervención:** ante fallos de red o servicio en el probe inicial, chat o diagnóstico, reintenta **solo** el estado autenticado `/v1/status` con esperas progresivas 15, 30, 60, 120 y máximo 300 segundos. Para HTTP 429 respeta al menos 75 segundos. No se hace sondeo periódico permanente cuando la IA está sana, para ahorrar llamadas al Worker y respetar cuotas gratuitas. Si la red cae mientras no se está utilizando, el fallo se detectará al intentar una operación.
- **Privacidad / consumo:** jamás reenvía automáticamente una pregunta, un diagnóstico ni telemetría; solo consulta disponibilidad autenticada. Al reintentar no cambia permisos. Sin Internet continúa funcionando CorePulse Windows y su diagnóstico local.
- **Credenciales y seguridad:** 401/403, autorización ausente o presupuesto agotado NO entran en reintento automático; se muestra el motivo. Los intentos programados se invalidan ante cierre de sesión, cambio de cuenta/token, apagado de IA, deshabilitación de preguntas, cambio de proveedor o cierre del programa. El usuario conserva «Reintentar» para probar manualmente.
- **Implementación:** se actualiza `core/ai.py` sin crear nuevos módulos ni archivos de producción. Etiqueta V128 en `ui/Main.qml`, seis pruebas con Qt falso en `tests/test_cloud_ai.py`, documentación e historial. NINGÚN cambio al código del Worker, claves, DNS, cuota ni datos persistentes.
- **Validación local:** suite Python **301 passed, 37 failed**: los 37 fallos previos de la V127 se compararon por nombre, sin regresiones. 61/61 pruebas cloud heredadas PASS. No validado visualmente en Windows; probar caída/restablecimiento de Internet y logout con la app real.
- **Despliegue:** no ejecutar `wrangler deploy`; basta abrir el ZIP V128 en Windows con `Iniciar_CorePulse.bat` o `main.py` desde VS Code. **Sin planes de pago ni servicios nuevos.**
- **Avance CorePulse AI:** V127 confirmada en Windows; V128 86 % estimado, sujeto a validación en PC real. Reversión mediante el ZIP V127 íntegro.

## REBUILD 127 — CorePulse AI automática, sin claves ni ajustes de proveedor para el usuario (18-10-2026)

- **Base:** ZIP completo REBUILD 126 probado por el usuario en Cloudflare y Windows. Reglas obligatorias y todo el historial conservados. El único objetivo de esta versión es simplificar la conexión; no introducir precios, Premium, nuevos servidores ni cambiar el motor de diagnóstico.
- **Conexión automática:** `cloud_url()` usa `https://ai.corepulse.cl` por defecto; solo acepta dominio oficial HTTPS o localhost en modo de desarrollo opt-in. La app instancia siempre el cliente de CorePulse AI Cloud; al arrancar verifica `/v1/status` en un trabajador sin bloquear QML si hay token de equipo guardado. Tras iniciar sesión en web, se conecta sola, y la pantalla permite reintentar si hay un fallo transitorio. No hay reintentos cíclicos.
- **Sin API Key del usuario:** se retira del panel de IA la selección de Groq, el formulario de clave y el paso manual «Conectar IA». El servicio cloud vigente sigue utilizando el proveedor configurado **en el servidor**, que no se migra en esta etapa. La comunicación con `ai.corepulse.cl` autentica con el token de CorePulse; jamás envía al PC el secreto Groq.
- **Consentimiento y privacidad:** la IA queda operativa por defecto únicamente para verificar el servicio y para enviar las **preguntas escritas y enviadas explícitamente**. No se transmiten conversaciones o lecturas al iniciar. Compartir hardware y compartir agregados de Tendencias siguen **apagados de inicio** y necesitan autorización separada. Se mantiene `REAL_OR_NA` y la comparación de sesiones requiere pregunta relevante; el usuario puede apagar toda la IA y bloquear preguntas. Los interruptores `enabled`/`questions` se recuerdan sin tokens, sensores ni chats en `LOCALAPPDATA/CorePulse/ai-preferences.json`; al cerrar sesión se invalida la conversación y al cambiar de cuenta se revocan permisos técnicos.
- **Costos controlados:** no se activa otra infraestructura, cobro o suscripción; la cuota central del Worker V126 no cambia. No prometer gratuidad o consultas generativas ilimitadas cuando un proveedor/plan gratuito puede imponer límites.
- **Cambios:** `core/ai.py`, `core/cuenta.py`, `ui/AIPage.qml`, etiqueta de `ui/Main.qml`, `tests/test_cloud_ai.py`, cuatro adaptaciones puntuales en pruebas UI históricas de `tests/test_rebuild.py`, documentación e historial. No se modifica el Worker ni la telemetría o la persistencia de salud.
- **Pruebas:** se compara la lista de fallos de Python con la V126, verificando que todos los fallos históricos son idénticos. Se añaden pruebas de cliente cloud por defecto, URL allowlist, preferencias, conexión/consulta/logout sin telemetría en un Qt simulado. Cloud JS sigue en 61/61. **No se pudo ejecutar QML real en Windows desde el entorno de desarrollo**; validación del usuario pendiente.
- **Despliegue:** no `wrangler deploy`, no `npm install` ni cambios de DNS/secretos. Abrir la nueva carpeta con `Iniciar_CorePulse.bat`, iniciar sesión si hace falta, preguntar y comprobar respuesta. Prueba de privacidad: sin activar «Compartir lecturas técnicas», el cliente debe enviar un `snapshot` vacío. Probar apagar y reabrir, luego activar.
- **Avance estimado AI:** 84 % tras validar V126 en Windows; V127 85 % implementado y pendiente de comprobación real.

## REBUILD 126 — Resumen plegable y recomendaciones verificables (18-10-2026)

- **Base:** ZIP V125 íntegro; `Reglas para crear Versiones nuevas.txt` y versiones anteriores preservadas. No se alteran sensores, inicio de sesión, SQLite, Tendencias, reportes, drivers ni temas.
- **Análisis completo sin segunda consulta:** cuando el usuario solicita comparar sesiones con consentimiento de Tendencias, el Worker entrega el resumen, la clasificación verificable y el desglose propio juntos; la tarjeta despliega el desglose **localmente** con «Ver análisis completo / Ocultar análisis». Sin gasto adicional de Groq ni cambio de permisos. Para el chat genérico no se envía ni se muestra comparación no autorizada.
- **Estado y fuentes:** se presenta el estado de la evidencia calculado por reglas CorePulse; fuentes oficiales contra lista permitida y sección «Fuentes» plegable con títulos cortos en vez de URLs largas. Los enlaces se abren solo mediante clic deliberado. El chat sigue mostrando texto plano, sin HTML interpretado.
- **Batería:** advertencias históricas recurrentes no determinan desgaste o carga defectuosa; desglose aconseja validar con el módulo Batería y el informe local `powercfg /batteryreport`, comparando capacidades **si existen lecturas**. No envía datos nuevos ni ejecuta acciones Windows.
- **Retrocompatibilidad:** se conserva el método de chat de texto anterior en el cliente; el nuevo transporte estructurado solo afecta al modo CorePulse AI Cloud y no cambia el esquema RAG ni el motor de presupuestos.
- **Pruebas locales:** 61/61 JS cloud, 267 Python aprobadas y los mismos 37 fallos heredados de V125 (verificados por nombres), sin nuevas regresiones. QML real / desplegado V126 pendiente.
- **Avance estimado CorePulse AI:** V125 80 % validado en el equipo → V126 82 % por usabilidad, sujeto a nueva validación Windows y Cloudflare.

## REBUILD 125 — Resumen útil y detalle bajo demanda de CorePulse AI (18-10-2026)

- **Base:** REBUILD 124 íntegra, ya probada por el usuario en Cloudflare/Windows. Se conserva la misma API, el modelo Groq, el dominio, los bindings, las cuotas, las fuentes RAG, las reglas REAL_OR_NA y el consentimiento separado de Tendencias. No se modifica la persistencia de sensores, sesiones ni el esquema SQLite.
- **Respuesta corta verificable:** el Worker usa sus propios contadores para presentar primero una conclusión breve con señales recurrentes o aisladas, cobertura, huecos sin medición y hasta dos pasos concretos. No satura el chat mostrando por defecto todas las categorías sin incidencias. La clasificación permanece en el servidor y no depende del modelo generativo.
- **Detalles a petición:** la conclusión técnica V124 se conserva sin pérdida y se devuelve únicamente al pedir explícitamente los detalles de comparación entre sesiones. Se agrega un botón **Ver análisis completo** en el chat únicamente cuando Cloud está conectado y el consentimiento de Tendencias está activo. El clic genera una pregunta expresa y vuelve a validar los permisos; no autoriza nada automáticamente ni accede a muestras crudas.
- **Batería:** las alertas históricas registradas son estados, no causas diagnósticas. Dos sesiones con advertencias no prueban degradación, fallos de carga ni pérdida de capacidad. Se recomienda revisar la sección Batería y el informe local `powercfg /batteryreport` cuando exista, sin enviar nuevos datos a la nube.
- **Continuidad:** si Groq está sin cuota o no responde, el resumen propio sigue disponible con comparación autenticada y autorizada; el detalle sigue disponible a petición. Otras funciones de chat mantienen su comportamiento previo.
- **Validación local:** 58/58 pruebas cloud aprobadas, incluidas cuatro pruebas de resumen, precisión de batería, detalle bajo petición y funcionamiento sin proveedor. Suite Python y sintaxis verificadas; 37 fallos históricos de la V124 sin regresiones nuevas. No se ha desplegado V125 ni probado visualmente en Windows.
- **Avance CorePulse AI:** V124 **75 %** tras la validación real del usuario; V125 **78 % estimado** por la mejora de usabilidad y trazabilidad, pendiente de publicar el Worker y comprobar el botón en Windows.

## REBUILD 124 — Dictamen propio en español para problemas entre sesiones (18-10-2026)

- **Base íntegra:** `CorePulse_REBUILD_123_AI_COMPARACION_ENTRE_SESIONES.zip`. Se mantienen reglas TXT, todos los módulos y base de datos; sin cambios en telemetría, permisos Windows, gráficos, reportes o esquema SQLite.
- **Cambio principal:** `verifiedSessionVerdict` del Worker parte solo del esquema de contadores cerrado y calcula conclusión e interpretación textual por componente. Recurrencia exige 2 sesiones con el mismo evento sostenido; un único evento, un pico extremo sin continuidad y sensores N/A se informan por separado. La falta de eventos no se interpreta como ausencia general de problemas. Se explicitan huecos sin datos y diferencia entre umbrales preventivos y límites oficiales.
- **Proveedor subordinado:** Groq solo aporta consejos generales filtrados; no puede alterar la conclusión ni insertar códigos `recurring`, `isolatedPeaks` o `no_recurrence_in_recorded_events` en el informe. Si se agota el presupuesto del modelo o falla el proveedor, el dictamen verificado puede entregarse sin consumir una nueva llamada. Fuera de este flujo, el chat y el diagnóstico funcionan como antes.
- **Fuentes RAG:** solo documentos aplicables a problemas observados y al fabricante verificado; no citar documentación general de rendimiento como respaldo de temperaturas.
- **Privacidad:** comparación únicamente bajo solicitud explícita + consentimiento de Tendencias, preguntas y hardware; no se transmiten IDs, muestras individuales ni horas exactas, y el Worker no los acepta en su esquema.
- **Validación local:** 54/54 tests cloud aprobados en Node.js 22; 265 tests Python aprobados y 37 fallos heredados en este entorno, idénticos a la base V123. Sin fallos nuevos. Prueba de la aplicación real y Worker V124 en Cloudflare pendientes.
- **Avance estimado IA:** V123 70 % → V124 **73 %**, provisional hasta una prueba real.

## REBUILD 123 — CorePulse AI: comparación de salud entre arranques (18-10-2026)

- **Base:** REBUILD 122 completa; historial, `Reglas para crear Versiones nuevas.txt`, backend Windows y Cloudflare, RAG y cuota Groq conservados.
- **Evidencia local:** comparación de hasta cuatro **arranques distintos de Windows** con muestras conservadas en Tendencias. No se crean sesiones cuando CorePulse se reabre; no se cambia la base SQLite, su esquema ni su retención actual de 90 días.
- **Criterios preventivos:** CPU >= 90 °C y GPU >= 85 °C durante al menos 3 minutos de muestras consecutivas; RAM >= 90 % durante al menos 5 minutos. Pausas de más de 95 segundos rompen los episodios. Pico extremo sin continuidad queda separado; umbrales preventivos CorePulse, no Tjmax oficial de hardware.
- **Cobertura:** cada componente informa cuántas sesiones tuvieron evidencia utilizable, cuántas mostraron el episodio, y cuántas carecieron de sensores o datos verificados. Batería y estado físico de disco vienen de alertas verificadas; casi lleno no equivale a daño SMART. Recurrencia requiere al menos 2 sesiones **independientes** con el mismo problema observado.
- **Privacidad:** se reutiliza el permiso **independiente, desactivado por defecto**, de Tendencias. Solo se accede a comparación tras una **pregunta explícita** sobre repetición/otras sesiones y los permisos de preguntas + hardware + historial activos. El cliente transmite únicamente contadores anónimos; ni IDs de sesión, timestamps exactos, filas crudas, rutas ni usuario. El Worker usa un esquema cerrado y descarta claves imprevistas. Sin permiso o con una sola sesión: no afirmar recurrencia.
- **Diagnóstico propio:** el Worker clasifica los episodios recurrentes, aislados, puntuales y sin lectura **mediante reglas del servidor**, antes del texto de Groq. El modelo genera la explicación, no determina por sí solo la recurrencia; RAG thermal por proveedor se mantiene.
- **Pruebas:** 49 pruebas JS, 288 pruebas Python aprobadas, 37 pruebas heredadas fallidas (idénticas a V122 original), sin regresiones nuevas. Comparación real Cloudflare/Windows y auditoría npm del usuario pendientes.
- **Despliegue:** ejecutar `npm.cmd install`, `npm.cmd run verify`, `npm.cmd audit`, `npx.cmd wrangler deploy` desde `cloud/corepulse-ai` en la cuenta Cloudflare habitual. Sin nueva clave, dominio ni binding. El Worker público sigue ejecutando la V122 hasta desplegar V123.
- **CorePulse AI:** **70 % estimado** tras implementar comparación; sujeto a la prueba real en Windows y nube. Porcentaje no es una métrica de calidad certificada.

## REBUILD 122 — RAG térmico afinado y Tendencias con consentimiento separado (18-10-2026)

- **Base:** V121 íntegra. Reglas y versiones históricas conservadas, sin modificar permisos de Windows, sensores, cambios de sistema ni infraestructura desplegada.
- **RAG:** reconocer consultas con "sobrecalentando", "grados", "°C", plurales y términos térmicos; solo fichas relevantes para CPU/GPU y proveedor; referencia NVIDIA oficial añadida; documentos Intel/AMD verificados. No confundir un umbral preventivo con el Tjmax específico.
- **Tendencias e IA:** compartir únicamente un resumen agregado de la sesión actualmente seleccionada, cuando el usuario active un permiso adicional, mantenga el permiso de telemetría y pregunte expresamente sobre historial/duración. Por defecto desactivado; se limpia al apagar la IA o cambiar proveedor. Nunca se envían muestras, sesiones identificables, nombres ni timestamps exactos.
- **Interpretación:** duración máxima de lecturas altas consecutivas con pausas de más de 95 segundos como corte; no se afirma monitoreo mientras CorePulse estuvo cerrado. Cero no equivale a ausencia definitiva de averías; campos faltantes siguen N/A.
- **Backend:** solo admite una lista cerrada de métricas agregadas validadas; no almacena historial en el Worker ni gasta llamadas adicionales. Presupuesto, modelo y DNS se mantienen.
- **Publicación:** V122 no se desplegó automáticamente; actualizar `ai.corepulse.cl` desde `cloud/corepulse-ai` con Wrangler y probar en Windows.
- **Avance estimado CorePulse AI:** 61 % V121 → **65 % V122** pendiente de validación de producción en Windows.

## REBUILD 121 — Diagnóstico responsable, RAG por fabricante y respuestas completas (18-10-2026)

- **Base:** ZIP V120 completo. Se conservan las reglas TXT, todas las pantallas, sensores, Tendencias, seguridad, cuotas, dominio y Worker configurado.
- **IA Cloud:** la política distingue lecturas instantáneas de historial temporal y prohíbe deducir "en reposo", sobrecalentamiento prolongado o throttling a partir de un único porcentaje de CPU. Se recomienda redactar respuestas concisas con conclusión.
- **Generación:** margen de hasta 2000 tokens de salida total de Groq para GPT-OSS 120B; ante `finish_reason=length` o contenido excesivamente largo, se presenta un aviso terminado y no una respuesta recortada. No hay reintento automático ni consumo extra oculto de cuotas.
- **Knowledge Engine v2:** nuevo documento oficial Intel para temperatura de portátiles y AMD para CPU; consultas térmicas dejan de recuperar el manual genérico de Administrador de tareas como respaldo. Se sigue verificando marca; sin fabricante conocido, no se adjudican fuentes térmicas específicas.
- **Cliente Windows:** admite HTTPS de `www.amd.com` de nuestro catálogo y no corta frases para mostrar referencias. Si no caben todos los enlaces, solo incorpora los que quepan completos.
- **Privacidad:** no se envía historial de Tendencias a Cloudflare en esta versión; requiere contrato explícito y autorización separada futura. API y sensor REAL_OR_NA permanecen como antes.
- **Despliegue:** Worker V121 debe ser publicado con `npx.cmd wrangler deploy`; el dominio vigente sigue mostrando el Worker V119 hasta entonces. No volver a crear dominio ni secretos.
- **Avance estimado:** 58 % V120 validado por video → **61 % V121 implementado**, sujeto a prueba real de respuestas en Windows.

## REBUILD 120 — Arranque Windows compatible con Python 3.12 (18-10-2026)

- **Base:** proyecto completo V119, sin modificar el motor AI/RAG, Cloudflare Workers, proveedores, sensores, ni los permisos.
- **Problema real:** en Windows, `py -3` seleccionó Python 3.15 para V119 y provocó `TypeError: 'lazy_import' object is not callable` al inicializar `StabilityHealth` con `ThreadPoolExecutor`. La instalación aislada de dependencias había terminado correctamente.
- **Solución segura:** el `.bat` prioriza 3.12 x64, luego 3.14 y 3.13, rechazando de forma clara 3.15 hasta completar pruebas de compatibilidad. Conserva instalación del runtime por versión y no solicita desinstalar versiones nuevas.
- **Pruebas:** contrato automático del orden del lanzador y del rechazo 3.15; falta comprobar el arranque visual en Windows. No se toca la configuración de `ai.corepulse.cl` ni se requiere redespliegue.
- **Avance estimado CorePulse AI:** 54 % (sin incremento por reparar arranque).

## REBUILD 119 — Verificación Cloud multiplataforma y versión de Wrangler fija (18-10-2026)

- **Base:** V118 íntegra, reglas e historial revisados. Se mantiene el RAG curado de V118 y la API cloud funcional, sin cambiar lógica de diagnóstico, temas, sensores, cliente, autenticación, quotas ni Worker remoto.
- **Fallo observado en Windows:** `npm.cmd run verify` no encontraba `test/*.test.mjs`, porque Node recibió el comodín sin resolver. Los archivos `test/knowledge.test.mjs` y `test/service.test.mjs` sí estaban en el ZIP. Los scripts `verify` y `test` ahora usan ambos nombres explícitos.
- **Dependencias:** Wrangler fijado a `4.151.1` (versión publicada y probada anteriormente en la cuenta del usuario); la V118 anterior declaraba `^4.36.0`, y la instalación realizada por el usuario seleccionó `4.86.0` con 6 avisos de auditoría (1 bajo, 5 altos). No se afirma que la nueva instalación esté libre de alertas hasta ejecutar `npm.cmd audit` sobre Windows. No se ejecuta `audit fix --force`.
- **Comprobaciones:** `node --check` de los dos módulos y 35 pruebas del Worker aprobadas en Node 22; no se requieren cambios de código cloud ni recrear dominio, Worker o secreto. **Despliegue V119 pendiente de confirmación del usuario**; salida de V118 mostraba inicio de OAuth, no éxito de publicación.
- **Progreso estimado IA:** permanece **54 %**; ajuste de herramientas, no nueva capacidad.

## REBUILD 118 — Knowledge Engine + RAG curado de CorePulse AI (18-10-2026)

- **Base:** ZIP REBUILD 117 que el usuario desplegó en `ai.corepulse.cl` y con el que verificó una conversación real. TXT de reglas y todo el historial revisados antes de editar. No se altera el nombre del Worker, la migración de Durable Object, las cuotas ni el dominio.
- **Nuevo conocimiento propio:** módulo compacto `cloud/corepulse-ai/src/knowledge.mjs` con **7 fichas de documentación oficial** revisadas: uso de CPU/RAM/GPU, temperatura Intel, espacio en disco, salud/contadores de almacenamiento, batería y drivers. Cada ficha tiene identificador, resumen acotado, título y URL de referencia; **sin scraping, buscador web ni embeddings externos**.
- **RAG básico verificable:** se seleccionan solo fichas relacionadas con la consulta o los indicadores de diagnóstico. El texto recuperado se pasa como contexto separado al modelo GPT-OSS 120B (Groq), manteniendo la política del servidor y las lecturas autorizadas. Una consulta genérica (`hola`) no recupera fichas. No se usa referencia Intel para CPU AMD.
- **Citas controladas:** el Worker responde un arreglo `sources` desde su catálogo, no URLs inventadas por el modelo. El cliente Windows valida que sean HTTPS de `support.microsoft.com`, `learn.microsoft.com` o `www.intel.com`, y las presenta como **Documentación de referencia (catálogo CorePulse)**. La bibliografía no constituye certificación de sensores, confirmación de salud del equipo ni consulta web en directo.
- **Privacidad/seguridad:** no se indexan datos del usuario en el conocimiento, no se guardan chats en cloud, no se permiten enlaces arbitrarios ni instrucciones desde la pregunta como fuentes, sin nueva dependencia ni archivos `.py`. Las reglas REAL_OR_NA y consentimiento separado siguen intactas. Solo 3 documentos máximo por respuesta.
- **Compatibilidad:** respuestas anteriores del Worker sin `sources` siguen funcionando; el cliente elimina la sección de fuentes de la memoria conversacional enviada a Groq para evitar repetición. El formato público de `/v1/chat` conserva `answer` y añade `knowledgeVersion`/`sources` de modo aditivo.
- **Pruebas:** 35 JavaScript aprobadas (12 nuevas respecto a V117); 277 Python aprobadas (3 nuevas), 37 fallos heredados idénticos a V117 — ninguna regresión. Windows visual y despliegue V118 **pendientes de ejecución por el usuario**; la nube sigue ejecutando V117 hasta redesplegar.
- **Progreso CorePulse AI estimado:** V117 comprobada con una respuesta real: 50 % → **V118 preparada: 54 %**. La implementación de un catálogo inicial NO equivale a un sistema RAG completo, actualizado automáticamente ni auditable a nivel de cada afirmación.
- **Actualización:** desde `cloud/corepulse-ai`, `npm.cmd install`, `npm.cmd run verify`, `npx.cmd wrangler deploy`; no recrear Worker ni secreto `GROQ_API_KEY`. Para probar enlaces en el chat, usar la aplicación Windows REBUILD 118 con `COREPULSE_AI_CLOUD_URL=https://ai.corepulse.cl` y permisos vigentes.

## REBUILD 117 — Control de presupuesto cloud: primera reserva (17-10-2026)

- **Base:** ZIP íntegro REBUILD 116. TXT obligatorio e historial leídos; cambios limitados al Worker y pruebas, documentación e indicador de versión.
- **Causa verificada:** `SqlStorageCursor.one()` arroja excepción al consultar un contador inexistente en SQLite de Durable Objects, por lo que la primera reserva terminaba en `model_budget_unavailable` (HTTP 503). Las pruebas previas usaban un mock que devolvía `undefined` y no reproducía Cloudflare.
- **Arreglo:** `toArray()[0]` para obtener el contador opcional, mientras se conserva la transacción SQLite, los límites por usuario/global, el bloqueo preventivo sin saldo y la separación de Groq. No se borran bases de datos ni se cambia el nombre del Durable Object.
- **Validación:** Node SQL de prueba con `.one()` estricta reproduce 4 fallos de V116; la corrección hace pasar las pruebas de presupuesto y el caso de chat desde un ledger vacío hacia proveedor simulado. No se validó una llamada real a Groq ni se desplegó este Worker desde el entorno de desarrollo.
- **Aplicación Windows:** no necesita cambio funcional: basta redesplegar el Worker con `npx.cmd wrangler deploy`; el ZIP completo V117 lleva el mismo cliente de V116 y nuevo indicador de versión. No recrear `GROQ_API_KEY` ni cambiar DNS.
- **Avance CorePulse AI:** 45 % estimado, sin incremento hasta probar conversación real autenticada.

## REBUILD 116 — Errores de CorePulse AI Cloud precisos (17-10-2026)

- **Base:** REBUILD 115, ZIP íntegro. Se leyeron las reglas obligatorias y el historial antes de modificar.
- **Problema observado:** en Windows el arranque funciona, pero `CLOUD_HTTP_503` se muestra erróneamente como «Cloud aún no está configurado», aunque el servidor puede devolver `identity_unavailable` (verificación web), `service_not_configured` (faltan bindings/secretos), presupuesto o proveedor fuera de servicio.
- **Corrección puntual:** el cliente interpreta **solo códigos públicos conocidos** del JSON de error 429/503, limitado a 1 KiB, y presenta un mensaje preciso. Ningún token/clave ni respuesta arbitraria aparece en la interfaz.
- **Sin despliegue:** el Worker real ya publicado y sus secretos quedan intactos; no se requiere redesplegar. Esto mejora el diagnóstico de la causa, no la resuelve sin verificar la configuración del servidor web.
- **Pruebas:** 13 casos de cliente cloud aprobados (8 más que V115). Suite conjunta: 274 aprobadas, 37 fallos idénticos heredados de V115 (266 aprobadas, 37 fallos). Sintaxis Python verificada. No hay nueva regresión. Validar en Windows el resultado real y la autenticación de `/api/app/yo`.
- **Avance de IA estimado:** 45 %, igual que V115, porque el chat autenticado todavía no está validado.

## REBUILD 115 — Corregir orden de inicio de CorePulse AI Cloud (17-10-2026)

- **Base:** ZIP REBUILD 114, sin modificaciones del núcleo ni de la infraestructura remota. Reglas y historial leídos; TXT obligatorio conservado.
- **Error reproducido:** en Windows `main.py` llama `make_ai_controller(telemetry, system_health, cuenta)` antes de ejecutar `cuenta = CuentaManager()`, lo que genera `UnboundLocalError` al iniciar.
- **Corrección:** instanciar `CuentaManager` justo antes de `make_ai_controller`, conservar todas las referencias de login, QML y cierre.
- **Prevención:** prueba de regresión específica del orden de inicialización y paso de la misma instancia de cuenta al controlador AI. Sin archivos Python nuevos ni cambios de requisitos.
- **Infraestructura cloud:** el usuario verificó públicamente `/v1/health` HTTP 200 y `/v1/status` sin token HTTP 401 de su Worker. Todavía no se ha validado un chat con un token de cuenta; no se cambia ni redepliega el Worker.
- **Avance IA estimado:** 45 % (igual que antes de este arreglo), porque todavía falta probar la autenticación de un usuario y una respuesta real del proveedor.
- **Validación:** sintaxis y pruebas automáticas locales; funcionamiento visual de Windows y chat real aún requieren prueba del usuario.

## REBUILD 114 — Presupuesto persistente para CorePulse AI Cloud (17-10-2026)

- **Base única:** ZIP REBUILD 113 AI Cloud Motor Propio. Leídos íntegramente el TXT de reglas y el historial. Se conservan las funciones existentes y se sigue usando Groq como proveedor intercambiable.
- **Gasto bajo control preventivo:** Cloudflare Durable Object SQLite `ModelBudgetLedger` con cuota de consultas generativas: 20 por cuenta y día (identidad verificable o token como alternativa), 250 global/día y 3000 global/mes (UTC). No mide consumo de tokens ni costo monetario real; no garantiza una factura máxima.
- **Seguridad:** comprobación y reserva atómica central antes de contactar Groq; se bloquea sin presupuesto (`429`) o sin almacenamiento (`503`). No se almacena contenido conversacional, correo ni token en el contador. El endpoint determinista `/v1/analyze` sigue sin requerir Groq.
- **Archivo de infraestructura:** `cloud/corepulse-ai/wrangler.jsonc` incluye binding, migración SQLite y dominio previamente previsto `ai.corepulse.cl`; sin despliegue, credenciales ni DNS modificados. El dominio no se compró ni se publicó desde aquí.
- **Protegido:** aplicación Windows, permisos de consentimiento, telemetría, reportes, temas, drivers y tendencias sin cambios funcionales. Solo cambian los indicadores de versión en CorePulse.
- **Pruebas:** 21 tests JavaScript PASS de cuota y motor; 265 Python PASS/37 FAIL, coincidentes con V113. No se ejecutó Wrangler ni pruebas reales contra Cloudflare: entorno sin acceso al registro npm ni a la cuenta.
- **Progreso estimado IA independiente:** V111 30 % → V112 35 % → V113 38 % → **V114 42 %**. Backend público validado: **0 %**; pendiente publicar `ai.corepulse.cl`, probar autenticación real, límites de proveedor, RAG y conocimiento propio.
- **Reversión:** conservar V113; la nueva clase Durable Object no se activará hasta desplegarse. No se migran datos locales ni se requiere cambiar la base de datos de CorePulse.

## REBUILD 113 — Motor de evidencia independiente de CorePulse AI Cloud (17-10-2026)

- **Base única:** ZIP de REBUILD 112. Se leyeron `Reglas para crear Versiones nuevas.txt` y el historial íntegro antes de editar. Se conserva el proyecto completo y su TXT intacto.
- **Motor cloud propio:** `analyzeSnapshot` con reglas verificables y entrada estrictamente limitada a CPU/GPU/RAM/ocupación, sin depender del LLM. Endpoint autenticado y con limitador `POST /v1/analyze`. Las lecturas proceden del cliente; no se inventan datos ni se afirma una medición certificada o daño permanente.
- **Chat especializado:** el Worker incorpora observaciones deterministas al contexto de las consultas que siguen utilizando GPT-OSS vía Groq. No se envían claves de proveedor al PC. No hay RAG aún.
- **Configuración preparada:** dominio `ai.corepulse.cl` como Cloudflare Custom Domain y guía de despliegue/verificación. **El Worker NO se desplegó**: falta acceso a la cuenta, secretos y prueba con sistema de autenticación en vivo.
- **Avance estimado del objetivo de IA independiente en nube:** V111 ~30 %, V112 ~35 %, **V113 ~38 %**. La cifra es una estimación de ingeniería y no acredita funcionamiento en producción. Despliegue público verificado: 0 %.
- **Alcance protegido:** sin cambios en sensores, diagnósticos locales, PDF, tendencias, GPU, temas, permisos de Windows ni operaciones de mantenimiento. El modo Groq anterior se conserva.
- **Archivos:** `cloud/corepulse-ai/src/index.mjs`, `cloud/corepulse-ai/test/service.test.mjs`, `cloud/corepulse-ai/wrangler.jsonc`, `cloud/corepulse-ai/package.json`, `cloud/corepulse-ai/README.md`, `ui/Main.qml`, `core/ai.py` (identificación de versión), `README.md` y este historial. Ningún nuevo archivo Python ni dependencia Python.
- **Verificaciones:** pruebas JavaScript y comprobaciones estáticas; integración Cloudflare/Groq real y QML/Windows pendientes.
- **Reversión:** conservar ZIP de V112. No hay migración de datos del usuario ni infraestructura remota creada.

## REBUILD 112 — Núcleo independiente de CorePulse AI Cloud (17-10-2026)

- **Base única:** REBUILD 111 cargada por el usuario. Leídos el TXT obligatorio y el historial. Sin cambios en los motores de CorePulse, sensores, informes PDF, drivers, temas, iconos aprobados ni Tendencias.
- **Infraestructura preparada, NO desplegada:** un Worker nuevo dentro de `cloud/corepulse-ai/` con ruta futura `ai.corepulse.cl`, API propia, verificación del token del usuario mediante `corepulse.cl/api/app/yo` y una pasarela Groq con clave exclusiva del servidor. Este paso NO equivale a alojar un modelo propio.
- **Seguridad:** `Authorization` verificado contra el sistema web; rechazo de accesos sin credencial válida; límite aproximado de 8 consultas/minuto por identidad de token en Cloudflare (no es cuota económica exacta); filtro de tipos/campos; modelo recibe política del servidor, no instrucciones de sistema enviadas por el cliente. Sin persistencia de chats en el Worker.
- **Cliente desacoplado:** `core/ai.py` incorpora `CorePulseCloudGateway` y selección de proveedor desde `ui/AIPage.qml`. La cuenta existente se reutiliza, conservando consentimiento de preguntas y permiso separado de telemetría. Solo se habilita Cloud con `COREPULSE_AI_CLOUD_URL=https://ai.corepulse.cl` explícito. Sin ello, Groq con clave propia sigue funcionando como antes.
- **Privacidad/seguridad:** ni tokens ni claves están incluidos en el paquete. No se habilita ejecución de acciones en Windows. Respuestas de IA siguen pasando las validaciones locales y los valores ausentes permanecen N/A.
- **Alcance:** separación arquitectónica y paquete listo para pruebas/despliegue. No se desplegó el Worker ni se verificaron credenciales reales; falta RAG, base de conocimiento, cuotas/budget centrales y pruebas de integración con la web y Windows.
- **Archivos de producción modificados:** `core/ai.py`, `ui/AIPage.qml`, `main.py`, `ui/Main.qml`. **Añadidos:** proyecto JS `cloud/corepulse-ai/` y pruebas `tests/test_cloud_ai.py`; no se agregan módulos Python de producción ni dependencias Python. Documentación/versión/tests actualizados.
- **Reversión:** conservar el ZIP V111; Worker independiente nunca altera el núcleo al estar desconectado.

## REBUILD 111 — Tendencias con evaluación preventiva por sesión (17-10-2026)

- **Base única:** ZIP íntegro de REBUILD 110. Releídas las reglas de versiones y el historial antes de editar. Se conserva el TXT obligatorio sin cambios.
- **Problema de líneas cortadas:** en el gráfico, los intervalos largos sin muestras se representan con conexiones tenues y discontinuas, sin crear datos. Las lecturas ausentes de un sensor mantienen trazos separados.
- **Nuevos datos históricos reales:** migración SQLite aditiva de `samples` con `cpu_temp`, `gpu_temp`, `battery_state` y `disk_state`. Registro cada 30 segundos de métricas reales y de estados confirmados del Centro de salud, sin controlar sensores ni modificar Windows. Las lecturas antiguas quedan sin atribución térmica o física retroactiva.
- **Sesión, evaluación preventiva:** RAM >=90 % durante >=5 min de muestras continuas; CPU >=90 °C y GPU >=85 °C durante >=3 min. Picos CPU >=95 °C o GPU >=90 °C se etiquetan como mediciones puntuales, nunca como calentamiento sostenido. Aviso de disco casi lleno >=95 %, batería con salud en estado atención/crítico o estado físico confirmado de discos con advertencia/crítico.
- **Ausencias:** los intervalos sin muestras rompen las rachas; sensores inexistentes o no confirmados siguen como N/A. Estado «Sin incidencias medidas» no garantiza hardware sano. No se equipara la ocupación del disco con su desgaste ni el porcentaje de carga de la batería con salud física.
- **Interfaz:** bajo el gráfico se muestra «Estado de esta sesión» con hasta cinco conclusiones en lenguaje sencillo. Cada sesión histórica muestra una etiqueta de estado. Se mantienen Inicio, Cierre, Ver/Comparar y gráfica de 30 segundos.
- **Rendimiento:** se reutiliza la evaluación ya calculada para sesiones históricas sin nuevas muestras; solo se reevalúan las que crecieron.
- **Cambios:** `core/health/monitoring_insights.py`, `ui/InsightsPage.qml`, `ui/Main.qml`, `tests/test_rebuild.py`, `README.md`, `versiones/HISTORIAL.md`. Sin módulos nuevos ni nuevas dependencias.
- **Pruebas:** migración SQLite, series reales y cortes, límites de tiempo y sensores desconocidos; falta verificación gráfica PySide6/Windows.
- **Reversión:** conservar por separado el ZIP V110 y la base de datos local.

## REBUILD 109 — Tendencias simples por sesiones de Windows (17-10-2026)

- **Base única:** REBUILD 108 GB y GPU por fabricante. Releídos el TXT de reglas y el historial; se conserva el archivo de reglas byte a byte.
- **Corrección esencial:** `psutil.boot_time()` puede variar 1–2 segundos entre ejecuciones; se fusionan de forma no destructiva las identidades de un mismo arranque cuando difieren hasta 10 segundos, trasladando las muestras al ID persistente más antiguo. No se crea otra sesión por cerrar/reabrir CorePulse.
- **Inicio y cierre:** se muestra fecha/hora local con precisión de segundo. Para cada encendido se priorizan eventos de inicio Kernel-General 12/EventLog 6005 (incluyendo Inicio rápido), o arranque del núcleo de Windows como alternativa. Un cierre de sesión anterior solo se fija si Windows aporta eventos de apagado (ID 13 o 6006); no se interpreta el cierre de la app ni la última muestra como apagado real. Si falta la evidencia, N/A. Se leen eventos en segundo plano sin bloquear Qt.
- **Interfaz:** se retiran tarjetas de promedios, recuentos y textos técnicos en Tendencias; quedan fechas de inicio y cierre, gráfico y listado de sesiones con Ver/Comparar. Se mantienen Alertas técnicas, Historial de alertas y frecuencia de muestreo de 30 s.
- **Mantenimiento:** migración SQLite compatible: `end_ts` y `end_source`, sin eliminar lecturas legadas. Sin dependencias nuevas ni archivos de producción nuevos.
- **Archivos modificados:** `core/health/monitoring_insights.py`, `ui/InsightsPage.qml`, `ui/Main.qml`, `tests/test_rebuild.py`, `README.md`, `versiones/HISTORIAL.md`.
- **Pendiente:** comprobar eventos reales de reinicio y apagado en Windows, visual de QML y comportamiento con Inicio rápido.

## REBUILD 108 — GB en detalles y color GPU coherente (17-10-2026)

- **Base:** `CorePulse_REBUILD_107_CORREGIDA_BASE_USUARIO_106_NVIDIA.zip`.
- **GPU detalle:** se elimina el acento morado heredado. La vista de Tarjeta gráfica ahora usa el color del fabricante detectado (`NVIDIA` verde, `AMD` rojo, `Intel` azul) para mantener coherencia visual con Resumen y con la insignia superior.
- **Unidades legibles:** en la interfaz QML se reemplaza `GiB` por `GB` en los valores visibles de VRAM, RAM y overlay, tal como pidió el usuario. No cambia el cálculo interno; solo cambia la presentación.
- **Texto:** la explicación del uso de GPU deja de mencionar siempre a NVIDIA y pasa a referirse de forma genérica a la GPU monitorizada por CorePulse.

## REBUILD 107 — Insignia NVIDIA V109 sobre base V106 del usuario (17-10-2026)

- **Base:** ZIP `CorePulse_REBUILD_106 (1).zip` aportado por el usuario. Se conserva su rama con integración de PDF, drivers y temas. Esta V107 sustituye la V107 defectuosa anterior; no se toma como base la V109 completa.
- **Corrección:** se copian de la V109 visualmente aprobada los cuatro elementos necesarios para reproducir el diseño: el vector NVIDIA blanco con bloque intercalado, la transformación del eje Y a proporción 383:597, el tratamiento de `fillColor` (sin trazo), y el tamaño 29×29 del logo en Resumen. El contenedor verde y la detección de fabricante siguen intactos.
- **Protegido:** AMD/Intel, telemetría REAL_OR_NA, PDF, drivers, temas, benchmark, diagnóstico, limpieza, Speedtest, CorePulse AI y restantes pantallas de la V106 original.
- **Archivos modificados:** `ui/Glyph.qml`, `ui/MetricLine.qml`, `ui/Main.qml`, `README.md`, `tests/test_rebuild.py` y este historial. No se agregan módulos ni dependencias.
- **Validación:** comparación por pruebas con la V106, comprobaciones específicas de geometría y de relleno, integridad del ZIP; revisión visual QML en Windows pendiente.
- **Reversión:** conservar el ZIP de la V106 original.

## REBUILD 106 — Integración de REBUILD 105 con PDF, drivers y temas (17-10-2026)

- **Base:** ZIP completo de REBUILD 105. Se mantienen íntegros el anillo de diagnóstico en reposo, el progreso real desde 0 % y las lecturas de esta versión.
- **Informes:** se integra la plantilla PDF profesional de REBUILD 099 y la corrección de márgenes de REBUILD 100. El informe general incluye resultados de benchmark disponibles y se conserva una exportación PDF específica de benchmark con métricas y FPS por escena. Todos los PDF usan el mismo marco imprimible.
- **Drivers:** se reincorporan la interfaz con equipo identificado y acceso OEM, filtros, progreso de búsqueda y descarga por lote; la consulta continúa usando coincidencias verificables por Hardware ID. Se conservan los bloqueos para BIOS/firmware en el flujo genérico.
- **Temas:** se restauran 15 paletas con fondo degradado adaptado a cada tema, manteniendo los colores de hardware y estados.
- **Archivos integrados:** `core/health/report.py`, `core/maintenance/drivers.py`, `main.py`, `ui/BenchmarkPage.qml`, `ui/DriversPage.qml`, `ui/ReportsPage.qml`, `ui/Main.qml`, `tests/test_rebuild.py`, `README.md` y este historial.
- `Reglas para crear Versiones nuevas.txt` se conserva byte a byte dentro del proyecto y del ZIP. No se añadieron dependencias.
- **Validación:** revisión estática de la integración y del paquete. No se ejecutaron pruebas automatizadas ni se abrió la aplicación.
- **Reversión:** conservar el ZIP original `CorePulse_REBUILD_105_ANILLO_DIAGNOSTICO_0_A_100.zip`.

## REBUILD 105 — Anillo completo en reposo y progreso real desde cero (17-10-2026)

- **Base exclusiva:** ZIP completo de REBUILD 104. Reglas y historial leídos antes del cambio; se mantiene `Reglas para crear Versiones nuevas.txt` intacto.
- **Iniciar diagnóstico, presentación:** el anillo se dibuja al 100 % en reposo como contorno del botón interactivo (no indica un diagnóstico ya completado).
- **Inicio real:** al hacer clic, el motor publica `progress = 0`; la interfaz vacía el anillo inmediatamente, sin el mínimo gráfico falso del 4 %. El primer sondeo real ocurre después del intervalo existente de 250 ms, para que el 0 % sea visible.
- **Avance:** el anillo utiliza solamente el progreso publicado por `SystemHealth`; suaviza visualmente aumentos, pero no agrega progreso ficticio. En estado parcial conserva el porcentaje realmente alcanzado. El motor de comprobaciones, tiempos máximos y fuentes de datos son los originales.
- **Archivos modificados:** `ui/Main.qml`, `core/health/system_health.py`, `tests/test_rebuild.py`, `README.md` y este historial. Ninguna dependencia ni archivo de producción adicional.
- **Validación:** pruebas de contrato del anillo, inicio en 0 y versión; pruebas QML nativas y arranque Windows pendientes.
- **Reversión:** conservar el ZIP de REBUILD 104 fuera del proyecto.

## REBUILD 104 — Centrado real del diagnóstico (17-10-2026)

- **Base:** REBUILD 103 completa. Releídas las reglas y el historial antes del cambio.
- **Iniciar diagnóstico:** la zona del círculo ahora consume la altura libre del visor durante el estado inicial y la ejecución. El anillo mantiene sus 320 × 320 px y se centra realmente en ese espacio, sin desplazamiento vertical fijo. Esto corrige el círculo visualmente alto de V103.
- **Resultados:** al terminar, la zona vuelve a su altura base y el `FastFlickable` conserva el desplazamiento necesario para el detalle de lecturas, PDF e IA, sin truncar información.
- **Sin cambios:** telemetría, motor de diagnóstico, reglas REAL_OR_NA, animación de latido, navegación y otras pantallas.
- **Archivos modificados:** `ui/Main.qml`, `tests/test_rebuild.py`, `README.md` y este historial. Sin dependencias ni archivos de producción nuevos.
- **Validación:** pruebas estáticas y de regresión de versión; pendiente comprobar la posición y escalado mediante QML nativo en Windows.
- **Reversión:** conservar el ZIP íntegro de REBUILD 103.

## REBUILD 103 — Diagnóstico centrado y ampliado (17-10-2026)

- **Base exclusiva:** ZIP completo de REBUILD 102. Se releen y respetan íntegramente `Reglas para crear Versiones nuevas.txt` y `versiones/HISTORIAL.md` antes de editar.
- **Pantalla afectada:** `Iniciar diagnóstico`.
- **Ajuste visual:** el bloque principal del diagnóstico se centra mejor dentro del área disponible y se aumenta su presencia visual para evitar que se vea pequeño o desbalanceado.
- **Escalado:** se agrandan el anillo, el icono/animación ECG y los textos internos para una lectura más clara y una composición más proporcional.
- **Protegido:** no se modifica la lógica del diagnóstico, el disparo del análisis, los resultados, la integración con IA ni el resto de pantallas.
- **Archivos modificados:** `ui/Main.qml`, `README.md` y este historial. Sin dependencias nuevas ni archivos Python nuevos.
- **Validación:** revisión estática/QML y pruebas puntuales de versión. Validación visual final en Windows pendiente.
- **Reversión:** conservar fuera del proyecto el ZIP REBUILD 102.

## REBUILD 102 — Red avanzada sin diagnóstico de conectividad (17-10-2026)

- **Base exclusiva:** ZIP completo de REBUILD 101. Se releen y respetan íntegramente `Reglas para crear Versiones nuevas.txt` y este historial antes de editar. Esta V102 reemplaza la V102 descartada por el usuario; el desarrollo continúa directamente desde V101.
- **Red avanzada, UI:** se elimina por completo la tarjeta `Diagnóstico de conectividad`, incluyendo encabezado, descripción, filas de resultado y botón `Ejecutar pruebas`. La pantalla queda enfocada en inventario de red, privacidad, tráfico real y prueba de velocidad.
- **Funcionalidad retirada:** se elimina la lógica backend asociada al diagnóstico bajo demanda (gateway/ICMP/DNS) para no dejar código obsoleto ni acciones huérfanas. Se conservan sin cambios el inventario real de adaptadores, el muestreo de tráfico, los ojos de privacidad y Speedtest.
- **Protegido:** no se alteran telemetría general, sensores, Speedtest, Centro de salud, Tendencias, IA, benchmark ni la política REAL_OR_NA.
- **Archivos modificados:** `ui/NetworkPage.qml`, `core/maintenance/network.py`, `ui/Main.qml`, `tests/test_rebuild.py`, `README.md` y este historial. Sin dependencias nuevas ni archivos Python nuevos.
- **Validación:** pruebas puntuales de versión, Red avanzada y eliminación del diagnóstico ejecutadas; validación visual/QML en Windows pendiente.
- **Reversión:** conservar fuera del proyecto el ZIP de REBUILD 101.

## REBUILD 101 — Tendencias por sesiones de Windows y comparación (17-10-2026)

- **Base:** ZIP completo de REBUILD 100. Se revisaron íntegramente las reglas e historial y se conserva el TXT original.
- **Identidad de sesión:** cada arranque verificable del núcleo de Windows obtiene un identificador persistente basado en `psutil.boot_time()`. Abrir/cerrar CorePulse dentro de ese arranque NO inicia una sesión nueva. Debido a Inicio rápido/hibernación, un apagado físico puede conservar ese mismo arranque; por ello se informa esta limitación.
- **Migración no destructiva SQLite:** `samples` incorpora `session_id` y una tabla de arranques en el mismo archivo. Las muestras previas permanecen sin `session_id`, no se asignan a ningún arranque inventado y se informa su cantidad. Retención local: 90 días; sesiones sin muestras se depuran.
- **Datos REAL_OR_NA:** solo se guardan porcentajes válidos, con posibles valores individuales N/A. Las medias se calculan sobre TODAS las muestras verificadas de la sesión mediante SQLite, no sobre una selección gráfica; si no existen lecturas de una métrica, su promedio es N/A. No se interpolan huecos. Cada sesión registra primero y último dato observado; nunca se afirma conocer la hora real de apagado.
- **Tendencias:** el gráfico pasa a mostrar la sesión seleccionada. Debajo aparece Historial de sesiones con arranque, último registro, número de muestras, intervalo y promedios; permite abrir una sesión anterior y compararla con otra con curvas tenues sobre progreso relativo y diferencia de promedios en puntos porcentuales. Se conserva el botón Volver superior. Para fluidez, solo se muestran hasta 480 lecturas reales por serie sin alterar los promedios.
- **Cadencia:** almacenamiento automático cada 30 s mientras CorePulse está abierto; sin actualizar cada segundo. Repintado del gráfico solo ante muestras nuevas o selección/comparación. Los períodos en que CorePulse no estuvo ejecutándose no contienen muestras y se identifican como huecos.
- **Protegido:** no se alteran motores de telemetría, alertas, benchmark, Speedtest, IA, temas, sidebar ni limpieza. Se mantiene el almacenamiento anterior y el cierre seguro del monitor.
- **Archivos modificados:** `core/health/monitoring_insights.py`, `ui/InsightsPage.qml`, `ui/Main.qml`, `tests/test_rebuild.py`, `README.md` y este historial. Sin archivos nuevos ni dependencias nuevas.
- **Validación:** pruebas unitarias y comparación con V100; renderizado Qt nativo y sesiones tras un reinicio real pendientes de validar en Windows.
- **Reversión:** conservar el ZIP V100. La base SQLite es compatible hacia adelante; la V100 ignora la nueva columna.

## REBUILD 100 — Tendencias cada 30 segundos y cabecera limpia (17-10-2026)

- **Base exclusiva:** CorePulse REBUILD 099 completo. Se leyeron íntegramente las reglas y este historial antes de editar; el TXT original se conserva sin cambios.
- **Cadencia:** Tendencias representa únicamente las muestras reales persistidas aproximadamente cada 30 segundos por `MonitoringInsights`; se retiran los valores y repintados de telemetría por segundo añadidos en V099. Los valores ausentes se muestran como N/A y no se interpolan como mediciones válidas.
- **Actualización manual:** el botón Actualizar sigue disponible para solicitar una captura explícita. Entrar en la vista deja de forzar un guardado adicional, para preservar el intervalo automático.
- **Interfaz:** Volver pasa a la cabecera inmediatamente antes de Actualizar; se elimina el pie antiguo con Volver y la nota de N/A, recuperando una distribución limpia. Los controles de Alertas e Historial de alertas conservan sus acciones.
- **Archivos modificados:** `ui/InsightsPage.qml`, `ui/Main.qml`, `tests/test_rebuild.py`, `README.md` y este historial. No se cambian los sensores ni el servicio de historial, y no se agregan dependencias o archivos Python de producción.
- **Pruebas:** comparación de regresión y pruebas específicas; revisión visual/QML nativa en Windows pendiente.
- **Reversión:** conservar fuera del proyecto el ZIP de V099.

## REBUILD 099 — Tendencias alineadas y lecturas en vivo (17-10-2026)

- **Base exclusiva:** REBUILD 098 «Speedtest resultados web». Leídos íntegramente `Reglas para crear Versiones nuevas.txt` y el historial antes de cambiar el código.
- **Alineación:** `ui/InsightsPage.qml` deja de distribuir altura sobrante en modo Tendencias. El gráfico se coloca inmediatamente después de las tarjetas de promedios, con espaciado uniforme y manteniendo tarjetas, paleta y fondo.
- **Datos reales:** el historial local conserva muestras verificables cada 30 s; la gráfica repinta además con la telemetría del momento (~1 s), representada en un tramo final de 4 % y un punto en el extremo derecho. Las lecturas no disponibles no se sustituyen por las antiguas ni por valores inventados. Los promedios siguen correspondiendo solo a muestras guardadas.
- **Señales:** `monitoringInsights.changed` y `telemetry.metricsChanged` disparan repintado; sin nuevos temporizadores, SQLite ni consultas extra.
- **Modificados:** `ui/InsightsPage.qml`, `ui/Main.qml`, `tests/test_rebuild.py`, `README.md`, este historial. **Protegidos:** motores de sensores/historial, gráficos de Resumen, limpieza, Speedtest, IA, benchmark y reglas TXT. Sin dependencias ni archivos nuevos de producción.
- **Validación:** pruebas nuevas y regresión comparada con REBUILD 098, sintaxis Python, integridad ZIP. Renderizado QML y comportamiento real en Windows pendientes de comprobar.
- **Reversión:** conservar externamente el ZIP íntegro de REBUILD 098.

## REBUILD 098 — Apertura automática de resultado oficial de Ookla (17-10-2026)

- **Base exclusiva:** REBUILD 097 «Superficies de tarjetas unificadas». Leídos íntegramente `Reglas para crear Versiones nuevas.txt` e historial antes del cambio.
- **Speedtest oficial:** al completar correctamente una prueba Ookla, se toma el enlace de `result.url` devuelto por la CLI, se comprueba que coincida con una página HTTPS de resultados del dominio `speedtest.net` y se abre automáticamente en el navegador. Se entrega mediante señal Qt a `Main.qml` para funcionar aunque el usuario haya cambiado de pantalla.
- **Sin resultados inventados:** Cloudflare no tiene enlace web equivalente; sus datos permanecen visibles en Red avanzada. No se abre la web si la prueba falla, carece de URL o la URL es inválida.
- **Privacidad:** el enlace compartible se extrae una sola vez del resultado interno y se elimina antes de exponer los datos a QML; sin persistencia ni IP pública, ISP, MAC o ubicación. Se conservan la aceptación explícita de términos Ookla y el inicio manual.
- **Archivos modificados:** `core/maintenance/speed_test.py`, `ui/Main.qml`, `ui/NetworkPage.qml`, `tests/test_rebuild.py`, `README.md` y este historial. Ningún archivo nuevo de producción ni dependencia.
- **Validación:** pruebas de URLs oficiales, exclusión de dominios ajenos, emisiones solo en éxito y no filtración al resultado visible. Renderizado / apertura real en Windows pendientes.
- **Reversión:** conservar fuera del proyecto el ZIP REBUILD 097 original.

## REBUILD 097 — Superficies de tarjetas unificadas (17-10-2026)

- **Base:** ZIP completo de REBUILD 096. Leídos previamente `Reglas para crear Versiones nuevas.txt` y este historial íntegro.
- **Corrección:** las tarjetas ordinarias de las pantallas que perdieron su marco envolvente ahora usan la misma superficie temática `panel` y el borde `panelBorder` de las tarjetas de **Limpieza de sistema** y **Resumen**. Se sustituyeron fondos `panelRaised` y el fondo fijo de las tarjetas de lectura donde correspondía.
- **Alcance:** Tendencias, Alertas e Historial de alertas, Benchmark, Red avanzada, Overlay, Inicio, Controladores, Reportes, fichas de CPU/GPU/RAM, Diagnóstico y Lecturas disponibles. Se mantienen las superficies del encabezado, los botones, los selectores, las advertencias especiales y los diálogos para conservar contraste y jerarquía.
- **Protegidos:** sin añadir marcos de página; `ui/Overview.qml`, `ui/CleanupPage.qml`, telemetría, motores, temas, IA, benchmark y lógica de mantenimiento no se modifican. `Reglas para crear Versiones nuevas.txt` conservado byte a byte.
- **Modificados:** `ui/InsightsPage.qml`, `ui/BenchmarkPage.qml`, `ui/NetworkPage.qml`, `ui/OverlayPage.qml`, `ui/StartupPage.qml`, `ui/DriversPage.qml`, `ui/ReportsPage.qml`, `ui/ComponentDetail.qml`, `ui/Main.qml`, `README.md`, `tests/test_rebuild.py` y este historial. Ningún archivo de producción nuevo.
- **Validación:** 246 pruebas aprobadas y 28 fallidas, con exactamente los mismos 28 fallos que en la V096 (244 aprobadas y 28 fallidas); las dos pruebas específicas de V097 pasan. Sintaxis Python verificada; comprobación visual en Windows y compilación QML nativa pendientes.
- **Reversión:** conservar fuera del proyecto el ZIP V096 original.

## REBUILD 096 — Quitar envolventes decorativas de páginas (17-10-2026)

- **Base única:** CorePulse REBUILD 095 «Corrección aviso QML bandeja». Leídos íntegramente `Reglas para crear Versiones nuevas.txt` y este historial antes de modificar.
- **Problema:** varias pantallas envolvían toda la interfaz en una tarjeta rectangular con fondo y borde, ocultando la capa base de CorePulse.
- **Solución:** se quitaron exclusivamente esos marcos exteriores en Tendencias, Alertas técnicas, Historial de alertas, Benchmark, Red avanzada, Overlay, Inicio de Windows, Controladores, Reportes, fichas CPU/GPU/RAM, Diagnóstico y Lecturas disponibles. El contenido, scrolls, tarjetas individuales, confirmaciones y acciones se mantienen. Los contenedores decorativos usados solo para agrupar contenido se transformaron en `Item` sin estilo; se eliminaron los fondos decorativos independientes.
- **Fondo y diseño:** el fondo base con degradado, el sidebar, los temas y las tarjetas funcionales interiores permanecen intactos. Los márgenes redundantes del panel eliminado se quitaron para aprovechar el área de contenido y mantener el espaciado definido por `pageLoader`.
- **Archivos modificados:** `ui/InsightsPage.qml`, `ui/BenchmarkPage.qml`, `ui/NetworkPage.qml`, `ui/OverlayPage.qml`, `ui/StartupPage.qml`, `ui/DriversPage.qml`, `ui/ReportsPage.qml`, `ui/ComponentDetail.qml`, `ui/Main.qml`, `tests/test_rebuild.py`, `README.md` y este historial. **Sin nuevos archivos de producción, sin nuevas dependencias**; TXT de reglas byte a byte idéntico.
- **Validación:** 244 pruebas PASS y 28 FAIL, exactamente los mismos 28 fallos existentes en REBUILD 095 (242 PASS, 28 FAIL). Las dos pruebas nuevas de REBUILD 096 pasan. Sintaxis Python y equilibrio de delimitadores QML verificados; ejecución y aspecto nativo QML en Windows pendientes.
- **Reversión:** conservar ZIP de REBUILD 095 externamente.

## REBUILD 095 — Eliminar conexión obsoleta de bandeja RAM (16-10-2026)

- **Base única:** ZIP completo REBUILD 094 «Insignias unificadas entre detalle y Resumen». Se revisaron `Reglas para crear Versiones nuevas.txt` y el historial previo antes del cambio; se conserva el TXT intacto.
- **Causa:** `ui/Main.qml` contenía `Connections` con `onOpenRamCleanupRequested`, pero `trayController` solo declara `ramCleanupRequested`. Esto provocaba una advertencia QML al iniciar.
- **Corrección:** se elimina la conexión obsoleta del QML. La acción de bandeja conserva su conexión real en `main.py` hacia `cleanup.cleanRamDeepFromTray()` (segundo plano, sin ventana ni confirmación); la acción directa desde Limpieza conserva su confirmación existente.
- **Pruebas:** se actualiza el contrato histórico de bandeja al flujo actual y se agrega una prueba de regresión que prohíbe la referencia a la señal inexistente. No se modifica la lógica de limpieza, sensores ni otras interfaces.
- **Modificados:** `ui/Main.qml`, `tests/test_rebuild.py`, `README.md` y este historial. Sin nuevas dependencias ni archivos Python de producción.
- **Pendiente:** comprobación de arranque QML y acción real desde bandeja en Windows.
- **Reversión:** ZIP original REBUILD 094 (externo al proyecto).

## REBUILD 094 — Insignias unificadas entre detalle y Resumen (16-10-2026)

- **Base:** REBUILD 093 «Leyenda de gráfica simplificada».
- **Resumen:** las filas de CPU y GPU adoptan las placas visuales de las fichas detalladas (Intel azul, AMD rojo y NVIDIA verde), conservando la leyenda de la gráfica con puntos simples.
- **Archivos:** `ui/MetricLine.qml`, `ui/Main.qml`, pruebas, README e historial. Sin cambios en sensores ni telemetría.

## REBUILD 092 — Insignias de CPU/GPU en la gráfica y el Resumen (16-10-2026)

- **Base exclusiva:** ZIP de REBUILD 091 «CPU por fabricante en detalle y resumen». Se leyeron previamente las reglas obligatorias y este historial.
- **Resumen, Estado del sistema:** la fila GPU identifica ahora NVIDIA, AMD o Intel mediante un símbolo compacto de la marca detectada (`gpuName`); el CPU conserva su distintivo de REBUILD 091. Si falta una marca verificable, aparece el icono original del componente.
- **Gráfica, leyenda:** los puntos de CPU y GPU se sustituyen por insignias compactas con los mismos fabricantes y colores que las filas del Estado del sistema. Los datos, series, suavizado y telemetría del gráfico no cambian.
- **Archivos modificados:** `ui/Overview.qml`, `ui/MetricLine.qml`, `ui/Main.qml`, `tests/test_rebuild.py`, `README.md` y este historial. No se crean archivos Python ni dependencias nuevas; se conserva intacto el TXT de reglas.
- **Validación:** pruebas puntuales de marcas y leyenda y comparación con la base; comprobación visual QML/Windows pendiente.
- **Reversión:** restaurar el ZIP de REBUILD 091 guardado fuera del proyecto.

## REBUILD 091 — CPU por fabricante en ficha y Resumen (16-10-2026)

- **Base:** REBUILD 090. CPU Intel y AMD reciben insignia en la ficha y la fila CPU de Estado del sistema; fabricante desconocido conserva el símbolo original. Sin cambios en las lecturas.
- **Modificados:** `ui/ComponentDetail.qml`, `ui/MetricLine.qml`, `ui/Overview.qml`, `ui/Main.qml`, pruebas, README e historial. No hay dependencias nuevas.

## REBUILD 090 — Insignias GPU más reconocibles (16-10-2026)

- **Base:** REBUILD 089. NVIDIA, AMD e Intel conservan detección por `gpuName`; se mejoró la presentación de sus insignias en la ficha Tarjeta gráfica. Sin telemetría ni dependencias nuevas.
- **Modificados:** `ui/ComponentDetail.qml`, `ui/Glyph.qml`, `ui/Main.qml`, pruebas, README e historial.

## REBUILD 089 — Identificación visual de GPU por fabricante (16-10-2026)

- **Base:** REBUILD 088 «Centro de salud refinado». Se leyeron íntegramente `Reglas para crear Versiones nuevas.txt` y este historial antes de editar.
- **Ficha Tarjeta gráfica:** el icono de cabecera identifica la marca de la GPU efectivamente monitoreada (`gpuName`): motivo ocular verde para NVIDIA/GeForce/Quadro, flechas rojas para AMD/Radeon y logotipo tipográfico azul para Intel/UHD/Iris/Arc. Ante nombre desconocido se mantiene el icono GPU genérico original; CPU y RAM no cambian.
- **Implementación:** símbolos locales vectoriales de Qt Quick sin imágenes externas, peticiones de red ni paquetes nuevos. La identificación se actualiza si cambia el modelo de GPU notificado por telemetría.
- **Archivos modificados:** `ui/ComponentDetail.qml`, `ui/Glyph.qml`, `ui/Main.qml`, `tests/test_rebuild.py`, `README.md` y este historial. El TXT de reglas y los motores de sensores permanecen idénticos. Se excluyen del ZIP cuatro archivos `.pytest_cache` que ya venían en la base y no son necesarios para la aplicación.
- **Validación:** selección de marca verificada para NVIDIA/AMD/Intel/desconocida; 36 archivos Python con sintaxis válida. REBUILD 088: 234 pruebas PASS y 28 FAIL; REBUILD 089: 235 PASS y los mismos 28 FAIL preexistentes. El renderizado QML/Windows queda pendiente (PySide6 no está disponible en este entorno).
- **Reversión:** restaurar el ZIP de REBUILD 088 fuera del proyecto.

## REBUILD 087 — Íconos más grandes y simetría en Limpieza (16-10-2026)

- **Base real:** `Versión de Maxi.rar`, que contiene REBUILD 086 «Unidades removibles dinámicas y estado de desgaste explícito». Se revisaron `Reglas para crear Versiones nuevas.txt` y el historial completo antes de cambiar código.
- **Centro de salud:** los siete íconos del hub (Batería, Windows, Reparación, Historial y cambios, Recuperación, Rendimiento y Test de Audio) crecen de 21 × 21 a 30 × 30 px; sin modificar colores, títulos, navegación ni fichas internas.
- **Limpieza:** Temporales, RAM, Caché, Espacio seguro, Duplicados y Papelera comparten altura base de 270 px. RAM conserva la expansión a 342 px cuando se muestran resultados y detalles. La lógica de limpieza, botones y confirmaciones no se modifica.
- **Conservado de REBUILD 086:** inventario dinámico USB/SMART, contadores NVMe, acciones desde bandeja, descargas oficiales, benchmark V29, IA, colores y demás pantallas.
- **Modificados:** `ui/HealthPage.qml`, `ui/CleanupPage.qml`, `ui/Main.qml`, `tests/test_rebuild.py`, `README.md` y este historial. **Añadidos/eliminados:** ningún archivo de producción. `Reglas para crear Versiones nuevas.txt` se conserva idéntico al original.
- **Validación:** 233 pruebas PASS y 27 FAIL, exactamente los mismos 27 fallos presentes en la REBUILD 086 de Maxi (231 PASS y 27 FAIL). Ambas pruebas nuevas de REBUILD 087 PASS. Sintaxis Python revisada en 36 archivos. Compilación y aspecto QML en Windows pendientes de comprobación.
- **Reversión:** restaurar ZIP de REBUILD 086 de Maxi, conservado fuera del proyecto.

## REBUILD 086 — Unidades removibles dinámicas y estado de desgaste explícito (15-10-2026)

- **Base:** REBUILD 085. Se revisaron las reglas del proyecto y el historial.
- **Unidades extraíbles:** el inventario ahora incluye volúmenes locales fijos y extraíbles. Mientras el selector está abierto, CorePulse consulta cada 900 ms; al detectar inserción o retiro actualiza la lista, cambia la selección si la unidad activa ya no está y solicita de forma asíncrona el inventario físico actualizado. Así evita dejar asociado a un USB nuevo el SMART de otro disco que reutilizó el número físico.
- **Información de volumen:** cada tarjeta enseña letra, etiqueta, sistema de archivos, tipo de unidad, capacidad, espacio usado/libre y, cuando Windows lo relaciona, nombre físico, bus y tipo de medio. Los detalles SMART siguen en «Ver detalles». Un dispositivo sin volumen montado/letra asignada no puede aparecer como volumen seleccionable; Windows y el controlador determinan qué datos físicos exponen.
- **Desgaste explícito:** la cabecera del disco ahora presenta el estado orientativo «Bajo», «Moderado», «Alto», «Muy alto» o «Resistencia estimada superada», además del porcentaje consumido. Bandas informativas: <20 %, 20–49 %, 50–79 %, 80–99 % y ≥100 %. El texto aclara que es resistencia estimada consumida, no estado SMART ni confirmación de fallo.
- **Versión:** cabecera, README y expectativas de versión activa pasan a REBUILD 086. Se conserva el esquema NVMe de solo lectura.
- **Archivos modificados:** `core/health/storage.py`, `ui/Overview.qml`, `ui/HealthPage.qml`, `ui/Main.qml`, `core/maintenance/speed_test.py` (identificador de descarga), `tests/test_rebuild.py`, `README.md` y este historial. Sin dependencias ni archivos nuevos de producción.
- **Validación:** se comprobó sintaxis Python con `ast.parse` y el contenido del paquete. No se ejecutaron pruebas ni la app; falta validar conectar/retirar un pendrive real y revisar visualmente el nuevo estado de desgaste.
- **Reversión:** volver a los archivos de REBUILD 085 y renombrar la carpeta y el ZIP a `CorePulse_REBUILD_085`.

## REBUILD 085 — Descargas automáticas, limpieza desde bandeja y contadores NVMe (15-10-2026)

- **Base:** REBUILD 084. Se revisaron las reglas y este historial completo.
- **Bandeja/RAM:** «Limpieza completa de RAM» ya no restaura la ventana ni navega a Limpieza. Inicia la misma limpieza profunda en segundo plano, omite confirmación/medidor/resultado QML y usa notificaciones de bandeja. La acción desde la pantalla de Limpieza mantiene sus diálogos. Si falta privilegio de administrador, la notificación informa el error; CorePulse no eleva el proceso por su cuenta.
- **Dependencias:** el lanzador continúa preparando y verificando el entorno Python aislado con `requirements.txt`. Al crear `NetworkSpeedTest`, una tarea de fondo comprueba Ookla y descarga la CLI oficial Windows x64 1.2.0 al perfil local si falta. El ZIP se valida con el SHA-256 `13e3d888b845d301a556419e31f14ab9bff57e3f06089ef2fd3bdc9ba6841efa` antes de extraer solo `speedtest.exe`; una descarga fallida no bloquea las demás pantallas y Red permite reintentar. Nunca se lanza una prueba al iniciar.
- **Licencia Ookla:** la primera prueba requiere que el usuario marque una aceptación explícita, con enlaces a las condiciones de uso y privacidad. Solo después CorePulse envía `--accept-license` y `--accept-gdpr` a la CLI. No se aceptan condiciones durante la descarga.
- **NVMe:** la lectura SMART/Health directa añade unidades de datos leídas/escritas, comandos de host y entradas del registro de errores. La vista convierte unidades de datos a bytes aproximados con la unidad NVMe de 512.000 bytes redondeada. Los contadores separados de error de lectura/escritura solo aparecen si la fuente los proporciona; en NVMe se ocultan cuando el controlador no los expone, sin convertir otros contadores en errores.
- **Versión:** cabecera y ventana pasan a REBUILD 085; la carpeta y el ZIP final llevan ese número.
- **Archivos modificados:** `main.py`, `core/maintenance/cleanup.py`, `core/maintenance/speed_test.py`, `core/health/storage.py`, `ui/CleanupPage.qml`, `ui/NetworkPage.qml`, `ui/HealthPage.qml`, `ui/Main.qml`, `tests/test_rebuild.py`, `README.md` y este historial. No se añaden dependencias Python ni archivos de producción.
- **Validación:** no se ejecutó la suite ni se abrió la app. Queda pendiente validación nativa de la limpieza desde la bandeja, descarga/aceptación/prueba Ookla y contadores del controlador. La lectura NVMe es solo lectura; Windows y el dispositivo pueden omitir campos.
- **Reversión:** restaurar los archivos de REBUILD 084 y devolver el nombre de carpeta a `CorePulse_REBUILD_084`.

## REBUILD 084 — Historial de benchmark, colores por marca y rótulos unificados (15-10-2026)

- **Base:** contenido funcional que ya incluía REBUILD 083, aunque la carpeta seguía llamándose `CorePulse_REBUILD_080`. Se mantiene el benchmark GPU V29 y se deja intacta la capa de temas Cristal Líquido, fuera del alcance de esta entrega.
- **Historial de benchmark:** `core/benchmark.py` guarda localmente hasta 500 sesiones terminadas con mediciones verificables en `%LOCALAPPDATA%\CorePulse\resultados\benchmark_historial.jsonl`. Admite CPU/RAM/SSD y GPU. Si todavía no hay historial, toma una vez los últimos archivos válidos guardados para no perder esos resultados. Un resultado GPU conserva escenas y resumen de sensores, pero no duplica su línea temporal de muestras.
- **Comparación y exportación:** `ui/BenchmarkPage.qml` añade filtros CPU/RAM/SSD y GPU, selección de dos sesiones y diferencias numéricas. Solo compara el mismo método; GPU además exige perfil y adaptador iguales. «Exportar CSV» genera un archivo local con el filtro elegido y las 500 sesiones como máximo.
- **Colores de marca:** `ui/Overview.qml` aplica el color de cada componente a su icono, barra y línea/leyenda del gráfico. CPU AMD sigue rojo; si CPU y GPU son AMD, la GPU pasa a naranja (`#F28C28`) para distinguirlas. NVIDIA permanece verde, Intel azul, RAM teal y SSD violeta. `ui/HistoryChart.qml` repinta cuando cambia cualquiera de los dos colores.
- **Versión visible:** ventana, cabecera, README e historial pasan a REBUILD 084; la carpeta pasa a `CorePulse_REBUILD_084`. No se cambian los IDs ni los colores semánticos de los temas.
- **Archivos modificados:** `core/benchmark.py`, `core/benchmark_gpu.py` (docstrings V29), `ui/BenchmarkPage.qml`, `ui/Overview.qml`, `ui/HistoryChart.qml`, `ui/Main.qml`, `tests/test_rebuild.py` (expectativas del rótulo actualizado), `README.md` y este historial. Sin nuevos archivos de código ni dependencias; el JSONL/CSV vive en la carpeta local de datos.
- **Validación:** la sintaxis de `core/benchmark.py` y `core/benchmark_gpu.py` pasó `ast.parse`. No se ejecutó la suite automatizada ni se abrió la app. No se pudo compilar QML porque el Python 3.12 disponible no tiene PySide6. Pendiente comprobar guardado, selección y exportación con resultados reales en Windows, además del cambio visual con CPU/GPU AMD simultáneos.
- **Reversión:** revertir las modificaciones de esta sección en esos nueve archivos y devolver el nombre de la carpeta a `CorePulse_REBUILD_080`.

## REBUILD 083 — Iniciar diagnóstico: animación «Latido» (15-10-2026)

- **Base:** REBUILD 082. Se leyeron las reglas y el historial.
- **Pedido del usuario:** quitar el texto «Consulta fuentes locales. No repara ni cambia Windows.» que aparecía debajo del círculo en reposo, y elegir una animación nueva. Se le mostraron cuatro propuestas animadas (Latido, Radar, Etapas, Ondas) y eligió **Latido**.
- **Texto:** en reposo ya no se muestra nada debajo del círculo. Mientras analiza sigue el progreso («68 % · Consultando Windows…») y al terminar, la etapa final.
- **Latido:**
  - El anillo late con un doble pulso cardíaco (escala 1 → 1,06 → 0,99 → 1,03 → 1 y pausa): cada 1,6 s en reposo y cada 0,9 s mientras analiza.
  - En el centro, una línea de pulso (ECG, `QtQuick.Shapes`) tiene una traza tenue fija y un tramo brillante que la recorre al mismo ritmo.
  - Al terminar, el latido se detiene y vuelve el ícono de resultado.
- **Anillo «en el aire»:** a pedido del usuario se quitaron el disco de fondo, su borde y la pista gris. Solo queda la barra de carga flotando sobre el panel.
- **Progreso real:** el arco ahora muestra `diagnostic.progress`. Antes giraba siempre con un 72 % fijo (`RotationAnimation`), que se eliminó por obsoleto. En reposo el arco ocupa el 31 %; completo, el 100 %.
- **Archivos modificados:** `ui/Main.qml` (más `import QtQuick.Shapes`) y este historial. Sin archivos nuevos.
- **Validación:** `Main.qml` compila (Ready). En la app real se capturó el círculo en reposo, analizando (0, 22 y 68 %) y terminado: el diámetro del anillo varía entre 255 y 263 px durante el latido, la línea de pulso se dibuja y el arco sigue el avance real. Suite sin fallos nuevos.
- **Reversión:** restaurar `CorePulse_REBUILD_082_respaldo_antes_estilo_texto.zip` y volver a aplicar REBUILD 082, o deshacer este bloque de `ui/Main.qml`.

## REBUILD 082 — Botones de acción destacados (15-10-2026)

- **Base:** REBUILD 081. Se leyeron las reglas y el historial. Respaldos previos: `CorePulse_REBUILD_081_respaldo_antes_botones.zip` y `CorePulse_REBUILD_082_respaldo_antes_estilo_texto.zip` (en `D:\Programacion\Corepulse`).
- **Pedido del usuario:** que se note qué botones hacen algo. Primero se probó un relleno sólido en todas las acciones. Después el usuario eligió el estilo de su captura de Limpieza: **fondo oscuro con el texto de color** para las acciones y **botón entero de color solo en Aplicar y Actualizar**.
- **Criterio final:**
  - **Texto de color:** Iniciar, Analizar, Ejecutar pruebas, Limpiar, Liberar, Vaciar, Eliminar, Crear punto, Generar o Crear PDF, Buscar actualizaciones, Descargar, Grabar, Reproducir, Mostrar u ocultar el overlay, Cambiar atajo, Localizar RTSS.exe, Confirmar en diálogos y las acciones de IA y Benchmark. Al pasar el mouse se ilumina el borde.
  - **Relleno completo:** Actualizar del Centro de salud, Red avanzada, Inicio de Windows, Alertas y Tweaks; Actualizar dispositivos; Aplicar del plan de energía; Aplicar capa de Temas; y Aplicar de Tweaks, que ya lo tenía.
  - **Secundarios, sin cambios:** Volver, Cancelar, Cerrar, Entendido, Abrir, Ver, Mostrar u ocultar detalles, Sí/No y selectores.
- **Color:** `themeManager.palette.action` (#17B9F7, el azul de Tweaks), junto con `actionText`, `actionMuted` y `actionMutedText` en `main.py`, fijo en todos los temas. Limpieza mantiene el color de cada tarjeta. Los botones de advertencia (Deshabilitar, Limpiar alertas, Reiniciar, Instalar driver) conservan su color de texto ámbar o rojo. Benchmark usa el color de cada tarjeta.
- **Implementación:** los componentes de Limpieza, Centro de salud, Temas y Red avanzada tienen las propiedades `actionStyle` (texto de color) y `solidStyle` (relleno). No se usó `action`, porque es una propiedad FINAL de `AbstractButton`. IA conserva su estilo original de texto de color, y Benchmark pasó el texto de sus botones principales al color de la tarjeta. Los botones armados a mano se restauraron desde el respaldo y se ajustaron uno por uno.
- **Archivos modificados:** `main.py`, `ui/BenchmarkPage.qml`, `ui/CleanupPage.qml`, `ui/HealthPage.qml`, `ui/ThemesPage.qml`, `ui/NetworkPage.qml`, `ui/DriversPage.qml`, `ui/StartupPage.qml`, `ui/ReportsPage.qml`, `ui/InsightsPage.qml`, `ui/OverlayPage.qml`, `ui/TweaksPage.qml`, `ui/Main.qml`, `tests/test_rebuild.py`, `README.md` y este historial. `ui/AIPage.qml` y `ui/StatTile.qml` quedaron como estaban antes de 082. Sin archivos nuevos.
- **Validación:** las 26 pantallas QML compilan (Ready). Se capturaron y revisaron 13 pantallas en la app real. `test_082_action_buttons_colored_text_and_solid_only_for_apply_update` comprueba el criterio. `test_rebuild_034_modal_hover_states…` se actualizó, porque ahora la rama de acción va antes que el color secundario. La suite queda en 230 PASS / 28 FAIL, sin fallos nuevos; los restantes ya fallaban antes y 016/018 de Tweaks son inestables.
- **Reversión:** restaurar uno de los ZIP de respaldo indicados arriba.

## REBUILD 081 — Privacidad en Red avanzada: botón de ojo (15-10-2026)

- **Base:** REBUILD 080 con el benchmark V29. Se leyeron las reglas y el historial. Respaldo previo: `D:\Programacion\Corepulse\CorePulse_REBUILD_080_respaldo_antes_ojo_red.zip`.
- **Pedido del usuario:** que los datos que identifican la red no se muestren de golpe y que haya un botón de ojo para verlos, siguiendo el análisis de riesgo de la pantalla.
- **Ocultos por completo:** SSID (las redes Wi-Fi se ubican en bases públicas como WiGLE) e IPv6 (suele ser pública y única).
- **Parciales:** IPv4, gateway y DNS muestran el rango (`192.168.1.•••`). Si la IPv4 es pública se ocultan dos tramos (`200.42.•••.•••`). El destino del diagnóstico de gateway también se envía enmascarado.
- **Cómo funciona:** `core/maintenance/network.py` guarda el inventario completo en el controlador y entrega a QML solo `_present_network()`, con los valores enmascarados salvo los revelados. `toggleReveal()` revela un campo de la conexión principal o un adaptador (`adapter:N`) por separado. `hideSensitive()` oculta todo y se ejecuta a los 30 s, al salir de la pantalla (`stopWatch`) y al actualizar el inventario. El valor real no llega a la interfaz hasta que se toca el ojo.
- **Datos que dejan de recolectarse:** las direcciones MAC (`Get-NetAdapter`/psutil) y el BSSID del router (`netsh wlan`), que con bases públicas da la ubicación exacta del hogar. Ninguna pantalla los usaba. En `core/maintenance/speed_test.py`, el resultado ya no guarda la IP pública ni la interna, el proveedor, la ciudad, la región o el país, la interfaz, la IP de enlace ni la URL del resultado. De `/meta` de Cloudflare solo se conserva el código del centro de datos.
- **UI:** nuevo componente reutilizable `ui/PrivacyEye.qml`, un botón con ícono, tooltip y estado revelado, que no guarda el valor. Se agregaron los íconos `eye` y `eye_off` a `ui/Glyph.qml`. En `ui/NetworkPage.qml` hay un ojo en la tarjeta IPv4, en Gateway, DNS, IPv6 y SSID, y en cada adaptador, junto con un texto que explica el ocultado.
- **Archivos:** añadido `ui/PrivacyEye.qml` (componente reutilizable que se podrá usar en otras pantallas). Modificados: `core/maintenance/network.py`, `core/maintenance/speed_test.py`, `ui/NetworkPage.qml`, `ui/Glyph.qml`, `tests/test_rebuild.py`, `README.md` y este historial.
- **Validación:** los QML compilan (Ready). Se probó en la app real en Windows: al abrir, todo queda enmascarado; tocar el ojo revela solo ese dato. Con el temporizador real, a los 30 s se vuelve a ocultar todo, incluidos los adaptadores. Se agregaron 3 tests 081 (enmascarado y revelado independiente, datos no recolectados, uso del componente), que pasan. Suite: 228 PASS / 29 FAIL; los fallos son de otras áreas. Los tests 016/018 de Tweaks son inestables por timeouts y varían entre corridas sin relación con este cambio.
- **Reversión:** restaurar el ZIP de respaldo indicado arriba.

## REBUILD 080 — Benchmark GPU V29: ciudad de neón (14-10-2026)

- **Base:** REBUILD 080 «Paleta original brillante». Se leyeron completos el TXT de reglas y este historial. Respaldo previo: `D:\Programacion\Corepulse\CorePulse_REBUILD_080_respaldo_antes_ciudad.zip`. Los archivos del benchmark de la 080 eran idénticos a los de la 074, así que la escena se trasladó sin pisar los cambios de 075–080 (telemetría multivendedor, colores de GPU, esquinas y paleta).
- **Pedido del usuario:** reemplazar la escena de islas y barco, poco moderna, por una ciudad cyberpunk.
- **Escena nueva:** `core/directx_scene.py` se reescribió. `city_layout()` genera con semilla fija una ciudad de 19×19 manzanas: 3.141 edificios con estilo, alto y semilla, 4.591 faroles, 600 vehículos voladores en carriles, nubes y vapor de alcantarillas. Hay un bulevar circular libre (radio 150–196) por donde recorre la cámara (`camera_pose`). Niveles: Avenida de neón, Distrito financiero, Horizonte nocturno y Megaciudad. Cada uno escala edificios, faroles, vehículos, pasos de luz volumétrica (12/20/32/56) y resolución del reflejo (Megaciudad a resolución completa).
- **Render V29 (`core/benchmark_gpu.py`):** las instancias van en un buffer de vértices por instancia (slot 1, `INSTA`/`INSTB`), en lugar de calcularse con hashes en el shader. Hay pasada de reflejo planar de la ciudad espejada en y=0 para las calles mojadas, con charcos nítidos y asfalto con reflejo estirado. La luna proyecta sombras (mapa 4096²). La luz volumétrica de luna es un ray-march sobre el mapa de sombras. Las fachadas tienen ventanas por pisos, franjas y bandas de neón, pantallas animadas, vidrieras y balizas. El suelo lleva calles, sendas peatonales, señalización y la luz de los faroles calculada analíticamente con la misma ubicación que `city_layout()`. Cielo nocturno con estrellas y luna. Se mantienen HDR/MSAA, bloom, ACES y la medición V27.
- **Correcciones encontradas al probar:**
  - Ventanas con «estática»: el hash de ventanas usaba la normal interpolada, que varía en los últimos decimales por píxel. Ahora usa la cara redondeada.
  - El suavizado lejano de fachadas se activaba también en ventanas cercanas y las apagaba a la mitad. Ahora depende solo de las ventanas por píxel.
  - Se quitaron las estrellas de los reflejos en vidrio, que generaban ruido.
  - **1% Low falso:** el worker imprimía y vaciaba stdout dentro del bucle medido, con pausas de unos 6 ms. Ahora los avisos los escribe un hilo aparte. En la Avenida, el 1% Low pasó de ~160 a ~235 FPS con la misma GPU.
- **Eliminado por obsoleto:** terreno de islas, agua, barco y su ruta, árboles, rocas, avión, fogata, modo «tormenta» y sol de atardecer.
- **App:** `core/benchmark.py` usa el método V29 y el archivo `benchmark_gpu_v29_ultimo_resultado.json`. `ui/BenchmarkPage.qml` muestra los nombres de las escenas nuevas y los rótulos V29. V29 no se compara con V28.
- **Archivos modificados:** `core/directx_scene.py`, `core/benchmark_gpu.py`, `core/benchmark.py`, `ui/BenchmarkPage.qml`, `tests/test_rebuild.py`, `README.md` y este historial. Sin archivos nuevos ni dependencias.
- **Validación:** prueba nativa en Windows 11 con RTX 2080 SUPER, perfiles Rápido y Estándar con estado OK y capturas de pantalla. Resultados: Avenida 263 FPS (1% Low 235), Distrito 233, Horizonte 128 y Megaciudad 95 (1% Low 85), con la GPU ocupada ≥99 %. `BenchmarkPage.qml` compila (Ready). Suite: 227 PASS / 27 FAIL. Antes de este cambio eran 30 FAIL; los 3 del benchmark quedaron corregidos y los 27 restantes son de otras áreas. Se restauraron los tests de medición, sensores y nombre del equipo que no habían llegado a la 074, y se agregaron 5 tests de la ciudad: bulevar libre para cámara, tráfico y vapor; carga creciente por nivel; constantes del shader iguales a `CITY`; orden de pasadas y liberación de recursos; UI.
- **Pendiente:** probar en GPUs AMD/Intel y en notebook. MSAA 1x solo se comprueba en GPUs sin soporte 4x.
- **Reversión:** restaurar el ZIP de respaldo indicado arriba.

## REBUILD 071 — Lecturas NVMe, colores y desplazamiento (14-10-2026)

- **Almacenamiento:** además de los contadores que entregue Windows Storage, NVMe consulta en solo lectura la página estándar S.M.A.R.T./Health mediante `IOCTL_STORAGE_QUERY_PROPERTY`. Si Windows permite accederla, aporta porcentaje estimado de resistencia consumida, horas y ciclos encendido, reserva disponible, advertencia crítica, apagados inseguros y errores de medio; los atributos ausentes siguen como N/A. El 100 % de desgaste significa que se consumió la resistencia estimada, no que haya una falla confirmada.
- **Resumen:** el color de CPU/GPU sigue la marca detectada (Intel azul, AMD rojo, NVIDIA verde); RAM tiene un acento teal fijo y SSD uno violeta fijo, manteniendo el aviso de RAM crítica. La palabra «Pulse» conserva el azul de marca; salud, alertas y estados de éxito/atención/error mantienen sus tonos semánticos fuera de las capas.
- **Temas:** los nueve estilos seleccionables combinan superficies oscuras con acentos saturados y definidos, sin tonos pastel claros. Solo cambian superficies y acentos decorativos; se conserva el ID de cada tema y la base CorePulse permanente.
- **Desplazamiento:** rueda y touchpad usan una velocidad común más rápida en Flickable, listas y paneles largos, incluidos los dos niveles del Overlay. En el límite del panel interno el evento puede continuar al panel exterior.
- **Archivos añadidos:** `ui/FastFlickable.qml`, `ui/FastWheelHandler.qml`.
- **Modificados:** `core/health/storage.py`, `main.py`, `README.md`, este historial, `ui/Overview.qml`, `ui/HealthPage.qml`, `ui/BenchmarkPage.qml`, `ui/CleanupPage.qml`, `ui/ComponentDetail.qml`, `ui/DriversPage.qml`, `ui/InsightsPage.qml`, `ui/Main.qml`, `ui/NetworkPage.qml`, `ui/OverlayPage.qml`, `ui/StartupPage.qml`, `ui/ThemesPage.qml`, `ui/AIPage.qml` y `ui/TweaksPage.qml`.
- **Validación:** no se ejecutaron pruebas automatizadas, compilaciones QML ni consulta SMART en el equipo. La lectura depende de que Windows/controlador exponga la interfaz NVMe estándar; el equipo físico requiere verificación.

## REBUILD 071 — Contraste de temas e identidad fija (14-10-2026)

- **Temas:** se reforzó saturación y definición de los acentos sin aclarar las superficies oscuras. CorePulse, el azul del logo y los indicadores de marca/estado ya no toman su color de la capa seleccionada; los acentos decorativos sí siguen siendo personalizables.
- **Vista previa:** la muestra de Temas enseña colores fijos para Intel, NVIDIA, AMD, RAM y SSD, separados de la paleta decorativa elegida.
- **Modificados:** `main.py`, `README.md`, este historial, `ui/Main.qml`, `ui/Overview.qml`, `ui/ThemesPage.qml`, `ui/HealthPage.qml`, `ui/NetworkPage.qml`, `ui/BenchmarkPage.qml`, `ui/DriversPage.qml` y `ui/StartupPage.qml`.
- **Validación:** no se ejecutaron pruebas ni compilación QML en esta corrección.

## REBUILD 071 — Integración del benchmark GPU V28 y nombre de PCs armados (14-10-2026)

- **Benchmark:** se integró el motor V28 del ZIP recibido, incluidos el render DirectX 11 con sombras, HDR, MSAA adaptativo, bloom y ACES, la selección de GPU de alto rendimiento, la resolución fija 1920×1080 y la medición por fotogramas presentados/tiempo real. Se añadió la tarjeta de condiciones de prueba; sensores NVIDIA se informan cuando están disponibles y fuentes no comprobables quedan como N/A. El método y el archivo de resultado cambian a V28, por lo que no se mezclan resultados de otra metodología.
- **Nombre del equipo:** machine_model() descarta los nombres de relleno SMBIOS. Los equipos de marca muestran fabricante/modelo; los PC armados muestran COMPUTERNAME junto al fabricante/modelo de placa.
- **Modificados:** core/benchmark.py, core/benchmark_gpu.py, core/directx_scene.py, core/monitoring/telemetry.py, ui/BenchmarkPage.qml, README.md y este historial. No se modificaron main.py, IA ni las páginas recientes del overlay.
- **Validación de esta integración:** no se ejecutaron pruebas automatizadas ni benchmark nativo; la prueba gráfica requiere Windows y una GPU DirectX 11. El ZIP de origen documenta sus propias pruebas V28, que no se repitieron en esta copia.

## REBUILD 071 — Correcciones del overlay y evaluación de control térmico (14-10-2026)

- **Vista compacta:** la previsualización calcula su altura según las seis métricas para que FPS y tiempo queden dentro de la tarjeta.
- **Atajos:** los botones «Cambiar» se centran en cada fila. Esc cancela la captura con un atajo de aplicación y el atajo global de Esc solo actúa cuando la ventana está en pantalla completa.
- **Desplazamiento:** rueda del ratón y touchpad avanzan más por evento en los controles largos del Overlay; en el límite del panel interno, el desplazamiento puede continuar en la página.
- **Control térmico por juego:** esta revisión no escribe límites TPL/PL1/PL2, curvas de voltaje/reloj ni registros del controlador integrado. La compatibilidad requiere una interfaz expuesta por el fabricante, BIOS y controlador; Game Boost actual sigue limitado a las acciones de software descritas abajo. La respuesta de viabilidad queda documentada en el README.
- **Modificados:** `ui/OverlayPage.qml`, `ui/Main.qml`, `README.md` y este historial. No se agregan dependencias ni archivos.
- **Validación:** `Main.qml` y `OverlayPage.qml` compilan con PySide6; la vista compacta se renderizó para revisar geometría a 820×480, 1024×600 y 1400×900. No se ejecutó la suite automatizada ni se verificó el scroll/cancelación con ratón real.

## REBUILD 071 — Diagnóstico circular, selector SSD y pulido de navegación (14-10-2026)

- **Diagnóstico:** la pestaña ahora inicia con un círculo reactivo. Al presionarlo, consulta lecturas locales y fuentes de Windows; al terminar muestra los indicadores correctos, de atención y no confirmados. Solo marca «Todo está en orden» si las lecturas verificables no señalan incidencias. La IA recibe el resumen únicamente cuando IA, conexión y ambos permisos de consultas/lecturas están habilitados; si no, se mantiene el resultado local. Los tutoriales se enlazan como búsquedas de YouTube construidas con el componente y el hallazgo, sin inventar IDs de video. El PDF incorpora el último resumen y la devolución de IA autorizada.
- **Almacenamiento:** el icono SSD del Resumen abre un selector de volúmenes fijos. La elección persiste en QSettings y cambia las lecturas del Resumen; «Ver detalles» abre una ficha inspirada en CrystalDiskInfo. Se consultan `Get-PhysicalDisk` y `Get-StorageReliabilityCounter` para modelo, estado, temperatura, desgaste, horas, ciclos y errores; el volumen solo se asocia al dispositivo cuando Windows confirma el identificador. Atributos ausentes quedan como N/A, sin simular SMART.
- **Interfaz y navegación:** se conservan colores semánticos saturados CPU/GPU y se agrandan iconos del sidebar y tarjetas. El hover anima la fila y el icono; se quita el contorno interno verde y la placa gris del botón de plegado. Las subpáginas del Centro de salud muestran el nombre del módulo y ya no rodean el icono del encabezado. Se pueden plegar categorías individuales de Tweaks. Historial de alertas mantiene «Actualizar» y añade «Limpiar alertas» con confirmación; las alertas aún activas siguen visibles.
- **Estabilidad:** la prueba CPU/RAM permanece disponible en Rendimiento y conserva su confirmación, cancelación y corte térmico; deja de ocupar la pantalla de diagnóstico general.
- **Base visual:** la capa de fondo original `corepulse` y su gradiente permanente no cambian.
- **Añadidos/eliminados:** ninguno. **Modificados:** `core/ai.py`, `core/health/system_health.py`, `core/health/storage.py`, `core/health/report.py`, `core/health/monitoring_insights.py`, `main.py`, `ui/Main.qml`, `ui/Overview.qml`, `ui/HealthPage.qml`, `ui/MetricLine.qml`, `ui/StatTile.qml`, `ui/TweaksPage.qml`, `ui/InsightsPage.qml`, `README.md` y este historial. Sin nuevas dependencias.
- **Validación:** sintaxis Python correcta en 6 archivos y compilación de 7 componentes QML con el runtime PySide6 de REBUILD 071. No se ejecutó la suite automatizada ni las consultas nativas de almacenamiento/Windows en el equipo de Tomás.

## REBUILD 071 — Capa base permanente y pulido de Temas (13-10-2026)

- **Base visual:** `corepulse` y el fondo original quedan definidos fuera de la colección seleccionable. El controlador los inyecta siempre al construir el catálogo; las nueve capas restantes sólo cambian superficies y acentos, y se puede volver a la base desde su tarjeta fija.
- **Interfaz y paletas:** Temas recibe una vista previa viva, una banda que explica la capa permanente, tarjetas con muestras más claras y una composición adaptable para ventanas estrechas. Las nueve paletas ganan saturación y contraste; la base original queda intacta. CPU/GPU y alertas conservan colores semánticos.
- **Modificados:** `main.py`, `ui/ThemesPage.qml`, `README.md` y este historial. Sin archivos nuevos ni dependencias.
- **Validación:** ThemesPage compila y se renderiza con PySide6 a 600×720 y 1100×1050; la base aparece en el catálogo y la interfaz mantiene una columna estrecha. No se ejecutó la suite automatizada.

## REBUILD 071 — Paridad adicional de V485 (13-10-2026)

- **Audio:** se reemplazaron los tonos WAV de salida por la prueba local WASAPI de V485. Incluye dispositivo predeterminado, canales izquierdo/derecho/ambos, captura de micrófono de 5 s en memoria, reproducción de la muestra, nivel y confirmación manual. Las respuestas se guardan en `%LOCALAPPDATA%\CorePulse\audio_test`; el audio grabado se borra al cerrar. El PDF incorpora solo el estado/evidencia reciente, nunca la grabación.
- **Limpieza:** se migraron el análisis de almacenamiento seguro mediante allowlist, revalidación por archivo y confirmación antes de borrar, además del escaneo de duplicados por tamaño+SHA-256 en una carpeta elegida. El detector de duplicados es de solo lectura y no elimina archivos personales.
- **RAM/Game Boost:** Limpieza incorpora el modo normal de V485 junto a standby y profunda. Game Boost añade purga standby opcional una vez por sesión y desactivación HighQoS/Power Throttling por proceso; los cambios del proceso y la prioridad conservan rollback y no se pisan estados externos.
- **Benchmark:** se conserva la implementación GPU V26. El historial persistente de sesiones comparables, filtros y exportación CSV del benchmark V485 queda pendiente de la integración de benchmark; 071 guarda solo el último resultado por método.
- **Archivos añadidos:** `core/maintenance/storage_cleanup.py`, `core/maintenance/audio_test.py`.
- **Modificados:** `core/maintenance/cleanup.py`, `core/health/game_boost.py`, `core/health/report.py`, `main.py`, `ui/CleanupPage.qml`, `ui/HealthPage.qml`, `README.md` y este historial. IA no se modifica.
- **Validación:** sintaxis Python correcta en 36 archivos; `CleanupPage.qml` y `HealthPage.qml` compilan con el runtime PySide6 del proyecto. **Pendiente:** pruebas nativas en Windows de WASAPI/micrófono, limpieza, privilegios de purga standby y HighQoS; la visibilidad RTSS in-game también sigue pendiente. No se ejecutó la suite automatizada.

## REBUILD 071 — UI adaptable y benchmark GPU DirectX 11 V26 (13-10-2026)

- **Ventanas:** ancho mínimo reducido a 820 px y alto a 480 px; la barra lateral se compacta automáticamente bajo 1080 px, la cabecera se ajusta y las páginas reciben más área útil. Overlay usa una o dos columnas según el ancho y muestra barras de desplazamiento tanto para la página como para sus controles.
- **Benchmark GPU:** revisión artística DirectX 11 V26 con luz de amanecer, cielo y bruma de color, agua turquesa y follaje con siluetas más estrechas y variación determinista por especie. Se conservan los conteos de geometría, cuatro niveles, perfiles e intervalos warm-up/settle/medición. El identificador cambia a V26 porque cambió el sombreado; sus FPS no se comparan con V25.
- **IA:** conserva el comportamiento de REBUILD 071; esta revisión no modifica el motor de IA.
- **Modificados:** `core/benchmark_gpu.py`, `core/directx_scene.py`, `ui/BenchmarkPage.qml`, `ui/Main.qml`, `ui/OverlayPage.qml`, `README.md`, este historial. No se agregan dependencias ni assets externos.
- **Arranque:** se conserva el instalador automático de `main.py` y el entorno aislado en `%LOCALAPPDATA%\\CorePulse\\runtime`.
- **Validación:** 20 archivos QML cargados con estado Ready; shaders VS/PS compilados; `py_compile` correcto; Overlay revisado visualmente a 820×480, 1024×600 y 1400×900; perfil GPU Rápido completado con estado OK en NVIDIA GeForce RTX 3060 Laptop GPU (3 escenas). RTSS aún requiere comprobación con un juego compatible.

## REBUILD 071 — Migración funcional de V485 sin IA ni benchmark (13-10-2026)

- **Base:** CorePulse REBUILD 071. Antes de editar se leyeron las reglas de versión y este historial completo. Se integraron los módulos de V485 al diseño PySide6/QML; no se arrastraron pantallas Tk ni compatibilidad obsoleta.
- **Migrado:** Game Boost reversible y desactivado por defecto; análisis de Inicio con restauración; Drivers Direct con consulta y acciones individuales; prueba de velocidad Cloudflare/Ookla bajo demanda; tendencias e historial persistentes; exportación PDF; FPS real desde RTSS Shared Memory para el PID del juego detectado, con N/A cuando falta una muestra fresca.
- **Windows:** Inicio, servicios, eventos y dispositivos se consultan desde el Centro de salud; el diagnóstico general agrega las lecturas existentes de hardware, batería, almacenamiento, recuperación y estado de Windows. Las acciones de reparación, drivers, Game Boost y velocidad siguen sujetas a controles explícitos.
- **Estabilidad:** se añadió una prueba CPU (10 s) y RAM (7 s), con confirmación previa, cancelación, telemetría y corte térmico. No calcula rendimiento. GPU queda excluida porque la carga original reutiliza el motor de benchmark, que está fuera de esta migración.
- **IA y benchmark:** excluidos de la migración. Los archivos preexistentes de AI y Benchmark de REBUILD 071 se conservan sin cambios; sus hashes se comparan antes de sincronizar.
- **Añadidos:** `core/health/fps.py`, `core/health/game_boost.py`, `core/health/monitoring_insights.py`, `core/health/report.py`, `core/health/stability.py`, `core/maintenance/drivers.py`, `core/maintenance/speed_test.py`, `core/maintenance/startup.py`, `ui/DriversPage.qml`, `ui/InsightsPage.qml`, `ui/ReportsPage.qml`, `ui/StartupPage.qml`.
- **Modificados:** `main.py`, `core/overlay.py`, `ui/Main.qml`, `ui/HealthPage.qml`, `ui/NetworkPage.qml`, `ui/OverlayPage.qml`, `README.md`, este historial. No se eliminan archivos de la base.
- **Privacidad y reversión:** trends, rollbacks e informes permanecen en `%LOCALAPPDATA%\\CorePulse`. No hay escaneo remoto al abrir Drivers ni Speed Test; ambas acciones son manuales. El lector FPS usa un mapeo RTSS de solo lectura. No hay descargas automáticas de Ookla ni instalación automática de drivers.
- **Corrección de arranque:** Qt detectó separadores `;` inválidos entre controles hijos en Inicio, Drivers y Red; se separaron los objetos QML. En Inicio, Drivers, Informes y Tendencias, el alias visual `palette` pasó a `theme` para evitar colisiones con `Control.palette`.
- **Arranque automático:** `main.py` conserva la preparación del entorno aislado y la instalación/reparación de las dependencias listadas en `requirements.txt`; no necesita instalaciones manuales de PySide6 o psutil.
- **Verificación:** los 20 archivos QML compilan con el runtime PySide6 del proyecto. Sin prueba visual completa ni comprobación de RTSS con juego compatible. Suite de pruebas no ejecutada en esta migración.

## REBUILD 071 — Benchmark GPU DirectX 11 V25 y pulido (13-10-2026)

- **Base:** REBUILD 070; revisadas las reglas obligatorias y el historial antes de editar.
- **GPU:** portado el motor D3D11 real y escenas deterministas Valle/Bosque/Lago/Extreme de V485. Conserva calentamiento/settle fuera de FPS, render+Present cronometrado y timestamps GPU si Direct3D los permite. Rápido/Estándar/Extendido.
- **Aislamiento:** ejecución en subprocess `python -m core.benchmark_gpu` para proteger QML ante fallos nativos de DirectX; cancelación termina el subproceso y no sobrescribe resultados antiguos con datos N/A.
- **UI:** botones separados GPU y CPU/RAM/SSD, selector de perfil, estado y progreso, tarjetas compactas, FPS y 1 % Low por cada escena, JSON de resultados.
- **Motores anteriores preservados:** telemetría, Overlay/RTSS, Tweaks (78), Limpieza, Red, IA y cuentas.
- **Nuevos:** `core/benchmark_gpu.py`, `core/directx_scene.py`. **Modificados:** `core/benchmark.py`, `ui/BenchmarkPage.qml`, `ui/Main.qml`, `tests/test_rebuild.py`, `README.md`, `versiones/HISTORIAL.md`. No se copiaron módulos históricos innecesarios.
- **Pendiente:** validación nativa en Windows con tarjeta DirectX 11 y visual de las cuatro escenas; resultados reales no verificados en este entorno Linux.

## REBUILD 070 — Benchmark inicial y RTSS condicionado (13-10-2026)

- **Base:** REBUILD 069; se leyeron las reglas y el historial antes de editar.
- **RTSS:** elimina autoarranque al abrir Overlay; incorpora vigilancia asíncrona de proceso con instantánea inicial (no dispara), seguida de detección de nuevos launchers/juegos (Steam, Epic, Riot, EA/Origin, Xbox y plataformas compatibles). No se abre RTSS solo por ejecutar CorePulse. Se conservan hotkeys y publicación OSD.
- **Benchmark fase 1:** CPU aritmético, RAM copias verificadas y SSD temporal con fsync+SHA-256; progreso por etapas, cancelar, JSON local y UI Qt. Valores reales, metodología explícita sin confundir con velocidad física o puntuaciones comparables.
- **GPU:** se mantiene como N/A, pendiente de migración del motor DirectX 11 V25 y sus cuatro escenas del CorePulse V485. No se simula rendimiento.
- **Red avanzada:** comparada con V485, confirma paridad del motor de inventario, tráfico y diagnóstico básico; sin instalación extra.
- **Archivos añadidos:** `core/benchmark.py`, `ui/BenchmarkPage.qml`. Modificados: `core/overlay.py`, `main.py`, `ui/OverlayPage.qml`, `ui/Main.qml`, `README.md`, `versiones/HISTORIAL.md`, `tests/test_rebuild.py`. Sin copiar módulos antiguos ni generar duplicados.
- **Pendiente:** pruebas visuales/nativas en Windows y medición GPU V25 completa.

## REBUILD 069 — Corrección publicación OSD RTSS y Red avanzada (13-10-2026)

- **Base:** REBUILD 068; lectura previa de reglas e historial, sin cambiar Tweaks/RAM/IA ni la navegación estable.
- **RTSS OSD:** corrección de offsets críticos `dwOSDFrame` (32) y `dwBusy` (36); V068 los usaba desplazados 4 bytes, lo que impedía que el renderer reconociera la publicación. Conectado y publicado ahora se distinguen en UI; no se afirma visibilidad in-game ni se evita anticheat.
- **Red avanzada V485:** se migra inventario real psutil/PowerShell/netsh, tráfico por contadores y diagnóstico ICMP/DNS bajo demanda, con UI propia en QML. Las consultas potencialmente lentas van fuera del hilo Qt.
- **Fuentes:** `RTSSSharedMemory.h` del SDK público y módulo histórico `core/maintenance/network_details.py` de V485. Sin inventar lecturas ni FPS.
- **Archivos modificados:** `core/overlay.py`, `main.py`, `ui/Main.qml`, `ui/OverlayPage.qml`, `tests/test_rebuild.py`, `README.md`, `versiones/HISTORIAL.md`.
- **Añadidos:** `core/maintenance/network.py` (único motor), `ui/NetworkPage.qml` (única vista). **Eliminados:** ninguno; no se ha arrastrado código Tk ni dependencias obsoletas V485.
- **Validación:** 233 pruebas automatizadas PASS y `compileall` correcto. Pendiente prueba Windows nativa de RTSS/Qt y del inventario de adaptadores.

## REBUILD 068 — Integración RTSS y atajos globales (13-10-2026)

- **Base:** REBUILD 067. Se leyeron reglas e historial.
- **RTSS:** arranque automático al abrir Overlay, comprobación del servicio mediante memoria compartida `RTSSSharedMemoryV2`, publicación de OSD real en slot propio, ocultación que libera únicamente el slot de CorePulse.
- **Atajos:** se incorporan hotkeys globales independientes para Mostrar y Ocultar con captura en QML, validación y persistencia. Los atajos pueden ser rechazados por Windows si están ocupados o bloqueados.
- **Conservado:** juego activo, telemetría real, FPS N/A sin fuente directa, paletas, sidebar, limpieza, tweaks y CorePulse AI.
- **Corrección adicional:** el sondeo de juegos ahora tiene consumidores independientes (Centro de salud y Overlay) para que dejar una pantalla no apague el detector de la otra.
- **Modificados:** `main.py`, `core/health/performance.py`, `ui/OverlayPage.qml`, `ui/Main.qml`, `tests/test_rebuild.py`, `README.md`, `versiones/HISTORIAL.md`. **Nuevo:** `core/overlay.py`.
- **Pendiente:** verificar visualmente el OSD en RTSS real, el arranque y los atajos con un juego compatible en Windows 11. No está confirmado en un equipo con RTSS desde el entorno de pruebas.

## REBUILD 067 — Sidebar limpio y Overlay inicial (13-10-2026)

- **Base:** REBUILD 066 «Fondo real + colores sobrios + diagnóstico».
- **Sidebar colapsado:** se retira el recuadro pequeño interno de los íconos al usar la barra lateral cerrada. Ahora, al seleccionar o pasar el mouse, queda solo el contenedor grande exterior, como pidió el usuario.
- **Overlay:** se implementa el módulo `Overlay` dentro de “Más módulos”. Esta primera versión muestra una vista previa funcional con telemetría real (CPU/GPU/RAM/VRAM), juego activo detectado y regla `REAL_FPS_OR_NA_ONLY` para FPS.
- **Controles del overlay:** incluye modo compacto/extendido, posición en las cuatro esquinas y opción para mostrar u ocultar temperaturas en la vista previa.
- **Fondo base:** se corrige el degradado del shell para que quede fijo sobre el fondo original de CorePulse y no vuelva a contaminarse con tonos del tema activo.
- **Modificados:** `ui/Main.qml`, `README.md`, `versiones/HISTORIAL.md`, `tests/test_rebuild.py`. **Añadidos:** `ui/OverlayPage.qml`. **Eliminados:** 0 archivos.

## REBUILD 066 — Fondo real, colores sobrios y diagnóstico (13-10-2026)

- **Base:** REBUILD 065 «Gráfico Fluido + Chat Ampliado». Antes de modificar se releen `Reglas para crear Versiones nuevas.txt` y este historial.
- **Fondo del shell:** se recupera la apariencia base pedida por el usuario: degradado oscuro real de CorePulse con salida violeta inferior. El fondo deja de depender del tema activo; los temas editan paneles, sidebar y acentos **sobre ese fondo**.
- **Paletas:** se sustituyen los acentos anteriores por una colección nueva de tonos más oscuros y menos brillantes. Se conservan 10 temas, pero con contraste más sobrio y consistente.
- **Diagnóstico:** `Iniciar diagnóstico` deja de ser un placeholder y pasa a ser una pantalla funcional con resumen de `systemHealth`, cobertura, conteo de alertas y accesos directos a Centro de salud / Lecturas / Windows / Rendimiento.
- **Resumen:** `Salud del sistema` y `Alertas` ya no quedan en `N/A` por defecto; se alimentan del consolidado real del diagnóstico ya disponible en el proyecto.
- **Modificados:** `main.py`, `ui/Main.qml`, `ui/Overview.qml`, `README.md`, `versiones/HISTORIAL.md`, `tests/test_rebuild.py`. **Añadidos:** 0 archivos. **Eliminados:** 0 archivos.
- **Preservado:** gráfico fluido, chat ampliado, cuenta web, Centro de salud, Limpieza, Tweaks, tray y arquitectura compacta sin archivos extra.
- **Pendiente:** validar visualmente en Windows los nuevos tonos y el flujo del diagnóstico para confirmar que la lectura del usuario coincide con la referencia final.

## REBUILD 040 — Centro de Salud: Reparación de Windows (11-10-2026)

- **Base:** REBUILD 039. Leídos previamente el TXT de reglas y el historial. TXT conservado byte por byte. Referencia histórica V485 `windows_repair.py` sin copiar infraestructura obsoleta.
- **Nuevo módulo:** Reparación de Windows con dos acciones manuales (diagnóstico DISM CheckHealth + ScanHealth y SFC VerifyOnly; reparación DISM RestoreHealth + SFC ScanNow + verificación DISM). Requiere confirmación explícita y administrador; no modifica el sistema al abrir. Ejecución en trabajador, avance por etapa, retorno real, clasificación conservadora, log local. Reparación del sistema no equivale a revertir Tweaks.
- **Visual:** las cuatro tarjetas de Análisis de Windows se compactaron y los botones Ver detalles se acercaron a sus datos. Ventana de confirmación comparte fondo y borde del software.
- **Añadido:** `core/health/repair.py` (uno). **Modificados:** `main.py`, `ui/Main.qml`, `ui/HealthPage.qml`, `tests/test_rebuild.py`, `README.md`, `versiones/HISTORIAL.md`. **Eliminados:** 0; sin código de compatibilidad antiguo. 31 archivos en ZIP.
- **Preservados:** motores Batería/Almacenamiento/Windows lectura, Limpieza, Tweaks y telemetría, rótulos, barra lateral y arranque automático.
- **Seguridad:** sólo comandos DISM/SFC literales en lista cerrada, sin shell y sin autoelevación. No se promete rollback de reparaciones; no se inventan porcentajes de DISM.
- **Pendiente:** pruebas reales de elevación y procesos DISM/SFC en Windows 11, y renderizado QML/DPI.
- **Reversión:** conservar ZIP V039 externo.

## REBUILD 039 — Centro de Salud: Análisis de Windows (11-10-2026)

- **Base y reglas:** REBUILD 038; leídos íntegramente `Reglas para crear Versiones nuevas.txt` y `versiones/HISTORIAL.md` antes de implementar. Reglas TXT conservadas byte por byte.
- **Referencia histórica:** V485 (`windows_health.py`, funciones de inicio/servicios/eventos/controladores). Nueva implementación compacta y de solo lectura dentro de la arquitectura Qt actual; no se arrastra el árbol antiguo.
- **Nueva tercera pestaña:** «Análisis de Windows» al lado de Batería (solo portátiles) y Almacenamiento. Conserva las tarjetas oscuras, acento turquesa, botón Actualizar y detalles plegables.
- **Datos:** entradas de inicio `Win32_StartupCommand`; inventario de servicios `Win32_Service`; hasta 80 errores/críticos recientes de Sistema/Aplicación con `Get-WinEvent` (últimos 7 días); incidencias de dispositivos PnP `Win32_PnPEntity.ConfigManagerErrorCode`. Una fuente fallida se representa `N/A`, no como sistema sano. No se leen comandos de inicio ni mensajes de eventos. No se equipara servicio automático detenido a fallo, ni código PnP a actualizaciones disponibles.
- **Seguridad/rendimiento:** consultas independientes dentro de PowerShell con errores aislados; trabajador único asíncrono, tiempo límite 45 s, consulta diferida hasta abrir la pestaña y actualización periódica a 5 min, salida limitada, sin Windows write, sin instalar/reparar drivers, sin deshabilitar servicios o programas de inicio, sin cambios al Registro.
- **Añadido:** `core/health/windows.py`. **Modificados:** `main.py`, `ui/Main.qml`, `ui/HealthPage.qml`, `tests/test_rebuild.py`, `README.md`, `versiones/HISTORIAL.md`. **Eliminados:** ninguno; no se generaron stubs ni implementaciones descartadas. 30 archivos en la versión completa.
- **Preservados:** Batería/Almacenamiento, autonomía, Tweaks, Limpieza, telemetría, arranque automático, UI de las otras pestañas y reglas. **Pruebas:** suite anterior actualizada más análisis/seguridad/regresión; QML y fuentes nativas deben verificarse en Windows real.
- **Reversión:** ZIP REBUILD 038 externo; no hay cambios del sistema que restaurar.

## REBUILD 038 — Centro de Salud: autonomía y almacenamiento (11-10-2026)

- **Base:** REBUILD 037; se leyeron las reglas TXT y el historial completo antes de modificar el proyecto. Reglas originales preservadas.
- **Batería:** autonomía mediante Windows real (`psutil`), respaldo de tasa de descarga `BatteryStatus` por `root/wmi` en trabajador (mWh/mW) y última alternativa basada en caída porcentual observada >=1 punto durante >=5 min; cada valor derivado se etiqueta como estimación. Sin historial válido o tasa fiable permanece N/A. En corriente se muestra su estado. No mezcla baterías distintas.
- **Detección:** no mostrar Batería como módulo en un equipo sin batería real; el Centro de Salud presenta Almacenamiento. El usuario puede seleccionar Almacenamiento también en portátil. No infiere desktop por modelo ni fabricantes.
- **Almacenamiento:** inventario de unidades fijas y espacio disponible/ocupado desde Windows, estado físico CIM `MSFT_PhysicalDisk` independiente del porcentaje usado. Estados desconocidos = N/A, no se inventa SMART/desgaste; es solo lectura.
- **Añadido:** `core/health/storage.py` (módulo independiente). **Modificados:** `core/health/battery.py`, `ui/HealthPage.qml`, `ui/Main.qml`, `main.py`, `tests/test_rebuild.py`, `README.md`, `versiones/HISTORIAL.md`. No hay archivos obsoletos nuevos ni modificaciones de los motores principales.
- **Pruebas:** regresión más escenarios de tasa de descarga real, muestra insuficiente, varias baterías, salud física desconocida y navegación sin batería; sintaxis Python, integridad ZIP. **Pendiente:** comprobar lecturas reales WMI, disco y renderizado QML en un portátil desconectado y una torre Windows 11.
- **Reversión:** usar REBUILD 037 (lecturas de solo diagnóstico, sin cambios del sistema).

## REBUILD 037 — Recuperación de capacidades/ciclos de batería desde V485 (11-10-2026)

- **Base:** REBUILD 036 y módulo real de batería de CorePulse V485. Se leyeron el TXT de reglas y el historial íntegros antes de realizar cambios; TXT original conservado literalmente.
- **Problema:** batería detectada y porcentaje real, pero capacidad de diseño, capacidad plena, ciclos y salud en N/A cuando las clases CIM del fabricante no devuelven datos.
- **Solución:** sumar como respaldo `powercfg /batteryreport /xml`, tal como hacía V485, procesando exclusivamente las baterías instaladas, con parseo XML compatible con namespaces. Archivo temporal de nombre único eliminado en `finally`, límite de tamaño, timeout y ejecución en el hilo existente. La operación no cambia ajustes ni planes de energía.
- **Política de seguridad:** no cruzar capacidades de baterías distintas ni calcular una salud sin un par completo de capacidades. Reportes de múltiples baterías se agregan solo si todas tienen datos verificables; los ciclos por batería no se suman. Compatibilidad REAL_OR_NA conservada.
- **UI:** al estar conectado a corriente, autonomía muestra el estado explícito en vez de N/A. Fuente de capacidad disponible en detalle técnico; geometría, tarjetas, colores, sidebar y resto del software intactos.
- **Modificados:** `core/health/battery.py`, `ui/HealthPage.qml`, `ui/Main.qml`, `tests/test_rebuild.py`, `README.md`, `versiones/HISTORIAL.md`. **Añadidos o eliminados:** 0 archivos, 0 `.py` nuevos.
- **Verificación:** suite de regresión más tests XML (namespace, una/dos baterías, ciclos, errores, combinación de fuentes), `py_compile`, contenido ZIP. **Pendiente:** comprobar reporte real powercfg y las lecturas en Windows 11, especialmente equipo Lenovo con datos CIM incompletos. No se prometen lecturas no proporcionadas por Windows.
- **Reversión:** conservar ZIP REBUILD 036.

## REBUILD 036 — Centro de Salud: batería real (11-10-2026)

- **Base:** REBUILD 035 con arranque automático. Leídos el TXT obligatorio y el historial antes del desarrollo.
- **Alcance:** primera pestaña funcional de Centro de Salud, exclusivamente Batería; se conserva el resto de las páginas y sus diseños. Acceso desde «Centro de salud» y desde «Batería» en módulos adicionales.
- **Datos reales:** estado de energía, porcentaje de carga y autonomía reportados por Windows (`psutil.sensors_battery`, API nativa), actualizados cada tres segundos; capacidades de diseño/plena carga y ciclos mediante clases CIM `BatteryStaticData`, `BatteryFullChargedCapacity` y `BatteryCycleCount` en `root\wmi`, con `Win32_Battery` como identificación y respaldo de capacidades cuando ofrece ambos valores y solo hay una batería. Ejecutado en hilo independiente con timeout.
- **Salud:** `capacidad plena / capacidad de diseño × 100` únicamente si Windows devuelve capacidades válidas y correlacionables por `InstanceName`; desgaste calculado únicamente a partir de esos dos datos, nunca de la carga. Varias baterías requieren pares completos. Sin sensor -> `N/A`, PC sin batería -> aviso explícito, y autonomía no calculada artificialmente.
- **Seguridad:** SOLO LECTURA; sin modificar batería, firmware, planes de energía ni registros. Consulta opcional PowerShell CIM no necesita administrador; no se envía telemetría externa. No se requieren dependencias nuevas.
- **Diseño:** `ui/HealthPage.qml` integrado a paleta oscura `#1A1C26` / borde `#303647`, acento turquesa, tarjeta de carga con anillo de datos reales, tarjeta independiente de salud y bloques de capacidades, ciclos y autonomía; interfaz adaptable y desplazable.
- **Añadidos:** `core/health/__init__.py`, `core/health/battery.py` y `ui/HealthPage.qml`; sin archivos obsoletos. **Modificados:** `main.py` (bridge y cierre), `ui/Main.qml` (routing/rótulo 036), `tests/test_rebuild.py`, `README.md`, este historial. TXT y motores existentes intactos.
- **Pruebas:** contratos antiguos + nuevos sobre correlación de baterías, N/A y renderizado estático QML; compilación Python e integridad del ZIP. **Pendiente:** verificar PowerShell CIM y QML visual en Windows 10/11 y equipo sin batería.
- **Reversión:** conservar ZIP REBUILD 035. Ningún ajuste de Windows es modificado.

## REBUILD 035 — Dependencias automáticas al ejecutar main.py (11-10-2026)

- **Base:** REBUILD 034. Antes del cambio se leyeron las reglas TXT y el historial íntegro. TXT obligatorio conservado literalmente.
- **Problema:** en un PC con Python 3.12 pero sin PySide6, main.py terminaba indicando instalar manualmente `pip -r requirements.txt`; ejecutar ese comando desde una carpeta superior provocaba `No such file or directory`.
- **Solución:** `main.py` detecta su propio directorio mediante `Path(__file__).resolve()`, localiza el manifiesto sin depender del directorio actual, crea un `venv` exclusivo en `%LOCALAPPDATA%\CorePulse\runtime` (por ABI x64 y hash de requirements), instala los paquetes con pip usando la ruta absoluta, valida imports de PySide6.QtCore/QtGui/QtQml y psutil y las distribuciones pythonnet/HardwareMonitor, y relanza automáticamente la aplicación con el intérprete aislado.
- **Fiabilidad:** reintenta una instalación interrumpida, evita instalaciones simultáneas mediante bloqueo de carpeta, no declara listo un runtime defectuoso, reutiliza el entorno en aperturas siguientes, no actualiza pip global ni modifica la instalación principal de Python. Sanea variables de entorno Qt/Python heredadas de otras instalaciones.
- **Limitaciones explícitas:** requiere Python 3.12 x64 y Windows 10/11, Internet en el primer arranque y acceso a PyPI; no pretende instalar el propio Python ni garantizar las DLL/controladores nativos de otros fabricantes. El arranque Qt definitivo debe probarse en Windows real.
- **Modificados:** `main.py`, `Iniciar_CorePulse.bat`, `ui/Main.qml` (solo numeración), `tests/test_rebuild.py`, `README.md`, `versiones/HISTORIAL.md`. **Añadidos/eliminados:** ninguno en el ZIP. **Sin cambios:** algoritmos RAM, Tweaks, telemetría, QML visual, reglas y requisitos de paquetes.
- **Pruebas:** contratos previos + pruebas del bootstrap (ruta CWD independiente, primera instalación, caché y reintento por fallo), compilación Python, integridad del ZIP. Sin descargas de pip durante tests; validación nativa Windows pendiente.
- **Reversión:** conservar V034 como respaldo. El entorno virtual está fuera de la carpeta CorePulse y no modifica respaldos de Tweaks.

## REBUILD 034 — Anclajes de ThinScroll y cuadros visuales unificados (11-10-2026)

- **Base:** REBUILD 033. Se leyeron íntegramente las reglas TXT y el historial; TXT conservado sin cambios.
- **Fallo reportado:** QML ThinScroll en Tweaks advertía repetidamente `Cannot anchor to an item that isn't a parent or sibling`.
- **Causa:** el `ThinScroll` estaba anidado dentro de un `Flickable`. Este reubica hijos declarativos en su `contentItem`, rompiendo la relación de parentesco requerida por los anclajes hacia el propio Flickable.
- **Solución:** `Flickable` y `ThinScroll` como hermanos dentro de un `Item` del Layout, con anclajes de barra a `parent`. Aplicado a Tweaks, Detalle de componentes y Lecturas disponibles. Limpieza ya tenía ambas piezas como hermanos y no requería modificación. Sin cambio de paleta, geometría o datos de lectura de barras.
- **Cuadros de Limpieza:** los cuadros de confirmación, progreso, error y éxito ahora reutilizan un único componente interno `ModalSurface` con fondo `#1A1C26`, borde `#303647`, radio 19 y un solo overlay neutro. Se retiran tonos azulados y bordes dobles ajenos a las tarjetas; el medidor turquesa y el ticket verde de éxito permanecen. Botones con hover oscuro coherente con el programa, sin blanco nativo.
- **Modificados:** `ui/TweaksPage.qml`, `ui/ComponentDetail.qml`, `ui/Main.qml`, `ui/CleanupPage.qml`, `tests/test_rebuild.py`, `README.md`, `versiones/HISTORIAL.md`. **Añadidos/eliminados:** ninguno. Motores Python intactos.
- **Pruebas:** suite automatizada y prueba de regresión de jerarquía de barras, compilación Python, integridad ZIP y comparación diferencial. **Pendiente:** validación gráfica real PySide6/QtQuick sobre Windows 11.
- **Reversión:** retornar al ZIP REBUILD 033; no hay migración de datos.

## REBUILD 033 — Paleta del monitor de RAM integrada con CorePulse (11-10-2026)

- **Base:** REBUILD 032. Reglas TXT e historial leídos previamente; TXT preservado literalmente.
- **Pedido:** retirar el celeste del cuadro de medidor que se abre tras pulsar limpiar RAM; conservar diseño y operaciones.
- **Diseño:** fondo del popup `page.surface` (`#1A1C26`) y borde `page.edge` (`#303647`); anillo, barra, icono y etiquetas acentuadas con el turquesa existente `#4EDDC8`. Se retiran del popup los tonos celestes `#68C9F5`, `#76D8ED` y `#77C6FF`. El overlay oscuro, mediciones y tamaño permanecen.
- **Modificados:** `ui/CleanupPage.qml`, `ui/Main.qml` (rótulo 033), `tests/test_rebuild.py`, `README.md`, `versiones/HISTORIAL.md`. **Añadidos/eliminados:** ninguno. Se sustituyen los colores antiguos obsoletos del popup; no se mantienen temas duplicados.
- **Preservado:** medidor real, backend RAM, standby, caché/DNS/Papelera, Tweaks, Resumen, diálogos de confirmación y modelo de telemetría.
- **Pruebas:** contratos QML, suite automatizada, sintaxis de Python, integridad de ZIP y revisión diferencial. **Pendiente:** ejecutar QML visualmente en Windows 11.
- **Reversión:** restaurar ZIP REBUILD 032 (no cambia datos persistentes).

## REBUILD 032 — Corrección de advertencias QML y layout (11-10-2026)

- **Base:** REBUILD 031. Leídos `Reglas para crear Versiones nuevas.txt` y `versiones/HISTORIAL.md`; TXT obligatorio conservado byte por byte.
- **GridLayout:** se reemplazan anchuras ligadas a `primary.width` por el ancho exterior de `page`; se mantienen proporción 70/30, filas adaptativas y geometría visual del Resumen. Objetivo: evitar `Detected recursive rearrange`.
- **Datos nulos:** protección de accesos a `telemetry.metrics` y `cleanup.data` en Resumen, Detalle de componentes, Lecturas y Limpieza durante inicio/cierre, manteniendo REAL_OR_NA.
- **Barras de desplazamiento:** eliminado el `ScrollBar` nativo personalizado que provocaba avisos de controles Windows (`background`/`contentItem`). Se reutiliza `ui/ThinScroll.qml` en Tweaks, Detalle, Lecturas y Limpieza; esta última pasa a `Flickable`. No requiere cambiar el estilo de Qt.
- **Archivos modificados:** `ui/Overview.qml`, `ui/Main.qml`, `ui/ComponentDetail.qml`, `ui/TweaksPage.qml`, `ui/CleanupPage.qml`, `tests/test_rebuild.py`, `README.md`, `versiones/HISTORIAL.md`. **Añadido:** `ui/ThinScroll.qml`, componente reutilizable. **Eliminado:** uso obsoleto de scrollbars Windows personalizados; ningún `.py` adicional.
- **Sin cambios:** motores de Tweaks y Limpieza, API de telemetría, estilos de tarjetas y navegación; rótulo visible actualizado a REBUILD 032.
- **Pruebas:** contratos automatizados, compilación Python, revisión de ZIP y comparativo de los motores intactos. **Pendiente:** ejecución/renderizado QML real y validación final de ausencia de advertencias en Windows 11.
- **Reversión:** regresar al proyecto completo REBUILD 031; no afecta backups persistentes ni revierte borrados de archivos del usuario.

## REBUILD 031 — Limpieza de caché, Papelera y DNS (11-10-2026)

- **Base:** REBUILD 030. Leído `Reglas para crear Versiones nuevas.txt` y el historial anterior; TXT preservado byte por byte.
- **Problema en video:** la tarjeta Temp del REBUILD 030 solo ofrecía limpieza de archivos antiguos; carecía de limpieza separada de cachés de Windows. Un resultado `0.0 MB` en Temp no representa la caché del sistema.
- **Nuevo motor de caché:** ubicaciones regenerables del perfil (`D3DSCache`, NVIDIA DX/GL, AMD DX, miniaturas Explorer) con inventario real, comprobación de rutas y enlaces, revalidación de tamaño/mtime antes de cada eliminación, omisión de archivos bloqueados y reanálisis de lo restante. No se eliminan carpetas ni documentos.
- **Papelera:** consulta de archivos y espacio por Shell32 `SHQueryRecycleBinW`, confirmación de borrado permanente y `SHEmptyRecycleBinW`; se vuelve a consultar tras la operación. No afecta Descargas ni documentos fuera de la Papelera.
- **DNS:** `ipconfig /flushdns` con timeout y comprobación del código de salida. Estado por tarjeta; no se presenta un ahorro inventado en MB.
- **Temporales:** tras borrar se vuelve a escanear para no mostrar cero si permanecen archivos no eliminables. Se conservan el límite de inventario, la antigüedad de 24 horas y la confirmación.
- **UI:** 3 tarjetas minimalistas, controles adaptables y confirmaciones oscuras; los botones y los resultados de RAM no cambian.
- **Modificados:** `core/maintenance/cleanup.py`, `ui/CleanupPage.qml`, `ui/Main.qml`, `tests/test_rebuild.py`, `README.md`, `versiones/HISTORIAL.md`. **Añadidos/eliminados:** ningún archivo de producción; sin código muerto ni rutas heredadas.
- **Pruebas:** suite REBUILD, comprobación de borrado sobre fixtures, aislamiento de rutas, omisiones por cambio concurrente, respuesta DNS y API de Papelera simulada, compilar Python e integridad ZIP. Falta ejecución Qt en Windows y test real de Shell32/DNS.
- **Reversión:** usar REBUILD 030 para el proyecto; vaciar la Papelera no es reversible con el ZIP.

## REBUILD 030 — Limpieza minimalista y resultados bajo demanda (11-10-2026)

- **Base:** REBUILD 029. Se leyeron el TXT de reglas y el historial antes de cambiar código. Se conserva el TXT literal.
- **Objetivo:** eliminar la franja permanente "Estado de limpieza" y reducir drásticamente texto de la tarjeta de memoria, conforme a la grabación del usuario.
- **UI:** `ui/CleanupPage.qml` ahora solo muestra un estado compacto mientras hay trabajo, o cuando falla la limpieza de temporales. Tarjeta RAM con nombre y descripción breves, resumen de la última variación de memoria disponible y botón contextual "Ver detalles" plegado por defecto. Los dos botones de RAM, diálogos oscuros, medidor real, ticket de confirmación y errores de permisos se conservan.
- **Fuente de verdad:** `core/maintenance/cleanup.py` conserva el último modo RAM completado con éxito en `lastRamKind`, evitando perder el resumen al analizar temporales. No cambia algoritmos de limpieza, privilegios ni el muestreo real.
- **Modificados:** `ui/CleanupPage.qml`, `core/maintenance/cleanup.py`, `ui/Main.qml` (etiqueta 030), `tests/test_rebuild.py`, `README.md`, `versiones/HISTORIAL.md`. **Añadidos/eliminados:** ninguno en producción.
- **Pruebas:** compilación Python, pruebas automatizadas y verificación del ZIP. Pendiente probar apariencia QML y operaciones Windows 11 in situ.
- **Reversión:** reemplazar el proyecto con el ZIP completo de REBUILD 029; sin migración de respaldos o cambio de datos de Windows.

## REBUILD 029 — Medidor de RAM real durante limpieza (11-10-2026)

- **Base:** REBUILD 028, reglas TXT e historial revisados antes de modificar.
- **Modificados:** `core/maintenance/cleanup.py`, `ui/CleanupPage.qml`, `ui/Main.qml`, `tests/test_rebuild.py`, `README.md`, `versiones/HISTORIAL.md`.
- **Medidor:** aparece al iniciar limpieza completa (confirmada) o standby; muestra RAM ocupada, total, disponible, porcentaje y variación frente al comienzo. Lectura física única desde `psutil.virtual_memory()` cada ~280 ms mientras se ejecuta el Future en un hilo independiente. Sin valores interpolados de telemetría ni promesas de reducción.
- **Diseño:** popup modal centrado, overlay oscuro con profundidad, anillo y barra de uso RAM, valores antes/ahora y cambio observado. La animación suaviza solo el trazo visual; cifras obtenidas de lecturas reales. No se puede cerrar mientras trabaja.
- **Finalización:** cierra el medidor al finalizar; conserva la confirmación verde ya aprobada solo con resultados positivos reales. Si la operación falla, informa en un diálogo oscuro ámbar, sin ticket de éxito.
- **Sin cambios:** algoritmo de limpieza profunda/standby, motor Tweaks, Resumen y estructura de carpetas. Sin nuevos archivos Python ni QML de producción. La variación de RAM puede deberse también a otras aplicaciones.
- **Validación:** pruebas Python y contratos QML; el renderizado Qt y el vaciado privilegiado requieren validación en Windows 11.

## REBUILD 028 — Hover, diálogos y confirmación real de RAM (11-10-2026)

- **Modificados:** `ui/CleanupPage.qml`, `ui/Main.qml`, `core/maintenance/cleanup.py`, `tests/test_rebuild.py`, `README.md`, `versiones/HISTORIAL.md`.
- **Correcciones:** botones no blancos al pasar el mouse, diálogos centrados en la ventana con overlay oscuro translúcido, acciones alineadas.
- **Nueva confirmación:** cuadro de éxito cuadrado con ticket verde rodeado de círculo verde para resultados reales de RAM. No se muestra con errores ni cancelaciones.
- **Alcance:** diseño y comunicación de resultado; sin cambiar el algoritmo de limpieza profunda ni Tweaks.
- **Pendiente:** verificación en Windows de renderizado Qt y operaciones nativas.

## REBUILD 027 — Organización de módulos Python (11-10-2026)

- **Base:** REBUILD 026. Se leyó y preservó íntegramente el TXT de reglas y el historial previo.
- **Alcance:** únicamente reorganización de archivos Python por responsabilidad; conserva todas las pantallas QML, su geometría y las operaciones existentes de telemetría, Tweaks y Limpieza. Rótulo de versión actualizado a 027.
- **Movidos:** `telemetry.py` → `core/monitoring/telemetry.py`; `tweaks.py` y `tweaks_engine.py` → `core/tweaks/`; `cleanup.py` → `core/maintenance/cleanup.py`. Se mantienen separados puente y motor de Tweaks por su responsabilidad independiente.
- **Añadidos:** cuatro `__init__.py` mínimos para paquetes Python. **Eliminados de raíz:** los cuatro archivos reubicados; queda `main.py` como único lanzador. Sin stubs ni copias duplicadas.
- **Modificados:** `main.py` (imports), `core/tweaks/tweaks_engine.py` (raíz de proyecto compatible con los snapshots anteriores), `ui/Main.qml` (etiqueta), pruebas de estructura y rutas, `README.md` y este historial.
- **Persistencia:** no cambia `%APPDATA%` ni `%LOCALAPPDATA%`, y la ruta heredada `data/windows_tweaks_state.json` sigue resolviendo desde la raíz original.
- **Validación:** suites automatizadas y compilación del código Python; ejecución nativa de UI/operaciones privilegiadas pendiente de Windows. **Reversión:** restaurar ZIP REBUILD 026 sin borrar respaldos persistentes.

## REBUILD 026 — Limpieza profunda de RAM y ajuste de interfaz (11-10-2026)

- **Base:** REBUILD 025. Referencia del motor V485 en `ram_optimizer.py`; integración de operaciones intensivas en `cleanup.py` sin copiar módulos completos.
- **RAM:** nuevo método `optimize_ram_deep()` con recorte de working sets externos accesibles, listas de memoria y caché del sistema, con permisos y reporte por operación. Se conserva botón standby separado. Confirmación explícita y medición antes/después; sin promesa de 99 %.
- **QML:** rectángulo de estado con altura dinámica; tarjetas más altas para el texto; diseño de confirmación profundo; barra de acciones separada.
- **Modificados:** `cleanup.py`, `ui/CleanupPage.qml`, `ui/Main.qml`, `README.md`, `tests/test_rebuild.py`, `versiones/HISTORIAL.md`. **Sin nuevos archivos de producción.** Se elimina `optimize_ram_safe` y su slot, por quedar obsoletos en esta interfaz.
- **Advertencia:** el trim externo y vaciado de cachés pueden inducir paginación o lentitud; uso manual con confirmación, no automático.
- **Pendiente:** prueba de ejecución nativa con administrador en Windows 11 y comprobación visual en DPI distintos.

## REBUILD 025 — Botones separados de RAM (11-10-2026)

- Base: REBUILD 024. Referencia: optimización segura del motor V485.
- Modificados: `cleanup.py`, `ui/CleanupPage.qml`, `ui/Main.qml`, `README.md`, `tests/test_rebuild.py`, `versiones/HISTORIAL.md`. Sin archivos nuevos de producción ni código obsoleto añadido.
- Se agrega botón **Limpiar RAM** junto a **Limpiar RAM standby**. Optimización segura mediante `gc.collect()` y `EmptyWorkingSet` limitados a CorePulse, sin alterar memoria privada de otros procesos. Resultado de diferencia global mostrado como medición, no como causalidad.
- Se mantiene purga de standby separada con privilegio temporal; controles desactivados durante tareas.
- Pruebas automatizadas y compilación; falta validar renderizado y efectividad en Windows 11. Reversión: conservar ZIP 024.

## REBUILD 024 — Privilegio RAM y controles de Limpieza (11-10-2026)

- **Base:** REBUILD 023; revisión del TXT obligatorio y del historial.
- **Motor:** `cleanup.py` habilita temporalmente `SeProfileSingleProcessPrivilege` usando el token del proceso, comprueba `ERROR_NOT_ALL_ASSIGNED`, ejecuta la purga standby y restituye el estado previo del privilegio incluso al fallar la operación.
- **Diseño:** `ui/CleanupPage.qml` sustituye botones blancos del estilo Qt por controles oscuros con acentos ámbar/azul/cian, confirma eliminación mediante diálogo personalizado y conserva distribución de tarjetas.
- **Versión:** `ui/Main.qml` actualiza rótulos a REBUILD 024.
- **Modificados:** `cleanup.py`, `ui/CleanupPage.qml`, `ui/Main.qml`, `README.md`, `tests/test_rebuild.py` y este historial. **Añadidos/eliminados:** ninguno.
- **Validación:** pruebas automatizadas y compilación; pendiente validación visual y purga nativa en Windows 11 (incluido token elevado).
- **Reversión:** conservar ZIP REBUILD 023 como respaldo. Ninguna operación elimina memoria privada de procesos.

## REBUILD 023 — Corrección de sintaxis de Limpieza (11-10-2026)

- **Base:** REBUILD 022; corrección puntual del fallo de arranque reportado en Windows al cargar `CleanupPage.qml:53:116` (`Unexpected token ;`).
- **Modificado:** `ui/CleanupPage.qml`: se retira el separador inválido entre dos objetos `Text` hermanos dentro de `RowLayout`, conservando distribución, estilos, lógica y controles; se normaliza la indentación de la propiedad `info`.
- **Pruebas:** `tests/test_rebuild.py` incluye regresión contra separadores inválidos entre elementos QML. Se valida la suite Python y la integridad del ZIP; el arranque nativo QML en Windows sigue pendiente de comprobar por el usuario.
- **Sin cambios:** motor de RAM/temporales, navegación, Tweaks, telemetría, reglas literales y demás interfaces. No se agregan archivos Python de producción.

## REBUILD 022 — Limpieza de sistema y RAM standby (11-10-2026)

- Base REBUILD 021. Se añade sección funcional de Limpieza, sin cambiar Resumen, Tweaks ni geometría aprobada.
- Añadidos: `cleanup.py` (operaciones reales aisladas y asíncronas) y `ui/CleanupPage.qml` (interfaz de limpieza).
- Modificados: `main.py`, `ui/Main.qml`, `tests/test_rebuild.py`, `README.md`, este historial.
- Temporales: analiza archivos de más de 24 horas en la carpeta Temp local del usuario, no sigue symlinks, limita recorrido, valida de nuevo antes de borrar, omite archivos bloqueados y exige confirmación explícita. Es eliminación permanente.
- RAM: llamada nativa `NtSetSystemInformation` clase 80, `MemoryPurgeStandbyList` valor 4; muestra RAM disponible antes, después y diferencia medidas por psutil. No garantiza 99 % ni libera memoria activa; puede fallar por privilegios.
- Ambas tareas se ejecutan en un hilo de trabajo; Qt publica resultado a través de polling de future en hilo principal.
- Pruebas: verificar contratos, compilación y aislamiento de ruta; validación nativa de Windows y permisos pendiente.
- Reversión del software: conservar el ZIP 021. Archivos borrados no son recuperables automáticamente: se advierte antes de confirmar.
- `cleanup.py` es el único nuevo Python y separa responsabilidad de escritura del módulo de telemetría (solo lectura).

## REBUILD 021 — Ampliación real del motor de Tweaks con V485 (11-10-2026)

- Base REBUILD 020; referencia CorePulse V485 del usuario. No se altera geometría, colores ni navegación.
- Añadido `tweaks_engine.py`: motor V485 adaptado sin dependencia de la estructura anterior, detección por objetivos, backups persistentes, aplicación y reversión verificada para tweaks adicionales cuando sean compatibles.
- Modificados `tweaks.py` (puente de las 44 entradas antes bloqueadas), `ui/TweaksPage.qml` (contador de disponibilidad real y textos de confirmación), `tests/test_rebuild.py`, `README.md`, historial.
- Siguen habilitados los 34 ajustes HKCU del motor REBUILD 020, manteniendo sus respaldos. El nuevo motor administra otros tweaks independientemente para evitar migraciones destructivas de snapshots.
- Bloqueadas nuevas aplicaciones de desinstalaciones sin rollback determinista (3) y desactivación de protecciones críticas/updates (6); su visualización no implica ejecución.
- Limitaciones: elevación automática UAC NO migrada del launcher antiguo; ajustes HKLM requieren ejecutar CorePulse como administrador y confirmar. Validación funcional en Windows 11 real pendiente.
- Eliminados: cachés de build/pruebas del ZIP. Archivo Python agregado: uno, necesario para aislar y auditar el motor V485 sin alterar la aplicación existente.

# CorePulse REBUILD — Historial y control de versiones

**Este es el único registro de versiones dentro del proyecto.** Antes de diseñar, crear, modificar o eliminar CUALQUIER elemento de CorePulse, leer y respetar obligatoriamente [`Reglas para crear Versiones nuevas.txt`](../Reglas%20para%20crear%20Versiones%20nuevas.txt) y este historial. La REBUILD 007 añade explícitamente una regla al TXT por solicitud del usuario; las reglas originales se conservan. Al publicar una entrega, añadir una nueva sección al principio del historial. No crear otra carpeta por versión ni copiar código antiguo dentro del proyecto. Los ZIP de respaldo se guardan fuera de esta carpeta.

## Reglas obligatorias para próximas entregas

1. **Proyecto pequeño y consolidado.** Crear archivos Python solo cuando haya una responsabilidad nueva claramente independiente; preferir mejorar archivos existentes cuando corresponda, sin convertirlos en archivos gigantes. Cada nuevo `.py` requiere justificación en el registro.
2. **Sin restos históricos.** No importar `gui/`, `main_legacy.py`, módulos Qt antiguos, caches, DLL copiadas, scripts obsoletos ni múltiples `.bat`. El REBUILD se desarrolla desde su propia base limpia.
3. **Una fuente de verdad.** Telemetría real o `N/A`, sin inventar sensores, FPS, temperaturas, alertas ni puntuaciones. La UI no modifica Windows; las acciones sensibles futuras requerirán confirmación y reversibilidad cuando aplique.
4. **Conservar lo aprobado.** No modificar diseño, navegación ni comportamientos fuera del alcance solicitado. Reusar componentes y estilos QML. Cada módulo pendiente debe permanecer explícitamente pendiente hasta implementarse.
5. **Control por versión.** Antes de entregar: describir alcance, archivos añadidos/modificados/eliminados, por qué, pruebas y resultados, pendientes conocidos y cómo volver a la versión anterior.
6. **Verificar, no suponer.** Pasar las pruebas posibles, revisar importaciones y arranque, inspeccionar el ZIP, e informar explícitamente lo no comprobado (por ejemplo ejecución visual Windows). No afirmar paridad funcional sin evidencia.
7. **ZIP completo y reproducible.** Distribuir únicamente el nuevo proyecto, sin artefactos locales, resultados temporales ni archivos `__pycache__`.
8. **TXT obligatorio para crear cualquier cosa.** Antes de crear o modificar versiones, archivos, componentes, funciones, diseños, iconos y scripts, leer y respetar íntegramente `Reglas para crear Versiones nuevas.txt` y este historial. El TXT debe viajar siempre en la raíz del ZIP; no cambiar sus reglas sin petición explícita del usuario. Retirar del árbol las copias/versiones obsoletas cuando ya no se usen.

---

## REBUILD 020 — Verificación del Registro al aplicar y restaurar (11-10-2026)

- **Alcance:** para los 34 tweaks ya habilitados, aplicar y restaurar ahora exige volver a leer Windows y confirmar que el Registro conserva el valor solicitado / original. Un fallo de verificación conserva el respaldo y no comunica éxito falso.
- **Sin paridad inventada:** los 44 ajustes restantes permanecen bloqueados hasta implementar operaciones comprobables y reversibles. Verificación del Registro no equivale a certificar efectos visibles en cada build de Windows 11.
- **Modificados:** `tweaks.py`, `tests/test_rebuild.py`, `README.md`, `versiones/HISTORIAL.md`; ningún archivo nuevo de producción, ningún cambio visual.
- **Pruebas:** contratos y casos adicionales de escritura/restauración que no se reflejan en el Registro. Prueba nativa de Windows pendiente.
- **Reversión:** respaldo ZIP REBUILD 019; los valores de `%APPDATA%` conservan compatibilidad de formato.

## REBUILD 019 — Eliminar cuadro de catálogo histórico (11-10-2026)

- **Reglas:** revisado el TXT obligatorio y el historial antes del cambio; ambos se preservan.
- **Alcance:** eliminado exclusivamente el recuadro informativo «Catálogo histórico» situado bajo el encabezado de Tweaks. Se conserva el banner transitorio de resultados de Apply/Restore, que aporta información funcional. No se altera la disposición de tarjetas, sus colores, navegación, ni el contador.
- **Seguridad:** catálogo de 78, 34 ajustes HKCU habilitados y 44 pendientes bloqueados sin cambios; copias originales y reversión conservadas. No se amplían capacidades de escritura.
- **Modificados:** `ui/TweaksPage.qml`, `README.md`, `tests/test_rebuild.py`, `versiones/HISTORIAL.md`. **Agregados o eliminados:** ningún archivo.
- **Pruebas:** comprobar contratos, pruebas automáticas, sintaxis Python y ZIP. Visualización real en Windows 11 pendiente.
- **Reversión:** extraer el ZIP 018 conservado fuera del proyecto; los respaldos del usuario en AppData permanecen compatibles.

## REBUILD 018 — Catálogo original V491 de 78 Tweaks (10-10-2026)

- **Lectura obligatoria previa:** se revisaron `Reglas para crear Versiones nuevas.txt` e historial. Se conserva el TXT íntegro y no se mezclan módulos legacy en el árbol actual.
- **Origen verificado:** RAR `CorePulse_V491_WINDOWS_FLAT_CONTROLS(3).rar`, motor histórico `core/maintenance/windows_tweaks.py`. Se analizaron estáticamente **78 entradas únicas** en 12 categorías. El RAR de origen NO se incluye en el proyecto.
- **Alcance:** 78 opciones visibles, 34 con implementación HKCU/REG_DWORD de una sola operación, no elevadas, de riesgo bajo/medio; 44 bloqueadas por compatibilidad, múltiples acciones, privilegios o riesgos. Esto NO es todavía paridad funcional de 78 tweaks.
- **Diseño:** 12 secciones con colores únicos, estados y explicaciones; el diseño de las tarjetas y navegación conserva la base REBUILD 017.
- **Seguridad:** mantiene confirmación explícita, respaldo del valor original, error cerrado y restauración exacta para los 34 aplicables. Los 44 pendientes son informativos y su ejecución está bloqueada a nivel de motor, no solo en QML. No desactiva protecciones, actualizaciones o servicios.
- **Compatibilidad:** conserva los ocho IDs de REBUILD 017 y la ruta de respaldo de AppData, evitando perder posibilidades de restaurar ajustes previamente aplicados.
- **Modificados:** `tweaks.py`, `ui/TweaksPage.qml`, `README.md`, `tests/test_rebuild.py`, `versiones/HISTORIAL.md`. No se añaden módulos Python ni carpetas del CorePulse V491.
- **Pruebas:** 55 pruebas unitarias automatizadas aprobadas con Registro simulado. No se probó la visualización QML ni la escritura real de Registro en Windows 11 desde este entorno.
- **Pendientes:** migrar de manera individual los 44 ajustes restantes, verificar variantes de Windows 11 y efectos reales; nunca afirmar mejoras de FPS sin mediciones.
- **Reversión:** conservar externamente ZIP 017 y reemplazar la carpeta de 018 por esa versión; respaldo durable por usuario mantenido en `%APPDATA%\\CorePulse\\rebuild\\tweaks_originales.json`.

## REBUILD 017 — Colores de categoría en Tweaks (10-10-2026)

- **Reglas leídas:** `Reglas para crear Versiones nuevas.txt` y este historial de REBUILD 016. TXT preservado byte por byte.
- **Cambio solicitado:** cada sección de Tweaks recibe identidad visual propia: Explorador cian, Barra de tareas violeta y Apariencia ámbar. Colores en cabeceras, líneas, tarjetas activas, estados y botones de aplicación. Contador dinámico de opciones disponibles en el catálogo.
- **Alcance real:** el ZIP base trae **8 tweaks**, no 78. No se agregaron 70 ajustes sin catálogo histórico verificable; la recuperación del conjunto original queda pendiente de disponer de su fuente e inspeccionar su seguridad y reversibilidad.
- **Modificados:** `ui/TweaksPage.qml`, `ui/Main.qml` (solo número de versión), `README.md`, `tests/test_rebuild.py`, `versiones/HISTORIAL.md`.
- **Añadidos/eliminados:** ninguno. `tweaks.py`, `main.py`, `telemetry.py`, resto de UI y TXT permanecen idénticos a la 016. El árbol mantiene 17 archivos.
- **Pruebas:** test de colores, contador y catálogo; regresión de pruebas existentes. No se ha certificado visualmente en Windows 11 desde este entorno.
- **Reversión:** conservar externamente el ZIP REBUILD 016 y reemplazar la carpeta por esa versión; los respaldos de ajustes de Windows siguen en AppData y son compatibles.

## REBUILD 016 — Tweaks Windows 11 funcionales, reversibles y con confirmación (10-10-2026)

- **Reglas revisadas:** leído el TXT `Reglas para crear Versiones nuevas.txt` y el historial antes de trabajar. TXT conservado **byte por byte**; no se incorpora ningún historial de versiones anteriores dentro del ZIP.
- **Referencia antigua:** auditado `core/maintenance/windows_tweaks.py` de CorePulse previo a Qt, conservando únicamente ocho definiciones de ajustes HKCU/REG_DWORD de bajo riesgo. No se copia el motor antiguo ni se reinstalan sus presets, operaciones de administrador o acciones de seguridad.
- **Implementados:** mostrar extensiones, mostrar archivos ocultos, abrir Explorador en Este equipo, vista compacta, alinear barra a la izquierda, ocultar Widgets, ocultar Vista de tareas y reducir transparencias. Solo para Windows 11 detectado; en otros sistemas quedan deshabilitados.
- **Interfaz:** un nuevo `ui/TweaksPage.qml` muestra categorías, estados leídos de Windows, explicación legible, hover, scroll oscuro responsivo, botón Actualizar, Volver y diálogo de confirmación separado para **Aplicar** y **Restaurar**. Ningún ajuste se aplica al abrir la pestaña. No se modifica el Resumen.
- **Motor de operaciones:** se justifica **1 nuevo Python**, `tweaks.py`, porque realiza escrituras del Registro y no corresponde mezclarlo con `telemetry.py` de solo lectura. La capa QML no puede escribir Registro directamente. Respaldos individuales de valores originales en `%APPDATA%\CorePulse\rebuild\tweaks_originales.json`; escritura atómica previa, restauración exacta del REG_DWORD anterior o eliminación de valores inexistentes originalmente; protección contra respaldos corruptos y tipos desconocidos. No se ejecutan scripts remotos, comandos privilegiados, reinicio de Explorer ni modificación de servicios, seguridad o actualizaciones.
- **Modificados:** `main.py` (conexión del nuevo objeto), `ui/Main.qml` (ruta y versión), `tests/test_rebuild.py`, `README.md`, este historial.
- **Añadidos:** `tweaks.py` y `ui/TweaksPage.qml`. **Eliminados:** ninguno; no se crean pruebas, BAT, proveedores o módulos de compatibilidad adicionales. Total **17 archivos**; 3 Python de producción, 8 QML y un BAT.
- **Conservados intactos:** `telemetry.py`, `ui/Overview.qml`, `ui/ComponentDetail.qml`, `ui/Glyph.qml`, gráfico, métricas, tarjetas, geometría y arrastre, `requirements.txt` y reglas TXT.
- **Pruebas:** unitarias del Registro simulado (estado, backup original, idempotencia, restauración, valor inexistente, backup corrupto, sistema no compatible y tipo no esperado), contratos QML y regresión REBUILD anterior. Pendiente comprobación real de efectos del Registro en Windows 11 con las confirmaciones explícitas.
- **Reversión de versión:** conservar fuera del proyecto `CorePulse_REBUILD_015_DETALLES_CLAROS.zip`. Para revertir ajustes aplicados, usar **Restaurar** en la pestaña de Tweaks antes de cambiar de versión; conservar la copia en AppData.

## REBUILD 015 — Componentes detallados y fáciles de entender (10-10-2026)

- **Reglas:** se leyó `Reglas para crear Versiones nuevas.txt` y este historial antes de los cambios. TXT conservado byte por byte. La REBUILD 014 es el respaldo externo, no se incluye en esta carpeta.
- **Referencia visual:** video del usuario comparando REBUILD 014 con CorePulse anterior a Qt. El antiguo mostraba uso, temperatura, frecuencia, potencia, especificaciones y sensores por núcleo. El nuevo separaba todo en una tabla larga; esta versión recupera niveles de información sin volverla demasiado técnica.
- **Pantallas CPU/GPU/RAM:** se reorganiza el único QML compartido `ui/ComponentDetail.qml` con secciones «Ahora mismo», «Cómo interpretarlo», «Conoce tu componente», módulo RAM/adaptadores gráficos y «Detalles avanzados». Por defecto se muestra primero lo esencial, con una frase sencilla por dato. Scroll oscuro responsive y botón Volver. No se duplican pantallas ni Python.
- **CPU:** se añade lectura **opcional** de potencia de CPU Package y temperaturas por núcleo a través de sensores CPU publicados por WMI o de la sonda de HardwareMonitor ya existente. Solo valores medidos válidos, con identificador CPU/hardware tipo CPU (y EC/SuperIO inequívoco en la sonda .NET). Se descartan valores GPU, SSD, cero, inválidos y obsoletos. El listado está limitado a 32 núcleos/sensores para evitar saturación. Nunca se infiere una potencia desde el % de uso.
- **Fuentes:** la procedencia de sensores adicionales (`cpuDetailSource`) queda disponible en detalles avanzados; cuando el proveedor no publica una lectura se indica `N/A`. La frecuencia estimada sigue etiquetada `(est.)`.
- **GPU:** se explica qué mide el uso NVIDIA y se presentan VRAM/capacidad, adaptadores y controlador solo si están disponibles. **RAM:** uso/capacidad/disponible y módulos físicos con capacidad, velocidad y fabricante en lenguaje claro. Los datos provienen de los mismos proveedores reales previos.
- **Modificados:** `ui/ComponentDetail.qml`, `telemetry.py`, `ui/Main.qml` (solo etiqueta de versión), `tests/test_rebuild.py`, `README.md`, este historial.
- **Añadidos/eliminados:** ningún archivo; **15 archivos totales, 2 `.py` de producción, 7 QML, 1 BAT y TXT obligatorio**. Se retiró la presentación antigua de tabla plana del QML, sustituida por el nuevo componente compartido. Nada de carpetas obsoletas o cachés.
- **Protegidos:** `Overview.qml`, `Glyph.qml`, gráfico, métricas principales, geometría/arrastre, navegación, SSD, `main.py`, requisitos y TXT idénticos a REBUILD 014.
- **Pruebas:** 46 contratos automatizados aprobados, validación de valores ausentes, WMI (potencia y sensores por núcleo), separación de CPU/GPU y estabilidad; verificar gráficamente el desplazamiento y los sensores nativos en Windows con PySide6. Es una integración incremental, no certificación de todos los sensores de cualquier portátil.
- **Reversión:** guardar `CorePulse_REBUILD_014_COMPONENTES.zip` fuera de la carpeta del proyecto.

## REBUILD 014 — Detalles de CPU, GPU y RAM desde el Resumen (10-10-2026)

- **Reglas leídas antes de trabajar:** `Reglas para crear Versiones nuevas.txt` y este historial. Se conserva el TXT original de REBUILD 013 exactamente, sin alteraciones.
- **Alcance solicitado:** al hacer clic en el **icono** de CPU, GPU o RAM del panel «Estado del sistema», abrir su pestaña de especificaciones, como sucedía en CorePulse anterior a Qt. No se activó navegación en SSD ni en tarjetas ajenas.
- **Referencia antigua:** páginas históricas `CpuPage.qml`, `GpuPage.qml` y `RamPage.qml` del CorePulse previo; se recupera su objetivo de mostrar identidad, carga, temperatura, memoria y datos de inventario, sin copiar el código viejo ni prometer paridad de todos sus sensores.
- **Navegación/UI:** `ui/MetricLine.qml` añade un botón de icono con hover y cursor de clic, conservando el tooltip existente; `ui/Overview.qml` emite la solicitud de componente; `ui/Main.qml` enruta por identificadores estables `cpu`, `gpu`, `ram`, habilita «Más módulos» y permite volver al Resumen. Se reutiliza **una sola** nueva vista `ui/ComponentDetail.qml` con tarjetas de lecturas y especificaciones adaptables, scroll oscuro y estado `N/A` si faltan sensores.
- **Inventario Windows solo lectura:** `telemetry.py` obtiene una sola vez y en segundo plano CPU (`Win32_Processor`: fabricante, socket, núcleos, hilos), adaptadores gráficos (`Win32_VideoController`: nombre/controlador) y memoria (`Win32_PhysicalMemory`: slot, capacidad, velocidad, tipo SMBIOS, fabricante, referencia). La cantidad de núcleos/hilos puede usar el recuento real `psutil.cpu_count()` como respaldo. Se conserva la RAM en vivo `total - disponible` y la telemetría NVIDIA/NVML ya existente. Solo se asocia un controlador GPU si el nombre coincide explícitamente: no se confunde Intel/AMD/NVIDIA.
- **Seguridad y veracidad:** no instala drivers ni ejecuta mantenimiento; ninguna lectura inventada. Mientras WMI está consultando, el inventario se marca evaluándose; si Windows no expone algo, aparece `N/A`. Las temperaturas/frecuencias mantienen proveedores, caducidad y marcadores de estimación de REBUILD 013.
- **Modificados:** `telemetry.py`, `ui/MetricLine.qml`, `ui/Overview.qml`, `ui/Main.qml`, `tests/test_rebuild.py`, `README.md`, este historial.
- **Añadidos:** `ui/ComponentDetail.qml` (**1 componente QML reutilizable**). **Eliminados:** ninguno; no hay código obsoleto nuevo que duplicar. El proyecto consta de **15 archivos**, **2 Python de producción**, **7 QML**, **1 BAT**, más TXT obligatorio; no se agrega ningún `.py`.
- **Pruebas:** 41 contratos y casos de lectura aprobados, incluidos validación de SMBIOS, inventarios incompletos, no confundir drivers iGPU/dGPU y rutas de navegación; comprobación de integridad del ZIP. La presentación y `Get-CimInstance` deben comprobarse realmente en Windows con PySide6.
- **Reversión:** conservar `CorePulse_REBUILD_013_CPU_TEXTO_SCROLL.zip` fuera de la carpeta.

## REBUILD 013 — Frecuencia legible y scroll de Lecturas disponibles (10-10-2026)

- **Antes de modificar:** se leyeron el TXT obligatorio y este historial; el TXT se conserva byte por byte.
- **Incidencias reproducidas en video de Windows:** el prefijo `≈` junto a la frecuencia de CPU se veía extraño y el scrollbar por defecto aparecía como una barra blanca que tapaba los valores de las lecturas.
- **Cambios funcionales:** solo presentación. La frecuencia estimada se muestra como `4.21 GHz (est.)` en lugar de `≈4.21 GHz`, con el origen «Estimación Windows…» conservado en el tooltip y en la lista. Frecuencia medida continúa sin sufijo. Los cálculos y muestras no cambian.
- **Scroll:** en `ui/Main.qml` se reemplazó la barra visual por defecto por una barra Qt Quick Controls oscura de 9 px y se reservó un canal de 16 px a la derecha del listado, evitando que la barra tape estados o cifras. Mantiene desplazamiento vertical, encabezado fijo y siete filas reales.
- **Modificados:** `ui/Overview.qml`, `ui/Main.qml`, `telemetry.py` (solo etiqueta de las lecturas), `tests/test_rebuild.py`, `README.md` y este historial.
- **Añadidos o eliminados:** ninguno; no se crean archivos `.py` ni QML adicionales, permanecen 14 archivos, 2 Python de producción y 1 BAT. Se eliminó el prefijo de render `≈` y la barra visual por defecto en la pantalla de lecturas.
- **Protegidos:** UI del Resumen, gráficos, iconos, lecturas CPU/GPU/RAM/SSD, contador verificable de siete métricas, hover, navegación, arrastre y tamaño universal.
- **Pruebas:** suite completa del REBUILD y nuevos contratos de representación de frecuencia y scroll. La interacción real y escalado DPI de Qt Windows requieren verificación visual en ese equipo.
- **Reversión:** conservar `CorePulse_REBUILD_012_LECTURAS_DISPONIBLES.zip` fuera de la carpeta del proyecto.

## REBUILD 012 — Lecturas disponibles: detalle interactivo y 7 verificaciones (10-10-2026)

- **Reglas:** se leyeron `Reglas para crear Versiones nuevas.txt` y este historial ANTES de cualquier cambio; el TXT se conserva idéntico al de REBUILD 011.
- **Nombre inalterado por solicitud expresa:** la tarjeta sigue llamándose **«Lecturas disponibles»** (NO «Trazabilidad»). El mismo rótulo encabeza la pantalla de detalle.
- **Alcance:** al pasar el mouse sobre la tarjeta se realzan discretamente color/borde; al pulsarla abre una pantalla que permite verificar las siete lecturas. Volver regresa a Resumen. Las otras tarjetas no ejecutan operaciones ni simulan navegación.
- **Contador real:** se reemplaza el conteo de cuatro indicadores por siete comprobaciones: uso CPU, frecuencia CPU, temperatura CPU, uso RAM, uso GPU, temperatura GPU y uso/capacidad VRAM. `7/7` solo si las siete son válidas; 0 y otros valores son legítimos. El SSD sigue en su bloque, pero NO se cuenta como temperatura/VRAM.
- **Fuente y seguridad:** se reutilizan las lecturas reales existentes y se añade `memory.used,memory.total` de NVIDIA-SMI en la consulta de GPU; se descartan muestras antiguas y valores de VRAM inválidos. Se muestra el origen de cada dato, distinguiendo frecuencia estimada `≈`; estados Disponible/Evaluando/No disponible, sin inventar sensores.
- **Archivos modificados:** `telemetry.py`, `ui/StatTile.qml`, `ui/Overview.qml`, `ui/Main.qml`, `tests/test_rebuild.py`, `README.md` y `versiones/HISTORIAL.md`. **Añadidos/eliminados: ninguno**; 14 archivos, 2 `.py` de producción, 1 `.bat`. Los componentes QML de iconos, gráfico e indicadores, el arranque, temas/diseño y las reglas no cambian.
- **Pruebas:** regresión del REBUILD, siete lecturas con válidos/ausentes/evaluándose, GPU/VRAM real, navegación y nombre estable. La prueba interactiva nativa Qt en Windows sigue pendiente.
- **Reversión:** ZIP externo `CorePulse_REBUILD_011_CPU_TEMP_LEGACY_RECUPERADA.zip`.

## REBUILD 011 — Recuperación de temperatura CPU del motor clásico (10-10-2026)

- **Reglas leídas:** TXT original y este historial antes de implementar. El TXT se conserva byte por byte.
- **Diagnóstico confirmado:** la REBUILD 010 solo consultaba LibreHardwareMonitor/OpenHardwareMonitor cuando otra aplicación publicaba WMI; la versión anterior al Qt leía directamente `HardwareMonitor`/`LibreHardwareMonitorLib`, y tenía compatibilidad para temperaturas CPU de portátiles publicadas bajo EC/SuperIO/Motherboard. Esa segunda ruta se perdió en el REBUILD.
- **Solución:** `telemetry.py` consulta primero WMI y, si no hay temperatura CPU, ejecuta una sonda DIRECTA en un proceso Python aislado usando `HardwareMonitor`/`pythonnet`, tal como hacía la ruta compatible del proyecto clásico. Activa únicamente los grupos CPU, placa y controladores; recorre sensores/subhardware, selecciona CPU Package/Tctl-Tdie/cores por prioridad y rechaza GPU, SSD, batería, ambient, 0 °C, temperatura inválida y distancia a TjMax. Siempre hay trazabilidad de origen y nombre físico del sensor.
- **Seguridad y rendimiento:** lectura en trabajador de fondo, `timeout=8`, caché de éxito (10 s) y de ausencia (45 s), sin descarga automática, cambios en Windows ni instalación silenciosa de driver. Si falta acceso de hardware o paquete, `N/A` y causa en tooltip.
- **Dependencias necesarias:** `HardwareMonitor>=1.2.1,<2` y `pythonnet>=3.1,<4` en `requirements.txt`, instalables por el usuario con pip del mismo Python 3.12 que ejecuta CorePulse. Para algunos equipos pueden requerirse permisos o driver de hardware ya instalado; no se instalará PawnIO sin consentimiento explícito.
- **Modificados:** `telemetry.py`, `requirements.txt`, etiquetas de `ui/Main.qml`, `tests/test_rebuild.py`, `README.md` y este historial. **Añadidos/eliminados:** 0 archivos; **2 Python de producción**, **1 BAT**, **14 archivos totales**.
- **Protegidos:** todo el layout, iconos, Resumen, gráfica, sensores RAM/SSD y GPU, tamaño estilo Steam, historial y reglas anteriores. El backend del REBUILD no importa los árboles antiguos.
- **Pruebas:** validación sintáctica, fuente embebida, prioridad WMI/directo, límites de temperatura, caché y regresiones anteriores. Pendiente confirmar lectura de hardware directamente en Windows del usuario.
- **Reversión:** conservar ZIP REBUILD 010 fuera de esta carpeta.

## REBUILD 010 — Precisión y procedencia de la telemetría (10-10-2026)

- **Reglas obligatorias leídas antes de cambiar nada:** `Reglas para crear Versiones nuevas.txt` y `versiones/HISTORIAL.md`. TXT conservado byte por byte.
- **Solicitud:** resolver frecuencia CPU fija en la nominal, aclarar diferencia de uso GPU con Administrador de tareas, preservar RAM/SSD correctos, temperatura CPU solo real.
- **Modificados:** `telemetry.py`, `ui/MetricLine.qml`, `ui/Overview.qml`, rótulos de versión de `ui/Main.qml`, `tests/test_rebuild.py`, `README.md`, `versiones/HISTORIAL.md`.
- **Archivos añadidos/eliminados:** ninguno (14 archivos, 2 Python de producción y un BAT).
- **CPU:** ahora se priorizan clocks físicos WMI de sensores CPU recientes (hasta 20 s). Como alternativa se consulta PDH `% Processor Performance` y la frecuencia nominal WMI `Win32_Processor.MaxClockSpeed` para obtener una **estimación** de GHz, marcada `≈` en pantalla y declarada en tooltip. Sin lecturas válidas, `N/A`. Se retiró el contador `Processor Frequency` obsoleto, frecuentemente fijo en la frecuencia base. No se confunde frecuencia calculada con un sensor directo.
- **GPU:** conserva uso real `utilization.gpu` de NVIDIA-SMI/NVML y temperatura GPU; descarta muestras de más de 5 s y muestra en tooltip el origen para explicar discrepancias frente a Task Manager. No inventa ni promedia porcentajes de motores distintos.
- **Temperatura CPU:** lectura WMI vigente de un monitor de hardware o `N/A`; se invalidan temperaturas de más de 20 s sin actualización. No se instala un monitor ni se fuerza un sensor.
- **RAM/SSD e interfaz visual:** sin cambios en las fuentes y cálculos de memoria/disco, sidebar, iconos, tamaños, tarjetas, ventana, gráficos ni navegación. Tooltips solo informativos.
- **Pruebas:** suites de base y nuevas validaciones de Turbo Boost estimado, ausencia/NaN, prioridad de sensores, fuentes en QML, proveedor WMI simulado e invariantes. Faltan verificaciones nativas PDH/CIM/NVIDIA/LHM y Qt en Windows.
- **Reversión:** el ZIP de REBUILD 009 permanece fuera del proyecto, nunca se copia dentro.

## REBUILD 009 — Telemetría CPU, GPU, RAM y almacenamiento (10-10-2026)

- **Reglas leídas:** `Reglas para crear Versiones nuevas.txt` y este historial antes de modificar. Se mantiene el TXT original byte por byte dentro del ZIP.
- **Solicitud:** corregir frecuencia/temperatura CPU, porcentaje NVIDIA GPU, uso RAM y mostrar nombre real de la unidad del sistema debajo de SSD.
- **Modificados:** `telemetry.py`, `ui/Overview.qml`, rótulos de versión de `ui/Main.qml`, `tests/test_rebuild.py`, `README.md` y `versiones/HISTORIAL.md`.
- **Añadidos/eliminados:** 0 archivos nuevos, 0 archivos completos eliminados; sigue en **14 archivos, 2 Python de producción y 1 BAT**. Se retiró la lectura obsoleta de `psutil.cpu_freq().current` como frecuencia de CPU dinámica en Windows y se reemplazó el cálculo de RAM que mezclaba `mem.percent` y `mem.used`.
- **CPU frecuencia:** utiliza PDH `Processor Information(_Total)\Processor Frequency` de Windows, con respaldo en los clocks CPU reales expuestos por WMI de LHM/OHM. Sin valor válido -> `N/A`.
- **CPU temperatura:** WMI de LibreHardwareMonitor/OpenHardwareMonitor, priorizando CPU Package/Tctl-Tdie; filtrado de sensores de GPU, 0 °C y valores inválidos. No se instala ni activa software o servicios.
- **GPU NVIDIA:** consulta real `nvidia-smi` en hilo de fondo cada ~2 s, eliminando porcentajes obsoletos; el indicador NVML no debe interpretarse como idéntico a los motores GPU de Task Manager. GPU no NVIDIA no soportada aún -> N/A.
- **RAM:** uso GB calculado con `total - available`, porcentaje derivado del mismo par y cifras expresadas en GiB; comparables internamente.
- **SSD:** mantiene medición de unidad del sistema y obtiene el modelo físico asociado a la letra mediante PowerShell Get-Partition/Get-Disk en un hilo; visualiza modelo sobre GB, o `Modelo N/A (C:\)` cuando Windows no devuelve nombre.
- **QML:** reemplazó comparaciones `===null` por validación `null/undefined/NaN` de números; ya no muestra `Temp. undefined °C`.
- **Pruebas:** se conservaron contratos anteriores y se añadieron pruebas de normalización, CPU térmico, RAM, NVIDIA y correlación de disco (PowerShell simulado). Falta comprobar la ejecución PDH/CIM/NVIDIA en Windows.
- **Protegidos:** ventanas tipo Steam, arrastre, sidebar, iconos HD, gráfico, tarjetas, navegación, colores y TXT de reglas sin cambios.
- **Reversión:** conservar `CorePulse_REBUILD_008_BENCHMARK_CORREGIDO.zip` fuera del proyecto.

## REBUILD 008 — Icono Benchmark corregido (10-10-2026)

- **Problema observado en Windows:** el icono de Benchmark parecía aplastado o deformado mientras el resto de iconos se veía bien.
- **Alcance:** corregir solo el símbolo `gauge` dentro de `ui/Glyph.qml`. Se cambió su arco SVG `A` por dos curvas Bézier `C`, con aguja, base y centro legibles a 22 píxeles lógicos y escalados DPI.
- **Modificados:** `ui/Glyph.qml`, los rótulos de versión en `ui/Main.qml`, `tests/test_rebuild.py`, `README.md` y este historial. **Sin añadidos de archivos ni Python.**
- **Eliminación de obsolescencia:** se retiró el trazado anterior del `gauge`, ya no necesario. No se conservaron variantes duplicadas ni implementaciones antiguas.
- **Protegido:** los demás 44 iconos, el layout del sidebar y Resumen, la telemetría y el cálculo de tamaño/arrastre permanecen sin cambios.
- **Reglas:** leído `Reglas para crear Versiones nuevas.txt` y este historial antes de modificar; TXT incluido literalmente sin cambios.
- **Pruebas:** suite del REBUILD, geometría del icono de Benchmark y comparación de archivos. La apariencia nativa definitiva debe comprobarse en Windows.
- **Reversión:** conservar `CorePulse_REBUILD_007_ICONOS_NITIDOS_DPI.zip` como copia de respaldo fuera del proyecto.

## REBUILD 007 — Iconos nítidos y reglas obligatorias (10-10-2026)

- **Objetivo:** corregir los bordes pixelados observados en los iconos vectoriales de REBUILD 006, manteniendo sus símbolos y el diseño del sidebar.
- **Modificados:** `ui/Glyph.qml`, `ui/Main.qml`, `tests/test_rebuild.py`, `README.md`, `versiones/HISTORIAL.md` y el TXT obligatorio a petición del usuario.
- **Regla incorporada:** queda escrito en el TXT que **cada nueva versión, componente, función o cambio debe respetar previamente el TXT y el historial**. No se alteran las reglas previas del usuario.
- **Renderizado:** se elimina `transform: Scale` y la `Shape` fija a 24×24. Las instrucciones SVG se adaptan con sus parámetros correctos a los píxeles lógicos reales del icono y la Shape ocupa el tamaño final de destino. Grosor mínimo de línea 1,8 px lógicos para reducir trazos débiles con DPI fraccionario. Se prefiere `Shape.CurveRenderer` cuando está presente (Qt 6.7+) por sus bordes con antialiasing independiente de MSAA; versiones anteriores usan `Shape.GeometryRenderer`.
- **Iconos del sidebar:** de 21×21 a 22×22 dentro del mismo fondo de 26×26; sidebar, paneles, gráfico y telemetría sin cambios.
- **Limpieza:** se eliminó la ruta obsoleta de escalado por `transform: Scale`, sin agregar `.py`, QML nuevo, fuentes ni imágenes externas. **14 archivos totales**, dos `.py` de producción, un `.bat`.
- **Pruebas:** contratos y validación matemática de coordenadas SVG, arcos y DPI 100/125/150/200 %; comparación de archivos protegidos y prueba de integridad del ZIP.
- **Pendiente:** aspecto final de Qt Quick Shapes y antialiasing deben verificarse en Windows; las pruebas estáticas no certifican renderizado nativo de GPU.
- **Reversión:** conservar `CorePulse_REBUILD_006_ICONOS_VECTOR_HD.zip` como respaldo externo.

## REBUILD 006 — Iconos vectoriales HD y reglas permanentes (10-10-2026)

- **Objetivo:** mejorar la nitidez de los iconos del sidebar en equipos Windows con resoluciones y DPI variables, y hacer que las reglas del usuario viajen dentro del proyecto.
- **Archivos modificados:** `ui/Glyph.qml`, `ui/Main.qml`, `tests/test_rebuild.py`, `README.md`, `versiones/HISTORIAL.md`.
- **Archivo añadido:** `Reglas para crear Versiones nuevas.txt`, copia literal del documento proporcionado por el usuario.
- **Archivos eliminados:** ninguno completo. Se eliminó el render anterior basado en `Canvas` dentro de `ui/Glyph.qml`, sustituido por un trazado vectorial `QtQuick.Shapes.Shape`/`PathSvg`, sin añadir `.py`, `.qml` ni recursos PNG/SVG.
- **Iconos:** todos los iconos existentes mantienen su sentido, proporciones y acentos; los accesos adicionales tienen ahora siluetas específicas (batería, juego, controladores, audio, Wi-Fi, etc.). Las bases tenues del sidebar y la navegación mantienen el diseño aprobado de REBUILD 005.
- **DPI:** se escala desde una geometría vectorial 24×24 hacia el tamaño del componente; no se genera un bitmap pequeño para ampliarlo.
- **Inventario esperado:** **14 archivos, 2 Python de producción, 6 QML, 1 BAT, 1 TXT obligatorio**. Sin cachés ni versiones antiguas en el ZIP.
- **Pruebas:** contratos sobre unicidad de trazados, rutas declaradas, QML Shape/PathSvg, reglas, no contaminación del proyecto, comparación de archivos protegidos y ZIP. **Pendiente:** prueba visual nativa con PySide6 en Windows, especialmente DPI de 125 %/150 % y el colapso del sidebar.
- **Reversión:** conservar `CorePulse_REBUILD_005_ICONOS_PULIDOS.zip` fuera de esta carpeta.

## REBUILD 005 — Pulido visual de iconos del sidebar (10-10-2026)

- **Alcance solicitado:** pulir todavía más el estilo visual de los iconos del sidebar, manteniendo la estructura compacta del REBUILD 004.
- **Modificados:** `ui/Glyph.qml`, `ui/Main.qml`, `tests/test_rebuild.py`, `README.md` y este `versiones/HISTORIAL.md`.
- **Añadidos/eliminados:** ninguno; se mantiene la base compacta del REBUILD con **13 archivos funcionales** y sin nuevos `.py` de producción.
- **Iconografía:** se redibujó el set vectorial con formas más limpias, esquinas redondeadas y siluetas más reconocibles para dashboard, benchmark, diagnóstico, salud, limpieza, tweaks, alertas, tendencias, historial, temas y CorePulse AI.
- **Sidebar:** cada icono del menú ahora vive dentro de una base visual sutil al hacer hover o al estar activo, mejorando legibilidad sin introducir imágenes externas ni colores raros.
- **Pruebas:** se actualizan las comprobaciones del REBUILD para reflejar el nuevo pulido visual y se conserva la validación de inventario mínimo.
- **Reversión:** conservar `CorePulse_REBUILD_004_ICONOS_SIDEBAR.zip` como respaldo.

## REBUILD 004 — Reajuste de iconos del sidebar (10-10-2026)

- **Alcance solicitado:** dejar de usar iconos genéricos o repetidos en la barra lateral, conservando el sidebar alineado de REBUILD 003.
- **Modificados:** `ui/Main.qml`, `ui/Glyph.qml`, `tests/test_rebuild.py`, `versiones/HISTORIAL.md` y `README.md`.
- **Añadidos/eliminados:** ninguno; el proyecto sigue con **13 archivos, 2 `.py` de producción y 1 `.bat`**.
- **Sidebar:** se reasignan iconos para que cada acceso principal tenga identidad propia: Resumen `dashboard`, Benchmark `gauge`, Iniciar diagnóstico `scan`, Centro de salud `health_shield`, Limpieza `broom`, Tweaks `sliders`, Alertas `bell_alert`, Tendencias `trend_up`, Historial `history` y CorePulse AI `spark_ai`.
- **Iconografía:** `ui/Glyph.qml` se amplía con un set vectorial nuevo, manteniendo el mismo sistema monocromático sin imágenes ni fuentes externas. Los iconos antiguos todavía compatibles no se eliminan si siguen siendo usados por otras zonas de la UI.
- **Pruebas:** se añaden comprobaciones de unicidad/rol de iconos del sidebar además de las pruebas previas del REBUILD. La validación visual final sigue siendo en Windows.
- **Reversión:** conservar `CorePulse_REBUILD_003_SIDEBAR_ALINEADO.zip` como respaldo.

## REBUILD 003 — Sidebar sin marca y alineado (10-10-2026)

- **Alcance solicitado:** retirar únicamente el icono de CorePulse con el texto "COREPULSE / Herramientas del equipo" del sidebar y subir las secciones de navegación para aprovechar ese espacio. Conservar el botón hamburguesa.
- **Modificados:** `ui/Main.qml`, `tests/test_rebuild.py`, `versiones/HISTORIAL.md` y `README.md`.
- **Añadidos/eliminados:** ninguno; continúa en **13 archivos, 2 `.py` de producción y un solo `.bat`**.
- **Interfaz:** se suprime el bloque de marca del sidebar; la cabecera lateral pasa de 92 a 52 píxeles lógicos, de modo que `MONITOREO` y los accesos siguientes suben 40 píxeles lógicos. El ancho del sidebar no cambia y la lista conserva su desplazamiento vertical para monitores pequeños.
- **Movimiento:** se preserva el arrastre nativo a través de la franja superior lateral libre, sin cubrir el botón de colapso; la cabecera principal, bordes de redimensionamiento, F11 y Escape no cambian.
- **Versión:** el rótulo de la ventana y subtítulo del Resumen se actualizan a Rebuild 003. El contenido del Resumen, lecturas de telemetría, gráficos y módulos pendientes no se modifican.
- **Pruebas:** `pytest` de contratos del REBUILD; comparación de archivos respecto de REBUILD 002. El renderizado y el arrastre nativos requieren comprobación en Windows.
- **Reversión:** conservar `CorePulse_REBUILD_002_VENTANA_STEAM_ARRASTRE.zip` como respaldo separado.

## REBUILD 002 — Ventana estilo Steam y movimiento (10-10-2026)

- **Alcance:** corregir únicamente el tamaño inicial, centrado y movimiento/redimensionado de la ventana Qt sin cambiar el Resumen, métricas ni sidebar.
- **Modificado:** `main.py`, `ui/Main.qml`, `tests/test_rebuild.py`, `README.md`, este `versiones/HISTORIAL.md`.
- **Añadidos/eliminados:** ninguno. Siguen 13 archivos totales y **solo 2 `.py` de producción**.
- **Tamaño inicial:** 1280×720 píxeles lógicos como referencia Steam en pantallas con espacio suficiente. En pantallas pequeñas, 90 % de la **superficie útil** de Windows (`availableGeometry()`, sin barra de tareas), centrado y respetando escalado DPI. Mínimos adaptados al monitor para no quedar fuera de la pantalla.
- **Arrastre:** desde la zona superior de la cabecera (excluyendo los controles) o el encabezado del sidebar; movimiento nativo con `startSystemMove()` y fallback manual cuando no está disponible. Doble clic en la zona de arrastre maximiza/restaura. Se habilitaron bordes izquierdo y superior para cambiar tamaño, además de derecho/inferior.
- **Regresión:** controles de ventana y botón hamburguesa preservados. Atajos F11/Escape se conservan.
- **Pruebas:** ver `tests/test_rebuild.py`; probar movimiento/redimensionado de manera nativa en Windows.
- **Pendiente:** verificación visual en Windows con PySide6 instalado; sigue siendo una base de reconstrucción, no paridad total con el proyecto antiguo.
- **Reversión:** conservar el ZIP de REBUILD 001 base documentada fuera de este directorio.

## REBUILD 001 — Base limpia (10-10-2026)

- **Objetivo:** iniciar CorePulse como aplicación Qt independiente con pocos archivos.
- **Estructura:** `main.py` (arranque), `telemetry.py` (fuente de datos reales), seis QML reutilizables, un `.bat`, `requirements.txt`, `README.md` y pruebas iniciales.
- **Estado funcional:** ventana, navegación, Resumen inicial y telemetría CPU/RAM/disco; GPU mediante `nvidia-smi` si está disponible; módulos futuros marcados como pendientes.
- **No implementado:** diagnóstico avanzado, benchmark, IA, temas completos, RTSS, operaciones de Windows. No simular estas funciones.
- **Pruebas declaradas en la entrega inicial:** siete pruebas del REBUILD; **pendiente:** comprobar QML nativo en Windows.
- **Respaldo:** conservar fuera de esta carpeta el proyecto antiguo V39; no usarlo como base de código.

## REBUILD 001 — Incorporación del historial (10-10-2026)

- **Motivo:** evitar la fragmentación y pérdida de trazabilidad de versiones anteriores.
- **Añadido:** `versiones/HISTORIAL.md` (único archivo de registro; ampliar en próximas versiones).
- **Modificado:** `README.md` para señalar las reglas y el historial; `tests/test_rebuild.py` para actualizar su control de inventario (12 → 13 archivos).
- **Python y QML:** sin modificaciones; **archivos `.py` nuevos: 0**.
- **Pruebas:** ejecutar pruebas existentes y verificar el archivo ZIP, sin afirmar ejecución visual Qt en Windows.
- **Pendiente:** usar este registro desde REBUILD 002 en adelante y confirmar la carga de interfaz en Windows.

## REBUILD 041 — SSD separado + progreso
- Se retiró Almacenamiento del set principal del Centro de Salud.
- El componente SSD del Resumen ahora abre directamente Almacenamiento.
- Se añadieron barras de progreso al Análisis de Windows y a Reparación de Windows.
- Se ajustó el flujo por defecto del Centro de Salud en equipos sin batería.
- Pruebas actualizadas y validadas: 123 PASS.

## REBUILD 042 — Recuperación del sistema
- Se agregó el módulo Recuperación del sistema al Centro de salud.
- Se integró lectura real de protección del sistema, puntos de restauración y Windows RE.
- Se añadió creación manual de punto de restauración con confirmación explícita y registro local.
- Se añadieron accesos directos a Restaurar sistema y a la Configuración de recuperación de Windows.
- Pruebas validadas: 124 PASS.

## REBUILD 043 — Recuperación sin errores de PowerShell
- Corregida la consulta PowerShell de puntos de restauración (sintaxis y fechas WMI).
- Paso de scripts con `-EncodedCommand` UTF-16LE y lectura de JSON UTF-8.
- Los errores de consulta ya no aparecen como texto corrupto en QML.
- Diferenciados N/A (dato inaccesible), cero puntos confirmado y estado de protección no confirmado.
- Parser de WinRE en español e inglés.
- Creación de puntos verificada contra nuevas secuencias, sin confirmar éxitos ficticios.
- 130 pruebas automatizadas PASS; ejecución nativa Windows pendiente.

## REBUILD 044 — Historial de cambios (12-10-2026)
- Basada exclusivamente en REBUILD 043 y en sus reglas originales.
- Centro de Salud incorpora pestaña «Historial»: registro de Tweaks persistente, informes de integridad DISM/SFC, historial local Windows Update y puntos de restauración de Windows.
- Cronología real en lectura, con fechas, resultados y filtros. Los errores de consulta se indican como N/A, nunca como cero eventos confirmado.
- Cuatro fuentes consultadas de manera independiente en segundo plano, barra de progreso por etapas realmente terminadas; no se ejecutan acciones de mantenimiento.
- Se reutiliza la consulta de restauración corregida en V043 en lugar de duplicar PowerShell. El motor de Tweaks y todos los anteriores se conservan sin cambios.
- Nuevo archivo modular necesario: `core/health/history.py`; icono nuevo `file_clock` vectorial.
- Pruebas: **135 PASS** (incluyen auditoría, informes, fuentes inaccesibles, orden cronológico y navegación). QML y Windows Update COM pendientes de validación nativa.

## REBUILD 045 — Estado general de salud (11-10-2026)
- Base exclusiva: REBUILD 044 con su archivo de reglas.
- Módulo general de salud basado en CPU/GPU, RAM, salud física y espacio de unidades, batería según presencia real, códigos de dispositivos y Windows RE.
- Estado cualitativo y cobertura verificable; no se inventa un porcentaje global de salud. Valores N/A permanecen sin verificar.
- Accesos de cada indicador a su módulo real y pestañas adaptables al ancho de ventana.
- Se corrigieron imports, instancias y conexiones duplicados de Recuperación e Historial que venían de la V044.
- Archivo modular nuevo `core/health/system_health.py`; no hay motores antiguos copiados ni módulos obsoletos añadidos.
- 140 pruebas automatizadas PASS; ejecución gráfica Qt/Windows pendiente de validación.

## REBUILD 046 — Alertas térmicas, RAM y reinicio opcional
- Base exclusiva: REBUILD 045 con el TXT de reglas conservado.
- CPU: sondeo de sensores más frecuente, prioridad de lectura directa si hay sensor real, WMI como alternativa, caducidad más rápida para evitar datos obsoletos.
- CPU ≥90 °C y GPU ≥85 °C: la temperatura se destaca en rojo. RAM ≥90 %: icono, barra y lectura se destacan en rojo.
- Tiempo desde arranque ≥10 horas: tarjeta e icono rojos; botón Reiniciar con confirmación. Solicita reinicio Windows con plazo de 60 s y permite cancelarlo. Nunca se ejecuta al abrir CorePulse ni al alcanzar el umbral sin acción explícita.
- Sin nuevos archivos .py ni modificaciones a motores restantes; REAL_OR_NA conservado.
- 144 pruebas automatizadas PASS; Qt/Windows nativo pendiente.


## REBUILD 048 — Integración Centro de Salud y Test de Audio en Alertas Térmicas
- Base exclusiva: ZIP entregado por usuario CorePulse REBUILD 046 «Alertas térmicas, RAM y reinicio opcional». No partir del antiguo V046 «Paridad inicial» ni sustituir por V047 completa.
- Preservados los motores de CPU, GPU, RAM, tiempo desde arranque y reinicio/cancelación con confirmación de V046.
- Migrada la portada de Centro de Salud de V047: tarjetas de acceso en vez de pestañas superiores; Volver retorna al panel principal.
- Test de Audio de salida integrado (izquierdo / ambos / derecho) con tonos WAV PCM locales; configuración de sonido de Windows disponible.
- Portada mantiene lecturas verificables plegadas, Batería/Windows/Reparación/Recuperación/Historial; Rendimiento permanece pendiente.
- Corregida normalización WinRE en la cobertura de salud.
- Sin nuevos módulos Python ni archivos obsoletos añadidos; 148 pruebas automatizadas PASS.
- Renderizado y sonido reales aún pendientes de comprobar en Windows 11.


## REBUILD 049 — Rendimiento: energía reversible y estabilidad (migración parcial V485)
- Base: V048 Alertas Térmicas + Centro de Salud + Audio, no sustituye motores heredados.
- Se restauró en el Centro de Salud la selección de planes de energía realmente existentes en Windows, con confirmación, comprobación y rollback persistente.
- Nueva vista de temperaturas reales CPU/GPU, con estado de throttling N/A donde falta evidencia directa; sin FPS inventados.
- Lectura conservadora de ejecutables Steam/Epic identificados por ruta, sin afirmar un Game Boost activo.
- Se evita crear planes, modificar ajustes sin consentimiento y confundir riesgo térmico con throttling confirmado.
- Game Boost completo, biblioteca avanzada y benchmark original de V485 permanecen pendientes y documentados.
- Un solo archivo Python de producción nuevo (`core/health/performance.py`), sin nuevas páginas QML.
- 155 pruebas automatizadas PASS; ejecución QML y pruebas de powercfg en Windows quedan pendientes.

## REBUILD 050 — Juego activo estilo Steam (migración incremental)
- Base única REBUILD 049; sin cambios en módulos de energía, RAM, CPU/GPU, reinicio y ajustes de Windows.
- Tarjeta de juego en ejecución con imagen Steam real local, título verificado desde appmanifest, plataforma, estado y duración basada en inicio real del proceso.
- Sondeo no bloqueante de Steam/Epic cada 2,5 segundos únicamente mientras Rendimiento está abierto.
- Imagen externa opcional con clic explícito (no transmisión de biblioteca al abrir la aplicación).
- Estado vacío y detección de cierres reales; FPS mantiene N/A y Game Boost permanece pendiente de migración.
- 159 pruebas automatizadas PASS; renderizado nativo Windows 11 pendiente.

## REBUILD 051 — Tarjeta de juego remaquetada
- En Rendimiento, la tarjeta de juego activo ahora muestra Estado, Tiempo activo y Origen debajo de la carátula.
- Se mantiene la detección real de juego, carátulas de Steam y tiempo de sesión.


## REBUILD 052 — Temas iniciales + iconos de Centro de Salud
- Base: REBUILD 051.
- Centro de Salud: cada icono del hub ahora usa un color distinto para diferenciar módulos.
- Se añadió el módulo Temas como primera versión funcional.
- Los temas aplican paleta base del shell principal (fondo, sidebar y acentos de navegación).
- Nuevo archivo: ui/ThemesPage.qml.
- Validación: pytest -q -> 161 PASS.


## REBUILD 053 — Tweaks de apertura rápida
- Base: REBUILD 052; catálogo conservado de 78 tweaks y 12 categorías.
- Verificación de estados en trabajador de segundo plano; el getter `options` deja de ejecutar Registro y PowerShell en el hilo QML.
- Todas las operaciones permanecen deshabilitadas hasta que el estado real quede verificado. Respaldo y rollback conservados.
- Renderizado virtualizado con `ListView` y tarjetas generadas al desplazarse.
- Resultados reutilizables durante 60 segundos; comprobación manual disponible con «Actualizar».
- Sin archivos Python de producción nuevos ni cambios en otros motores.
- Validación: 165 pruebas PASS. Pendiente de probar rendimiento y renderizado en Windows.

## REBUILD 054 — Riot Games en Rendimiento
- Base: REBUILD 053 — Tweaks rápidos.
- La tarjeta de juego activo reconoce VALORANT, League of Legends y Legends of Runeterra mediante procesos reales y rutas coherentes de instalación, incluyendo otras unidades.
- League distingue cliente abierto de partida en ejecución y prioriza el proceso de partida para el tiempo de sesión.
- Riot Client, Vanguard y otros servicios/anticheats quedan excluidos de la detección.
- Steam/Epic conservados. Sin FPS inventados ni carátulas Riot no verificadas.
- Sin nuevos módulos Python ni alteración de Tweaks, Audio, Limpieza o sensores.
- 170 pruebas automatizadas PASS. Prueba nativa de Riot Games/Qt en Windows pendiente.

## REBUILD 055 — Diez temas, bandeja del sistema y RAM
- Base: REBUILD 054 Riot Games. Ningún cambio en sensores, Steam/Epic/Riot ni Tweaks engine.
- Diez temas distinguibles y persistentes con QSettings, aplicados a fondo, sidebar, paneles, tarjetas, bordes y botones principales.
- La X minimiza a bandeja (si existe) con menú de restauración, acceso a limpieza de RAM y opción de salida real.
- Limpieza de RAM completa conserva confirmación y medidor real. Una ejecución parcial muestra estado parcial, no éxito falso.
- Sin archivos de motor Python nuevos; se centralizó gestor de temas/bandeja en main.py.
- 173 pruebas automatizadas PASS; prueba Qt/Windows pendiente.

## REBUILD 056 — Arte local multi-tienda y hover de sidebar
- Base V055. Se amplía Rendimiento a instalaciones EA app y Microsoft Store/Xbox con fuentes locales verificadas, preservando Steam/Epic/Riot.
- Intenta mostrar la carátula local/logo de paquete o icono auténtico del ejecutable cuando no hay portada disponible; sin búsquedas externas automáticas.
- Sidebar colapsado: animación de elevación de iconos, borde y tooltip; incluye módulos adicionales.
- Los motores de RAM, Tweaks, sensores, bandeja y temas permanecen intactos.
- 177 pruebas PASS; validación gráfica nativa y casos OEM pendientes.

## REBUILD 057 — Portadas panorámicas verificadas de juegos
- Sobre V056, se añadió solicitud explícita de carátula oficial para Riot Games con caché y validación de dominio, título y tamaño de imagen.
- Se añadió `Elegir portada` para asociar arte local panorámico a cualquier juego reconocido por tienda y nombre.
- Mantiene carátulas Steam y arte de instalaciones locales; el ícono pequeño solo se usa como respaldo.
- Conserva Steam, Epic, Riot, EA, Xbox/Microsoft Store, temas, bandeja y RAM.
- Pruebas automatizadas: 181 PASS; pendiente ejecución nativa de QML e imágenes oficiales en Windows.

## REBUILD 058 — Portadas automáticas sin controles manuales
- Base: V057.
- Se elimina la elección manual de portada y sus botones QML/Python obsoletos.
- Descarga automática en segundo plano por Riot oficial, Steam App ID real y equivalencias de otras tiendas por título exactamente igual en Steam.
- Cachas automáticas separadas, validación de origen/tamaño/dimensiones y límite de peticiones (no en cada sondeo).
- Los íconos pequeños no se clasifican como portadas panorámicas.
- No se envían procesos/rutas/telemetría; únicamente título o ID público para búsqueda de arte.
- REAL_OR_NA y motores anteriores conservados; 185 pruebas PASS. Windows gráfico y fuentes remotas pendientes de comprobación.

## REBUILD 059 — Menú de cuenta en el botón Usuario (12-10-2026)
- Base: V058. Leídos el TXT de reglas y el historial antes de implementar.
- El botón de cuenta de la barra superior (antes «U · Usuario») muestra, sin sesión, un icono de persona y «Iniciar sesión»; con la futura web mostrará inicial/foto y nombre. Despliega debajo una lista: Iniciar sesión, Registrarse, Ajustes de cuenta y Cerrar sesión. Se cierra con Escape, clic fuera o nuevo clic.
- Cada opción abrirá la futura web de cuentas (`accountWebBase` + ruta). La web aún no existe: la dirección queda vacía y el menú avisa «próximamente» sin abrir nada. Solo se aceptan direcciones `https://`; no se envían datos del equipo.
- Nuevos iconos `user`, `login`, `user_plus` y `logout` en `Glyph.qml`.
- **Añadidos:** ninguno. **Modificados:** `ui/Main.qml`, `ui/Glyph.qml`, `tests/test_rebuild.py`, `README.md`, `versiones/HISTORIAL.md`. **Eliminados:** ninguno. 36 archivos.
- 186 pruebas PASS. Renderizado comprobado con PySide6 en macOS; prueba gráfica en Windows pendiente.
- **Reversión:** usar el ZIP V058.

## REBUILD 060 — Inicio de sesión de la app a través de la web (13-10-2026)
- Base: V059. Leídos el TXT de reglas y el historial antes de implementar.
- «Iniciar sesión» abre `/app/conectar` en la web; el usuario autoriza el equipo y el navegador vuelve a `http://127.0.0.1:<puerto>/callback`; la app canjea código + verificador (PKCE) por un token de equipo y pasa al frente.
- Espera de hasta 10 minutos en el navegador (permite crear la cuenta y confirmar el email). La app nunca ve la contraseña. Token cifrado con DPAPI (`%LOCALAPPDATA%\CorePulse\cuenta.dat`); fuera de Windows solo en memoria. Cerrar sesión revoca el token en la web.
- Menú de cuenta según el estado (sin sesión / esperando / conectado con nombre, email y plan). Se retira `accountWebBase` y el aviso «próximamente» de V059.
- **Añadido:** `core/cuenta.py` (responsabilidad nueva e independiente: sesión de usuario y comunicación con la web; justificado según la regla 1). **Modificados:** `main.py`, `ui/Main.qml`, `tests/test_rebuild.py`, `README.md`, `versiones/HISTORIAL.md`. **Eliminados:** ninguno. 37 archivos.
- Privacidad: solo HTTPS a la web de CorePulse para canjear el código, leer el perfil y cerrar sesión; sin datos del equipo ni telemetría.
- 192 pruebas PASS. Flujo SQL probado en PostgreSQL. Pendiente: prueba completa en Windows (DPAPI, navegador predeterminado) y migración en Supabase.
- **Reversión:** usar el ZIP V059.

## REBUILD 061 — Dominio propio corepulse.cl (13-10-2026)
- Base: V060. Leídos el TXT de reglas y el historial antes de implementar.
- La web de cuentas pasa a `https://corepulse.cl` (Cloudflare Workers); `WEB_PREDETERMINADA` en `core/cuenta.py` deja de apuntar a Render. Sin otros cambios de comportamiento.
- **Añadidos:** ninguno. **Modificados:** `core/cuenta.py`, `ui/Main.qml` (número de versión), `tests/test_rebuild.py`, `README.md`, `versiones/HISTORIAL.md`. **Eliminados:** ninguno. 37 archivos.
- 193 pruebas PASS. Pendiente: prueba completa en Windows.
- **Reversión:** usar el ZIP V060 (apunta a Render).

## REBUILD 062 — Gráfico de rendimiento fluido (13-10-2026)
- Base: V061. Leídos el TXT de reglas y el historial antes de implementar.
- `HistoryChart.qml`: deslizamiento continuo a 60 fps entre muestras (animación lineal de 1 s sincronizada con el muestreo de telemetry) y curva monótona Fritsch–Carlson. Sin valores inventados: las N/A cortan la línea, no hay sobrepicos y se recorta al área del gráfico. Eje «Hace 60 s» → «Ahora».
- **Añadidos:** ninguno. **Modificados:** `ui/HistoryChart.qml`, `ui/Main.qml` (versión), `tests/test_rebuild.py`, `README.md`, `versiones/HISTORIAL.md`. **Eliminados:** ninguno. 37 archivos.
- 194 pruebas PASS. Movimiento comprobado en la vista previa macOS (fotogramas cada 0,25 s). Pendiente: prueba en Windows.
- **Reversión:** usar el ZIP V061.


## REBUILD 065 — Fusión Gráfico Fluido (Agustín) + Chat Ampliado (13-10-2026)
- **Base elegida:** REBUILD 062 GRÁFICO FLUIDO de Agustín. Se descarta la rama de Diagnóstico/Paletas Nuevas de Maximiliano para esta versión, según petición expresa.
- **Fuente IA:** REBUILD 064 AI CHAT AMPLIADO con Login. Reglas del TXT y los dos historiales leídos previamente.
- **Conservado de Agustín:** `ui/HistoryChart.qml` intacto (1 s, curva monótona, 0–100 %, N/A) y `core/cuenta.py` intacto (`https://corepulse.cl`). UI del resto de pestañas intacta.
- **Integrado de IA:** `core/ai.py`, `ui/AIPage.qml`, controlador creado/cerrado en `main.py` y ruta de navegación `aiComponent` en `ui/Main.qml`; chat ampliado con controles A−/A+, ajustes plegables y permisos independientes.
- **Agregados:** 2 archivos de producción. **Modificados:** `main.py`, `ui/Main.qml`, `tests/test_rebuild.py`, `README.md`, `versiones/HISTORIAL.md`. **Eliminados:** ninguno; sin copias paralelas ni servidores adicionales.
- **Validación:** pruebas automatizadas conjuntas de Agustín, IA, cuenta, QML y reglas; comprobar gráficos/hover y login/web en Windows real.
- **Reversión:** conservar ZIPs originales 062 GRÁFICO FLUIDO y 064 CHAT AMPLIADO como respaldos.

## REBUILD 074 — Detección multiversión de Python (14-10-2026)
- Base: ZIP REBUILD 073 entregado. Leídos las reglas y el historial.
- Inicio `.bat` descarta interpretes dañados mediante importación de `encodings`, exige Python >=3.12 de 64 bits y prueba alternativas del lanzador `py` y `python`/`python3`.
- `main.py` acepta Python >=3.12 de 64 bits y conserva los entornos virtuales independientes por ABI, arquitectura y hash de requisitos. No se modificó QML, sensores, IA ni requisitos.
- Alcance: compatibilidad del arranque; dependencias reales por versión y funcionamiento Windows/Qt requieren validación en cada Python. No incluye runtime portable ni promete soporte de versiones futuras.
- Sin archivos de motor adicionales ni código obsoleto acumulado. Reversión: ZIP REBUILD 073.

## REBUILD 075 — Telemetría GPU multivendedor (14-10-2026)
- Base: REBUILD 074. Se conservaron todas las páginas y dependencias.
- GPU: sonda HardwareMonitor aislada con GPU habilitada; sensores de carga, temperatura y VRAM solo cuando el propio hardware los publica. NVIDIA-SMI sigue como alternativa.
- En equipos Intel + AMD se prefiere la AMD dedicada cuando proporciona sensores, sin mezclar métricas de dispositivos distintos. Si no hay lecturas se mantiene N/A y se informa el motivo del fallo de la sonda.
- Corregida secuencia de escape en ruta predeterminada NVIDIA. No se modificaron páginas QML.
- No se garantiza soporte para todos los sensores; requiere validación en Windows con GPU reales. Reversión: ZIP REBUILD 074.

## REBUILD 076 — Color del gráfico según GPU activa (14-10-2026)
- Base: REBUILD 075; reglas e historial revisados.
- `ui/Overview.qml`: la leyenda, curva de GPU y medidor lateral comparten `gpuBrandColor`, derivado del nombre de la GPU monitoreada. AMD rojo, NVIDIA verde, Intel azul y fabricante desconocido morado. CPU sin cambios.
- `ui/HistoryChart.qml`: repinta el Canvas cuando cambia el color GPU sin alterar el deslizamiento, muestreo o la política de N/A.
- No se agregan dependencias, archivos de producción o código de telemetría; sin cambios en diseños. Reversión: ZIP REBUILD 075.

## REBUILD 077 — Esquinas exteriores cuadradas (14-10-2026)
- Base: REBUILD 076; leídas las reglas y el historial.
- `ui/Main.qml`: el contenedor exterior `background` usa `radius:0` tanto en modo ventana como en maximizado, eliminando el recorte redondeado de las cuatro esquinas. Se mantiene el gradiente, borde, sidebar, tarjetas y demás componentes intactos.
- No se añaden archivos de producción ni dependencias. Prueba visual en Windows pendiente. Reversión: ZIP REBUILD 076.

## REBUILD 080 — Paleta original CorePulse (14-10-2026)
- Base: REBUILD 079; se consultaron reglas e historial antes de modificar.
- Solo tema `corepulse` de `main.py`: se restauraron los 10 valores originales de REBUILD 065 (3 fondos, sidebar, panel, panel elevado, borde, acento turquesa, azul y morado).
- Sin modificaciones a QML, GPU, sensores, animaciones, otras paletas o funcionalidades. Reversión: ZIP REBUILD 079.

## REBUILD 110 — TENDENCIAS GRAFICO AJUSTADO
- Ajustado el gráfico de Tendencias para comprimir huecos largos cuando CorePulse estuvo cerrado durante la misma sesión de Windows.
- Se mantienen únicamente muestras reales verificadas; no se interpolan ni inventan datos.
- La sesión sigue definida por el arranque de Windows, pero el gráfico queda visualmente más legible.
