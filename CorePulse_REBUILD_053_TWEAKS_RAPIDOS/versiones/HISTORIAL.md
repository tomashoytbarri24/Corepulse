## REBUILD 040 — Centro de Salud: Reparación de Windows (11-10-2026)

- **Base:** REBUILD 039. Leídos previamente el TXT de reglas y el historial. TXT conservado byte por byte. Referencia histórica V485 `windows_repair.py` sin copiar infraestructura obsoleta.
- **Nuevo módulo:** Reparación de Windows con dos acciones manuales (diagnóstico DISM CheckHealth + ScanHealth y SFC VerifyOnly; reparación DISM RestoreHealth + SFC ScanNow + verificación DISM). Requiere confirmación explícita y administrador; no modifica el sistema al abrir. Ejecución en trabajador, avance por etapa, retorno real, clasificación conservadora, log local. Reparación del sistema no equivale a revertir Tweaks.
- **Visual:** las cuatro tarjetas de Análisis de Windows se compactaron y los botones Ver detalles se acercaron a sus datos. Ventana de confirmación comparte fondo y borde del software.
- **Añadido:** `core/health/repair.py` (uno). **Modificados:** `main.py`, `ui/Main.qml`, `ui/HealthPage.qml`, `tests/test_rebuild.py`, `README.md`, `versiones/HISTORIAL.md`. **Eliminados:** 0; sin código de compatibilidad antiguo. 31 archivos en ZIP.
- **Preservados:** motores Batería/Almacenamiento/Windows lectura, Limpieza, Tweaks y telemetría, rótulos, barra lateral y arranque automático.
- **Seguridad:** sólo comandos DISM/SFC literales en lista cerrada, sin shell y sin autoelevación. No se promete rollback de reparaciones; no se inventan porcentajes de DISM.
- **Pendiente:** pruebas reales de elevación y procesos DISM/SFC en Windows 11, y renderizado QML/DPI.
- **Reversión:** conservar ZIP V039 externo.

## REBUILD 039 — Centro de Salud: Análisis de Windows (11-10-2026)

- **Base y reglas:** REBUILD 038; leídos íntegramente `Reglas para crear Versiones nuevas.txt` y `versiones/HISTORIAL.md` antes de implementar. Reglas TXT conservadas byte por byte.
- **Referencia histórica:** V485 (`windows_health.py`, funciones de inicio/servicios/eventos/controladores). Nueva implementación compacta y de solo lectura dentro de la arquitectura Qt actual; no se arrastra el árbol antiguo.
- **Nueva tercera pestaña:** «Análisis de Windows» al lado de Batería (solo portátiles) y Almacenamiento. Conserva las tarjetas oscuras, acento turquesa, botón Actualizar y detalles plegables.
- **Datos:** entradas de inicio `Win32_StartupCommand`; inventario de servicios `Win32_Service`; hasta 80 errores/críticos recientes de Sistema/Aplicación con `Get-WinEvent` (últimos 7 días); incidencias de dispositivos PnP `Win32_PnPEntity.ConfigManagerErrorCode`. Una fuente fallida se representa `N/A`, no como sistema sano. No se leen comandos de inicio ni mensajes de eventos. No se equipara servicio automático detenido a fallo, ni código PnP a actualizaciones disponibles.
- **Seguridad/rendimiento:** consultas independientes dentro de PowerShell con errores aislados; trabajador único asíncrono, tiempo límite 45 s, consulta diferida hasta abrir la pestaña y actualización periódica a 5 min, salida limitada, sin Windows write, sin instalar/reparar drivers, sin deshabilitar servicios o programas de inicio, sin cambios al Registro.
- **Añadido:** `core/health/windows.py`. **Modificados:** `main.py`, `ui/Main.qml`, `ui/HealthPage.qml`, `tests/test_rebuild.py`, `README.md`, `versiones/HISTORIAL.md`. **Eliminados:** ninguno; no se generaron stubs ni implementaciones descartadas. 30 archivos en la versión completa.
- **Preservados:** Batería/Almacenamiento, autonomía, Tweaks, Limpieza, telemetría, arranque automático, UI de las otras pestañas y reglas. **Pruebas:** suite anterior actualizada más análisis/seguridad/regresión; QML y fuentes nativas deben verificarse en Windows real.
- **Reversión:** ZIP REBUILD 038 externo; no hay cambios del sistema que restaurar.

## REBUILD 038 — Centro de Salud: autonomía y almacenamiento (11-10-2026)

- **Base:** REBUILD 037; se leyeron las reglas TXT y el historial completo antes de modificar el proyecto. Reglas originales preservadas.
- **Batería:** autonomía mediante Windows real (`psutil`), respaldo de tasa de descarga `BatteryStatus` por `root/wmi` en trabajador (mWh/mW) y última alternativa basada en caída porcentual observada >=1 punto durante >=5 min; cada valor derivado se etiqueta como estimación. Sin historial válido o tasa fiable permanece N/A. En corriente se muestra su estado. No mezcla baterías distintas.
- **Detección:** no mostrar Batería como módulo en un equipo sin batería real; el Centro de Salud presenta Almacenamiento. El usuario puede seleccionar Almacenamiento también en portátil. No infiere desktop por modelo ni fabricantes.
- **Almacenamiento:** inventario de unidades fijas y espacio disponible/ocupado desde Windows, estado físico CIM `MSFT_PhysicalDisk` independiente del porcentaje usado. Estados desconocidos = N/A, no se inventa SMART/desgaste; es solo lectura.
- **Añadido:** `core/health/storage.py` (módulo independiente). **Modificados:** `core/health/battery.py`, `ui/HealthPage.qml`, `ui/Main.qml`, `main.py`, `tests/test_rebuild.py`, `README.md`, `versiones/HISTORIAL.md`. No hay archivos obsoletos nuevos ni modificaciones de los motores principales.
- **Pruebas:** regresión más escenarios de tasa de descarga real, muestra insuficiente, varias baterías, salud física desconocida y navegación sin batería; sintaxis Python, integridad ZIP. **Pendiente:** comprobar lecturas reales WMI, disco y renderizado QML en un portátil desconectado y una torre Windows 11.
- **Reversión:** usar REBUILD 037 (lecturas de solo diagnóstico, sin cambios del sistema).

## REBUILD 037 — Recuperación de capacidades/ciclos de batería desde V485 (11-10-2026)

- **Base:** REBUILD 036 y módulo real de batería de CorePulse V485. Se leyeron el TXT de reglas y el historial íntegros antes de realizar cambios; TXT original conservado literalmente.
- **Problema:** batería detectada y porcentaje real, pero capacidad de diseño, capacidad plena, ciclos y salud en N/A cuando las clases CIM del fabricante no devuelven datos.
- **Solución:** sumar como respaldo `powercfg /batteryreport /xml`, tal como hacía V485, procesando exclusivamente las baterías instaladas, con parseo XML compatible con namespaces. Archivo temporal de nombre único eliminado en `finally`, límite de tamaño, timeout y ejecución en el hilo existente. La operación no cambia ajustes ni planes de energía.
- **Política de seguridad:** no cruzar capacidades de baterías distintas ni calcular una salud sin un par completo de capacidades. Reportes de múltiples baterías se agregan solo si todas tienen datos verificables; los ciclos por batería no se suman. Compatibilidad REAL_OR_NA conservada.
- **UI:** al estar conectado a corriente, autonomía muestra el estado explícito en vez de N/A. Fuente de capacidad disponible en detalle técnico; geometría, tarjetas, colores, sidebar y resto del software intactos.
- **Modificados:** `core/health/battery.py`, `ui/HealthPage.qml`, `ui/Main.qml`, `tests/test_rebuild.py`, `README.md`, `versiones/HISTORIAL.md`. **Añadidos o eliminados:** 0 archivos, 0 `.py` nuevos.
- **Verificación:** suite de regresión más tests XML (namespace, una/dos baterías, ciclos, errores, combinación de fuentes), `py_compile`, contenido ZIP. **Pendiente:** comprobar reporte real powercfg y las lecturas en Windows 11, especialmente equipo Lenovo con datos CIM incompletos. No se prometen lecturas no proporcionadas por Windows.
- **Reversión:** conservar ZIP REBUILD 036.

## REBUILD 036 — Centro de Salud: batería real (11-10-2026)

- **Base:** REBUILD 035 con arranque automático. Leídos el TXT obligatorio y el historial antes del desarrollo.
- **Alcance:** primera pestaña funcional de Centro de Salud, exclusivamente Batería; se conserva el resto de las páginas y sus diseños. Acceso desde «Centro de salud» y desde «Batería» en módulos adicionales.
- **Datos reales:** estado de energía, porcentaje de carga y autonomía reportados por Windows (`psutil.sensors_battery`, API nativa), actualizados cada tres segundos; capacidades de diseño/plena carga y ciclos mediante clases CIM `BatteryStaticData`, `BatteryFullChargedCapacity` y `BatteryCycleCount` en `root\wmi`, con `Win32_Battery` como identificación y respaldo de capacidades cuando ofrece ambos valores y solo hay una batería. Ejecutado en hilo independiente con timeout.
- **Salud:** `capacidad plena / capacidad de diseño × 100` únicamente si Windows devuelve capacidades válidas y correlacionables por `InstanceName`; desgaste calculado únicamente a partir de esos dos datos, nunca de la carga. Varias baterías requieren pares completos. Sin sensor -> `N/A`, PC sin batería -> aviso explícito, y autonomía no calculada artificialmente.
- **Seguridad:** SOLO LECTURA; sin modificar batería, firmware, planes de energía ni registros. Consulta opcional PowerShell CIM no necesita administrador; no se envía telemetría externa. No se requieren dependencias nuevas.
- **Diseño:** `ui/HealthPage.qml` integrado a paleta oscura `#1A1C26` / borde `#303647`, acento turquesa, tarjeta de carga con anillo de datos reales, tarjeta independiente de salud y bloques de capacidades, ciclos y autonomía; interfaz adaptable y desplazable.
- **Añadidos:** `core/health/__init__.py`, `core/health/battery.py` y `ui/HealthPage.qml`; sin archivos obsoletos. **Modificados:** `main.py` (bridge y cierre), `ui/Main.qml` (routing/rótulo 036), `tests/test_rebuild.py`, `README.md`, este historial. TXT y motores existentes intactos.
- **Pruebas:** contratos antiguos + nuevos sobre correlación de baterías, N/A y renderizado estático QML; compilación Python e integridad del ZIP. **Pendiente:** verificar PowerShell CIM y QML visual en Windows 10/11 y equipo sin batería.
- **Reversión:** conservar ZIP REBUILD 035. Ningún ajuste de Windows es modificado.

## REBUILD 035 — Dependencias automáticas al ejecutar main.py (11-10-2026)

