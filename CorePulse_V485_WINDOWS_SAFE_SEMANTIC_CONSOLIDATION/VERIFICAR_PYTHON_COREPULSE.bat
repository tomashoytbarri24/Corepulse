@echo off
setlocal
cd /d "%~dp0"
set "PY=python"
if exist ".corepulse_runtime_python.txt" (
  set /p PY=<.corepulse_runtime_python.txt
) else (
  py -3.12 -c "import sys" >nul 2>&1 && set "PY=py -3.12"
)
%PY% -c "import sys; print(sys.executable)"
endlocal
