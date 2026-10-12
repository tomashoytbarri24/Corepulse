# Historial de CorePulse — VALIDACIONES HISTORICAS

Registro histórico consolidado para reducir archivos sueltos. No es una guía de ejecución actual.

---

## Documento original: `VALIDACION_V404_CLEAN_REBUILD_MASTER_WORKSPACE.md`

# Validación V404 · Clean Rebuild Master Workspace

Base funcional: V400.

Objetivos:
- conservar todas las funciones de producto;
- reducir archivos no necesarios en la distribución;
- usar una sola imagen de fondo para todas las vistas;
- mantener intacto el diseño de tarjetas V400.

La suite V400 se ejecutó antes de la reconstrucción: **76/76 PASS**. Después de integrar el rebuild y los contratos V404 se ejecutó una suite temporal sobre la nueva carpeta: **79/79 PASS**. La compilación completa de Python también finalizó correctamente.

## Auditoría estructural final

- Archivos finales de producto: **231**.
- Archivos Python: **168**.
- Módulos de producto sin ruta de importación estática desde los entrypoints: **0**.
- Duplicados binarios dentro de `assets/`: **0**.
- Caches `__pycache__` / `.pyc` en distribución final: **0**.
- Fondo maestro: `assets/workspace/CorePulseWorkspaceBackground.png`.
- Entry points auditados: `main.py`, `corepulse_launcher.py`, `CorePulse_AI_Server/app/main.py`.

### Funcionalidad preservada

Telemetría CPU/GPU/RAM/almacenamiento, sensores LHM/PawnIO, diagnóstico completo, Centro de salud, limpieza, Tweaks, red, alertas/tendencias/historial, Benchmark, Gaming/Game Boost, FPS real/PresentMon, planes de energía nativos de Windows, drivers, reportes, bandeja, F11, temas y CorePulse AI local con autoarranque.

---

## Documento original: `VALIDACION_V405_FULL_CLIENT_MASTER_BACKGROUND.md`

# Validación V405 · Full Client Master Background

- Base funcional: V404 clean rebuild.
- Wallpaper: `assets/workspace/CorePulseWorkspaceBackground.png`.
- El fondo se instala en la raíz de la aplicación, no en `main_content`.
- La imagen completa se preserva con `ImageOps.contain`; no se usa crop/zoom.
- Sidebar y contenido permanecen encima.
- Sin cambios en tarjetas, telemetría, IA, Gaming, planes de energía o diagnóstico.

---

## Documento original: `VALIDACION_V406_MASTER_BACKGROUND_HEADER.md`

# CorePulse V406 · Fondo maestro continuo + encabezado

- Basado en CorePulse V405 completo adjuntado.
- Un único recurso PNG maestro; escalado a la totalidad del cliente, sin barras con relleno plano.
- El renderer sincroniza por coordenadas globales los CTkFrame estructurales sobre el único wallpaper.
- Encabezado superior opaco con bordes de la paleta existente; CorePulse AI deja de tener columnas competitivas y el header conserva su altura útil.
- Se conservaron todos los módulos y no se editaron las tarjetas de recursos, salud, gráficos, Gaming ni los sistemas de telemetría.
- Validación visual y de arranque final pendiente en equipo Windows del usuario.

---

## Documento original: `VALIDACION_V407_HEADER_NAME_ONLY_INTEGRATED.md`

# Validación V407 · HEADER_NAME_ONLY_INTEGRATED

## Objetivo
Corregir el encabezado del Resumen para que el bloque izquierdo no parezca una tarjeta, sino un encabezado integrado al fondo maestro con el nombre del equipo.

## Cambios
- `gui/dashboard.py`: `_build_header()` reconstruido con contenedor transparente.
- El bloque izquierdo ahora muestra sólo identidad del equipo.
- La tarjeta de CorePulse AI permanece como única tarjeta de la franja superior.

## Alcance
- No se rediseñan las tarjetas funcionales existentes.
- No se modifica la lógica de telemetría, IA, diagnóstico, drivers ni gaming.

## Verificación rápida
1. Ejecutar `python main.py`.
2. Abrir `Resumen`.
3. Confirmar que arriba a la izquierda ya no existe una tarjeta opaca; debe verse sólo el nombre del equipo sobre el fondo.
4. Confirmar que la tarjeta `CorePulse AI` sigue visible a la derecha.

---

## Documento original: `VALIDACION_V408_HEADER_TRUE_BACKGROUND_INTEGRATION.md`

# Validación V408 · HEADER_TRUE_BACKGROUND_INTEGRATION

## Objetivo
Hacer que el encabezado del Resumen use realmente el mismo fondo maestro alineado, evitando la apariencia de banda o bloque separado.

## Cambios
- `gui/dashboard.py`: al reconstruir el layout, `workspace_background.register_page(app._header, max_depth=4)` integra el encabezado al wallpaper.
- Se mantiene la tarjeta `CorePulse AI` como única tarjeta visual en la fila superior.

## Verificación rápida
1. Ejecutar `python main.py`.
2. Abrir `Resumen`.
3. Confirmar que la zona del nombre del equipo se ve fusionada con el fondo y ya no como una banda uniforme.
4. Confirmar que `CorePulse AI` sigue separado a la derecha.

---

## Documento original: `VALIDACION_V409_HEADER_IDENTITY_TRUE_ALPHA_FIX.md`

# CorePulse V409 · Encabezado sin recuadros negros

## Qué se corrigió
- `gui/header_identity_canvas.py`: identidad del equipo mediante Canvas nativo con logo RGBA y texto dinámico.
- `gui/workspace_background.py`: pintado del recorte maestro alineado detrás de los elementos del Canvas, respetando el orden de capas.
- `gui/dashboard.py`: reemplazo exclusivo de los controles opacos de nombre/logo y registro de la nueva superficie pictórica.

## Comprobaciones
- Render Tk aislado con pantalla virtual: composición, cambio de texto, cambio de tamaño y posición de capas PASS.
- Compilación de sintaxis Python: PASS.
- El arranque de toda la aplicación Windows y la telemetría hardware deberán validarse en el equipo de destino.

