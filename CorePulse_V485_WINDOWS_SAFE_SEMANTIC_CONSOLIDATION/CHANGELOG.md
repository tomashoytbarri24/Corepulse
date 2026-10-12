# V485 — Windows Safe Semantic Consolidation
- Se agrupan `core/runtime/frozen_selftest.py` y `core/runtime/startup_readiness.py`, preservando las rutinas públicas de autoverificación y preflight.
- Se unifican `core/diagnostics/health_history.py` y `core/diagnostics/session_trends.py`, manteniendo historial SQLite, tendencias y métricas reales.
- Alias para rutas antiguas (planas y con subcarpeta); compatibilidad especial de helpers de igual nombre pero distinta semántica.
- Cinco auditorías históricas reunidas sin pérdida de contenido en `docs/historico/AUDITORIAS_V480_V484.md`.
- RTSS, sensores de captura, benchmarks, Game Boost y módulos CorePulse AI protegidos sin cambios internos. Validación Windows pendiente.

## V484 — Consolidación interna y deduplicación (Windows)

- Tres archivos Python fusionados en módulos funcionales, imports históricos diferidos.
- Dos helpers numéricos idénticos reutilizados; no se modificó RTSS, Game Boost ni CorePulse AI.
- 398 pruebas aprobadas; 8 fallas y 1 omisión heredadas de V483.

## V483 — Consolidación segura del runtime (Windows)

- Cinco módulos fusionados con imports históricos diferidos; versión centralizada y políticas intactas.
- Cancelación cooperativa con `@contextmanager` verificada; sin cambios internos en AI, FPS RTSS, benchmarks o Game Boost.
- Tests comparables: 387 PASS, 8 FAIL heredadas, 1 SKIP (8 pruebas V483 nuevas).

# V482 — Consolidación avanzada Windows-only
- 14 módulos Python funcionales fusionados por dominio; compatibilidad diferida con rutas antiguas cortas y por subcarpetas.
- 5 suites históricas agrupadas en 2, casos originales preservados y 6 nuevas pruebas V482.
- 304 → 288 archivos completos y 205 → 188 archivos Python, sin forzar una meta de eliminación.
- 379 PASS / 8 FAIL preexistentes / 1 SKIP (suite ampliada en contenedor, excluido backend V460).
- CorePulse AI, Game Boost, benchmarks, proveedores FPS RTSS sin modificación de código interno; Docker cloud remoto opcional preservado.
- Auditoría: `docs/historico/AUDITORIAS_V480_V484.md`.

# V481 — Consolidación Windows-only
- 13 módulos funcionales relacionados fusionados en implementaciones comunes, importaciones históricas con resolución diferida y sin loaders de hardware durante el import de core/gui.
- 32 pruebas históricas consolidadas en cinco suites temáticas, cobertura original conservada, más siete controles V481.
- 341 → 304 archivos distribuibles; 243 → 205 archivos Python. No se redujeron capacidades para alcanzar la cifra.
- Restaurados módulos livianos cuya fusión cambiaba las dependencias de arranque.
- CorePulse AI, Game Boost/performance y RTSS sin cambios internos; despliegue cloud remoto preservado.
- Pruebas 373 PASS / 8 FAIL preexistentes / 1 SKIP (suite sin backend V460; validar Windows).
- Auditoría: `docs/historico/AUDITORIAS_V480_V484.md`.

# V480 — Professional Refactor
- Canonicalización de componentes idénticos de UI en `gui/widget_updates` (CPU, GPU, RAM, Red).
- Única implementación de pausa/reactivación de fichas de hardware.
- Backups transaccionales consolidados dentro de `performance/profile_manager.py`; el registro legado de planes dentro de `performance/power_manager.py` con aliases de imports históricos.
- Sondas manuales de CPU y PawnIO reubicadas en `herramientas/diagnostico/` en una única herramienta con opción `--check-pawnio` y rutas BAT ajustadas.
- El `CorePulse.spec` incluye únicamente helpers de runtime, no las sondas manuales.
- Actualización consistente de identificadores V480; pruebas heredadas de V479 siguen exigiendo RTSS real.
- Sin cambios al motor CorePulse AI, a sensores, a Game Boost ni a la captura FPS.
- Validación limitada fuera de Windows; consultar `docs/historico/AUDITORIAS_V480_V484.md`.

## V479 — FPS de juegos sólo mediante RTSS; retirada completa de PresentMon
- Retirados PresentMon.exe, los dos capturadores ETW y toda instancia activa/dependencia de PresentMon.
- Certificación de FPS desde RTSS Shared Memory con N/A cuando no existen lecturas válidas o frescas. Sin FPS inventados ni estimados.
- Conservadas mediciones DirectX propias del benchmark GPU; no usan PresentMon.
- Build EXE, self-test, readiness y pruebas actualizados; RTSS es una capacidad externa.
- Los documentos históricos conservan referencias a versiones anteriores, pero no son rutas ejecutables.

## V477 — limpieza estructural y portabilidad
- Las herramientas BAT numeradas se mantienen funcionales dentro de `herramientas/ia/`, con rutas actualizadas en el panel AI.
- Guías, validaciones y notas históricas consolidadas bajo `docs/historico/` para reducir el ruido en VS Code.
- Se retiran del ZIP los punteros de Python ajenos a otros PCs y los artefactos generados de build/test.
- Las carpetas funcionales `core/`, `gui/`, `performance/`, `CorePulse_AI_Server/` y los tests se conservan.

# V476 · Investigación temporal segura · 2026-10-09
- Historial efímero limitado a lecturas de consultas del chat; sin nuevos sensores, sin almacenamiento persistente, sin monitoreo continuo.
- Comparación temporal entre instantáneas válidas separadas al menos 15 segundos, con origen y límites explícitos. No crea alertas ni concluye causalidad.
- GPT-OSS 120B recibe el contexto estructurado, y el fallback offline informa diferencias sin inventar diagnósticos.
- Al retirar consentimiento, cambiar de servidor/proveedor o limpiar la conversación, se borran las muestras de sesión.
- `24_VALIDAR_INVESTIGACION_V476.bat`: evaluación sintética sin red ni API key.
- Pruebas de regresión; sigue pendiente la verificación de interfaz en Windows.

