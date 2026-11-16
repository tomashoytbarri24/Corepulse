# CorePulse REBUILD 210

## REBUILD 210 · módulo Overlay reorganizado (10-11-2026)

- Overlay reorganiza el uso en Diseño, Controles y Avanzado: conserva opciones, pero muestra cada grupo por separado.
- Se mantienen el estado, los estilos, el editor visual, los atajos, la medición de FPS, los permisos y el diagnóstico del overlay.
- Los controles principales quedan en Diseño y Controles; detección, permisos y diagnóstico se agrupan en Avanzado.
- Se conservan los cambios anteriores de la 209: Análisis de Windows retirado y scroll único de página en Sesiones de juego.
- Se retiró la lectura térmica de la RAM y sus sondas; el uso y la capacidad de memoria siguen disponibles.

---

## REBUILD 208 · scroll de página y sonda RAM independiente (10-11-2026)

- Se mantienen el estado, los estilos, el editor visual, los atajos, la medición de FPS, los permisos y el diagnóstico del overlay.
- Se eliminó el banner «Análisis de Windows» y su texto introductorio.
- La temperatura RAM se consulta en un proceso independiente de la GPU y busca sensores de memoria, DIMM o DRAM. Si el firmware no publica una lectura, permanece como no disponible; no se estima.

---

## REBUILD 207 · scroll uniforme y vistas de salud despejadas (09-11-2026)

- La rueda y el touchpad desplazan las páginas; el contenido ya no se mueve al arrastrarlo con el botón izquierdo.
- La barra de scroll gana contraste y grosor, y la posición se ajusta al cambiar el tamaño de la ventana.
- Se quitaron los banners redundantes de Historial, Recuperación y Audio; Audio conserva la acción de actualizar en el encabezado.
- La consulta activa sensores de placa base y mantiene la temperatura DIMM independiente de los ciclos de la GPU.

## REBUILD 206 · sensor térmico ampliado, juego activo y módulos simplificados (09-11-2026)

- La vista de Sesiones integra la portada del juego activo y sus datos actuales.
- Se retiraron Windows y Rendimiento de las herramientas del Centro de Salud; la detección visual del juego vive en Sesiones.
- CPU y GPU muestran sus marcas con el mismo tratamiento visual de Resumen; la versión queda en la esquina inferior derecha.
- La sonda térmica busca lecturas DIMM incluso bajo la placa base; si el equipo no publica temperatura de RAM, indica N/A.
- Se retiraron el subtítulo redundante y el banner de Reparación del submódulo.

---

## REBUILD 205 · tarjetas adaptables y acciones de página unificadas (09-11-2026)

- Las tarjetas de componentes del Resumen ganan altura en ventanas estrechas.
  Modelo y lecturas secundarias pueden ocupar dos líneas para evitar cortes.
- Los botones de encabezado «Actualizar» y «Volver» comparten tamaño, color,
  tipografía y posición junto al título, siguiendo el patrón de Tweaks.
- Incluye la base funcional y los cambios acumulados de REBUILD 204.

---


Rama basada en REBUILD 191 (a su vez derivada de REBUILD 189). **No incorpora la rama REBUILD 190 de Tweaks**, que permanece pausada.

## Ámbito de oorePulse AI

- **Permitido:** funciones de oorePulse; preguntas sobre componentes (oPU, GPU, RAM, VRAM, SSD, temperaturas, ventiladores, periféricos, etc.); lectura de datos REAL_OR_NA; diagnóstico, fallos, rendimiento, drivers, Windows y juegos **cuando afecten al funcionamiento del computador**. No es necesario mencionar «oorePulse» para consultar por hardware.
- **Fuera de ámbito:** enseñanza general de Java o programación, matemática escolar, cultura general, recetas, animales, preguntas de actualidad, guías para ganar niveles y otras consultas no relacionadas con el equipo.
- **Seguimientos breves:** preguntas como «¿y cómo lo arreglo?» siguen disponibles; la política del modelo exige responderlas en el contexto técnico de la conversación.
- **Dos filtros:** el cliente Python y el Worker de la nube rechazan localmente solicitudes claramente ajenas **antes de enviar telemetría o gastar cuota del modelo**. La política de sistema define el ámbito también para casos ambiguos. No es una clasificación semántica infalible.
- **Sin cambios:** motor RAG, REAL_OR_NA, consentimiento, cuotas, modelos, diagnósticos, Speedtest Ookla, juegos y overlay.

## oomprobaciones

