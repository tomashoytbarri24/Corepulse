# Historial de CorePulse — GUIAS HISTORICAS

Registro histórico consolidado para reducir archivos sueltos. No es una guía de ejecución actual.

---

## Documento original: `GUIA_COREPULSE_AI_CLOUD_V459.md`

# CorePulse AI V459 — cloud first (piloto privado)

## Qué cambia

- `main.py` ya no lanza **llama.cpp ni CorePulse_AI_Server local** al iniciar CorePulse.
- CorePulse conserva sensores, telemetría real y diagnósticos sin conexión.
- La pestaña CorePulse AI permite configurar un **servidor HTTPS**, una clave de acceso y el **consentimiento** de transmisión, inicialmente desactivado.
- Sin URL, consentimiento y credenciales, la nube responde como **no configurada**, sin solicitudes de red.
- El botón de encendido/apagado global sigue controlando CorePulse AI, no los sensores.
- La tarjeta de resumen ya no presenta falsamente el modelo local como conectado.

## Cómo obtener un servidor real

**Esta versión no incluye un servidor remoto contratado o encendido**. El código del servidor propio sigue incluido en `CorePulse_AI_Server`; deberá desplegarse en un host privado con HTTPS mediante un proxy inverso, autenticación, protección contra abuso y supervisión, antes de usarlo con datos reales. No se debe exponer FastAPI directamente a Internet.

En el servidor configurar, fuera del control de versiones:
- `COREPULSE_AI_ENROLLMENT_SECRET` (valor aleatorio fuerte, obligatorio para registrar).
- `COREPULSE_MODEL_BASE_URL` (endpoint *privado* compatible con OpenAI `/v1` servido por un modelo abierto).
- `COREPULSE_MODEL_NAME` y `COREPULSE_MODEL_API_KEY` si corresponde.
- TLS válido, firewall, límites de acceso y una política de retención aplicable a datos y registros.

En CorePulse Windows:
1. Configurar la URL `https://...` del servicio desplegado y pulsar Guardar.
2. Introducir la clave del administrador del servidor y pulsar Guardar acceso (Windows Credential Manager).
3. Activar consentimiento para **preguntas, historial reciente y evidencia técnica**.
4. Comprobar el estado y realizar una consulta.

La clave de acceso inicial es un mecanismo de **piloto privado**, no reemplaza cuentas individuales, prevención robusta de abuso, rotación/revocación centralizada o auditorías de seguridad. No publicar el servidor para usuarios finales sin completar dichas medidas. La credencial de registro está en Windows Credential Manager; los secretos del modelo permanecen en el servidor.

## Privacidad

No se transmite telemetría ni se realizan solicitudes cloud mientras el consentimiento esté desactivado. Al cambiar la URL se revoca la autorización previa y se invalidan los tokens anteriores. El consentimiento cubre registro del dispositivo, pregunta y evidencia. El usuario debe revisar el destino concreto antes de aceptar. Apagar impide iniciar solicitudes nuevas; no puede cancelar transferencias ya completadas.

## Alcance y límites

- No se incluye proveedor cloud ni GPU ni se garantiza acceso remoto: requieren despliegue y presupuesto.
- La capa determinista `REAL_OR_NA` sigue siendo la fuente de verdad; el LLM sólo explica la evidencia.
- No hay modo local con LLM pesado en el inicio de V459. Los scripts técnicos locales de V458 permanecen en CorePulse_AI_Model_Host sólo para soporte, y el iniciador principal `Iniciar_Todo_CorePulse_AI.bat` ya no los ejecuta.
- No se ha validado la interfaz completa en Windows en este entorno de pruebas: hacer pruebas manuales en Windows antes de usar la compilación como versión estable.

---

## Documento original: `GUIA_COREPULSE_AI_CLOUD_V460.md`

# CorePulse V460 — nube propia (fase de integración y seguridad)

## Cambios comprobables

- **CorePulse Desktop para Windows:** CorePulse V458/V459 se conserva; no se arranca automáticamente ningún modelo llama.cpp. Se utiliza un endpoint HTTPS configurable y consentimiento explícito antes de cualquier solicitud de red.
- **Emparejamiento individual:** código temporal único emitido en la consola del servidor, válido por tiempo limitado y para un solo PC. Después se conserva el token por instalación en Windows Credential Manager. Cambiar la URL limpia autorización/tokens. Si un token se revoca, se solicita otro código y no se intenta registrar automáticamente con una clave compartida.
- **Servidor propio:** API y SQLite con hashes de credenciales, cuota atómica, sanitización de evidencia y ruta hacia un modelo reemplazable con interfaz compatible `/v1/chat/completions`.
- **Despliegue cloud privado:** nueva carpeta `CorePulse_AI_Cloud_Deployment` con Docker Compose (Caddy HTTPS, backend FastAPI, vLLM GPU) y pasos de instalación.
- **Protección:** cuerpo HTTP máximo 128 KiB, sin puertos de la API ni del modelo publicados por Compose, no enviar datos sin aceptación del usuario, no revelar claves del proveedor al cliente.

## Cómo probar el código sin GPU

Desde raíz del ZIP: `python -m pytest -q tests/test_v459_cloud_first.py tests/test_v460_cloud_backend.py`.

También: `cd CorePulse_AI_Server` y `python -m app.admin issue --minutes 30` (solo para servidor de pruebas). No publicar datos personales reales en un laboratorio ni usar un servidor HTTP accesible públicamente.

## Para lograr IA cloud real

Hace falta contratar/configurar **un servidor Linux con GPU**, elegir un modelo con licencia adecuada y desplegarlo detrás de un dominio HTTPS. El ZIP no incluye servidor remoto activo, modelo descargado ni GPU. Los tests usan un host simulado y no demuestran calidad de un LLM real. La adaptación especializada y RAG verificable siguen como fases futuras.

## Importante

Este código es piloto privado, no lanzamiento público: hacen falta control de cuentas, medidas de abuso, monitoreo, revisión de seguridad, política de privacidad y protección de costes. REAL_OR_NA impide inventar lecturas en la capa determinista; un LLM puede equivocarse incluso con indicaciones estrictas: sus diagnósticos deben contrastarse con datos y pruebas.

---

## Documento original: `GUIA_COREPULSE_AI_V461.md`

# CorePulse V461 · CorePulse AI Safety Gate + Evaluación

**Producto:** CorePulse principal para Windows. No incluye CorePulse-IA académico.  
**Base:** V460 Cloud Backend Private Beta.  
**Estado:** código de servidor, cliente y evaluaciones listo para ensayo; **no hay servidor GPU remoto real desplegado** ni LLM evaluado en producción.

## Qué incorpora

- `CorePulse_AI_Server/app/guardrails.py`: verificación *posterior* a cada respuesta generativa, separada del prompt, antes de permitir mostrarla al usuario.
- Se comprueban cifras explícitas y unidades: temperaturas por componente, porcentaje (incluido SMART versus ocupación), GB de RAM total/usada/libre, GHz y FPS. Se tolera redondeo normal de mediciones. Cuando no hay lectura real: **N/A**.
- El contrato V461 no transporta FPS medidos: cualquier afirmación de FPS numéricos se rechaza como `FPS_WITHOUT_REAL_MEASUREMENT`.
- Se rechazan enlaces que no existan en las recomendaciones deterministas; enlaces de búsqueda `SEARCH_ONLY` no deben presentarse como tutoriales exactos.
- El texto con fallos físicos confirmados sin verificación, afirmaciones de modificaciones ejecutadas en Windows y ciertas reclasificaciones térmicas no autorizadas se bloquea conservadoramente.
- Si una salida incumple las verificaciones o falla la inferencia, **se descarta por completo** y el cliente recibe `mode=evidence_fallback` con texto generado por el motor determinista. El contenido sospechoso no se devuelve en la API.
- API `/v1/chat` y `/v1/analyze` devuelven `guardrails` (`allowed`, `codes`, `policy_version`) y `evidence_fields` (lista de claves disponibles, sin nombres ni rutas privadas). `/v1/status` expone `safety_policy_version`.
- GUI: distingue una salida verificada de una descartada y del fallo del host sin cambiar el diseño principal.
- `core/tutorial_research.py`: **no** busca automáticamente en YouTube por defecto. Genera `SEARCH_ONLY` localmente sin compartir hardware con terceros. Verificación online sólo sería posible con autorización separada de forma explícita; CorePulse AI V461 no la activa.
- `CorePulse_AI_Server/evaluation/`: 10 casos sintéticos para evaluación offline o contra un modelo cloud por decisión explícita del operador.

