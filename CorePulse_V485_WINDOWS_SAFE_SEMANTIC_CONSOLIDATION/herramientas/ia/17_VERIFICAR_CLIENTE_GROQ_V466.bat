@echo off
setlocal
cd /d "%~dp0..\..\CorePulse_AI_Server"
set "COREPULSE_MODEL_PROVIDER=groq"
python -m app.groq_client_check
pause
