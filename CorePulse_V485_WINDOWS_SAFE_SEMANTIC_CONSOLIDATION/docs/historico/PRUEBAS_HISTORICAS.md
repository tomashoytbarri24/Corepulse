# Historial de CorePulse — PRUEBAS HISTORICAS

Registro histórico consolidado para reducir archivos sueltos. No es una guía de ejecución actual.

---

## Documento original: `PRUEBAS_V460_CLOUD.md`

# Registro de validación V460

## Verificado en este entorno

- Pruebas V459+V460: **16/16 PASS** (`tests/test_v459_cloud_first.py` y `tests/test_v460_cloud_backend.py`).
- HTTP real FastAPI/Uvicorn en bucle local con SQLite temporal: **PASS** para `/v1/status`, canje de código de un solo uso y `/v1/chat` en modo `evidence_fallback` conservando **CPU N/A**.
- Estructura `compose.yaml` leída correctamente con PyYAML: servicio `proxy` publica 80/443; `api` y `model` no publican puertos.
- `compileall` de backend, cliente e interfaz: PASS.

## Limitaciones (no ocultarlas)

- La prueba Tk de V458 requiere escritorio X11/Windows. Con Xvfb, el test Tk de V458 pasa, pero otra prueba antigua V447 no se puede completar porque `customtkinter` no está instalado y no se pudo descargar en este entorno.
- Tres pruebas de estilo heredadas (`test_v427`, `test_v428`, `test_v440`) fallan igualmente en la base V459 original; no se modificaron los componentes implicados en V460.
- No se ha instalado un servidor cloud real con GPU ni ejecutado un LLM real. Docker/Compose/Caddy no están disponibles aquí para comprobar contenedores funcionando.
- No se ha ejecutado la aplicación gráfica completa en Windows ni se ha comprobado Credential Manager nativo.
- No hay medición de calidad del diagnóstico generativo; el adaptador sí puede conectarse a un host compatible una vez desplegado.

## Pruebas manuales recomendadas

1. Abrir CorePulse V460 y confirmar que no se inicie `llama.cpp` ni servidor local.
2. Antes de consentir, verificar que no se emitan solicitudes HTTPS.
3. Introducir URL del servidor HTTPS y un código generado por `python -m app.admin issue`.
4. Activar consentimiento; preguntar por un sensor N/A y confirmar que la respuesta lo conserve.
5. Canjear un código dos veces: la segunda debe ser rechazada.
6. Revocar la instalación, intentar preguntar y comprobar que se solicite otro código.
7. Desactivar CorePulse AI: no deben iniciarse solicitudes nuevas; monitoreo y diagnósticos locales continúan.
8. Comprobar el uso de memoria del proceso CorePulse antes/después de la IA para verificar que no existe LLM local cargado.

---

## Documento original: `PRUEBAS_V461_AI_GUARDRAILS.md`

# Registro de pruebas · CorePulse V461

Fecha: 2026-10-09. Entorno disponible: Linux / Python 3.13, no Windows 10/11 real.

## Resultado comprobado

- `python -m pytest -q tests/test_v461_ai_guardrails.py tests/test_v459_cloud_first.py tests/test_v460_cloud_backend.py`: **57 pruebas aprobadas**, 0 fallos. Incluyen dispositivo autorizado, límite diario, privacidad/consentimiento, fallback ante respuestas inventadas, tutoriales sin consultas externas, SMART N/A y `REAL_FPS_OR_NA_ONLY`.
- Compilación (`python -m compileall -q CorePulse_AI_Server core gui/ai_panel.py`): completada sin errores de sintaxis.
- `python CorePulse_AI_Server/evaluation/evaluate_v461.py --out ...`: **10 casos sintéticos válidos**, sin LLM ni llamadas externas. No es puntuación de calidad de respuestas generativas.

## Pruebas históricas fuera de V461

- En una ejecución completa con escritorio Xvfb, la suite reportó **112 aprobadas, 8 fallidas, 1 omitida y 37 subtests aprobados**. Las fallas ocurrieron en pruebas antiguas de apariencia/Canvas, en una prueba que exige `customtkinter` no disponible y en assert de código antiguo; no se tocaron las implementaciones involucradas en estas diferencias, salvo el texto de estado del chat CorePulse AI.
- En una segunda ejecución total con Xvfb el proceso Python 3.13/Tk abortó de forma nativa antes de completar; por ese motivo **no hay un resultado final exitoso de la suite completa** en este entorno.
- No se ha comprobado el funcionamiento de la interfaz en Windows real, la persistencia de Credential Manager en Windows ni contenedores GPU/LLM remoto. No se probó la calidad de un modelo cloud real.

## Alcance de las verificaciones

Los controles regex+reglas rechazan varios tipos conocidos de alucinaciones cuantitativas; **no garantizan la verdad de todas las respuestas posibles**. En particular, falta evaluación semántica más general, detección de números sin unidad y evaluación independiente por especialistas. Tampoco hay servidor GPU desplegado ni modelo definitivo elegido.

