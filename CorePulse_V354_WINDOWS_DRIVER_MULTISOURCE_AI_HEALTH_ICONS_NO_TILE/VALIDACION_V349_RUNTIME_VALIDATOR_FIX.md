# Validación V349 — Runtime Validator Fix

- Base: V348.
- Corrige el bloqueo de inicio del bootstrap automático en Python 3.14.x.
- `tools/validate_python_runtime.py` ya no exige importar `groq` en el cliente de escritorio.
- Esto alinea la validación con la arquitectura consolidada: CorePulse de escritorio usa `core/ai_client.py` como cliente HTTP del backend y no depende directamente del SDK de Groq/OpenAI.
- `requirements-base.txt`, `requirements-runtime-lock.txt` y `requirements-runtime-flex.txt` permanecen sin SDKs de proveedores, por diseño.
- El aviso de PawnIO puede seguir apareciendo si PawnIO no está instalado; ese aviso limita algunos sensores profundos, pero no debe impedir el arranque.
- Se conserva íntegro el cambio visual V348 del Game Boost morado.
- REAL_OR_NA y REAL_FPS_OR_NA_ONLY permanecen intactos.