## Prueba manual en Windows
1. Ejecuta `python main.py` o `Iniciar_CorePulse.bat`.
2. En `Resumen`, confirma que ni el logo ni el nombre tienen fondo negro propio.
3. Cambia tamaño o maximiza. El mismo fondo maestro debe mantenerse continuo.
4. Comprueba que el nombre corresponda al equipo real y que CorePulse AI se mantenga a la derecha.
5. Verifica la navegación y las tarjetas que ya funcionaban en V408.

---

## Documento original: `VALIDACION_V410_NATIVE_WORKSPACE_DESIGN.md`

# CorePulse V410 · superficie nativa de aplicación

## Objetivo
Sustituir el wallpaper instalado en las versiones V404–V409 por una capa inferior propia de la interfaz, sin modificar las tarjetas del usuario.

## Implementación
- `gui/workspace_background.py`: compositor Tk nativo que utiliza los roles del tema; no carga PNG, crea líneas/áreas y reparte la misma geometría sobre contenedores estructurales.
- `gui/header_identity_canvas.py`: logo RGBA y nombre de equipo real sobre ese diseño, sin rellenos de CTkLabel.
- `gui/dashboard.py`: encabezado sin tarjeta a la izquierda, CorePulse AI separada a la derecha.
- `core/frozen_selftest.py`: verifica el compositor en lugar de buscar el wallpaper retirado.
- `assets/workspace/`: se retira el fondo PNG obsoleto.

## Comprobaciones en Windows
1. Ejecutar `python main.py`.
2. En Resumen, confirmar que no se ve una fotografía estirada ni cuadros negros detrás del logo/nombre.
3. Maximizar y restaurar: líneas discretas sin costuras entre las capas.
4. Navegar a Benchmark, Diagnóstico, Temas y CorePulse AI: misma base visual en el área estructural y tarjetas sin cambios.
5. Cambiar el tema: los colores de fondo acompañan a la paleta seleccionada.
6. Verificar telemetría real, FPS reales o N/A y funcionamiento de IA.

Este entorno no equivale a probar el funcionamiento completo de CorePulse en Windows; los controles funcionales requieren validación allí.

---

## Documento original: `VALIDACION_V411_SURFACE.md`

# V411 · Validación visual y funcional

## Objetivo
Que la capa oscura INFERIOR de CorePulse muestre un diseño propio perceptible, sin recurrir a una fotografía ni recrear tarjetas.

## Verificación manual en Windows
1. Abrir `python main.py` o `Iniciar_CorePulse.bat`.
2. En Resumen, mirar el área **detrás** del nombre de equipo, las separaciones entre las tarjetas y los raíles a ambos lados del workspace. Deben ser perceptibles los planos azules y los trazos finos sin marcos enormes.
3. Maximizar/restaurar y colapsar/expandir sidebar. El riel izquierdo debe seguir la zona de trabajo.
4. Cambiar tema y navegar entre pestañas; comprobar que las capas son coherentes y que las tarjetas no cambian.
5. Confirmar que CPU/RAM/GPU/SSD, IA, gaming y diagnósticos mantienen su funcionamiento.

## Alcance
`gui/workspace_background.py` y metadatos de versión/documentación. Sin alteraciones de lógica ni telemetría.

---

## Documento original: `VALIDACION_V412_SURFACE_NO_ARTIFACTS.md`

# V412 · Comprobación de superficie nativa corregida

## Defecto V411
La composición V411 incluía raíles longitudinales y una retícula global. Las tarjetas los tapaban parcialmente, por lo que quedaban líneas y figuras sueltas, principalmente junto al sidebar, en los bordes y bajo el encabezado.

## Corrección
- Sólo fondo cromático nativo y un breve indicador horizontal bajo la identidad (sin recuadro).
- No se crean polígonos, retículas, rails ni marcas que atraviesen tarjetas.
- Recorte explícito de las primitivas del fondo dentro de cada canvas CTk.

## Prueba en Windows
1. Abrir `Iniciar_CorePulse.bat` o `python main.py`.
2. Revisar que no haya líneas verticales duplicadas junto al sidebar ni trazos interrumpidos entre tarjetas.
3. Verificar el encabezado: sólo logo, nombre del equipo y tarjeta CorePulse AI, sin cajas negras.
4. Maximizar/restaurar, colapsar/expandir sidebar y entrar a otra pestaña.
5. Comprobar que todas las tarjetas, gráficos, sensores y accesos siguen funcionando.

---

## Documento original: `VALIDACION_V413_SIDEBAR_CHART_SSD_ALIGNMENT.md`

# CorePulse V413 · Validación de geometría

## Verificar en Windows
1. Abrir CorePulse y Resumen con una sola unidad SSD detectada. El visor no debe mostrar una segunda franja oscura ni un sobreborde.
2. Comprobar que el borde inferior del sidebar coincide con el borde inferior del panel de gráficos.
3. Redimensionar, maximizar y plegar/restaurar el sidebar; no deben reaparecer líneas decorativas sueltas ni bordes cortados.
4. Probar con 2 o más unidades: ambas tarjetas deben quedar completas; con 3+ debe funcionar el scroll interno.
5. Abrir página interna y volver a Resumen.

## Alcance
Cambios sólo en presentación y sincronización geométrica: `gui/dashboard.py`, `gui/dashboard_layout.py`, `gui/workspace_background.py`, `main.py`. Se conservan contratos REAL_OR_NA y REAL_FPS_OR_NA_ONLY.

## Limitación
La comprobación real del posicionamiento bajo Windows y distintos escalados DPI requiere la ejecución en el equipo del usuario.

---

## Documento original: `VALIDACION_V414_SURFACE_STUDIO.md`

# V414 · Surface Studio

## Objetivos
1. Eliminar la separación azul llamativa a la derecha del sidebar.
2. Rehacer la capa inferior nativa compartida, sin rediseñar tarjetas ni reinstalar un wallpaper.
3. Conservar V413: SSD sin sobreborde y sidebar alineado al final de los gráficos.

## Código
- `gui/workspace_background.py`: compositor nativo V414 con superficies cromáticas sin artefactos geométricos.
- `gui/dashboard_layout.py`: margen izquierdo del contenido adaptable; margen derecho conservado.
- `main.py`: geometría inicial coherente con la alineación responsiva.
- `core/version.py`: V414.