## Verificaciones manuales futuras

Probar en Windows con permisos y credenciales aisladas, capturar conexiones salientes sin consentimiento, confirmar apagado real de IA, repetir 10 casos contra el modelo cloud y revisar casos clínicamente/técnicamente incorrectos antes de producción.

---

## Documento original: `PRUEBAS_V462_CLOUD_MODEL_EVALUATION.md`

# Pruebas de CorePulse V462 (9 octubre 2026)

## Estado de pruebas automáticas

- V462 nuevo: **28 tests aprobados**, sin utilizar GPU externa, con transporte HTTP loopback contra stub local.
- Pruebas focalizadas V459–V462: **85 tests aprobados**, incluyendo validadores REAL_OR_NA y API de V461.
- Corpus V462: **30 casos sintéticos, 13 críticos**, estructura correcta; ejecución predeterminada **sin red** y **sin modelo**.
- Suite completa en este entorno Linux sin pantalla: **20 fallidos, 131 aprobados, 3 omitidos**, más 37 subpruebas aprobadas.
- La misma suite completa en base V461, en el mismo entorno: **20 fallidos, 103 aprobados, 3 omitidos**, más 37 subpruebas aprobadas. Los 20 fallos corresponden a escritorio Tk no disponible y contratos heredados de diseño: no se introdujeron fallos nuevos observados en esa suite.

## Precaución

Las pruebas de V462 de transporte HTTP no validan razonamiento de un LLM real, conexión GPU externa ni rendimiento del programa de Windows. **No se ha desplegado servidor GPU ni generado una tabla de precisión real entre modelos.**

No se modificaron el esquema de la interfaz gráfica, el control de sensores ni los cambios de Windows. Solo se reutilizó el generador de mensajes de producción dentro del evaluador, evitando divergencia de prompts.

## Comandos

```powershell
python -m pytest -q tests/test_v459_cloud_first.py tests/test_v460_cloud_backend.py tests/test_v461_ai_guardrails.py tests/test_v462_cloud_model_evaluation.py
python CorePulse_AI_Server/evaluation/benchmark_v462.py --out resultados/evaluacion_dataset_v462.json
```

## Comprobaciones manuales pendientes (Windows)

1. Abrir CorePulse y validar que sigue mostrando V462 y que el chat no inicia llama.cpp en segundo plano.
2. Desactivar IA; confirmar que la telemetría y el diagnóstico base siguen disponibles.
3. Probar una conexión cloud HTTPS a servidor real, consentimiento y revocación de token por dispositivo.
4. Probar 30 escenarios en cada modelo candidato, repetir y revisar manualmente respuestas complejas con personal técnico.
5. Capturar estadísticas reales del GPU server, latencia, costos y fallos y no promocionar un modelo sin calidad validada.

---

## Documento original: `PRUEBAS_V463_GROQ_CLOUD.md`

# Evidencia de pruebas — CorePulse V463

| Área | Resultado |
|---|---|
| Tests V459–V463 | 105 aprobados; simulación HTTP, permiso, vinculación, Groq y Safety Gate |
| Suite histórica completa | 20 fallos heredados, relacionados con GUI (pantalla Tk inexistente) y contratos visuales antiguos; no deben interpretarse como pruebas V463 aprobadas |
| Conexión externa real Groq | NO EJECUTADA (sin credencial del usuario, sin costo) |
| Capturas de pantalla Windows | NO EJECUTADAS (entorno Linux headless) |
| Prueba automática con datos reales del usuario | PROHIBIDA; solo se habilita al aceptar consentimiento |

Los tests usan datos **sintéticos** y mocks que no realizan consultas al proveedor real. El evaluador V462 no certifica precisión diagnóstica. El modo seguro se mantiene cuando el modelo no se puede usar o falla el filtro post-generación.

**Comandos:** `python -m pytest -q tests/test_v459_cloud_first.py tests/test_v460_cloud_backend.py tests/test_v461_ai_guardrails.py tests/test_v462_cloud_model_evaluation.py tests/test_v463_groq_cloud.py`.

**Prueba manual de Windows necesaria:** arrancar el BAT 11, comprobar la vinculación local, permitir telemetría explícitamente, realizar una consulta y comprobar el estado del Safety Gate; desactivar IA y verificar la interrupción de nuevas solicitudes.

---

## Documento original: `PRUEBAS_V464_GROQ_DIAGNOSTICS.md`

# CorePulse V464 — Evidencia de pruebas

- **119 tests focalizados PASS (V459-V464).**
- Proveedor Groq real: **NO EJECUTADO** porque no hay clave de API del usuario en este entorno.
- Interfaz Windows: **NO VALIDADA** porque este entorno no cuenta con GUI Windows.
- Se verificó con mocks que GET /models no incluye telemetría del equipo ni historial y que no sigue redirecciones.
- No se modificaron diagnósticos de Windows ni mediciones; se mantiene REAL_OR_NA.
- El historial de pruebas generales incluye fallos de interfaz heredados; esta versión no declara que se hayan solucionado.

