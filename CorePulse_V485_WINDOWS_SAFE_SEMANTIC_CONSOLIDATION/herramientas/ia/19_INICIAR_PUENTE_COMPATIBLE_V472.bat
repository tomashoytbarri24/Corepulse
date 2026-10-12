@echo off
setlocal
cd /d "%~dp0..\..\CorePulse_AI_Server"
set "COREPULSE_MODEL_PROVIDER=openai_compatible"
set "COREPULSE_AI_HOST=127.0.0.1"
set "COREPULSE_AI_PORT=8766"
set "COREPULSE_AI_DAILY_LIMIT=100"
rem No arrastrar destinos o modelos de otros procesos del usuario.
set "COREPULSE_MODEL_BASE_URL="
set "COREPULSE_MODEL_NAME="
set "COREPULSE_MODEL_API_KEY="
echo [CorePulse V472] Puente alternativo. Requiere modelo HTTPS ya desplegado.
python -m app.compatible_setup status
if errorlevel 1 goto error
python -m pip install -r requirements.txt
if errorlevel 1 goto error
python -m uvicorn app.main:app --host 127.0.0.1 --port 8766 --no-access-log
:error
pause
