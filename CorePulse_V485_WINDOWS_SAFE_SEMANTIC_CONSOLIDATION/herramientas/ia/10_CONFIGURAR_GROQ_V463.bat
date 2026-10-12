@echo off
setlocal
cd /d "%~dp0..\..\CorePulse_AI_Server"
echo [CorePulse V463] Guarda tu clave gratuita de Groq de forma segura.
python -m app.groq_setup configure
pause
