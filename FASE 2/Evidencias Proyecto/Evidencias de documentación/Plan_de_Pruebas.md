# Plan de pruebas de CorePulse

Plan de pruebas de la aplicación de escritorio (REBUILD 210), con los tipos de prueba, los casos, los criterios de aceptación y los resultados al cierre de la Fase 2.

## 1. Objetivo

Verificar que CorePulse entrega datos reales o N/A, que toda acción sobre Windows es reversible, que protege los datos del usuario y que funciona en distintos equipos Windows, de acuerdo con los requisitos no funcionales (`Requisitos_No_Funcionales.md`).

## 2. Alcance

| Incluido | Fuera del alcance |
|---|---|
| Aplicación de escritorio: telemetría, salud, tweaks, limpieza, red, IA, informes, overlay, sesiones de juego y benchmark | Pruebas de carga del sitio web en producción |
| Cliente de CorePulse AI y su servicio en la nube (con respuestas simuladas) | Consultas reales al modelo de IA (tienen costo) |
| Base de datos local (SQLite) y scripts de la base web (PostgreSQL) | Compatibilidad con juegos que usan antitrampas |
| Validación manual en equipos Windows reales | Sistemas distintos de Windows 10/11 de 64 bits |

## 3. Tipos de prueba

| Tipo | Qué verifica | Herramienta | Dónde está |
|---|---|---|---|
| Unitarias y de regresión | Cada módulo por separado y que una versión nueva no rompa funciones existentes | pytest | `tests/test_rebuild.py`, `test_runtime.py`, `test_sensor_startup.py`, `test_cloud_ai.py`, `test_overlay_activation.py`, `test_game_capture.py`, `test_game_sessions.py`, `test_health_reports.py`, `test_speedtest_live.py`, `test_rebuild_193_persistent_permissions.py` |
| Integración | Varios módulos trabajando juntos con almacenamiento real: sesiones de juego en SQLite, motor de tweaks con su respaldo, cuenta con cifrado DPAPI | pytest | `tests/test_integracion.py` |
| Rendimiento | Tiempos máximos en operaciones frecuentes | pytest con límites de tiempo | `tests/test_rendimiento.py` |
| Seguridad | Cifrado del token, PKCE, redirecciones, enmascarado de datos de red, rechazo de entradas alteradas y falla cerrada | pytest | `tests/test_seguridad.py` |
| Servicio de IA | Rutas, límites de uso, conocimiento curado y presupuesto, con respuestas simuladas | Node.js (`npm run verify`) | `cloud/corepulse-ai/test/` |
| Base de datos web | Las 10 migraciones se ejecutan en orden sobre PostgreSQL y crean el modelo completo | PostgreSQL / Docker | `Evidencias de sistema/Base de datos/` |
| Validación manual en hardware real | Funciones que dependen del equipo: sensores, FPS en juegos, instalador | Equipos de los integrantes y de usuarios externos | Sección 6 |

## 4. Casos de prueba de integración

| ID | Caso | Pasos | Resultado esperado |
|---|---|---|---|
| CPI-01 | Sesión de juego completa | Iniciar sesión, registrar 4 muestras y una incidencia, cerrar, reabrir la base | Los datos se conservan, el promedio de FPS es correcto (52,5) y un sensor faltante queda vacío, no inventado |
| CPI-02 | Partida abierta al cerrar CorePulse | Iniciar una sesión y cerrar la base sin terminarla | Al reabrir, la sesión queda como "interrumpida" |
| CPI-03 | Aplicar y restaurar un tweak | Aplicar un tweak sobre un Registro simulado y luego restaurarlo | El valor original se guarda antes de escribir, se verifica el cambio y restaurar devuelve el valor original y limpia el respaldo |
| CPI-04 | Tweak sin valor previo | Aplicar un tweak cuyo valor no existía y restaurarlo | Restaurar elimina el valor en vez de dejar uno inventado |
| CPI-05 | Sesión de cuenta con DPAPI | Guardar, leer y borrar la sesión | Se lee el mismo token y perfil; después de borrar no hay sesión |

## 5. Casos de prueba de rendimiento

| ID | Caso | Criterio de aceptación |
|---|---|---|
| CPR-01 | Guardar una hora de partida (720 muestras) | Menos de 5 s |
| CPR-02 | Leer el detalle de una partida de una hora | Menos de 0,5 s |
| CPR-03 | Listar el historial con 100 partidas | Menos de 0,2 s |
| CPR-04 | Enmascarar Red avanzada con 50 adaptadores | Menos de 0,1 s |
| CPR-05 | Guardar y leer el respaldo de los 78 tweaks | Menos de 0,5 s |
| CPR-06 | 10.000 consultas a la codificación de la consola | Menos de 0,1 s (se calcula una sola vez) |

