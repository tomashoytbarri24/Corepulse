# Validación V329 — CorePulse AI One Click

V329 agrega un lanzador único para desarrollo local de CorePulse AI.

## Flujo
1. Detecta Python.
2. Prepara `.venv` de `CorePulse_AI_Server`.
3. Detecta o instala llama.cpp.
4. Inicia y espera el Model Host en 127.0.0.1:8766.
5. Inicia y espera CorePulse AI Server en 127.0.0.1:8765.
6. Abre CorePulse mediante `CorePulse.vbs`.

El modelo GGUF no se incluye en el ZIP. La primera ejecución puede descargarlo en el host.
