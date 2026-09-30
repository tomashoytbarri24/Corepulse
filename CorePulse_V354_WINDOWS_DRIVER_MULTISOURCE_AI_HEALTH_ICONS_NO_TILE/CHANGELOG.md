# CorePulse V354 — Health Center Icons No Tile

- Base directa V353; se conservan Game Boost, CorePulse AI, llama.cpp y el resto del layout sin cambios.
- En las tarjetas del Centro de salud se elimina únicamente el cuadrado/fondo redondeado que envolvía cada icono.
- Los iconos quedan limpios sobre la tarjeta, manteniendo su color de acento, posición y jerarquía visual.
- No se modifican textos, botones, bordes laterales, estados, telemetría ni lógica funcional.

# CorePulse V353 — Game Boost Clean Icon Fix

- Base directa V352; se conservan intactas las correcciones de CorePulse AI y llama.cpp.
- Se elimina el mando vectorial grueso/glow introducido en V352.
- El fondo, las ondas, dimensiones y layout de Game Boost no se modifican.
- El mando vuelve a dibujarse con el glyph nativo `Segoe MDL2 Assets`, en cyan, centrado y sin recuadro, cápsula ni halo propio.

# CorePulse V352 — Game Boost Icon Only Reference

- Base directa V351: se conserva completa la corrección de `llama.exe` / `llama-server.exe`, el arranque de CorePulse AI y el resto del layout Gaming.
- Se elimina exclusivamente el modelo de cápsula/botón del centro visual de Game Boost.
- El fondo, las ondas y el panel se mantienen intactos; sólo cambia el icono.
- El mando pasa a ser un icono vectorial cyan, centrado y sin recuadro detrás, siguiendo la referencia final aprobada por el usuario.

# CorePulse V351 — Game Boost Centro de Salud Model

- Base directa V350: se conserva completa la corrección de descubrimiento de `llama.exe` / `llama-server.exe` y el inicio en un clic de CorePulse AI.
- Game Boost deja definitivamente la baldosa/cuadrado del mando: ahora usa un botón/cápsula horizontal inspirado en la opción activa `Centro de salud`.
- El nuevo modelo usa relleno azul, borde cian, halo muy sutil, línea lateral verde y mando blanco; no se utiliza morado.
- No se modifica el layout general de Gaming, telemetría, perfiles, detección de juegos, `REAL_OR_NA` ni `REAL_FPS_OR_NA_ONLY`.

# CorePulse V350 — llama.cpp Host Discovery + Game Boost Health Style

- Corregido el inicio en un clic de CorePulse AI: WinGet instala el paquete real `ggml.llamacpp` y CorePulse detecta tanto `llama.exe` como `llama-server.exe`.
- Tras instalar llama.cpp, el BAT localiza el ejecutable inmediatamente en PATH, WinGet Links o WinGet Packages; ya no obliga a cerrar y volver a abrir la consola.
- El Model Host usa `llama serve` cuando existe el frontend unificado y ejecuta `llama-server.exe` directamente cuando ésa es la distribución instalada.
- Game Boost conserva la baldosa redondeada solicitada, pero adopta el lenguaje azul/cian de la selección Centro de salud; se elimina el morado.
- Sin cambios en REAL_OR_NA, REAL_FPS_OR_NA_ONLY, telemetría, perfiles de energía ni detección de juegos.

# CorePulse V348 — Gaming Game Boost Purple Tile

- Game Boost adopta el icono morado de la referencia: baldosa `#271733` + mando `#D28BFF`.
- Se conserva el placeholder procedural con ondas; no se añaden imágenes ni assets externos.
- Sin cambios en telemetría, perfiles de energía, lógica de Game Boost, REAL_OR_NA ni REAL_FPS_OR_NA_ONLY.

# CorePulse V347 — Gaming Profile Card Crop

- Base V346.
- Recortada la altura de las cuatro tarjetas de perfil para que sus bordes cierren inmediatamente después del contenido, como en la referencia marcada.
- Eliminado el tramo vacío inferior dentro de Equilibrado, Rendimiento, Máximo y Ahorro de energía.
- Ajuste responsivo para 1080p/900p/ventanas pequeñas sin reducir Game Boost.
- Se conservan acentos funcionales, perfiles de Windows, REAL_OR_NA y REAL_FPS_OR_NA_ONLY.

# CorePulse V346 — Gaming Reference Spacing Polish

- Base V345.
- Eliminada la franja inferior sobrante del bloque Perfil de rendimiento.
- Las cuatro tarjetas de energía aprovechan esa altura y conservan sus acentos verde/cian/violeta/ámbar.
- Añadida una separación limpia entre las pestañas Inicio/Biblioteca/Estabilidad/Overlay y el plan de energía.
- Cabecera Gaming reajustada para una jerarquía visual más equilibrada, sin reintroducir marco exterior.
- Se conserva el tamaño restaurado de Game Boost y el escalado responsivo de V345.
- Sin cambios en REAL_OR_NA, REAL_FPS_OR_NA_ONLY, Driver Hub, CorePulse AI o telemetría.

# CorePulse V345 — Gaming Content Scale Restore

- Base V344.
- Recuperada la escala visual del área útil de Gaming sin revertir la cabecera compacta.
- Perfiles de energía más altos y legibles en 900p/1080p, manteniendo las cuatro opciones visibles.
- Game Boost recupera tamaño: visual izquierdo, juego/FPS y recursos se escalan según la altura real de la ventana.
- En ventanas pequeñas se conserva un tamaño reducido y el scroll evita recortes.
- Sin cambios en REAL_OR_NA, REAL_FPS_OR_NA_ONLY, detección de juegos, perfiles o telemetría.

