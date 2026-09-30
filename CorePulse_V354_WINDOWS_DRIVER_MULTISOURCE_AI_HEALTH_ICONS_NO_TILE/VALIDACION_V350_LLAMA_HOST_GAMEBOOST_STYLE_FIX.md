# VALIDACIÓN V350 — llama.cpp Host Discovery + Game Boost Health Style

## Problema reproducido
La V349 instalaba llama.cpp mediante WinGet, pero después buscaba únicamente `llama.exe`. La distribución WinGet de llama.cpp puede exponer `llama-server.exe`, por lo que el inicio en un clic terminaba con un falso error de ejecutable no encontrado.

## Correcciones
- Identificador WinGet principal: `ggml.llamacpp`.
- Detección compatible con `llama.exe` y `llama-server.exe`.
- Búsqueda en PATH, `%LOCALAPPDATA%\Microsoft\WinGet\Links` y directorios de paquetes WinGet.
- No se requiere reiniciar la consola tras la instalación.
- Invocación compatible con frontend unificado (`llama serve`) y binario `llama-server.exe`.
- Game Boost pasa de morado al estilo azul/cian de Centro de salud.

## Contratos preservados
- REAL_OR_NA
- REAL_FPS_OR_NA_ONLY
- Sin telemetría inventada
- CorePulse AI continúa desacoplado del SDK del proveedor en el cliente Desktop
