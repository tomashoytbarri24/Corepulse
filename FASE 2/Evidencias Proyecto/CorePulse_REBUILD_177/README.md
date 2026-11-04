# CorePulse REBUILD 177

Aplicación de diagnóstico y monitoreo para Windows 10 y 11 de 64 bits.
Incluye telemetría de CPU, GPU, RAM y almacenamiento, diagnóstico, benchmark,
informes PDF, herramientas de mantenimiento, temas y CorePulse AI.

## Instalar y abrir

Ejecuta **CorePulse_Setup_177_x64.exe**, entregado por separado del código
fuente y disponible en `release` de la copia local completa. El instalador
incluye Python, Qt y los componentes propios: no necesitas instalar Python
ni RTSS para usarlo. El EXE no se incluye en Git por su tamaño.
Antes de actualizar, cierra CorePulse desde la bandeja y los juegos abiertos.

Para ejecutar el código fuente, abre `Iniciar_CorePulse.bat`; esta modalidad
requiere Python 3.12 o posterior de 64 bits y prepara su entorno automáticamente.
La preparación inicial de dependencias y las funciones en línea requieren conexión.

## Comportamiento de la 177

- Abre sin administrador. En Overlay puedes reiniciar con permisos completos
  o elegir abrir siempre con ellos. Algunas lecturas y acciones los requieren.
  Sin la lectura correspondiente, se muestra N/A.
- El módulo interno del overlay está apagado por defecto. Su autorización es
  por ejecutable y se pueden retirar los permisos. Los juegos detectados con
  antitrampas mantienen el módulo interno bloqueado; se conserva el host externo.
  Un servicio antitrampas activo también puede bloquearlo para otro juego.
- PawnIO se comprueba al iniciar y se instala solo al solicitarlo en Resumen.
- Una base SQLite dañada se conserva con un nombre `.danada-<fecha>` y se crea
  otra. Un bloqueo temporal no se interpreta como corrupción.

## Overlay y registros heredados

En **Monitoreo → Overlay**, el editor permite mover el OSD, ordenar y ocultar
métricas, ajustar tamaño, opacidad y separación, y guardar diseños por juego.
La línea de frametime utiliza intervalos reales entre presentaciones capturados
por ETW; si no hay fotogramas disponibles, indica N/A.

**Shift+F2** abre el panel rápido con mouse. **Ctrl+Shift+F8**, configurable,
registra hasta 30 segundos anteriores y unos 15 posteriores a un problema.
También existe el botón REGISTRAR del panel. **Sesiones de juego → Registros**
incluye línea, marcador, estadísticas, lecturas próximas y PDF independiente.
La proximidad de una lectura a un pico no demuestra su causa.

Los informes quedan en `%LOCALAPPDATA%\CorePulse\reportes` y los registros
en `%LOCALAPPDATA%\CorePulse\registros`. Se conservan al desinstalar.

## Historial y revisión

Los cambios de cada versión y sus detalles técnicos se concentran en
[versiones/HISTORIAL.md](versiones/HISTORIAL.md). Los resultados verificables
de esta revisión están en [versiones/VALIDACION_177.json](versiones/VALIDACION_177.json).

En la revisión del 3 de noviembre de 2026 pasaron 105 pruebas enfocadas de Python
y 61 del servicio Node.js. La suite histórica mantiene 63 fallas ya presentes
en la 176: las mismas pruebas fallan en ambas bases. No se declara aprobada esa
suite completa ni compatibilidad universal con todos los juegos y equipos.
Overlay y Sesiones abrieron sin avisos QML. En esta prueba sin administrador,
la temperatura de CPU no estuvo disponible. No se reinstaló el EXE recibido.

## Compilar el instalador

El procedimiento y las dependencias de compilación están en
[installer/README.md](installer/README.md). El código nativo del overlay está
en `native`; sus binarios x86/x64 están en `bin`. Se conservan sin cambios frente
a la 176 porque el cambio de la 177 está en el controlador Python y el arranque.
El SHA-256 del instalador se registra en `release/SHA256.txt`.

Las reglas para crear versiones están en `Reglas para crear Versiones nuevas.txt`.
La revisión documental conserva la lógica del programa y el instalador de la 177.
