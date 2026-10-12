@echo off
setlocal
cd /d "%~dp0..\..\CorePulse_AI_Server"
set "COREPULSE_MODEL_PROVIDER=groq"
echo [CorePulse V466] Esta verificacion consulta GET /models de Groq.
echo No envia sensores ni preguntas. Solo la API key para autenticacion.
choice /m "Comprobar conexion y disponibilidad de GPT-OSS 120B"
if errorlevel 2 exit /b 0
python -m app.groq_diagnostics
pause
