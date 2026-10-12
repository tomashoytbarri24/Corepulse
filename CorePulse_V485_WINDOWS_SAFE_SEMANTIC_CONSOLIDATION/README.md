# CorePulse V485 — Consolidación semántica segura (Windows)

**Programa:** CorePulse principal para Windows. **Fuente de FPS de juegos:** únicamente RTSS Shared Memory; ausencia de mediciones certificadas = `N/A` (`REAL_FPS_OR_NA_ONLY`). Telemetría: `REAL_OR_NA`. CorePulse AI interpreta evidencia real y requiere consentimiento cuando corresponde.

**Inicio:** `Iniciar_CorePulse.bat` (o `CorePulse.vbs`). **Dependencias:** `instalar_dependencias.bat`.

**Cambios V485:** se consolidaron la validación de arranque y la autocomprobación del EXE en `core/startup_readiness`, y la persistencia longitudinal de salud con tendencias de sesiones en `core/session_trends`. Las rutas históricas de importación siguen disponibles. Las auditorías V480–V484 se archivaron sin perder contenido en [`docs/historico/AUDITORIAS_V480_V484.md`](docs/historico/AUDITORIAS_V480_V484.md). El informe actual está en [`docs/AUDITORIA_V485.md`](docs/AUDITORIA_V485.md).

**Importante:** V484 fue probada en Windows por el usuario; V485 requiere probar el inicio, guardado de historial, diagnósticos y self-test del ejecutable en Windows real antes de considerarla estable.

---

> **V484 — Windows Internal Dedup:** las consolidaciones y pruebas están descritas en `docs/historico/AUDITORIAS_V480_V484.md`. Validar en Windows antes de adoptarla como versión estable.

> **V483 — Windows Safe Consolidation:** proyecto completo; ver `docs/historico/AUDITORIAS_V480_V484.md` para fusiones, compatibilidad y pruebas.

# CorePulse V482 — Advanced Consolidation · Windows Only

**ZIP completo de código fuente para Windows** basado en V481. **RTSS Only** para FPS de juegos; política `REAL_OR_NA` y sin datos FPS sintéticos. Se consolidaron 14 módulos y se agruparon suites históricas sin perder tests, reduciendo el proyecto **304 → 288 archivos** (188 archivos Python). CorePulse AI, Game Boost, benchmarks y RTSS mantienen el código interno de V481.

**Para iniciar:** `Iniciar_CorePulse.bat` tras instalar las dependencias desde `instalar_dependencias.bat`. **Documentación detallada, resultados y limitaciones:** [`docs/historico/AUDITORIAS_V480_V484.md`](docs/historico/AUDITORIAS_V480_V484.md). **Nota:** arranque, RTSS, sensores y EXE todavía deben validarse en Windows real.

---

# CorePulse V481 — Windows Consolidated Refactor

**ZIP completo para Windows**, construido sobre V480 y el motor RTSS Only de V479. Esta entrega mantiene monitoreo, diagnóstico, benchmarks, Game Boost, mantenimiento, reportes PDF, FPS RTSS y CorePulse AI; consolida **37 archivos** sin borrar las funcionalidades.

**Iniciar:** `Iniciar_CorePulse.bat` en Windows (Python 3.12 x64 y dependencias instaladas). **Informe y límites de pruebas:** [`docs/historico/AUDITORIAS_V480_V484.md`](docs/historico/AUDITORIAS_V480_V484.md). **Instalación:** `instalar_dependencias.bat`.

La fuente de FPS de juegos es **sólo RTSS Shared Memory**. Sin lectura medible/vigente se informa **N/A**. Los sensores conservan `REAL_OR_NA`; la infraestructura cloud opcional no significa soporte Linux del cliente Windows. **El arranque real y el EXE deben probarse en Windows** antes de distribuirlos.

---

# CorePulse V480 — Professional Refactor (Windows)

Versión sobre **V479 RTSS Only**. Refactorización conservadora: cuatro fichas comparten primitivas
visuales y de activación, sin alterar el proveedor de FPS, la capa de telemetría ni CorePulse AI.

