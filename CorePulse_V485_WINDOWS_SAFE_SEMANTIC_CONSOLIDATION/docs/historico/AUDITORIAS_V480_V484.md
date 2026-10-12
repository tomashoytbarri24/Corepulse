# Auditorías históricas V480–V484

Conservadas íntegramente y agrupadas para mantener limpia la carpeta `docs/`.


---

## Documento original: `AUDITORIA_REFACTORIZACION_V480.md`

# CorePulse V480 — Auditoría profunda y refactorización conservadora

Base: **CorePulse V479 RTSS Only**, archivo aportado `CorePulse_V479_RTSS_ONLY.zip`.
V480 es un **ZIP completo de código para Windows**, no un instalador `.exe` precompilado.

## Inventario y decisión de alcance

| Directorio / grupo | Archivos V479 | V480 | Decisión |
|---|---:|---:|---|
| `core/` | 103 | 103 | Conservar sensores/diagnósticos/benchmark/IA. No se borró código por aparente antigüedad. |
| `gui/` | 53 | 53 | Extraer y centralizar implementaciones duplicadas. |
| `performance/` | 8 | 6 | Fusionar persistencia transaccional y capa de compatibilidad energética con sus únicos consumidores. |
| `herramientas/` | 19 | 20 | Sonda manual reubicada y unificada con comprobación PawnIO. |
| `tools/` | 4 | 2 | Dejar sólo helpers de runtime/instalación. |
| `tests/` | 39 | 40 | Sumar pruebas del refactor, sin descartar regresiones históricas. |
| `build/`, `installer/` | 7 | 7 | Mantener fuentes del empaquetado en ubicaciones de desarrollo. |
| `CorePulse_AI_Server/` | 39 | 39 | Intacto; motor de IA fuera de alcance. |
| `docs/` | 8 | 9 | Añadir esta auditoría; mantener guías previas como documentación histórica. |
| Total del ZIP | **342** | **341** | Se conservaron los componentes; reducción no destructiva. |

Otros directorios (`database/`, `assets/`, `CorePulse_AI_Model_Host/`, `CorePulse_AI_Cloud_Deployment/`) y archivos de raíz se conservan. **No se encontraron dos archivos completos idénticos por SHA-256**. Sí se identificaron varias implementaciones Python equivalentes o idénticas: eso se trata como deuda de código, no como permiso para eliminar módulos.

## Refactorización funcional efectuada

### 1. Vistas de hardware/red y un solo código de comportamiento

En `gui/components/widget_updates.py` se agruparon funciones compartidas de presentación:

- Formato de métricas sin lecturas inventadas (`numeric_or_none`, `format_detail_number`, `format_detail_integer`, `detail_age_text`).
- Construcción de tarjetas resumen (`create_detail_summary_card`), idénticas en fichas CPU, GPU, RAM y Red.
- Construcción de tarjetas de sección (`create_detail_section_card`) para CPU, GPU y RAM.
- Determinación de desplazamiento (`detail_is_scrolling`) para los cuatro paneles.
- Pausa y reactivación de eventos Tk (`set_detail_panel_active`) para las fichas CPU, GPU y RAM.

Los métodos originales siguen existiendo como **adaptadores con la misma firma**, así que los llamadores conservan sus contratos y los colores/geometrías particulares de cada panel. No se agregaron sondeos, estimaciones, nuevos `after()` ni cambios en los sensores. Aproximadamente 148 líneas duplicadas de las cuatro vistas fueron eliminadas (sin computar la implementación compartida).

### 2. Energía: dos fusiones reales, sin perder funciones

- `performance/settings_backup.py` pasó a `performance/profile_manager.py`: `STATE_PATH`, `load_backup`, `save_backup`, `mark_restored` y `has_pending_backup`. Preservada la escritura atómica y la restauración.
- `performance/managed_power_plans.py` pasó a `performance/power_manager.py`: clase `ManagedPowerPlans`, lectura de planes existentes y reglas de propiedad de instalaciones antiguas. No se añadió creación/borrado masivo de planes.
- `performance/__init__.py` conserva los nombres importables históricos `performance.settings_backup` y `performance.managed_power_plans` mediante alias de módulo en `sys.modules`, sin archivos Python vacíos o wrappers intermedios.

**Game Boost, la selección de perfiles y el restablecimiento seguro siguen siendo parte del código**. La validación real de cambios de energía/rollback en Windows requiere pruebas de sistema en esa plataforma.

### 3. Separación de herramientas de desarrollo y runtime

- `herramientas/diagnostico/cpu_sensor_probe.py` concentra ahora la sonda térmica manual y el diagnóstico de PawnIO (`--check-pawnio`). Las dos entradas BAT de `herramientas/ia/` fueron actualizadas para conservar el flujo del usuario.
- `tools/` contiene únicamente `cpu_temp_package_probe.py` y `validate_python_runtime.py`, necesarios para el proceso de instalación/compatibilidad.
- `build/CorePulse.spec` deja de distribuir indiscriminadamente todo `tools/` y copia **sólo** esos dos helpers. Las sondas manuales siguen disponibles en el ZIP fuente para ejecutarse en Windows.
- `build/`, `installer/`, `tests/` y `herramientas/` son directorios de código fuente y desarrollo, no funciones empaquetadas automáticamente en el ejecutable. El `build_exe.bat` existente permanece en raíz por compatibilidad de herramientas y pruebas.