## 6. Casos de prueba de seguridad

| ID | Caso | Criterio de aceptación |
|---|---|---|
| CPS-01 | Archivo de sesión `cuenta.dat` | No contiene el token, el correo ni contraseñas en texto legible |
| CPS-02 | Archivo de sesión alterado | Un archivo sin cifrar o de otro usuario no entrega un token |
| CPS-03 | PKCE al conectar la cuenta | El reto es el SHA-256 del verificador, el verificador tiene al menos 43 caracteres y no viaja en la URL |
| CPS-04 | Verificadores PKCE | 50 verificadores generados son todos distintos |
| CPS-05 | Redirecciones del servidor de IA | El cliente no sigue redirecciones que podrían desviar el token |
| CPS-06 | Datos de red sensibles | IP, IPv6 y SSID se muestran enmascarados hasta que el usuario los revela |
| CPS-07 | Tweak desconocido | No se escribe en el Registro |
| CPS-08 | Falla al guardar el respaldo | No se modifica Windows (falla cerrada) |
| CPS-09 | Respaldo alterado con claves ajenas | Se rechaza y no se escribe en el Registro |
| CPS-10 | Respaldo con valores fuera de rango | Se rechaza |

## 7. Validación manual en hardware real

| ID | Caso | Resultado |
|---|---|---|
| VM-01 | Medición de FPS por eventos de Windows en un juego real | 86,6 FPS medidos en World of Warcraft |
| VM-02 | Overlay sobre un juego en sus tres modos (minimalista, avanzado y panel rápido) | Correcto |
| VM-03 | Instalador en equipos de usuarios externos | Instalado; se detectaron y corrigieron cierres en Windows en español y una falla del benchmark en un notebook |
| VM-04 | Lectura de la consola en Windows en español (cp850) | Corregido y verificado con salidas reales |
| VM-05 | Matriz de compatibilidad en al menos tres equipos distintos | Pendiente |

## 8. Criterios de aceptación de la suite

- Las pruebas de integración, rendimiento y seguridad deben aprobarse al 100 %.
- Ninguna versión nueva puede agregar fallos respecto de la versión anterior (Definition of Done).
- Las pruebas que dependen de textos de pantallas se reescriben para verificar comportamiento.

## 9. Cómo ejecutar las pruebas

```bash
cd "FASE 2/Evidencias Proyecto/Evidencias de sistema/Aplicación/CorePulse_REBUILD_210"
python -B -m pytest -p no:cacheprovider -q tests
```

Para ejecutar solo un tipo de prueba:

```bash
python -B -m pytest -p no:cacheprovider -q tests/test_integracion.py
python -B -m pytest -p no:cacheprovider -q tests/test_rendimiento.py
python -B -m pytest -p no:cacheprovider -q tests/test_seguridad.py
```

Las pruebas de integración y seguridad no modifican Windows: el Registro se simula y los archivos se crean en carpetas temporales.

## 10. Resultados al cierre de la Fase 2

Ejecución del 16 de noviembre de 2026 sobre REBUILD 210:

| Archivo | Tipo | Aprobadas | Fallidas | Total |
|---|---|---|---|---|
| test_integracion.py | Integración | 5 | 0 | 5 |
| test_rendimiento.py | Rendimiento | 5 | 0 | 5 |
| test_seguridad.py | Seguridad | 10 | 0 | 10 |
| test_cloud_ai.py | Unitarias (CorePulse AI) | 36 | 0 | 36 |
| test_overlay_activation.py | Unitarias (overlay) | 32 | 0 | 32 |
| test_game_capture.py | Unitarias (captura de juego) | 21 | 0 | 21 |
| test_sensor_startup.py | Unitarias (sensores) | 10 | 0 | 10 |
| test_game_sessions.py | Unitarias (sesiones de juego) | 8 | 0 | 8 |
| test_health_reports.py | Unitarias (informes) | 7 | 0 | 7 |
| test_runtime.py | Unitarias (arranque) | 11 | 3 | 14 |
| test_speedtest_live.py | Unitarias (prueba de velocidad) | 9 | 1 | 10 |
| test_rebuild_193_persistent_permissions.py | Regresión (permisos) | 1 | 3 | 4 |
| test_rebuild.py | Regresión general | 279 | 76 | 355 |
| **Total** | | **434** | **83** | **517** |

**Análisis:** las pruebas de integración, rendimiento y seguridad se aprueban al 100 %, igual que las de IA, overlay, captura de juego, sensores, sesiones e informes. Las 83 fallidas se concentran en la regresión general y verifican textos o estructuras de pantallas que el equipo rediseñó o retiró en las últimas versiones; no corresponden a fallas de funcionamiento. Quedan registradas en el Product Backlog (PB17) para reescribirlas de modo que verifiquen comportamiento.
