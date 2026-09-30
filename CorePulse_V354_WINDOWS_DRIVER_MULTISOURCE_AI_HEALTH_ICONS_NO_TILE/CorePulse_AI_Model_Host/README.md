# CorePulse AI Model Host V1

Host de desarrollo para el modelo generativo de CorePulse AI.

**No usa Ollama** y no se incluye dentro de CorePulse Desktop. Se ejecuta únicamente en la máquina que hará de servidor de IA durante desarrollo o en la futura infraestructura de CorePulse.

## Modelo de desarrollo

Se usa `Qwen/Qwen3-4B-GGUF:Q4_K_M` mediante llama.cpp. Es un modelo abierto con formato GGUF. La primera ejecución descarga el modelo al caché del host; no aumenta el tamaño del programa CorePulse instalado en los PCs de los usuarios.

## Preparación en Windows

Ejecuta `Preparar_CorePulse_AI_Model.bat`. El script instala llama.cpp mediante WinGet si no está disponible.

## Iniciar el modelo

Ejecuta `Iniciar_Modelo_CorePulse_AI.bat`.

El host queda en:

`http://127.0.0.1:8766/v1`

Después ejecuta `CorePulse AI Server V1.2` en el puerto 8765 y finalmente CorePulse V328.

## Producción

Este paquete es para desarrollo. En producción el mismo protocolo OpenAI-compatible puede estar detrás de un servidor con GPU dedicado. CorePulse Desktop no necesita descargar el modelo.