## Integridad y trazabilidad

- `core/version.py`, `LATEST_VERSION.txt`, `pyproject.toml`: V480 consistente.
- Se conservan políticas `REAL_OR_NA`, `REAL_FPS_OR_NA_ONLY`; los FPS de videojuegos continúan dependiendo exclusivamente de **RTSS Shared Memory**; el benchmark GPU usa su contador interno.
- `core/ai_engine/` y `CorePulse_AI_Server/`: archivos Python verificados byte a byte contra V479, **sin cambios**.
- Importaciones internas: auditoría estática / resolución de **155 rutas** importadas (`core`, `gui`, `performance`, `CorePulse_AI_Server`) sin rutas ausentes en el entorno de prueba.
- Los nombres `core.algo`/`gui.algo` siguen resolviendo a subdirectorios físicos mediante la capa de compatibilidad heredada.
- No se borraron imágenes de interfaz ni recursos asociados a acciones de la app por tener nombres similares.

## Pruebas (Linux de validación, Python 3.13)

Regresión prioritaria (V477–V480): **21 PASS** en la última ejecución.

Comandos (desde raíz del código fuente):

```powershell
python -m compileall -q core gui performance CorePulse_AI_Server main.py corepulse_launcher.py
python -m pytest -q tests/test_v477_clean_structure.py tests/test_v478_modular_structure.py tests/test_v479_rtss_only.py tests/test_v480_shared_panels.py
```

Batería ampliada ejecutada con pantalla virtual (`xvfb-run`) y excluyendo temporalmente `test_v460_cloud_backend.py`: **V479: 356 PASS / 8 FAIL / 1 SKIP**, **V480: 366 PASS / 8 FAIL / 1 SKIP**. Las **ocho fallas son preexistentes** y coinciden entre los dos árboles: tres problemas de introspección/render Canvas/Tk, varios contratos visuales de versiones históricas y falta de `customtkinter` en el entorno. Los fallos son en `test_v425`, `v427`, `v428`, `v436`, `v437`, `v438`, `v440`, `v447`. No se han ocultado ni declarado corregidos.

La suite `test_v460_cloud_backend.py` sufrió una **terminación nativa del intérprete Python** al ejecutarse con `starlette`/`anyio` en este contenedor. No se cambió el código del motor de IA para eludir este problema de infraestructura; la prueba debe repetirse en ambiente compatible.

**No comprobado aquí:** apertura real de ventana en Windows, detección de CPU/GPU, LHM/PawnIO, lectura RTSS con juego real, benchmarks DirectX, `powercfg`, tareas de mantenimiento, integración Groq en vivo, PyInstaller ni instalador Inno Setup. La ausencia de errores de sintaxis, importación o unit tests no sustituye ese cierre de validación.

## Checklist de aceptación antes de publicar instalador Windows

1. Ejecutar `instalar_dependencias.bat` y `VERIFICAR_PYTHON_COREPULSE.bat` en Windows 10/11 con Python 3.12 x64.
2. Abrir `Iniciar_CorePulse.bat`; confirmar Resumen, CPU/GPU/RAM/Disco/Red, tarjetas, desplazamiento, F11/Escape, restauración de ventana y cierre sin lag.
3. Probar sensor LHM/PawnIO y herramientas manuales 06/07; `N/A` para sensores ausentes.
4. Verificar FPS reales con RTSS activo y **N/A** sin juegos/RTSS; ejecutar GPU/CPU/RAM/SSD benchmarks y comprobar JSON de resultados.
5. Probar Game Boost, detección de juegos, reversión transaccional de energía, mantenimiento y backups en equipo de pruebas o VM.
6. Verificar CorePulse AI (consentimiento explícito, conectado/desconectado, no alucinar métricas), sin enviar información sensible en pruebas automáticas.
7. Ejecutar `python -m pytest -q` y registrar diferencias de dependencias; repetir batería cloud V460.
8. Ejecutar `build_exe.bat` y `build_installer.bat`; exigir `self-test` del EXE antes de compartirlo.

## Trabajo seguro pendiente

La mayor cantidad de código sigue concentrada en `main.py`, `gui/panels/health_center_panel.py`, `core/maintenance/windows_tweaks.py` y los motores de benchmark. Una nueva fusión indiscriminada allí podría alterar señales Tk, tareas de Windows y garantías de sensores. Para una V481 se sugiere descomponer sus funciones complejas en componentes probados con dependencias explícitas y pruebas de interfaz reales en Windows; **no eliminar por tamaño o fecha**.


---

## Documento original: `AUDITORIA_CONSOLIDACION_V481.md`