## Prueba en Windows
Ejecutar `python main.py`; revisar Resumen maximizado y ventana normal, bordes junto al sidebar, nombre del equipo, SSD y unión entre almacenamiento y gráficos. Comprobar otras pestañas y cambio de tema.

## Política
REAL_OR_NA; REAL_FPS_OR_NA_ONLY; telemetría y funciones sin cambios.

---

## Documento original: `VALIDACION_V415_GLASS_CARD_EFFECT.md`

# Validación V415 · GLASS_CARD_EFFECT

## Objetivo
Crear un efecto visual de transparencia en las tarjetas sin usar transparencia alfa real, manteniendo estabilidad y legibilidad.

## Cambios
- `core/theme_manager.py`: nuevos roles derivados para superficies glass.
- `main.py`: tarjetas principales, almacenamiento y gráficos usan `glass_surface` / `glass_surface_2`.
- `gui/dashboard.py`: cards y hover del Resumen usan la nueva paleta glass.

## Comprobaciones
- Sintaxis Python: PASS
- Integridad del ZIP: pendiente de empaquetado final
- Render real en Windows: pendiente del usuario

---

## Documento original: `VALIDACION_V416_GLASS_CARD_VISIBLE.md`

# V416 · Verificación del glass óptico

1. Confirmar en Resumen que las tarjetas tienen tono azul cristal, borde ligeramente luminoso y reflejo en borde superior.
2. Comprobar las cuatro tarjetas de estado, tres métricas CPU/RAM/GPU, CorePulse AI y las tarjetas SSD tras actualizar telemetría.
3. Cambiar el tema en Personalización y volver a Resumen; verificar que el tinte no queda azul de otro tema.
4. Redimensionar/maximizar y colapsar el sidebar: comprobar que no aparecen brillos entre tarjetas, ni esquinas cuadradas, ni sobrebordes SSD.
5. Verificar los enlaces y barras de progreso; no hay modificaciones a sus eventos o datos.

## Límites
- En Windows debe comprobarse el resultado visual final; una prueba aislada de Tk no sustituye el programa completo.
- Es glass óptico, no translucidez real del sistema operativo.

## Pruebas previas al empaquetado
- Compilación de módulos modificados.
- Pruebas con display virtual Tk: 5 grupos PASS (clip, brillo, temas, wrappers, resize).
- Verificación de archivo ZIP y manifiesto.

---

## Documento original: `VALIDACION_V417_SINGLE_GLASS_NO_RECTANGLES.md`

# Validación V417 · CLEAN_SINGLE_LAYER_GLASS

## Defecto corregido
En V416, `GlassCardVisuals.register()` descendía hasta 3 niveles y pintaba un reflejo en cada `CTkFrame` transparente. Tk y CustomTkinter componen esos lienzos como superficies independientes, dejando barras o rectángulos oscuros sobre tarjetas de estado, recursos y SSD.

## Implementación
- `gui/glass_cards.py`: sólo la tarjeta raíz recibe el reflejo (`_cp_glass_v417`). Se eliminó la recursión de wrappers transparentes.
- Se mantiene el color glass de V416 y la distribución de V414.
- Brillo especular suave, sin líneas rectas ni remates inferiores y con recorte para esquinas redondeadas.
- SSD añadidos dinámicamente reciben la misma única capa.
- La telemetría, el diagnóstico, la IA local, drivers, gaming y FPS permanecen sin cambios.

## Qué revisar en Windows
1. Resumen: las cuatro tarjetas superiores, CPU/RAM/GPU, SSD y CorePulse AI no deben mostrar barras ni rectángulos oscuros sobre sus textos.
2. Redimensionar la ventana, maximizar y contraer el sidebar sin reaparición de recuadros.
3. Comprobar que el color glass se conserva en hover y al cambiar de tema.
4. Confirmar que sigue correcto el borde inferior entre sidebar y gráficos.

**Nota:** no se puede dar por validado el renderizado final de CustomTkinter en Windows sin ejecutar esa aplicación allí.

## CorePulse AI
El estado «El modelo local se cerró» proviene del administrador real de llama.cpp (`MODEL_EXITED`), no es un problema de pintura. Buscar `corepulse_ai_model.log` y `corepulse_ai_autostart.log` en el directorio de logs que devuelve `core.runtime_paths.log_path()` para diagnosticarlo sin suponer una causa.

---

## Documento original: `VALIDACION_V418_SIDEBAR_PERSONALIZATION_UNIFIED.md`

# Validación V418 · SIDEBAR_PERSONALIZATION_UNIFIED

## Objetivo
Unificar visualmente el bloque Personalización con el resto del sidebar y mejorar la alineación del panel lateral con los gráficos del Resumen.

## Cambios
- `gui/dashboard.py`: Temas/CorePulse AI usan la misma geometría base del sidebar y se ajusta el cálculo de altura del sidebar.
- `gui/dashboard_layout.py`: el layout responsivo conserva la misma lógica visual para Personalización en todos los anchos/alturas.

## Verificación
- Sintaxis Python: PASS
- Integridad del ZIP: pendiente de empaquetado
- Render real en Windows: pendiente del usuario

---

## Documento original: `VALIDACION_V419_SIDEBAR_EXACT_CHART_ALIGNMENT.md`

# Validación V419 · SIDEBAR_EXACT_CHART_ALIGNMENT

## Objetivo
Eliminar el desalineado residual entre el sidebar y el panel de gráficos del Resumen.

## Cambios
- `gui/dashboard.py`: el cálculo de altura del sidebar usa directamente la altura real del panel de gráficos.
- `gui/dashboard.py` y `gui/dashboard_layout.py`: se compacta el bloque Personalización.

## Verificación
- Sintaxis Python: PASS
- Render real en Windows: pendiente del usuario

---

## Documento original: `VALIDACION_V420_SIDEBAR_BORDER_TRIM.md`

# Validación V420 · SIDEBAR_BORDER_TRIM

## Objetivo
Eliminar el posible borde/línea residual que aún deja el sidebar más abajo que el panel de gráficos.

## Cambios
- `gui/dashboard.py`: espesor del perímetro nativo reducido a 1 px; recorte visible de 2 px al cierre del sidebar.
- `gui/dashboard.py` y `gui/dashboard_layout.py`: footer de Personalización más compacto.

## Verificación
- Sintaxis Python: PASS
- Render real en Windows: pendiente del usuario