# V344 — Gaming Header Compact + Energy Layout

- Eliminado el acento cian suelto de la cabecera Gaming.
- Cabecera y navegación superior movidas hacia arriba y compactadas.
- Perfiles de energía reorganizados en cuatro tarjetas equivalentes, incluyendo Ahorro de energía visible.
- Se mantienen los contratos REAL_OR_NA y REAL_FPS_OR_NA_ONLY.

# V343 — Gaming Profile + Navigation Fix

- Base: V342.
- Gaming: corregido el bloque Perfil de rendimiento para que Equilibrado, Rendimiento y Máximo vuelvan a mostrar siempre título y descripción en distintos DPI.
- Gaming: restaurado Ahorro de energía como control visible, con acento ámbar y borde cuadrado.
- Gaming: eliminado únicamente el cuadro/borde exterior de la cabecera; se conservan volver, CENTRO DE RENDIMIENTO, Gaming e icono.
- Gaming: pestañas Inicio/Biblioteca/Estabilidad/Overlay ahora se distribuyen de forma adaptable a todo el ancho útil y reciben un acabado más limpio.
- Sin cambios en REAL_OR_NA, REAL_FPS_OR_NA_ONLY, Driver Hub o CorePulse AI.

# V342 — Summary Card Hover Expand

- Base: V341.
- Las tarjetas principales de Resumen ahora usan la misma micro-expansión horizontal suave del sidebar al posicionar el mouse.
- El efecto se aplica a Salud del sistema, Supervisión actual, Trazabilidad, Sesión y las tarjetas CPU/RAM/GPU.
- La expansión reutiliza el espacio de los márgenes internos del layout: no aumenta la altura ni altera la telemetría.
- Se conservan los botones contextuales "Ver detalles" y el hover visual existente.
- Sin cambios en REAL_OR_NA, REAL_FPS_OR_NA_ONLY, Driver Hub, Gaming o CorePulse AI.

# V341 — Sidebar Hover Expand

- Base: V340.
- Las opciones del sidebar ahora se expanden horizontalmente al posicionar el mouse.
- Animación breve con easing, sin cambiar la altura ni desplazar las opciones vecinas.
- El efecto se aplica a navegación, Temas y CorePulse AI.
- Se desactiva automáticamente cuando el sidebar está colapsado.
- Sin cambios en telemetría, REAL_OR_NA, REAL_FPS_OR_NA_ONLY, Drivers o CorePulse AI.

# CorePulse Changelog — rama actual

## V340
- Gaming: Juego actual/FPS y las tres tarjetas de CPU/GPU/RAM pasan a bordes cuadrados.
- Gaming: los tres perfiles de rendimiento pasan a tarjetas de borde cuadrado.
- Gaming: cada perfil muestra permanentemente una franja inicial con su color funcional: Equilibrado verde, Rendimiento cian y Máximo violeta.
- El perfil activo conserva además el borde completo en su color correspondiente.
- Sin cambios en telemetría, REAL_OR_NA, REAL_FPS_OR_NA_ONLY, Driver Hub o CorePulse AI.

## V339
- Gaming: el icono central de espera usa el mismo glyph limpio de la esquina superior (Segoe MDL2 Assets), sin caja de fondo.
- Gaming: tarjeta Perfil de rendimiento recortada para eliminar espacio vertical sobrante.
- Gaming: Perfil de rendimiento y Game Boost alineados con el borde izquierdo de la navegación superior.
- Se conserva el render 4x + LANCZOS de las ondas y los contratos REAL_OR_NA / REAL_FPS_OR_NA_ONLY.

## V338
- Base V337.
- Game Boost: recuperado el aspecto redondeado del mando usado en V336, pero integrado dentro del raster del placeholder para eliminar por completo el cuadrado oscuro del widget superpuesto.
- Ondas renderizadas con supersampling 4x, 420 muestras por curva y un único downsample LANCZOS para reducir dientes de sierra en DPI/escalados distintos.
- Cintas de fondo más finas y transparentes; líneas principales de ~1 px real con glow separado para un acabado más limpio.
- El icono y las ondas se componen en una sola imagen procedural, sin assets generativos ni telemetría simulada.
- Sin cambios a REAL_OR_NA, REAL_FPS_OR_NA_ONLY, Driver Hub o CorePulse AI.

## V337
- Base V336.
- Pulido visual de Game Boost para acercarlo a la referencia aprobada y corregir lo observado en la prueba real.
- El mando de espera deja de depender del emoji de Windows y se dibuja por código dentro del mismo lienzo, eliminando el recuadro oscuro que podía aparecer detrás.
- Ondas azules/cian redistribuidas hacia la zona media-inferior, con cintas translúcidas, glow suave y trazos más finos para reducir el espacio vacío y mejorar profundidad.
- Placeholder generado a 2x con Pillow, reducción LANCZOS y clipping redondeado para mantener suavidad entre DPI distintos.
- Panel derecho compactado ligeramente para que Juego actual, FPS y las tres filas de recursos queden visualmente equilibrados con la carátula.
- Sin cambios a telemetría, REAL_OR_NA, REAL_FPS_OR_NA_ONLY, Driver Hub o CorePulse AI.

## V336
- Base V335.
- Rediseñado el fondo de espera de Game Boost para eliminar las masas/polígonos dentados observados en distintos DPI.
- Las ondas se generan por código con Pillow a 2x y reducción LANCZOS, logrando líneas cian/azules más finas, suaves y concentradas en el tercio inferior.
- Añadido glow sutil y fondo oscuro degradado sin assets decorativos externos ni imágenes generadas.
- El icono de juego se reposiciona sobre las ondas para acercarse a la referencia aprobada.
- Sin cambios a telemetría, REAL_OR_NA, REAL_FPS_OR_NA_ONLY, Driver Hub o CorePulse AI.