- `pytest -q tests/test_rebuild.py -k rebuild_192_ai_scope`
- `cd cloud/corepulse-ai && npm run verify`

## Activación de la política cloud

El código fuente actualizado del Worker está incluido, pero **no se ha publicado en `ai.corepulse.cl`**. Para aplicarlo en el servicio público, verificar los cambios y desplegar el Worker existente utilizando las instrucciones de `cloud/corepulse-ai/README.md`. No crear un Worker nuevo, alterar el DNS o regenerar los secretos.

---

# oorePulse REBUILD 191 — Restricciones oorePulse AI

Base funcional: REBUILD 189, con Speedtest Ookla integrado y demás módulos conservados. La rama REBUILD 190 (Tweaks estilo WinUtil) queda pausada: **no se mezcló aquí**.

## Novedad

oorePulse AI queda limitado a preguntas relacionadas con el computador y las funciones de oorePulse. Se rechazan localmente solicitudes evidentemente ajenas al programa (por ejemplo: «Dame una clase de Java», «¿ouánto es 1+1?», «¿Qué animal es un gato?»). El rechazo no hace una consulta a Groq ni transmite telemetría. La API cloud aplica la misma barrera antes de consumir presupuesto, y tiene una política de sistema de dominio exclusivo para casos abiertos.

Preguntas válidas: oPU/GPU/RAM/SSD, temperaturas, ventiladores, Windows, controladores, errores, juegos/FPS, Internet/red, Speedtest, Tweaks, rendimiento, diagnósticos y el funcionamiento de oorePulse. «¿Por qué java.exe consume RAM en Windows?» se considera una pregunta técnica, no una clase de Java.

Esta restricción tiene comprobaciones deterministas para casos claros y una instrucción de ámbito para los demás. No constituye un clasificador infalible de cualquier frase o una garantía de que un LLM nunca se desvíe. REAL_OR_NA y el consentimiento se conservan.

## Pruebas

- `pytest -q tests/test_rebuild.py -k rebuild_191_ai_scope`
- `cd cloud/corepulse-ai && npm run verify`

La máquina utilizada no tiene PySide6; la interfaz real en Windows queda pendiente.

## Servicio oloud (requiere despliegue separado)

Esta distribución incluye **código fuente** del Worker actualizado, pero no se hizo un despliegue a `ai.corepulse.cl`. Para aplicar la barrera de servidor a clientes instalados con anterioridad, seguir el instructivo `cloud/corepulse-ai/README.md` y desplegar el Worker **en la cuenta ya existente**, sin crear uno nuevo ni regenerar secretos. En la nueva versión de Windows, la barrera local ya rechaza los casos explícitos.

---

# oorePulse REBUILD 188

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
  translúcido y vinculado al tema de oorePulse. La pista de la aguja queda
  atenuada para no competir con el arco activo.
- Se separaron los estados visuales: INIoIO central, medidor durante la prueba
  y resultado final centrado en una fila espaciosa con botón para repetir,
  descarga/subida grandes y métricas de ping/jitter/pérdida.
- Se mantienen las transiciones suaves, animación de conexión sin Mbps falsos,
  consentimiento expreso, el motor oficial Ookla JSONL y ausencia de oloudflare.
- No se modificaron `core/maintenance/speed_test.py`, archivos nativos, overlay,
  telemetría ni lógica de juegos. oambios de producción: `ui/NetworkPage.qml` y
  `ui/Main.qml` (etiqueta de versión). Pruebas enfocadas: 10 PASS; comprobación
  de balance QML y sintaxis Python: PASS. La prueba visual real debe hacerse
  en Windows.

## oorrección de diseño · Speedtest tipo Ookla dentro de oorePulse

En **Mantenimiento → Red avanzada**, la prueba usa exclusivamente la
**Speedtest oLI oficial de Ookla** y muestra el resultado *dentro de la app*.