- **Base:** REBUILD 034. Antes del cambio se leyeron las reglas TXT y el historial íntegro. TXT obligatorio conservado literalmente.
- **Problema:** en un PC con Python 3.12 pero sin PySide6, main.py terminaba indicando instalar manualmente `pip -r requirements.txt`; ejecutar ese comando desde una carpeta superior provocaba `No such file or directory`.
- **Solución:** `main.py` detecta su propio directorio mediante `Path(__file__).resolve()`, localiza el manifiesto sin depender del directorio actual, crea un `venv` exclusivo en `%LOCALAPPDATA%\CorePulse\runtime` (por ABI x64 y hash de requirements), instala los paquetes con pip usando la ruta absoluta, valida imports de PySide6.QtCore/QtGui/QtQml y psutil y las distribuciones pythonnet/HardwareMonitor, y relanza automáticamente la aplicación con el intérprete aislado.
- **Fiabilidad:** reintenta una instalación interrumpida, evita instalaciones simultáneas mediante bloqueo de carpeta, no declara listo un runtime defectuoso, reutiliza el entorno en aperturas siguientes, no actualiza pip global ni modifica la instalación principal de Python. Sanea variables de entorno Qt/Python heredadas de otras instalaciones.
- **Limitaciones explícitas:** requiere Python 3.12 x64 y Windows 10/11, Internet en el primer arranque y acceso a PyPI; no pretende instalar el propio Python ni garantizar las DLL/controladores nativos de otros fabricantes. El arranque Qt definitivo debe probarse en Windows real.
- **Modificados:** `main.py`, `Iniciar_CorePulse.bat`, `ui/Main.qml` (solo numeración), `tests/test_rebuild.py`, `README.md`, `versiones/HISTORIAL.md`. **Añadidos/eliminados:** ninguno en el ZIP. **Sin cambios:** algoritmos RAM, Tweaks, telemetría, QML visual, reglas y requisitos de paquetes.
- **Pruebas:** contratos previos + pruebas del bootstrap (ruta CWD independiente, primera instalación, caché y reintento por fallo), compilación Python, integridad del ZIP. Sin descargas de pip durante tests; validación nativa Windows pendiente.
- **Reversión:** conservar V034 como respaldo. El entorno virtual está fuera de la carpeta CorePulse y no modifica respaldos de Tweaks.

## REBUILD 034 — Anclajes de ThinScroll y cuadros visuales unificados (11-10-2026)

- **Base:** REBUILD 033. Se leyeron íntegramente las reglas TXT y el historial; TXT conservado sin cambios.
- **Fallo reportado:** QML ThinScroll en Tweaks advertía repetidamente `Cannot anchor to an item that isn't a parent or sibling`.
- **Causa:** el `ThinScroll` estaba anidado dentro de un `Flickable`. Este reubica hijos declarativos en su `contentItem`, rompiendo la relación de parentesco requerida por los anclajes hacia el propio Flickable.
- **Solución:** `Flickable` y `ThinScroll` como hermanos dentro de un `Item` del Layout, con anclajes de barra a `parent`. Aplicado a Tweaks, Detalle de componentes y Lecturas disponibles. Limpieza ya tenía ambas piezas como hermanos y no requería modificación. Sin cambio de paleta, geometría o datos de lectura de barras.
- **Cuadros de Limpieza:** los cuadros de confirmación, progreso, error y éxito ahora reutilizan un único componente interno `ModalSurface` con fondo `#1A1C26`, borde `#303647`, radio 19 y un solo overlay neutro. Se retiran tonos azulados y bordes dobles ajenos a las tarjetas; el medidor turquesa y el ticket verde de éxito permanecen. Botones con hover oscuro coherente con el programa, sin blanco nativo.
- **Modificados:** `ui/TweaksPage.qml`, `ui/ComponentDetail.qml`, `ui/Main.qml`, `ui/CleanupPage.qml`, `tests/test_rebuild.py`, `README.md`, `versiones/HISTORIAL.md`. **Añadidos/eliminados:** ninguno. Motores Python intactos.
- **Pruebas:** suite automatizada y prueba de regresión de jerarquía de barras, compilación Python, integridad ZIP y comparación diferencial. **Pendiente:** validación gráfica real PySide6/QtQuick sobre Windows 11.
- **Reversión:** retornar al ZIP REBUILD 033; no hay migración de datos.

## REBUILD 033 — Paleta del monitor de RAM integrada con CorePulse (11-10-2026)

- **Base:** REBUILD 032. Reglas TXT e historial leídos previamente; TXT preservado literalmente.
- **Pedido:** retirar el celeste del cuadro de medidor que se abre tras pulsar limpiar RAM; conservar diseño y operaciones.
- **Diseño:** fondo del popup `page.surface` (`#1A1C26`) y borde `page.edge` (`#303647`); anillo, barra, icono y etiquetas acentuadas con el turquesa existente `#4EDDC8`. Se retiran del popup los tonos celestes `#68C9F5`, `#76D8ED` y `#77C6FF`. El overlay oscuro, mediciones y tamaño permanecen.
- **Modificados:** `ui/CleanupPage.qml`, `ui/Main.qml` (rótulo 033), `tests/test_rebuild.py`, `README.md`, `versiones/HISTORIAL.md`. **Añadidos/eliminados:** ninguno. Se sustituyen los colores antiguos obsoletos del popup; no se mantienen temas duplicados.
- **Preservado:** medidor real, backend RAM, standby, caché/DNS/Papelera, Tweaks, Resumen, diálogos de confirmación y modelo de telemetría.
- **Pruebas:** contratos QML, suite automatizada, sintaxis de Python, integridad de ZIP y revisión diferencial. **Pendiente:** ejecutar QML visualmente en Windows 11.
- **Reversión:** restaurar ZIP REBUILD 032 (no cambia datos persistentes).

## REBUILD 032 — Corrección de advertencias QML y layout (11-10-2026)

- **Base:** REBUILD 031. Leídos `Reglas para crear Versiones nuevas.txt` y `versiones/HISTORIAL.md`; TXT obligatorio conservado byte por byte.
- **GridLayout:** se reemplazan anchuras ligadas a `primary.width` por el ancho exterior de `page`; se mantienen proporción 70/30, filas adaptativas y geometría visual del Resumen. Objetivo: evitar `Detected recursive rearrange`.
- **Datos nulos:** protección de accesos a `telemetry.metrics` y `cleanup.data` en Resumen, Detalle de componentes, Lecturas y Limpieza durante inicio/cierre, manteniendo REAL_OR_NA.
- **Barras de desplazamiento:** eliminado el `ScrollBar` nativo personalizado que provocaba avisos de controles Windows (`background`/`contentItem`). Se reutiliza `ui/ThinScroll.qml` en Tweaks, Detalle, Lecturas y Limpieza; esta última pasa a `Flickable`. No requiere cambiar el estilo de Qt.
- **Archivos modificados:** `ui/Overview.qml`, `ui/Main.qml`, `ui/ComponentDetail.qml`, `ui/TweaksPage.qml`, `ui/CleanupPage.qml`, `tests/test_rebuild.py`, `README.md`, `versiones/HISTORIAL.md`. **Añadido:** `ui/ThinScroll.qml`, componente reutilizable. **Eliminado:** uso obsoleto de scrollbars Windows personalizados; ningún `.py` adicional.
- **Sin cambios:** motores de Tweaks y Limpieza, API de telemetría, estilos de tarjetas y navegación; rótulo visible actualizado a REBUILD 032.
- **Pruebas:** contratos automatizados, compilación Python, revisión de ZIP y comparativo de los motores intactos. **Pendiente:** ejecución/renderizado QML real y validación final de ausencia de advertencias en Windows 11.
- **Reversión:** regresar al proyecto completo REBUILD 031; no afecta backups persistentes ni revierte borrados de archivos del usuario.

## REBUILD 031 — Limpieza de caché, Papelera y DNS (11-10-2026)

- **Base:** REBUILD 030. Leído `Reglas para crear Versiones nuevas.txt` y el historial anterior; TXT preservado byte por byte.
- **Problema en video:** la tarjeta Temp del REBUILD 030 solo ofrecía limpieza de archivos antiguos; carecía de limpieza separada de cachés de Windows. Un resultado `0.0 MB` en Temp no representa la caché del sistema.
- **Nuevo motor de caché:** ubicaciones regenerables del perfil (`D3DSCache`, NVIDIA DX/GL, AMD DX, miniaturas Explorer) con inventario real, comprobación de rutas y enlaces, revalidación de tamaño/mtime antes de cada eliminación, omisión de archivos bloqueados y reanálisis de lo restante. No se eliminan carpetas ni documentos.
- **Papelera:** consulta de archivos y espacio por Shell32 `SHQueryRecycleBinW`, confirmación de borrado permanente y `SHEmptyRecycleBinW`; se vuelve a consultar tras la operación. No afecta Descargas ni documentos fuera de la Papelera.
- **DNS:** `ipconfig /flushdns` con timeout y comprobación del código de salida. Estado por tarjeta; no se presenta un ahorro inventado en MB.
- **Temporales:** tras borrar se vuelve a escanear para no mostrar cero si permanecen archivos no eliminables. Se conservan el límite de inventario, la antigüedad de 24 horas y la confirmación.
- **UI:** 3 tarjetas minimalistas, controles adaptables y confirmaciones oscuras; los botones y los resultados de RAM no cambian.
- **Modificados:** `core/maintenance/cleanup.py`, `ui/CleanupPage.qml`, `ui/Main.qml`, `tests/test_rebuild.py`, `README.md`, `versiones/HISTORIAL.md`. **Añadidos/eliminados:** ningún archivo de producción; sin código muerto ni rutas heredadas.
- **Pruebas:** suite REBUILD, comprobación de borrado sobre fixtures, aislamiento de rutas, omisiones por cambio concurrente, respuesta DNS y API de Papelera simulada, compilar Python e integridad ZIP. Falta ejecución Qt en Windows y test real de Shell32/DNS.
- **Reversión:** usar REBUILD 030 para el proyecto; vaciar la Papelera no es reversible con el ZIP.

## REBUILD 030 — Limpieza minimalista y resultados bajo demanda (11-10-2026)