**Abrir:** `Iniciar_CorePulse.bat` (o `CorePulse.vbs`) en Windows.
**Instalar dependencias:** `instalar_dependencias.bat` cuando sea necesario.
**Auditoría, evidencia y pruebas:** [`docs/historico/AUDITORIAS_V480_V484.md`](docs/historico/AUDITORIAS_V480_V484.md).
**Arquitectura runtime/desarrollo:** incluida en la auditoría V480.

La disponibilidad de FPS requiere RTSS y datos de juego válidos; sin ellos se muestra N/A.
Las pruebas realizadas fuera de Windows no certifican sensores, instalación ni EXE. Antes de distribuir
un binario, ejecutar los BAT de build y pruebas en Windows real.

---

**V479 — Política FPS de juegos:** sólo RTSS Shared Memory. Se retiró completamente PresentMon del ejecutable, la captura y los chequeos. Si RTSS no entrega FPS medidos y válidos, CorePulse muestra N/A. Los FPS del benchmark GPU DirectX provienen de su propio contador de fotogramas y no de RTSS ni de PresentMon.

# CorePulse V478 — Core y GUI organizados por funciones

**Para abrir CorePulse:** haz doble clic en `Iniciar_CorePulse.bat` desde esta carpeta.
**Para conectar CorePulse AI:** abre la pestaña CorePulse AI, concede permiso si corresponde y pulsa **Conectar IA**.
**Configuración de Groq (solo primera vez):** `herramientas/ia/10_CONFIGURAR_GROQ_V463.bat`.

Organización de esta entrega:
- `core/` y `gui/`: ahora tienen subcarpetas temáticas. La importación histórica `core.modulo` y `gui.modulo` permanece válida.
- Consulta `docs/ESTRUCTURA_MODULAR_V478.md` para entender el mapa y las reglas de compatibilidad.
- `core/`, `gui/`, `performance/`, `database/`: módulos funcionales del producto, conservados sin eliminar capacidades.
- `CorePulse_AI_Server/`: puente Groq y motores de análisis propios.
- `herramientas/ia/`: scripts auxiliares y pruebas manuales antes acumulados en la raíz.
- `docs/`: guía vigente y referencias históricas consolidadas.
- `tests/`: pruebas automáticas, conservadas para detectar regresiones.
- `build/`, `installer/`: código y especificaciones de compilación; sin resultados de ejecución antiguos.

Los punteros locales de Python y los resultados de diagnóstico se generan en la instalación/ejecución; no se distribuyen con rutas de otros equipos. **V477 no cambia sensores, políticas de IA, funciones del chat ni optimización de Windows.**

[Ver informe de auditoría y límites de validación](docs/AUDITORIA_ESTRUCTURA_V477.md).

---

# CorePulse V476 — Investigation Engine

Ver [Guía V476](docs/GUIA_IA_ACTUAL_V476.md). Descarga el ZIP completo, extrae e inicia `Iniciar_CorePulse.bat`.

# CorePulse V473 — IA Cloud sin complicaciones

Para usar el chat abre CorePulse, marca la autorización de datos y pulsa **Conectar IA**. Los detalles técnicos se encuentran en **Configuración avanzada**. Lee [Guía de CorePulse AI V473](docs/historico/GUIAS_HISTORICAS.md). La conexión real requiere API key Groq preconfigurada, pero **no** un LLM local ni un servidor GPU propio.

# CorePulse V468 — CorePulse Intelligence Engine: mantenimiento preventivo

La conversación con GPT-OSS 120B se realiza desde la pestaña CorePulse AI, con puente local de pruebas y modelo en Groq Cloud, consentimiento explícito, vinculación por equipo y seguridad `REAL_OR_NA`. Guía de activación: **`GUIA_COREPULSE_AI_V467.md`**. La nube privada y GPU dedicada no se despliegan en este ZIP.

# CorePulse V466 — Groq Edge User-Agent Fix