## V335
- Base V334.
- Game Boost corregido para coincidir con la referencia final aprobada: visual grande a la izquierda y estado del juego/FPS arriba a la derecha.
- CPU/GPU/RAM vuelven a filas verticales con barras proporcionales a telemetría real.
- El estado sin juego dibuja por código ondas azules/cian dentro del visual, sin assets generados ni borde azul interno.
- Se mantiene carátula real cuando existe un juego activo, REAL_OR_NA y REAL_FPS_OR_NA_ONLY.
- Sin cambios a Driver Hub, CorePulse AI ni al módulo de Actualizaciones de CorePulse (sigue retirado).

## V334
- Base V333.
- Game Boost ajustado al modelo visual aprobado: visual/carátula grande a la izquierda y un único panel de información a la derecha.
- Recursos CPU/GPU/RAM vuelven a una fila horizontal de tres tarjetas en la parte superior derecha.
- Juego actual y FPS quedan debajo de los recursos, separados por un divisor discreto.
- Eliminadas las barras de progreso del rediseño V333 para conservar la composición exacta de la referencia.
- La carátula conserva un marco estructural neutro, sin borde cian/azul interno.
- Sin cambios a telemetría, REAL_OR_NA, REAL_FPS_OR_NA_ONLY, Driver Hub o CorePulse AI.

## V333
- Rediseño del bloque Game Boost según la referencia visual aprobada.
- Carátula/visual del juego ampliado a la izquierda, sin borde azul interno.
- Juego actual y FPS reubicados al panel superior derecho.
- CPU/GPU/RAM apilados a la derecha con barras de uso real.
- Ajuste adaptable para distintas resoluciones/DPI, sin alterar REAL_OR_NA ni REAL_FPS_OR_NA_ONLY.

# V332 — Consolidation Fix: CorePulse Updates UI Remains Removed

- Base V331 consolidada.
- Se reafirma la decisión de producto de mantener eliminado el módulo interno **Actualizaciones de CorePulse**.
- Personalización queda únicamente con **Temas** y **CorePulse AI**; no se reintroducen botón, ruta ni diálogo de actualizaciones de la aplicación.
- Se limpian referencias de widgets heredados durante la reconstrucción del sidebar para impedir que una rama antigua vuelva a mostrar ese acceso.
- Driver Hub, actualizaciones de controladores y opciones de Windows Update dentro de Tweaks permanecen intactas porque son funciones separadas.
- Sin cambios a REAL_OR_NA, REAL_FPS_OR_NA_ONLY, CorePulse AI, Driver Hub, benchmark o telemetría.

# V331 — Consolidated Driver Multi-source + CorePulse AI

- Consolida la rama **V327 Driver Hub Multi-source** con la rama **V330 CorePulse AI Response Polish**.
- Se conserva el Driver Hub con búsqueda multi-fuente, flujo inline de buscar/descargar/instalar, inventario priorizado y validación antes de instalar.
- Se conserva CorePulse AI generativa con backend propio, host local de desarrollo, lanzador de un solo clic, guardas de solicitudes y respuestas en texto limpio.
- Se mantienen `REAL_OR_NA` y `REAL_FPS_OR_NA_ONLY`; la IA explica evidencia y no sustituye el motor técnico.
- Navegación, temas, almacenamiento y mejoras responsive de la rama Driver Hub quedan preservadas junto con CorePulse AI.

# V330 — CorePulse AI Response Polish

- Base V329.
- Corregido el Markdown visible observado en la prueba real: CorePulse AI ahora entrega texto plano limpio en el CTkTextbox.
- El prompt del servidor deja explícito que la IA no puede aumentar ni reducir la severidad calculada por CorePulse ni cambiar "elevada" por "muy cerca/crítica".
- Las respuestas distinguen entre valor observado y clasificación de CorePulse, evitando crear umbrales propios.
- Se priorizan acciones reversibles y de bajo riesgo; BIOS, voltajes y firmware sólo se mencionan si el usuario lo solicita.
- Respuestas más concisas y con menos repetición; límite generativo predeterminado reducido a 650 tokens.
- CorePulse AI Server actualizado a V1.3; REAL_OR_NA, sensores y Health Engine permanecen sin cambios.

# V329 — CorePulse AI One Click

- Unifica la preparación y el arranque del Model Host, CorePulse AI Server y CorePulse Desktop en `Iniciar_Todo_CorePulse_AI.bat`.
- Crea un entorno virtual aislado para el backend y prepara sus dependencias sólo en la primera ejecución.
- Instala `llama.cpp` mediante WinGet cuando falta, reutilizando una instalación existente cuando ya está disponible.
- Espera activamente a los puertos 8766 y 8765 antes de abrir CorePulse para evitar carreras de inicio.
- Mantiene el modelo fuera de CorePulse Desktop; la descarga pesada sólo pertenece al host de desarrollo.
- Conserva REAL_OR_NA y la separación CorePulse mide / CorePulse AI explica.

# CorePulse Changelog — V328

