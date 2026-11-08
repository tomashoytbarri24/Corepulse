# Compilar e instalar CorePulse 182

Esta versión conserva sin cambios los nativos de la REBUILD 181. El instalador 182 todavía
no se ha construido; esta guía describe cómo generarlo.

Una vez compilado, ejecuta `CorePulse_Setup_182_x64.exe`. Windows 10 2004 o posterior y Windows 11,
arquitectura x64. Instala en `%LOCALAPPDATA%\Programs\CorePulse`; no requiere
Python, pip, Qt ni RTSS instalados por el usuario. Incluye desinstalador y
acceso desde Inicio. El acceso al escritorio es opcional.

CorePulse.exe y CorePulseWorker.exe llevan asInvoker: abren sin UAC. Los
permisos completos se piden solo si el usuario reinicia con ellos o activa
«Abrir siempre con permisos» en Overlay; denegar UAC no impide abrir la app.

Los informes, cuentas, historial y ajustes se conservan bajo
`%LOCALAPPDATA%\CorePulse`. Desinstalar la aplicación no los borra.
PawnIO se instala solo si el usuario lo pide desde el Resumen. Ookla
mantiene su descarga oficial verificada; requiere Internet para prepararse
por primera vez y aceptación de sus términos al ejecutar una prueba.

## Reproducir la compilación

Python 3.12 x64, dependencias de `requirements.txt`, PyInstaller 6.22.3,
Zig 0.14.1 e Inno Setup 7.1.1 x64 (soporte de rutas largas). Desde PowerShell:

```powershell
python -m pip install -r requirements.txt pyinstaller==6.22.3
.\installer\build_installer.ps1 -Python python -Iscc 'C:\Program Files\Inno Setup 7\ISCC.exe' -Zig zig
```

`dist/CorePulse` contiene el ejecutable con las bibliotecas; `release` contiene
el instalador. No quitar `_internal` ni separar los EXE de esa carpeta.

El EXE gráfico y el Worker comparten exactamente el mismo código. Los procesos
de sensores y benchmark pasan por entradas explícitas; el Worker tiene salida
de consola para JSON, pero se lanza oculto. Los errores del EXE se guardan en
`%LOCALAPPDATA%\CorePulse\logs\app.log`.

Para comprobar el paquete sin aplicar ajustes:

```powershell
.\dist\CorePulse\CorePulseWorker.exe --installation-check "$env:TEMP\corepulse-check.json"
.\dist\CorePulse\CorePulse.exe --smoke-test "$env:TEMP\corepulse-ui.json"
```

La comprobación de UI se cierra sola y omite PawnIO y la activación del overlay.
Esta primera compilación no tiene firma digital propia de CorePulse. Antes de
publicarla masivamente: firma de código y prueba en un Windows limpio y en juegos
reales a 1080p/2,5K. La compilación de las cinco API no equivale a esa prueba.

El Worker cpu-stream mantiene el proveedor abierto, emite JSON UTF-8 y finaliza
al cerrar stdin o desaparecer el padre. Se reinicia si deja de responder ocho
segundos. La app inicia la lectura antes de mostrar su ventana principal.

La interfaz propia vive en CorePulseWizard.iss. WizardBackdrop.svg y
render_assets.ps1 generan los PNG a doble resolución. La compilación normal
no incluye el temporizador de integración TestBuild; /DTestBuild usa un AppId
y acceso directo independientes para no reemplazar la app del usuario.

Para exportar las vistas del formulario sin instalar:

```powershell
.\release\CorePulse_Setup_182_x64.exe /PREVIEWDIR="C:\carpeta-de-prueba"
```

Guarda tres BMP y termina con salida 2 (cancelación esperada). El 65 % de la
vista de diseño es una muestra; el instalador normal usa progreso real.

La 174 usa MulDiv para evitar que la división entera del script mantenga
el porcentaje y la barra en cero. /DTestBuild permite verificar una instalación
real con /AUTOTEST=1 y /PROGRESSDIR="C:\carpeta-de-prueba": registra cada porcentaje
y exporta capturas al 25/50/75 %. El instalador distribuido no incluye esas
funciones de integración, y mantiene el AppId normal para actualizar CorePulse.

La 176 mantiene el cálculo y sustituye el repintado completo por controles
compuestos y actualizaciones locales. La ruta validada se muestra junto al
avance. CorePulseCaptureGuard.exe gestiona únicamente CorePulseOverlay_PID:
retira sesiones con dueño muerto y permite al padre cerrar solo la suya.
El helper forma parte del paquete, no se instala como servicio ni modifica
sesiones de Windows o de terceros. Los 17 recursos/dependencias se comprueban
con --installation-check. El usuario final no necesita Python instalado.