# V475 · CorePulse Intelligence Engine · 2026-10-09

- Motor de evidencia propio en `CorePulse_AI_Server/app/intelligence_engine.py` (sin llamadas a IA ni Internet): observaciones y fuentes por campo, ausencia de datos `N/A`, alertas declaradas, hipótesis no confirmadas y pruebas siguientes seguras.
- NO infiere alerta térmica por °C ni avería por RAM alta; almacenamiento distingue ocupación y salud SMART. No modifica Windows ni genera FPS.
- El modelo cloud recibe el razonamiento estructurado sólo cuando se solicita diagnóstico; el modelo sigue subordinado a REAL_OR_NA y Safety Gate.
- Si el modelo falla o su respuesta se rechaza durante una consulta diagnóstica, CorePulse responde con una guía determinista basada en evidencia (no con conclusiones inventadas).
- Las respuestas API `/v1/analyze` y `/v1/chat` incluyen `intelligence`, auditable y separada del texto generativo. `/v1/status` expone la versión del motor.
- Prueba offline `23_VALIDAR_INTELIGENCIA_V475.bat`; dataset 100% sintético. No se ha validado visualmente en Windows ni se reivindica diagnóstico médico, reparación automática o precisión certificada.

# V474 · Orientación educativa segura y legible

- En consultas de mantenimiento general, una concentración de alcohol expresamente identificada como propiedad del producto no se interpreta como un porcentaje de CPU, GPU, RAM o SSD. La excepción es estrecha y exige intención educativa.
- Las cifras de sensores no sustentadas, FPS falsos, enlaces no verificados y acciones no autorizadas siguen rechazándose sin mostrar el texto del modelo.
- Prompt educativo orientado a pasos seguros y sin métricas de hardware inventadas.
- Respuestas preventivas de contingencia con pasos separados por líneas; tipografía del chat más legible.
- Se conservan conexión simple a Groq, proveedor alternativo, apagado de IA, consentimiento y sensores reales.
- La salida rechazada del video de V473 no está disponible: no se afirma una causa concreta sin evidencia.

# V473 · Conexión simplificada a CorePulse AI Cloud

- Panel principal con botón **Conectar IA**, estado legible y autorización cloud siempre visible.
- Se ocultan de forma predeterminada las direcciones de servidor, modelos alternativos, códigos y BAT auxiliares bajo **Configuración avanzada**.
- Para la prueba local Groq en Windows, el botón inicia el puente si no está activo, verifica su identidad y vincula automáticamente el equipo con un código temporal local (se emite/canjea una sola vez y no se expone en la UI).
- Con consentimiento ausente o revocado nunca se envían preguntas ni sensores. Un servidor diferente requiere su propio permiso.
- Los servidores alternativos, la vinculación manual y el diagnóstico REAL_OR_NA se conservan. No se activa ningún modelo local pesado.
- No se confunde disponibilidad del modelo con sesión vinculada. La interfaz rechaza permisos retirados a mitad de conexión.
- Ver `GUIA_COREPULSE_AI_V473.md`; faltan validaciones gráficas en Windows real.

# V472 · Independencia práctica del motor cloud

- Proveedor OpenAI-compatible configurado por usuario, detrás del backend CorePulse existente.
- Puente alternativo aislado en loopback `127.0.0.1:8766` y base separada de vinculaciones. Groq permanece en `8765`.
- Selector en pestaña AI, consentimiento y token anulados al cambiar de servidor.
- Wizard de URL/modelo y secreto en Credential Manager; bloqueo de redirecciones de upstream y HTTPS obligatorio.
- Guía y tests para verificar independencia sin inventar métricas ni disponibilidad cloud.

# V471 · 2026-10-09 · Vinculación persistente y tutorial limpio

- El bridge Groq guarda vinculaciones en LocalAppData (separado de cada ZIP) cuando se ejecuta en Windows.
- API GET /v1/session autenticada sin consumir cuota ni telemetría; el panel distingue servicio disponible de sesión validada.
- Mensaje de sesión no reconocida en lugar de afirmar revocación sin prueba.
- Tutorial CPU incluye modelo de notebook solo si proviene de evidencia actual, y la búsqueda de YouTube se muestra mediante botón sin URL larga.
- Nuevas pruebas de persistencia, revocación, privacidad y presentación.

# V470 · 2026-10-09 · Contexto de mantenimiento por notebook y CPU

- Se corrige la pérdida de intención tras pedir tutoriales de YouTube: «¿y para mi notebook?» y «¿y para mi CPU modelo exacto?» continúan el mantenimiento preventivo cuando corresponde.
- Identidad exacta del equipo solamente desde evidencia actual, con N/A si falta; una CPU no autoriza desmontaje de un portátil.
- Búsquedas específicas en YouTube solo después de un clic explícito; no son videos verificados y el usuario sabe que abrirlas revela los términos buscados.
- No hereda temas educativos tras un cambio a consulta de métricas, RAM u otras materias; evita fallas por contexto viejo.
- Motor contextual determinista propio sin llamada adicional al LLM; 185 pruebas focalizadas aprobadas, suite completa con 20 fallos gráficos heredados.

# V467 · 2026-10-09 · Chat Cloud desde CorePulse

- Chat UI: acceso directo a puente y generación de códigos, canje explícito del equipo, estado de vinculación claro.
- Preguntas generales permitidas sin telemetría; hardware ausente sigue siendo `N/A`. Análisis del equipo requiere lecturas.
- Estado visible al revocar permiso durante solicitud; mejora de diagnóstico fallback para preguntas de temperatura y sobrecalentamiento.
- Conexión cloud a través de V466, manteniendo cabecera Groq confirmada funcional por el usuario (`CorePulse-AI/466`).
- Pruebas de integración y callbacks sin red pública; no hay prueba visual real de Windows en este entorno.

## V466 — Groq Edge User-Agent Fix

