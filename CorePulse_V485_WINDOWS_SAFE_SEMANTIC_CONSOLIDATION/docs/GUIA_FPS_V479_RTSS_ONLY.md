# CorePulse V479 — FPS sólo RTSS en juegos

- Los FPS de juegos y su frametime se obtienen únicamente desde RTSS Shared Memory.
- RTSS es externo a CorePulse y debe estar instalado para la medición de juegos.
- Si no hay una aplicación 3D válida, los datos están obsoletos o RTSS no está disponible: FPS = N/A (None en la API), sin estimación ni interpolación.
- El benchmark GPU DirectX conserva su medición interna de frames del renderizado; esto NO es medición del FPS de un juego.
- El EXE ya no incluye ni exige PresentMon; no se inician sesiones ETW de ese programa.
- Documentos históricos previos pueden mencionarlo como parte de versiones antiguas.
- Validar la lectura FPS/frametime en un equipo Windows con RTSS instalado y un juego compatible.