Se recomienda leer `GUIA_COREPULSE_AI_V466.md` y comenzar por `17_VERIFICAR_CLIENTE_GROQ_V466.bat`.

**V465 — Permisos y credenciales Groq:** ejecuta `16_REVISAR_CREDENCIAL_GROQ_V465.bat`, después `15_DIAGNOSTICAR_GROQ_V464.bat`. Lee [GUIA_COREPULSE_AI_V465.md](docs/historico/GUIAS_HISTORICAS.md).

**V463 — Prueba GPT-OSS 120B en Groq Cloud**: consulta [`GUIA_COREPULSE_AI_V463.md`](docs/historico/GUIAS_HISTORICAS.md) y los BAT 10–14. No se incluye API key ni se descarga un modelo local.

# CorePulse V462 — Cloud Model Evaluation

**Novedades V462:** laboratorio de 30 escenarios sintéticos, medición de modelos cloud bajo ejecución y consentimiento explícitos, comparación de informes verdaderamente medidos y catálogo preliminar de modelos abiertos. **No incluye servidor GPU desplegado ni resultados de inferencia real.** [Guía V462](docs/historico/GUIAS_HISTORICAS.md).

# CorePulse V461 — CorePulse AI Safety Gate

**Novedades de V461:** seguridad de respuestas LLM tras inferencia (REAL_OR_NA / REAL_FPS_OR_NA_ONLY), abstención mediante fallback determinista, provenance de campos, rechazo de enlaces no verificados, ausencia de búsquedas automáticas con datos de hardware a YouTube y un corpus sintético de 10 escenarios para evaluar modelos cloud. Ver `GUIA_COREPULSE_AI_V461.md`. **No está desplegado un modelo cloud de producción.**

# CorePulse V460 — Cloud Backend Private Beta

**Novedades de V460:** vinculación por código individual de un solo uso, servicio FastAPI integrado con cuota y control de accesos, despliegue privado de referencia con Caddy HTTPS + vLLM GPU, cliente ligero que mantiene consentimiento y telemetría REAL_OR_NA. Ver `GUIA_COREPULSE_AI_CLOUD_V460.md` y `CorePulse_AI_Cloud_Deployment/README.md`. No hay nube pública preconfigurada ni se arranca LLM local automáticamente.

---

# CorePulse V447

CorePulse para Windows: monitoreo, diagnóstico, mantenimiento, gaming, drivers y CorePulse AI con política REAL_OR_NA.

## Arranque

```powershell
python main.py
```

El arranque normal mantiene la telemetría local. La inferencia pesada de CorePulse AI Cloud solo se inicia por petición del usuario mediante el puente Groq y consentimiento explícito.

## Arquitectura visual V410

La superficie visual del área de trabajo se dibuja en código desde `gui/workspace_background.py`: capas oscuras, guías discretas y acentos mediante la paleta del tema activo. No se carga ni distribuye un wallpaper. La misma composición se reproduce en los contenedores estructurales de Resumen y de las vistas internas, manteniendo las tarjetas funcionales intactas.

## Estructura

- `core/`: telemetría, diagnóstico, salud, mantenimiento, gaming, drivers, energía e IA.
- `gui/`: shell, navegación y paneles de CorePulse.
- `performance/`: Game Boost, detección de juegos y planes de energía nativos.
- `database/`: persistencia local.
- `CorePulse_AI_Server/`: servidor local de CorePulse AI.
- `CorePulse_AI_Model_Host/`: host llama.cpp del modelo local temporal.
- `assets/`: recursos gráficos de marca y controles (sin wallpaper de fondo).
- `tools/`: herramientas runtime necesarias.
- `build/` e `installer/`: empaquetado Windows.

## Contratos

- `REAL_OR_NA`: ningún dato de hardware se inventa.
- `REAL_FPS_OR_NA_ONLY`: FPS únicamente desde fuentes reales.
- CorePulse determina hechos/estados; la IA los interpreta y explica.
- Los planes de energía se descubren desde Windows y sólo se activan por GUID real; CorePulse no crea esquemas.