## V328
- Base V327.
- CorePulse AI incorpora conversación real mediante `/v1/chat`, manteniendo la evidencia REAL_OR_NA actual en cada turno.
- Backend actualizado a CorePulse AI Server V1.2 con conexión a host generativo privado OpenAI-compatible.
- El servidor distingue modelo configurado de host realmente alcanzable y conserva Evidence Engine como degradación segura.
- Historial conversacional limitado a 8 mensajes y no persistido por el backend.
- La interfaz permite conversar, enviar con Enter, limpiar historial y ejecutar análisis del estado actual.
- Preparado para un Model Host separado basado en llama.cpp/Qwen3; no se usa Ollama y el modelo no se incluye en CorePulse Desktop.
- Sin cambios a sensores, Health Engine o reglas REAL_OR_NA.

## V327
- Base V326.
- Corregido el agotamiento accidental del límite de CorePulse AI observado en la prueba real: ráfagas repetidas del mismo análisis ya no consumen múltiples cuotas.
- Cliente AI añade guardia temporal y mantiene una única solicitud activa por interacción.
- Backend CorePulse AI V1.1 deduplica solicitudes idénticas durante 8 s y eleva el límite de desarrollo predeterminado a 200 consultas/día por instalación.
- La interfaz muestra las consultas restantes cuando el servidor las informa.
- REAL_OR_NA y la autoridad técnica de CorePulse permanecen sin cambios.

## V326
- Base V325.
- CorePulse AI deja de pedir/procesar claves OpenAI/Groq en el PC del usuario.
- Nuevo cliente liviano para backend propio de CorePulse AI con registro por instalación y token en Windows Credential Manager.
- Contexto de hardware sanitizado y contrato REAL_OR_NA preservado.
- Incluido proyecto `CorePulse_AI_Server` con FastAPI, rate limit, almacenamiento de tokens, Evidence Engine seguro y adaptador para modelo autoalojado.
- Eliminadas dependencias `openai` y `groq` del runtime de escritorio.
- Sin Ollama ni modelos locales dentro de CorePulse.

## V325 — CorePulse AI Cloud Only
- Base V324.
- Se elimina Ollama/IA local del Centro de IA.
- Proveedores disponibles: Automático, OpenAI y Groq.
- Automático prioriza OpenAI y usa Groq como alternativa cuando existe una clave configurada.
- Se eliminan URL local, modelo local, detección del servicio local y llamadas HTTP a Ollama.
- Las claves siguen guardándose en Windows Credential Manager.

## V324 — CorePulse AI Provider Center
- Base V323.
- Nuevo módulo interno `CorePulse AI` en Personalización.
- Proveedor automático: OpenAI -> Groq -> IA local (Ollama) según disponibilidad.
- OpenAI usa Responses API; modelo predeterminado `gpt-5.6-luna` y opciones Terra/Sol.
- Groq conserva compatibilidad con GPT-OSS; Ollama permite modo local sin clave.
- Claves OpenAI/Groq se guardan en Windows Credential Manager, nunca dentro del ZIP o `ai_settings.json`.
- Nuevo análisis del estado actual usando solo contexto sanitizado REAL_OR_NA: salud, CPU, RAM, GPU y almacenamiento.
- La IA queda explícitamente limitada a explicar; no modifica sensores, diagnóstico ni Windows.

# V327 — Driver Hub Multi-source

- Intel Wireless Bluetooth se consulta también contra Intel Download Center oficial.
- Microsoft Catalog pasa a fallback y usa Hardware/Compatible IDs.
- El escaneo principal cubre siempre GPU, red, audio, almacenamiento y Bluetooth.
- Los instaladores oficiales se descargan con verificación SHA-256/firma y se ejecutan elevados tras respaldo.
- Resumen: Procesador / Memoria RAM / Tarjeta Gráfica.

# V326 — Driver Hub Inline Install Flow

- Cada incidencia puede buscar su actualización online sin recargar la página.
- Cuando existe una versión compatible, la misma tarjeta cambia a Descargar y luego Instalar.
- Buscar seleccionados actualiza las tarjetas en el sitio y conserva resultados previos.

# V325 — Driver Hub feedback + contrast

- Contraste fijo de botones en todos los temas oscuros.
- Buscar seleccionados muestra resultado por dispositivo.
- Inventario conserva HardwareID real para consultas seleccionadas.

# V324 — Driver Hub 2.1 Compact & Fast

- Incidencias seleccionables y búsqueda prioritaria de seleccionados.
- Tarjetas locales y resumen compactados.
- La búsqueda reutiliza el inventario Windows ya cargado; elimina un segundo barrido CIM.
- Búsqueda normal limitada a 5 dispositivos prioritarios y timeout web reducido.
- Caché del inventario local entre reaperturas del Centro de salud.

# V323 — Driver Hub 2.0

- Nueva interfaz de controladores centrada en hardware importante y decisiones accionables.
- Búsqueda por Hardware ID con caché de inventario, caché de resultados y consultas paralelas.
- Selector por actualización, Descargar todo e Instalar seleccionados.
- Firmware separado de la instalación masiva.
- Enlaces de soporte oficial cuando el fabricante es reconocible.
- Respaldo del driver OEM actual mediante PnPUtil antes de reemplazarlo.

# V322 — Storage Startup Health Guard

- Corrige la regresión donde el warm-up podía mostrar `Salud N/A` aunque existiera un porcentaje real cacheado.
- Preserva el paquete completo de evidencia de salud cuando una lectura transitoria falla.
- El splash espera brevemente la lectura cuantitativa lenta si hace falta.

# V321 — Instant Data + Live Themes Polish

- Dos muestras reales estabilizadas antes de revelar el Dashboard.
- Salud NVMe rápida precargada durante el splash para evitar corrección tardía.
- Salud de almacenamiento alineada al extremo derecho.
- Sidebar exterior compactado al contenido real.
- Temas aplicados en caliente, sin reinicio del proceso.