# CorePulse V481 — Auditoría de consolidación Windows-only

**Base:** CorePulse V480 Professional Refactor, sin PresentMon.  **Entrega:** ZIP completo del código fuente, scripts de inicio y recursos para Windows. **No es un .exe compilado.**

## Resultado cuantitativo

| Área | Archivos V480 | Archivos V481 | Diferencia |
|---|---:|---:|---:|
| `core/` | 103 | 95 | -8 |
| `gui/` | 53 | 48 | -5 |
| `performance/` | 6 | 6 | 0 |
| `tests/` | 40 | 14 | -26 |
| Raíz | 21 | 22 | +1, importador de compatibilidad |
| `docs/` | 9 | 10 | +1, auditoría nueva |
| Resto de directorios | 109 | 109 | 0 |
| **TOTAL** | **341** | **304** | **-37 (10,9 %)** |

**Archivos Python:** 243 → 205 (-38). Los números incluyen archivos distribuibles; excluyen cachés `__pycache__`, `.pytest_cache` y `.pyc`. No se han eliminado funciones para cumplir una cifra objetivo.

## Fusiones reales de módulos (13 eliminados)

| Archivo antiguo eliminado | Implementación unificada y responsabilidad |
|---|---|
| `core/diagnostics/alert_history_persistence.py` | `core/diagnostics/alert_history_store.py`: retención, eventos y persistencia de alertas |
| `core/diagnostics/diagnostic_pipeline.py` | `core/diagnostics/recommendation_engine.py`: recomendaciones y su integración con diagnóstico actual |
| `core/diagnostics/diagnostic_history.py` | `core/diagnostics/session_recovery.py`: recuperación y comparación del diagnóstico previo |
| `core/diagnostics/diagnostic_lifecycle.py` | `core/diagnostics/session_recovery.py`: ciclo de vida y cancelación de sesiones |
| `core/diagnostics/diagnostic_evidence.py` | `core/diagnostics/diagnostic_summary.py`: evaluación física y evidencia trazable |
| `core/diagnostics/diagnostic_explainer.py` | `core/diagnostics/diagnostic_summary.py`: explicación sin nuevos datos de sensor |
| `core/reports/pdf_context.py` | `core/reports/report_builder.py`: contexto estricto y construcción PDF |
| `core/reports/report_generator.py` | `core/reports/report_builder.py`: generación y construcción PDF en un punto |
| `gui/dashboard_parts/header_identity_canvas.py` | `gui/dashboard_parts/professional_visuals.py`: identidad del equipo |
| `gui/dashboard_parts/status_symbols.py` | `gui/dashboard_parts/professional_visuals.py`: símbolos semánticos |
| `gui/dashboard_parts/render_polish.py` | `gui/dashboard_parts/professional_visuals.py`: acabados y comportamiento visual |
| `gui/navigation/sidebar.py` | `gui/navigation/compact_sidebar.py`: navegación lateral expandida/compacta |
| `gui/windowing/high_refresh.py` | `gui/windowing/resize_render_guard.py`: política de refresco y guardas de redibujado |

Los bloques implementados se trasladaron con sus firmas y lógica; los imports internos apuntan al nuevo módulo. `_corepulse_compat_imports.py` resuelve **diferidamente** las 13 rutas importables anteriores, sin importar Tk, telemetría o hardware al cargar únicamente `core` o `gui`. Esto conserva la posibilidad de `from core.diagnostic_lifecycle import DiagnosticRun`, etc. La compatibilidad de importación no garantiza monkeypatching de variables privadas del módulo anterior.

**Decisiones conservadoras:** se restituyeron `core.cpu_frequency`, `core.overlay_theme`, `gui.dialogs` y `gui.flat_workspace_page` como archivos independientes porque fusionarlos cargaba dependencias adicionales en rutas anteriormente livianas, con riesgo de arranque o pruebas. No se han fusionado sensores críticos, el motor de Game Boost ni un panel de 8.000 líneas por mera reducción cosmética.

## Consolidación de tests sin perder cobertura

Se agruparon **32 archivos históricos** en cinco suites temáticas: `test_ui_legacy_regressions.py`, `test_cloud_provider_contracts.py`, `test_cloud_credentials_contracts.py`, `test_cloud_conversation_contracts.py` y `test_ai_diagnostic_history_contracts.py`. Cada bloque está delimitado y conserva sus casos originales; se ajustaron las importaciones internas entre pruebas fusionadas y un `ROOT` que apuntaba a `gui/`, ahora `GUI_ROOT` para evitar colisión. Se mantuvo `test_v460_cloud_backend.py` por separado para poder aislar su fallo nativo en Linux y repetirlo en Windows.

`test_v481_consolidated.py` añade siete pruebas de compatibilidad, conservación del pipeline PDF, cancelación, versión y reglas de FPS. `test_v480_shared_panels.py` ya comprueba una versión de paquete consistente sin fijar permanentemente el número 480. Los tests históricos se conservan dentro del ZIP fuente: **no deben copiarse a `dist/CorePulse` como datos de runtime.**