- **Base:** REBUILD 029. Se leyeron el TXT de reglas y el historial antes de cambiar código. Se conserva el TXT literal.
- **Objetivo:** eliminar la franja permanente "Estado de limpieza" y reducir drásticamente texto de la tarjeta de memoria, conforme a la grabación del usuario.
- **UI:** `ui/CleanupPage.qml` ahora solo muestra un estado compacto mientras hay trabajo, o cuando falla la limpieza de temporales. Tarjeta RAM con nombre y descripción breves, resumen de la última variación de memoria disponible y botón contextual "Ver detalles" plegado por defecto. Los dos botones de RAM, diálogos oscuros, medidor real, ticket de confirmación y errores de permisos se conservan.
- **Fuente de verdad:** `core/maintenance/cleanup.py` conserva el último modo RAM completado con éxito en `lastRamKind`, evitando perder el resumen al analizar temporales. No cambia algoritmos de limpieza, privilegios ni el muestreo real.
- **Modificados:** `ui/CleanupPage.qml`, `core/maintenance/cleanup.py`, `ui/Main.qml` (etiqueta 030), `tests/test_rebuild.py`, `README.md`, `versiones/HISTORIAL.md`. **Añadidos/eliminados:** ninguno en producción.
- **Pruebas:** compilación Python, pruebas automatizadas y verificación del ZIP. Pendiente probar apariencia QML y operaciones Windows 11 in situ.
- **Reversión:** reemplazar el proyecto con el ZIP completo de REBUILD 029; sin migración de respaldos o cambio de datos de Windows.

## REBUILD 029 — Medidor de RAM real durante limpieza (11-10-2026)

- **Base:** REBUILD 028, reglas TXT e historial revisados antes de modificar.
- **Modificados:** `core/maintenance/cleanup.py`, `ui/CleanupPage.qml`, `ui/Main.qml`, `tests/test_rebuild.py`, `README.md`, `versiones/HISTORIAL.md`.
- **Medidor:** aparece al iniciar limpieza completa (confirmada) o standby; muestra RAM ocupada, total, disponible, porcentaje y variación frente al comienzo. Lectura física única desde `psutil.virtual_memory()` cada ~280 ms mientras se ejecuta el Future en un hilo independiente. Sin valores interpolados de telemetría ni promesas de reducción.
- **Diseño:** popup modal centrado, overlay oscuro con profundidad, anillo y barra de uso RAM, valores antes/ahora y cambio observado. La animación suaviza solo el trazo visual; cifras obtenidas de lecturas reales. No se puede cerrar mientras trabaja.
- **Finalización:** cierra el medidor al finalizar; conserva la confirmación verde ya aprobada solo con resultados positivos reales. Si la operación falla, informa en un diálogo oscuro ámbar, sin ticket de éxito.
- **Sin cambios:** algoritmo de limpieza profunda/standby, motor Tweaks, Resumen y estructura de carpetas. Sin nuevos archivos Python ni QML de producción. La variación de RAM puede deberse también a otras aplicaciones.
- **Validación:** pruebas Python y contratos QML; el renderizado Qt y el vaciado privilegiado requieren validación en Windows 11.

## REBUILD 028 — Hover, diálogos y confirmación real de RAM (11-10-2026)

- **Modificados:** `ui/CleanupPage.qml`, `ui/Main.qml`, `core/maintenance/cleanup.py`, `tests/test_rebuild.py`, `README.md`, `versiones/HISTORIAL.md`.
- **Correcciones:** botones no blancos al pasar el mouse, diálogos centrados en la ventana con overlay oscuro translúcido, acciones alineadas.
- **Nueva confirmación:** cuadro de éxito cuadrado con ticket verde rodeado de círculo verde para resultados reales de RAM. No se muestra con errores ni cancelaciones.
- **Alcance:** diseño y comunicación de resultado; sin cambiar el algoritmo de limpieza profunda ni Tweaks.
- **Pendiente:** verificación en Windows de renderizado Qt y operaciones nativas.

## REBUILD 027 — Organización de módulos Python (11-10-2026)

- **Base:** REBUILD 026. Se leyó y preservó íntegramente el TXT de reglas y el historial previo.
- **Alcance:** únicamente reorganización de archivos Python por responsabilidad; conserva todas las pantallas QML, su geometría y las operaciones existentes de telemetría, Tweaks y Limpieza. Rótulo de versión actualizado a 027.
- **Movidos:** `telemetry.py` → `core/monitoring/telemetry.py`; `tweaks.py` y `tweaks_engine.py` → `core/tweaks/`; `cleanup.py` → `core/maintenance/cleanup.py`. Se mantienen separados puente y motor de Tweaks por su responsabilidad independiente.
- **Añadidos:** cuatro `__init__.py` mínimos para paquetes Python. **Eliminados de raíz:** los cuatro archivos reubicados; queda `main.py` como único lanzador. Sin stubs ni copias duplicadas.
- **Modificados:** `main.py` (imports), `core/tweaks/tweaks_engine.py` (raíz de proyecto compatible con los snapshots anteriores), `ui/Main.qml` (etiqueta), pruebas de estructura y rutas, `README.md` y este historial.
- **Persistencia:** no cambia `%APPDATA%` ni `%LOCALAPPDATA%`, y la ruta heredada `data/windows_tweaks_state.json` sigue resolviendo desde la raíz original.
- **Validación:** suites automatizadas y compilación del código Python; ejecución nativa de UI/operaciones privilegiadas pendiente de Windows. **Reversión:** restaurar ZIP REBUILD 026 sin borrar respaldos persistentes.

## REBUILD 026 — Limpieza profunda de RAM y ajuste de interfaz (11-10-2026)

- **Base:** REBUILD 025. Referencia del motor V485 en `ram_optimizer.py`; integración de operaciones intensivas en `cleanup.py` sin copiar módulos completos.
- **RAM:** nuevo método `optimize_ram_deep()` con recorte de working sets externos accesibles, listas de memoria y caché del sistema, con permisos y reporte por operación. Se conserva botón standby separado. Confirmación explícita y medición antes/después; sin promesa de 99 %.
- **QML:** rectángulo de estado con altura dinámica; tarjetas más altas para el texto; diseño de confirmación profundo; barra de acciones separada.
- **Modificados:** `cleanup.py`, `ui/CleanupPage.qml`, `ui/Main.qml`, `README.md`, `tests/test_rebuild.py`, `versiones/HISTORIAL.md`. **Sin nuevos archivos de producción.** Se elimina `optimize_ram_safe` y su slot, por quedar obsoletos en esta interfaz.
- **Advertencia:** el trim externo y vaciado de cachés pueden inducir paginación o lentitud; uso manual con confirmación, no automático.
- **Pendiente:** prueba de ejecución nativa con administrador en Windows 11 y comprobación visual en DPI distintos.

## REBUILD 025 — Botones separados de RAM (11-10-2026)

- Base: REBUILD 024. Referencia: optimización segura del motor V485.
- Modificados: `cleanup.py`, `ui/CleanupPage.qml`, `ui/Main.qml`, `README.md`, `tests/test_rebuild.py`, `versiones/HISTORIAL.md`. Sin archivos nuevos de producción ni código obsoleto añadido.
- Se agrega botón **Limpiar RAM** junto a **Limpiar RAM standby**. Optimización segura mediante `gc.collect()` y `EmptyWorkingSet` limitados a CorePulse, sin alterar memoria privada de otros procesos. Resultado de diferencia global mostrado como medición, no como causalidad.
- Se mantiene purga de standby separada con privilegio temporal; controles desactivados durante tareas.
- Pruebas automatizadas y compilación; falta validar renderizado y efectividad en Windows 11. Reversión: conservar ZIP 024.

## REBUILD 024 — Privilegio RAM y controles de Limpieza (11-10-2026)

- **Base:** REBUILD 023; revisión del TXT obligatorio y del historial.
- **Motor:** `cleanup.py` habilita temporalmente `SeProfileSingleProcessPrivilege` usando el token del proceso, comprueba `ERROR_NOT_ALL_ASSIGNED`, ejecuta la purga standby y restituye el estado previo del privilegio incluso al fallar la operación.
- **Diseño:** `ui/CleanupPage.qml` sustituye botones blancos del estilo Qt por controles oscuros con acentos ámbar/azul/cian, confirma eliminación mediante diálogo personalizado y conserva distribución de tarjetas.
- **Versión:** `ui/Main.qml` actualiza rótulos a REBUILD 024.
- **Modificados:** `cleanup.py`, `ui/CleanupPage.qml`, `ui/Main.qml`, `README.md`, `tests/test_rebuild.py` y este historial. **Añadidos/eliminados:** ninguno.
- **Validación:** pruebas automatizadas y compilación; pendiente validación visual y purga nativa en Windows 11 (incluido token elevado).
- **Reversión:** conservar ZIP REBUILD 023 como respaldo. Ninguna operación elimina memoria privada de procesos.

## REBUILD 023 — Corrección de sintaxis de Limpieza (11-10-2026)

- **Base:** REBUILD 022; corrección puntual del fallo de arranque reportado en Windows al cargar `CleanupPage.qml:53:116` (`Unexpected token ;`).
- **Modificado:** `ui/CleanupPage.qml`: se retira el separador inválido entre dos objetos `Text` hermanos dentro de `RowLayout`, conservando distribución, estilos, lógica y controles; se normaliza la indentación de la propiedad `info`.
- **Pruebas:** `tests/test_rebuild.py` incluye regresión contra separadores inválidos entre elementos QML. Se valida la suite Python y la integridad del ZIP; el arranque nativo QML en Windows sigue pendiente de comprobar por el usuario.
- **Sin cambios:** motor de RAM/temporales, navegación, Tweaks, telemetría, reglas literales y demás interfaces. No se agregan archivos Python de producción.

## REBUILD 022 — Limpieza de sistema y RAM standby (11-10-2026)

- Base REBUILD 021. Se añade sección funcional de Limpieza, sin cambiar Resumen, Tweaks ni geometría aprobada.
- Añadidos: `cleanup.py` (operaciones reales aisladas y asíncronas) y `ui/CleanupPage.qml` (interfaz de limpieza).
- Modificados: `main.py`, `ui/Main.qml`, `tests/test_rebuild.py`, `README.md`, este historial.
- Temporales: analiza archivos de más de 24 horas en la carpeta Temp local del usuario, no sigue symlinks, limita recorrido, valida de nuevo antes de borrar, omite archivos bloqueados y exige confirmación explícita. Es eliminación permanente.
- RAM: llamada nativa `NtSetSystemInformation` clase 80, `MemoryPurgeStandbyList` valor 4; muestra RAM disponible antes, después y diferencia medidas por psutil. No garantiza 99 % ni libera memoria activa; puede fallar por privilegios.
- Ambas tareas se ejecutan en un hilo de trabajo; Qt publica resultado a través de polling de future en hilo principal.
- Pruebas: verificar contratos, compilación y aislamiento de ruta; validación nativa de Windows y permisos pendiente.
- Reversión del software: conservar el ZIP 021. Archivos borrados no son recuperables automáticamente: se advierte antes de confirmar.
- `cleanup.py` es el único nuevo Python y separa responsabilidad de escritura del módulo de telemetría (solo lectura).

## REBUILD 021 — Ampliación real del motor de Tweaks con V485 (11-10-2026)