- Cabecera `User-Agent: CorePulse-AI/466` explícita para evitar el identificador `Python-urllib` en solicitudes a Groq.
- Diagnóstico seguro `GROQ_EDGE_BLOCKED_1010` para bloqueos del perímetro Cloudflare, sin revelar respuestas privadas.
- Nuevo BAT 17 para verificar cliente HTTPS sin conexión. Se preservan las reglas, los diagnósticos y el programa CorePulse Windows.
- No garantiza que el error 403 desaparezca: requiere validación en Windows y cuenta real.

## V465 — Groq Permission Root Cause
- Preferencia por Credential Manager, diagnóstico offline de conflictos con GROQ_API_KEY.
- Distinción segura entre bloqueos de modelo a nivel organización o proyecto mediante códigos declarados por Groq.
- Estado HTTP 403 indeterminado queda sin atribución no demostrada; se preserva privacidad.
- Sin cambios en sensores, diagnósticos deterministas, UI o funciones de Windows.

## V463 · GROQ GPT-OSS 120B CLOUD TRIAL
- El backend propio habla con Groq (HTTPS fijo, modelo `openai/gpt-oss-120b`) sin exponer la clave al cliente.
- Puente local opt-in sólo para pruebas gratuitas: `127.0.0.1:8765`, sin LLM local.
- Clave Groq bajo Windows Credential Manager y scripts de configuración y vinculación.
- Consentimiento y tokens reiniciados al cambiar de servidor; apagado general y REAL_OR_NA preservados.
- Prueba sintética explícita y pruebas de red simulada; conexión real requiere API key y Windows.
- Conserva el servidor HTTPS independiente del proveedor y las funcionalidades de V462.

## V462 — 2026-10-09 — Cloud Model Evaluation

- Evaluación por defecto offline sobre 30 situaciones totalmente sintéticas; 13 de riesgo crítico.
- Comparador de modelos con inferencia explícita en cloud (reutiliza exactamente las instrucciones de producción), latencia y tokens reportados cuando existen; resultados ausentes se muestran como N/A/null.
- Comparaciones entre ejecuciones reales condicionadas a SHA-256 del dataset y cantidad igual de muestras; nunca se simula ganador.
- Tres candidatos abiertos para validar; sin decisión definitiva ni demanda de VRAM inferida sin pruebas.
- Tests de seguridad y transporte HTTP local; sin cambios de UI, sensores, diagnóstico local ni acciones Windows.

## V461 · COREPULSE_AI_POST_MODEL_EVIDENCE_GATE

- Barrera determinista de verificación posterior a inferencia para chat y análisis, con rechazo y fallback seguro.
- Control de métricas CPU/GPU/RAM/SSD, SMART, GHz, FPS medidos N/A, URLs de tutorial y afirmaciones de acciones de Windows.
- Distingue `model` de `evidence_fallback` e informa códigos de verificación y campos de evidencia; sin revelar texto rechazado.
- Desactivadas consultas automáticas a YouTube desde CorePulse AI para no exponer hardware a terceros; sólo sugerencias `SEARCH_ONLY` sin red.
- Evaluador sintético de 10 escenarios sin conexión y modo cloud en el servidor sujeto a invocación explícita.
- Nueva guía de política, pruebas y límites de validación (`GUIA_COREPULSE_AI_V461.md`).
- Se preserva la interfaz y motor de diagnóstico locales, opción de apagado, HTTPS + consentimiento cloud y vinculación individual de V460.

# V460 — COREPULSE AI CLOUD BACKEND PRIVATE BETA

- Seguridad: registro individual mediante códigos de un solo uso (sin clave global persistente en cada PC).
- Gestión en servidor: emitir/listar/revocar, con códigos y tokens almacenados exclusivamente como hashes SHA-256 en SQLite.
- Backend: máximo 128 KiB por solicitud y cuota diaria por token atómica.
- Despliegue de referencia: Docker Compose para Caddy HTTPS, backend y modelo vLLM en servidor GPU, sin publicar puertos de inferencia.
- Windows: sigue sin arrancar LLM pesado; conserva consentimiento y REAL_OR_NA. La interfaz aclara el código temporal.
- Limitación: sin servidor propio ya desplegado. Pendiente prueba física de UI Windows, GPU cloud y calidad diagnóstica.

## V458 — SSD principal con scroll e interruptor local de IA
- Base: V457 proporcionada y validada. Los discos se muestran en viewport de 86 px (una unidad visible), con scrollbar desde dos unidades.
- El disco asociado a la unidad del sistema de Windows se ordena primero; los demás se consultan desplazando la rueda o el scrollbar.
- No se reinicia la posición del scroll en cada muestra de sensores; sólo cuando cambia la topología de unidades.
- El espacio vertical recuperado permite que la zona de gráficos ocupe su altura responsive, sin alterar curvas ni sensores.
- El botón minimalista de encendido de IA está dibujado sobre el mismo lienzo del encabezado. Hover muestra «Apagar IA»/«Encender IA».
- El apagado invoca `LocalAIRuntimeManager.stop()` en background: detiene procesos iniciados por CorePulse y evita el autoarranque al reabrir (preferencia en AppData).
- En modo IA apagada, se suspenden los sondeos de estado y el encabezado muestra «IA LOCAL DESACTIVADA». El usuario puede volver a encenderla.
- Un llama.cpp/servidor iniciado externamente no se cierra, para evitar intervenir procesos ajenos; el BAT iniciado por CorePulse finaliza su árbol de procesos propio.
- Se mantiene REAL_OR_NA, el fondo maestro, la telemetría y el resto de CorePulse.