## Plataforma y Linux

**CorePulse de escritorio es exclusivamente Windows.** `main.py`, el launcher, RTSS, temperaturas, servicios, Win32 y operaciones de mantenimiento sólo están destinados a Windows. No existe un backend de FPS de Linux ni se ha añadido compatibilidad Linux al cliente. Se conservaron `if os.name != 'nt'` y comprobaciones de plataforma que **bloquean operaciones no soportadas y fallan de forma segura**; quitarlas no reduce archivos y sí quitaría esa protección.

**Excepción importante:** `CorePulse_AI_Cloud_Deployment/compose.yaml`, `Caddyfile` y `CorePulse_AI_Server/Dockerfile` corresponden al **servidor remoto opcional** de IA, no al cliente de escritorio. Los conservamos porque eliminarlos retiraría una vía de despliegue de CorePulse AI en la nube. Si en el futuro se decide usar sólo un proveedor cloud gestionado, se podrá retirar esa infraestructura opcional con una decisión separada y documentada.

## Comprobaciones realizadas (entorno Linux de análisis, Python 3.13)

- Validación AST y compilación de fuentes: sin errores de sintaxis.
- **21/21** tests prioritarios V477–V480 aprobados antes de agrupar las suites históricas.
- Batería ampliada V480: **366 PASS, 8 FAIL, 1 SKIP**.
- Batería ampliada V481 después de consolidar + 7 pruebas nuevas: **373 PASS, 8 FAIL, 1 SKIP**, y 37 subtests PASS. **No se observaron regresiones adicionales.**
- Las 8 fallas anteriores reaparecen con las mismas clases y causas aparentes: Tk/canvas/píxeles, expectativas visuales antiguas y `customtkinter` ausente en el entorno. No se corrigieron alterando funcionalidad sólo para hacer pasar tests.
- Se omite `test_v460_cloud_backend.py` de la batería ampliada de este contenedor: en V480 provoca terminación nativa con el stack servidor; debe ejecutarse en un entorno Windows compatible.
- Archivos de `core/ai_engine/`, `CorePulse_AI_Server/`, `performance/` y cliente/flujo principal de IA conservados byte a byte frente a V480 (SHA-equivalentes).
- Políticas `REAL_OR_NA` y `REAL_FPS_OR_NA_ONLY` preservadas; RTSS sigue siendo la única fuente de FPS de juegos. No se agregó PresentMon.

**Comandos de validación:**

```powershell
python -m compileall -q core gui performance CorePulse_AI_Server main.py corepulse_launcher.py
python -m pytest -q tests/test_v477_clean_structure.py tests/test_v478_modular_structure.py tests/test_v479_rtss_only.py tests/test_v480_shared_panels.py tests/test_v481_consolidated.py
python -m pytest -q tests
```

La prueba completa incluye `test_v460_cloud_backend.py` (omitida sólo en el contenedor de análisis). **Pendiente de validar en Windows**: inicio real con CTk, lectura LHM/PawnIO, RTSS con juego, benchmarks DirectX y almacenamiento real, Game Boost/rollback powercfg, audio, mantenimiento, networking, empaquetado PyInstaller e Inno Setup. El ZIP no demuestra por sí mismo que el EXE arranque en otro PC.


---

## Documento original: `AUDITORIA_CONSOLIDACION_V482.md`

# CorePulse V482 — Informe de consolidación avanzada (Windows)

**Versión base:** V481 Windows Consolidated; motor FPS de V479 **RTSS Only**. **Plataforma:** aplicación de escritorio exclusivamente para Windows. **Tipo de entrega:** código fuente completo, recursos y scripts Windows; no es un EXE compilado.

## Inventario medido

| Indicador | V479 | V481 (base) | V482 (entrega) |
|---|---:|---:|---:|
| Archivos totales | 342 | 304 | 288 |
| Archivos Python | 245 | 205 | 188 |
| Archivos eliminados por fusión de implementaciones V482 | — | — | 14 |
| Suites de test reagrupadas V482 | — | — | 5 → 2 (−3 archivos, +6 pruebas nuevas) |

**V481 → V482:** −16 archivos (−5,3%), −17 `.py` (−8,3%). **V479 → V482:** −54 archivos (−15,8%). Se añade este informe dentro del ZIP (de 287 a 288). No se alcanzó de forma forzada una meta de 250–270: se respetaron límites arquitectónicos y contratos de tests.

## Fusiones de implementación realizadas

