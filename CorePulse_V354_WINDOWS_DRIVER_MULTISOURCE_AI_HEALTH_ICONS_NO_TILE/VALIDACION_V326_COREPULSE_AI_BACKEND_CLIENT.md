# V326 — CorePulse AI Backend Client

- Sustituye el selector OpenAI/Groq del escritorio por un único servicio **CorePulse AI**.
- El cliente no contiene modelos ni API keys de proveedores.
- Token opaco por instalación guardado en Windows Credential Manager.
- Endpoint de desarrollo por defecto: `http://127.0.0.1:8765`; producción exige HTTPS salvo loopback.
- Contexto sanitizado: salud, CPU, RAM, GPU y almacenamiento; sin seriales, rutas, usuario, IP ni MAC.
- Se incluye `CorePulse_AI_Server/` con FastAPI, registro por instalación, límite diario y adaptador a un motor autoalojado compatible con OpenAI Chat Completions.
- Sin modelo configurado, el servidor usa un Evidence Engine determinista y lo identifica como tal; no simula IA ni inventa datos.
- Se preserva `REAL_OR_NA`; la IA no modifica sensores ni decisiones técnicas.
- El análisis narrativo del PDF ahora también pasa por `CorePulse AI Backend`; no usa SDK/clave OpenAI/Groq en el cliente.
