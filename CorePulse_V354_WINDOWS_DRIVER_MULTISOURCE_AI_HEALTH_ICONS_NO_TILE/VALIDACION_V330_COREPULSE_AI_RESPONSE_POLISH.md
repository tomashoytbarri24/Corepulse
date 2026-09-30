# Validación V330 — CorePulse AI Response Polish

## Objetivo
Pulir la salida observada en la prueba real de V329 sin alterar telemetría ni clasificación técnica.

## Cambios
- Respuestas visibles en texto plano, sin `**`, encabezados Markdown ni bloques de código.
- La IA debe conservar la severidad y el wording técnico de CorePulse en lugar de intensificarlo.
- Consejos de bajo riesgo por defecto.
- CorePulse AI Server V1.3.

## Contratos conservados
- REAL_OR_NA.
- CorePulse mide y clasifica; la IA explica.
- Sin cambios al Health Engine ni sensores.
