# CorePulse AI Server V1.3

Backend propio de CorePulse AI. El cliente de escritorio nunca necesita una API key de un proveedor.

## V1.3

- Salida en texto plano para el panel de CorePulse; se eliminan marcadores Markdown residuales.
- El prompt impide que el modelo aumente o reduzca por su cuenta la severidad definida por CorePulse.
- Respuestas más breves y menos repetitivas; cambios de BIOS/voltajes no se sugieren salvo petición explícita.


## Flujo

CorePulse -> CorePulse AI Server (8765) -> host de modelo privado (8766 en desarrollo).

El servidor vuelve a sanitizar la evidencia `REAL_OR_NA`, autentica cada instalación, aplica cuota y sólo después consulta el modelo generativo. Si el host generativo no está disponible, conserva el Evidence Engine como degradación segura.

## Ejecutar

1. Instala las dependencias: `python -m pip install -r requirements.txt`
2. Opcional: copia `.env.example` como `.env`.
3. Ejecuta `Iniciar_CorePulse_AI_Server.bat`.
4. Estado: `http://127.0.0.1:8765/v1/status`.

## Modelo generativo

V1.2 espera un endpoint OpenAI-compatible en `COREPULSE_MODEL_BASE_URL`. Para desarrollo se dejó preparado `http://127.0.0.1:8766/v1`. Puede usarse el paquete separado **CorePulse AI Model Host V1**, basado en llama.cpp; no usa Ollama.

En producción, el modelo se ejecutaría en infraestructura de CorePulse y los usuarios finales sólo se conectarían a `api.corepulse.ai`.

## Endpoints

- `GET /v1/status`
- `POST /v1/register`
- `POST /v1/analyze`
- `POST /v1/chat`

El historial de chat llega sólo en la solicitud actual; V1.2 no persiste conversaciones en la base SQLite.