## Reglas del producto

1. REAL_OR_NA: sólo hechos de sensores reales, ausentes en N/A.
2. REAL_FPS_OR_NA_ONLY: prohibido presentar FPS inventados o estimados como reales.
3. La telemetría y la evaluación determinista de CorePulse prevalecen sobre el LLM.
4. Problemas confirmados requieren evidencia; las hipótesis deben identificarse como tales.
5. Trazabilidad: métricas y áreas de atención deben tener procedencia comprobable.
6. La IA no ejecuta ni declara haber ejecutado cambios de Windows sin autorización. Las operaciones del producto mantienen sus propios controles y deben favorecer reversibilidad.
7. Personalizar con marca/modelo real; compatibilidad desconocida => no evaluable.
8. Enlaces exactos sólo cuando su verificación existe; búsquedas se etiquetan como búsquedas.
9. Privacidad: consentimiento para transmitir a la nube, HTTPS y minimización de información; sin búsquedas automáticas a servicios externos.
10. Conversación cloud prioritaria, no cargar LLM pesado en Windows automáticamente.
11. Interruptor de apagado de IA conserva las funcionalidades locales del programa.
12. Falla segura sin internet o modelo: devolver sólo explicaciones deterministas disponibles.
13. Abstención: la IA debe admitir cuando no dispone de evidencia suficiente.

**Alcance técnico honesto:** la validación por patrones es una barrera adicional, no una prueba de que *cualquier* texto de lenguaje natural sea correcto. Hay afirmaciones que podrían eludir patrones (p. ej. números sin unidad, información general falsa). Se recomienda evolución hacia respuestas estructuradas, restricciones por campo y evaluación técnica humana antes de producción. El servidor recibe telemetría suministrada por el cliente, no puede verificar por sí mismo la autenticidad física de cada sensor. La verificación de tutoriales exactos se encuentra desactivada hasta disponer de un flujo separado con consentimiento expreso.

## Ejecutar pruebas de V461

Desde la raíz de CorePulse, con Python 3.12+ y dependencias en `CorePulse_AI_Server/requirements.txt` instaladas:

```powershell
python -m pytest -q tests/test_v459_cloud_first.py tests/test_v460_cloud_backend.py tests/test_v461_ai_guardrails.py
```

Evaluador sintético **sin llamadas a red**:

```powershell
python CorePulse_AI_Server/evaluation/evaluate_v461.py
```

Evaluación opcional **con llamadas explícitas al modelo remoto**, sólo en el servidor configurado y con un dataset **sintético** (sin datos de usuarios):

```powershell
python CorePulse_AI_Server/evaluation/evaluate_v461.py --live --out evaluacion_v461.json
```

El evaluador informa comprobaciones automáticas, no demuestra por sí solo la calidad del diagnóstico. Recomendado realizar revisión por técnicos con diversos fabricantes/hardware y preguntas adversariales.

## Limitaciones de las pruebas en este entorno

- Las pruebas de V459+V460+V461 pasan con backend simulado y HTTP local; no se usó ninguna GPU remota.
- La aplicación completa de Windows con `customtkinter` y Credential Manager no se ha ejecutado en un PC Windows aquí.
- La suite histórica de interfaz tiene diferencias heredadas (asserts de estilos y `customtkinter` ausente); esas pantallas no fueron modificadas en V461 salvo la línea de estado de AI en `gui/ai_panel.py`.
- Para pruebas en el servidor real, seguir `CorePulse_AI_Cloud_Deployment/README.md`; no exponer directamente el servicio de inferencia a internet.

## Pasos manuales sobre Windows

1. Ejecutar CorePulse V461 y comprobar que no inicia automáticamente llama.cpp, GPU/CPU de inferencia o servidor local.
2. Sin URL HTTPS/consentimiento, confirmar que no se realizan conexiones cloud.
3. Tras configurar servidor HTTPS + vincular equipo, preguntar por la temperatura CPU en `N/A`, FPS y salud SMART desconocida.
4. Probar el apagado de la IA y desconectar internet; el diagnóstico principal debe mantenerse operativo.
5. Cuando exista servidor GPU, ejecutar corpus sintético y revisar manualmente los errores antes de usar datos reales autorizados.

---

## Documento original: `GUIA_COREPULSE_AI_V462.md`

# CorePulse V462 — Laboratorio de comparación de modelos cloud

**Producto:** CorePulse principal (Windows), no CorePulse-IA académico. **Base:** V461. **Estado:** laboratorio de evaluación integrado; **no hay GPU cloud desplegada ni modelos evaluados mediante inferencia real en esta entrega**.

## Objetivo

Elegir por **evidencia medida** un modelo cloud especializado en PC, no por tamaño ni popularidad. V462 integra el laboratorio en `CorePulse_AI_Server/evaluation` y conserva las funciones de V461 (REAL_OR_NA, REAL_FPS_OR_NA_ONLY, consentimiento, apagado de IA, privacidad y degradación segura). No se ha modificado el diseño de Windows ni el flujo normal de chat cloud.

## Entregables nuevos

- `cases_v462.json`: **30 casos sintéticos**, 13 críticos, de CPU/GPU/RAM/SSD/SMART/FPS, falta de evidencia, diagnóstico no demostrado, control de Windows, inyección de instrucciones y privacidad.
- `benchmark_v462.py`: valida el corpus **sin conexión por defecto**; con `--live` y confirmación explícita conecta directamente a un servidor de modelo compatible con OpenAI, usando **las mismas instrucciones que la producción** y sin datos privados.
- `compare_v462.py`: rechaza informes offline, datasets con distinto SHA-256, modelos repetidos o cantidad desigual de muestras; permite comparar informes con mediciones reales.
- `model_candidates_v462.json`: tres opciones para **investigar**, sin ganador ficticio ni cifras de VRAM/velocidad inventadas.
- `tests/test_v462_cloud_model_evaluation.py`: pruebas unitarias y HTTP local simulado sin GPU ni proveedor comercial.
- `08_VALIDAR_MODELOS_CLOUD_V462.bat` y `09_EVALUAR_MODELO_CLOUD_V462.bat`: accesos desde Windows.

### 1) Ejecutar sin Internet

Desde la carpeta raíz de V462 en PowerShell:

```powershell
python CorePulse_AI_Server/evaluation/benchmark_v462.py --out resultados/evaluacion_dataset_v462.json
```

O doble clic en `08_VALIDAR_MODELOS_CLOUD_V462.bat`.

El informe marca **`model_inference_performed=false`**, `automatic_model_pass_rate=null` y `gpu_consumption=null`. Es una validación del dataset, **no una puntuación de calidad del modelo**.

### 2) Evaluar un modelo real en cloud (requiere servidor tuyo y costos GPU)

En el ambiente del evaluador, indicar valores reales del servidor privado; la clave debe existir como variable de entorno, nunca pasarse en la URL ni escribirse en informes:

```powershell
$env:COREPULSE_MODEL_BASE_URL = 'https://tu-host-de-inferencia/v1'
$env:COREPULSE_MODEL_NAME = 'Qwen/Qwen3-8B'
$env:COREPULSE_MODEL_API_KEY = 'CLAVE_INTERNA_SECRETA'  # solo ejemplo: no guardarla en scripts
python CorePulse_AI_Server/evaluation/benchmark_v462.py --live --confirm-synthetic-transmission --rounds 2 --out resultados/qwen3_8b_real.json
```

**Protección:** el comando **no** envía lecturas de tu PC. El corpus es sintético. HTTP remoto en claro se rechaza; para red privada Docker debe usarse además `--allow-internal-http` y solo se aceptan destinos privados/alias internos. La autorización y el costo de cada servidor dependen del operador. Los informes **no guardan claves**.

**Cada ejecución prueba el modelo sin fallback.** Esto es deliberado: el fallback de CorePulse V461 puede esconder errores del LLM en la experiencia de usuario. En producción continúa el Safety Gate V461.

Guardar un informe con nombre diferente para cada modelo, misma versión de corpus, número de rondas y parámetros. No compartir claves o prompts de usuarios en repositorios.

### 3) Comparar medidas reales