| Ruta retirada | Ruta consolidada | Responsabilidad |
|---|---|---|
| `core/runtime/startup_profiler.py` | `core/runtime/startup_readiness.py` | marca temporal, etapas y preflight de arranque |
| `core/runtime/overlay_theme.py` | `core/runtime/overlay_preferences.py` | tema RTSS, diseño overlay y preferencias persistentes |
| `core/runtime/pythonnet_shutdown.py` | `core/runtime/safe_shutdown.py` | cierre ordenado y liberación de sensores Python.NET |
| `core/sensors/pawnio_support.py` | `core/sensors/sensor_stack_setup.py` | estado de PawnIO y preparación asistida de sensores |
| `core/sensors/gpu_display_logic.py` | `core/sensors/device_identity.py` | identidad de hardware y representación verificada de GPU |
| `core/storage/storage_summary_health.py` | `core/storage/storage_health.py` | salud real de discos y resumen con caché trazable |
| `core/diagnostics/diagnostic_session.py` | `core/diagnostics/session_recovery.py` | sesiones de diagnóstico y recuperación |
| `core/diagnostics/alert_engine.py` | `core/diagnostics/alert_history_store.py` | eventos técnicos y persistencia/historial de alertas |
| `core/diagnostics/health_intelligence.py` | `core/diagnostics/health_engine.py` | interpretación de salud usando misma implementación de `_num` |
| `core/sensors/sensor_diagnostics.py` | `core/diagnostics/corepulse_diagnostics.py` | evidencia de sensores y diagnóstico de capacidades |
| `core/maintenance/audio_test.py` | `core/maintenance/windows_audio.py` | WASAPI + prueba guiada/confirmación de audio |
| `core/storage/nvme_smart_windows.py` | `core/smartctl_storage.py` | lectura NVMe SMART Windows y fallback smartctl |
| `core/diagnostics/thermal_throttling.py` | `core/diagnostics/health_engine.py` | clasificación térmica por evidencia sin datos ficticios |
| `gui/components/thermal_health_binding.py` | `gui/components/live_health_binding.py` | autoridades térmica y salud instantánea en UI |

Los cuerpos funcionales se trasladaron al destino preservando firmas y comportamiento. En `health_engine` se reutilizó el auxiliar `_num` ya idéntico por AST; `thermal_throttling` preservó su conversión propia bajo `_throttling_number`. En GUI se renombraron únicamente helpers privados para evitar que una paleta sobrescribiera a la otra. En `smartctl_storage`, `__all__` conserva las exportaciones de ambas fuentes de información.

**Reversiones preventivas:** las propuestas de unir `gui/navigation/sidebar_native_hover.py` con el sidebar compacto y `gui/chart_workspace_surface.py` con las tarjetas visuales se descartaron: la primera añadía una dependencia de `customtkinter` durante importación de tests Tk, y la segunda rompía contratos que exigen un archivo físico independiente. Ambas rutas siguen disponibles sin cambios en el ZIP.

## Compatibilidad e importaciones

- Rutas cortas históricas (`core.audio_test`, `core.nvme_smart_windows`, `gui.thermal_health_binding`, etc.) siguen disponibles por el resolvedor diferido del V481.
- V482 añade rutas históricas por carpeta (`core.storage.nvme_smart_windows`, `core.runtime.startup_profiler`, etc.), incluidos 13 módulos fusionados previamente por V481.
- Importaciones de consumidores normales actualizadas al destino; código interno CorePulse AI y benchmarks críticos se dejó con sus importaciones originales para no intervenir sus implementaciones.
- Una importación histórica apunta a la implementación real consolidada; no se crean 14 archivos adaptadores vacíos ni se fuerza un import global de Tk/hardware al importar `core`/`gui`.
- **Límite documentado:** importar con nombres anteriores preserva los símbolos públicos, pero el atributo `__module__` de clases trasladadas, el monkeypatch de variables privadas y rutas físicas bajo `inspect.getsourcefile()` pueden diferir. Por eso no se fusionaron módulos críticos basados en esas identidades.

## Organización de tests y herramientas

- `test_v477_clean_structure.py`, `test_v478_modular_structure.py` y `test_v479_rtss_only.py` → `tests/test_structure_fps_contracts.py`.
- `test_v480_shared_panels.py` y `test_v481_consolidated.py` → `tests/test_refactor_contracts.py` (incluye seis pruebas nuevas V482).
- Los tests agrupados conservan sus funciones, lógica y expectativas históricas excepto las verificaciones de versión, que se adaptaron a V482; no se suprimieron casos para mejorar las cifras.
- `tools/` conserva helpers realmente usados por el build/runtime; `herramientas/` y `tests/` siguen separados de la distribución PyInstaller.

## Linux y servidor remoto

No se identificó un backend funcional Linux del cliente que se pudiera suprimir sin alterar el comportamiento: el cliente ya es Windows-only. Se conservan protecciones `os.name != "nt"` que impiden operaciones inseguras en otra plataforma; **no son soporte Linux**. Los archivos Docker/Compose/Caddy del **servidor remoto opcional** de CorePulse AI se conservaron, porque su sistema operativo de despliegue es independiente del cliente Windows.

## Funcionalidades preservadas