---

## Documento original: `VALIDACION_V421_SIDEBAR_FRAME_REMOVED.md`

# Validación V421 · SIDEBAR_FRAME_REMOVED

## Objetivo
Eliminar el cuadro visual que rodea los botones del sidebar para que el menú quede en la primera capa.

## Cambios
- `main.py`: sidebar sin borde (`border_width=0`).
- `gui/dashboard.py`: se retira el perímetro nativo/custom del sidebar; el helper queda solo para mantener altura/alineación.

## Verificación
- Sintaxis Python: PASS
- Render real en Windows: pendiente del usuario

---

## Documento original: `VALIDACION_V422_SIDEBAR_FIRST_LAYER_INTEGRATION.md`

# Validación V422 · SIDEBAR_FIRST_LAYER_INTEGRATION

## Objetivo
Hacer que el sidebar forme parte de la primera capa visual del producto, en lugar de verse como un panel oscuro separado.

## Cambios
- `main.py`: sidebar transparente y registrado en `workspace_background`.
- `gui/dashboard.py`: la reconstrucción del sidebar conserva el fondo transparente y vuelve a registrarlo como superficie estructural.
- `gui/dashboard_layout.py`: el layout responsivo ya no restituye un fondo sólido para el sidebar.

## Verificación
- Sintaxis Python: PASS
- Render real en Windows: pendiente del usuario

---

## Documento original: `VALIDACION_V423_SIDEBAR_PERSONALIZATION_UNIFIED_BUTTONS_FLAT.md`

# Validación V423 · SIDEBAR_PERSONALIZATION_UNIFIED_BUTTONS_FLAT

## Objetivo
- Hacer que Personalización se construya exactamente igual que las demás secciones del sidebar.
- Eliminar el color oscuro/feo residual que seguía viéndose en los botones del lateral.

## Cambios
- `gui/dashboard.py`: Personalización deja de usar un `CTkFrame` propio y pasa a construirse directamente en `app.sidebar`.
- `gui/dashboard_layout.py`: navegación lateral y botones de Personalización se aplanan con `bg_color='transparent'` y hover transparente cuando no están activos.
- `main.py`: se alinean los estilos base de los botones laterales para evitar flashes de color antes del reflow del dashboard.

## Verificación
- Sintaxis Python: PASS
- Render real en Windows: pendiente del usuario

---

## Documento original: `VALIDACION_V424_SIDEBAR_HOVER_RUNTIME_FIX.md`

# V424 · Corrección del bloqueo de arranque en CustomTkinter

**Error original**: `ValueError: transparency is not allowed for this attribute` en `main.py`, al construir `btn_overlay`.

**Causa**: `CTkButton` acepta `fg_color='transparent'`, pero no acepta `hover_color='transparent'`. V423 puso este último en varios botones y llamadas `configure`.

**Corrección**: color de hover válido ligado al tema, hover desactivado en botones de navegación construidos en el arranque y en Personalización, y auditoría de todos los archivos Python.

**Pruebas**: `python -m compileall`; prueba automatizada de búsqueda de atributos inválidos y estructura de Personalización; integridad del ZIP.

**Pendiente**: comprobación del arranque y visual real en Windows del usuario.

---

## Documento original: `VALIDACION_V425_SIDEBAR_NATIVE_CONTROL_SURFACE.md`

# CorePulse V425 — Superficie nativa para controles del sidebar

## Motivo
En V424, el menú permanecía sobre la primera capa, pero CTkButton y CTkLabel heredaban un fondo distinto del diseño procedural. El resultado eran rectángulos casi negros alrededor de todas las opciones y encabezados, incluido Personalización.

## Implementación
- `gui/workspace_background.py`: `native_surface_color_at()` replica el sustrato de Surface Studio por coordenadas absolutas de la ventana. `_paint_sidebar_controls()` repinta en los Canvas de los botones y etiquetas, sincroniza el fondo de sus labels internos y preserva los botones activos.
- `gui/dashboard.py`: registra contenedores transparentes del sidebar para que utilicen la misma superficie compartida.
- `gui/dashboard_layout.py`: solicita una actualización de pintura después de aplicar el reflow de navegación.
- `gui/dashboard.py`: Personalización conserva su construcción directa en `app.sidebar` (sin contenedor especial).
- Sin cambios en la lógica de IA, telemetría, SSD ni benchmarks.

## Pruebas aisladas (Linux + Xvfb, sin CustomTkinter instalado)
- Igualdad por píxel del color procedural: PASS (varios tamaños y temas).
- Simulación real Tk de CTkButton/CTkLabel: PASS; seleccionado conserva color azul y controles inactivos coinciden con la superficie.
- Contrato sin hover_color transparente: PASS (regresión V424).
- Sintaxis Python: PASS.

## Pendiente
- Ejecutar `python main.py` en Windows con CustomTkinter real. Confirmar ausencia de parches negros, navegación, cambio de pestaña/tema y tamaño de ventana.

---

## Documento original: `VALIDACION_V426_TOP_STATUS_CARD_OVERBORDER_FIX.md`

# Validación V426 · TOP_STATUS_CARD_OVERBORDER_FIX

## Objetivo
Eliminar el efecto de sobreborde o doble contorno en la franja superior del Resumen sin alterar el resto del dashboard.

## Cambios
- `gui/dashboard.py`: `ai_card`, `_health_status_card` y `_status_card` pasan a `border_width=0`.
- Se mantiene `corner_radius=15`, el acento lateral y la misma superficie base.

## Verificación
- Sintaxis Python: PASS
- Render real en Windows: pendiente del usuario

---

## Documento original: `VALIDACION_V427_TOP_STATUS_BORDER_AUTHORITY_FIX.md`

# Validación V427 — eliminación definitiva del borde externo superior

Causa verificada: en V426 `dashboard.py` construía las 4 tarjetas con
`border_width=0`, pero `dashboard_layout.py::_style_status_band()` las
reconfiguraba con `border_width=1` después del montaje.

Corrección:
- Estilo inicial: `border_width=0` en tarjetas de Salud, Supervisión, Trazabilidad y Sesión.
- Reflow compacto, estándar y amplio: también `border_width=0`.
- CorePulse AI ya se construía sin borde y se conserva sin modificaciones.
- CPU/RAM/GPU/SSD, sidebar y telemetría: sin cambios.

