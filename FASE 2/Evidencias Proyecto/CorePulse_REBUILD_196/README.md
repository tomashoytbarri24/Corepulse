# CorePulse REBUILD 196 — Diagnóstico real de fullscreen y detección sin bordes

Basada en REBUILD 195. La IA, Speedtest y los archivos binarios nativos permanecen sin modificaciones.

### Correcciones
- La detección de pantalla completa comprueba rectángulo Win32, borde visible DWM y área de cliente. En Windows 11 los bordes de redimensionamiento invisibles pueden impedir que una ventana sin bordes se identifique como fullscreen si solo se compara `GetWindowRect`.
- La pantalla Overlay informa por separado del render interno y del estado Win32 del host (`ventana no creada`, `visible según Windows`, `oculto según Windows` o error). **Esto no verifica que el usuario lo vea encima del juego**.
- El diagnóstico copiable incluye modo de render, estado del host, pantalla completa y registro de atajos para identificar la causa de fallos reales.
- Los juegos conocidos con antitrampas muestran el módulo interno como bloqueado sin ofrecer un botón de permiso operativo; no se evita ni sortea ninguna protección.

### Prueba real requerida (Windows)
1. Cerrar por completo CorePulse de versiones anteriores y abrir REBUILD 196.
2. Probar primero un juego en ventana. Activar overlay con `Ctrl+Shift+O` y panel con `Shift+F2`.
3. Cambiar **el mismo juego** a `Pantalla completa sin bordes` y repetir. Si falla, volver a CorePulse → Overlay → Estado → **Copiar diagnóstico**, pegar el texto para distinguir objetivo no detectado / host oculto / exclusividad.
4. Si usas *pantalla completa exclusiva*, el host externo puede quedar detrás del juego por el modo de presentación. No hay garantía para ese modo. No activar módulos inyectados en juegos con antitrampas (PUBG, ARC Raiders, etc.).

### Limitaciones
- No se modificaron ni recompilaron los módulos internos D3D/OpenGL ni el binario `CorePulseOverlayHost.exe`.
- No se garantiza que funcione en exclusiva, juegos con anticheat ni modos de presentación DirectFlip que oculten overlays externos.
- Se verificó sintaxis Python y lógica de geometría con pruebas aisladas. La validación visual Windows y las pruebas Qt necesitan realizarse en un PC con Windows.

---

# CorePulse REBUILD 195 — Overlay y panel rápido en pantalla completa (transiciones y respaldo)

Basada en REBUILD 194. No cambia CorePulse AI, la nube, Speedtest ni las funciones de Tweaks.

### Qué se corrigió
- El host externo **no desaparece mientras un módulo gráfico está cargando**. Solo cede el dibujado cuando el hook autorizado confirma fotogramas reales. El panel rápido usa la misma selección para evitar panel duplicado.
- Estado claro en la pestaña Overlay sobre qué modo se utiliza y si la pantalla completa exclusiva podría ocultar la ventana externa.
- ARC Raiders (`PioneerGame.exe`) se añade a la lista de bloqueo explícito del módulo interno, incluso si la protección no aparece todavía en la memoria del proceso.
- Se conservan los atajos globales y la activación explícita por juego **solo para juegos sin antitrampas**.

### Limitaciones que siguen existiendo
- **Ventana/sin bordes:** usa el overlay externo y panel rápido nativos sin modificar el juego. La presentación de algunas combinaciones DirectFlip/Windows puede ocultar una ventana superpuesta.
- **Exclusivo real:** necesita presentación en la superficie gráfica del juego o una vía aprobada oficialmente. CorePulse ya tiene módulos D3D9/10/11/12/OpenGL, pero solo se intentan con permiso explícito y jamás en juegos identificados como protegidos. Vulkan no está implementado.
- No se garantiza compatibilidad con juegos en línea, fullscreen optimizations, ni anticheats. La prueba visual de esta versión en Windows está pendiente.
- Para juegos como PUBG y ARC Raiders se recomienda pantalla completa **sin bordes** y no activar la DLL interna.