## V457 — Salud de discos a la izquierda + tiempo activo reactivo
- Base exclusiva: V456 WINDOWS_SIDEBAR_SMOOTH_MOTION.
- Las tarjetas de almacenamiento ahora muestran la salud del disco junto a la línea de capacidad/uso, en el lado izquierdo de la tarjeta.
- El extremo superior derecho del disco deja de usar texto “Ver detalles” y ahora usa un botón compacto con icono de ojo.
- El valor visual de salud de disco se simplifica a “Salud XX%” / “Salud N/A” para reducir ruido visual.
- La tarjeta “Tiempo activo” ahora reacciona al estado real del uptime: normal bajo 8 h, advertencia desde 8 h y condición crítica en rojo al superar 10 h.
- Al superar 10 horas activas se muestra recomendación de reiniciar el PC y se habilita un botón “Reiniciar PC” en la esquina inferior derecha de esa tarjeta.
- Se agrega acción real `request_system_restart()` con confirmación previa para solicitar `shutdown /r /t 0` en Windows.
- Se conservan telemetría real, navegación interna, detalle de discos y contrato REAL_OR_NA.


## V456 — Sidebar con movimiento suave al pasar el mouse
- Base exclusiva: V455 del RAR del usuario (derivada de CorePulse_V451(1).rar); sin mezclar ramas V452–V454.
- El contenido del botón existente (icono y texto) se desplaza hasta 5 px con easing; al salir, retorna a su posición. El botón y sus vecinos no se desplazan.
- El resaltado nativo transiciona gradualmente, sin añadir tarjetas, frames, overlays ni fondos secundarios.
- Animación única por botón con cancelación de temporizadores, debounce contra parpadeo y selección persistente.
- Si el cursor entra en otra opción, el hover anterior se revierte; también funciona en Temas y CorePulse AI.
- Repintado parcial durante las transiciones para no recalcular los demás controles; método original conservado para refresh global.
- Se respetan las rutas de navegación, el click, la capa maestra y la configuración responsive.


## V455 — Sidebar: hover nativo restaurado (base del usuario V451)
- Se restaura la respuesta al puntero en las entradas del sidebar (monitoreo, diagnóstico, mantenimiento, historial y personalización).
- Se corrige la pintura que sobrescribía hover_color con el mismo color del fondo.
- El relleno en hover se pinta en el mismo CTkButton original: sin frames/tarjetas/láminas adicionales.
- Se mantienen el clic, la selección activa y la integración con el fondo maestro.
- Se protege el cruce entre icono/texto y se redibuja correctamente al salir.
- Base usada: CorePulse_V451(1).rar proporcionado por el usuario. No se incorporan cambios de V452–V454.


## V451 — navegación, almacenamiento y CorePulse AI
- El botón de menú del sidebar se integra con el fondo del dashboard al contraerlo.
- Los volúmenes montados se actualizan al conectar o retirar una unidad USB.
- Temas y CorePulse AI usan iconos más grandes y una tarjeta de estado con detalle real.

## V450 — AI card rebalanced
- Rebalanced the AI card composition to reduce the awkward look reported in V449.
- Kept the title smaller and tucked into the upper-left corner.
- Re-centered the main AI status across the card and lowered it slightly for a cleaner visual balance.


## V449 — AI card visual polish
- Refined the AI header card composition to look more natural.
- Positioned the accent strip with inner margins like the original card.
- Kept "CorePulse AI" in the upper-left corner and reduced the central status emphasis.
- Rebalanced spacing so the centered status sits lower and feels less forced.


## V448 — AI title + balanced centered text
- Reduced the visual size of the centered AI status text in the top card.
- Restored a discreet "CorePulse AI" label in the upper-left corner of the same integrated surface.
- Kept the native single-canvas implementation and preserved the V445 base elsewhere.

## V447 · AI_NATIVE_INTEGRATED (base única V445)
- Corrige V446: la tarjeta de IA ya no crea un rectángulo de etiqueta/fondo sobre el encabezado.
- El texto centrado y la franja de estado se dibujan sobre el mismo lienzo del fondo maestro de Surface Studio, mediante `AIStatusCanvas` registrado en `WorkspaceBackground`.
- El único texto de IA es el estado real (conectada/iniciando/desconectada), conservando la navegación por clic y el hover.
- Sin cambios en gráficos, telemetría, otras tarjetas ni en los sensores. No contiene los cambios de las ramas V446/V447 anteriores.

## V445 · CHART_COLUMNS_LEFT_ALIGNMENT
- Desplazamiento de 20 px a la izquierda en CPU/RAM/GPU calculado por geometría real.
- Sin cambios en los datos, trazos, ejes de porcentaje, superficie de fondo ni efectos de las tarjetas.
- Pruebas V437 actualizadas y nuevo contrato V445 de alineación persistente en distintas resoluciones.

## V444 · SEAMLESS_INNER_CHART_AXES
- CPU, RAM y GPU: eje transparente sin parche azul opaco ni contorno rectangular.
- Se conserva la imagen del fondo maestro por debajo de las líneas/grillas.
- `main.py`, `dashboard.py`, `dashboard_layout.py` y `chart_workspace_surface.py` comparten contrato sin cuadro, incluso tras reflow.
- Se mantienen hover optimizado de tarjetas (V443) y todas las demás funcionalidades.

## V443 · OPTIMIZED_ROUNDED_CARD_GLOW
- Sustituido el halo por trazos redondeados y cacheados (máximo 3 trazos por canvas participante).
- Hover actualiza sólo el halo, evitando el repintado completo de CTkFrames y fondos interiores.
- Mantiene las esquinas sin líneas rectas o fugas de color y preserva las funciones V442.

# Changelog

## V442 · NATIVE_CARD_PERIMETER_GLOW
- Efecto de borde luminoso integrado al mismo canvas del fondo, no mediante el border_width de CustomTkinter.
- Degradado perimetral continuo cian/verde/violeta/ámbar según tarjeta y estado.
- Redibujo inmediato en Enter/Leave y al cambiar estado AI/Salud, conservando el workspace sin cuadros superpuestos.
- V440 conserva la eliminación de cabeceras superiores en vistas internas.
- Se corrige la versión interna y el nombre de entrega (V441 anterior reportaba V440 por error).

## V440 · INTERNAL_PAGES_NO_TOP_HEADERS
- Se retira la cabecera introductoria de 18 vistas internas: ni texto, ni insignias, ni tarjetas hero, ni reserva vertical vacía.
- El contenido funcional (tarjetas, filtros, pruebas, configuradores y resultados) comienza arriba, sin cambios en cálculos ni telemetría.
- Tweaks ya no restaura el header al salir del Centro de restauración.
- Diagnóstico traslada Cancelar y Sensores a la sección de evidencia en lugar de ocultar sus acciones.
- Detalles SSD y Trazabilidad mantienen Actualizar dentro del contenido inferior.
- Contrato automático en `tests/test_v440_page_headers_removed.py`.