Prueba manual en Windows: abrir Resumen, maximizar y restaurar la ventana,
cambiar de pestaña y volver. Las cuatro tarjetas deben conservar los laterales
de color, pero no recuperar el contorno extra exterior.

---

## Documento original: `VALIDACION_V428_STATUS_ROW_LAYER_AND_GAP_FIX.md`

# CorePulse V428 — validación de fila superior

Base: V427 (mantiene los cambios aprobados de V425).

## Causas revisadas
1. La fila de tarjetas estaba separada del encabezado por un espacio estructural innecesario.
2. Los controles anidados de Salud del sistema heredaban un fondo opaco distinto del glass.
3. Las cuatro tarjetas superiores recibían una película de brillo adicional además del material glass.

## Cambios
- `gui/dashboard.py`: encabezado más compacto y superficies internas de Salud sincronizadas.
- `gui/dashboard_layout.py`: altura y separación del encabezado coherentes en todos los modos.
- `gui/glass_cards.py`: sin reflejo extra en la fila superior; sí en AI/CPU/RAM/GPU/SSD.
- `tests/test_v428_status_band_surface_contract.py`: test de geometría, materiales y registro efectivo de glass.

## Verificar en Windows
1. Iniciar `python main.py` y entrar a Resumen.
2. Confirmar que la fila de estado comienza más cerca del encabezado y sin capa superior duplicada.
3. Confirmar que Salud no muestra recuadros oscuros en el icono/texto/porcentaje.
4. Probar ventanas normales, maximizado y cambio de pestaña.
5. Verificar que el sidebar de V425, la IA y las telemetrías siguen funcionando.

Estas verificaciones visuales no pueden confirmarse aquí sin ejecutar el programa completo en Windows.

---

## Documento original: `VALIDACION_V429_CHARTS_OUTER_CONTAINER_BORDER_REMOVED.md`

# Validación V429 · CHARTS_OUTER_CONTAINER_BORDER_REMOVED

## Objetivo
Eliminar el borde del cuadro exterior que encapsula los gráficos CPU, RAM y GPU.

## Cambios
- `main.py`: `frame_charts` pasa a `border_width=0`.
- `gui/dashboard_layout.py`: `_style_charts()` deja de restaurar el borde del contenedor.

## Verificación
- Sintaxis Python: PASS
- Render real en Windows: pendiente del usuario

---

## Documento original: `VALIDACION_V430_CHARTS_CONTAINER_BLEND_NO_BOX.md`

# Validación V430 · CHARTS_CONTAINER_BLEND_NO_BOX

## Objetivo
Eliminar la lectura visual de “caja” del contenedor grande que agrupa CPU, RAM y GPU.

## Cambios
- `frame_charts` adopta el fondo principal del dashboard.
- La figura y el widget Tk del canvas comparten ese fondo.
- Se quitan acentos decorativos del contenedor exterior.

## Verificación
- Sintaxis Python: PASS
- Render real en Windows: pendiente del usuario

---

## Documento original: `VALIDACION_V431_CHARTS_CANVAS_PERIMETER_LINES_REMOVED.md`

# Validación V431 · CHARTS_CANVAS_PERIMETER_LINES_REMOVED

## Objetivo
Eliminar las líneas del perímetro del lienzo de gráficos (izquierda, derecha e inferior).

## Cambios
- `main.py`: figura Matplotlib sin frame y canvas Tk sin borde ni relieve.
- `gui/dashboard_layout.py`: los reflows y reajustes mantienen el canvas sin perímetro.

## Verificación
- Sintaxis Python: PASS
- Render real en Windows: pendiente del usuario

---

## Documento original: `VALIDACION_V432_CHARTS_UNIFIED_SURFACE_NO_OUTER_FRAME.md`

# CorePulse V432 · Validación del marco exterior de gráficos

## Defecto reproducido desde capturas V429–V431
El área CPU / RAM / GPU conservaba un perímetro porque tres rutas del proyecto configuraban `frame_charts` de manera contradictoria. En particular, `_style_charts()` en `gui/dashboard.py` reactivaba `border_width=1` y `border_color=COLORS['border']` después de desactivarlos desde `main.py` y `dashboard_layout.py`. V431 añadió un rectángulo negro al establecer `Figure(frameon=False)`.

## Cambios
- `main.py`: la tarjeta contenedora nace sin borde y con el mismo color que el fondo de figura y TkAgg; Matplotlib utiliza `frameon=True` y un relleno opaco consistente.
- `gui/dashboard.py`: el estilizado profesional conserva `border_width=0`, retira acentos adicionales de esta caja y reestablece `Figure(frameon=True)` con fondo sin contorno; mantiene intactos los gráficos internos.
- `gui/dashboard_layout.py`: el estilizado responsivo utiliza el mismo material para `frame_charts`, la figura y el canvas, sin reponer marcos ni recurrir a transparencias no soportadas.
- `tests/test_v432_chart_frame_contract.py`: pruebas de regresión sobre las tres rutas y píxeles del fondo real de Matplotlib.

## Validaciones
- Compilación de sintaxis Python: PASS
- Pruebas automáticas de integración visual con pantalla Xvfb: 20/20 PASS
- Integridad del ZIP: pendiente en esta etapa; se comprueba al empaquetar
- Prueba del programa completo sobre Windows: **pendiente de validación por el usuario**

## Alcance
No se alteran la fuente de telemetría, sensores, datos reales, ejes, curvas, navegación, sidebar, IA, salud, diagnóstico, SSD ni tarjetas restantes.

---

## Documento original: `VALIDACION_V433_CHARTS_OUTER_MARGIN_BLEND_FIX.md`

# Validación V433 · CHARTS_OUTER_MARGIN_BLEND_FIX

## Objetivo
Eliminar los bordes más oscuros que sobresalen alrededor del bloque de gráficos CPU/RAM/GPU.

## Cambios
- `frame_charts` se integra al fondo principal del dashboard.
- El Figure y el canvas de Matplotlib usan el mismo fondo exterior.
- Se preserva el fondo interno oscuro de cada gráfico.

## Verificación
- Sintaxis Python: PASS
- Render real en Windows: pendiente del usuario

