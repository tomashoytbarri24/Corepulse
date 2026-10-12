> **V462:** antes de elegir modelo o GPU, ejecutar los 30 casos sintéticos del [laboratorio V462](../GUIA_COREPULSE_AI_V462.md) contra cada servidor candidato; no confundir pruebas de corpus offline con inferencia. Mantener métricas `/metrics` de vLLM solo en la red de inferencia.

# CorePulse AI Cloud V460 — despliegue privado de referencia

**Estado:** componentes y pruebas de software listos; **NO está desplegado** ni se incluye GPU, dominio o servidor remoto. Solo usar en piloto privado controlado. Este despliegue NO está certificado como producción abierta al público.

## Requisitos

- Servidor **Linux** con GPU NVIDIA admitida por el modelo, controladores CUDA/NVIDIA Container Toolkit y Docker Compose moderno; el cliente CorePulse sigue funcionando en **Windows**.
- DNS del dominio apuntando al servidor. TCP 80 y 443 accesibles para TLS automático de Caddy.
- Memoria de GPU adecuada para modelo, KV cache y concurrencia. Verificar antes de contratar recursos. El modelo `Qwen/Qwen3-8B` aquí es sólo **ejemplo reemplazable**.
- Acceso administrativo seguro para emitir y revocar códigos. No compartir `.env` ni abrir el host vLLM directamente.

## Arranque de piloto

1. En el servidor copiar esta carpeta y `CorePulse_AI_Server` en rutas hermanas como en el ZIP.
2. `cp .env.example .env`; definir `COREPULSE_CLOUD_DOMAIN` y una clave `COREPULSE_MODEL_API_KEY` aleatoria distinta. `chmod 600 .env`.
3. Elegir modelo y comprobar **licencia de uso, hardware y tamaño**. Para desplegar en serio, fijar versiones o digest de contenedores tras probarlos; no dejar `latest`.
4. `docker compose --env-file .env config` para revisar configuración sin iniciar contenedores (no compartir la salida: contiene secretos).
5. `docker compose --env-file .env up -d --build`.
6. Comprobar `https://TU_DOMINIO/v1/status` desde una máquina independiente. `model_ready=true` solo cuando el servicio compruebe el host de inferencia; no implica calidad diagnóstica.
7. Emitir un **código de un solo uso** en el servidor (no es una API pública):
   `docker compose exec api python -m app.admin issue --minutes 30`
8. En CorePulse Windows V460, pegar `https://TU_DOMINIO`, guardar, introducir el código y pulsar **Guardar código**; habilitar la casilla de consentimiento; realizar una consulta. La primera consulta registra el equipo; el código se consume, el token exclusivo del equipo se guarda en Credential Manager.
9. Revocar un dispositivo cuando sea necesario:
   `docker compose exec api python -m app.admin list`
   `docker compose exec api python -m app.admin revoke ID_DEL_DISPOSITIVO`

**Red:** el proxy Caddy expone 443 (y 80 para TLS). FastAPI (`api:8765`) y vLLM (`model:8000`) se mantienen en redes Docker sin puertos publicados. No habilitar `ports` en `api` o `model` ni confiar en la `--api-key` de vLLM como única protección: versiones actuales exponen rutas de inferencia adicionales fuera de `/v1`.

**Privacidad:** no se guardan historiales ni telemetría en el SQLite de CorePulse AI; se conservan hashes de credenciales, IDs de instalación y recuentos de cuota. El servidor procesa preguntas/contexto en memoria y envía al modelo por red privada Docker. No adjuntar contenido de prompts en logs y limitar acceso a backups. Antes de abrir a usuarios reales faltan políticas de retención, cuentas, auditoría independiente, alertas, antifraude y pruebas de seguridad. Consentimiento explícito en Windows obligatorio.

**Límites:** sin Internet no hay chat en nube; CorePulse continúa con telemetría y diagnóstico local sin ejecutar LLM pesado. No hay facturación, automatización de operaciones sobre Windows ni proveedor externo configurado por defecto. La calidad clínica/técnica de las respuestas del LLM todavía requiere evaluación humana con casos de prueba.