- Base REBUILD 020; referencia CorePulse V485 del usuario. No se altera geometría, colores ni navegación.
- Añadido `tweaks_engine.py`: motor V485 adaptado sin dependencia de la estructura anterior, detección por objetivos, backups persistentes, aplicación y reversión verificada para tweaks adicionales cuando sean compatibles.
- Modificados `tweaks.py` (puente de las 44 entradas antes bloqueadas), `ui/TweaksPage.qml` (contador de disponibilidad real y textos de confirmación), `tests/test_rebuild.py`, `README.md`, historial.
- Siguen habilitados los 34 ajustes HKCU del motor REBUILD 020, manteniendo sus respaldos. El nuevo motor administra otros tweaks independientemente para evitar migraciones destructivas de snapshots.
- Bloqueadas nuevas aplicaciones de desinstalaciones sin rollback determinista (3) y desactivación de protecciones críticas/updates (6); su visualización no implica ejecución.
- Limitaciones: elevación automática UAC NO migrada del launcher antiguo; ajustes HKLM requieren ejecutar CorePulse como administrador y confirmar. Validación funcional en Windows 11 real pendiente.
- Eliminados: cachés de build/pruebas del ZIP. Archivo Python agregado: uno, necesario para aislar y auditar el motor V485 sin alterar la aplicación existente.

# CorePulse REBUILD — Historial y control de versiones

**Este es el único registro de versiones dentro del proyecto.** Antes de diseñar, crear, modificar o eliminar CUALQUIER elemento de CorePulse, leer y respetar obligatoriamente [`Reglas para crear Versiones nuevas.txt`](../Reglas%20para%20crear%20Versiones%20nuevas.txt) y este historial. La REBUILD 007 añade explícitamente una regla al TXT por solicitud del usuario; las reglas originales se conservan. Al publicar una entrega, añadir una nueva sección al principio del historial. No crear otra carpeta por versión ni copiar código antiguo dentro del proyecto. Los ZIP de respaldo se guardan fuera de esta carpeta.

## Reglas obligatorias para próximas entregas

1. **Proyecto pequeño y consolidado.** Crear archivos Python solo cuando haya una responsabilidad nueva claramente independiente; preferir mejorar archivos existentes cuando corresponda, sin convertirlos en archivos gigantes. Cada nuevo `.py` requiere justificación en el registro.
2. **Sin restos históricos.** No importar `gui/`, `main_legacy.py`, módulos Qt antiguos, caches, DLL copiadas, scripts obsoletos ni múltiples `.bat`. El REBUILD se desarrolla desde su propia base limpia.
3. **Una fuente de verdad.** Telemetría real o `N/A`, sin inventar sensores, FPS, temperaturas, alertas ni puntuaciones. La UI no modifica Windows; las acciones sensibles futuras requerirán confirmación y reversibilidad cuando aplique.
4. **Conservar lo aprobado.** No modificar diseño, navegación ni comportamientos fuera del alcance solicitado. Reusar componentes y estilos QML. Cada módulo pendiente debe permanecer explícitamente pendiente hasta implementarse.
5. **Control por versión.** Antes de entregar: describir alcance, archivos añadidos/modificados/eliminados, por qué, pruebas y resultados, pendientes conocidos y cómo volver a la versión anterior.
6. **Verificar, no suponer.** Pasar las pruebas posibles, revisar importaciones y arranque, inspeccionar el ZIP, e informar explícitamente lo no comprobado (por ejemplo ejecución visual Windows). No afirmar paridad funcional sin evidencia.
7. **ZIP completo y reproducible.** Distribuir únicamente el nuevo proyecto, sin artefactos locales, resultados temporales ni archivos `__pycache__`.
8. **TXT obligatorio para crear cualquier cosa.** Antes de crear o modificar versiones, archivos, componentes, funciones, diseños, iconos y scripts, leer y respetar íntegramente `Reglas para crear Versiones nuevas.txt` y este historial. El TXT debe viajar siempre en la raíz del ZIP; no cambiar sus reglas sin petición explícita del usuario. Retirar del árbol las copias/versiones obsoletas cuando ya no se usen.

---

## REBUILD 020 — Verificación del Registro al aplicar y restaurar (11-10-2026)

- **Alcance:** para los 34 tweaks ya habilitados, aplicar y restaurar ahora exige volver a leer Windows y confirmar que el Registro conserva el valor solicitado / original. Un fallo de verificación conserva el respaldo y no comunica éxito falso.
- **Sin paridad inventada:** los 44 ajustes restantes permanecen bloqueados hasta implementar operaciones comprobables y reversibles. Verificación del Registro no equivale a certificar efectos visibles en cada build de Windows 11.
- **Modificados:** `tweaks.py`, `tests/test_rebuild.py`, `README.md`, `versiones/HISTORIAL.md`; ningún archivo nuevo de producción, ningún cambio visual.
- **Pruebas:** contratos y casos adicionales de escritura/restauración que no se reflejan en el Registro. Prueba nativa de Windows pendiente.
- **Reversión:** respaldo ZIP REBUILD 019; los valores de `%APPDATA%` conservan compatibilidad de formato.

## REBUILD 019 — Eliminar cuadro de catálogo histórico (11-10-2026)

- **Reglas:** revisado el TXT obligatorio y el historial antes del cambio; ambos se preservan.
- **Alcance:** eliminado exclusivamente el recuadro informativo «Catálogo histórico» situado bajo el encabezado de Tweaks. Se conserva el banner transitorio de resultados de Apply/Restore, que aporta información funcional. No se altera la disposición de tarjetas, sus colores, navegación, ni el contador.
- **Seguridad:** catálogo de 78, 34 ajustes HKCU habilitados y 44 pendientes bloqueados sin cambios; copias originales y reversión conservadas. No se amplían capacidades de escritura.
- **Modificados:** `ui/TweaksPage.qml`, `README.md`, `tests/test_rebuild.py`, `versiones/HISTORIAL.md`. **Agregados o eliminados:** ningún archivo.
- **Pruebas:** comprobar contratos, pruebas automáticas, sintaxis Python y ZIP. Visualización real en Windows 11 pendiente.
- **Reversión:** extraer el ZIP 018 conservado fuera del proyecto; los respaldos del usuario en AppData permanecen compatibles.

## REBUILD 018 — Catálogo original V491 de 78 Tweaks (10-10-2026)

- **Lectura obligatoria previa:** se revisaron `Reglas para crear Versiones nuevas.txt` e historial. Se conserva el TXT íntegro y no se mezclan módulos legacy en el árbol actual.
- **Origen verificado:** RAR `CorePulse_V491_WINDOWS_FLAT_CONTROLS(3).rar`, motor histórico `core/maintenance/windows_tweaks.py`. Se analizaron estáticamente **78 entradas únicas** en 12 categorías. El RAR de origen NO se incluye en el proyecto.
- **Alcance:** 78 opciones visibles, 34 con implementación HKCU/REG_DWORD de una sola operación, no elevadas, de riesgo bajo/medio; 44 bloqueadas por compatibilidad, múltiples acciones, privilegios o riesgos. Esto NO es todavía paridad funcional de 78 tweaks.
- **Diseño:** 12 secciones con colores únicos, estados y explicaciones; el diseño de las tarjetas y navegación conserva la base REBUILD 017.
- **Seguridad:** mantiene confirmación explícita, respaldo del valor original, error cerrado y restauración exacta para los 34 aplicables. Los 44 pendientes son informativos y su ejecución está bloqueada a nivel de motor, no solo en QML. No desactiva protecciones, actualizaciones o servicios.
- **Compatibilidad:** conserva los ocho IDs de REBUILD 017 y la ruta de respaldo de AppData, evitando perder posibilidades de restaurar ajustes previamente aplicados.
- **Modificados:** `tweaks.py`, `ui/TweaksPage.qml`, `README.md`, `tests/test_rebuild.py`, `versiones/HISTORIAL.md`. No se añaden módulos Python ni carpetas del CorePulse V491.
- **Pruebas:** 55 pruebas unitarias automatizadas aprobadas con Registro simulado. No se probó la visualización QML ni la escritura real de Registro en Windows 11 desde este entorno.
- **Pendientes:** migrar de manera individual los 44 ajustes restantes, verificar variantes de Windows 11 y efectos reales; nunca afirmar mejoras de FPS sin mediciones.
- **Reversión:** conservar externamente ZIP 017 y reemplazar la carpeta de 018 por esa versión; respaldo durable por usuario mantenido en `%APPDATA%\\CorePulse\\rebuild\\tweaks_originales.json`.

## REBUILD 017 — Colores de categoría en Tweaks (10-10-2026)

- **Reglas leídas:** `Reglas para crear Versiones nuevas.txt` y este historial de REBUILD 016. TXT preservado byte por byte.
- **Cambio solicitado:** cada sección de Tweaks recibe identidad visual propia: Explorador cian, Barra de tareas violeta y Apariencia ámbar. Colores en cabeceras, líneas, tarjetas activas, estados y botones de aplicación. Contador dinámico de opciones disponibles en el catálogo.
- **Alcance real:** el ZIP base trae **8 tweaks**, no 78. No se agregaron 70 ajustes sin catálogo histórico verificable; la recuperación del conjunto original queda pendiente de disponer de su fuente e inspeccionar su seguridad y reversibilidad.
- **Modificados:** `ui/TweaksPage.qml`, `ui/Main.qml` (solo número de versión), `README.md`, `tests/test_rebuild.py`, `versiones/HISTORIAL.md`.
- **Añadidos/eliminados:** ninguno. `tweaks.py`, `main.py`, `telemetry.py`, resto de UI y TXT permanecen idénticos a la 016. El árbol mantiene 17 archivos.
- **Pruebas:** test de colores, contador y catálogo; regresión de pruebas existentes. No se ha certificado visualmente en Windows 11 desde este entorno.
- **Reversión:** conservar externamente el ZIP REBUILD 016 y reemplazar la carpeta por esa versión; los respaldos de ajustes de Windows siguen en AppData y son compatibles.

## REBUILD 016 — Tweaks Windows 11 funcionales, reversibles y con confirmación (10-10-2026)