## V320
- Splash: porcentaje visible de carga hasta 100%.
- Almacenamiento: restaurado el pipeline NVMe/SMART cuantitativo, caché persistente y refresco en dos fases para evitar regresiones a N/A.
- Dashboard: la tarjeta de almacenamiento consume el campo real `health`.
- Drivers: búsqueda prioritaria acelerada, sin consulta PnP por cada driver, 10 dispositivos en paralelo, timeout corto y caché del catálogo.
- Temas: 20 temas oscuros y selector visual mejorado con muestras de paleta.
- Contrato de no regresión y tests para proteger estas funciones en merges futuros.

## V318
- Base V317.
- Salud del sistema: pulido visual premium del porcentaje de salud.
- Porcentaje principal más grande y jerarquía reforzada.
- Barra de salud con transición visual suave hacia el valor real.
- Mini indicador de estado de tres niveles (normal / atención / crítico).
- Tooltip refinado con encabezados y bullets más limpios.
- El color del acento lateral, icono y estado ahora sigue la severidad real.
- Sin cambios en la política REAL_OR_NA ni en los valores de telemetría.

## V314
- Base V313.
- Resumen: separación clara entre "Estado del agente" y "Supervisión actual".
- Estado del agente ahora informa solo disponibilidad del monitoreo, modo actual y frescura de actualización.
- Las alertas y condiciones del equipo quedan exclusivamente en Supervisión actual, evitando duplicación visual y semántica.

## V313
- Base V312.
- Resumen: rediseño visual de la tarjeta "Estado del agente" para integrarla mejor con el lenguaje del Resumen.
- La tarjeta pasa a un formato más compacto/cuadrado, con mejor jerarquía visual, mejor espaciado y acento lateral coherente con las tarjetas superiores.
- Se añade un acento lateral dinámico que sigue el tono del estado del agente.

## V312
- Base V311.
- Sidebar: reduce la latencia percibida manteniendo el commit estabilizado que eliminó los artefactos visuales.
- Slide reducido de 72 ms / 6 pasos a 52 ms / 4 pasos, con avance inicial más inmediato.
- Se eliminan de la ruta crítica del clic las limpiezas de máscaras/capas heredadas que ya no se usan.
- El reflow de Matplotlib continúa asíncrono y se agenda después del frame estable.

## V311
- Base V310.
- Sidebar: el commit final ya no reactiva el dibujo de Windows inmediatamente después del cambio de grid.
- El HWND raíz permanece congelado un ciclo idle adicional para que CustomTkinter termine sus redibujos internos antes de publicar el frame final.
- Se elimina el frame fantasma con textos/tarjetas duplicadas observado al finalizar la apertura/cierre.
- Se conserva el drawer rápido de V310 y el reflow de Matplotlib sigue siendo asíncrono.

## V310
- Base V309, conservando su comportamiento visual estable.
- Sidebar: transición reducida de 96 ms a 72 ms y de 8 a 6 pasos para mejorar respuesta percibida.
- Se evita llamar lift() en cada frame de la animación; el sidebar se eleva una sola vez al iniciar.
- Reflujo de gráficos posterior al commit reducido de 24 ms a 8 ms y sigue usando draw_idle.
- Sin cambios en telemetría, REAL_OR_NA, REAL_FPS_OR_NA_ONLY ni lógica funcional.

## V309
- Base V308.
- Sidebar: nuevo drawer asíncrono. Durante el deslizamiento sólo se mueve el sidebar; el dashboard no cambia de ancho por frame.
- El cambio de ancho del contenido ocurre una sola vez al final bajo un commit Win32 corto.
- Se elimina `_apply_layout()` de la ruta crítica del clic y Matplotlib se refluye 24 ms después del commit.
- Se usa un único HWND raíz para WM_SETREDRAW, evitando el frame fantasma/duplicado observado en V308.
- Se soporta un segundo clic rápido mediante cola de estado, sin reentrancia de geometría.

## V308
- Base estable V306; se descarta el slide geométrico de V307 porque reintroducía estados intermedios visibles.
- Sidebar: transición atómica más rápida usando WM_SETREDRAW sin mover el sidebar real con place().
- Se elimina el canvas.draw() síncrono del gesto de abrir/cerrar; Matplotlib se redibuja con draw_idle después del commit final.
- El layout deja de forzarse completo durante el toggle y usa el fast-path cuando el breakpoint no cambia.
- Se conserva Windows-only, multi-Python, frecuencia CPU universal y REAL_OR_NA.

## V306
- Base V305.
- Sidebar: se elimina la transición por captura/snapshot y cualquier efecto visual artificial al abrir/cerrar.
- El cambio de geometría ahora se realiza con suspensión nativa de repintado de Windows (WM_SETREDRAW) y un único repintado final.
- El objetivo es evitar que Tk/CustomTkinter/Matplotlib expongan estados intermedios de tarjetas, separadores y gráficos durante el reflow.
- Sin cambios en telemetría, REAL_OR_NA, Gaming, Benchmark o diagnóstico.

## V305
- Base V304 Windows-only.
- Sidebar: transición atómica basada en un fotograma real de la ventana.
- Se elimina del flujo activo la máscara de borde, la estela y el reflow visible por etapas.
- Tk/CustomTkinter y Matplotlib terminan de acomodarse detrás del fotograma congelado y el estado final se publica de una sola vez.
- Sin cambios en telemetría, diagnóstico ni política REAL_OR_NA.

