# CorePulse REBUILD 109 — Tendencias por sesiones de Windows

## REBUILD 106 — Integración de REBUILD 105 con el trabajo anterior (17-10-2026)

- **Base:** ZIP completo de REBUILD 105. Se conserva el anillo de diagnóstico en reposo y el progreso real desde 0 %, junto con el resto de sus cambios.
- **Informes PDF:** se reincorpora la plantilla A4 compartida, con portada, encabezados, paginación, tablas y gráficos. El informe general incorpora benchmarks guardados y se añade el PDF dedicado al benchmark. Se conserva la corrección de márgenes laterales y verticales.
- **Drivers:** se recuperan la vista profesional, el modelo detectado y acceso al soporte OEM, avance de consulta, filtros y descarga por lote. La coincidencia sigue basada en Hardware ID; BIOS/firmware no se ofrece como controlador común.
- **Temas:** vuelven las 15 paletas y el fondo degradado propio de cada tema. Las superficies temáticas y colores por componente/estado conservan sus reglas.
- **Validación:** integración estática de archivos y revisión del paquete. No se ejecutaron la aplicación ni pruebas automatizadas.


## REBUILD 098 — Abrir resultados oficiales de Speedtest en navegador

- **Base:** REBUILD 097, sin cambios en la interfaz visual ni los sensores.
- **Ookla oficial:** tras completar correctamente una prueba, la CLI proporciona un enlace único a la página de resultados. CorePulse valida que sea un enlace HTTPS de `speedtest.net` y lo abre automáticamente en el navegador predeterminado.
- **Privacidad:** el identificador de resultado se transporta solo hasta la señal de apertura; no se añade a las mediciones públicas del controlador ni se guarda en archivos locales. No se recuperan IP, ISP ni ubicación.
- **Cloudflare:** mantiene la medición local. Como ese motor no ofrece la página de resultados de Ookla, no se abre un enlace ajeno ni se muestra una prueba ficticia.
- **Errores / URL ausente:** no se abre el navegador si Ookla no finaliza correctamente o no devuelve un enlace oficial válido.
- **Consentimiento:** la prueba sigue iniciándose solo tras una acción del usuario y aceptación de términos en el caso de Ookla.

Esta entrega continúa la línea REBUILD 071 e integra las funciones autorizadas de V485, con el benchmark GPU V29. El arranque usa Python 3.12 o superior (versiones validadas), PySide6 y QML. CorePulse AI conserva su implementación previa. No se incorporaron las interfaces antiguas de Tk ni código auxiliar obsoleto.


## REBUILD 087 — Íconos del Centro de salud y simetría de Limpieza

- **Base íntegra:** REBUILD 086 entregada como `Versión de Maxi.rar`, con detección dinámica de USB, SMART/NVMe, bandeja, benchmark V29 y botones de acción conservados.
- **Centro de salud:** los siete íconos de las tarjetas del panel principal pasan de 21 × 21 a 30 × 30 píxeles. No se alteran otras familias de íconos ni tamaños de tarjeta.
- **Limpieza de sistema:** las tarjetas de Temporales, RAM, Caché, Espacio seguro, Duplicados y Papelera usan altura base común de 270 px; RAM conserva expansión a 342 px cuando el usuario abre detalles. No se altera la ejecución de ninguna operación.
- **Versión visible de esa entrega:** REBUILD 087. Las expectativas de versión en las pruebas se actualizaron. Sin archivos Python nuevos ni dependencias añadidas.
- **Validación:** sintaxis Python correcta en 36 archivos y 233 pruebas aprobadas, con 27 fallos preexistentes también presentes en la V086 original; las dos pruebas nuevas pasaron. El aspecto QML/Windows queda pendiente de prueba visual.

## Funciones migradas