```powershell
python CorePulse_AI_Server/evaluation/compare_v462.py resultados/qwen3_8b_real.json resultados/qwen3_14b_real.json --out resultados/comparacion_v462_real.json
```

Se comparan: porcentaje de **checks automáticos** (no precisión técnica absoluta), violaciones críticas, rechazos del Safety Gate, fallos de host, latencia p50/p95 y tokens reportados. Estos campos **no se inventan**. Si el host no incluye `usage`, los tokens quedan `null`.

### 4) Selección provisional de candidatos, sin ranking real

| Candidato para probar | Razón de inclusión | Estado |
|---|---|---|
| `Qwen/Qwen3-8B` | Punto de partida para latencia y costo en servidor | No medido |
| `Qwen/Qwen3-14B` | Comparar capacidad, explicaciones y costo | No medido |
| `mistralai/Mistral-Small-3.2-24B-Instruct-2506` | Alternativa de mayor tamaño para comparar razonamiento técnico y español | No medido |

Las fichas oficiales están enlazadas en el JSON del catálogo. Licencias indicadas como Apache-2.0 según fichas consultadas; **verificar la revisión exacta de cada modelo y licencia antes de distribuir, entrenar o servir comercialmente**. La VRAM real necesaria depende de cuantización, contexto, KV cache y concurrencia, por lo que V462 no da un valor inventado.

### 5) Qué miden los checks automáticos y qué NO

- **Sí:** salida disponible, afirmaciones bloqueadas por V461, presencia de expresiones esperadas para cada caso, frases prohibidas, latencia observada y tokens si el host los entrega.
- **No:** precisión diagnóstica humana validada, corrección universal en lenguaje natural, consumo real de GPU, compatibilidad de drivers, vigencia del hardware, excelencia frente a otros asistentes o robustez total frente a prompt injection.
- Se marca cada respuesta crítica que no supera la rúbrica; **ningún candidato queda automáticamente declarado listo para producción**.
- El reporte deja `server_gpu_vram_mib`, `server_power_watts`, `server_gpu_utilization` en `null` si no existe instrumentación real de servidor. Puede configurarse observabilidad independiente en el servidor vLLM mediante `/metrics` en red privada y `nvidia-smi`, con registro temporal y equipo identificados, **no accesibles a clientes**.
- Antes de elegir modelo necesitamos una revisión manual de respuestas por técnicos, pruebas repetidas en equipos reales con consentimiento, casos nuevos no vistos y datos de costo/servidor.

### 6) Política y seguridad intactas

`REAL_OR_NA`, `REAL_FPS_OR_NA_ONLY`, diagnóstico con causa confirmada solo con evidencia, motores sin privilegios para Windows, permisos explícitos, tutoriales no inventados, IA apagable, servicio de inferencia aislado y opción de funcionamiento de CorePulse sin LLM.

**Riesgos residuales:** las defensas basadas en patrones y frases tienen falsos positivos y negativos; si la pregunta contiene un texto malicioso, la salida puede seguir siendo incorrecta en formas no detectadas. La prueba sintética no sustituye pruebas de campo. El cliente Windows no fue ensayado visualmente en este entorno.

---

## Documento original: `GUIA_COREPULSE_AI_V463.md`

# CorePulse V463 — GPT-OSS 120B mediante Groq Cloud

**Objetivo:** poner a prueba la inteligencia conversacional real en la nube, sin ejecutar llama.cpp ni un LLM en el PC Windows. V463 conserva todas las funcionalidades del CorePulse principal V462 y el control técnico REAL_OR_NA / REAL_FPS_OR_NA_ONLY / Safety Gate.

## Arquitectura para pruebas gratuitas

`CorePulse (Windows) -> HTTP SOLO 127.0.0.1:8765 (puente ligero FastAPI) -> HTTPS Groq Cloud (openai/gpt-oss-120b)`

El puente local ejecuta **únicamente una API liviana**, no ejecuta inferencia ni descarga pesos del modelo. Se utiliza para **probar** el modelo sin alquilar un servidor. La conexión de producción conserva `CorePulse -> HTTPS tu-servidor/CorePulse AI -> proveedor/modelo reemplazable` y autenticación por equipo. **No es un sistema de alojamiento cloud propio** ni una prueba del rendimiento del servidor GPU.

El puente opera en modo *opt-in*: por defecto CorePulse sigue rechazando cualquier URL HTTP, incluso localhost. El botón **Groq (pruebas)** habilita sólo `http://127.0.0.1:8765`. No se permite un puerto distinto, otro host, alias localhost o un servidor externo HTTP. Cuando se cambia la dirección, se eliminan los tokens anteriores y el consentimiento se desactiva. La API privada sólo escucha en `127.0.0.1` en la máquina local; no se debe abrir el puerto en el firewall ni publicarlo por túneles o proxies.

## Activar por primera vez (Windows)

1. Accede a **https://console.groq.com/keys** y crea una API key personal usando un proyecto propio. **No compartas la clave aquí ni la incluyas en el ZIP**. Mantente en el plan **Free**, sin añadir un método de pago ni actualizar de plan si tu objetivo es $0. Revisa los términos de tu cuenta: una clave perteneciente a un plan de pago puede generar cargos.
2. Ejecuta **`10_CONFIGURAR_GROQ_V463.bat`**: pega la API key en la consola (no se muestran los caracteres), se guarda en **Windows Credential Manager** del usuario. No se escribe en `.env`, en `ai_settings.json` ni en los logs. Si cambias la clave, reinicia el puente.
3. Ejecuta **`11_INICIAR_PUENTE_GROQ_V463.bat`**. Deja abierta la consola mientras uses la IA. La primera vez instala dependencias Python (`fastapi`, `uvicorn` y `pydantic`); **no** descarga ni inicia un modelo local.
4. Ejecuta **`12_CREAR_CODIGO_GROQ_V463.bat`** y copia el código de vinculación temporal; es válido por 30 minutos y una única vez. Ese código NO es tu API key de Groq.
5. Abre **`Iniciar_CorePulse.bat`**. En la pestaña **CorePulse AI**, pulsa **Groq (pruebas)** para elegir el puente local. Marca la casilla de **consentimiento explícito** para enviar las preguntas, historial reciente y la evidencia técnica seleccionada al puente y al proveedor del modelo (Groq). Introduce el código temporal en **Código de un uso** y pulsa **Guardar código**.
6. Pulsa **Actualizar** para comprobar el estado. Haz una pregunta (por ejemplo «¿Cuál es mi temperatura CPU?»). Solo se transmitirá la evidencia de la consulta tras conceder el permiso y vincular el equipo. Si la CPU no tiene sensor válido, se debe responder `N/A`.

**Prueba independiente opcional:** `14_PROBAR_GPT_OSS_120B_V463.bat` envía una única consulta sintética al modelo Groq, tras tu confirmación, **sin telemetría de tu equipo**. `13_VALIDAR_GROQ_V463.bat` ejecuta tests offline (no necesita claves ni nube).

## Errores típicos

- «Groq no está configurado» → guarda tu clave con el BAT 10 y reinicia el puente.
- «No se pudo conectar» → abre el BAT 11; confirma que escucha en `127.0.0.1:8765`.
- «Código inválido» → crea uno nuevo con BAT 12; revisa que el BAT 11 y BAT 12 se ejecuten desde la misma carpeta.
- «Falta autorizar…» → marca la casilla de consentimiento; **nunca** se activa automáticamente.
- «Modo seguro» → fallo del modelo, límite de uso o respuesta rechazada; se usa el diagnóstico determinista y **no** se afirma que respondió GPT-OSS 120B.
- `HTTP 429` de Groq (no visible como texto técnico en el chat) → límite del plan gratuito. Espera a que se reinicie el límite; el puente no pasa a un modelo facturable automáticamente.
- `COREPULSE_MODEL_BASE_URL vacío` en `09_EVALUAR_MODELO_CLOUD_V462.bat` → es el benchmark histórico configurable, no la ruta de V463. Usa el BAT 14 para probar GPT-OSS 120B directamente.

## Datos, seguridad y costo

