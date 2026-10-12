@echo off
setlocal
cd /d "%~dp0..\..\CorePulse_AI_Server"
set "COREPULSE_MODEL_PROVIDER=openai_compatible"
set "COREPULSE_MODEL_BASE_URL="
set "COREPULSE_MODEL_NAME="
set "COREPULSE_MODEL_API_KEY="
echo [CorePulse V472] Prueba sintetica del proveedor alternativo.
echo Requiere el servidor remoto disponible. No se envia telemetria real.
choice /m "Enviar UNA pregunta sintetica a un modelo remoto HTTPS"
if errorlevel 2 exit /b 0
python -m app.compatible_probe
pause