# CorePulse REBUILD 194 — Chat de IA directo y panel de privacidad discreto

Rama basada en REBUILD 191 (a su vez derivada de REBUILD 189). **No incorpora la rama REBUILD 190 de Tweaks**, que permanece pausada.

## Ámbito de CorePulse AI

- **Permitido:** funciones de CorePulse; preguntas sobre componentes (CPU, GPU, RAM, VRAM, SSD, temperaturas, ventiladores, periféricos, etc.); lectura de datos REAL_OR_NA; diagnóstico, fallos, rendimiento, drivers, Windows y juegos **cuando afecten al funcionamiento del computador**. No es necesario mencionar «CorePulse» para consultar por hardware.
- **Fuera de ámbito:** enseñanza general de Java o programación, matemática escolar, cultura general, recetas, animales, preguntas de actualidad, guías para ganar niveles y otras consultas no relacionadas con el equipo.
- **Seguimientos breves:** preguntas como «¿y cómo lo arreglo?» siguen disponibles; la política del modelo exige responderlas en el contexto técnico de la conversación.
- **Dos filtros:** el cliente Python y el Worker de la nube rechazan localmente solicitudes claramente ajenas **antes de enviar telemetría o gastar cuota del modelo**. La política de sistema define el ámbito también para casos ambiguos. No es una clasificación semántica infalible.
- **Sin cambios:** motor RAG, REAL_OR_NA, consentimiento, cuotas, modelos, diagnósticos, Speedtest Ookla, juegos y overlay.

## Comprobaciones

- `pytest -q tests/test_rebuild.py -k rebuild_192_ai_scope`
- `cd cloud/corepulse-ai && npm run verify`

## Activación de la política cloud

El código fuente actualizado del Worker está incluido, pero **no se ha publicado en `ai.corepulse.cl`**. Para aplicarlo en el servicio público, verificar los cambios y desplegar el Worker existente utilizando las instrucciones de `cloud/corepulse-ai/README.md`. No crear un Worker nuevo, alterar el DNS o regenerar los secretos.

---

# CorePulse REBUILD 191 — Restricciones CorePulse AI

Base funcional: REBUILD 189, con Speedtest Ookla integrado y demás módulos conservados. La rama REBUILD 190 (Tweaks estilo WinUtil) queda pausada: **no se mezcló aquí**.

## Novedad

CorePulse AI queda limitado a preguntas relacionadas con el computador y las funciones de CorePulse. Se rechazan localmente solicitudes evidentemente ajenas al programa (por ejemplo: «Dame una clase de Java», «¿Cuánto es 1+1?», «¿Qué animal es un gato?»). El rechazo no hace una consulta a Groq ni transmite telemetría. La API cloud aplica la misma barrera antes de consumir presupuesto, y tiene una política de sistema de dominio exclusivo para casos abiertos.

Preguntas válidas: CPU/GPU/RAM/SSD, temperaturas, ventiladores, Windows, controladores, errores, juegos/FPS, Internet/red, Speedtest, Tweaks, rendimiento, diagnósticos y el funcionamiento de CorePulse. «¿Por qué java.exe consume RAM en Windows?» se considera una pregunta técnica, no una clase de Java.

Esta restricción tiene comprobaciones deterministas para casos claros y una instrucción de ámbito para los demás. No constituye un clasificador infalible de cualquier frase o una garantía de que un LLM nunca se desvíe. REAL_OR_NA y el consentimiento se conservan.

## Pruebas

- `pytest -q tests/test_rebuild.py -k rebuild_191_ai_scope`
- `cd cloud/corepulse-ai && npm run verify`

La máquina utilizada no tiene PySide6; la interfaz real en Windows queda pendiente.

## Servicio Cloud (requiere despliegue separado)

