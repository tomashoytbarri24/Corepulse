**V463: prueba con Groq** — Ver `../docs/historico/GUIAS_HISTORICAS.md`. La clave del proveedor se guarda fuera del cliente y del repositorio.

> **V462:** se añade `evaluation/benchmark_v462.py` (offline por defecto; `--live` con confirmación expresa), `evaluation/compare_v462.py`, `evaluation/cases_v462.json` y catálogo. No existe inferencia real medida incluida. Véase `../docs/historico/GUIAS_HISTORICAS.md`.

# CorePulse AI Server V461

Backend **propio** de CorePulse para conectar Windows con un LLM remoto alojado en infraestructura administrada por nosotros. `FastAPI` sanitiza el contexto, aplica `REAL_OR_NA`, autentica dispositivos y limita consumo diario. El modelo es intercambiable por configuración de servidor, sin desplegar LLM en el PC del usuario.

## Desarrollo

```powershell
cd CorePulse_AI_Server
python -m pip install -r requirements.txt
copy .env.example .env
python -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --no-access-log
```

En una segunda consola del servidor: `python -m app.admin issue --minutes 30` para crear un código de un solo uso. El código expira y no se guarda en texto plano. `python -m app.admin list` y `python -m app.admin revoke <installation_id>` administran accesos. El código es exclusivamente para la vinculación inicial; el cliente guarda un token individual y descarta el código.

## Endpoints

- `GET /v1/status`: estado técnico, sin incluir secretos.
- `POST /v1/register`: canje único del código enviado en `X-CorePulse-Enrollment` (solo si el usuario ya autorizó la conexión).
- `POST /v1/analyze`: análisis de evidencia con token individual `Authorization: Bearer`.
- `POST /v1/chat`: respuesta con historial reciente sanitizado.

Por defecto `/v1/analyze` y `/v1/chat` vuelven al motor determinista etiquetado como `evidence_fallback` si el modelo no está disponible; nunca presentan esa salida como generada por el LLM. Las cifras ausentes se conservan como N/A. Los mensajes son *texto no confiable*: la instrucción del usuario no debe prevalecer sobre las reglas de evidencia.

## Nube

Ver `../CorePulse_AI_Cloud_Deployment/README.md` para desplegar proxy HTTPS + API + vLLM, TODO en el servidor. El archivo `.env` de backend **no** va en el Windows del usuario. No exponer FastAPI o vLLM directamente a Internet. Nunca usar un código maestro permanente en todos los PCs.

## Verificación de salidas V461

`app/guardrails.py` valida la respuesta del LLM *después* de inferencia. Si hay datos cuantitativos no respaldados, enlaces no verificados u otras afirmaciones prohibidas, se responde con `evidence_fallback`. Los códigos de política y fuentes disponibles se incluyen como `guardrails` y `evidence_fields`; el texto bloqueado no se devuelve. La política es complementaria al prompt y no sustituye auditoría de calidad ni garantiza detectar todas las alucinaciones.

Sin búsqueda automática de tutoriales externos desde Windows. Los ejemplos de evaluación sintética están en `evaluation/`.