## V445 · Alineación horizontal de gráficos

- Se desplazan 20 px a la izquierda los tres gráficos del Resumen para alinearlos con las columnas CPU/RAM/GPU.
- Se mueven juntos ejes, títulos, etiquetas y curvas sin cambiar el ancho ni los valores representados.
- La posición se obtiene de las tarjetas reales durante los cambios de tamaño; el fondo maestro y el hover V443 siguen intactos.

## V444 · Gráficos sobre el fondo maestro, sin cuadros internos

- Se eliminan los fondos opacos de los ejes CPU, RAM y GPU (`facecolor='none'`).
- Se desactivan los cuatro contornos (`spines`) de cada gráfico.
- La superficie maestra generada en `chart_workspace_surface.py` permanece visible directamente bajo las curvas y cuadrículas.
- Se conserva la alineación con las tarjetas de CPU/RAM/GPU y no se altera la telemetría, las curvas, las escalas o el hover V443.
- Se aplica también en los restylings y redimensionamientos para que no reaparezcan los cuadros.

## V443 · Hover optimizado con esquinas redondeadas

- Conserva la iluminación de tarjetas de V442, ahora formada por tres líneas suaves en el perímetro redondeado, en vez de centenares/millares de segmentos por frame.
- Al entrar o salir con el cursor actualiza solamente el brillo; no reconstruye las superficies nativas ni los controles internos.
- Respeta el `corner_radius` de cada tarjeta y elimina los segmentos rectos que cruzaban las esquinas.
- Mantiene los colores según estado/CPU/RAM/GPU/SSD, la alineación del resumen y las páginas sin cabecera.

## V442 · Hover visible en el lienzo nativo sin cuadros

La iluminación se dibuja sobre la misma superficie nativa de cada tarjeta,
con un resplandor de perímetro suavemente degradado usando los colores reales
del tema. Al pasar el mouse sobre Salud, Supervisión, Trazabilidad, Sesión,
CorePulse AI, CPU, RAM, GPU o SSD, aparece el brillo de su acento; al salir,
se elimina sin dejar capas acumuladas. Ningún icono, porcentaje o barra de
datos cambia su fondo. Conserva todas las vistas internas sin cabeceras V440.

## V440 · Páginas internas sin cabecera introductoria

Se elimina completamente de la geometría visible el bloque superior de título, subtítulo, badges, etiquetas y tarjeta hero de 18 vistas internas (Benchmark, Limpieza, Tweaks, Red, Gaming, Diagnóstico, Centro de salud, IA, Temas, alertas, tendencias y fichas de hardware). El contenido operativo se desplaza hacia arriba automáticamente, sin dejar una banda o tarjeta vacía. Se conservan los títulos internos propios de operaciones, tarjetas y controles que comienzan inmediatamente debajo. Las acciones críticas de diagnóstico y la actualización manual de detalles se encuentran ahora dentro de las áreas funcionales correspondientes.

## V439 · Corrección estructural de los cuadros del hover

Los rectángulos visibles al mover el mouse no se corrigen variando la intensidad del brillo: se elimina la segunda capa de rectángulos sobre los CTkCanvas internos. El fondo maestro aprobado en V436 sigue siendo la única capa de superficie de las tarjetas. Para proporcionar feedback de hover sólo se ilumina, temporalmente, el acento lateral original de la tarjeta; nunca se modifican el tamaño ni los fondos de sus iconos, etiquetas, botones o barras. Se respetan los colores de estado real de Salud y CorePulse AI. La salida del mouse restaura el color exacto.

## V438 · Hover elegante sin recuadros de color

La superficie maestra aprobada en V436 y la alineación real de las columnas en V437 se mantienen intactas. El brillo interactivo ya no cubre toda la tarjeta con un tinte intenso ni recolorea el fondo de etiquetas/botones: ahora se concentra suavemente alrededor del acento lateral y se desvanece horizontal y verticalmente, sin producir un rectángulo visible. El botón contextual «Ver detalles» mantiene su funcionamiento.