## V439 · HOVER_CANVAS_TILE_ROOT_FIX
- `gui/card_workspace_surface.py`: se elimina el render de rectángulos de hover sobre CTkCanvas, incluso en marcos anidados y sobre iconos o texto.
- El hover ilumina únicamente la franja lateral existente, manteniendo intacto el sustrato nativo y la geometría del Dashboard.
- Cada franja se marca como acento para que el repintado estructural nunca la considere un panel opaco ordinario al iluminarse.
- Se conservan los estados dinámicos de Salud/CorePulse AI, además de los botones contextuales y las líneas de CPU/RAM/GPU/SSD.
- Se agregan pruebas de idempotencia y regresión para verificar que no reaparezcan capas ni colores acumulados en los cambios de hover.

## V438 · SUBTLE_HOVER_FEATHER_NO_TILES
- Se reduce y limita el halo de hover de las tarjetas interactivas para que no se vea como rectángulo cian/verde/violeta/ámbar.
- El brillo nace junto a la línea lateral y desaparece de manera progresiva hacia el centro, los bordes superior/inferior y el extremo derecho.
- Las etiquetas, barras y botones conservan su color exacto del fondo maestro durante el hover, eliminando parches sólidos interiores.
- Se conserva la posición de gráficos V437, el estado de la IA, la navegación y la telemetría.
- Nuevas pruebas de difuminado y no-superposición; suite completa de regresión Tk.

## V437 · CHARTS_ALIGNED_ACCENT_HOVER
- Los ejes de Matplotlib se alinean por posición y ancho real con las tarjetas CPU/RAM/GPU, también en cambios de tamaño.
- Hover con iluminación gradual según acento funcional, dibujada encima de la superficie nativa sin panel extra.
- El brillo responde correctamente al entrar/salir, también sobre etiquetas y controles hijos de la tarjeta.
- Salud del sistema y CorePulse AI usan el tono de su estado operativo real; Sesión informativa no simula interacción.
- Se preserva la visual V436 sin fondos opacos, sidebar ni cambios a la telemetría.
- Nuevas pruebas de geometría y brillo visual Tk.

## V436 · CARDS_TRUE_WORKSPACE_SURFACE
- `gui/card_workspace_surface.py`: pinta en el Canvas de cada tarjeta el mismo gradiente de Surface Studio, respetando las coordenadas reales del workspace; sin colores de relleno aproximados.
- `gui/dashboard.py`: se elimina la mezcla de azul opaco de V435 y se impide teñir toda la tarjeta en hover.
- `gui/workspace_background.py`: tarjetas registradas y redibujadas junto con la superficie principal para tema, cambio de tamaño y navegación.
- `gui/dashboard_layout.py`: el estilizado responsive deja de reinstalar bordes/rellenos de recursos y discos.
- Se mantienen las barras de colores, pastillas, botones de detalle, curvas de los gráficos y telemetría real.

## V435 · CARDS_NATIVE_SURFACE_MATCH
- Nuevo muestreo de la superficie nativa para tarjetas del Resumen: CorePulse AI, estado superior, CPU, RAM, GPU y almacenamiento.
- Las tarjetas usan un material alineado con su posición real en el workspace y ya no dependen de un bloque glass fijo.
- Se eliminan bordes rígidos en tarjetas de recursos y almacenamiento para integrarlas al mismo criterio visual aprobado en gráficos.
- El hover utiliza la nueva superficie dinámica de cada tarjeta, preservando interacción y botones contextuales.
- La sincronización se ejecuta en inicio, reflow responsive, cambios de tamaño y actualización de discos.

## V434 · CHARTS_NATIVE_SURFACE_MATCH
- `gui/chart_workspace_surface.py`: nuevo muestreo de la capa maestra para dibujar únicamente el fondo Matplotlib, sin imagen externa ni wallpaper.
- `frame_charts` sin marco y pintado como contenedor estructural nativo.
- Autoridades `main.py`, `dashboard.py` y `dashboard_layout.py` sincronizan el lienzo en inicio y reflow, preservando curvas y ejes.
- Salud del sistema: sus contenedores/etiquetas internos igualan el material de la tarjeta en todos los cambios de tema.
- Nuevas pruebas de coincidencia píxel por píxel y rasterización de Matplotlib.

## V433 · CHARTS_OUTER_MARGIN_BLEND_FIX
- `frame_charts` adopta `role_color('bg')` en lugar de la superficie oscura.
- El fondo del Figure y del canvas de Matplotlib usa el color de la app.
- El estilizado de `dashboard.py` y `dashboard_layout.py` mantiene ese mismo fondo en reflows y reconfiguraciones.
- Los 3 gráficos internos conservan su fondo propio y sus curvas sin cambios.

## V432 · CHARTS_UNIFIED_SURFACE_NO_OUTER_FRAME
- `dashboard._style_charts()` deja de reactivar el marco exterior.
- Figura y canvas Tk restauran relleno opaco y coherente; no aparece el recuadro negro de V431.
- Se retiran los acentos superpuestos del contenedor externo (no afecta las curvas CPU/RAM/GPU).
- El layout responsivo mantiene el material y el borde 0.

## V431 · CHARTS_CANVAS_PERIMETER_LINES_REMOVED
- El `Figure` de Matplotlib usa `frameon=False`, sin borde visible.
- El patch de la figura fuerza `edgecolor` = fondo y `linewidth = 0`.
- El widget Tk del canvas usa `bd=0`, `relief='flat'` y `highlightthickness=0`.
- La sincronización responsive conserva estos ajustes y no reintroduce las líneas.

