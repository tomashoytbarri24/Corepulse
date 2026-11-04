# Evidencias del proyecto — Fase 2

Entrega preparada por Maximiliano Carrasco el 3 de noviembre de 2026.

Se conserva la organización por fases del repositorio. La aplicación actual
reemplaza a la entrega 146 en esta carpeta; su evolución permanece en el historial.

- [CorePulse REBUILD 177](CorePulse_REBUILD_177/README.md): versión actual del escritorio.
- [Historial consolidado](CorePulse_REBUILD_177/versiones/HISTORIAL.md): cambios y revisión 176/177.
- [Validación 177](CorePulse_REBUILD_177/versiones/VALIDACION_177.json): resultados y SHA-256 del instalador.
- [CorePulse web](../../README.md#web): material web conservado del repositorio.

## Alcance de la revisión

Se comparó la entrega 177 con la 176: 336 archivos idénticos y 26 modificados,
sin altas ni bajas en el conjunto comparado. Se mantienen los binarios y fuentes
nativos, el editor, las sesiones, el frametime, los registros y los reportes.
Los cambios de seguridad y permisos de la 177 están documentados en el historial.

Pasaron 105 pruebas enfocadas de Python y 61 de Node. La suite histórica mantiene
las mismas 63 fallas en ambas versiones (286 aprobadas por versión). Las páginas
Overlay y Sesiones abrieron sin avisos QML. En la prueba sin administrador la
temperatura de CPU quedó N/A. No se afirma compatibilidad universal ni se repitió
la instalación del EXE durante esta revisión documental.

## Distribución

El instalador `CorePulse_Setup_177_x64.exe` se entrega por separado: supera el
límite de archivo de Git. El código sí incluye los módulos nativos y sus licencias.
Para distribuirlo desde GitHub, adjuntar el instalador, el ZIP y `SHA256.txt` a
una Release de prueba. No agregar el EXE al commit.

La autoevaluación individual está en `../Evidencias Individuales/`.