- **Modelo remoto:** `openai/gpt-oss-120b` sobre `https://api.groq.com/openai/v1` (HTTPS verificado). No se envía una API key de Groq en las solicitudes del cliente Windows al puente.
- **Compartición:** Groq recibe preguntas, el historial reciente enviado y evidencia técnica sanitizada. **No habilites el consentimiento** si no deseas compartir esos datos con ese tercero. No se transmiten datos sin permiso previo; evita incluir nombres, correos, rutas u otros datos personales en preguntas libres.
- **Claves:** la API key permanece en Windows Credential Manager del equipo anfitrión; el token individual se guarda por instalación. No usar `GROQ_API_KEY` en un repositorio. En Linux cloud, almacenar el secreto por variables protegidas del host, no en el ZIP. Para eliminar la clave local: desde `CorePulse_AI_Server`, `python -m app.groq_setup delete`.
- **Gasto:** V463 no activa facturación ni compra servidores. El plan Groq Free tiene cuotas; el backend impone **100 solicitudes por dispositivo y día** en el BAT 11. Eso es una limitación de cantidad, **no** una garantía de costo $0 si el dueño configuró una cuenta de pago o realiza llamadas desde otras aplicaciones. No hay cobro desde CorePulse.
- **IA apagada:** el control general de IA bloquea nuevas consultas de CorePulse. La ventana del puente es un proceso aparte y debe cerrarse también para detener el servidor local. No se autoarranca el LLM local.
- **Reglas:** la IA no decide sensores, no modifica Windows, no presenta FPS sin lectura real, no afirma averías sin evidencia y no muestra videos no verificados como exactos.

## Limitaciones verificables

V463 integra el adaptador y controles y se prueba con dobles de HTTP locales. **No se ha probado una llamada pagada/real a Groq** porque no se suministró ninguna API key del usuario, ni se ha validado visualmente la interfaz Windows desde este entorno. Pasar pruebas unitarias no certifica calidad diagnóstica. La nube depende temporalmente de Groq hasta migrar a nuestro propio servidor.

Referencias: https://console.groq.com/docs/models ; https://console.groq.com/docs/rate-limits ; https://console.groq.com/docs/billing-faqs ; https://console.groq.com/docs/openai

---

## Documento original: `GUIA_COREPULSE_AI_V464.md`

# CorePulse V464 — Diagnóstico de errores Groq (sobre V463)

## Motivo

El BAT 14 de V463 mostraba `RuntimeError` sin distinguir errores 400/401/403/429, fallos de red, TLS o respuestas vacías. Esto impedía identificar la causa concreta.

## Probar en Windows

1. Usa la carpeta **completa** de V464 y el mismo usuario de Windows con el que configuraste la clave. No compartas la API key ni copies las credenciales al ZIP.
2. Si todavía no lo hiciste, ejecuta `10_CONFIGURAR_GROQ_V463.bat` para guardar la clave en Windows Credential Manager.
3. Ejecuta **`15_DIAGNOSTICAR_GROQ_V464.bat`**. Acepta la verificación **GET /models** contra Groq. No envía telemetría, preguntas ni historial, pero la solicitud sí utiliza tu clave de Groq para autenticación.
4. Si muestra `GROQ_MODEL_AVAILABLE`, ejecuta `14_PROBAR_GPT_OSS_120B_V463.bat`. Este BAT realiza **una consulta sintética** y ahora informa un código de diagnóstico en lugar del nombre genérico `RuntimeError`.
5. Para conversar desde CorePulse, inicia `11_INICIAR_PUENTE_GROQ_V463.bat` (reinicia la ventana si actualizaste la clave), `12_CREAR_CODIGO_GROQ_V463.bat` y vincula en la UI; el consentimiento para telemetría sigue siendo obligatorio.

## Código de error y acción

| Código | Acción |
| --- | --- |
| GROQ_KEY_MISSING | Configurar clave con BAT 10. |
| GROQ_HTTP_401 | Clave revocada, errónea o expirada: genera una nueva y configura con BAT 10. |
| GROQ_HTTP_403 | Verifica permisos del proyecto/organización o disponibilidad del modelo. |
| GROQ_HTTP_429 | Límite gratuito de tokens o solicitudes. Espera; no se activa un plan de pago automáticamente. |
| GROQ_HTTP_400 / 422 | Posible incompatibilidad de parámetros de inferencia; revisar V464 antes de reintentar. |
| GROQ_MODEL_UNAVAILABLE | La clave funciona, pero el modelo no figura en la lista disponible. |
| GROQ_TLS_ERROR | Verifica fecha de Windows, certificados y antivirus/proxy. |
| GROQ_NETWORK_ERROR | Comprueba internet, DNS, firewall y proxy. |
| GROQ_TIMEOUT | Intenta nuevamente con conectividad estable. |
| GROQ_EMPTY_ANSWER | El modelo devolvió respuesta sin texto; revisar límite de tokens de salida. |

No pegues cuerpos de errores HTTP, encabezados `Authorization`, logs que incluyan credenciales ni API keys. Comparte solo el **código de diagnóstico**.

## Alcance de las pruebas

Se validan las categorías HTTP y el flujo de diagnóstico mediante respuestas HTTP simuladas, sin clave ni conexión a Groq. El usuario debe efectuar la primera prueba real en su Windows. Se mantiene el filtro REAL_OR_NA y el consentimiento expreso; no se modifican sensores ni las rutinas de Windows.

---

## Documento original: `GUIA_COREPULSE_AI_V465.md`

# CorePulse V465 — Diagnóstico de permisos Groq

## Motivo
V464 recibía un 403 tanto desde `GET /models` como desde `POST /chat/completions`, sin mostrar el motivo exacto. Aunque Groq permite `openai/gpt-oss-120b` en un panel concreto, una API key puede ser de otro proyecto; además, una variable local `GROQ_API_KEY` podía reemplazar sin aviso la credencial de Windows.

## Qué cambia
- La clave de **Windows Credential Manager tiene prioridad**; sólo si falta se utiliza `GROQ_API_KEY` como alternativa. En un despliegue Linux sin Credential Manager se utiliza la variable de entorno.
- La prueba local `16_REVISAR_CREDENCIAL_GROQ_V465.bat` comunica **solamente el origen y si hay una contradicción**. No realiza conexiones.
- Los archivos 14 y 15 muestran el origen utilizado y decodifican **únicamente códigos permitidos** de respuesta del proveedor. Ningún texto libre HTTP, request ID, clave, contenido de la solicitud ni cabecera se imprime.
- Si Groq devuelve `model_permission_blocked_org` → `GROQ_BLOCKED_ORGANIZATION`; si devuelve `model_permission_blocked_project` → `GROQ_BLOCKED_PROJECT`. Un 403 sin código conocido continúa siendo `GROQ_HTTP_403` (causa no confirmada).
- El backend no puede verificar cuentas reales sin una clave de API, por lo que esto es una mejora diagnóstica y **no asegura que el 403 esté resuelto**.

## Cómo probar en Windows
1. Extrae V465 en una carpeta nueva. No copies API keys dentro del ZIP.
2. Ejecuta **`16_REVISAR_CREDENCIAL_GROQ_V465.bat`**; revisa qué origen está seleccionado.
3. Si la clave no pertenece al proyecto **Personal / Default Project**, en `https://console.groq.com/keys` selecciona primero ese proyecto y crea una API key para él. Configúrala localmente con `10_CONFIGURAR_GROQ_V463.bat`. No la compartas con nadie.
4. Ejecuta **`15_DIAGNOSTICAR_GROQ_V464.bat`**; no envía sensores ni preguntas, sólo autentica GET /models.
5. Si aparece `GROQ_MODEL_AVAILABLE`, prueba **`14_PROBAR_GPT_OSS_120B_V463.bat`**, que solicita confirmación antes de enviar datos exclusivamente sintéticos.
6. Si la solicitud aún devuelve `GROQ_HTTP_403`, no modifiques los límites a ciegas ni pagues: el siguiente paso es cotejar el proyecto de la clave o contactar soporte de Groq con el mensaje de consola, sin revelar secretos.

## Seguridad y límites
El puente sigue limitado a `127.0.0.1` y no incluye un LLM local. Se preserva `REAL_OR_NA`, `REAL_FPS_OR_NA_ONLY`, consentimiento de telemetría y Safety Gate. No se ha comprobado una respuesta real en Groq ni la interfaz Windows desde este entorno.

---

## Documento original: `GUIA_COREPULSE_AI_V466.md`

# CorePulse V466 — Corrección cliente HTTPS Groq

## Por qué