Para repetir: `python -m pytest -q tests/test_v459_cloud_first.py tests/test_v460_cloud_backend.py tests/test_v461_ai_guardrails.py tests/test_v462_cloud_model_evaluation.py tests/test_v463_groq_cloud.py tests/test_v464_groq_diagnostics.py`.

---

## Documento original: `PRUEBAS_V465_GROQ_PERMISSION_ROOTCAUSE.md`

# Verificación V465

- **136/136 pruebas específicas de V459–V465 aprobadas** (`python -m pytest -q` con siete archivos `test_v459...` a `test_v465...`).
- **Suite general:** 182 PASS, 20 FAIL, 3 SKIPPED, 37 subtests PASS. Los fallos afectan contratos gráficos antiguos y pruebas que necesitan Tk/Windows; no se validó la interfaz de escritorio en este entorno.
- Se probaron las prioridades de credenciales con dos claves diferentes, códigos reales documentados de bloqueo de modelos y respuestas HTML/JSON no confiables sin filtrar texto sensible.
- Se comprobó con mocks que la prueba de credenciales V465 no necesita Internet. **No se probó una cuenta real de Groq** (no disponemos de clave de usuario).
- Los límites `REAL_OR_NA`/`REAL_FPS_OR_NA_ONLY` y la supervisión local permanecen sin cambios.

---

## Documento original: `PRUEBAS_V466_GROQ_EDGE.md`

# Pruebas V466

- Tests V466 del `User-Agent` Groq y fallback de otros proveedores, peticiones GET y POST sin modificar URL ni tokens.
- Clasificación de bloqueo Cloudflare 1010 por HTTP 403 sin filtrar contenidos arbitrarios ni secretos.
- Fallback de permisos de organización/proyecto y de 403 genérico de V465.
- Verificación local no contacta Internet ni revela credenciales.
- Pruebas heredadas del producto y documentación de límites: ver informe ejecutado por el desarrollador.

## Resultados de este entorno (Linux sin pantalla Windows)

- **143/143 pruebas focalizadas V459–V466 PASAN**.
- Suite general: **189 PASS, 20 FAIL, 3 SKIPPED y 37 subtests PASS**. Los 20 fallos se mantienen de V465 y corresponden a contratos de UI heredados y casos que requieren display gráfico; no se ha validado Windows real.
- GET `/models` y POST `/chat/completions`: pruebas con red simulada (sin cuenta real), ambas con `User-Agent: CorePulse-AI/466`.
- Cloudflare 1010 reconocido por firma acotada sin exhibir contenidos sensibles.
- **La respuesta auténtica de Groq todavía no ha sido verificada con la API key del usuario.**

---

## Documento original: `PRUEBAS_V469_TUTORIAL_FOLLOWUPS.md`

# Pruebas V469

- Caso del vídeo V468: "tutorial de mantenimiento preventivo" → "un link de youtube": búsqueda pertinente, no vídeo exacto.
- Sin tema previo: petición de aclaración.
- Tema antiguo sustituido por otra consulta: no rescatar tema antiguo.
- Respuesta del asistente no se usa para deducir tema.
- URL exclusiva `https://www.youtube.com/results?search_query=`; rechazar dominio parecido, vídeos inventados y parámetros extra.
- El botón jamás abre el navegador automáticamente; requiere clic.
- El servidor rechaza chat sin token; el enlace educativo no consulta el LLM.
- Se conservan consentimiento, REAL_OR_NA y el flujo de diagnóstico preexistentes.

Estado de la suite general en este entorno: 20 fallos heredados (pantallas Tk sin display y aserciones antiguas de UI) y 3 omitidas. La interfaz real de Windows requiere validación manual.

---

## Documento original: `PRUEBAS_V472_INDEPENDENCIA.md`

# Evidencia de pruebas V472

- Escenarios nuevos: selección de proveedor, URL HTTPS, secretos ligados al destino, transición de consentimiento/token, identidad del modelo activo, bloqueo del puente antiguo antes de enviar telemetría, formateo compartido y seguridad ante respuestas inventadas.
- Ejecución local: `python -m pytest -q tests/test_v472_provider_independence.py`.
- Suite cloud V459–V472: `python -m pytest -q tests/test_v4{59,60,61,62,63,64,65,66,67,68,69,70,71,72}*py` (en Bash; en Windows ejecutar selección por archivo o `22_VALIDAR_INDEPENDENCIA_V472.bat`).
- Entorno: Python 3.13 de Linux, sin GUI Windows ni credenciales remotas. No afirmar inferencia real del segundo proveedor.
- La prueba `/v1/chat` con modelo alternativo simula el HTTP upstream; el bloqueo de datos antes de `/v1/chat` se prueba por separado.
- No modificar los 20 fallos heredados de pruebas gráficas; documentarlos, no ocultarlos.
