@echo off
setlocal
cd /d "%~dp0..\..\CorePulse_AI_Server"
set "COREPULSE_MODEL_PROVIDER=groq"
echo [CorePulse V466] Esta prueba hara UNA solicitud a Groq con datos 100%% sinteticos.
echo Sin telemetria real de este equipo.
choice /m "Enviar una consulta sintetica a GPT-OSS 120B"
if errorlevel 2 exit /b 0
python -m app.groq_probe
pause