- `REAL_OR_NA`: métricas con ausencia de sensor continúan como `N/A`, no estimaciones.
- `REAL_FPS_OR_NA_ONLY`: FPS de juegos sólo desde RTSS Shared Memory; sin PresentMon ni ETW de juegos. Los FPS internos de benchmarks DirectX pertenecen al propio benchmark y no se inventan.
- Monitorización, diagnóstico, benchmarks, mantenimiento, Game Boost, audio, almacenamiento, overlays y CorePulse AI incluidos.
- Carpetas `core/ai_engine/`, `CorePulse_AI_Server/`, `performance/`, `core/benchmarks/`, módulos RTSS/FPS, `gui/ai_panel.py` y `core/maintenance/windows_tweaks.py` conservadas **byte a byte** respecto a V481 mediante verificación SHA-256.

## Pruebas reproducibles en contenedor (no equivalen a Windows)

- Sistema: entorno Linux de análisis Python 3.13 con pantalla virtual Xvfb; no puede verificar sensores reales, DirectX, RTSS en juego o construcción EXE.
- Línea base V481: **373 PASS, 8 FAIL, 1 SKIP** y 37 subtests PASS, excluido `test_v460_cloud_backend.py` por fallo nativo documentado.
- V482 tras consolidaciones y seis tests nuevos: **379 PASS, 8 FAIL, 1 SKIP**, 37 subtests PASS; **cero regresiones adicionales detectadas**.
- Las ocho fallas coinciden con la base y se concentran en contratos UI Tk/canvas/píxeles, una cabecera histórica, y falta de `customtkinter` en este entorno de pruebas. No se maquillaron modificando código productivo.
- Pruebas añadidas: compatibilidad de 14 rutas cortas, NVMe inválido rechazado, overlay RTSS con `N/A`, evaluación térmica sin falsa confirmación, comprobación de archivos críticos y ausencia de wrappers vacíos.
- AST/`compileall` del código Python aprobado, importaciones de rutas históricas core probadas; ZIP validado con CRC.

### Comandos sugeridos para verificar en Windows

```powershell
py -3.12 -m compileall -q core gui performance CorePulse_AI_Server main.py corepulse_launcher.py
py -3.12 -m pytest -q tests/test_refactor_contracts.py tests/test_structure_fps_contracts.py
py -3.12 -m pytest -q tests
.\Iniciar_CorePulse.bat
.\build_exe.bat
.\verificar_exe.bat
```

**Pendiente antes de considerar V482 estable:** validación de arranque visual con customtkinter en Windows; LHM/PawnIO CPU/GPU, RTSS en un juego activo, benchmark GPU/storage, rollback Game Boost/powercfg, audio, tráfico de red, CorePulse AI nube/consentimiento, PyInstaller e instalador Inno Setup. No se hizo ninguna medición real de hardware en el contenedor.


---

## Documento original: `CorePulse_V483_AUDITORIA.md`

# CorePulse V483 — Auditoría de consolidación segura (Windows)

**Base real:** `CorePulse_V482_WINDOWS_ADVANCED_CONSOLIDATION.zip` verificada por el usuario en Windows. **Plataforma:** cliente exclusivo Windows. **Modalidad de entrega:** proyecto fuente completo para Windows (no un ejecutable).

## Inventario

| Métrica | V479 original | V482 base | V483 entrega |
|---|---:|---:|---:|
| Archivos totales | 342 | 288 | 284 |
| Archivos `.py` | 245 | 188 | 183 |
| Archivos físicos fusionados en esta versión | — | — | 5 |

**V482 → V483:** eliminación neta de 4 archivos contando este informe (5 módulos Python fusionados, 1 informe nuevo); sin añadir wrappers Python vacíos. El descenso no se fuerza cuando compromete contratos de importación o carga ligera de módulos.

## Fusiones concretas

| Origen eliminado | Implementación de destino | Justificación |
|---|---|---|
| `core/runtime/product_contract.py` | `core/version.py` | Contratos de producto junto a versión y políticas permanentes, incluyendo `REAL_OR_NA` y `REAL_FPS_OR_NA_ONLY` |
| `core/runtime/cancellable_process.py` | `core/maintenance/windows_commands.py` | Ejecución de procesos con cancelación cooperativa y comandos silenciosos Windows en una implementación |
| `core/diagnostics/adaptive_diagnostic.py` | `core/diagnostics/session_recovery.py` | Diagnóstico adaptativo reutiliza directamente el objeto real `DiagnosticSession` definido en el destino |
| `core/runtime/env_config.py` | `core/runtime/runtime_logging.py` | Configuración y observabilidad del entorno en una única unidad de runtime |
| `gui/components/dialogs.py` | `gui/components/integration.py` | Diálogos nativos y validación de integración de UI; sin rediseño visual |

**Cambio preventivo revertido:** se intentó consolidar `gui/components/widget_updates.py` con `gui/components/ui_consistency.py`; se deshizo antes de la entrega porque añadía dependencia de `customtkinter` a herramientas livianas de lectura/escritura visual y falló la recopilación de pruebas en Linux. No se incluyó esa fusión.

## Garantías y compatibilidad

