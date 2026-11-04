> **REBUILD 127 (cliente Windows):** este Worker es exactamente el de REBUILD 126. No se necesita redesplegarlo ni modificar secretos/DNS. La aplicación ahora usa `https://ai.corepulse.cl` por defecto, sin variable de entorno ni clave del usuario; el proveedor Groq existente sigue exclusivamente en el servidor hasta una futura migración verificada.

# REBUILD 126 — Dictamen completo en una llamada y fuentes legibles

El Worker devuelve `answer` (resumen) y `details` (dictamen verificado) en **la misma respuesta** para una comparación válida de sesiones; `assessmentStatus` describe la cobertura o recurrencia calculada por reglas. La interfaz expande el detalle localmente, sin otra consulta ni gasto de tokens. Los títulos y enlaces oficiales van en `sources` para mostrarse en una sección separada. No cambia la autenticación, las cuotas ni el nombre del Worker.

# REBUILD 125 — Resumen verificable y análisis completo opcional

- Para consultas sobre recurrencia entre arranques, `POST /v1/chat` conserva `answer`, `assessmentEngine`, `sources` y `knowledgeVersion`. El valor `answer` ahora contiene un resumen con prioridades, no todas las filas del dictamen. Un usuario puede solicitar **en detalle la comparación entre sesiones** para ver el dictamen íntegro de V124.
- Ambos modos usan exclusivamente `safeSessionComparison` y `analyzeSessionComparison`; no se añaden contadores personales ni se aceptan fechas, IDs, muestras o direcciones. La información solo llega desde el cliente tras permisos y una consulta explícita. No hay llamada adicional en segundo plano.
- Las recomendaciones breves son estáticas y conservadoras: revisar refrigeración/uso, RAM, estado del SSD y batería según los eventos verificados; una advertencia histórica de batería jamás indica automáticamente desgaste o falla de carga.
- La clasificación es independiente de Groq. Si el presupuesto no permite llamar al modelo, se devuelve el resumen propio. Pedir detalles manualmente puede consumir una consulta si el proveedor está disponible; no crea cambios automáticos en Windows.
- Despliegue: desde esta carpeta, `npm.cmd install`, `npm.cmd run verify`, `npm.cmd audit`, revisar sus resultados y después `npx.cmd wrangler deploy`. Worker `corepulse-ai-cloud` y dominio `ai.corepulse.cl` existentes; no regenerar secretos.
- **V125:** pruebas locales 58/58 cloud, más prueba específica del cliente Windows; la integración y el servicio público reales requieren validación. IA estimada **78 %**.

---

# REBUILD 124 — Conclusión propia y explicación subordinada

- `POST /v1/chat` conserva el mismo contrato. Para **preguntas explícitas** entre sesiones con contadores agregados autorizados y válidos, la API ahora devuelve `answer` con texto verificable redactado por el propio Worker (`assessmentEngine: corepulse-rules-v2`), evitando mostrar categorías internas. Groq solo puede añadir un consejo general bajo filtros estrictos.
- El dictamen reconoce episodios sostenidos, eventos en una sola sesión, picos térmicos no sostenidos, cobertura insuficiente y huecos sin datos. Un valor RAM de 87 % nunca cumple el criterio de 90 % por 5 minutos, y no se presume continuidad sin muestras.
- Si Groq no responde o se agotó su presupuesto, una comparación ya evaluada puede devolver el dictamen sin el consejo generativo. Sigue exigiendo autenticación, límites de solicitudes y consentimiento previo en Windows; otras preguntas mantienen el manejo habitual de errores.
- Documentos oficiales de RAG seleccionados por problemas efectivamente presentes. No se afirma haber obtenido límites oficiales de temperatura a partir de porcentajes ni se envían datos históricos crudos.
- **Para desplegar**, en PowerShell desde esta carpeta: `npm.cmd install`, `npm.cmd run verify`, `npm.cmd audit`, `npx.cmd wrangler whoami`, `npx.cmd wrangler deploy` (solo si las pruebas y auditoría son aceptables). No usar `secret put` de nuevo, no subir tokens ni crear un Worker nuevo.
- Despliegue y prueba de conversación real de V124 pendientes; si no despliegas, `ai.corepulse.cl` sigue atendiendo con V123.

---

# REBUILD 123 — Comparación intersesiones con evidencia agregada