- **Reglas revisadas:** leído el TXT `Reglas para crear Versiones nuevas.txt` y el historial antes de trabajar. TXT conservado **byte por byte**; no se incorpora ningún historial de versiones anteriores dentro del ZIP.
- **Referencia antigua:** auditado `core/maintenance/windows_tweaks.py` de CorePulse previo a Qt, conservando únicamente ocho definiciones de ajustes HKCU/REG_DWORD de bajo riesgo. No se copia el motor antiguo ni se reinstalan sus presets, operaciones de administrador o acciones de seguridad.
- **Implementados:** mostrar extensiones, mostrar archivos ocultos, abrir Explorador en Este equipo, vista compacta, alinear barra a la izquierda, ocultar Widgets, ocultar Vista de tareas y reducir transparencias. Solo para Windows 11 detectado; en otros sistemas quedan deshabilitados.
- **Interfaz:** un nuevo `ui/TweaksPage.qml` muestra categorías, estados leídos de Windows, explicación legible, hover, scroll oscuro responsivo, botón Actualizar, Volver y diálogo de confirmación separado para **Aplicar** y **Restaurar**. Ningún ajuste se aplica al abrir la pestaña. No se modifica el Resumen.
- **Motor de operaciones:** se justifica **1 nuevo Python**, `tweaks.py`, porque realiza escrituras del Registro y no corresponde mezclarlo con `telemetry.py` de solo lectura. La capa QML no puede escribir Registro directamente. Respaldos individuales de valores originales en `%APPDATA%\CorePulse\rebuild\tweaks_originales.json`; escritura atómica previa, restauración exacta del REG_DWORD anterior o eliminación de valores inexistentes originalmente; protección contra respaldos corruptos y tipos desconocidos. No se ejecutan scripts remotos, comandos privilegiados, reinicio de Explorer ni modificación de servicios, seguridad o actualizaciones.
- **Modificados:** `main.py` (conexión del nuevo objeto), `ui/Main.qml` (ruta y versión), `tests/test_rebuild.py`, `README.md`, este historial.
- **Añadidos:** `tweaks.py` y `ui/TweaksPage.qml`. **Eliminados:** ninguno; no se crean pruebas, BAT, proveedores o módulos de compatibilidad adicionales. Total **17 archivos**; 3 Python de producción, 8 QML y un BAT.
- **Conservados intactos:** `telemetry.py`, `ui/Overview.qml`, `ui/ComponentDetail.qml`, `ui/Glyph.qml`, gráfico, métricas, tarjetas, geometría y arrastre, `requirements.txt` y reglas TXT.
- **Pruebas:** unitarias del Registro simulado (estado, backup original, idempotencia, restauración, valor inexistente, backup corrupto, sistema no compatible y tipo no esperado), contratos QML y regresión REBUILD anterior. Pendiente comprobación real de efectos del Registro en Windows 11 con las confirmaciones explícitas.
- **Reversión de versión:** conservar fuera del proyecto `CorePulse_REBUILD_015_DETALLES_CLAROS.zip`. Para revertir ajustes aplicados, usar **Restaurar** en la pestaña de Tweaks antes de cambiar de versión; conservar la copia en AppData.

## REBUILD 015 — Componentes detallados y fáciles de entender (10-10-2026)

- **Reglas:** se leyó `Reglas para crear Versiones nuevas.txt` y este historial antes de los cambios. TXT conservado byte por byte. La REBUILD 014 es el respaldo externo, no se incluye en esta carpeta.
- **Referencia visual:** video del usuario comparando REBUILD 014 con CorePulse anterior a Qt. El antiguo mostraba uso, temperatura, frecuencia, potencia, especificaciones y sensores por núcleo. El nuevo separaba todo en una tabla larga; esta versión recupera niveles de información sin volverla demasiado técnica.
- **Pantallas CPU/GPU/RAM:** se reorganiza el único QML compartido `ui/ComponentDetail.qml` con secciones «Ahora mismo», «Cómo interpretarlo», «Conoce tu componente», módulo RAM/adaptadores gráficos y «Detalles avanzados». Por defecto se muestra primero lo esencial, con una frase sencilla por dato. Scroll oscuro responsive y botón Volver. No se duplican pantallas ni Python.
- **CPU:** se añade lectura **opcional** de potencia de CPU Package y temperaturas por núcleo a través de sensores CPU publicados por WMI o de la sonda de HardwareMonitor ya existente. Solo valores medidos válidos, con identificador CPU/hardware tipo CPU (y EC/SuperIO inequívoco en la sonda .NET). Se descartan valores GPU, SSD, cero, inválidos y obsoletos. El listado está limitado a 32 núcleos/sensores para evitar saturación. Nunca se infiere una potencia desde el % de uso.
- **Fuentes:** la procedencia de sensores adicionales (`cpuDetailSource`) queda disponible en detalles avanzados; cuando el proveedor no publica una lectura se indica `N/A`. La frecuencia estimada sigue etiquetada `(est.)`.
- **GPU:** se explica qué mide el uso NVIDIA y se presentan VRAM/capacidad, adaptadores y controlador solo si están disponibles. **RAM:** uso/capacidad/disponible y módulos físicos con capacidad, velocidad y fabricante en lenguaje claro. Los datos provienen de los mismos proveedores reales previos.
- **Modificados:** `ui/ComponentDetail.qml`, `telemetry.py`, `ui/Main.qml` (solo etiqueta de versión), `tests/test_rebuild.py`, `README.md`, este historial.
- **Añadidos/eliminados:** ningún archivo; **15 archivos totales, 2 `.py` de producción, 7 QML, 1 BAT y TXT obligatorio**. Se retiró la presentación antigua de tabla plana del QML, sustituida por el nuevo componente compartido. Nada de carpetas obsoletas o cachés.
- **Protegidos:** `Overview.qml`, `Glyph.qml`, gráfico, métricas principales, geometría/arrastre, navegación, SSD, `main.py`, requisitos y TXT idénticos a REBUILD 014.
- **Pruebas:** 46 contratos automatizados aprobados, validación de valores ausentes, WMI (potencia y sensores por núcleo), separación de CPU/GPU y estabilidad; verificar gráficamente el desplazamiento y los sensores nativos en Windows con PySide6. Es una integración incremental, no certificación de todos los sensores de cualquier portátil.
- **Reversión:** guardar `CorePulse_REBUILD_014_COMPONENTES.zip` fuera de la carpeta del proyecto.

## REBUILD 014 — Detalles de CPU, GPU y RAM desde el Resumen (10-10-2026)

- **Reglas leídas antes de trabajar:** `Reglas para crear Versiones nuevas.txt` y este historial. Se conserva el TXT original de REBUILD 013 exactamente, sin alteraciones.
- **Alcance solicitado:** al hacer clic en el **icono** de CPU, GPU o RAM del panel «Estado del sistema», abrir su pestaña de especificaciones, como sucedía en CorePulse anterior a Qt. No se activó navegación en SSD ni en tarjetas ajenas.
- **Referencia antigua:** páginas históricas `CpuPage.qml`, `GpuPage.qml` y `RamPage.qml` del CorePulse previo; se recupera su objetivo de mostrar identidad, carga, temperatura, memoria y datos de inventario, sin copiar el código viejo ni prometer paridad de todos sus sensores.
- **Navegación/UI:** `ui/MetricLine.qml` añade un botón de icono con hover y cursor de clic, conservando el tooltip existente; `ui/Overview.qml` emite la solicitud de componente; `ui/Main.qml` enruta por identificadores estables `cpu`, `gpu`, `ram`, habilita «Más módulos» y permite volver al Resumen. Se reutiliza **una sola** nueva vista `ui/ComponentDetail.qml` con tarjetas de lecturas y especificaciones adaptables, scroll oscuro y estado `N/A` si faltan sensores.
- **Inventario Windows solo lectura:** `telemetry.py` obtiene una sola vez y en segundo plano CPU (`Win32_Processor`: fabricante, socket, núcleos, hilos), adaptadores gráficos (`Win32_VideoController`: nombre/controlador) y memoria (`Win32_PhysicalMemory`: slot, capacidad, velocidad, tipo SMBIOS, fabricante, referencia). La cantidad de núcleos/hilos puede usar el recuento real `psutil.cpu_count()` como respaldo. Se conserva la RAM en vivo `total - disponible` y la telemetría NVIDIA/NVML ya existente. Solo se asocia un controlador GPU si el nombre coincide explícitamente: no se confunde Intel/AMD/NVIDIA.
- **Seguridad y veracidad:** no instala drivers ni ejecuta mantenimiento; ninguna lectura inventada. Mientras WMI está consultando, el inventario se marca evaluándose; si Windows no expone algo, aparece `N/A`. Las temperaturas/frecuencias mantienen proveedores, caducidad y marcadores de estimación de REBUILD 013.
- **Modificados:** `telemetry.py`, `ui/MetricLine.qml`, `ui/Overview.qml`, `ui/Main.qml`, `tests/test_rebuild.py`, `README.md`, este historial.
- **Añadidos:** `ui/ComponentDetail.qml` (**1 componente QML reutilizable**). **Eliminados:** ninguno; no hay código obsoleto nuevo que duplicar. El proyecto consta de **15 archivos**, **2 Python de producción**, **7 QML**, **1 BAT**, más TXT obligatorio; no se agrega ningún `.py`.
- **Pruebas:** 41 contratos y casos de lectura aprobados, incluidos validación de SMBIOS, inventarios incompletos, no confundir drivers iGPU/dGPU y rutas de navegación; comprobación de integridad del ZIP. La presentación y `Get-CimInstance` deben comprobarse realmente en Windows con PySide6.
- **Reversión:** conservar `CorePulse_REBUILD_013_CPU_TEXTO_SCROLL.zip` fuera de la carpeta.

## REBUILD 013 — Frecuencia legible y scroll de Lecturas disponibles (10-10-2026)

- **Antes de modificar:** se leyeron el TXT obligatorio y este historial; el TXT se conserva byte por byte.
- **Incidencias reproducidas en video de Windows:** el prefijo `≈` junto a la frecuencia de CPU se veía extraño y el scrollbar por defecto aparecía como una barra blanca que tapaba los valores de las lecturas.
- **Cambios funcionales:** solo presentación. La frecuencia estimada se muestra como `4.21 GHz (est.)` en lugar de `≈4.21 GHz`, con el origen «Estimación Windows…» conservado en el tooltip y en la lista. Frecuencia medida continúa sin sufijo. Los cálculos y muestras no cambian.
- **Scroll:** en `ui/Main.qml` se reemplazó la barra visual por defecto por una barra Qt Quick Controls oscura de 9 px y se reservó un canal de 16 px a la derecha del listado, evitando que la barra tape estados o cifras. Mantiene desplazamiento vertical, encabezado fijo y siete filas reales.
- **Modificados:** `ui/Overview.qml`, `ui/Main.qml`, `telemetry.py` (solo etiqueta de las lecturas), `tests/test_rebuild.py`, `README.md` y este historial.
- **Añadidos o eliminados:** ninguno; no se crean archivos `.py` ni QML adicionales, permanecen 14 archivos, 2 Python de producción y 1 BAT. Se eliminó el prefijo de render `≈` y la barra visual por defecto en la pantalla de lecturas.
- **Protegidos:** UI del Resumen, gráficos, iconos, lecturas CPU/GPU/RAM/SSD, contador verificable de siete métricas, hover, navegación, arrastre y tamaño universal.
- **Pruebas:** suite completa del REBUILD y nuevos contratos de representación de frecuencia y scroll. La interacción real y escalado DPI de Qt Windows requieren verificación visual en ese equipo.
- **Reversión:** conservar `CorePulse_REBUILD_012_LECTURAS_DISPONIBLES.zip` fuera de la carpeta del proyecto.