- **Game Boost:** desactivado por defecto; requiere confirmación. Cambia temporalmente la prioridad y Game Mode, y ofrece HighQoS y purga standby opcionales. Guarda el rollback antes de aplicar cambios y restaura lo que siga bajo control de CorePulse al salir del juego o cerrar la app.
- **Inicio de Windows:** inventario de entradas y acciones individuales para deshabilitar/restaurar; cada acción tiene confirmación y respaldo local.
- **Drivers:** consulta bajo demanda del catálogo oficial, descarga individual y confirmación aparte antes de instalar. Se respalda el paquete OEM cuando Windows lo permite.
- **Velocidad de Internet:** CorePulse descarga y valida con SHA-256 la CLI oficial Ookla en segundo plano al iniciar. Las pruebas siguen siendo manuales. Para ejecutar Ookla, el usuario debe revisar y aceptar sus condiciones y privacidad en la app; Cloudflare queda como opción sin Ookla.
- **Botones de acción:** los que inician, analizan o ejecutan algo muestran el texto de color sobre fondo oscuro (`themeManager.palette.action`, el azul de Tweaks, o el color de su tarjeta). Solo Aplicar y Actualizar tienen el botón entero de color. Los de navegación y respuesta (Volver, Cancelar, Abrir) quedan secundarios.
- **Privacidad en Red avanzada:** el nombre del Wi-Fi (SSID) y la IPv6 se muestran ocultos, y la IPv4, el gateway y el DNS se muestran parcialmente (`192.168.1.•••`). El botón de ojo los revela uno por uno; se vuelven a ocultar solos a los 30 s o al salir de la pantalla. El valor real no llega a la interfaz hasta tocar el ojo. No se recolectan MAC ni BSSID, y la prueba de velocidad no guarda IP pública, proveedor ni ubicación.
- **FPS del juego:** el overlay lee RTSS Shared Memory en modo lectura y solo enseña FPS para el PID del juego detectado con una muestra fresca. En cualquier otro caso muestra `N/A`; no estima FPS.
- **Nombre del equipo:** los PC de marca muestran fabricante y modelo; en equipos armados se filtran los textos de relleno de SMBIOS y se muestra el nombre de Windows junto al fabricante/modelo de la placa madre.
- **Overlay:** el modo compacto ajusta la vista previa para contener CPU, GPU, RAM, VRAM, FPS y tiempo. Los botones «Cambiar» quedan centrados, Esc cancela la captura del atajo y la rueda/touchpad desplaza más contenido por movimiento.
- **Historial y tendencias:** muestras de monitorización y transiciones de alertas se guardan localmente en SQLite. El Historial de alertas permite actualizar o limpiar sus transiciones; las alertas que siguen activas permanecen visibles.
- **Reportes:** exportación local a PDF con lecturas y cobertura verificables. Tras un diagnóstico incluye la devolución de CorePulse AI si se autorizó y enlaces de búsqueda de tutoriales específicos.
- **Windows y salud:** accesos al estado de inicio, servicios, eventos recientes, dispositivos y módulos de batería, almacenamiento, recuperación y reparación ya integrados en el Centro de salud. Cada subpágina identifica el módulo abierto y sus iconos de cabecera no llevan un recuadro.
- **Diagnóstico general:** una acción circular inicia la consulta local de componentes, ocupación y fuentes de Windows. El resultado diferencia lecturas correctas, atención preventiva y datos no confirmados; ofrece tutoriales de YouTube por componente/lectura y exportación a PDF. CorePulse AI solo recibe el resumen al iniciar el diagnóstico si está activada, conectada y tiene permiso de compartir lecturas; sin esos permisos el resumen local sigue funcionando.
- **Almacenamiento SSD y USB:** el selector incluye volúmenes fijos y extraíbles, enseña etiqueta, sistema de archivos, capacidad/uso y, cuando Windows los relaciona, modelo, bus y tipo de medio. Mientras permanece abierto detecta conexiones y retiros en aproximadamente un segundo; al retirar una unidad la elimina y ajusta la selección automáticamente. «Ver detalles» abre el estado físico estilo CrystalDiskInfo. NVMe consulta SMART/Health en solo lectura. El desgaste ahora indica un nivel orientativo además del porcentaje de resistencia estimada consumida; no equivale a una predicción de fallo. Las lecturas que Windows/controlador no expone permanecen como N/A.
- **Bandeja:** «Limpieza completa de RAM» inicia la tarea en segundo plano y comunica el resultado desde la bandeja; no restaura la ventana ni abre los cuadros de confirmación/medidor de Limpieza. La confirmación y el monitor visual siguen en la acción de RAM dentro de CorePulse.
- **Interfaz:** en Resumen, CPU Intel usa azul y CPU AMD rojo; GPU NVIDIA usa verde, Intel azul y AMD rojo. Si CPU y GPU son AMD, la GPU usa naranja para distinguir las dos piezas. Las líneas del gráfico, leyendas, iconos y barras siguen el mismo color de marca. RAM usa teal y SSD violeta, con el aviso de RAM crítica conservado. El logo CorePulse y los colores de marca y estado (CPU/GPU, salud, alertas y éxito/atención/error) quedan fijos; solo las superficies y los acentos decorativos responden al tema. La rueda y el touchpad avanzan más en las pantallas y listas largas. Los iconos del sidebar crecen, reaccionan al hover y dejan de mostrar el marco verde; el botón para plegarlo queda sin placa gris y cada grupo de Tweaks puede plegarse por separado.
- **Limpieza V485:** RAM normal, standby y profunda; escaneo local de duplicados mediante tamaño y SHA-256 (sin borrado automático); análisis de espacio en ubicaciones regenerables permitidas y limpieza únicamente después de confirmación y revalidación.
- **Test de audio:** salida izquierda/derecha/ambos y prueba de micrófono WASAPI de 5 s. La muestra se mantiene en memoria mientras CorePulse está abierto, puede reproducirse y requiere confirmación manual; no se envía. El informe PDF puede incluir evidencia reciente verificada, nunca la grabación.
- **Game Boost V485:** HighQoS/Power Throttling y purga standby opcionales al detectar una sesión. Se guardan respaldos por proceso y se restauran cambios que CorePulse aún controla.
- **Estabilidad bajo carga:** CPU por 10 segundos y memoria por 7 segundos, solo después de una confirmación. Incluye cancelación, corte ante temperaturas extremas, sin puntuación ni cambios en Windows. GPU queda excluida porque V485 genera esa carga desde el motor de benchmark.
- **Benchmark GPU V29 «ciudad de neón»:** cuatro escenas DirectX 11 nocturnas (Avenida de neón, Distrito financiero, Horizonte nocturno y Megaciudad). Incluyen rascacielos con ventanas, franjas de neón y pantallas animadas, calles mojadas con reflejo planar, faroles, vehículos voladores, vapor, sombras de luna y luz volumétrica. Render HDR con MSAA 4x cuando la GPU lo admite, bloom y tonemapping ACES. Render fijo de 1920×1080, selección de GPU de alto rendimiento en equipos híbridos y FPS por fotogramas presentados/tiempo real. En NVIDIA muestra condiciones de prueba —temperatura, relojes, consumo, throttling, batería/cargador y plan de energía—; datos que el controlador no expone quedan como N/A. V29 no se compara con V28.
- **Historial de benchmark:** conserva en un JSONL local hasta 500 sesiones CPU/RAM/SSD y GPU ya completadas con mediciones reales. Se filtra por tipo, compara dos sesiones con el mismo método (para GPU, también perfil y adaptador) y exporta el filtro actual a CSV. En la primera ejecución, incorpora el último resultado CPU y GPU existente si el historial todavía está vacío. No se transmiten resultados.
- **Ventanas adaptables:** la navegación se compacta en anchos pequeños, la cabecera reduce su altura y Overlay reordena la vista previa y los controles. Los paneles largos muestran desplazamiento visible.
- **Temas:** la capa de fondo y estructura original de CorePulse permanece fija. Nueve estilos seleccionables usan superficies oscuras y acentos saturados, definidos y de alto contraste (acero, carbono, óxido, cobalto, bosque táctico, rojo torque, titanio ámbar, acero táctico y verde radar). Se mantienen sus IDs guardados para que una selección previa adopte la paleta renovada; la base sigue marcada como permanente.