## V437 · Gráficos alineados + iluminación por función

Los tres ejes de tendencias CPU/RAM/GPU toman la posición horizontal de las
columnas de sus tarjetas correspondientes y se recalculan en cada reflow del
Resumen. Se mantiene la capa base nativa de V436 y el acabado sin marcos.

Las tarjetas interactivas ahora tienen iluminación suave en hover: cian en
CPU/SSD/Trazabilidad, verde en RAM, violeta en GPU, y ámbar o verde según
el estado de Salud y Supervisión. CorePulse AI adopta el color de su estado
actual. La iluminación se genera sobre el mismo lienzo del fondo maestro;
no se añade otra tarjeta ni un PNG opaco.

## V436 · Tarjetas sin bloques superpuestos: superficie exacta

Las tarjetas del Resumen ya no mezclan el fondo maestro con un azul glass opaco. Sobre sus Canvas nativos, CorePulse pinta la **misma porción del Surface Studio** que queda detrás de cada tarjeta: bandas cromáticas sincronizadas con posición, ventana, tema y sidebar. Los CTkFrame internos se unifican con esa capa sin ocultar los acentos laterales, iconos, botones, indicadores o barras de datos. El hover deja de teñir la tarjeta completa. La reproducción de la superficie reutiliza el motor visual de `gui/workspace_background.py`, sin wallpapers ni imágenes estáticas.

## V435 · Tarjetas integradas a la superficie nativa

Después de integrar correctamente el bloque de gráficos al fondo maestro, esta versión aplica el mismo criterio a las tarjetas principales del Resumen: CorePulse AI, Salud/Supervisión/Trazabilidad/Sesión, CPU, RAM, GPU y almacenamiento. Cada tarjeta calcula su material según la posición real que ocupa sobre la superficie nativa de CorePulse, eliminando el aspecto de bloque aislado y evitando bordes oscuros que sobresalgan. Se conserva la jerarquía visual mediante acentos laterales, hover y tipografías.

## V434 · Gráficos integrados al fondo maestro

La capa exterior del área de CPU, RAM y GPU ya no usa un negro fijo ni el azul de otra tarjeta. El contenedor queda estructural y sin marco; el `FigureCanvasTkAgg` reproduce como capa inferior el mismo tono del fondo nativo de CorePulse en cada fila, respetando posición, tamaño de ventana y temas. Los ejes, las curvas y la autoridad de las métricas permanecen sin cambios. Se sincroniza también el material interno de Salud del sistema para evitar recuadros de color distinto tras redimensionar o cambiar de tema.

## V433 · Integración del margen exterior del bloque de gráficos

El contenedor exterior del bloque CPU/RAM/GPU y el margen del Figure de Matplotlib ahora usan el mismo fondo principal del dashboard. Esto elimina los bordes más oscuros que sobresalían alrededor del conjunto de gráficos, manteniendo intacto el fondo interno de cada gráfico.

## V432 · Gráficos sin marco restaurado y sin fondo negro

Corrige la tercera ruta que reactivaba el borde (`gui/dashboard.py::_style_charts`). Restablece `frameon=True` para que Matplotlib pinte el relleno correcto y utiliza la misma superficie glass en el contenedor, figura y canvas. El resto del dashboard conserva la V431.

## V431 · Eliminadas líneas del perímetro del lienzo de gráficos

Se eliminan las líneas izquierda, derecha e inferior que seguían viéndose alrededor del bloque de gráficos. La corrección se aplica al Figure y al canvas Tk de Matplotlib, sin tocar las curvas ni la disposición interna de CPU, RAM y GPU.

## V430 · Contenedor de gráficos integrado al fondo

El bloque grande que envuelve CPU, RAM y GPU deja de pintarse como una caja propia. Se integra visualmente al fondo principal del dashboard para que desaparezca el efecto de panel exterior y solo queden visibles los gráficos internos.

## V429 · Sin borde en el contenedor exterior de gráficos