## REBUILD 012 — Lecturas disponibles: detalle interactivo y 7 verificaciones (10-10-2026)

- **Reglas:** se leyeron `Reglas para crear Versiones nuevas.txt` y este historial ANTES de cualquier cambio; el TXT se conserva idéntico al de REBUILD 011.
- **Nombre inalterado por solicitud expresa:** la tarjeta sigue llamándose **«Lecturas disponibles»** (NO «Trazabilidad»). El mismo rótulo encabeza la pantalla de detalle.
- **Alcance:** al pasar el mouse sobre la tarjeta se realzan discretamente color/borde; al pulsarla abre una pantalla que permite verificar las siete lecturas. Volver regresa a Resumen. Las otras tarjetas no ejecutan operaciones ni simulan navegación.
- **Contador real:** se reemplaza el conteo de cuatro indicadores por siete comprobaciones: uso CPU, frecuencia CPU, temperatura CPU, uso RAM, uso GPU, temperatura GPU y uso/capacidad VRAM. `7/7` solo si las siete son válidas; 0 y otros valores son legítimos. El SSD sigue en su bloque, pero NO se cuenta como temperatura/VRAM.
- **Fuente y seguridad:** se reutilizan las lecturas reales existentes y se añade `memory.used,memory.total` de NVIDIA-SMI en la consulta de GPU; se descartan muestras antiguas y valores de VRAM inválidos. Se muestra el origen de cada dato, distinguiendo frecuencia estimada `≈`; estados Disponible/Evaluando/No disponible, sin inventar sensores.
- **Archivos modificados:** `telemetry.py`, `ui/StatTile.qml`, `ui/Overview.qml`, `ui/Main.qml`, `tests/test_rebuild.py`, `README.md` y `versiones/HISTORIAL.md`. **Añadidos/eliminados: ninguno**; 14 archivos, 2 `.py` de producción, 1 `.bat`. Los componentes QML de iconos, gráfico e indicadores, el arranque, temas/diseño y las reglas no cambian.
- **Pruebas:** regresión del REBUILD, siete lecturas con válidos/ausentes/evaluándose, GPU/VRAM real, navegación y nombre estable. La prueba interactiva nativa Qt en Windows sigue pendiente.
- **Reversión:** ZIP externo `CorePulse_REBUILD_011_CPU_TEMP_LEGACY_RECUPERADA.zip`.

## REBUILD 011 — Recuperación de temperatura CPU del motor clásico (10-10-2026)

- **Reglas leídas:** TXT original y este historial antes de implementar. El TXT se conserva byte por byte.
- **Diagnóstico confirmado:** la REBUILD 010 solo consultaba LibreHardwareMonitor/OpenHardwareMonitor cuando otra aplicación publicaba WMI; la versión anterior al Qt leía directamente `HardwareMonitor`/`LibreHardwareMonitorLib`, y tenía compatibilidad para temperaturas CPU de portátiles publicadas bajo EC/SuperIO/Motherboard. Esa segunda ruta se perdió en el REBUILD.
- **Solución:** `telemetry.py` consulta primero WMI y, si no hay temperatura CPU, ejecuta una sonda DIRECTA en un proceso Python aislado usando `HardwareMonitor`/`pythonnet`, tal como hacía la ruta compatible del proyecto clásico. Activa únicamente los grupos CPU, placa y controladores; recorre sensores/subhardware, selecciona CPU Package/Tctl-Tdie/cores por prioridad y rechaza GPU, SSD, batería, ambient, 0 °C, temperatura inválida y distancia a TjMax. Siempre hay trazabilidad de origen y nombre físico del sensor.
- **Seguridad y rendimiento:** lectura en trabajador de fondo, `timeout=8`, caché de éxito (10 s) y de ausencia (45 s), sin descarga automática, cambios en Windows ni instalación silenciosa de driver. Si falta acceso de hardware o paquete, `N/A` y causa en tooltip.
- **Dependencias necesarias:** `HardwareMonitor>=1.2.1,<2` y `pythonnet>=3.1,<4` en `requirements.txt`, instalables por el usuario con pip del mismo Python 3.12 que ejecuta CorePulse. Para algunos equipos pueden requerirse permisos o driver de hardware ya instalado; no se instalará PawnIO sin consentimiento explícito.
- **Modificados:** `telemetry.py`, `requirements.txt`, etiquetas de `ui/Main.qml`, `tests/test_rebuild.py`, `README.md` y este historial. **Añadidos/eliminados:** 0 archivos; **2 Python de producción**, **1 BAT**, **14 archivos totales**.
- **Protegidos:** todo el layout, iconos, Resumen, gráfica, sensores RAM/SSD y GPU, tamaño estilo Steam, historial y reglas anteriores. El backend del REBUILD no importa los árboles antiguos.
- **Pruebas:** validación sintáctica, fuente embebida, prioridad WMI/directo, límites de temperatura, caché y regresiones anteriores. Pendiente confirmar lectura de hardware directamente en Windows del usuario.
- **Reversión:** conservar ZIP REBUILD 010 fuera de esta carpeta.

## REBUILD 010 — Precisión y procedencia de la telemetría (10-10-2026)

- **Reglas obligatorias leídas antes de cambiar nada:** `Reglas para crear Versiones nuevas.txt` y `versiones/HISTORIAL.md`. TXT conservado byte por byte.
- **Solicitud:** resolver frecuencia CPU fija en la nominal, aclarar diferencia de uso GPU con Administrador de tareas, preservar RAM/SSD correctos, temperatura CPU solo real.
- **Modificados:** `telemetry.py`, `ui/MetricLine.qml`, `ui/Overview.qml`, rótulos de versión de `ui/Main.qml`, `tests/test_rebuild.py`, `README.md`, `versiones/HISTORIAL.md`.
- **Archivos añadidos/eliminados:** ninguno (14 archivos, 2 Python de producción y un BAT).
- **CPU:** ahora se priorizan clocks físicos WMI de sensores CPU recientes (hasta 20 s). Como alternativa se consulta PDH `% Processor Performance` y la frecuencia nominal WMI `Win32_Processor.MaxClockSpeed` para obtener una **estimación** de GHz, marcada `≈` en pantalla y declarada en tooltip. Sin lecturas válidas, `N/A`. Se retiró el contador `Processor Frequency` obsoleto, frecuentemente fijo en la frecuencia base. No se confunde frecuencia calculada con un sensor directo.
- **GPU:** conserva uso real `utilization.gpu` de NVIDIA-SMI/NVML y temperatura GPU; descarta muestras de más de 5 s y muestra en tooltip el origen para explicar discrepancias frente a Task Manager. No inventa ni promedia porcentajes de motores distintos.
- **Temperatura CPU:** lectura WMI vigente de un monitor de hardware o `N/A`; se invalidan temperaturas de más de 20 s sin actualización. No se instala un monitor ni se fuerza un sensor.
- **RAM/SSD e interfaz visual:** sin cambios en las fuentes y cálculos de memoria/disco, sidebar, iconos, tamaños, tarjetas, ventana, gráficos ni navegación. Tooltips solo informativos.
- **Pruebas:** suites de base y nuevas validaciones de Turbo Boost estimado, ausencia/NaN, prioridad de sensores, fuentes en QML, proveedor WMI simulado e invariantes. Faltan verificaciones nativas PDH/CIM/NVIDIA/LHM y Qt en Windows.
- **Reversión:** el ZIP de REBUILD 009 permanece fuera del proyecto, nunca se copia dentro.

## REBUILD 009 — Telemetría CPU, GPU, RAM y almacenamiento (10-10-2026)

- **Reglas leídas:** `Reglas para crear Versiones nuevas.txt` y este historial antes de modificar. Se mantiene el TXT original byte por byte dentro del ZIP.
- **Solicitud:** corregir frecuencia/temperatura CPU, porcentaje NVIDIA GPU, uso RAM y mostrar nombre real de la unidad del sistema debajo de SSD.
- **Modificados:** `telemetry.py`, `ui/Overview.qml`, rótulos de versión de `ui/Main.qml`, `tests/test_rebuild.py`, `README.md` y `versiones/HISTORIAL.md`.
- **Añadidos/eliminados:** 0 archivos nuevos, 0 archivos completos eliminados; sigue en **14 archivos, 2 Python de producción y 1 BAT**. Se retiró la lectura obsoleta de `psutil.cpu_freq().current` como frecuencia de CPU dinámica en Windows y se reemplazó el cálculo de RAM que mezclaba `mem.percent` y `mem.used`.
- **CPU frecuencia:** utiliza PDH `Processor Information(_Total)\Processor Frequency` de Windows, con respaldo en los clocks CPU reales expuestos por WMI de LHM/OHM. Sin valor válido -> `N/A`.
- **CPU temperatura:** WMI de LibreHardwareMonitor/OpenHardwareMonitor, priorizando CPU Package/Tctl-Tdie; filtrado de sensores de GPU, 0 °C y valores inválidos. No se instala ni activa software o servicios.
- **GPU NVIDIA:** consulta real `nvidia-smi` en hilo de fondo cada ~2 s, eliminando porcentajes obsoletos; el indicador NVML no debe interpretarse como idéntico a los motores GPU de Task Manager. GPU no NVIDIA no soportada aún -> N/A.
- **RAM:** uso GB calculado con `total - available`, porcentaje derivado del mismo par y cifras expresadas en GiB; comparables internamente.
- **SSD:** mantiene medición de unidad del sistema y obtiene el modelo físico asociado a la letra mediante PowerShell Get-Partition/Get-Disk en un hilo; visualiza modelo sobre GB, o `Modelo N/A (C:\)` cuando Windows no devuelve nombre.
- **QML:** reemplazó comparaciones `===null` por validación `null/undefined/NaN` de números; ya no muestra `Temp. undefined °C`.
- **Pruebas:** se conservaron contratos anteriores y se añadieron pruebas de normalización, CPU térmico, RAM, NVIDIA y correlación de disco (PowerShell simulado). Falta comprobar la ejecución PDH/CIM/NVIDIA en Windows.
- **Protegidos:** ventanas tipo Steam, arrastre, sidebar, iconos HD, gráfico, tarjetas, navegación, colores y TXT de reglas sin cambios.
- **Reversión:** conservar `CorePulse_REBUILD_008_BENCHMARK_CORREGIDO.zip` fuera del proyecto.

## REBUILD 008 — Icono Benchmark corregido (10-10-2026)