---

## Documento original: `VALIDACION_V434_CHARTS_NATIVE_SURFACE_MATCH.md`

# V434 · CHARTS_NATIVE_SURFACE_MATCH

## Objetivo
Eliminar el rectángulo negro aparecido en V433 y los límites visibles alrededor de los gráficos.

## Implementación
- El fondo de la figura se construye desde los mismos cálculos de `native_surface_color_at` empleados por el fondo maestro.
- La figura y el contenedor dejan de introducir un color plano ajeno a la superficie.
- La actualización se realiza solo al recrear/reajustar los gráficos, no en cada muestra de telemetría.
- Salud del sistema conserva un material interior idéntico al color de su tarjeta.

## Validación
- Prueba de muestreo 1:1: PASS
- Rasterización Agg: PASS
- Pruebas automatizadas con pantalla virtual: PASS (23 pruebas)
- Sintaxis Python: PASS
- Render real en Windows: pendiente de revisión del usuario

---

## Documento original: `VALIDACION_V436_CARDS_TRUE_WORKSPACE_SURFACE.md`

# Validación V436 · CARDS_TRUE_WORKSPACE_SURFACE

## Objetivo
Eliminar bloques de color superpuestos en tarjetas y alinearlas con el fondo maestro existente.

## Cambios
- Pincel Tk nativo en cada tarjeta y contenedor interior.
- Superficie exacta, sin tinte opaco ni película adicional.
- Sin hover opaco, manteniendo interacciones y botones de detalles.
- Material sincronizado por una autoridad, incluyendo cambio de tamaño y tema.

## Verificación
- Pruebas `test_v*.py`: 25 OK en entorno virtual Tk/Xvfb.
- Prueba de coincidencia cromática Canvas/superficie a varias alturas: PASS.
- Revisión de sintaxis: PASS.
- Render completo en Windows: pendiente del usuario.

---

## Documento original: `VALIDACION_V437_CHARTS_ALIGNED_ACCENT_HOVER.md`

# V437 · Validación de alineación y hover

Base: CorePulse V436.

## Contrato visual
- `gui/dashboard_layout.py`: los tres ejes toman su X/anchura directamente de CPU, RAM y GPU. Reserva de margen para ticks Y. Sin alterar muestras, FPS, ni telemetría.
- `gui/card_workspace_surface.py`: el hover se calcula sobre la capa nativa por columna/altura y el acento de cada función; al salir, desaparece completamente.
- `gui/dashboard.py`: los cambios hover no cambian la geometría; se conserva la acción de detalle, click y tooltip.
- `gui/live_health_binding.py` y `gui/ai_status_card.py`: el tono del hover respeta el estado real de la salud y de CorePulse AI.

## Validación
- Unit tests y pruebas Tk virtuales: realizadas y aprobadas.
- Sintaxis Python: realizada y aprobada.
- Inicio gráfico completo en Windows: pendiente de comprobación en el equipo del usuario.

---

## Documento original: `VALIDACION_V438_SUBTLE_HOVER_FEATHER_NO_TILES.md`

# CorePulse V438: evaluación de hover suave

## Objetivo
Evitar los halos con forma de rectángulo sólido vistos en V437 y conservar el fondo maestro aprobado.

## Cambios
- `gui/card_workspace_surface.py`: iluminación local con caída horizontal y vertical, sin tintes uniformes en el fondo de widgets hijos.
- `tests/test_v437_chart_columns_and_card_glow.py`: comprueba diferencias de intensidad en la zona media donde existe halo.
- `tests/test_v438_soft_hover_feather_contract.py`: comprueba atenuación a cero en los bordes, no extender glow por todo el ancho y restauración exacta al salir.

## Validación
- 32 tests Tk/Xvfb: PASS
- Sintaxis Python: PASS
- Arranque y aspecto en Windows: pendiente de prueba del usuario

---

## Documento original: `VALIDACION_V439_HOVER_CANVAS_TILE_ROOT_FIX.md`

# V439 · Eliminación de cuadrados generados por el hover

## Problema observado en el video
Los iconos/textos y el fondo de las tarjetas mostraban bloques cuadrados durante el movimiento del puntero. En V437/V438 se añadían rectángulos de iluminado sobre los CTkCanvas de las tarjetas y también sobre algunos marcos anidados, que tienen capas internas independientes en CustomTkinter.

## Corrección de raíz
- Se elimina el raster de hover en todas las tarjetas del dashboard.
- Se elimina el repintado recursivo que se ejecutaba por cada entrada/salida del mouse.
- El hover sólo aclara el acento lateral ya existente (sin cambiar su ancho), y al salir devuelve su color real.
- Se marca el acento para excluirlo del render de superficies estructurales incluso mientras está iluminado.
- Las tarjetas conservan su fondo nativo, los ejes y la alineación de gráficos.

## Pruebas
- Unitarias/Tk virtual: suite V424–V439; sin capas de hover después de transiciones repetidas.
- CustomTkinter en Windows: **pendiente de prueba del usuario**. El entorno local no permite instalar CustomTkinter durante esta ejecución.
- No se realizaron ajustes de telemetría, IA, drivers ni sensores.

---

## Documento original: `VALIDACION_V440_NO_TOP_HEADERS.md`

# V440 · Sin cabeceras introductorias de las páginas internas

## Requisito
Eliminar todos los títulos, subtítulos, insignias, botones y otros elementos ubicados en las cabeceras superiores de todas las pestañas del menú, recuperando el espacio vertical y mostrando el contenido inmediatamente inferior. No tocar las tarjetas funcionales, sus textos ni los controles de operación.

## Cobertura
- Benchmark
- Limpieza de sistema
- Tweaks de Windows 11
- Red avanzada / Conectividad
- Gaming
- CorePulse AI
- Temas
- Alertas técnicas
- Historial de alertas
- Tendencias
- Overlay In-Game
- Diagnóstico
- Centro de salud
- CPU / GPU / RAM / SSD (detalles)
- Trazabilidad de telemetría

## Protección de funcionalidades
- Las cabeceras dejan de insertarse en Tk (`pack`/`grid`), pero conservan sus referencias y actualizaciones internas para que no fallen los callbacks existentes.
- Sensores y Cancelar del Diagnóstico, y Actualizar en SSD y Trazabilidad, se trasladan a áreas del contenido visible.
- Tweaks impide que restaurar de nuevo el Centro de restauración haga reaparecer la cabecera.