Esta distribución incluye **código fuente** del Worker actualizado, pero no se hizo un despliegue a `ai.corepulse.cl`. Para aplicar la barrera de servidor a clientes instalados con anterioridad, seguir el instructivo `cloud/corepulse-ai/README.md` y desplegar el Worker **en la cuenta ya existente**, sin crear uno nuevo ni regenerar secretos. En la nueva versión de Windows, la barrera local ya rechaza los casos explícitos.

---

# CorePulse REBUILD 188

Proyecto completo para Windows 10/11 x64. Se construye directamente sobre
REBUILD 187 y conserva los íconos de juegos, mejoras anteriores, telemetría,
benchmark, overlay, historial, diagnósticos y mantenimiento.

## REBUILD 188 · Arco sincronizado y diseño integrado (07-11-2026)

- El arco de color ya no se pinta completo al recibir la primera muestra: su
  extensión se calcula con la **misma velocidad suavizada** y función de escala
  que la aguja. La punta de la aguja y el final del arco coinciden durante
  la descarga y la subida. La cifra central usa esa misma velocidad visual,
  mientras las tarjetas superiores muestran las lecturas recibidas de Ookla.
- Se eliminaron por completo los **dos discos circulares decorativos** que
  oscurecían el fondo. El Speedtest utiliza el `GlassPanel` compartido,
  translúcido y vinculado al tema de CorePulse. La pista de la aguja queda
  atenuada para no competir con el arco activo.
- Se separaron los estados visuales: INICIO central, medidor durante la prueba
  y resultado final centrado en una fila espaciosa con botón para repetir,
  descarga/subida grandes y métricas de ping/jitter/pérdida.
- Se mantienen las transiciones suaves, animación de conexión sin Mbps falsos,
  consentimiento expreso, el motor oficial Ookla JSONL y ausencia de Cloudflare.
- No se modificaron `core/maintenance/speed_test.py`, archivos nativos, overlay,
  telemetría ni lógica de juegos. Cambios de producción: `ui/NetworkPage.qml` y
  `ui/Main.qml` (etiqueta de versión). Pruebas enfocadas: 10 PASS; comprobación
  de balance QML y sintaxis Python: PASS. La prueba visual real debe hacerse
  en Windows.

## Corrección de diseño · Speedtest tipo Ookla dentro de CorePulse

En **Mantenimiento → Red avanzada**, la prueba usa exclusivamente la
**Speedtest CLI oficial de Ookla** y muestra el resultado *dentro de la app*.

- REBUILD 187: integra el velocímetro en el fondo de cristal de CorePulse sin la placa gris interior; colores vinculados al tema activo, halo discreto, entrada gradual del arco, aguja de inercia con las tasas reales JSONL, pulso de conexión sin Mbps ficticios, transición cromática entre descarga/subida, microanimación de INICIO y aparición suave del resumen. Sin modificar la fuente ni el cálculo de las mediciones.
- REBUILD 186: reemplaza el GridLayout que comprimía el dial por un panel central responsivo de ancho reservado. En reposo aparece un círculo INICIO; durante la prueba aparece un velocímetro grande y centrado, con arco turquesa/verde en descarga y violeta/rosa en subida; al terminar se ven los resultados y se puede repetir. Solo se anima con muestras JSONL reales.
- El velocímetro cambia automáticamente de descarga a subida; muestra ping y jitter en vivo cuando la CLI los entrega.
- Medidores de descarga, subida, ping y jitter arriba del velocímetro, más pérdida de paquetes al finalizar (N/A cuando Ookla no proporciona el dato).
- La aguja (520 ms) y el arco utilizan el mismo valor interpolado para sincronizar posición y extensión; sin velocidades ficticias ni tasas inferidas a partir del reloj.
- Nombre real del servidor cuando Ookla lo comunica; de otro modo se indica selección automática o no informado, nunca se inventa un servidor.
- Se eliminó Cloudflare como proveedor y motor del módulo, y se quitó la
  redirección automática a la página de resultados.