## V304
- Base V303.
- Contrato de plataforma consolidado: CorePulse queda exclusivamente orientado a Windows 10/11 x64.
- Eliminados backends, rutas de apertura, bindings y archivos alternativos de otros sistemas operativos.
- Runtime multi-Python se mantiene para CPython 3.12+ x64 dentro de Windows, con validación completa del stack.
- Sin cambios en REAL_OR_NA, REAL_FPS_OR_NA_ONLY, telemetría, benchmark ni diagnóstico.

## V303
- Base V302.
- Sidebar: se reemplaza la máscara/wipe de pantalla completa por una micro-transición localizada de borde.
- El dashboard permanece visible durante todo el abrir/cerrar del sidebar.
- Settle reducido y redraw único para disminuir parpadeos sin una cortina invasiva.

## V302
- Base V301.
- Sidebar: nueva transición de máscara/wipe para ocultar el reflow visual al abrir/cerrar el lateral.
- Durante el cambio de geometría se congela visualmente el contenido, se estabilizan los gráficos y luego se revela el dashboard con una cortina breve desde el borde izquierdo.
- No reconstruye el sidebar y no modifica telemetría, gráficos ni datos; sólo controla el ruido visual de renderizado.

## V301
- Base V300.
- Resumen: se aumenta la separación superior de la tarjeta de gráficos (CPU/RAM/GPU) para que quede visualmente más abajo respecto al bloque de almacenamiento.
- Ajuste puramente visual; no modifica telemetría ni lógica de gráficos.

## V300
- Base V299; conserva el fix universal de frecuencia CPU y el runtime multi-Python.
- Sidebar: Personalización deja de anclarse al borde inferior por entrar en modo compacto.
- El bloque Temas / Actualizaciones / versión permanece inmediatamente después de Historial en cualquier ancho o DPI.
- En alturas realmente bajas (<690 px) solo se compactan alturas/paddings; no se crea un hueco artificial.

## V299
- Base V298.
- Frecuencia CPU universal: mantiene LibreHardwareMonitor como fuente prioritaria y agrega fallbacks reales/trazables para equipos que no exponen sensores Clock.
- Fallback 1: `psutil.cpu_freq().current`.
- Fallback 2: `Win32_PerfFormattedData_Counters_ProcessorInformation` usando `ProcessorFrequency` y `PercentProcessorPerformance` reales del sistema.
- Fallback 3: `Win32_Processor.CurrentClockSpeed`.
- La capa certificada conserva fuente, sensor, timestamp y bandera `derived_from_real`; no inventa ni aplica offsets.
- Mantiene `REAL_OR_NA` y devuelve N/A si ninguna fuente real entrega frecuencia.

## V298
- Base V297.
- Corrige el arranque directo con un Python 3.12+ que no tenga `customtkinter` u otras dependencias instaladas.
- `main.py` y `corepulse_launcher.py` ahora aprovisionan automáticamente un venv aislado para el mismo minor de Python antes de importar la GUI.
- El bootstrap intenta primero el lock reproducible y luego una resolución adaptable; sólo registra el runtime si pasa la validación completa de Windows.
- Se elimina el fallo inmediato `ModuleNotFoundError: customtkinter` como ruta normal de primer arranque.

## V297
- Base V296.
- Runtime fuente multi-Python: CorePulse ya no exige exactamente Python 3.12; acepta CPython 3.12+ x64 sin límite menor artificial.
- `instalar_dependencias.bat` detecta automáticamente el Python disponible (incluido 3.13/3.14), crea un runtime aislado por versión y valida el stack completo antes de declararlo compatible.
- Se mantiene un lock reproducible como primer intento y se agrega una resolución flexible compatible para versiones nuevas de Python cuando un wheel exacto no exista.
- `main.py` y `corepulse_launcher.py` pueden redirigirse al runtime validado si se ejecutan desde otro Python sin dependencias.
- `build_exe.bat` deja de exigir Python 3.12 exacto y usa el runtime validado 3.12+ x64.
- La compatibilidad nunca se finge: si pythonnet / pywin32 / HardwareMonitor / LibreHardwareMonitor no cargan, la instalación falla y esa combinación de Python no se declara equivalente.

## V296
- Base V295.
- Gaming Inicio: corrección real del bloque de recursos para que CPU/GPU/RAM queden como una fila baja de tarjetas rectangulares, no columnas altas.
- Se reduce el ancho reservado a recursos y se da más aire al recuadro principal del juego actual.
- Ajuste fino del bloque derecho para mantenerlo horizontal y legible.

## V295
- Base V294.
- Gaming Inicio: corrección de altura de las tres tarjetas CPU/GPU/RAM para evitar que se extiendan demasiado hacia abajo.
- Se mantiene el recuadro del juego actual como bloque horizontal principal, con su composición intacta.
- Ajustes finos de padding y proporción para que el conjunto quede más balanceado.

## V294
- Base V293.
- Corregido el layout de CPU/GPU/RAM en Gaming: dejan de estirarse horizontalmente.
- Las tres tarjetas pasan a tamaño fijo rectangular y recuperan una distribución equilibrada con el bloque del juego actual.
- Se reemplaza el acento superior por un acento lateral más coherente con el lenguaje visual del Resumen.
- Sin cambios en telemetría real, Game Boost ni REAL_OR_NA / REAL_FPS_OR_NA_ONLY.

## V293
- Base V292.
- Gaming Inicio: corrección visual de las tres tarjetas de recursos (CPU/GPU/RAM).
- Las tarjetas quedan con proporción rectangular más clara, mejor jerarquía de texto y mejor alineación interna.
- Se mejora el ancho útil y la distribución del bloque de recursos sin tocar la lógica real de telemetría.

