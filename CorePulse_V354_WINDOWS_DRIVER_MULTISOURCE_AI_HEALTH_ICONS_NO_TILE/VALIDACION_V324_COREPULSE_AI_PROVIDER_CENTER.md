# Validación V324 — CorePulse AI Provider Center

## Objetivo
Agregar una capa de IA utilizable por cualquier usuario sin convertir la IA en autoridad técnica.

## Proveedores
- Automático: OpenAI -> Groq -> IA local.
- OpenAI: Responses API.
- Groq: compatibilidad con la integración existente.
- IA local: endpoint Ollama `127.0.0.1:11434`.

## Seguridad
- API keys en Windows Credential Manager.
- `ai_settings.json` contiene solo preferencias no secretas.
- El contexto enviado elimina seriales y se limita a telemetría relevante.

## Política
- CorePulse mide y clasifica.
- La IA explica.
- REAL_OR_NA permanece intacto.
- La IA no modifica Windows ni inventa sensores.