Se elimina el borde del panel grande que encapsula los tres gráficos (CPU, RAM y GPU), manteniendo intactos los gráficos internos, sus ejes y el acabado visual del resto del dashboard.

## V428 · Corrección de la franja y del sobreborde superior

- Se ajusta la geometría del encabezado para eliminar el espacio visual excesivo antes de las tarjetas superiores, tanto al abrir la ventana como al reajustarla.
- Salud del sistema usa el mismo material glass en los contenedores y etiquetas interiores: evita recuadros negros de CustomTkinter bajo texto/iconos.
- La fila de Salud, Supervisión, Trazabilidad y Sesión deja de recibir la película óptica adicional, manteniendo el tinte glass y los acentos laterales.
- Conserva el sidebar aprobado de V425 y las tarjetas de CPU, RAM, GPU, SSD y gráficos. No se cambia telemetría, diagnóstico ni IA.

## V427 · Borde de la franja superior corregido desde el estilizador

V426 eliminaba el borde al crear Salud, Supervisión, Trazabilidad y Sesión, pero
`gui/dashboard_layout.py::_style_status_band` restauraba `border_width=1`
después del montaje. Ahora las dos rutas de estilizado (inicial y responsive)
conservan `border_width=0` en estas cuatro tarjetas. La tarjeta CorePulse AI
sigue sin borde, tal como quedó en V426. No se tocan CPU, RAM, GPU, SSD,
gráficos, sidebar ni datos de telemetría.

## V426 · Corrección de sobreborde en tarjetas superiores

Se elimina el borde externo de la franja superior del Resumen (CorePulse AI + tarjetas de Salud, Supervisión, Trazabilidad y Sesión) para evitar el efecto de doble contorno / sobreborde. El resto del dashboard se mantiene intacto.

## V425 · Sidebar sin bandas negras en los controles

Los controles y etiquetas del lateral reproducen el mismo sustrato Surface Studio que la ventana principal. Se eliminan los rectángulos casi negros creados por la falsa transparencia de CustomTkinter. Personalización continúa en el flujo normal y el botón activo mantiene su selección azul. Sin cambios en las tarjetas o en la telemetría.

## V424 · Corrección de cierre de inicio en CTkButton

Se corrige el fallo `ValueError: transparency is not allowed for this attribute` que impedía abrir V423. `hover_color` de los botones ya no recibe `transparent`; se usa un color válido del tema y se desactiva el hover de los botones laterales creados en `main.py` y Personalización para conservar el acabado plano. El nuevo test de regresión rechaza volver a introducir este valor inválido. Personalización sigue en el mismo sidebar, sin su contenedor separado.

## V423 · Personalización unificada + botones laterales planos

La zona de Personalización deja de construirse como un bloque separado y pasa a usar exactamente el mismo flujo visual del resto del sidebar. Además, los botones laterales se aplanan (`bg_color='transparent'`, `hover_color='transparent'` en estado normal) para eliminar el tono oscuro/feo que seguía viéndose sobre el lateral.

## V422 · Sidebar integrado a la primera capa

El lateral deja de usar un fondo sólido propio. El sidebar se vuelve estructural/transparente y se registra en la misma superficie nativa que el resto de la interfaz, para que los botones queden realmente sobre la primera capa visual.

## V421 · Sidebar sin cuadro perimetral

Se elimina el cuadro que rodeaba los botones del sidebar. El menú lateral queda directamente sobre la primera capa visual, manteniendo solamente su panel/base y la lógica de altura alineada al contenido.

## V420 · Recorte de borde residual del sidebar

Se compacta aún más el bloque final del sidebar y se recorta la altura visible en 2 px para compensar la línea inferior/borde residual que seguía desalineando el cierre con el panel de gráficos.

## V419 · Sidebar con alineación exacta a gráficos

Se compacta el footer de Personalización y el cálculo de altura del sidebar prioriza la alineación exacta con la línea inferior real del panel de gráficos del Resumen.

