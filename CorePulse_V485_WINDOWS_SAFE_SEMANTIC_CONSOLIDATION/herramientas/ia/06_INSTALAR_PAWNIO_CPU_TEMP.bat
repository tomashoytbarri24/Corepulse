@echo off
setlocal
cd /d "%~dp0..\.."
chcp 65001 >nul

echo ============================================================
echo CorePulse V390 - Habilitar sensores CPU con PawnIO
echo ============================================================
echo.
echo PawnIO es un driver de sistema requerido por LibreHardwareMonitor
echo para ciertos sensores de bajo nivel. Esta accion modifica Windows.
echo CorePulse NO lo instala sin tu confirmacion.
echo.
set /p CONFIRM=Escribe S para instalar PawnIO con winget, o cualquier otra tecla para cancelar: 
if /I not "%CONFIRM%"=="S" (
  echo [CANCELADO] No se realizaron cambios.
  pause
  exit /b 0
)

echo.
echo [INFO] Instalando namazso.PawnIO desde winget...
winget install --id namazso.PawnIO -e --source winget --accept-package-agreements --accept-source-agreements
if errorlevel 1 (
  echo.
  echo [WARN] El ID exacto no funciono. Intentando busqueda por nombre...
  winget install PawnIO --accept-package-agreements --accept-source-agreements
)

echo.
echo [INFO] Verificando instalacion...
set PY=python
if exist ".corepulse_runtime_python.txt" set /p PY=<.corepulse_runtime_python.txt
"%PY%" herramientas\diagnostico\cpu_sensor_probe.py --check-pawnio
if errorlevel 1 (
  echo.
  echo [WARN] PawnIO aun no fue detectado. Si el instalador pidio UAC, completalo y vuelve a ejecutar esta verificacion.
) else (
  echo.
  echo [PASS] PawnIO detectado. Cierra por completo CorePulse y vuelve a abrir Iniciar_CorePulse.bat.
)
pause