## V430 · CHARTS_CONTAINER_BLEND_NO_BOX
- `frame_charts` usa `role_color('bg')` en lugar de una superficie glass propia.
- La figura Matplotlib usa fondo `role_color('bg')` para que el margen externo no forme caja.
- El widget Tk del canvas usa el mismo fondo del dashboard.
- Se eliminan los acentos decorativos del contenedor grande de gráficos.

## V429 · CHARTS_OUTER_CONTAINER_BORDER_REMOVED
- `frame_charts` se crea con `border_width=0`.
- `_style_charts()` ya no reimpone borde al contenedor exterior de gráficos.
- Se mantienen sin cambios los tres gráficos internos y el acento visual lateral del bloque.

## V428 · STATUS_ROW_LAYER_AND_GAP_FIX
- El encabezado del Resumen reduce la franja estructural sin contenido: altura 108→96 y separación inferior 7→2, también en el layout responsivo.
- Se alinean los fondos de los elementos internos de Salud del sistema con la superficie glass.
- Se retira exclusivamente la capa de reflejo PNG sobre las cuatro tarjetas de estado; su color glass y barras laterales permanecen.
- Los módulos inferiores y el sidebar se conservan sin rediseño.
- Se incorporan pruebas de regresión del encabezado, fondos de Salud y registro de capas glass.

## V427 · TOP_STATUS_BORDER_AUTHORITY_FIX
- Corrige la sobreescritura del borde de las tarjetas superiores en `gui/dashboard_layout.py`.
- `_style_status_band` ahora respeta `border_width=0` y la superficie glass.
- `_style_status_mode` mantiene `border_width=0` durante cada reflow responsive.
- Se añadió test de regresión para el estilizado y creación de las tarjetas superiores.

## V426 · TOP_STATUS_CARD_OVERBORDER_FIX
- Se elimina el borde externo de `ai_card` en la cabecera.
- Se elimina el borde externo de `_health_status_card`.
- Se elimina el borde externo de `_status_card` (Supervisión, Trazabilidad y Sesión).
- Se conserva el acento lateral, la superficie glass y las tarjetas inferiores sin cambios.

## V425 · SIDEBAR_NATIVE_CONTROL_SURFACE
- Corrección de fondos propios de CTkButton/CTkLabel sobre la primera capa.
- Color y pintura de controles sincronizados con Surface Studio en coordenadas reales.
- Se preservan selección de menú, comandos, cambios de tema y layout adaptable.

## V424 · SIDEBAR_HOVER_RUNTIME_FIX
- Corregidos todos los valores inválidos `hover_color='transparent'` introducidos en V423: causaban excepción al crear `CTkButton`.
- Se usa `role_color('sidebar')` como hover válido, y `hover=False` en los botones iniciales del sidebar y los dos de Personalización.
- Incluida prueba de regresión para el uso prohibido de color transparente en hover.
- Sin cambios en telemetría, IA, diagnósticos ni tarjetas.

## V423 · SIDEBAR_PERSONALIZATION_UNIFIED_BUTTONS_FLAT
- `PERSONALIZACIÓN` ya no usa un contenedor propio: se compone directamente en `app.sidebar`, igual que Monitoreo, Diagnóstico, Mantenimiento e Historial.
- Los botones del sidebar y de Personalización usan `bg_color='transparent'`.
- Los botones inactivos pasan a `hover_color='transparent'` para eliminar el tono oscuro residual.

## V422 · SIDEBAR_FIRST_LAYER_INTEGRATION
- El `CTkFrame` del sidebar usa `fg_color='transparent'`.
- El sidebar se registra como superficie del `workspace_background`.
- En reconstrucciones y layout responsivo se conserva el modo transparente, evitando que el lateral reaparezca como bloque oscuro independiente.

## V421 · SIDEBAR_FRAME_REMOVED
- Se elimina el perímetro nativo/custom del sidebar.
- El `CTkFrame` lateral queda sin borde (`border_width=0`).
- Se conserva la lógica de alineación/altura del sidebar sin dibujar líneas alrededor del menú.

## V420 · SIDEBAR_BORDER_TRIM
- El perímetro nativo del sidebar pasa a 1 px.
- El footer de Personalización se compacta nuevamente.
- En Resumen, la altura visible del sidebar se recorta 2 px para compensar el borde residual y alinear el cierre con los gráficos.

## V419 · SIDEBAR_EXACT_CHART_ALIGNMENT
- El footer de Personalización se compacta para eliminar altura sobrante en el sidebar.
- En Resumen, la altura del sidebar se iguala exactamente a la línea inferior del panel de gráficos.
- Se prioriza la alineación visual aunque el bloque final tenga que recortar unos pocos píxeles de aire inferior.

## V418 · SIDEBAR_PERSONALIZATION_UNIFIED
- El bloque Personalización del sidebar adopta la misma geometría y lenguaje visual que el resto del menú.
- Temas y CorePulse AI usan alturas, radios y paddings consistentes con las opciones principales.
- El sidebar cierra en la misma línea inferior que el panel de gráficos cuando la geometría lo permite.

## V417 · CLEAN_SINGLE_LAYER_GLASS
- Corrige recuadros oscuros y líneas sobre las tarjetas V416 provocados por añadir el reflejo RGBA repetidamente a CTkFrames transparentes hijos.
- `gui/glass_cards.py` compone un único reflejo sobre el Canvas de cada tarjeta raíz, sin descender a wrappers internos; mantiene el tinte azul glass y los acentos de color de V416.
- Sustituye líneas especulares horizontales por una transición suave de brillo con recorte redondeado y sin bordes duros.
- Conserva el fondo nativo V414, las tarjetas de salud, CPU/RAM/GPU, SSD y CorePulse AI, el sidebar y los gráficos sin cambiar su geometría.
- El estado de CorePulse AI se sigue mostrando según el runtime real; si llama.cpp se cierra, revisar sus logs (no se falsea el estado).

