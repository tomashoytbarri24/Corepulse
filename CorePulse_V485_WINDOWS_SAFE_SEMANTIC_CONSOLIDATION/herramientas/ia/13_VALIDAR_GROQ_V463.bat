@echo off
setlocal
cd /d "%~dp0..\.."
python -m pytest -q tests/test_v463_groq_cloud.py tests/test_v464_groq_diagnostics.py
pause