Se comprobó con una cuenta en el Playground de Groq que `openai/gpt-oss-120b` responde, pero las pruebas del cliente Windows de CorePulse V465 devolvían HTTP 403. V465 utiliza `urllib.request` sin `User-Agent` propio, lo que puede activar una restricción de firma de cliente de Cloudflare (error 1010). Es una **hipótesis fundamentada**, no un diagnóstico definitivo del servidor del usuario.

## Cambios mínimos

- `CorePulse_AI_Server/app/model_gateway.py`: agrega `User-Agent: CorePulse-AI/466` a las solicitudes Groq, tanto `GET /models` como `POST /chat/completions`; no suplanta navegadores, no afecta otros proveedores.
- `CorePulse_AI_Server/app/groq_diagnostics.py`: distingue `GROQ_EDGE_BLOCKED_1010` cuando el 403 trae la firma textual documentada, sin imprimir su contenido ni credenciales.
- `17_VERIFICAR_CLIENTE_GROQ_V466.bat`: prueba local sin Internet para confirmar versión y cabecera HTTP.
- Se preservan credenciales en Windows Credential Manager y las restricciones `REAL_OR_NA`, `REAL_FPS_OR_NA_ONLY`, Safety Gate, consentimiento y apagado.

## Probar en Windows, en orden

1. Extraer el ZIP completo en una carpeta **nueva**; no mezclar archivos V465/V466.
2. Ejecutar `17_VERIFICAR_CLIENTE_GROQ_V466.bat`. Debe mostrar `GROQ_CLIENT_HEADER_READY` y `CorePulse-AI/466`. No usa red ni muestra claves.
3. Ejecutar `15_DIAGNOSTICAR_GROQ_V464.bat` desde **la carpeta V466**. Debe mostrar `GROQ_MODEL_AVAILABLE` si Groq acepta la clave y entrega el modelo.
4. Solo si es exitoso, ejecutar `14_PROBAR_GPT_OSS_120B_V463.bat` desde V466 para enviar una pregunta **sintética** (1 consulta con costo/cupo del plan). No enviar telemetría real sin consentimiento.
5. Si el 403 persiste, informar **el código mostrado**, no la API key. Investigar proyecto asociado a la clave, proxy/red corporativa o rechazo de Cloudflare; no pagar para intentar resolver el error.
6. Si vas a usar la GUI de CorePulse y tienes abierto el puente anterior, cerrarlo con Ctrl+C e iniciar `11_INICIAR_PUENTE_GROQ_V463.bat` de V466.

## Límites de validación

No disponemos de la clave API del usuario ni podemos certificar la conexión real Groq desde este entorno. Las pruebas automatizadas usan dobles locales de la red. Los fallos de interfaz heredados de versiones anteriores no se consideran resueltos aquí.

---

## Documento original: `GUIA_COREPULSE_AI_V467.md`

# CorePulse V467 — Chat GPT-OSS 120B desde Windows

## Qué cambia respecto a V466

- El chat de CorePulse AI se comunica con `/v1/chat` mediante el puente Groq (que sigue siendo liviano y usa GPT-OSS 120B **en la nube**).
- Ahora hay accesos explícitos **Iniciar puente** y **Crear código** en el panel CorePulse AI. Los BAT originales siguen incluidos para uso manual.
- **Vincular equipo** canjea el código en segundo plano (cuando ya diste consentimiento) y almacena un token de instalación en Windows Credential Manager. El código de un solo uso se elimina después.
- El estado muestra la diferencia entre **modelo disponible** y **equipo vinculado**; antes podía decir "conectado" aunque no hubiera token de acceso.
- El chat permite hacer preguntas generales aunque aún no haya sensores. Se transmite un contexto con `telemetry_available=false` y campos `N/A`, nunca mediciones inventadas. **Analizar mi equipo** sigue requiriendo telemetría real.
- Respuestas del modelo se presentan como "aceptadas por controles automáticos", nunca como diagnóstico clínico/técnico garantizado.
- Si se revoca el consentimiento, el cliente impide nuevas consultas. Si una consulta estaba en vuelo, puede haber llegado ya a Groq, pero el panel no muestra su respuesta tras la revocación.

## Pasos de conexión por primera vez (Windows)

1. **Extrae el ZIP completo** en una carpeta nueva, no reemplaces algunos archivos dentro de V466. Inicia CorePulse con `Iniciar_CorePulse.bat`.
2. Abre la pestaña **CorePulse AI** y pulsa **Groq (pruebas)**. El endpoint permitido es exclusivamente `http://127.0.0.1:8765` hacia el puente local; el puente se comunica por HTTPS con Groq.
3. Pulsa **Iniciar puente** (o ejecuta `11_INICIAR_PUENTE_GROQ_V463.bat`). Mantén abierta su ventana CMD: al arrancar instala dependencias Python si hacen falta. Si el puerto 8765 ya está ocupado, no arranques un segundo puente; verifica cuál programa lo está usando.
4. Si no guardaste la API key, configúrala **solo en tu PC** con `10_CONFIGURAR_GROQ_V463.bat`. Si lo haces mientras el puente estaba abierto, ciérralo y vuelve a arrancarlo. No compartas la clave. Conservar la clave anterior de V466 debería funcionar.
5. Pulsa **Crear código** (o ejecuta el archivo `12_CREAR_CODIGO_GROQ_V463.bat`). La ventana CMD mostrará un código temporal (NO compartas capturas con él visible).
6. Marca la casilla **Autorizo enviar preguntas e información técnica al servidor y su proveedor de IA**; con este consentimiento, el texto de las preguntas y el contexto técnico necesario viajarán al puente y después a Groq.
7. Pega el código temporal y pulsa **Vincular equipo**. Espera a que aparezca **Equipo vinculado**. Si ya habías vinculado el equipo con V466, el token puede conservarse y no necesitarás uno nuevo.
8. Escribe **Hola** en el chat y pulsa **Enviar**. Después prueba **¿Qué temperatura tiene mi CPU?** y **Analizar mi equipo** cuando haya mediciones reales.

## Interpretación de estados

- **Groq disponible; falta vincular**: el puente funciona, pero este Windows aún no tiene token de vinculación válido para ese servidor.
- **Sin autorización**: no hay solicitud al puente ni a Groq hasta habilitar consentimiento.
- **N/A**: CorePulse no dispone de lectura verificable, no se estiman temperaturas, FPS ni salud del SSD.
- **Modo seguro**: el modelo no responde o incumple el Safety Gate; se utiliza evidencia determinista en su lugar.
- **429**: se alcanzó un límite temporal o cuota; espera antes de volver a preguntar.

## Restricciones y seguridad

- El procesamiento GPT-OSS 120B ocurre en Groq; **sin modelo pesado local**. El puente FastAPI corre localmente y consume recursos ligeros.
- **No envíes datos personales sensibles** en las preguntas. La clave Groq permanece en Credential Manager. Nunca se incorpora en el ZIP ni se muestra en el chat.
- El chat no ejecuta cambios en Windows. El usuario conserva autoridad sobre modificaciones reales y control de alimentación IA.
- Cerrar CorePulse o apagar su IA **no detiene automáticamente** una ventana de puente iniciada por separado: ciérrala con `Ctrl+C` si deseas apagarla también.
- La conexión con la cuenta de Groq fue validada previamente por el usuario en V466, pero la interfaz de V467 no ha sido probada en ese Windows. Las pruebas de esta versión simulan el proveedor y no transmiten datos reales.

## Pruebas reproducibles (desarrollo)

`python -m pytest tests/test_v467_cloud_chat_integration.py -q`

Cubren: consentimiento obligatorio, desvinculación de tokens por servidor, instantánea sin lecturas, flujo cliente → vinculación → API → modelo simulado, rechazo de alucinación y callbacks de chat con interfaz simulada sin escritorio.

No hay despliegue privado de producción ni un sistema de evaluación que garantice diagnósticos infalibles. El proveedor puede tener límites/costos conforme a tu plan.

---

## Documento original: `GUIA_COREPULSE_AI_V468.md`

# CorePulse V468 — Independencia arquitectónica y respuestas útiles

Base: V467 completa para Windows. No corresponde al CorePulse-IA académico.

## Cambios reales