## V416 · VISIBLE_ACRYLIC_GLASS_CARDS
- Corregida la autoridad cromática: `gui/dashboard_layout.py` ya no sobrescribe con colores opacos el efecto glass de `dashboard.py` y `main.py`.
- Glass oscuro visible con tinte de la paleta activa, borde técnico y reflejo óptico frío suave en los límites internos de las tarjetas.
- Nuevo módulo `gui/glass_cards.py`: brillo semitransparente RGBA en memoria, recortado a tarjeta y wrappers CTk sin costuras ni capas flotantes.
- SSD creados dinámicamente reciben el efecto; se mantienen los datos reales y la navegación, los gráficos y el sidebar.
- `core/theme_manager.py` remapea los nuevos roles glass cuando se cambia el tema en vivo.
- No hay alpha nativo de ventana: el acabado es óptico y reversible; no hay imagen wallpaper.

## V415 · GLASS_CARD_EFFECT
- Se añaden roles visuales derivados `glass_surface`, `glass_surface_2`, `glass_hover`, `glass_border` y `glass_track`.
- Las tarjetas del Resumen adoptan un efecto visual tipo glass oscuro (pseudo-transparencia), sin usar alfa real.
- Se mantiene la legibilidad de texto, barras y métricas; no se alteran sensores, IA ni lógica de CorePulse.

## V414 · SURFACE_STUDIO_UNIFIED_GUTTER
- El margen izquierdo del workspace pasa a ser asimétrico y menor (7/9/10 px según layout). Sidebar y gráficos conservan el cierre inferior coordinado de V413.
- Nueva superficie nativa mate para toda la aplicación, con profundidad vertical progresiva y luz ambiental de caída suave en el encabezado.
- Sin comienzo abrupto del tinte en el borde del sidebar; desaparece la franja azul vertical entre paneles.
- Composición de una sola fuente cromática y coordenadas absolutas en los wrappers transparentes, sin PNG, cuadrículas, raíles ni polígonos atravesando tarjetas.
- Conservadas todas las tarjetas, sección SSD, CorePulse AI, telemetría, benchmarks, drivers y Game Boost.

## V413 · SIDEBAR_CHART_SSD_ALIGNMENT_FIX
- Alineación responsive del borde inferior del sidebar con el borde inferior real de los gráficos del Resumen, mediante sincronización después del layout.
- El visor de SSD utiliza una altura exacta de 86 px por tarjeta y un único separador entre unidades, eliminando el sobreborde del host de scroll.
- La superficie interna del visor SSD comparte color con la tarjeta para impedir una franja residual por escalado DPI.
- Espaciado reducido y consistente entre almacenamiento y gráficos.
- Se retira la marca horizontal aislada bajo la cabecera; no se modifican tarjetas ni módulos funcionales.

## V412 · CLEAN_NATIVE_SURFACE_NO_ARTIFACTS
- Se corrige el renderizado recortado de líneas y formas nativas en los huecos de V411.
- Fuera polígonos gigantes, retícula, marcas y raíles junto al sidebar que causaban aspecto de bug.
- Diseño del sustrato como profundidad cromática suave con una única marca corta alineada al encabezado.
- La geometría se recorta por superficie y usa coordenadas globales estables al cambiar tamaño/tema/sidebar.
- Sin imágenes de fondo, cambios en tarjetas ni en módulos de telemetría, IA o mantenimiento.

## V411 · VISIBLE_NATIVE_SURFACE
- Corrige la escasa visibilidad del fondo nativo V410: colores y contraste rediseñados para que se distinga en los espacios reales entre módulos.
- Cabecera con tratamiento cromático progresivo, planos vectoriales arquitectónicos, líneas de precisión y separadores visibles.
- Riel funcional que se adapta a la posición real del sidebar y detalles discretos en los márgenes; diseño hecho por Canvas/Tk, sin PNG de fondo.
- Mismo sistema de coordenadas para raíz, contenedores y encabezado, sin rectángulos opacos sobre el nombre real del equipo.
- No se modifican tarjetas, telemetría, IA, drivers, Gaming ni benchmarks.

## V410 · NATIVE_WORKSPACE_DESIGN
- Retira el wallpaper PNG usado desde V404–V409. El fondo pasa a ser una superficie diseñada mediante primitivas Tk y colores del tema activo.
- Composición única y alineada en la ventana, los contenedores estructurales y las páginas internas; sin recortes ni imagen estirada.
- Conserva el encabezado con sólo la identidad del equipo y la tarjeta CorePulse AI independiente; sin cuadrados de fondo tras el logo/nombre.
- Actualiza el self-test del EXE para comprobar la disponibilidad del compositor nativo, en vez de exigir la imagen que se retiró.
- No se alteran las tarjetas funcionales, sensores, benchmarks, Game Boost, drivers ni contratos REAL_OR_NA / REAL_FPS_OR_NA_ONLY.

## V409 · HEADER_IDENTITY_TRUE_ALPHA_FIX
- Elimina los recuadros oscuros bajo el símbolo blanco y el nombre del equipo provocados por CTkLabel sobre un fondo compuesto.
- Dibuja la identidad en un Canvas con el **mismo recorte alineado** del wallpaper maestro, texto actualizable y logo RGBA transparente.
- Mantiene el encabezado sin tarjeta, CorePulse AI a la derecha y el resto de tarjetas/funciones de V408.
- Valida la composición Tk, actualización del nombre, resize y orden de capas en un entorno gráfico aislado.

## V408 · HEADER_TRUE_BACKGROUND_INTEGRATION
- El encabezado del Resumen se registra como superficie del wallpaper maestro, igual que otras capas estructurales.
- La zona donde se muestra el nombre del equipo deja de verse como una banda uniforme separada.
- Se conserva la tarjeta de CorePulse AI como único bloque visual independiente en la franja superior.

## V407 · HEADER_NAME_ONLY_INTEGRATED
- El bloque superior izquierdo del Resumen deja de renderizarse como tarjeta opaca.
- El encabezado muestra solamente el nombre real del equipo/notebook, integrado directamente al fondo maestro.
- Se conserva la tarjeta independiente de CorePulse AI a la derecha, sin rediseñar las demás tarjetas ni afectar la telemetría.

