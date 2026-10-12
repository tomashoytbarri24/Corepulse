# CorePulse V477 — Auditoría estructural

## Resultado

- Archivos en V476: **418**.
- Archivos en V477 después de depurar y añadir las pruebas nuevas: **341**.
- Archivos sueltos en raíz: **116 → 21**.
- Auxiliares BAT trasladados y adaptados: **19**.
- Documentos históricos consolidados conservando su contenido: **72**.
- Artefactos de ejecución/compilación y punteros específicos de otro equipo descartados: **10**.

## Decisiones de seguridad

No se ha suprimido código por basarse únicamente en el nombre o antigüedad de un archivo. `core/`, `gui/`, rendimiento, benchmarks, modelos, evaluador y suite de pruebas permanecen; sus múltiples módulos representan responsabilidades distintas. Reducir esos archivos mediante fusiones de código sin auditoría de dependencias aumentaría el riesgo de regresiones.

Los `.bat` en `herramientas/ia/` conservan el directorio de trabajo original; el panel AI fue actualizado para encontrar los scripts. Las referencias usadas por pruebas anteriores fueron ajustadas para reflejar la nueva ubicación.

Se eliminaron punteros generados que contenían rutas absolutas a instalaciones Python de otro PC: al iniciar, CorePulse detectará o preparará el runtime en el sistema actual según su lógica existente.

## Límites

Esta revisión estructural no constituye una validación de todas las ventanas de Windows ni de todos los sensores físicos. La comprobación de interfaz y el flujo de compilación PyInstaller/Inno Setup se deben volver a ejecutar en un equipo Windows. Se mantienen las políticas `REAL_OR_NA`, consentimiento cloud, y la elección de Groq/modelo alternativo.