- La API acepta de forma aditiva `sessionComparison` en `POST /v1/chat` únicamente si la pregunta solicita comparar sesiones. La aplicación Windows obtiene los contadores de hasta cuatro arranques, localmente y bajo el permiso independiente de Tendencias.
- El Worker valida esquema y rangos, filtra las claves adicionales y vuelve a clasificar la recurrencia (`analyzeSessionComparison`) sin depender de Groq para decidir si un hallazgo se repitió. No guarda datos personales ni fechas ni nombres de usuario.
- Denominadores independientes: solo sesiones con mediciones verificables de un componente se consideran evaluadas. Los umbrales son **preventivos**, no límites térmicos garantizados; sin datos o con una sola sesión, no se afirma recurrencia.
- Se conserva compatibilidad con el protocolo V122: `sessionSummary` para una sola sesión, fuentes del catálogo, contraseñas exclusivamente del servidor, identidad, cuotas, RAG, modelo y URLs.
- Validar: `npm.cmd install`, `npm.cmd run verify`, `npm.cmd audit`, luego `npx.cmd wrangler deploy` si la auditoría está limpia. No recrear Worker, DNS ni secreto Groq. El despliegue y la conversación real requieren validación en Cloudflare y Windows.

# Actualización REBUILD 122 — RAG térmico y permiso independiente de Tendencias

**Base:** REBUILD 121 completa. Mismo Worker `corepulse-ai-cloud`, `ai.corepulse.cl`, GPT-OSS 120B vía Groq y las cuotas existentes. Los archivos siguientes contienen el historial de cambios de versiones anteriores.

- El catálogo `src/knowledge.mjs` utiliza versión `corepulse-kb-v3`. Se ha incorporado una fuente técnica oficial NVIDIA y ampliado el reconocimiento de consultas térmicas en CPU/GPU (incluidas las formas «sobrecalentando», «grados» y «°C»). Intel, AMD y NVIDIA solo se citan cuando corresponde al fabricante y componente detectado. No equivale a consulta web actualizada ni a certificado de daño.
- La aplicación Windows incorpora un **tercer permiso independiente, apagado por defecto**, para enviar únicamente un resumen de la sesión seleccionada en Tendencias. Requiere consentimiento de preguntas y lecturas, modo Cloud y pregunta explícita sobre historial, sesión o duración. Apagar IA, cambiar proveedor o retirar permisos lo desactiva.
- El resumen se calcula localmente y contiene únicamente contadores, picos y rachas de lecturas consecutivas observadas (máximo 95 segundos entre lecturas), y si existieron alertas verificadas de batería o almacenamiento. No envía muestras crudas, fechas exactas, nombres, ID de Windows, rutas, identificadores de discos ni chats históricos de Tendencias. Una pausa sin mediciones jamás equivale a salud normal.
- El servidor valida una lista blanca cerrada y trata el agregado como dato aportado por el cliente, no como verificación independiente del Worker. No se almacenan conversaciones en el código cloud. Las cuotas siguen contando una consulta por petición generativa; no hay búsqueda web ni embeddings.
- Los resultados del proveedor llegan al usuario por CorePulse; los enlaces documentales del catálogo se filtran localmente. No se altera el sistema operativo ni se activa ningún permiso en nombre del usuario.

**Pruebas locales (antes de publicar):** con Node.js 22+ y Wrangler instalado: `npm.cmd install`, `npm.cmd run verify` y `npm.cmd audit`. Revisar alertas de auditoría antes de desplegar. Si todo está correcto, `npx.cmd wrangler whoami` y `npx.cmd wrangler deploy` desde esta carpeta. No recrear Worker ni claves; Cloudflare sigue ejecutando V121 hasta desplegar V122. Probar en Windows con `COREPULSE_AI_CLOUD_URL=https://ai.corepulse.cl`. Para Tendencias, seleccionar una sesión, activar el nuevo permiso y preguntar «¿Cómo estuvo la RAM durante esta sesión?». Los resultados en producción requieren validación del usuario.

**Avance de CorePulse AI:** V121 61 % → V122 65 % estimado en código, pendiente comprobación real en Cloudflare/Windows. Groq sigue siendo el proveedor de inferencia, no el dueño de nuestro sistema ni un modelo entrenado por CorePulse.

---

# Actualización REBUILD 121 — RAG térmico y respuestas sin cortes

