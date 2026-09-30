# Validación V328 — CorePulse AI Generative Chat

- Base: V327.
- Nuevo endpoint conversacional `/v1/chat` con historial limitado y no persistente.
- El cliente envía en cada turno evidencia REAL_OR_NA actual; la evidencia actual tiene prioridad sobre el historial.
- CorePulse AI Server V1.2 soporta un host generativo privado OpenAI-compatible y mantiene Evidence Engine como degradación segura.
- Estado del servicio distingue modelo configurado y host realmente alcanzable.
- UI de CorePulse AI pasa de respuesta única a conversación y admite Enter, limpiar conversación y análisis del equipo.
- Sin OpenAI/Groq SDK ni claves del usuario dentro de CorePulse Desktop.
- Sin Ollama.