## V418 · Sidebar Personalización unificado

Se unifica el bloque de Personalización con el lenguaje del resto del sidebar: mismas alturas, radios, paddings y acentos laterales. Además, el cierre inferior del sidebar prioriza la alineación visual exacta con el panel de gráficos cuando el contenido cabe sin desbordes.

## V417 · Glass sin rectángulos ni líneas sobrantes

El acabado de V416 se conserva en el tinte y la legibilidad, pero el reflejo RGBA ahora se dibuja **una sola vez por tarjeta**. No se inyectan más imágenes ni capas en contenedores transparentes anidados que generan rectángulos oscuros. Se mantienen el fondo nativo, las tarjetas y toda la funcionalidad. El aviso de modelo local cerrado depende del runtime de IA y no se oculta mediante cambios visuales.

## V416 · Glass óptico visible en tarjetas

Se corrige la V415, cuyo cambio cromático era demasiado sutil y además era reescrito por el motor de layout responsivo. Ahora las tarjetas del Resumen, CorePulse AI y las unidades SSD utilizan el **mismo rol glass** tanto en su creación como al remaquetar la ventana. Un reflejo translúcido de luz fría (RGBA creado en memoria) se dibuja **dentro** de cada tarjeta sin alterar datos, barras, botones ni los márgenes exteriores. Los contenedores CTk transparentes reproducen el reflejo en sus propias coordenadas para evitar cortes. Las esquinas quedan recortadas. No hay transparencia real de la ventana ni wallpaper.

## V415 · Efecto glass en tarjetas

Se aplica un efecto de pseudo-transparencia visual en las tarjetas del Resumen y superficies estructurales principales. No usa alfa real de CustomTkinter: las tarjetas emplean colores recalculados para dejar respirar más la capa base sin perder legibilidad.

## V414 · Surface Studio · Capa base unificada

En la V414 se elimina la franja llamativa entre sidebar y contenido al estrechar el margen lateral y retirar cualquier cambio brusco de color en ese punto. El diseño inferior de la aplicación se reconstruye con un acabado mate de profundidad progresiva, una luz ambiental suave en el encabezado y tonalidad continua en todos los espacios estructurales. Es geometría Tk nativa, no una imagen de fondo; el diseño se comparte entre pestañas y responde a cambios de tamaño y tema. Tarjetas, gráficos, tarjetas SSD y módulos funcionales mantienen el diseño aprobado en V413.

## V413 · Alineación sidebar, gráficos y sección SSD

- El sidebar termina alineado con el borde inferior del panel de gráficos cuando Resumen está visible.
- El visor de SSD/almacenamiento usa la altura exacta de sus tarjetas y deja de mostrar un segundo panel debajo.
- Se reduce a un espaciado consistente la separación entre discos y tendencias.
- Se retira el pequeño remate celeste flotante bajo el encabezado, que parecía un borde cortado.
- No cambian sensores, telemetría, IA, gaming ni lógica del producto.

## V412 · Superficie nativa sin artefactos

Se retiraron las formas poligonales grandes, la retícula que se recortaba entre tarjetas y los raíles con marcas laterales de V411. La capa inferior ahora es una superficie cromática nativa y continua, con profundidad azul discreta y un solo acento corto en el encabezado. Mantiene intactas las tarjetas, el nombre real del PC y CorePulse AI.

## V411 · Superficie nativa visible

La zona oscura de fondo tiene contraste y elementos de diseño perceptibles: tratamiento de cabecera, paneles cromáticos vectoriales sin recuadros, líneas estructurales, riel lateral y remates. Son primitivas gráficas nativas y comparten geometría entre las pestañas. Las tarjetas mantienen su diseño.

## V410 · Diseño nativo del área de trabajo (sin wallpaper)

Se retira el archivo de fondo fotográfico y se sustituye por una **superficie de aplicación programática**: tonos oscuros graduados, retícula arquitectónica muy sutil y guías de precisión. Los colores se obtienen de los roles del tema seleccionado. Un compositor único alinea el dibujo entre los contenedores de todas las pestañas, incluso durante el resize. La identidad del equipo se dibuja sobre el mismo lienzo, sin cajas negras, mientras CorePulse AI mantiene su tarjeta separada.