Base: V120 íntegra, Worker `corepulse-ai-cloud` existente. Se mantiene `ai.corepulse.cl`, su Durable Object, las cuotas y el secreto del servidor. No crear recursos nuevos.

- `src/knowledge.mjs` contiene ahora nueve documentos curados (Microsoft, Intel y AMD), con dos fichas nuevas sobre temperatura de portátiles Intel y CPU AMD. El catálogo estático se recupera temáticamente (máximo tres fichas). Un porcentaje de uso documentado por Microsoft no respalda por sí mismo una conclusión térmica. El código no descarga páginas web durante las preguntas.
- El servidor trata las lecturas como **instantáneas**, sin asumir reposo ni duración. Las advertencias de uso de RAM o calor elevado siguen siendo observaciones preventivas, no confirmaciones de avería.
- Se permite un máximo de 2000 tokens de finalización (incluidos los tokens de razonamiento del proveedor) y se solicita una respuesta breve. Cuando el proveedor señala `finish_reason=length`, se evita publicar una conclusión recortada; aparece un aviso completo. No se reintenta automáticamente ni se duplican llamadas. **Este nuevo máximo puede aumentar el consumo de tokens y su costo**; las cuotas de peticiones existentes no sustituyen un presupuesto monetario.
- En Windows, las fuentes de `www.amd.com` son válidas; no se recorta la respuesta para insertar enlaces. La V121 no envía muestras históricas ni cambia el consentimiento de telemetría.

Desde la raíz `CorePulse_REBUILD_121`:

```powershell
cd .\cloud\corepulse-ai
npm.cmd install
npm.cmd run verify
npm.cmd audit
# Solo si las pruebas pasan y la auditoría no presenta problemas sin revisar:
npx.cmd wrangler whoami
npx.cmd wrangler deploy
```

**No volver a crear el dominio, ni introducir ni compartir la clave.** Si `wrangler whoami` no está autenticado, ejecutar `npx.cmd wrangler login`. Las pruebas Node son simuladas; después del despliegue hay que probar la respuesta real desde CorePulse Windows con el consentimiento pertinente. No se ha realizado este despliegue en la cuenta del usuario.

**Avance CorePulse AI:** V120 comprobada 58 % → V121 implementada 61 % estimado; pendiente validación del Worker y cliente Windows.

---

# Actualización REBUILD 119 — Instalación y verificación multiplataforma

La REBUILD 118 falló en PowerShell porque `node --test test/*.test.mjs` dependía de expansión de comodines. Esta versión llama explícitamente los dos archivos de pruebas y fija Wrangler `4.151.1` (no se añade dependencia al Worker desplegado).

```powershell
cd .\cloud\corepulse-ai  # desde la raíz de CorePulse_REBUILD_119
npm.cmd install
npm.cmd run verify
npm.cmd audit
# Si hay alertas altas, revisar el detalle antes de continuar.
# Si la auditoría es aceptable y las pruebas pasan:
npx.cmd wrangler whoami
npx.cmd wrangler deploy
```

**Si audit detecta vulnerabilidades:** guardar el informe, examinar cadenas de dependencias y severidad; no ejecutar `npm audit fix --force` a ciegas. No se ha podido descargar npm en el entorno de preparación para certificar un resultado de auditoría. Una advertencia no significa automáticamente que el Worker publicado contenga un componente vulnerable: Wrangler es una herramienta de desarrollo; revisar igualmente las dependencias.

`wrangler deploy` solo se considera completado cuando indica `Deployed ...` junto al dominio `ai.corepulse.cl` y un `Current Version ID`. Si aparece la autorización OAuth, completarla en el navegador del dueño de la cuenta y esperar la confirmación. No repetir `secret put`; la clave revocada del chat previo no debe reutilizarse. El Worker V117 seguirá publicado hasta desplegar V119.

**Avance CorePulse AI:** 54 % estimado, sin incremento por corregir empaquetado/verificación.

---

# CorePulse AI Cloud — Knowledge Engine v1 (REBUILD 118)

A partir de la V117 ya publicada y comprobada en un equipo Windows, la V118 agrega un **RAG inicial de recuperación léxica sobre documentación curada**. El código vive en `src/knowledge.mjs`, sin usar vector databases, scraping web ni claves nuevas. Siete entradas con identificador y URL de Microsoft/Intel verificadas manualmente; no son sensores, diagnósticos certificados ni citas live de páginas. Para sumar fichas, revisar manualmente enlace, alcance y resumen y agregar pruebas. No indexar datos personales o inventarios de usuarios.