## Alcance de IA

Se conserva el motor de chat de REBUILD 071. El diagnóstico usa ese mismo controlador solo bajo sus permisos existentes: IA activada, consultas autorizadas, conexión lista y autorización de lecturas técnicas. Sin permiso se presenta el resultado local. El modelo puede estimar la generación del CPU/GPU con sus conocimientos, pero CorePulse no consulta el mercado en vivo; las recomendaciones no confirman fallos físicos. Los enlaces de tutorial se construyen localmente como búsquedas de YouTube con el nombre del componente y la lectura que requiere atención.

## Control de rendimiento térmico

El detector identifica el juego activo, pero Game Boost aplica una política general: prioridad, Game Mode, HighQoS y purga standby opcional. No mantiene perfiles térmicos distintos por juego ni cambia límites TPL/PL1/PL2 del CPU, curva de voltaje/reloj de GPU o velocidad de ventiladores. Para incorporarlos habría que detectar qué controles permite cada combinación de equipo, BIOS y controlador, guardar el estado original y restaurarlo al cerrar el juego. La interfaz podría mostrar solo controles compatibles, perfiles Silencioso/Equilibrado/Juego y atajos. Bajar límites de potencia puede bajar temperatura, pero no garantiza el mismo rendimiento en toda carga.

## Ejecución