- Se preservan imports históricos por rutas **cortas** y **con subcarpetas**, mediante el resolvedor diferido ya usado por V481/V482, sin añadir módulos de compatibilidad de una sola línea.
- Se actualizan imports de consumidores normales para apuntar al módulo consolidado, compatible con análisis de PyInstaller; no se cambia la lógica de sensores, diagnósticos ni IA.
- Se conserva el decorador `@contextmanager` en `cancellation_scope`, comprobado mediante una ejecución real controlada y bloqueo de cancelación. El primer prototipo había perdido el decorador; fue corregido y probado.
- `REAL_OR_NA` y `REAL_FPS_OR_NA_ONLY` permanecen en los contratos de versión; RTSS Shared Memory continúa como única fuente de FPS de juegos.
- Verificación byte a byte SHA-256/equivalencia de bytes de **80 archivos protegidos**: CorePulse AI cliente/servidor/despliegue/model host, Game Boost (`performance/`, panel Gaming), benchmarks, RTSS/FPS y tweaks críticos, sin diferencias respecto a V482.
- Se conservan Docker y Caddy del servidor cloud de CorePulse AI, que **no son soporte Linux del cliente**.
- Las políticas de seguridad continúan impidiendo ejecutar operaciones Windows sobre un SO incompatible; no representan soporte Linux de escritorio.
- **Límites técnicos de alias:** las rutas antiguas proporcionan funciones/clases idénticas a las reales, pero introspección de `__module__`, alteración de variables privadas por monkeypatch e `inspect.getsourcefile` pueden ver el destino físico. Cualquier plugin externo que dependa del archivo fuente literal requiere adaptación. Los consumidores internos se cambiaron a la ruta real.

## Pruebas

En Linux de análisis (Python 3.13 + Xvfb), usando la **misma invocación** sobre V482 y V483 (`pytest -q tests --ignore=tests/test_v460_cloud_backend.py`):

| Resultado | V482 | V483 |
|---|---:|---:|
| PASS | 379 | 387 |
| FAIL | 8 | 8 |
| SKIP | 1 | 1 |
| Subtests PASS | 37 | 37 |

- Ocho pruebas nuevas V483: alias históricos, cancelación activa/inactiva, herencia de sesión adaptativa, políticas, parser de entorno, diálogos, ausencia de wrappers, y conservación de utilidades visuales ligeras.
- Las **8 fallas de V483 son las mismas 8 fallas existentes en V482**, relativas a pixel/renderizado Tk, una cabecera histórica y falta de `customtkinter` en el entorno de análisis. No se retiraron pruebas para ocultar fallas.
- `test_v460_cloud_backend.py` excluido de ambas baterías porque en el entorno Linux dispara fallo nativo del intérprete, documentado desde V481.
- `compileall` Python y análisis AST de funciones/decoradores de módulos fusionados aprobados; ZIP verificado con CRC.

## Verificación recomendada en Windows

```powershell
py -3.12 -m compileall -q core gui performance main.py corepulse_launcher.py
py -3.12 -m pytest -q tests/test_refactor_contracts.py tests/test_structure_fps_contracts.py
py -3.12 -m pytest -q tests
.\Iniciar_CorePulse.bat
.\build_exe.bat
.\verificar_exe.bat
```

**Pendiente de validación práctica:** arranque Win11, LHM/PawnIO y sensores reales, RTSS en juego, Game Boost y reversión, benchmarks, audio, CorePulse AI en nube/consentimiento, EXE PyInstaller e instalador Inno Setup. Las pruebas en Linux no certifican esas funciones. El usuario confirmó que la base V482 funciona; la V483 aún no está comprobada por el usuario.


---

## Documento original: `CorePulse_V484_AUDITORIA.md`

# CorePulse V484 — Auditoría de consolidación interna y deduplicación

**Origen exacto:** `CorePulse_V483_WINDOWS_SAFE_CONSOLIDATION.zip`. **Destino:** cliente Windows. **Tipo de paquete:** fuente completa, scripts de inicio, recursos y construcción, no EXE precompilado.

## Inventario reproducible

| Métrica | V479 | V483 | V484 |
|---|---:|---:|---:|
| Archivos incluidos | 342 | 284 | 282 |
| Archivos Python | 245 | 183 | 180 |
| Diferencia desde V483 | — | — | **−2 archivos** |
| Reducción respecto de V479 | — | — | **−60 (17,5 %)** |

Se han eliminado físicamente 3 archivos Python por fusión real, se han agrupado 11 pruebas nuevas dentro de `tests/test_refactor_contracts.py` y se ha añadido este informe. V484 incluye todos los archivos fuente de V483 salvo los 3 originales fusionados. No se busca reducir la cifra de forma artificial.

## Fusiones concretas

| Archivo V483 eliminado | Destino físico V484 | Motivo |
|---|---|---|
| `gui/navigation/compact_sidebar.py` | `gui/navigation/internal_navigation.py` | Navegación compacta, sincronización del sidebar y navegación interna bajo un módulo compartido que ya depende de CustomTkinter. El hover nativo mantiene su propio archivo físico. |
| `core/diagnostics/before_after.py` | `core/diagnostics/session_trends.py` | Comparaciones antes/después, operaciones e historial de sesiones en un mismo módulo de tendencias, conservando persistencia y rutas. |
| `core/sensors/cpu_frequency.py` | `core/sensors/device_identity.py` | Obtención de evidencia certificada de frecuencia del CPU junto a su identidad física y evidencia de hardware. No se añade fallback sintético. |