**Consulta y funcionamiento:** el Worker recupera hasta 3 fichas según el tema de la pregunta y los avisos del diagnóstico, limita la selección de Intel cuando el CPU es AMD/desconocido, agrega resúmenes al contexto controlado por servidor y devuelve `knowledgeVersion` y `sources` junto a `answer`. La app Windows solo muestra URLs HTTPS oficiales de Microsoft/Intel; las citas son referencia temática, no evidencia de temperaturas/SMART. Sin referencias, `sources=[]`. Los mensajes de usuario no se indexan ni se guardan en la nube por este módulo.

**Actualizar desde PowerShell en esta carpeta:**

```powershell
npm.cmd install
npm.cmd run verify
npx.cmd wrangler whoami
npx.cmd wrangler deploy
```

**No volver a crear `GROQ_API_KEY`, otro dominio ni otro Durable Object.** El Worker publicado sigue ejecutando V117 hasta que el usuario despliegue V118. Luego abrir Windows V118 con `COREPULSE_AI_CLOUD_URL=https://ai.corepulse.cl`, iniciar sesión y comprobar una pregunta específica sobre RAM/CPU/SSD. No mostrar tokens ni secretos. `GET /v1/health` comprueba servicio, pero no el RAG ni el modelo; se necesita una conversación autenticada para validarlos.

**Límites de esta etapa:** RAG básico con fichas estáticas; no búsqueda web al momento de responder, sin índice vectorial, revisión automática de cambios en documentación o citas alineadas con cada frase generada. Groq/GPT-OSS 120B sigue siendo el motor generativo reemplazable. Avance total de CorePulse AI estimado: **54 %**, sin acreditar aún un despliegue de V118.

---

# REBUILD 117 — Corrección del presupuesto Cloudflare ya publicado

El Worker `corepulse-ai-cloud` ya fue desplegado por el usuario y `GET /v1/health` devolvió 200 y `/v1/status` sin token devolvió 401. En Windows, el chat de V116 mostró `model_budget_unavailable` (503). La primera reserva fallaba porque el código llamaba `.one()` sobre un contador SQLite todavía ausente: Cloudflare lanza excepción si la consulta tiene 0 filas. V117 utiliza `toArray()[0]` y conserva transacción y topes.

**Actualizar solo el Worker** desde PowerShell, en esta carpeta:

```powershell
npm.cmd run verify
npx.cmd wrangler whoami
npx.cmd wrangler deploy
```

No ejecutar `secret put` de nuevo ni enviar claves a nadie. Revisar que aparezca `corepulse-ai-cloud` y `ai.corepulse.cl`; no crear otro Worker. La V116 de Windows puede continuar abierta y reconectarse, o iniciarse de nuevo. `GET /v1/health` no comprueba las cuotas: la prueba decisiva es enviar una pregunta al chat autenticado y recibir respuesta. Si falla, revisar mensajes conocidos y `npx.cmd wrangler tail` sin mostrar tokens ni información personal en capturas.

**Estado:** corrección comprobada con pruebas simuladas de Cloudflare SQLite; Worker de V117 no desplegado aquí y Groq no probado en vivo. Progreso total estimado de IA: 45 %.

---

# CorePulse AI Cloud — motor propio y presupuesto central (REBUILD 114)

Servicio independiente de la aplicación Windows, preparado para Cloudflare Workers. El cliente utiliza `/v1/status` y `/v1/chat`; también se incorpora `/v1/analyze` para obtener observaciones basadas en reglas sin llamar a Groq. La clave de Groq permanece **solo en el Worker**. El modelo conversacional aún es GPT-OSS 120B mediante Groq; no hay RAG, inferencia propia ni modelo alojado por CorePulse en esta versión.

## Antes de desplegar