En Windows, inicia `Iniciar_CorePulse.bat` o ejecuta `main.py` con Python 3.12 o superior de 64 bits. El lanzador prepara `%LOCALAPPDATA%\CorePulse\runtime` e instala o repara las dependencias de `requirements.txt` desde PyPI. Al abrir la app, descarga la CLI Ookla oficial a `%LOCALAPPDATA%\CorePulse\tools\ookla` y verifica el ZIP con SHA-256; un fallo de Internet no impide usar el resto del software y se puede reintentar desde Red. Los módulos QML y el código ya vienen en la carpeta/ZIP de CorePulse. La prueba de estabilidad, búsquedas de drivers y pruebas de velocidad siguen requiriendo una acción explícita; la primera prueba Ookla pide aceptar los términos enlazados en pantalla.

Los respaldos reversibles, tendencias, unidad seleccionada, informes y benchmark se guardan localmente en `%LOCALAPPDATA%\CorePulse`; el historial de sesiones está en `resultados\benchmark_historial.jsonl`. La carpeta del proyecto conserva `Reglas para crear Versiones nuevas.txt` en su raíz y el historial de cambios en `versiones/HISTORIAL.md`.

## Estado de validación

La revisión 086 añade volúmenes removibles al selector, detección de conexión/retiro cada 900 ms mientras está abierto y una categoría visible para el desgaste estimado. La revisión 085 añadió provisión automática de Ookla, aceptación explícita de sus condiciones, limpieza de RAM desde bandeja sin diálogos y contadores NVMe. No se ejecutó la suite automatizada ni se abrió la app; hace falta validar inserción/retiro con un USB real y contrastar el nivel de desgaste con el controlador del equipo. Los valores SMART dependen del dispositivo/controlador. Ookla requiere comprobar descarga, aceptación y prueba real. La validación de benchmark V29 está descrita en REBUILD 080. RTSS aún requiere un juego compatible para confirmar el OSD; la instalación de drivers puede requerir UAC.

La lectura directa NVMe requiere Windows y que el controlador/puente exponga la consulta estándar; falta confirmarla en el equipo físico del usuario. El historial de benchmark conserva hasta 500 sesiones recientes en este equipo; los resultados persistidos en la instalación antes de esta versión se incorporan solo desde los dos archivos de último resultado.

### REBUILD 075 — GPU AMD/Intel/NVIDIA
El monitor intenta leer sensores GPU reales mediante la dependencia HardwareMonitor en un proceso aislado. Si no hay sensores compatibles, conserva N/A (REAL_OR_NA). NVIDIA-SMI permanece como alternativa. La cobertura efectiva depende de controladores, permisos y sensores disponibles.

### REBUILD 076 — Colores del gráfico por GPU monitoreada

La línea de GPU y su leyenda en Resumen heredan el color de la misma GPU que muestra el medidor lateral (AMD rojo, NVIDIA verde, Intel azul, desconocida morado). La REBUILD 084 extiende la regla al CPU; si CPU y GPU son AMD, la GPU usa naranja para conservar contraste. Ambas líneas se actualizan sin reiniciar las muestras.