## Verificación
- Sintaxis Python: verificar con compileall.
- Pruebas: test_v440_page_headers_removed, pruebas anteriores.
- Validación real en Windows: pendiente.

---

## Documento original: `VALIDACION_V442_NATIVE_CARD_PERIMETER_GLOW.md`

# Validación V442 · Native Card Perimeter Glow

- Base estable V440, con cabeceras eliminadas.
- Corrige el versionado inconsistente reportado por V441.
- Iluminación visible sobre el canvas nativo de las tarjetas, sin depender del border_width de CTkFrame.
- Respeta el fondo maestro original, iconos, textos, barras de telemetría y áreas funcionales.
- La entrada y salida del mouse fuerzan sólo el redibujado de la tarjeta activa.
- La tarjeta de Sesión tiene hover visual pero ninguna acción de clic.
- Probar visualmente en Windows: CPU, RAM, GPU, SSD, salud, supervisión, trazabilidad, sesión y AI.

---

## Documento original: `VALIDACION_V443_GLOW_LIGERO_ESQUINAS.md`

# V443 · Glow ligero con esquinas redondeadas

Base: V442. Se conserva la superficie maestra, alineación de gráficos, sidebar y vistas internas sin cabecera.

## Causa verificada en código

V442 generaba múltiples trazos separados cada 16 píxeles para cada distancia del perímetro y reconstruía todo el árbol visual de la tarjeta al entrar/salir con el mouse. Como no respetaba `corner_radius`, iluminaba esquinas cuadradas.

## Correcciones

- 3 curvas cerradas de perímetro redondeado, como máximo, por canvas que toca el borde real de la tarjeta.
- Los trazos siguen `corner_radius`, son recortados al canvas y evitan las esquinas exteriores cuadradas.
- Caché por geometría, acento, paleta y tamaño; el mismo estado no recrea objetos Tk.
- En hover se actualizan solo los trazos y la franja lateral, sin volver a dibujar el fondo ni tocar los textos, íconos, barras o botones.
- Primera entrada antes del pintado inicial mantiene un fallback de inicialización única.
- Sin datos simulados: REAL_OR_NA y REAL_FPS_OR_NA_ONLY no se alteran.

## Verificación

- Sintaxis Python y suite de regresión ejecutadas en entorno Tk virtual.
- Una prueba de CustomTkinter queda omitida porque el paquete no está instalado en el entorno de pruebas.
- Validación visual final en Windows real: pendiente del usuario.

---

## Documento original: `VALIDACION_V444_SEAMLESS_INNER_CHART_AXES.md`

# V444 · Pruebas de regresión de gráficos sobre fondo maestro

- Partida: V443 completa.
- Sólo se elimina el relleno rectangular y los spines de CPU, RAM y GPU.
- El fondo global continúa proveniendo de `sampled_workspace_background` / `figimage`.
- Las curvas CPU/RAM/GPU, ticks, cuadrículas, alineación y el hover V443 se conservan.
- Comprobación visual en el Windows del usuario: pendiente.

---

## Documento original: `VALIDACION_V445_CHART_COLUMNS_LEFT_ALIGNMENT.md`

# V445 · Alineación horizontal de gráficos

Base V444. Cambio único: desplazar 20 px a la izquierda CPU, RAM y GPU por geometría relativa a las tarjetas. No cambia ancho, posición vertical, curva, ejes ni la superficie maestra.

Validación: pruebas automatizadas del cálculo de columnas, sintaxis Python y comprobación de integridad del ZIP. Representación final en Windows: pendiente.

---

## Documento original: `VALIDACION_V447_AI_NATIVE_INTEGRATED.md`

# Validación V447 · IA integrada a la capa maestra

## Base y alcance
- Única base: V445 `CorePulse_V445_WINDOWS_CHART_COLUMNS_LEFT_ALIGNMENT.zip`.
- No se incorporan las ramas descartadas V446/V447 de gráficos.
- Tarjeta superior de CorePulse AI: texto centrado, un único estado dinámico REAL_OR_NA y franja de estado.
- La tarjeta no usa etiquetas ni marcos CTk interiores que generen un rectángulo opaco.
- `AIStatusCanvas` se registra mediante `WorkspaceBackground.register_canvas` para pintar exactamente el mismo fondo maestro de la ventana. El hover V445 dibuja su halo en este mismo canvas, no detrás de él.
- El resto de tarjetas, los gráficos, los sensores y las llamadas IA permanecen con código idéntico a V445.

## Comprobaciones
- Suite heredada V445 + pruebas V447 con `xvfb-run -a python -m unittest discover -s tests -q`.
- Un test dinámico monta el canvas real de Tk, comprueba la textura nativa y su conservación tras cambios de estado y anchura.
- En Windows, abrir el Resumen y comprobar integración visual, modo ventana, hover, cambio de tema, redimensionado y acceso al centro de IA haciendo clic en la tarjeta. El resultado visual final requiere comprobarse en Windows.

---

## Documento original: `VALIDACION_V455_HOVER.md`

# CorePulse V455 — Hover del sidebar

## Origen
Versión creada exclusivamente desde `CorePulse_V451(1).rar` subido por el usuario.
No mezcla los cambios de la rama V452–V454.

## Error encontrado
El controlador de la capa maestra aplanaba los `CTkButton` y sobrescribía
`hover_color` con el mismo color de fondo del botón. También mantenía un
bitmap superpuesto a la pintura interna, ocultando cualquier variación nativa.

## Solución
- Se asocia hover reversible a cada botón existente del sidebar.
- La misma función que reproduce el fondo maestro dibuja el resaltado sobre el
  canvas interno del botón; no se añaden tarjetas ni widgets extra.
- Se conservan botones seleccionados, clics, comandos, el icono y el texto.
- Debounce de 45 ms para evitar parpadeos entre los elementos internos.

## Verificación
- 10 pruebas del área de sidebar: correctas; una prueba antigua excluida por
  un supuesto incorrecto de Canvas Tk (`fill` en elementos de imagen).
- Suite completa comparada con el RAR original: exactamente los mismos siete
  fallos existentes y la misma subprueba fallida. No aparecen fallos nuevos.