1. Verifica que la cuenta web `corepulse.cl` ya responda `GET /api/app/yo` con **HTTP 200 y `{"perfil":{...}}` únicamente para tokens de dispositivo válidos**; todo token inválido debe recibir HTTP 401/403. El Worker rechaza solicitudes si no logra comprobar ese token.
2. Comprueba que el dominio `corepulse.cl` esté administrado en tu cuenta de Cloudflare. `wrangler.jsonc` ahora usa un **Custom Domain** `ai.corepulse.cl`, que Cloudflare puede asociar al Worker dentro de tu zona. Verifica que no existan rutas/DNS incompatibles antes de publicar. **No se despliega nada automáticamente.**
3. En esta carpeta: `npm install`, `npm run verify` (Node.js 22+ para la prueba SQLite), `npx wrangler login`, `npx wrangler whoami`, `npx wrangler secret put GROQ_API_KEY`, y `npm run deploy`. La migración `v1-model-budget` creará el Durable Object SQLite automáticamente en el primer despliegue cuando Cloudflare lo permita.
4. Comprueba `GET https://ai.corepulse.cl/v1/health` (solo confirma que el Worker responde), y con **tu token de prueba de dispositivo** prueba `GET /v1/status` (HTTP 200), `POST /v1/analyze` y `POST /v1/chat`. Nunca publiques el token en capturas, logs ni comandos compartidos.
5. En el equipo Windows configura `COREPULSE_AI_CLOUD_URL=https://ai.corepulse.cl` y reinicia CorePulse. En CorePulse AI, inicia sesión con tu cuenta, acepta cada permiso por separado y conecta. Si no existe esa variable, seguirá disponible la integración anterior con Groq y clave propia.

## Seguridad y privacidad

- Cada consulta pasa por `/api/app/yo`; no se confía en el `userId` que envíe el cliente.
- El Worker no guarda conversaciones, IP ni telemetría en bases de datos; la plataforma o proveedores externos podrían registrar metadatos según sus propias políticas. No hay retención persistente controlada por este Worker.
- El Worker no recibe la clave personal de Groq del usuario. La `GROQ_API_KEY` del servicio se define como **secreto de Cloudflare**, no en `wrangler.jsonc`, el ZIP ni código fuente.
- Datos del hardware: sin permiso, `{}`. Con permiso, solo nombres acotados y CPU/GPU/RAM/ocupación, sin identificadores, rutas o números de serie. Los campos no válidos pasan a N/A. El diagnóstico se envía solo al autorizar compartir lecturas.
- La política de seguridad de CorePulse reside en el servidor; nunca se aceptan mensajes de tipo `system` del cliente.
- El límite de 8 consultas/minuto/usuario es **aproximado y por ubicación de Cloudflare**, no un presupuesto económico fiable. La V114 incorpora una cuota global y diaria por cuenta con un Durable Object SQLite; **no mide dinero ni tokens**. Siguen pendientes alertas de gasto real, facturación del proveedor, observabilidad sin datos sensibles, gestión de cuentas, revocación y política de privacidad.
- Para que la nube no exponga tokens a dominios arbitrarios, el cliente solo permite `https://ai.corepulse.cl` (en desarrollo se puede optar explícitamente por loopback HTTP con `COREPULSE_AI_DEV=1`). Nunca habilites esa opción en usuarios finales.
- `npm test` verifica autentificación, límites y filtrado **con respuestas simuladas**, sin gastar tokens.

## Limitaciones históricas de REBUILD 114

No se ha desplegado ni probado en Windows contra un Worker real. No hay RAG ni búsqueda web automatizada, herramienta de gestión de costos, razonamiento propietario entrenado ni independencia total del modelo. Esta entrega establece un backend administrable y la separación segura del cliente.

## REBUILD 113 — diagnóstico preliminar independiente del LLM

La API ofrece `POST /v1/analyze` con un cuerpo JSON de ejemplo:

```json
{"kind":"snapshot","snapshot":{"cpuTemp":81.5,"gpuTemp":73,"ramPercent":93,"diskPercent":54}}
```

El endpoint exige un token de dispositivo autorizado mediante `corepulse.cl/api/app/yo` y el mismo límite de frecuencia que el chat, pero **no requiere ni consume Groq**. En ausencia de `GROQ_API_KEY`, solo esta ruta puede funcionar si la cuenta y RATE_LIMITER están configurados; `/v1/chat` continúa deshabilitado. No se necesita inventar información: los datos incompletos se consideran desconocidos.

Reglas orientativas iniciales sobre **una lectura puntual**: CPU ≥90 °C, GPU ≥85 °C, RAM ≥90 % y ocupación del disco ≥95 %. Se devuelven observaciones y recomendaciones, **no diagnósticos de avería**, persistencia, batería o salud SMART. En chat, los mismos hallazgos se calculan por el Worker antes de consultar Groq, como contexto adicional; el proveedor sigue siendo responsable de redactar la respuesta.