Las tarjetas, el sidebar, los gráficos, la telemetría y las funciones no se rediseñan.

## V409 · Identidad del equipo sin recuadros opacos

El logo y el nombre real del PC/notebook se dibujan sobre un lienzo Tk con
el recorte alineado del único fondo maestro. Se eliminan los rectángulos
oscuros que aparecían detrás de los controles `CTkLabel`. El texto dinámico,
el diseño adaptable y la tarjeta independiente de CorePulse AI se conservan.

## V408 · Encabezado realmente fusionado con el fondo

La franja superior del Resumen se registra como superficie estructural del fondo maestro. Así, el área donde aparece el nombre del equipo deja de verse como una banda separada y utiliza el mismo wallpaper alineado que el resto de la interfaz.

## V407 · Nombre del equipo integrado al fondo

El bloque superior izquierdo deja de ser una tarjeta visual. Ahora el encabezado muestra únicamente el nombre real del PC/notebook integrado al fondo maestro, mientras la tarjeta independiente de CorePulse AI se mantiene a la derecha.

## V406 · Fondo maestro continuo y encabezado ordenado

La imagen de fondo única ahora cubre por completo el cliente y se compone en las capas estructurales CTk, sin alterar tarjetas. La tarjeta CorePulse AI superior evita el recorte vertical y los textos superpuestos.

## V405 · Fondo maestro completo
- El wallpaper maestro se renderiza sobre toda el área cliente de CorePulse, no sólo dentro de `main_content`.
- La imagen se escala con `contain`: se ve completa, sin recorte ni deformación.
- Sidebar, tarjetas y funcionalidad permanecen por encima sin rediseño.


### V458: discos y botón de IA

En **Resumen**, sólo el disco de Windows ocupa el alto visible del área de almacenamiento. Sitúa el cursor sobre el disco y utiliza la rueda del mouse o la barra lateral para consultar otras unidades. Los gráficos ocupan el espacio restante.

El icono de encendido situado a la derecha del encabezado **CorePulse AI** sirve para apagar o encender la IA. Al apagarla, CorePulse detiene únicamente los procesos que creó y recuerda la opción en AppData para futuros inicios. Si el servidor llama.cpp pertenece a otro programa o fue arrancado manualmente, CorePulse no lo finaliza.


## CorePulse V464 — Diagnóstico seguro Groq

Si `14_PROBAR_GPT_OSS_120B_V463.bat` falla, ejecuta `15_DIAGNOSTICAR_GROQ_V464.bat` primero. Revisa `GUIA_COREPULSE_AI_V464.md`. V464 conserva V463 y añade causas de error clasificadas sin mostrar secretos.


V468: mantenimiento preventivo y respuestas educativas aun sin alertas; filtro de nombres técnicos internos; configuración de conexión plegable en el chat cuando ya está vinculado. Conserva Groq como proveedor temporal de inferencia, no asegura independencia de proveedor todavía.


## CorePulse AI V470

Para probar continuidad de tutoriales en notebook y CPU sin inventar modelos, consultar [GUIA_COREPULSE_AI_V470.md](docs/historico/GUIAS_HISTORICAS.md).


## CorePulse AI V471 — Vinculación persistente

Consulta [GUIA_COREPULSE_AI_V471.md](docs/historico/GUIAS_HISTORICAS.md) para migrar el puente Groq y validar el estado de la sesión sin enviar telemetría.

## CorePulse AI V472 — Motor cloud independiente

Consulta [GUIA_COREPULSE_AI_V472.md](docs/historico/GUIAS_HISTORICAS.md): Groq permanece como predeterminado de pruebas y se integra una segunda ruta OpenAI-compatible opcional, con consentimiento y credenciales separados. No incluye ni contrata un segundo modelo real ni una GPU remota.