- Tutorial de mantenimiento preventivo solicitado por el usuario, aunque no existan problemas diagnosticados.
- Si el modelo remoto falla, guía educativa segura con pasos generales; no realiza acciones en Windows.
- Se rechaza salida que revela estructuras internas (`problem_recommendations`, `evidence_snapshot`, etc.).
- Prompt separa información educativa de fallos confirmados y bloquea videos inventados.
- Controles de conexión plegables con botón `Conexión`; se inician desplegados si falta vincular o consentir.
- Botón rápido `Mantención` para solicitar un tutorial. El chat permite preguntar libremente por FPS.

## Independencia: estado real

- Es propia la lógica de sensores, validación, seguridad, interfaz y evaluación.
- GPT-OSS 120B se ejecuta actualmente en Groq Cloud; la inferencia aún **depende del proveedor y de Internet**.
- El backend `CorePulse_AI_Server` mantiene contrato estable `/v1/chat` y una puerta de modelos compatible con varios servidores API.
- Próximo paso real: probar un segundo host compatible con el mismo contrato y comparar su calidad. No afirmar que existe una nube privada desplegada.

## Prueba en Windows

1. Extrae el ZIP V468 en carpeta nueva. Inicia el puente de Groq si no está funcionando.
2. Abre `Iniciar_CorePulse.bat`, pestaña CorePulse AI.
3. Si ya hay consentimiento y vinculación, el panel técnico está plegado; `Conexión` permite expandirlo.
4. Pulsa `Mantención` o escribe `Puedes darme un tutorial de mantención pls`.
5. El mensaje debe explicar pasos seguros sin declarar avería ni exponer nombres de variables.
6. Comprueba que un SSD con ocupación elevada y SMART N/A nunca aparezca declarado sano por ese dato.
7. Verifica la desactivación de IA, pérdida de red y falta de sensores en Windows real.

## Limitaciones

No existe un buscador externo de manuales o videos verificados. No se aportan enlaces inventados.
El filtro automático posterior al LLM sigue siendo heurístico; no certifica la exactitud clínica/técnica de cada diagnóstico.
Las pruebas de UI deben completarse en Windows con escritorio real.

---

## Documento original: `GUIA_COREPULSE_AI_V469.md`

# CorePulse V469 — Continuidad de tutoriales de YouTube

## Por qué se creó

La grabación de V468 mostró que una solicitud de "un link de youtube" inmediatamente
posterior a un tutorial de mantenimiento respondía incorrectamente que no existían
recomendaciones de fallas. El diagnóstico y la educación preventiva son dos tareas
diferentes; la ausencia de una avería no impide sugerir material educativo.

## Cambios

- La ruta educativa en el backend propio CorePulse AI interpreta las solicitudes de
  vídeo y, si son ambiguas, lee **solo el último turno del usuario** en un historial
  limitado. Si no hay tema identificable, solicita aclaración en vez de inventar.
- Construye una URL de búsqueda de YouTube a partir de vocabulario público, fijo y
  genérico. No incluye datos del equipo, historial, métricas, número de serie o nombres
  libres ingresados por usuarios. No consulta Internet automáticamente.
- Identifica claramente la URL como **búsqueda no verificada**, nunca como un vídeo
  específico validado ni un tutorial oficial del fabricante.
- Muestra un botón de apertura manual solo para URL permitidas de búsqueda en
  `www.youtube.com/results?search_query=...` y sin parámetros adicionales.
- Respuestas normales de hardware, diagnóstico y conversación siguen usando el
  adaptador LLM de nube, sujeto a REAL_OR_NA, consentimiento y el filtro existente.
- Los enlaces educativos predeterminados se procesan en el Intelligence Engine
  determinista, sin una solicitud adicional a Groq. Los controles del backend por
  dispositivo siguen vigentes; la cuota del puente sigue contándose por solicitud.
- Cambia "respuesta verificada automáticamente" por "filtrada automáticamente
  (no certifica diagnóstico)"; evita sugerir que el Safety Gate certifica exactitud.

## Prueba en Windows

1. Extraer el ZIP completo en una carpeta nueva.
2. Cerrar el puente Groq anterior; iniciar el puente desde V469 si se usa ese modo.
3. Iniciar `Iniciar_CorePulse.bat`; permitir conexión cloud si aún no estaba configurada.
4. En CorePulse AI, escribir "Dame un tutorial de mantenimiento preventivo".
5. Escribir "un link de youtube". Debe ofrecer una búsqueda de mantenimiento y
   un botón "Abrir búsqueda en YouTube". No asegura que haya un vídeo exacto.
6. Pulsar el botón **solo si se desea** abrir YouTube en el navegador.
7. Pulsar "Limpiar", escribir "un link de youtube": debe pedir tema.
8. Preguntar temperatura CPU: las lecturas faltantes se mantienen en N/A.

## Pruebas automatizadas

`python -m pytest -q tests/test_v46*.py tests/test_v459_cloud_first.py`

Incluye prueba HTTP real de `/v1/chat` contra un servidor FastAPI local, con
vinculación, autenticación y bloqueo de inferencia no deseada para tutoriales públicos.

## Límites

- La ejecución gráfica real debe validarse en Windows: este entorno no tiene display.
- Una búsqueda pública no comprueba la seguridad ni la compatibilidad de sus resultados.
- Las consultas de modelos cloud siguen requiriendo conexión, consentimiento y clave.
- La continuidad del tema es intencionalmente limitada: no se analizan otros chats,
  recuerdos permanentes ni respuestas del modelo para deducir temas de búsqueda.

---

## Documento original: `GUIA_COREPULSE_AI_V470.md`

# CorePulse V470 — Mantenimiento contextual para notebook y CPU

Esta versión continúa el CorePulse principal (Windows), con GPT-OSS 120B remoto por Groq o mediante otro backend compatible; no contiene ni inicia automáticamente un LLM pesado local.

## Corrección observada en V469

En una conversación sobre mantenimiento preventivo y YouTube, al responder «¿y para mi notebook?» o «¿y para mi CPU modelo exacto?» el sistema cambiaba de tema y entregaba una lista de métricas. V470 interpreta estos mensajes como seguimientos **solo cuando** el tema reciente del usuario realmente era mantenimiento/limpieza. Si el usuario cambia de tema (temperatura, consumo, salud, RAM, etc.) no hereda ese tema automáticamente.

## Evidencia e independencia

- El modelo de CPU proviene exclusivamente de `cpu.name` y el del portátil, de `device.model` / `device.display_model` y `device.manufacturer` en la evidencia de **esa consulta**.
- Si falta un modelo exacto, se muestra `N/A`. El fabricante por sí solo no se considera un modelo completo.
- El modelo de CPU no determina el procedimiento de desmontaje del portátil: un desmontaje requiere el modelo exacto del equipo y documentación compatible.
- El servidor forma respuestas educativas con una ruta determinista **propia de CorePulse**, sin pedir una nueva inferencia al LLM, cuando corresponde a estos seguimientos.
- Se crea un enlace de **resultados de búsqueda**, no un vídeo verificado. No se contacta a YouTube al generar la respuesta. Al pulsar el botón, YouTube recibe los términos de búsqueda, incluidos los modelos visibles que se usen en ella. Se advierte esto antes de abrirla.
- No se alteran sensores, temperaturas, reglas `REAL_OR_NA`, FPS ni permisos de Windows. No se realizan acciones de mantenimiento automáticamente.

## Cómo probar en Windows

1. Extraer el ZIP completo a **una carpeta nueva**.
2. Cerrar el puente Groq de la versión anterior (Ctrl+C en su CMD), abrir CorePulse V470 y utilizar el botón «Iniciar puente» de su pestaña AI. La clave de Groq ya guardada en Windows Credential Manager no necesita introducirse en el chat.
3. Autorizar las consultas y vincular el equipo si la aplicación lo solicita.
4. Escribir: «Dame un tutorial de mantenimiento preventivo».
5. Escribir: «Un link de YouTube»; el botón abre **resultados**, no un vídeo que afirmemos haber revisado.
6. Escribir: «¿Y para mi notebook?»; debe aparecer el modelo de notebook real o `N/A`, orientación preventiva y una búsqueda pertinente.
7. Escribir: «¿Y para mi CPU modelo exacto?»; debe citar la CPU recibida o `N/A` y explicar que conocer la CPU **no** basta para desmontar el notebook.
8. Escribir: «¿Qué temperatura tiene mi GPU?»; debe volver a la telemetría del turno sin prolongar el mantenimiento.

## Pruebas y límites

