@echo off
setlocal
cd /d "%~dp0..\..\CorePulse_AI_Server"
set "COREPULSE_MODEL_PROVIDER=groq"
set "COREPULSE_AI_HOST=127.0.0.1"
set "COREPULSE_AI_PORT=8765"
set "COREPULSE_AI_DAILY_LIMIT=100"
echo [CorePulse V463] Puente ligero local - modelo GPT-OSS 120B en Groq Cloud
python -m app.groq_setup status
python -m pip install -r requirements.txt
if errorlevel 1 goto error
python -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --no-access-log
:error
pause
