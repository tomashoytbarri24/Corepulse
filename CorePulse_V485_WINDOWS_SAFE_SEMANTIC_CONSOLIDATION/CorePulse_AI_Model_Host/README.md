# CorePulse AI Model Host

Host local del modelo generativo de CorePulse AI. Usa `llama.cpp` y expone un endpoint OpenAI-compatible únicamente en loopback.

## Modelo actual

Durante el desarrollo se utiliza `Qwen/Qwen3-4B-GGUF:Q4_K_M` como modelo transitorio. El objetivo del producto es sustituirlo por CorePulseLM sin cambiar la interfaz entre CorePulse y el host.

## Flujo normal

En V399 `python main.py` inicia el host automáticamente incluso en un PC limpio. Primero intenta una instalación existente/WinGet y, si hace falta, usa un runtime portable oficial en AppData. Los BAT de esta carpeta quedan como preparación, fallback y diagnóstico manual.

- `Preparar_CorePulse_AI_Model.bat`: instala/localiza llama.cpp cuando sea necesario.
- `Localizar_Llama_Host.bat`: resuelve `llama-server.exe`/`llama.exe` en PATH y WinGet.
- `Iniciar_Modelo_CorePulse_AI.bat`: inicia el host en `127.0.0.1:8766`.
- `Probar_Modelo_CorePulse_AI.bat`: prueba manual del endpoint local.

CorePulse no utiliza Ollama para este runtime.