- Pruebas cloud V460–V470: 185 aprobadas (sin conectar al proveedor de IA real).
- Suite general: 236 aprobadas, 20 fallidas, 3 omitidas, 37 subtests aprobados. Los 20 fallos ya ocurrían en V469 (pantallas Tk sin servidor gráfico y contratos visuales antiguos).
- No es una prueba de funcionamiento visual nativa de Windows ni una verificación de calidad de vídeos de YouTube. El modelo remoto y la credencial deben probarse en el equipo del usuario.

---

## Documento original: `GUIA_COREPULSE_AI_V471.md`

# CorePulse V471 — Vinculación persistente del puente Groq

## Qué se observó en el video de V470

1. **Aclaración aportada por el usuario:** el mensaje «Acceso revocado» se debió a que se introdujo incorrectamente el código de vinculación. No hay evidencia de una revocación real ni de que el cambio de versión causara este incidente. En versiones anteriores, la base del puente estaba dentro de cada ZIP; V471 ofrece almacenamiento estable como mejora preventiva separada, no como solución a una causa demostrada.
2. La explicación preventiva funciona, pero un tutorial de mantenimiento físico **no puede ser exacto utilizando únicamente el nombre de la CPU**. Se necesita modelo real de la carcasa, manual o documentación compatible.
3. La URL extensa de búsqueda aparecía en la burbuja: ahora se conserva únicamente el botón al mostrar la conversación.

## Cambios de V471

- El modo Groq en Windows utiliza `%LOCALAPPDATA%\CorePulse\ai_cloud_bridge\corepulse_ai.sqlite3` para sus tokens **hasheados** y códigos de vinculación, incluso al cambiar la carpeta de la aplicación. El archivo del código de CorePulse se puede reemplazar sin reiniciar la identidad del servidor. El proveedor de inferencia sigue siendo Groq y está sujeto a consentimiento; no se inicia un LLM pesado local.
- `12_CREAR_CODIGO_GROQ_V463.bat` y `11_INICIAR_PUENTE_GROQ_V463.bat` seleccionan ambos el modo Groq, para que apunten a **la misma** base persistente.
- Se añadió `GET /v1/session`: consulta autenticada de la vinculación sin enviar telemetría, sin generar texto, sin gastar cuota. La interfaz informa «Falta vincular» cuando el servidor rechaza el token, aunque Windows aún tenga un secreto almacenado.
- Un `401` de sesión se informa como «El puente no reconoce esta vinculación»; no se atribuye sin evidencia a revocación administrativa. Un `403` al canjear código se informa como **código no aceptado** (incorrecto, vencido o utilizado), sin afirmar cuál de esas razones concretas ocurrió.
- Las búsquedas educativas sobre la CPU pueden incluir fabricante/modelo del notebook si lo proporciona la telemetría sanitizada. Los videos **no están verificados** y solo se abre la búsqueda en YouTube mediante un clic del usuario.
- La burbuja oculta la URL cruda de YouTube si cumple la validación estricta del botón.

## Migración desde V470 (una sola vez)

1. Descomprime V471 en una **carpeta nueva**. Cierra la consola del puente V470 (Ctrl+C) antes de iniciar otra para que el puerto `8765` quede libre.
2. Abre CorePulse V471, ve a CorePulse AI y conserva la opción **Groq (pruebas)**. El check de consentimiento es independiente de la vinculación.
3. Inicia el puente V471 desde el botón **Iniciar puente** (o BAT 11). Es normal que V471 necesite **vincularse una vez**: las vinculaciones antiguas permanecían en la base de la carpeta V470 y no se migran automáticamente para evitar leer bases desconocidas.
4. Pulsa **Crear código** (o BAT 12), copia el código temporal **solo en tu equipo**, introdúcelo en el campo del chat y pulsa **Vincular equipo**. Si aparece «Código de vinculación no aceptado», revisa el ingreso y solicita otro código; no es prueba de revocación.
5. Pulsa **Actualizar**. Solo cuando el endpoint de sesión confirma el token mostrará la nube conectada y el vínculo disponible.
6. Prueba «Dame un tutorial de mantenimiento preventivo» y luego «Quiero un tutorial exacto para limpiar mi procesador». Si el modelo real del notebook no se detecta, CorePulse debe pedirlo antes de indicar pasos físicos concretos.

La clave de Groq sigue guardada en Windows Credential Manager, separada del archivo SQLite. **Nunca envíes por chat tu clave API, códigos temporales o tokens de vinculación.**

## Alcance de las pruebas

- Pruebas Python sin acceso a la cuenta real: autenticación, consulta de sesión, persistencia de ruta, contextos de mantenimiento, validación de URL, consentimiento y no emisión de telemetría en la verificación de vínculo.
- No es una validación de la interfaz en Windows real ni certifica tutoriales de YouTube o diagnóstico del hardware.
- Conservar `REAL_OR_NA`, `REAL_FPS_OR_NA_ONLY` y la autorización previa a enviar datos.

---

## Documento original: `GUIA_COREPULSE_AI_V472.md`

# V472 — Independencia del proveedor de inferencia

CorePulse AI conserva sus propias reglas `REAL_OR_NA`, `REAL_FPS_OR_NA_ONLY`, consentimiento, Safety Gate y backend `/v1/chat`. El motor remoto se elige detrás del backend, **sin modificar la telemetría**.

## Opciones existentes

- **Groq**: GPT-OSS 120B mediante `11_INICIAR_PUENTE_GROQ_V463.bat`, en `127.0.0.1:8765`. Sigue siendo el modo probado por el usuario en V466–V471.
- **Modelo alternativo**: un servidor de inferencia OpenAI-compatible **ya existente** bajo `https://.../v1`, con nombre de modelo configurado. Se usa un segundo puente local, `127.0.0.1:8766`, para no reutilizar el token/consentimiento de Groq.
- **Servidor CorePulse propio (futuro)**: también puedes configurar en la interfaz el endpoint HTTPS de un servidor remoto CorePulse que implemente `/v1/status`, `/v1/register`, `/v1/session`, `/v1/chat`. Esto no requiere puente local. **No** introduzcas una URL de API de Groq directamente en el campo «Servidor IA»: ese campo se conecta al backend CorePulse, no al proveedor de inferencia.

## ¿Cómo usar un modelo alternativo en Windows?

1. El modelo alternativo **debe estar alojado previamente** en un proveedor compatible o un servidor GPU administrado por ti. Esta versión no contrata ni despliega GPU.
2. Ejecuta `18_CONFIGURAR_MODELO_COMPATIBLE_V472.bat`: dirección confiable HTTPS finalizada en `/v1`, ID exacto del modelo y API key opcional (oculta, Credential Manager). El archivo JSON guarda **solo URL y nombre**, nunca la clave.
3. Cierra cualquier puente alternativo antiguo que ocupe `8766`; ejecuta `19_INICIAR_PUENTE_COMPATIBLE_V472.bat` y mantén abierta la consola. Si falta configuración, se detiene antes de iniciar.
4. En CorePulse AI selecciona **«Modelo alternativo»**. El cambio de servidor anula el permiso y token anteriores. Marca de nuevo el consentimiento **solo si aceptas enviar preguntas, historial y telemetría al destino remoto configurado**.
5. Ejecuta `20_CREAR_CODIGO_COMPATIBLE_V472.bat`, introduce su código de un uso en CorePulse y pulsa **Vincular equipo**. También puedes pulsar «Crear código» desde el panel tras elegir el modelo alternativo.
6. Consulta `/v1/status` con «Actualizar» y envía una pregunta sintética. `21_PROBAR_MODELO_COMPATIBLE_V472.bat` permite probar el LLM con datos ficticios, previo consentimiento específico en consola.
7. Puedes regresar a Groq seleccionando **Groq (pruebas)**; será necesario volver a autorizar el destino. La conexión cloud requiere Internet, pero el diagnóstico local ligero sigue disponible sin LLM.

## Restricciones y seguridad