- **Problema observado en Windows:** el icono de Benchmark parecía aplastado o deformado mientras el resto de iconos se veía bien.
- **Alcance:** corregir solo el símbolo `gauge` dentro de `ui/Glyph.qml`. Se cambió su arco SVG `A` por dos curvas Bézier `C`, con aguja, base y centro legibles a 22 píxeles lógicos y escalados DPI.
- **Modificados:** `ui/Glyph.qml`, los rótulos de versión en `ui/Main.qml`, `tests/test_rebuild.py`, `README.md` y este historial. **Sin añadidos de archivos ni Python.**
- **Eliminación de obsolescencia:** se retiró el trazado anterior del `gauge`, ya no necesario. No se conservaron variantes duplicadas ni implementaciones antiguas.
- **Protegido:** los demás 44 iconos, el layout del sidebar y Resumen, la telemetría y el cálculo de tamaño/arrastre permanecen sin cambios.
- **Reglas:** leído `Reglas para crear Versiones nuevas.txt` y este historial antes de modificar; TXT incluido literalmente sin cambios.
- **Pruebas:** suite del REBUILD, geometría del icono de Benchmark y comparación de archivos. La apariencia nativa definitiva debe comprobarse en Windows.
- **Reversión:** conservar `CorePulse_REBUILD_007_ICONOS_NITIDOS_DPI.zip` como copia de respaldo fuera del proyecto.

## REBUILD 007 — Iconos nítidos y reglas obligatorias (10-10-2026)

- **Objetivo:** corregir los bordes pixelados observados en los iconos vectoriales de REBUILD 006, manteniendo sus símbolos y el diseño del sidebar.
- **Modificados:** `ui/Glyph.qml`, `ui/Main.qml`, `tests/test_rebuild.py`, `README.md`, `versiones/HISTORIAL.md` y el TXT obligatorio a petición del usuario.
- **Regla incorporada:** queda escrito en el TXT que **cada nueva versión, componente, función o cambio debe respetar previamente el TXT y el historial**. No se alteran las reglas previas del usuario.
- **Renderizado:** se elimina `transform: Scale` y la `Shape` fija a 24×24. Las instrucciones SVG se adaptan con sus parámetros correctos a los píxeles lógicos reales del icono y la Shape ocupa el tamaño final de destino. Grosor mínimo de línea 1,8 px lógicos para reducir trazos débiles con DPI fraccionario. Se prefiere `Shape.CurveRenderer` cuando está presente (Qt 6.7+) por sus bordes con antialiasing independiente de MSAA; versiones anteriores usan `Shape.GeometryRenderer`.
- **Iconos del sidebar:** de 21×21 a 22×22 dentro del mismo fondo de 26×26; sidebar, paneles, gráfico y telemetría sin cambios.
- **Limpieza:** se eliminó la ruta obsoleta de escalado por `transform: Scale`, sin agregar `.py`, QML nuevo, fuentes ni imágenes externas. **14 archivos totales**, dos `.py` de producción, un `.bat`.
- **Pruebas:** contratos y validación matemática de coordenadas SVG, arcos y DPI 100/125/150/200 %; comparación de archivos protegidos y prueba de integridad del ZIP.
- **Pendiente:** aspecto final de Qt Quick Shapes y antialiasing deben verificarse en Windows; las pruebas estáticas no certifican renderizado nativo de GPU.
- **Reversión:** conservar `CorePulse_REBUILD_006_ICONOS_VECTOR_HD.zip` como respaldo externo.

## REBUILD 006 — Iconos vectoriales HD y reglas permanentes (10-10-2026)

- **Objetivo:** mejorar la nitidez de los iconos del sidebar en equipos Windows con resoluciones y DPI variables, y hacer que las reglas del usuario viajen dentro del proyecto.
- **Archivos modificados:** `ui/Glyph.qml`, `ui/Main.qml`, `tests/test_rebuild.py`, `README.md`, `versiones/HISTORIAL.md`.
- **Archivo añadido:** `Reglas para crear Versiones nuevas.txt`, copia literal del documento proporcionado por el usuario.
- **Archivos eliminados:** ninguno completo. Se eliminó el render anterior basado en `Canvas` dentro de `ui/Glyph.qml`, sustituido por un trazado vectorial `QtQuick.Shapes.Shape`/`PathSvg`, sin añadir `.py`, `.qml` ni recursos PNG/SVG.
- **Iconos:** todos los iconos existentes mantienen su sentido, proporciones y acentos; los accesos adicionales tienen ahora siluetas específicas (batería, juego, controladores, audio, Wi-Fi, etc.). Las bases tenues del sidebar y la navegación mantienen el diseño aprobado de REBUILD 005.
- **DPI:** se escala desde una geometría vectorial 24×24 hacia el tamaño del componente; no se genera un bitmap pequeño para ampliarlo.
- **Inventario esperado:** **14 archivos, 2 Python de producción, 6 QML, 1 BAT, 1 TXT obligatorio**. Sin cachés ni versiones antiguas en el ZIP.
- **Pruebas:** contratos sobre unicidad de trazados, rutas declaradas, QML Shape/PathSvg, reglas, no contaminación del proyecto, comparación de archivos protegidos y ZIP. **Pendiente:** prueba visual nativa con PySide6 en Windows, especialmente DPI de 125 %/150 % y el colapso del sidebar.
- **Reversión:** conservar `CorePulse_REBUILD_005_ICONOS_PULIDOS.zip` fuera de esta carpeta.

## REBUILD 005 — Pulido visual de iconos del sidebar (10-10-2026)

- **Alcance solicitado:** pulir todavía más el estilo visual de los iconos del sidebar, manteniendo la estructura compacta del REBUILD 004.
- **Modificados:** `ui/Glyph.qml`, `ui/Main.qml`, `tests/test_rebuild.py`, `README.md` y este `versiones/HISTORIAL.md`.
- **Añadidos/eliminados:** ninguno; se mantiene la base compacta del REBUILD con **13 archivos funcionales** y sin nuevos `.py` de producción.
- **Iconografía:** se redibujó el set vectorial con formas más limpias, esquinas redondeadas y siluetas más reconocibles para dashboard, benchmark, diagnóstico, salud, limpieza, tweaks, alertas, tendencias, historial, temas y CorePulse AI.
- **Sidebar:** cada icono del menú ahora vive dentro de una base visual sutil al hacer hover o al estar activo, mejorando legibilidad sin introducir imágenes externas ni colores raros.
- **Pruebas:** se actualizan las comprobaciones del REBUILD para reflejar el nuevo pulido visual y se conserva la validación de inventario mínimo.
- **Reversión:** conservar `CorePulse_REBUILD_004_ICONOS_SIDEBAR.zip` como respaldo.

## REBUILD 004 — Reajuste de iconos del sidebar (10-10-2026)

- **Alcance solicitado:** dejar de usar iconos genéricos o repetidos en la barra lateral, conservando el sidebar alineado de REBUILD 003.
- **Modificados:** `ui/Main.qml`, `ui/Glyph.qml`, `tests/test_rebuild.py`, `versiones/HISTORIAL.md` y `README.md`.
- **Añadidos/eliminados:** ninguno; el proyecto sigue con **13 archivos, 2 `.py` de producción y 1 `.bat`**.
- **Sidebar:** se reasignan iconos para que cada acceso principal tenga identidad propia: Resumen `dashboard`, Benchmark `gauge`, Iniciar diagnóstico `scan`, Centro de salud `health_shield`, Limpieza `broom`, Tweaks `sliders`, Alertas `bell_alert`, Tendencias `trend_up`, Historial `history` y CorePulse AI `spark_ai`.
- **Iconografía:** `ui/Glyph.qml` se amplía con un set vectorial nuevo, manteniendo el mismo sistema monocromático sin imágenes ni fuentes externas. Los iconos antiguos todavía compatibles no se eliminan si siguen siendo usados por otras zonas de la UI.
- **Pruebas:** se añaden comprobaciones de unicidad/rol de iconos del sidebar además de las pruebas previas del REBUILD. La validación visual final sigue siendo en Windows.
- **Reversión:** conservar `CorePulse_REBUILD_003_SIDEBAR_ALINEADO.zip` como respaldo.

## REBUILD 003 — Sidebar sin marca y alineado (10-10-2026)

- **Alcance solicitado:** retirar únicamente el icono de CorePulse con el texto "COREPULSE / Herramientas del equipo" del sidebar y subir las secciones de navegación para aprovechar ese espacio. Conservar el botón hamburguesa.
- **Modificados:** `ui/Main.qml`, `tests/test_rebuild.py`, `versiones/HISTORIAL.md` y `README.md`.
- **Añadidos/eliminados:** ninguno; continúa en **13 archivos, 2 `.py` de producción y un solo `.bat`**.
- **Interfaz:** se suprime el bloque de marca del sidebar; la cabecera lateral pasa de 92 a 52 píxeles lógicos, de modo que `MONITOREO` y los accesos siguientes suben 40 píxeles lógicos. El ancho del sidebar no cambia y la lista conserva su desplazamiento vertical para monitores pequeños.
- **Movimiento:** se preserva el arrastre nativo a través de la franja superior lateral libre, sin cubrir el botón de colapso; la cabecera principal, bordes de redimensionamiento, F11 y Escape no cambian.
- **Versión:** el rótulo de la ventana y subtítulo del Resumen se actualizan a Rebuild 003. El contenido del Resumen, lecturas de telemetría, gráficos y módulos pendientes no se modifican.
- **Pruebas:** `pytest` de contratos del REBUILD; comparación de archivos respecto de REBUILD 002. El renderizado y el arrastre nativos requieren comprobación en Windows.
- **Reversión:** conservar `CorePulse_REBUILD_002_VENTANA_STEAM_ARRASTRE.zip` como respaldo separado.

## REBUILD 002 — Ventana estilo Steam y movimiento (10-10-2026)

- **Alcance:** corregir únicamente el tamaño inicial, centrado y movimiento/redimensionado de la ventana Qt sin cambiar el Resumen, métricas ni sidebar.
- **Modificado:** `main.py`, `ui/Main.qml`, `tests/test_rebuild.py`, `README.md`, este `versiones/HISTORIAL.md`.
- **Añadidos/eliminados:** ninguno. Siguen 13 archivos totales y **solo 2 `.py` de producción**.
- **Tamaño inicial:** 1280×720 píxeles lógicos como referencia Steam en pantallas con espacio suficiente. En pantallas pequeñas, 90 % de la **superficie útil** de Windows (`availableGeometry()`, sin barra de tareas), centrado y respetando escalado DPI. Mínimos adaptados al monitor para no quedar fuera de la pantalla.
- **Arrastre:** desde la zona superior de la cabecera (excluyendo los controles) o el encabezado del sidebar; movimiento nativo con `startSystemMove()` y fallback manual cuando no está disponible. Doble clic en la zona de arrastre maximiza/restaura. Se habilitaron bordes izquierdo y superior para cambiar tamaño, además de derecho/inferior.
- **Regresión:** controles de ventana y botón hamburguesa preservados. Atajos F11/Escape se conservan.
- **Pruebas:** ver `tests/test_rebuild.py`; probar movimiento/redimensionado de manera nativa en Windows.
- **Pendiente:** verificación visual en Windows con PySide6 instalado; sigue siendo una base de reconstrucción, no paridad total con el proyecto antiguo.
- **Reversión:** conservar el ZIP de REBUILD 001 base documentada fuera de este directorio.

