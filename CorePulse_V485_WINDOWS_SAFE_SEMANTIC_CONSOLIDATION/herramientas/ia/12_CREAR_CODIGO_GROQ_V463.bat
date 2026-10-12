@echo off
setlocal
cd /d "%~dp0..\..\CorePulse_AI_Server"
set "COREPULSE_MODEL_PROVIDER=groq"
echo [CorePulse V471] Codigo de vinculacion temporal para ESTE equipo.
python -m app.admin issue --minutes 30
pause