- El puente de pruebas solo escucha en `127.0.0.1`. No expongas los puertos `8765` ni `8766` a Internet o a tu red local.
- El puente alternativo solo acepta **HTTPS remoto** (sin credenciales en URL, sin parámetros ni fragmentos; ruta `/v1`). No sigue redirecciones HTTP para evitar filtrar tokens.
- El almacenamiento local de credenciales usa nombres diferentes por proveedor y el puente alternativo guarda sus vinculaciones en un directorio separado bajo `%LOCALAPPDATA%`.
- **Cambiar el proveedor dentro de un mismo puente no está soportado sin reiniciar y vincular de nuevo.** No hay failover automático silencioso: jamás enviar datos a un tercero sin permiso independiente.
- La compatibilidad OpenAI API **no implica igual capacidad o calidad**, ni certifica que el modelo sea apto para CorePulse. Comparar candidatos con el evaluador V462 y verificar hardware/Windows con casos técnicos.
- El endpoint alternativo y la clave se confían explícitamente al propietario del modelo. No introduzcas un endpoint de un tercero desconocido.
- La suite automatizada usa modelos simulados. No se ha probado un segundo proveedor real ni validado visualmente la interfaz de Windows en este entorno.

## Pruebas

`22_VALIDAR_INDEPENDENCIA_V472.bat` ejecuta pruebas offline de URLs, secretos, identidad, separación de puertos, consentimiento y backend HTTP simulado.

---

## Documento original: `GUIA_COREPULSE_AI_V473.md`

# CorePulse V473 — Conexión simple a GPT-OSS 120B en la nube

Esta versión simplifica la **pestaña CorePulse AI**. No altera el motor de diagnóstico ni carga un LLM pesado en el computador.

## Conectar, sin códigos manuales en Groq local

1. **Cierra el CMD** del puente de versiones anteriores y extrae el ZIP V473 en una carpeta nueva.
2. Ejecuta `Iniciar_CorePulse.bat` y abre la pestaña **CorePulse AI**.
3. Marca **«Permito enviar preguntas y datos a Groq»** solo si autorizas transmitir tu mensaje y el contexto técnico usado en las consultas a Groq Cloud. Este permiso se puede retirar desmarcando la casilla.
4. Pulsa **Conectar IA**. Si no hay configuración de servidor, selecciona el puente Groq por defecto. La aplicación inicia el puente ligero si es necesario y, en Windows, puede emitir/canjear un código local de un solo uso automáticamente. Espera a que indique **Conectada**.
5. Escribe **«Hola, CorePulse»** y pulsa Enviar. La inferencia de GPT-OSS 120B ocurre en Groq; no corre localmente.

## Primera configuración (solo si la aplicación lo pide)

Si falta la API key, ejecuta una vez `10_CONFIGURAR_GROQ_V463.bat` desde esta carpeta. Debes generar la clave en tu proyecto de Groq, sin compartirla con nadie. Se guarda en Windows Credential Manager.

Si el puente tarda en iniciar, espera a que la consola CMD muestre que está listo y vuelve a pulsar **Conectar IA**. Si la vinculación automática falla, abre **Configuración avanzada**, pulsa **Crear código** y vincula manualmente.

## Otros servidores

La opción **Modelo alternativo**, servidores HTTPS y los BAT 18–22 permanecen dentro de **Configuración avanzada**. No están incluidos dentro del asistente automático para no emitir códigos administrativos en servidores remotos. La autorización para Groq no se reutiliza en otro proveedor.

## Seguridad y limitaciones

- Sin consentimiento, CorePulse no envía preguntas o sensores a ningún LLM; la comprobación de conexión se hace con estado local autorizado.
- La vinculación automática solo usa el puente Groq de prueba en `127.0.0.1:8765`. Un servidor remoto requiere código de su administrador.
- La ventana CMD del puente debe permanecer abierta. Se usa Python/FastAPI ligero; no se descarga ni ejecuta el modelo GPT-OSS en el PC.
- Si CorePulse AI está apagada, el botón no inicia el servicio. El apagado se controla desde la app.
- REAL_OR_NA, REAL_FPS_OR_NA_ONLY y el Safety Gate permanecen activos.
- Los estados «Conectada» indican disponibilidad de sesión y modelo; **no garantizan precisión diagnóstica**.
- Las pruebas del código no sustituyen una prueba gráfica en Windows; validar que el panel quede ordenado en tu resolución.

## Pruebas técnicas

Ejecutar desde la raíz con Python y pytest disponibles:

```powershell
python -m pytest -q tests/test_v473_simplified_connection.py
```

Se conserva la suite cloud V459–V472. Ninguna prueba requiere una clave Groq real, datos del computador del usuario ni pago.

---

## Documento original: `GUIA_COREPULSE_AI_V474.md`

# CorePulse V474 — Orientación preventiva y protección REAL_OR_NA

Esta versión continúa V473. No requiere una API key nueva, ni cambia Groq o el proveedor alternativo.

## Prueba en Windows

1. Cierra CorePulse y el puente Groq anterior. Extrae el ZIP completo en una carpeta nueva.
2. Ejecuta `Iniciar_CorePulse.bat` y entra a CorePulse AI.
3. Autoriza el envío de preguntas y datos técnicos solamente si quieres usar la nube; presiona **Conectar IA**.
4. Solicita: `Dame un tutorial general de mantenimiento preventivo, paso a paso y sin asumir averías.`
5. Pregunta luego por temperaturas reales: `¿Qué temperatura tienen actualmente mi CPU y GPU?`. No debe inventar lecturas ni clasificar averías.
6. Opcional: selecciona **Configuración avanzada** para comprobar la vinculación; no se requiere para el uso habitual.

## Cambios

- Diferencia estrechamente una concentración explícita de alcohol en una guía educativa de un porcentaje de uso del equipo. Solo en solicitudes educativas se puede mencionar esa concentración sin tratarla como sensor.
- CPU, GPU, RAM, SSD, FPS, temperaturas, URLs y acciones en Windows siguen sujetos a los controles anteriores.
- Si la salida remota contiene datos no verificables, se descarta y se muestra orientación segura; se mejora el estado del chat sin mostrar texto privado rechazado.
- Las guías preventivas de contingencia muestran cada paso en una línea separada.
- Texto de chat un poco más legible, sin modificar las otras pestañas del programa.

## Limitaciones

- No se dispone de la respuesta privada rechazada en la grabación de V473, por lo que esta corrección no demuestra cuál fue el código preciso de aquel rechazo.
- No se han realizado pruebas con la API key del usuario ni validación visual nativa de Windows en este entorno.
- Las reglas de seguridad no sustituyen una evaluación profesional ni garantizan precisión perfecta. El servidor remoto sigue siendo proveedor de la inferencia.

---

## Documento original: `GUIA_COREPULSE_AI_V475.md`

# CorePulse AI V475 · Intelligence Engine

Esta versión introduce un motor técnico propio y **sin modelo local pesado**; la conversación en la nube permanece conectada a GPT-OSS 120B por Groq, con el proveedor alternativo disponible.

## Uso normal en Windows

1. Cierra el puente Groq de la versión anterior y descomprime el ZIP completo en otra carpeta.
2. Ejecuta `Iniciar_CorePulse.bat` y abre **CorePulse AI**.
3. Si estás de acuerdo en enviar preguntas y telemetría al proveedor, marca el consentimiento y pulsa **Conectar IA**.
4. Escribe «Analiza mi equipo y dime qué debo comprobar».
5. Para probar el motor sin red ni claves ejecuta `23_VALIDAR_INTELIGENCIA_V475.bat`. Esta prueba emplea exclusivamente datos sintéticos.

## Qué hace realmente

- Reúne observaciones existentes con el nombre de cada fuente, sin crear sensores ni FPS.
- Acepta alertas térmicas sólo cuando el diagnóstico determinista de CorePulse las indica; un valor aislado no implica una falla.
- Diferencia presión de RAM de daño físico, y uso de SSD de salud SMART.
- Entrega hipótesis **no confirmadas** y comprobaciones seguras para investigar los problemas.
- Si se solicita un diagnóstico y el modelo falla o inventa una cifra, utiliza el informe determinista como respuesta de contingencia.
- Las respuestas API (`/v1/chat`, `/v1/analyze`) llevan también un campo estructurado `intelligence`; para el chat Windows el texto sigue llegando por `text`.

## Límites

- No hay prueba física en Windows ni ensayo con tu cuenta Groq en este entorno.
- No identifica averías reales sólo por correlación de un único instante; requiere mediciones longitudinales y registros adicionales.
- No valida por sí mismo la edad de cada sensor. La fuente original debe asegurar la frescura.
- No efectúa cambios automáticos en Windows; las recomendaciones son informativas.
- El servidor cloud externo solo recibe telemetría cuando el usuario ha autorizado el envío; el motor no inicia tráfico por su cuenta.
