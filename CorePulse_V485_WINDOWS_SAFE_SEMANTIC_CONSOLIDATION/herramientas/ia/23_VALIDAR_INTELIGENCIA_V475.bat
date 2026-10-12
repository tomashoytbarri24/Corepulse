@echo off
setlocal
cd /d "%~dp0..\.."
set "PYTHONPATH=%CD%"
where py >nul 2>nul
if not errorlevel 1 (
  py -3.12 -m CorePulse_AI_Server.evaluation.verify_engine_v475
  if not errorlevel 1 goto DONE
)
python -m CorePulse_AI_Server.evaluation.verify_engine_v475
:DONE
set "STATUS=%ERRORLEVEL%"
echo.
if not "%STATUS%"=="0" echo VALIDACION V475 FALLIDA: %STATUS%
pause
exit /b %STATUS%
