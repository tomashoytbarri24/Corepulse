# CorePulse V485 — Auditoría de consolidación semántica segura

**Base:** `CorePulse_V484_WINDOWS_INTERNAL_DEDUP.zip` (la V484 fue probada por el usuario en Windows).  
**Destino:** CorePulse principal para **Windows**, código fuente completo, no EXE compilado.  
**Alcance:** reducir archivos mediante fusiones reales verificadas y agrupar documentos históricos sin retirar funciones.

## Inventario final

| Métrica | V484 (origen) | V485 |
|---|---:|---:|
| Archivos incluidos | 282 | **278** |
| Archivos Python | 180 | **179** |
| Reducción neta en la ronda | — | **4 archivos** |
| Reducción acumulada desde V479 (342 archivos) | 60 | **64 (18,7 %)** |

Las dos fusiones retiraron físicamente dos fuentes Python y conservaron sus definiciones en módulos existentes. Cinco informes de auditoría V480–V484 se archivaron **íntegros** en un documento histórico. Se agregó una suite de pruebas específica de V485 y el presente informe; no se eliminó ninguna prueba.

## Cambios exactos

| Archivo eliminado | Nuevo hogar | Motivo / protección |
|---|---|---|
| `core/runtime/frozen_selftest.py` | `core/runtime/startup_readiness.py` | Preflight y autocomprobación del EXE relacionados. `run_self_test()` y sus operaciones siguen disponibles. No se ejecuta self-test durante importación. |
| `core/diagnostics/health_history.py` | `core/diagnostics/session_trends.py` | Persistencia histórica de salud, benchmarks, estabilidad y tendencias de sesiones en una unidad funcional. La estructura SQLite y su ruta de datos conservadas. |
| `docs/AUDITORIA_REFACTORIZACION_V480.md` | `docs/historico/AUDITORIAS_V480_V484.md` | Auditoría histórica preservada íntegramente. |
| `docs/AUDITORIA_CONSOLIDACION_V481.md` | Igual | Auditoría histórica preservada íntegramente. |
| `docs/AUDITORIA_CONSOLIDACION_V482.md` | Igual | Auditoría histórica preservada íntegramente. |
| `docs/CorePulse_V483_AUDITORIA.md` | Igual | Auditoría histórica preservada íntegramente. |
| `docs/CorePulse_V484_AUDITORIA.md` | Igual | Auditoría histórica preservada íntegramente. |

Archivos nuevos: `tests/test_v485_safe_consolidation.py`, `docs/historico/AUDITORIAS_V480_V484.md` y `docs/AUDITORIA_V485.md`.

### Compatibilidad preservada

- Las rutas `core.frozen_selftest`, `core.runtime.frozen_selftest`, `core.health_history` y `core.diagnostics.health_history` siguen resolviéndose mediante el importador de compatibilidad. En los consumidores actuales se emplean rutas canónicas.
- Los helpers privados `_is_admin` y `_find_rtss` de la autocomprobación tenían el mismo nombre que funciones del preflight, pero no eran necesariamente equivalentes. Sus implementaciones se conservaron como `_selftest_is_admin` y `_selftest_find_rtss` y las rutas antiguas exportan la versión correspondiente.
- El helper privado `_num` de historial de salud se conserva como `_health_history_num`, distinto del helper de tendencias. El módulo importado por la ruta antigua sigue exportando el helper correcto.
- Comparación de árboles AST: **14 definiciones migradas idénticas**, permitiendo exclusivamente los renombres privados anteriores.
- No se cambiaron umbrales, cálculos de telemetría, fuentes, políticas o estructura de las mediciones.

## Superficies críticas sin modificación interna

Se compararon **80 archivos protegidos, con hashes de contenido idénticos a V484**, entre ellos:

- CorePulse AI cliente y servidor (`core/ai_engine/`, `CorePulse_AI_Server/`, `CorePulse_AI_Model_Host/`, `CorePulse_AI_Cloud_Deployment/`, paneles AI).
- Game Boost y los módulos `performance/`.
- Benchmarks CPU/GPU, DirectX y módulos de escena y telemetría de benchmark.
- Motor de FPS `core/sensors/rtss_osd.py`, certificación y overlay RTSS.
- Tweaks de Windows protegidos.

**FPS de juegos:** solamente RTSS Shared Memory. **Sin datos FPS válidos:** `N/A`. Se preservan las políticas `REAL_OR_NA` y `REAL_FPS_OR_NA_ONLY`. No se reintroduce PresentMon. **Windows-only:** no se introducen backends Linux para el cliente; el despliegue Docker opcional de AI Cloud es infraestructura del servidor y se conserva.

## Pruebas comparativas

Batería ejecutada en Linux/Python 3.13 con pantalla virtual Xvfb:

```text
xvfb-run -a python -m pytest -q tests --ignore=tests/test_v460_cloud_backend.py
```

| Resultado | V484 original | V485 final |
|---|---:|---:|
| Aprobadas | 398 | **405** |
| Fallidas | 8 | **8** |
| Omitidas | 1 | **1** |
| Subpruebas aprobadas | 37 | **37** |

Las ocho fallas son las mismas pruebas visuales de interfaz/contratos antiguos que ya fallan en V484 en este entorno (opciones Tk, comparación de píxeles y ausencia de `customtkinter`). **Ninguna falla nueva en la batería ejecutada**. Se ajustaron únicamente dos pruebas de versión con V484 codificada explícitamente, para validar coherentemente el identificador V485; se actualizó el control de ausencia de PresentMon para inspeccionar el nuevo archivo físico. Se añadieron siete comprobaciones nuevas, incluyendo importaciones históricas, estructura SQLite y políticas.

Otras comprobaciones: todos los `.py` parsean correctamente; importaciones canónicas y rutas antiguas comprobadas; contenidos de los cinco documentos históricos verificados completos; los 80 archivos críticos protegidos comparados byte por byte; ZIP verificado por integridad.

**Exclusión conocida:** `tests/test_v460_cloud_backend.py` se mantuvo fuera de ambas baterías, pues en este contenedor provoca un fallo nativo del intérprete. No se eliminó del ZIP.

## Archivos que se decidió conservar

Las cadenas de telemetría LHM/RTSS, los adaptadores de sensores y los controladores de gráficos no son archivos inútiles, aunque algunos tengan pocas líneas. Fusionarlos indiscriminadamente podría modificar el orden de carga, ciclos de imports, tiempos de arranque o lecturas reales. Se conservaron. También siguen disponibles las herramientas de desarrollo y las pruebas, separadas de la aplicación de ejecución mediante sus directorios.

## Verificación pendiente en Windows real

No se pudo probar aquí el cliente gráfico con Windows, LibreHardwareMonitor/PawnIO, juegos con RTSS, Game Boost, benchmarks DirectX ni compilar el EXE. La V484 estaba confirmada por el usuario, pero **V485 es una candidata que requiere validación**.

En Windows 10/11 con Python 3.12 x64, probar:

```powershell
py -3.12 -m compileall -q core gui performance main.py corepulse_launcher.py
py -3.12 -m pytest -q tests/test_v485_safe_consolidation.py tests/test_structure_fps_contracts.py
.\Iniciar_CorePulse.bat
.\build_exe.bat
.\verificar_exe.bat
```

Comprobar el historial de salud (persistencia entre reinicios), diagnóstico, navegación, RTSS con juego, Game Boost con reversión, sensores reales/N/A y ejecución del self-test del EXE. Si V485 no se comporta igual, volver a V484, que ya fue validada por el usuario.