## V292
- Base V291.
- Corregido error al abrir Gaming: `transparency is not allowed for this attribute`.
- La flecha de retorno del header deja de usar un CTkButton con `border_color='transparent'`; ahora es un glifo CTkLabel clickeable sin cuadro de fondo.
- Se mantiene el icono Gaming sin cuadro, las tarjetas rectangulares CPU/GPU/RAM y el resto del diseño de V291.
- Sin cambios en telemetría real, benchmark ni contratos REAL_OR_NA / REAL_FPS_OR_NA_ONLY.

## V291
- Base V290.
- Cabecera Gaming: se eliminan los cuadros de fondo que sostenían la flecha de retorno y el icono de gaming; quedan solo los iconos.
- Inicio Gaming: se corrigen las tarjetas CPU/GPU/RAM, que ahora son rectangulares de forma consistente y con mejor ajuste visual.
- Juego actual: se ajusta el tamaño del título cuando no hay juego activo para evitar cortes y desbordes.
- Sin cambios en telemetría real, benchmark ni contratos REAL_OR_NA / REAL_FPS_OR_NA_ONLY.

## V290
- Base V289.
- Gaming Inicio: tarjeta GAME BOOST ampliada para mejorar lectura y presencia visual.
- Se corrigen los problemas visuales de las tarjetas CPU/GPU/RAM aumentando tamaño, área útil y ajuste de texto.
- El bloque del juego actual se amplía con carátula más grande y jerarquía visual más clara.
- Sin cambios en telemetría real, benchmark ni contratos REAL_OR_NA / REAL_FPS_OR_NA_ONLY.

## V289
- Base V288.
- Gaming Inicio: recursos CPU/GPU/RAM rediseñados como tarjetas cuadradas inspiradas en el lenguaje visual del Resumen.
- Bloque de juego actual ahora muestra carátula/artwork real del juego detectado junto a su nombre, manteniendo REAL_FPS_OR_NA_ONLY.
- Tarjeta de Perfil de rendimiento recortada verticalmente para mejorar el balance visual de la portada Gaming.
- Sin cambios en telemetría real, benchmark ni contratos REAL_OR_NA.

## V288
- Base V287.
- Game Boost absorbe la información útil de la antigua tarjeta de sesión.
- Nuevo layout: métricas CPU/GPU/RAM a la izquierda, Game Boost al centro y juego actual en una tarjeta principal.
- Se elimina el botón grande Configurar del extremo derecho; el acceso a ajustes queda como control discreto junto al título.
- FPS permanece REAL_FPS_OR_NA_ONLY y se muestra sólo dentro del bloque del juego cuando existe evidencia real.
- Sin cambios en la lógica del Game Boost, telemetría, perfiles o benchmark.

## V287
- Base V286.
- Eliminada únicamente la tarjeta superior de Sesión de juego en Gaming (juego detectado, FPS/CPU/GPU/RAM y accesos rápidos asociados).
- Se conserva intacto Perfil de rendimiento, Game Boost, cabecera Gaming, navegación y Benchmark.

## V286
- Base V285.
- Cabecera de Gaming aún más compacta.
- Eliminado el subtítulo gris bajo el título "Gaming".
- Reducida la altura del recuadro superior para una presencia más limpia y ajustada.
- Conserva flecha izquierda, icono de gaming a la derecha y el resto del layout aprobado.

## V285
- Base V284.
- Cabecera de Gaming recortada verticalmente para eliminar el espacio vacío inferior.
- Se añade icono de Gaming en la esquina superior derecha del recuadro, manteniendo la flecha profesional a la izquierda.
- Se conserva intacto el resto del layout aprobado: Inicio, Sesión de juego, Perfil de rendimiento y mejoras de Benchmark.

## V284
- Base V283.
- Corregida la distribución de la cabecera de Gaming según la revisión visual.
- Eliminada la tarjeta de estado superior derecha que sobrecargaba la cabecera.
- El bloque superior de Gaming ahora usa geometría cuadrada, flecha de retorno a la izquierda y título centrado.
- Se conservan sin cambios las tarjetas de Sesión de juego y Perfil de rendimiento aprobadas visualmente.
- Se mantienen las mejoras de Benchmark de V283 y no cambia la lógica REAL_OR_NA / REAL_FPS_OR_NA_ONLY.

## V283
- Base V282.
- Pulido de la cabecera de Gaming: botón de retorno minimalista con flecha y tarjeta superior de estado en formato cuadrado.
- Game Boost en Inicio queda más compacto, manteniendo la misma identidad visual.
- Benchmark recibe un rediseño visual más coherente con el lenguaje actual de CorePulse: cabecera profesional, tarjeta de estado, navegación y estado de carga más cuidados.
- Sin cambios en telemetría real, benchmark real ni contratos REAL_OR_NA / REAL_FPS_OR_NA_ONLY.

## V282
- Base V280; V281 descartada por interpretación visual demasiado literal del Resumen.
- Gaming conserva su propia estructura y adopta sólo el lenguaje visual del dashboard: superficies, bordes, radios, jerarquía tipográfica, acentos laterales y estados activos.
- Pulido de cabecera, navegación, sesión de juego, métricas, perfiles y Game Boost sin clonar la composición del Resumen.
- Sin cambios en telemetría real, diagnóstico, benchmark, SMART ni contratos REAL_OR_NA / REAL_FPS_OR_NA_ONLY.

