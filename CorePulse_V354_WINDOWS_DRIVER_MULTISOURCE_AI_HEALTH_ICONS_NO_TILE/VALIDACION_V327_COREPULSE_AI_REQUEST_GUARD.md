# Validación V327 — CorePulse AI Request Guard

- Base: V326.
- Caso reproducido desde video: el backend recibió múltiples `POST /v1/analyze` y alcanzó HTTP 429 tras 20 solicitudes.
- Corrección cliente: guardia de 1.25 s, solicitud única activa y descarte de respuestas obsoletas.
- Corrección servidor V1.1: deduplicación temporal por token + contexto + pregunta; duplicados no consumen cuota.
- Límite local predeterminado elevado de 20 a 200, configurable por entorno.
- REAL_OR_NA intacto.
