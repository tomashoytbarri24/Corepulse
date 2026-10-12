@echo off
setlocal
cd /d "%~dp0..\..\CorePulse_AI_Server"
set "COREPULSE_MODEL_PROVIDER=groq"
echo [CorePulse V465] Prueba local - NO enviara ninguna solicitud por Internet.
python -m app.groq_key_status
pause