## V280
- Base V279.
- Corregido el cierre/apertura del sidebar para reutilizar el árbol ya construido en lugar de destruirlo y reconstruirlo al reabrir.
- Eliminada la resincronización forzada de todo el dashboard en cada toggle; el cambio de visibilidad queda limitado a la geometría mínima necesaria.
- Se conserva la X por hover de V279 y las mejoras de navegación/Benchmark de V279.
- Sin cambios en telemetría, sensores, SMART, diagnóstico, benchmark real ni contratos REAL_OR_NA / REAL_FPS_OR_NA_ONLY.

## V279
- Base V277 (V278 descartada).
- Estabilizado el hover de la X del sidebar: la geometría del control queda fija y sólo cambia su contenido visible; se elimina el bind recursivo sobre todos los widgets hijos.
- Añadido debounce de salida del sidebar para evitar parpadeos al cruzar botones, iconos, labels y separadores.
- Navegación a Benchmark publicada en dos fases: pre-mapeo oculto detrás de la vista actual + commit en el siguiente frame.
- El contenido pesado del Benchmark se construye en un staging host fuera del viewport y se intercambia cuando ya está listo, conservando el estado de carga hasta entonces.
- Sin cambios en telemetría, sensores, benchmark real, SMART, diagnóstico ni contratos REAL_OR_NA / REAL_FPS_OR_NA_ONLY.

## V277
- Base V276.
- Reacomodado el bloque superior del sidebar.
- La X de cierre deja de quedar fija a la izquierda: ahora aparece arriba a la derecha solo cuando el mouse entra al sidebar.
- Ajustado el espaciado superior para que la cabecera del sidebar quede limpia y mejor alineada.
- Sin cambios funcionales en navegación, telemetría, diagnóstico, benchmark, SMART o REAL_OR_NA.

## V276
- Base V275.
- Corregido el criterio que empujaba Personalización al fondo del sidebar en alturas normales.
- El bloque Personalización solo se ancla abajo en ventanas realmente bajas; en tamaños normales queda inmediatamente después de Historial.
- Sin cambios funcionales en navegación, telemetría, diagnóstico, benchmark, SMART o REAL_OR_NA.

## V275
- Base V274.
- Corregida la composición visual de la parte baja del sidebar.
- Personalización deja de quedar flotando en ventanas con alto normal: ahora fluye justo después de Historial y solo se ancla abajo en layouts realmente ajustados.
- Ajustados márgenes del bloque inferior y de la versión para un cierre más limpio.
- Sin cambios funcionales en navegación, telemetría, diagnóstico, benchmark, SMART o REAL_OR_NA.

## V274
- Base V273.
- Ajustado el borde inferior del sidebar para que quede anclado al borde real inferior del panel, sin verse desplazado ni hacia adentro.
- Reducido levemente el margen inferior del bloque Personalización para que el cierre visual inferior del sidebar se vea limpio y continuo.
- Sin cambios funcionales en navegación, telemetría, diagnóstico, benchmark, SMART o REAL_OR_NA.

## V273
- Base V272.
- Corregido el borde del sidebar: los cuatro lados ya no quedan 8 px hacia adentro; ahora siguen el perímetro real del panel.
- Se conserva el borde estructural neutro y los separadores internos neutros de V272.
- Sin cambios funcionales en navegación, telemetría, diagnóstico, benchmark, SMART o REAL_OR_NA.

## V272
- Base V271.
- Borde exterior del sidebar reconstruido con cuatro líneas nativas de 2 px para mejorar definición y continuidad visual.
- Separadores internos cambiados de celeste a borde estructural neutro del tema.
- Sin cambios funcionales en navegación, telemetría, diagnóstico, benchmark, SMART o REAL_OR_NA.

## V271
- Base V269.
- Borde exterior corregido sin cambiar el fondo del sidebar.
- Separadores horizontales en celeste CorePulse.

## V268
- Igualado el ancho visual de Supervisión actual con Salud del sistema.

## V267
- Borde exterior del sidebar reforzado para que el rectángulo sea claramente visible.

## V266
- Borde del sidebar continuo.
- Separadores horizontales visibles.
- Actualizaciones permanece visible.

## V265
- Reparación visual del borde del sidebar y divisores horizontales.
- Se conserva Actualizaciones visible en el footer.

## V264
- Restaurados separadores horizontales visibles del sidebar.
- Corregido el recorte de Actualizaciones en Personalización.
- Ajustado espaciado vertical sin alterar navegación ni lógica funcional.

## V263
- Sidebar completo convertido en panel rectangular integrado.
- Sin cuadro interno: todos los controles siguen siendo hijos del sidebar original.
- Añadidos borde exterior y separadores visuales.
- Basado en V259 para evitar regresiones de V260/V262.

## V259
- Tarjeta de inicio con bordes cuadrados.
- Se elimina el porcentaje del splash; queda sólo la barra de progreso real.

# CorePulse Changelog — rama actual

## V257
- Limpieza estructural del proyecto sobre V256.
- Eliminados `__pycache__`, `.pyc`, `.pytest_cache`, logs/resultados vacíos y documentación de validaciones históricas.
- Eliminados runners GPU versionados antiguos de `tools/` y raíz.
- Eliminado bootstrap fuente obsoleto y helpers físicos no usados por el runtime actual.
- Eliminado `core/visual_benchmark.py`, sin imports desde la ruta vigente DirectX.
- Conservados código funcional, assets, PresentMon, build/installer y contratos REAL_OR_NA.

## V256
- Eliminación de textos secundarios marcados por el usuario.

## V255
- Corrección de `padx` inválido en CTkButton.

## V254
- Refinamiento visual del sidebar.

## V253
- Paridad de posición del control de sidebar.

## V252
- Controles de sidebar con iconos simples.
