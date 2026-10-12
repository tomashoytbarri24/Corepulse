@echo off
setlocal
cd /d "%~dp0..\.."
chcp 65001 >nul
set PY=python
if exist ".corepulse_runtime_python.txt" set /p PY=<.corepulse_runtime_python.txt

echo ============================================================
echo CorePulse V390 - Diagnostico de sensor termico CPU
echo ============================================================
"%PY%" herramientas\diagnostico\cpu_sensor_probe.py > evidence\cpu_sensor_probe.txt 2>&1
type evidence\cpu_sensor_probe.txt
echo.
echo Evidencia guardada en:
echo evidence\cpu_sensor_probe.txt
echo evidence\cpu_sensor_probe.json
pause