## REBUILD 077 — Bordes de ventana
La superficie exterior en `ui/Main.qml` ahora tiene cuatro esquinas rectas (`radius:0`); no se han modificado las tarjetas internas.


## REBUILD 079 — Restauración del color del sidebar
- Tema base CorePulse: fondo del sidebar restaurado a `#14131D` (REBUILD 065).
- Sin cambios en las demás propiedades de la paleta, gráficos o telemetría.


## REBUILD 088 — Centro de salud
- Botón `Actualizar` del hub cambiado a icono compacto alineado a la derecha.
- Estado general del hub simplificado: sin texto fijo de evaluación ni línea de evidencia.
- Mensaje principal centrado y redactado según la incidencia dominante, usando `headlineDisplay` y `headlineDetail`.


## REBUILD 089 — Logotipos por fabricante en la ficha GPU

- Base: REBUILD 088. La cabecera de **Tarjeta gráfica** muestra un símbolo de NVIDIA, AMD o Intel según `gpuName` (la GPU realmente monitorizada); si no se identifica, conserva el icono GPU anterior.
- Los símbolos son vectoriales y locales, sin dependencias ni descargas. Se quitaron cuatro archivos `.pytest_cache` heredados del ZIP original. Solo se modifica la presentación de la ficha GPU; telemetría, gráficos, otras tarjetas y CorePulse AI permanecen intactos.
- Archivos modificados: `ui/ComponentDetail.qml`, `ui/Glyph.qml`, `ui/Main.qml`, `tests/test_rebuild.py`, `README.md` y `versiones/HISTORIAL.md`.

## REBUILD 090 — Logotipos GPU más reconocibles
- La ficha de Tarjeta gráfica ahora usa insignias más cercanas a NVIDIA, AMD e Intel, manteniendo detección automática por fabricante.
- Se conservan el fallback genérico y el resto de la UI.

## REBUILD 091 — CPU por fabricante
- La ficha de Procesador ahora muestra una insignia visual por fabricante (Intel/AMD) cuando puede identificarse.
- La tarjeta de Resumen / Estado del sistema también reacciona al fabricante del CPU, en su icono lateral y color de acento.

## REBUILD 092 — Insignias CPU/GPU en Resumen y gráfica
- En Estado del sistema, tanto CPU como GPU muestran una identificación compacta por fabricante Intel/AMD/NVIDIA cuando la marca está confirmada por el nombre detectado.
- En la leyenda de Rendimiento en tiempo real se muestran distintivos coherentes con la tarjeta lateral; ante fabricante desconocido permanecen los puntos de color.
- Se preservan los datos históricos, el comportamiento de las líneas, los sensores y las demás pantallas de REBUILD 091.

## REBUILD 093 — Leyenda de gráfica simplificada
- La leyenda de Rendimiento en tiempo real vuelve a usar puntos de color simples para CPU y GPU.
- Las insignias por fabricante se mantienen en Estado del sistema y en las fichas de detalle.

## REBUILD 094 — Insignias unificadas entre detalle y Resumen
- CPU y GPU ahora usan en Estado del sistema la misma insignia visual que se ve en sus fichas de detalle.
- La leyenda del gráfico mantiene solo puntos de color para conservar limpieza visual.


## REBUILD 095 — Conexión QML obsoleta eliminada
- Se quitó de `ui/Main.qml` la referencia a `onOpenRamCleanupRequested`, una señal inexistente en `trayController`.
- La acción de limpieza profunda desde la bandeja conserva la señal real `ramCleanupRequested` y la ejecución Python en segundo plano sin diálogos. La limpieza desde la pantalla mantiene su confirmación.
- No se alteró la presentación del Resumen, la telemetría, los sensores ni la lógica de limpieza.

## REBUILD 096 — Páginas sin marcos exteriores

