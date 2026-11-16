# Matriz de pruebas - REBUILD 181

Fecha: 5 de noviembre de 2026. Base: 180.

| Área | Comprobación | Resultado |
|---|---|---|
| GPU | Sonda CorePulse y NVIDIA-SMI reales; consulta sin cambiar ajustes. | Ambos entregan actividad. Muestras separadas, sin comparación de precisión. |
| Valores GPU | Cero válido, N/A y datos inválidos del parser. | Prueba aprobada. |
| Registro automático | Guardado antes/después, pico original, agrupación, preferencia y cambio de PID. | 20 pruebas aprobadas. |
| Activación overlay | Manejadores, permisos y ciclo de vida. | 30 pruebas aprobadas. |
| Sesiones | Historial, métricas y PDF existente. | 7 pruebas aprobadas. |
| QML | Registros sin botones manuales; cambio de discos y demás vistas heredadas. | 28 casos sin avisos. |
| App completa | Página Overlay, tres atajos, carga QML. | Versión 181 abierta sin avisos. |
| Panel GDI | Dos resoluciones y dos combinaciones de marca; botones, perfiles, cerrar y hueco transparente. | Cuatro vistas revisadas y clics comprobados. |
| Panel Direct3D 11 | Las mismas combinaciones, dos botones y ratón. | Cuatro vistas; 16 acciones comprobadas con aserciones activas. |
| Nativos | Host, auxiliares y cinco API x86/x64. | Compilación completada. |

El render de prueba usa métricas simuladas y no ejecuta RAM ni cambios de plan.
No se han usado juegos comerciales ni otro PC para esta revisión. Los nativos
de un juego ya abierto permanecen cargados hasta cerrarlo; cerrar juegos y
CorePulse antes de abrir main.py de la 181.

Los registros se revisan en Monitoreo → Sesiones de juego → Registros. Los nuevos
se guardan automáticamente con el monitor activo y fotogramas reales; no hay
que pulsar ningún botón de registro. Esperar unos 15 s después del pico para
completar el contexto posterior. La carpeta y el PDF siguen disponibles.