- AST comprobado para 197 archivos Python; sin errores.
- El ZIP debe verificarse con `ZipFile.testzip()`.

## Prueba en Windows pendiente
Abrir Resumen, pasar el mouse por Benchmark, Centro de salud, Tendencias,
Temas y CorePulse AI. Comprobar que se resalta el botón bajo el puntero y
que el efecto desaparece al salir, tanto sobre icono como sobre texto.

---

## Documento original: `VALIDACION_V456_SIDEBAR_MOTION.md`

# CorePulse V456 · Validación de animación del sidebar

**Base:** CorePulse V455 nativo derivado del RAR `CorePulse_V451(1).rar` del usuario.

## Código modificado
- `gui/sidebar_native_hover.py`: movimiento de contenido de hasta 5 px y fade in/out con `after` cancelable. Sin nuevas capas ni widgets. Control de solo una opción hover activa.
- `gui/workspace_background.py`: interpolación cromática dentro del CTkButton actual. Nuevo repintado parcial `_paint_sidebar_controls_target` con el contrato `_paint_sidebar_controls()` intacto.
- `core/version.py`: V456.
- `tests/test_v455_sidebar_native_hover.py`: adapta el tiempo esperado a la animación y comprueba icono/texto, reversión, selección, controles deshabilitados, orden entre opciones y estabilidad de geometría.

## Tests
- Sidebar (Tk real con Xvfb, botones de prueba): **8 de 8 correctas**.
- Suite general V455 original: **7 fallos, 51 correctas, 1 omitida, 37 subpruebas correctas**.
- Suite general V456: **7 fallos, 55 correctas, 1 omitida, 37 subpruebas correctas**.
- **Ningún fallo nuevo respecto a la base.** Los 7 fallos preexistentes incluyen pruebas de contratos antiguos y dependencias no instaladas.
- Aún se requiere comprobar el efecto en Windows con CustomTkinter real; las pruebas Tk simuladas no sustituyen dicha verificación.

## Prueba manual Windows
1. Abrir el Resumen; pasar el mouse por Benchmark, Centro de salud, Alertas técnicas, Tendencias, Temas y CorePulse AI.
2. Comprobar que icono y texto se mueven discretamente a la derecha y vuelven al salir; el fondo se aclara progresivamente.
3. Mover el puntero rápidamente entre dos opciones. La anterior debe dejar de reaccionar sin mantener una tarjeta iluminada.
4. Probar en maximizado y en ventana normal. La anchura de los botones, el sidebar, los clics y la opción seleccionada deben permanecer estables.

---

## Documento original: `VALIDACION_V457_STORAGE_HEALTH_LEFT_UPTIME_RESTART.md`

# VALIDACIÓN V457 — STORAGE_HEALTH_LEFT_UPTIME_RESTART

## Alcance
- Reubicar la salud de discos hacia la izquierda, junto a capacidad/uso.
- Sustituir “Ver detalles” por un botón con icono de ojo en el extremo derecho.
- Hacer reactiva la tarjeta de “Tiempo activo”.
- Mostrar recomendación de reinicio + botón de reinicio al superar 10 horas.

## Archivos modificados
- `main.py`
- `gui/dashboard.py`
- `gui/hardware_storage_view.py`
- `core/version.py`
- `CHANGELOG.md`

## Validación técnica
- `python -m py_compile main.py gui/dashboard.py gui/hardware_storage_view.py core/version.py` ✅

## Resultado esperado
1. En cada disco, la línea de capacidad muestra capacidad/uso y a su lado la píldora de salud.
2. El botón del extremo derecho del encabezado del disco muestra un ojo y abre detalles del disco.
3. La tarjeta de uptime se mantiene morada en condiciones normales.
4. Entre 8 h y 9:59 h la tarjeta entra en advertencia.
5. Desde 10 h en adelante, el icono y el valor cambian a rojo, aparece el texto recomendando reinicio y se habilita el botón `Reiniciar PC`.
6. Al pulsar `Reiniciar PC`, CorePulse pide confirmación antes de solicitar el reinicio de Windows.

---

## Documento original: `VALIDACION_V458_SCROLL_Y_IA.md`

# Validación V458

- Base V457 conservada, sin alterar telemetría ni lógica de diagnóstico.
- Vista de almacenamiento: altura de una fila (86 px), scroll visible a partir de dos discos, sistema C: en primera posición.
- El scroll conserva su posición durante refrescos de sensores.
- IA: icono de apagado/encendido dibujado sobre el mismo canvas; clic no abre el centro de IA.
- El estado apagado se persiste en AppData. El administrador detiene sólo sus procesos; procesos externos permanecen ajenos.
- Pruebas automáticas V458: 6/6 superadas en Tk virtual, incluyendo interacción real del canvas.
- Suite heredada: ocho fallos preexistentes tanto en V457 como en V458 por dependencias/contratos antiguos; sin fallos nuevos.
- No validado aún en Windows con CustomTkinter real (dependencia no disponible en el entorno de pruebas).

---

## Documento original: `VALIDACION_COREPULSE_V475.txt`

COREPULSE V475 · REGISTRO DE VALIDACIÓN

Base: V474 Educational Safety Refinement.
Motor independiente: V475 CorePulse Intelligence Engine.
Pruebas cloud y motor (V459-V475): 278 PASS.
Pruebas nuevas V475: 23 PASS (incluye endpoints reales con TestClient sin conexión pública).
Ejecutor offline sintético: COREPULSE_INTELLIGENCE_V475_PASS.
Regresión completa antes de las 2 últimas pruebas HTTP: 322 PASS, 20 FAIL, 3 SKIP, 37 subtests PASS.
Los 20 fallos corresponden a contratos antiguos de GUI (Tk requiere pantalla gráfica o tests de interfaz viejos); estaban presentes en V474.
Las 2 pruebas HTTP nuevas se ejecutaron aparte y pasaron; no modifican la GUI.
No hay mediciones reales de temperatura, FPS, latencia cloud ni validación gráfica Windows en este entorno.
No se consultó el servicio real Groq en este ciclo.
La interpretación es apoyo informativo, no confirmación de fallas.

Para probar en Windows: 23_VALIDAR_INTELIGENCIA_V475.bat