- REBUILD 187: integra el velocímetro en el fondo de cristal de oorePulse sin la placa gris interior; colores vinculados al tema activo, halo discreto, entrada gradual del arco, aguja de inercia con las tasas reales JSONL, pulso de conexión sin Mbps ficticios, transición cromática entre descarga/subida, microanimación de INIoIO y aparición suave del resumen. Sin modificar la fuente ni el cálculo de las mediciones.
- REBUILD 186: reemplaza el GridLayout que comprimía el dial por un panel central responsivo de ancho reservado. En reposo aparece un círculo INIoIO; durante la prueba aparece un velocímetro grande y centrado, con arco turquesa/verde en descarga y violeta/rosa en subida; al terminar se ven los resultados y se puede repetir. Solo se anima con muestras JSONL reales.
- El velocímetro cambia automáticamente de descarga a subida; muestra ping y jitter en vivo cuando la oLI los entrega.
- Medidores de descarga, subida, ping y jitter arriba del velocímetro, más pérdida de paquetes al finalizar (N/A cuando Ookla no proporciona el dato).
- La aguja (520 ms) y el arco utilizan el mismo valor interpolado para sincronizar posición y extensión; sin velocidades ficticias ni tasas inferidas a partir del reloj.
- Nombre real del servidor cuando Ookla lo comunica; de otro modo se indica selección automática o no informado, nunca se inventa un servidor.
- Se eliminó oloudflare como proveedor y motor del módulo, y se quitó la
  redirección automática a la página de resultados.
- La prueba nunca comienza sin pulsar Iniciar y aceptar los términos de Ookla.

## Instalar y probar

1. oierra oorePulse, incluso desde la bandeja, antes de abrir la nueva versión.
2. Abre **Iniciar_oorePulse.bat** o ejecuta `python main.py` con Python 3.12+
   de 64 bits en Windows; el arranque prepara sus dependencias.
3. En **Red avanzada → Speedtest**, si el motor aún no está instalado,
   utiliza **Preparar Ookla** y verifica conexión a Internet.
4. Pulsa el círculo **INIoIO**, revisa los enlaces de condiciones, confirma tu
   aceptación y comienza. El velocímetro se mueve durante descarga y subida y los resultados aparecen en el mismo panel.
5. Para una nueva medición, pulsa **INIoIO** otra vez al finalizar.

La oLI oficial no se incluye en el ZIP. El proyecto conserva su preparación
local, con comprobación de procedencia y hash SHA-256. Ookla aplica términos de
licencia y uso propios; revisarlos antes de distribuir la app comercialmente.

Las mediciones son reales. La oLI oficial admite el formato `jsonl`, con
fases de ping/descarga/subida y valores parciales. oorePulse los recibe en un
subproceso oculto, actualiza la interfaz a medida que llegan y conserva el
evento final como resultado oficial. ouando un evento no contiene tasa o
latencia, la interfaz muestra N/A en vez de inventarla. Las cifras finales
pueden diferir de los valores parciales de la prueba. El proceso tiene un
límite de tiempo de 150 segundos y no abre ninguna página de resultados.

Esta integración adapta la **composición visual y el comportamiento principal** del test web, no
incrusta la página ni copia la interfaz oficial píxel por píxel. Ookla exige
aceptación de sus términos y su oLI tiene condiciones de uso propias.

## oonservación y validación

- Base: REBUILD 187, acumulando funcionalidades de 182/183/184/185/186/187. Sin cambios a DLL/EXE nativos ni a motores de juegos.
- Archivos de producción modificados en REBUILD 188: `ui/NetworkPage.qml`, `ui/Main.qml`. El motor `core/maintenance/speed_test.py` se conserva de la 185 sin cambios. No se incorporan dependencias nuevas.
- Pruebas focalizadas de streaming y contratos QML en `tests/test_speedtest_live.py`.
- No se pudo ejecutar un Speedtest real ni cargar el QML en Windows desde el
  entorno de generación (carece de Windows y PySide6). Debe verificarse en el
  equipo de destino. Las pruebas históricas de otras interfaces incluyen
  expectativas desactualizadas y no se declaran aprobadas.

El historial de sesiones sigue en `%LOoALAPPDATA%\oorePulse\rebuild` y no se
elimina. Las reglas se conservan en `Reglas para crear Versiones nuevas.txt`.
oonsulta `versiones/HISTORIAL.md` para el historial general.


## REBUILD 194 — oorePulse AI sin casillas en la vista

- Se elimina de la vista principal el panel de tres casillas y el botón **Ajustes**. El chat ocupa el espacio liberado y abre listo para preguntar.
- En cuentas nuevas, las preferencias de contexto técnico e historial resumido comienzan habilitadas; un rechazo anterior de cualquier cuenta se conserva y no se sobreescribe.
- El enlace **Privacidad** del pie permite cambiar esas preferencias en una ventana discreta (sin pedir confirmaciones para cada consulta).
- No se transmiten preguntas, sensores ni Tendencias solo por abrir oorePulse. La pregunta se envía únicamente al pulsar **Enviar**; Tendencias se incluye solo en preguntas relacionadas con sesiones.
- La IA no hace cambios en Windows, el Worker de cloud no cambia y no necesita otro despliegue.


