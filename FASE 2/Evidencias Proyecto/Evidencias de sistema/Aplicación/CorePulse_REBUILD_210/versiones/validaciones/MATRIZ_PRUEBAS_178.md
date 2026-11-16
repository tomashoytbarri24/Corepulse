# Matriz de pruebas — CorePulse REBUILD 178

Fecha: 5 de noviembre de 2026. Base: REBUILD 177. Área: salud, mantenimiento y validación.

«Comprobado» indica una ejecución registrada en esta revisión. Los escenarios
de interfaz y los PDF usan datos sintéticos, identificados como tales. Las
lecturas reales se limitan a este equipo; no se publican IP, seriales ni datos de cuenta.

| ID | Área y procedimiento | Resultado esperado | Estado / evidencia |
|---|---|---|---|
| UI-01 | Abrir Centro de Salud; probar anchos amplios y compactos. | Accesos legibles, columnas adaptables y lecturas disponibles al desplegar. | Comprobado en Qt; 21 escenarios totales sin avisos. |
| UI-02 | Batería: desplegar información; repetir sin capacidades y sin batería. | N/A cuando falta capacidad; una torre sin batería no muestra su acceso. | Comprobado con escenarios sintéticos. |
| UI-03 | Almacenamiento: abrir detalles SMART; simular USB sin SMART y cambio de inventario. | Cero de ocupación válido; salud desconocida sin inventar lecturas; selección actualizada. | Comprobado con escenarios sintéticos. |
| UI-04 | Limpieza: pulsar Profunda y cancelar. | Aparece confirmación; no se inicia ninguna limpieza antes de confirmar. | Comprobado con controlador de prueba; no se ejecutó mantenimiento real. |
| UI-05 | Red: cambiar proveedor, iniciar Ookla, intentar pulsar el fondo, aceptar, reabrir y pulsar Escape. | Fondo bloqueado; no inicia sin aceptación; aceptación se reinicia; Escape cancela. | Comprobado con controlador de prueba; ninguna transferencia de velocidad. |
| UI-06 | Probar valores 0, ausente, NaN y negativo en resultados de velocidad. | 0 se presenta como lectura; el resto aparece N/A. | Comprobado en expresiones QML reales. |
| UI-07 | Informes: sin diagnóstico, completarlo y usar Crear/Abrir diagnóstico. | Creación deshabilitada sin ejecución; usa generateDiagnostic/openDiagnostic y su ruta. | Comprobado con clics y controlador de prueba. |
| UI-08 | Abrir almacenamiento, limpieza, red e informes a 760×680 con tema Marea. | Contenido accesible con scroll y colores de estado conservados. | Comprobado y revisado visualmente. |
| QML-01 | Parsear seis QML modificados e iniciar la aplicación completa. | Sin errores de carga ni referencias indefinidas. | Comprobado: seis parseados, Main abre sin avisos, sensores preparados. |
| HW-01 | Consultar batería, discos y adaptadores sin mantenimiento. | Inventario real disponible y datos sensibles de red ocultos. | Comprobado en este PC: batería, dos discos, seis adaptadores; consultas terminadas en 12 s. |
| PDF-01 | Generar informe de equipo con lecturas controladas. | Titular íntegro, tablas alineadas y encabezados junto al contenido. | Comprobado: dos páginas renderizadas y revisadas. |
| PDF-02 | Generar diagnóstico completo y diagnóstico parcial con CPU de nombre largo. | PDF independiente, saltos correctos, texto envuelto, sin puntuaciones de benchmark. | Comprobado: una página por caso; ambas revisadas. |
| PDF-03 | Incluir lectura ausente, cero verificado y estado desconocido. | N/A/Sin datos, 0/Correcto y Sin datos respectivamente. | Cuatro pruebas de contenido aprobadas. |
| REG-01 | Ejecutar pruebas enfocadas en procesos separados por archivo. | Sin fallos en PDF, runtime, sensores, activación, sesiones, registros e IA. | 109 aprobadas; detalle en VALIDACION_178.json. |
| REG-02 | Ejecutar test_rebuild.py en 177 y 178 bajo el mismo entorno. | No añadir fallos a la base. | Ambas: 290 aprobadas / 59 fallidas, mismos identificadores. Suite completa no aprobada. |
| INT-01 | Conectar y retirar un pendrive físico durante la vista de discos. | Aparece/desaparece automáticamente; la selección vuelve a una unidad existente. | Pendiente físico. La lógica no cambió; la actualización se simuló en UI-03. |
| INT-02 | Ejecutar una prueba Cloudflare y una Ookla en una conexión de prueba. | Progreso, resultados reales y apertura del enlace oficial cuando existe. | Pendiente de transferencia real. Solo se verificó la interfaz y el consentimiento. |
| INT-03 | Ejecutar limpiezas, Papelera, duplicados o reparación en un entorno descartable. | Acciones solo tras confirmación y resultados reales. | Pendiente. No se borraron archivos ni se ejecutaron DISM/SFC durante la revisión. |
| INT-04 | Abrir en otro PC, con otra escala de Windows y permisos distintos. | Lecturas disponibles o N/A; sin solapamientos. | Pendiente. No se declara compatibilidad universal. |
| DIST-01 | Compilar, instalar y desinstalar el EXE 178 en Windows limpio. | Versión correcta, dependencias incluidas y datos del perfil conservados. | Pendiente: entrega fuente, sin instalador nuevo. |
| GAME-01 | Verificar OSD y panel en un juego. | Comportamiento heredado de la 177. | No ejecutado en esta revisión; fuentes y 245 archivos native/bin conservados por SHA-256. |

## Comprobación rápida al volver

1. Cierra CorePulse desde la bandeja y abre `Iniciar_CorePulse.bat` de la 178.
2. En Centro de Salud abre Batería y Almacenamiento; prueba sus secciones de detalles.
3. En Limpieza abre Profunda y cancela; comprueba que no comienza la operación.
4. En Red revisa el ojo y los adaptadores; iniciar una prueba real consume datos.
5. Ejecuta un diagnóstico y crea su PDF desde Informes. Comprueba que abre su propio
   documento y que Carpeta de reportes muestra los archivos guardados.

La suite histórica conserva deuda anterior. Sus 59 identificadores están en el
JSON de validación; no se ocultan ni se contabilizan como aprobados. Un intento
conjunto de las pruebas enfocadas terminó sin resumen; los resultados registrados
son las ejecuciones completas por archivo, aislando el ciclo de vida de Qt.