- Se retiraron los paneles decorativos que cubrían toda la página en Tendencias, Alertas técnicas, Historial de alertas, Benchmark, Red avanzada, Overlay, Inicio de Windows, Controladores, Reportes, CPU/GPU/RAM, Iniciar diagnóstico y Lecturas disponibles.
- El fondo base y el degradado de CorePulse permanecen visibles. Los contenedores de tarjetas de datos, gráficos, formularios, diálogos y mensajes de alerta se conservan.
- Se eliminó el margen adicional que correspondía al marco anterior; se conserva el margen global de `pageLoader` y el canal necesario para las barras de desplazamiento.
- No cambian cálculos, telemetría, sensores, operaciones ni navegación. No se agregaron módulos Python ni dependencias.

## REBUILD 097 — Tarjetas con la superficie de Limpieza y Resumen
- Base: ZIP completo de REBUILD 096, sin recuperar marcos exteriores.
- Tarjetas de métricas, gráficos, listados y resultados de las páginas revisadas usan `themeManager.palette.panel` (o su alias), con borde `panelBorder`, igual que Limpieza y Resumen.
- Se mantienen las capas base, botones, paneles de confirmación, encabezados, estados y colores por fabricante. No se modificó la telemetría ni los módulos de backend.
- El registro detallado de archivos, pruebas y reversión está en `versiones/HISTORIAL.md`.

## REBUILD 099 — Tendencias en vivo y alineación
- Tendencias agrupa las tarjetas y el gráfico cerca del encabezado, sin que el alto sobrante introduzca separaciones excesivas.
- La base SQLite sigue guardando una muestra real cada 30 segundos (sin cambiar el motor); el gráfico también muestra la lectura actual de telemetría (~1 s) al extremo derecho y repinta con ambas señales.
- Los porcentajes de la leyenda inferior representan lecturas actuales verificadas; si alguna no está disponible, se muestra N/A. Promedios y cuenta de muestras solo usan registros guardados.
- No se añaden dependencias ni nuevos módulos; el resto de pantallas se mantiene.


## REBUILD 100 — Tendencias cada 30 s y cabecera limpia
- Tendencias se actualiza automáticamente con las nuevas muestras reales guardadas cada 30 segundos. No repinta por eventos de telemetría a 1 s ni añade valores instantáneos al gráfico.
- El botón **Volver** se coloca junto a **Actualizar**, arriba. El pie anterior con Volver y la nota de N/A desaparece.
- El botón Actualizar permite solicitar una captura manual; abrir la vista ya no fuerza escrituras de historial. El gráfico de Resumen y los sensores siguen con su propia frecuencia normal.


## REBUILD 101 — Tendencias entre sesiones de Windows

El historial de Tendencias separa los datos por **arranque de Windows**, identificado a partir del tiempo de inicio de su núcleo (psutil). Cerrar CorePulse o volver a abrirlo no crea una nueva sesión. Inicio rápido de Windows, suspensión o hibernación pueden conservar el mismo arranque entre apagados: no se promete detectar todos los apagados físicos.

- Cada 30 segundos, si hay telemetría válida, se guarda una lectura en `%LOCALAPPDATA%/CorePulse/rebuild/monitoring_history.sqlite3`. Se conserva un máximo de **90 días**. Los intervalos sin CorePulse abierto no tienen datos.
- En **Tendencias** aparece la sesión elegida, su gráfico y **debajo** su historial de sesiones. `Ver` selecciona otra sesión y `Comparar` incorpora una segunda para contrastar gráficas (posición relativa del período observado) y promedios. `Quitar comparación` vuelve a mostrar una sola.
- En cada registro se muestra la **última lectura**, no una falsa hora de apagado. Las duraciones indicadas son el intervalo observado entre primera y última lectura y pueden contener pausas.
- Los porcentajes ausentes permanecen como N/A. El gráfico usa muestras reales reducidas a un máximo de 480 puntos por sesión para no bloquear la interfaz; los promedios SQLite abarcan **todas** las muestras de cada sesión. Los huecos prolongados separan los trazos.
- La migración del SQLite existente es automática y **no borra** las lecturas previas: como no tenían sesión verificable, se conservan fuera de la comparación e informa cuántas hay.
- La opción `Actualizar` solicita una muestra manual; no cambia la cadencia de guardado automático. Los módulos de Alertas e Historial de alertas conservan su comportamiento.