**Prevención de colisiones:** se renombraron exclusivamente dos helpers privados (`_num` a `_before_after_num` y a `_cpu_frequency_num`) para conservar el comportamiento *distinto* del `_num` ya existente en sus módulos de destino. Se verificó con AST que **27 definiciones trasladadas** mantienen cuerpo y decoradores originales salvo esos renombres.

## Deduplicación de funciones sin nuevos archivos

- `core/storage/storage_health.py`: su `_num` duplicado se reemplaza por importación de la implementación **AST-idéntica** ya existente en `core.smartctl_storage` (que el módulo ya importaba).
- `core/diagnostics/complete_diagnostic.py`: se reutiliza el `_num` **AST-idéntico** de `core.diagnostic_summary` (dependencia que ya existía).
- Estas dos sustituciones reducen lógica repetida. No se alteran formatos, umbrales, sensores o clasificación REAL_OR_NA.

## Compatibilidad y superficies protegidas

- Los consumidores principales (`main.py`, `gui/dashboard.py`, `gui/windows_tweaks_panel.py`, `gui/components/ui_consistency.py`, `gui/panels/cleaning_actions.py`, `gui/panels/health_center_panel.py`, `core/sensors/telemetry_background.py`) usan las rutas físicas actualizadas.
- Los imports históricos planos y con subcarpetas se mantienen mediante `_corepulse_compat_imports.py` y los alias registrados en `core/__init__.py` / `gui/__init__.py`. No se añaden archivos Python vacíos de reexportación.
- `gui/navigation/sidebar_native_hover.py` y `gui/components/widget_updates.py` siguen independientes para evitar cargar dependencias extras donde no corresponda.
- Comparación de contenido idéntico en **80 archivos protegidos** (CorePulse AI cliente y nube, Game Boost y módulos `performance/`, benchmarks, RTSS/FPS, tweaks principales); las reglas `REAL_OR_NA` y `REAL_FPS_OR_NA_ONLY` se conservan.
- Se conserva RTSS Shared Memory como fuente FPS; no se reintroduce PresentMon.
- El código Linux-específico del cliente no se añadió. Docker/Caddy se conserva para servidor cloud de CorePulse AI.

## Ejecución de pruebas en el entorno de análisis

Linux/Python 3.13 con Xvfb, usando `python -m pytest -q tests --ignore=tests/test_v460_cloud_backend.py` exactamente en ambas bases.

| Resultado | V483 (base) | V484 |
|---|---:|---:|
| Aprobadas | 387 | 398 |
| Fallidas | 8 | 8 |
| Omitidas | 1 | 1 |
| Subpruebas aprobadas | 37 | 37 |

Las **8 fallas de V484 son exactamente las mismas 8 fallas de V483** (tests UI de píxeles de Tk, contratos antiguos y módulo `customtkinter` ausente en este entorno); no se eliminó ninguna prueba previa. Se incorporaron 11 casos nuevos, incluidos cuatro alias parametrizados, tres contratos de evidencia y controles de interfaz/estructura. `test_v460_cloud_backend.py` permanece excluido de ambas baterías: en este entorno causa una caída nativa del intérprete. Se verificó además la sintaxis AST de todos los archivos `.py`, las fuentes protegidas y las importaciones canónicas.

## Riesgos y limitaciones

- No se ha ejecutado el cliente gráfico, LHM/PawnIO, RTSS con un juego, benchmark DirectX, Game Boost ni generación EXE en **Windows real** desde este entorno.
- La V482 había sido probada y confirmada en Windows por el usuario; **la V483 no cuenta todavía con esa confirmación en este chat**. Por tanto, V484 es una candidata para prueba, no una versión certificada.
- Las rutas antiguas funcionan para importación y acceso de símbolos, pero el origen físico reflejado por introspección será el módulo consolidado; `monkeypatch` de globals privados por módulos antiguos podría requerir adaptación.
- `core.device_identity` ahora importa `psutil` en carga inicial por la fusión de CPU frequency. Se trata de una dependencia ya requerida por CorePulse, pero puede tener un pequeño coste de arranque a comprobar en Windows.

## Pruebas recomendadas en Windows

```powershell
py -3.12 -m compileall -q core gui performance main.py corepulse_launcher.py
py -3.12 -m pytest -q tests/test_refactor_contracts.py tests/test_structure_fps_contracts.py
py -3.12 -m pytest -q tests
.\Iniciar_CorePulse.bat
.\build_exe.bat
.\verificar_exe.bat
```

Comprobar además en pantalla el sidebar expandido/colapsado, CPU GHz real o N/A, historial de optimizaciones, diagnóstico total, RTSS overlay/FPS y Game Boost con reversión.
