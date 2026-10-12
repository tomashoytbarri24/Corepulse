# CorePulse REBUILD 051 — Tarjeta de juego activo estilo Steam

## Base
**REBUILD 049 — Rendimiento**. Se respetan `Reglas para crear Versiones nuevas.txt` e `versiones/HISTORIAL.md`.

## Cambios
- Rendimiento presenta una **tarjeta principal de juego activo**, inspirada en la biblioteca Steam y adaptada a CorePulse: imagen grande izquierda, tres indicadores a la derecha (estado, tiempo de sesión y plataforma).
- Detección automática de procesos ejecutables instalados en `steamapps/common` y `Epic Games`, con filtros para descartar launchers y procesos auxiliares conocidos. Un juego no detectado se presenta como ausencia de identificación, nunca como una lectura inventada.
- Nombre e identificador de juego real desde `steamapps/appmanifest_<appid>.acf` y carpeta de instalación del proceso; el nombre del ejecutable se conserva como dato de proceso.
- Carátulas **locales** Steam buscadas en las carpetas `appcache/librarycache` / `steamapps/librarycache` del cliente, incluyendo bibliotecas no principales.
- Si falta la carátula, se puede pulsar **Cargar carátula de Steam**. Solo con este clic se autoriza una solicitud al CDN público de Steam con el appid numérico verificado. Sin clic no hay consulta externa de arte ni transmisión de la biblioteca.
- Actualización real aproximadamente cada **2,5 segundos** mientras la página Rendimiento está abierta. El trabajo de consulta va a un hilo para no congelar Qt; al salir se detiene el sondeo.
- La tarjeta reacciona al abrir o cerrar un juego. Cuando no se identifica un juego, se muestra **Aún no hay juego activo**. No se inventan FPS, tiempo de juego, ni Game Boost.
- Se elimina el bloque anterior de "procesos probables" que duplicaba esta tarjeta. Se mantienen planes de energía reversibles, estabilidad térmica y resto de Centro de Salud.

## Límites
- No es integración con API privada de Steam ni detector universal de juegos. Títulos de Xbox, Microsoft Store, EA, Battle.net, instaladores personalizados y ejecutables no ubicados en rutas conocidas pueden no aparecer.
- Si Steam no tiene carátula local y no se autoriza carga online, se muestra el marcador oscuro de CorePulse.
- La sesión se calcula por el tiempo de vida real del proceso, no por el tiempo registrado en la cuenta Steam.
- El estado "en ejecución" verifica el proceso, no que se esté jugando activamente; no confundir con FPS o Game Boost aplicado.
- Ejecución real de Qt y detección de juegos en Windows pendiente de comprobación.

## Validación
- **159 pruebas automatizadas PASS**, incluidas pruebas de manifiesto local, filtro de anticheat, tiempo real, estado vacío y permiso para arte online.
- Compilación de código Python y comprobación estructural de QML.
- No se añaden archivos Python nuevos ni se tocan motores externos a Rendimiento.

## Inicio
Descomprime el ZIP completo y ejecuta `main.py` (Python 3.12 x64 en Windows) o `Iniciar_CorePulse.bat`. Abre **Centro de Salud → Rendimiento** y luego inicia un juego de Steam. El nombre y la carátula local deberían aparecer al siguiente sondeo.


## Ajuste de V051
- Las tarjetas **Estado**, **Tiempo activo** y **Origen** de juego activo se movieron **debajo de la carátula** en vez de al costado, siguiendo la referencia del usuario.