## REBUILD 001 — Base limpia (10-10-2026)

- **Objetivo:** iniciar CorePulse como aplicación Qt independiente con pocos archivos.
- **Estructura:** `main.py` (arranque), `telemetry.py` (fuente de datos reales), seis QML reutilizables, un `.bat`, `requirements.txt`, `README.md` y pruebas iniciales.
- **Estado funcional:** ventana, navegación, Resumen inicial y telemetría CPU/RAM/disco; GPU mediante `nvidia-smi` si está disponible; módulos futuros marcados como pendientes.
- **No implementado:** diagnóstico avanzado, benchmark, IA, temas completos, RTSS, operaciones de Windows. No simular estas funciones.
- **Pruebas declaradas en la entrega inicial:** siete pruebas del REBUILD; **pendiente:** comprobar QML nativo en Windows.
- **Respaldo:** conservar fuera de esta carpeta el proyecto antiguo V39; no usarlo como base de código.

## REBUILD 001 — Incorporación del historial (10-10-2026)

- **Motivo:** evitar la fragmentación y pérdida de trazabilidad de versiones anteriores.
- **Añadido:** `versiones/HISTORIAL.md` (único archivo de registro; ampliar en próximas versiones).
- **Modificado:** `README.md` para señalar las reglas y el historial; `tests/test_rebuild.py` para actualizar su control de inventario (12 → 13 archivos).
- **Python y QML:** sin modificaciones; **archivos `.py` nuevos: 0**.
- **Pruebas:** ejecutar pruebas existentes y verificar el archivo ZIP, sin afirmar ejecución visual Qt en Windows.
- **Pendiente:** usar este registro desde REBUILD 002 en adelante y confirmar la carga de interfaz en Windows.

## REBUILD 041 — SSD separado + progreso
- Se retiró Almacenamiento del set principal del Centro de Salud.
- El componente SSD del Resumen ahora abre directamente Almacenamiento.
- Se añadieron barras de progreso al Análisis de Windows y a Reparación de Windows.
- Se ajustó el flujo por defecto del Centro de Salud en equipos sin batería.
- Pruebas actualizadas y validadas: 123 PASS.

## REBUILD 042 — Recuperación del sistema
- Se agregó el módulo Recuperación del sistema al Centro de salud.
- Se integró lectura real de protección del sistema, puntos de restauración y Windows RE.
- Se añadió creación manual de punto de restauración con confirmación explícita y registro local.
- Se añadieron accesos directos a Restaurar sistema y a la Configuración de recuperación de Windows.
- Pruebas validadas: 124 PASS.

## REBUILD 043 — Recuperación sin errores de PowerShell
- Corregida la consulta PowerShell de puntos de restauración (sintaxis y fechas WMI).
- Paso de scripts con `-EncodedCommand` UTF-16LE y lectura de JSON UTF-8.
- Los errores de consulta ya no aparecen como texto corrupto en QML.
- Diferenciados N/A (dato inaccesible), cero puntos confirmado y estado de protección no confirmado.
- Parser de WinRE en español e inglés.
- Creación de puntos verificada contra nuevas secuencias, sin confirmar éxitos ficticios.
- 130 pruebas automatizadas PASS; ejecución nativa Windows pendiente.

## REBUILD 044 — Historial de cambios (12-10-2026)
- Basada exclusivamente en REBUILD 043 y en sus reglas originales.
- Centro de Salud incorpora pestaña «Historial»: registro de Tweaks persistente, informes de integridad DISM/SFC, historial local Windows Update y puntos de restauración de Windows.
- Cronología real en lectura, con fechas, resultados y filtros. Los errores de consulta se indican como N/A, nunca como cero eventos confirmado.
- Cuatro fuentes consultadas de manera independiente en segundo plano, barra de progreso por etapas realmente terminadas; no se ejecutan acciones de mantenimiento.
- Se reutiliza la consulta de restauración corregida en V043 en lugar de duplicar PowerShell. El motor de Tweaks y todos los anteriores se conservan sin cambios.
- Nuevo archivo modular necesario: `core/health/history.py`; icono nuevo `file_clock` vectorial.
- Pruebas: **135 PASS** (incluyen auditoría, informes, fuentes inaccesibles, orden cronológico y navegación). QML y Windows Update COM pendientes de validación nativa.

## REBUILD 045 — Estado general de salud (11-10-2026)
- Base exclusiva: REBUILD 044 con su archivo de reglas.
- Módulo general de salud basado en CPU/GPU, RAM, salud física y espacio de unidades, batería según presencia real, códigos de dispositivos y Windows RE.
- Estado cualitativo y cobertura verificable; no se inventa un porcentaje global de salud. Valores N/A permanecen sin verificar.
- Accesos de cada indicador a su módulo real y pestañas adaptables al ancho de ventana.
- Se corrigieron imports, instancias y conexiones duplicados de Recuperación e Historial que venían de la V044.
- Archivo modular nuevo `core/health/system_health.py`; no hay motores antiguos copiados ni módulos obsoletos añadidos.
- 140 pruebas automatizadas PASS; ejecución gráfica Qt/Windows pendiente de validación.

## REBUILD 046 — Alertas térmicas, RAM y reinicio opcional
- Base exclusiva: REBUILD 045 con el TXT de reglas conservado.
- CPU: sondeo de sensores más frecuente, prioridad de lectura directa si hay sensor real, WMI como alternativa, caducidad más rápida para evitar datos obsoletos.
- CPU ≥90 °C y GPU ≥85 °C: la temperatura se destaca en rojo. RAM ≥90 %: icono, barra y lectura se destacan en rojo.
- Tiempo desde arranque ≥10 horas: tarjeta e icono rojos; botón Reiniciar con confirmación. Solicita reinicio Windows con plazo de 60 s y permite cancelarlo. Nunca se ejecuta al abrir CorePulse ni al alcanzar el umbral sin acción explícita.
- Sin nuevos archivos .py ni modificaciones a motores restantes; REAL_OR_NA conservado.
- 144 pruebas automatizadas PASS; Qt/Windows nativo pendiente.


## REBUILD 048 — Integración Centro de Salud y Test de Audio en Alertas Térmicas
- Base exclusiva: ZIP entregado por usuario CorePulse REBUILD 046 «Alertas térmicas, RAM y reinicio opcional». No partir del antiguo V046 «Paridad inicial» ni sustituir por V047 completa.
- Preservados los motores de CPU, GPU, RAM, tiempo desde arranque y reinicio/cancelación con confirmación de V046.
- Migrada la portada de Centro de Salud de V047: tarjetas de acceso en vez de pestañas superiores; Volver retorna al panel principal.
- Test de Audio de salida integrado (izquierdo / ambos / derecho) con tonos WAV PCM locales; configuración de sonido de Windows disponible.
- Portada mantiene lecturas verificables plegadas, Batería/Windows/Reparación/Recuperación/Historial; Rendimiento permanece pendiente.
- Corregida normalización WinRE en la cobertura de salud.
- Sin nuevos módulos Python ni archivos obsoletos añadidos; 148 pruebas automatizadas PASS.
- Renderizado y sonido reales aún pendientes de comprobar en Windows 11.


## REBUILD 049 — Rendimiento: energía reversible y estabilidad (migración parcial V485)
- Base: V048 Alertas Térmicas + Centro de Salud + Audio, no sustituye motores heredados.
- Se restauró en el Centro de Salud la selección de planes de energía realmente existentes en Windows, con confirmación, comprobación y rollback persistente.
- Nueva vista de temperaturas reales CPU/GPU, con estado de throttling N/A donde falta evidencia directa; sin FPS inventados.
- Lectura conservadora de ejecutables Steam/Epic identificados por ruta, sin afirmar un Game Boost activo.
- Se evita crear planes, modificar ajustes sin consentimiento y confundir riesgo térmico con throttling confirmado.
- Game Boost completo, biblioteca avanzada y benchmark original de V485 permanecen pendientes y documentados.
- Un solo archivo Python de producción nuevo (`core/health/performance.py`), sin nuevas páginas QML.
- 155 pruebas automatizadas PASS; ejecución QML y pruebas de powercfg en Windows quedan pendientes.

## REBUILD 050 — Juego activo estilo Steam (migración incremental)
- Base única REBUILD 049; sin cambios en módulos de energía, RAM, CPU/GPU, reinicio y ajustes de Windows.
- Tarjeta de juego en ejecución con imagen Steam real local, título verificado desde appmanifest, plataforma, estado y duración basada en inicio real del proceso.
- Sondeo no bloqueante de Steam/Epic cada 2,5 segundos únicamente mientras Rendimiento está abierto.
- Imagen externa opcional con clic explícito (no transmisión de biblioteca al abrir la aplicación).
- Estado vacío y detección de cierres reales; FPS mantiene N/A y Game Boost permanece pendiente de migración.
- 159 pruebas automatizadas PASS; renderizado nativo Windows 11 pendiente.

## REBUILD 051 — Tarjeta de juego remaquetada
- En Rendimiento, la tarjeta de juego activo ahora muestra Estado, Tiempo activo y Origen debajo de la carátula.
- Se mantiene la detección real de juego, carátulas de Steam y tiempo de sesión.


## REBUILD 052 — Temas iniciales + iconos de Centro de Salud
- Base: REBUILD 051.
- Centro de Salud: cada icono del hub ahora usa un color distinto para diferenciar módulos.
- Se añadió el módulo Temas como primera versión funcional.
- Los temas aplican paleta base del shell principal (fondo, sidebar y acentos de navegación).
- Nuevo archivo: ui/ThemesPage.qml.
- Validación: pytest -q -> 161 PASS.


## REBUILD 053 — Tweaks de apertura rápida
- Base: REBUILD 052; catálogo conservado de 78 tweaks y 12 categorías.
- Verificación de estados en trabajador de segundo plano; el getter `options` deja de ejecutar Registro y PowerShell en el hilo QML.
- Todas las operaciones permanecen deshabilitadas hasta que el estado real quede verificado. Respaldo y rollback conservados.
- Renderizado virtualizado con `ListView` y tarjetas generadas al desplazarse.
- Resultados reutilizables durante 60 segundos; comprobación manual disponible con «Actualizar».
- Sin archivos Python de producción nuevos ni cambios en otros motores.
- Validación: 165 pruebas PASS. Pendiente de probar rendimiento y renderizado en Windows.