- La prueba nunca comienza sin pulsar Iniciar y aceptar los términos de Ookla.

## Instalar y probar

1. Cierra CorePulse, incluso desde la bandeja, antes de abrir la nueva versión.
2. Abre **Iniciar_CorePulse.bat** o ejecuta `python main.py` con Python 3.12+
   de 64 bits en Windows; el arranque prepara sus dependencias.
3. En **Red avanzada → Speedtest**, si el motor aún no está instalado,
   utiliza **Preparar Ookla** y verifica conexión a Internet.
4. Pulsa el círculo **INICIO**, revisa los enlaces de condiciones, confirma tu
   aceptación y comienza. El velocímetro se mueve durante descarga y subida y los resultados aparecen en el mismo panel.
5. Para una nueva medición, pulsa **INICIO** otra vez al finalizar.

La CLI oficial no se incluye en el ZIP. El proyecto conserva su preparación
local, con comprobación de procedencia y hash SHA-256. Ookla aplica términos de
licencia y uso propios; revisarlos antes de distribuir la app comercialmente.

Las mediciones son reales. La CLI oficial admite el formato `jsonl`, con
fases de ping/descarga/subida y valores parciales. CorePulse los recibe en un
subproceso oculto, actualiza la interfaz a medida que llegan y conserva el
evento final como resultado oficial. Cuando un evento no contiene tasa o
latencia, la interfaz muestra N/A en vez de inventarla. Las cifras finales
pueden diferir de los valores parciales de la prueba. El proceso tiene un
límite de tiempo de 150 segundos y no abre ninguna página de resultados.

Esta integración adapta la **composición visual y el comportamiento principal** del test web, no
incrusta la página ni copia la interfaz oficial píxel por píxel. Ookla exige
aceptación de sus términos y su CLI tiene condiciones de uso propias.

## Conservación y validación

- Base: REBUILD 187, acumulando funcionalidades de 182/183/184/185/186/187. Sin cambios a DLL/EXE nativos ni a motores de juegos.
- Archivos de producción modificados en REBUILD 188: `ui/NetworkPage.qml`, `ui/Main.qml`. El motor `core/maintenance/speed_test.py` se conserva de la 185 sin cambios. No se incorporan dependencias nuevas.
- Pruebas focalizadas de streaming y contratos QML en `tests/test_speedtest_live.py`.
- No se pudo ejecutar un Speedtest real ni cargar el QML en Windows desde el
  entorno de generación (carece de Windows y PySide6). Debe verificarse en el
  equipo de destino. Las pruebas históricas de otras interfaces incluyen
  expectativas desactualizadas y no se declaran aprobadas.

El historial de sesiones sigue en `%LOCALAPPDATA%\CorePulse\rebuild` y no se
elimina. Las reglas se conservan en `Reglas para crear Versiones nuevas.txt`.
Consulta `versiones/HISTORIAL.md` para el historial general.


## REBUILD 194 — CorePulse AI sin casillas en la vista

- Se elimina de la vista principal el panel de tres casillas y el botón **Ajustes**. El chat ocupa el espacio liberado y abre listo para preguntar.
- En cuentas nuevas, las preferencias de contexto técnico e historial resumido comienzan habilitadas; un rechazo anterior de cualquier cuenta se conserva y no se sobreescribe.
- El enlace **Privacidad** del pie permite cambiar esas preferencias en una ventana discreta (sin pedir confirmaciones para cada consulta).
- No se transmiten preguntas, sensores ni Tendencias solo por abrir CorePulse. La pregunta se envía únicamente al pulsar **Enviar**; Tendencias se incluye solo en preguntas relacionadas con sesiones.
- La IA no hace cambios en Windows, el Worker de cloud no cambia y no necesita otro despliegue.