## REBUILD 102 — Red avanzada sin diagnóstico de conectividad
- Se retira la tarjeta `Diagnóstico de conectividad` de Red avanzada y se elimina su lógica asociada.
- Se mantienen inventario, privacidad, tráfico en tiempo real y prueba de velocidad.

## REBUILD 103 — Diagnóstico centrado y ampliado
- Se reajusta la pantalla `Iniciar diagnóstico` para centrar mejor el bloque principal y aumentar su tamaño visual.
- Se amplían el anillo, el ícono y los textos internos para mejorar legibilidad y equilibrio visual.
- No se alteran la lógica del diagnóstico, resultados, IA, sensores ni otras pantallas.

## REBUILD 104 — Centrado vertical real en Iniciar diagnóstico
- El anillo de 320 px se centra respecto del alto disponible del área de diagnóstico, no respecto de un bloque fijo inmediatamente debajo del título.
- Antes y durante la prueba, la sección central aprovecha el espacio libre; al aparecer resultados, vuelve a su altura base para mantener la lista de resultados y el scroll normal.
- Se mantienen las animaciones, el botón circular, la ejecución real del diagnóstico, el PDF y la integración con CorePulse AI.


## REBUILD 105 — Progreso del botón de diagnóstico
- Presentación: el círculo está trazado completo antes de iniciar el análisis (100 % solo como estado visual del botón, no como diagnóstico realizado).
- Ejecución: al pulsar, el anillo se reinicia a 0 % y crece según el progreso real del motor. No se fuerza un mínimo ficticio de 4 %.
- El primer sondeo se realiza después de 250 ms para mostrar el 0 %; no se inventan etapas ni porcentajes. Los saltos posteriores son posibles si Windows termina varias consultas rápidamente.
- Los resultados, el estado parcial y las acciones de PDF/IA permanecen iguales.

## REBUILD 108 — NVIDIA corregido sobre la integración V106
- **Base íntegra:** REBUILD 106 compartida por el usuario, con PDF profesionales, controladores y 15 paletas conservados.
- **Solo NVIDIA:** exactamente el vector y los ajustes de la REBUILD 109 visualmente aprobada: ojo blanco intercalado con el bloque, aspecto horizontal original y tamaño de 29 px en el Resumen.
- **Corrección de V107 anterior:** se incorpora tanto el relleno blanco (`fillColor`) como la relación de aspecto `383/597`; no basta con copiar el trazado.
- AMD, Intel, diagnósticos, PDF, drivers, temas y telemetría sin cambios.

## REBUILD 109 — Tendencias por inicio y cierre de Windows

- **Base conservada:** REBUILD 108 (GB, acento por fabricante e insignia NVIDIA aprobada).
- Una sesión representa un arranque de Windows; cerrar o reabrir CorePulse no la reinicia. Se fusionan automáticamente los arranques antiguos duplicados cuya marca difiere como máximo 10 segundos, conservando todas sus muestras existentes en SQLite.
- Las tarjetas de Tendencias muestran fecha y hora local **Inicio de Windows** y **Cierre de Windows** con segundos. Los registros del historial muestran esas mismas dos marcas y permiten consultar/comparar gráficas. Se eliminan porcentajes promedio, conteos y párrafos técnicos del apartado de Tendencias.
- Para sesiones pasadas, se recupera en segundo plano la marca de apagado de los eventos `Kernel-General 13`/`EventLog 6006` cuando Windows la proporciona. Es la hora **registrada por Windows**, que puede adelantarse unos segundos al corte físico; no equivale a un sensor de electricidad. Si no hay evento, figura **N/A**. No se utiliza la hora de cierre de CorePulse ni la última muestra como cierre.
- Apagados forzados pueden carecer de evento; Inicio rápido/hibernación puede conservar el mismo arranque del núcleo. CorePulse no presenta tiempos exactos que no pueda comprobar. Sigue recopilando solo mientras funciona, cada 30 segundos. Sin servicios Windows, permisos nuevos ni dependencias adicionales.