## Comprobar antes del despliegue

Desde PowerShell en `cloud/corepulse-ai`:

```powershell
npm install
npm run verify
npx wrangler login
npx wrangler whoami
npx wrangler secret put GROQ_API_KEY
npx wrangler deploy
```

`wrangler login` debe ejecutarlo el propietario de la cuenta en su equipo. Nunca compartas en un chat la clave Groq, el token de Cloudflare ni el token de CorePulse. Si la sesión en Cloudflare, el dominio o el secreto no están listos, **no se debe anunciar que el servicio está publicado**. Tras desplegar, revisar `https://ai.corepulse.cl/v1/health`, realizar una prueba autenticada desde la app Windows y verificar consentimiento y respuesta real. La ruta pública de salud **no** demuestra que funcionen el proveedor ni la autenticación.

Documentación oficial: https://developers.cloudflare.com/workers/wrangler/configuration/ y https://developers.cloudflare.com/workers/runtime-apis/bindings/rate-limit/.

## Progreso de CorePulse AI (estimación de ingeniería)

- V111: ~30 % — chat/diagnóstico integrado, pero sin API propia.
- V112: ~35 % — API y transporte separados, todavía sin despliegue real.
- **V113: ~38 %** — primera evaluación determinista del servidor, ruta sin Groq y pruebas adicionales.
- **V114: ~42 %** — límite centralizado persistente para consultas generativas; despliegue y gastos reales sin validar. **Alojamiento en producción: 0 % verificado**.

El porcentaje es orientativo, no una cobertura automática de pruebas. Pendientes críticos: desplegar con cuenta real, autenticación extremo a extremo, gestión de presupuesto por usuario/servicio, base de conocimiento con fuentes, RAG y validaciones contra equipos reales.

## REBUILD 114 — límites conservadores de consultas del modelo

- `MODEL_BUDGET` es un **Durable Object de Cloudflare con SQLite** creado con la migración `v1-model-budget` incluida en `wrangler.jsonc` (Workers Free solo admite Durable Objects SQLite). No se requiere otra cuenta ni comprar un dominio nuevo si `corepulse.cl` ya es una zona activa y administrada en Cloudflare.
- El presupuesto inicial del piloto está fijado en `src/index.mjs` y es común a todos los clientes: **20 consultas generativas diarias por cuenta** (si el servidor web aporta `perfil.id`; si no, por token), **250 consultas generativas diarias en total** y **3000 mensuales en total**. Los períodos se reinician en **UTC**. Se usan claves hash, no se guarda el texto de chats, tokens ni contraseñas en el contador.
- Los tres límites se revisan y actualizan en una **transacción SQLite** antes de llamar a Groq. Si se agotó un límite, `POST /v1/chat` responde `429` sin contactar al modelo. Si el almacén no responde o no está configurado, responde `503` y **no utiliza** Groq. `POST /v1/analyze` sigue funcionando mediante reglas locales del servidor y no consume presupuesto del modelo.
- Cada petición generativa reserva **una llamada** (no tokens ni costo en USD/CLP). Una reserva no se reintegra si falla Groq, para evitar gastar por encima del presupuesto. Estos límites **no garantizan un monto máximo facturado**: la longitud de entrada, precio del modelo y otros servicios pueden variar. Configurar alertas y topes monetarios también en el proveedor antes de abrirlo a usuarios.
- `GET /v1/health` solo indica que el Worker responde; `/v1/status` no verifica cupo restante. Ninguno demuestra que el sistema de pagos, el dominio o la cuenta estén integrados en producción.
- **Despliegue pendiente:** ejecutar `npm install`, `npm run verify`, `npx wrangler login`, `npx wrangler secret put GROQ_API_KEY`, `npx wrangler deploy`, verificar DNS/HTTPS y probar cuenta real con consentimiento en Windows. Los comandos NO se han ejecutado sobre la cuenta del usuario. No subir `.dev.vars` ni secretos al repositorio.
- **Pruebas:** 21 tests JavaScript, incluida persistencia de SQLite, bloqueo por cuenta y cuota global, y ausencia de llamadas a Groq si no hay cupo. Son tests en Node con simulaciones del Worker y SQL de Node, **no son pruebas de integración real con Cloudflare**.
