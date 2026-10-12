@echo off
setlocal
cd /d "%~dp0..\..\CorePulse_AI_Server"
set "COREPULSE_MODEL_PROVIDER=openai_compatible"
set "COREPULSE_AI_PORT=8766"
echo [CorePulse V472] Codigo temporal para el puente alternativo, no compartas capturas.
python -m app.admin issue --minutes 30
pause