## V406 · SEAMLESS_MASTER_BACKGROUND_HEADER_FIX
- Se elimina el relleno azul plano de `ImageOps.contain`: un solo PNG maestro cubre 100 % del cliente sin márgenes ni recortes.
- Los CTkFrame estructurales renderizan el recorte alineado de la **misma** imagen fuente; no se alteran tarjetas y widgets opacos.
- Navegación sincronizada con el fondo maestro tanto en Resumen como en páginas internas.
- La tarjeta CorePulse AI del encabezado conserva su estilo y estado, pero se evita el solapamiento por columnas y la compresión vertical responsive.
- Funciones, sensores, IA, drivers, Gaming, FPS y lógica CorePulse permanecen iguales a V405.

## V405 · FULL_CLIENT_MASTER_BACKGROUND
- Corrige el fondo maestro de V404 que se recortaba al tamaño/aspect ratio de `main_content`.
- El fondo ahora cubre toda el área cliente de CorePulse y conserva la imagen completa mediante `ImageOps.contain`.
- No se modifican tarjetas, gráficos, telemetría, sidebar ni navegación funcional.

## V404 · CLEAN_REBUILD_MASTER_WORKSPACE
- Nueva carpeta de producto reconstruida desde la base funcional V400.
- Se eliminaron caches Python/pytest, tests de desarrollo empaquetados y validaciones históricas del runtime.
- Se añadió un único fondo maestro compartido por todo el workspace.
- Las páginas internas usan una raíz transparente sobre la misma capa; no se replica el fondo por pestaña.
- Se conserva el diseño funcional V400 de tarjetas y controles.
- Se eliminó el botón redundante `← Resumen` de CorePulse AI; el sidebar queda como navegación canónica.
- Se mantiene el bootstrap de IA para PC limpio, telemetría, diagnósticos, drivers, Gaming y REAL_OR_NA.

## V400 · HEADER_BACK_BUTTON_REMOVAL_CLEANUP
- Se eliminaron los botones de encabezado "Volver al monitoreo" en Centro de salud, detalles de CPU/GPU/RAM/Red/Telemetría, Tweaks, Limpieza y Diagnóstico.
- Se reajustó el bloque de títulos para ocupar correctamente el espacio liberado.
- Se limpió código obsoleto asociado a esos botones (imports y contexto de header no usados).

## V399 · FRESH_PC_AI_BOOTSTRAP_FIX

- Corregido el primer arranque de CorePulse AI en un PC Windows limpio.
- WinGet se localiza también desde WindowsApps/Get-Command, no sólo desde PATH.
- Si WinGet no deja `llama.cpp` disponible, CorePulse descarga automáticamente el runtime portable oficial CPU x64 de llama.cpp a AppData y lo reutiliza en siguientes inicios.
- El build EXE incorpora CorePulse AI Server y lo ejecuta embebido en el proceso, por lo que no requiere Python/pip externo para el servidor.
- FastAPI/Uvicorn/Pydantic pasan a formar parte del runtime normal y del build de CorePulse.
- `CorePulse_AI_DATA_DIR` se mueve a AppData para que el servidor no escriba dentro de la carpeta del programa.
- Se mantiene la descarga del modelo Qwen3-4B GGUF por llama.cpp y la autoridad `REAL_OR_NA` de CorePulse.
- La limpieza estructural de V398 se conserva; no se reintroduce la rama académica.

## V398 · PROJECT_CLEANUP_RUNTIME_ONLY

- Limpieza estructural del proyecto sin cambiar la funcionalidad de producto.
- Eliminados cachés `__pycache__`, `.pyc` y `.pytest_cache`.
- Eliminado del CorePulse normal el módulo académico antiguo CorePulse-IA (Groq/Ollama, demos, evidencia, RAG académico, scripts y documentación ISY0101), que pertenece a su repositorio separado.
- Eliminado `gui/monitoring_status.py`, sin referencias activas.
- Eliminado `CorePulse_AI_Model_Host/Localizar_Llama_Host.ps1`, obsoleto desde el localizador BAT.
- Eliminadas validaciones históricas V390–V397 del root; la trazabilidad vigente queda en este changelog y en la validación V398.
- Manifiestos de dependencias reducidos a los que usa el producto/runtime/build.
- Recursos binarios duplicados consolidados: un PNG de marca y un ICO canónico.
- Credenciales de IA reducidas al token propio `corepulse_server`; se retira la superficie Groq del producto normal.
- README y guía de pruebas reescritos para el producto CorePulse actual.
- Conservados telemetría, discos, sensores, Gaming, Game Boost, F11, planes nativos, drivers, mantenimiento, CorePulse AI local, `REAL_OR_NA` y `REAL_FPS_OR_NA_ONLY`.

## V397 · AI_MODEL_LAUNCH_FALLBACK_FIX

- Autoarranque de IA con múltiples candidatos de llama.cpp y fallback al BAT manual.
- Bind local a `127.0.0.1` y diagnóstico mediante log real.

## V396 · AI_AUTOSTART_RELIABILITY_FIX

- Orden de arranque modelo → servidor y reutilización del entorno del servidor.

## V395 · AI_PER_QUERY_EVIDENCE_AUTOSTART

- Evidencia congelada por consulta y autoarranque de CorePulse AI desde el inicio normal.

## V394 · NATIVE_POWER_PLAN_DISCOVERY_LEGACY_CLEANUP

- Planes de energía obtenidos desde Windows; limpieza segura de planes CorePulse heredados.

## V393 · NATIVE_POWER_PLANS_ONLY

- CorePulse deja de crear o modificar planes de energía.

## V392 · STATIC_CARD_HOVER_FIX

- Las tarjetas dejan de expandirse al hover.

## V391 · F11_NATIVE_MONITOR_FULLSCREEN_FIX

- Corrección de fullscreen F11 y restauración de geometría.

### V464 — Groq Connection Diagnostics

- Se elimina la salida genérica RuntimeError de la prueba sintética y se muestra un código de fallo no sensible.
- Nuevo diagnóstico GET /models sin telemetría real, sin seguir redirecciones HTTP.
- Corrección de ruta en 13_VALIDAR_GROQ_V463.bat.
- Se mantienen el consentimento, REAL_OR_NA, seguridad y fallback del CorePulse V463.
