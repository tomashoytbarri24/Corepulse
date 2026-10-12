@echo off
setlocal
cd /d "%~dp0"
py -3.12 --version >nul 2>nul
if not errorlevel 1 (
    py -3.12 -B "%~dp0main.py"
) else (
    python -B "%~dp0main.py"
)
if errorlevel 1 (
    echo.
    echo [CorePulse] No se pudo iniciar. Comprueba Python 3.12 x64,
    echo Internet para la primera instalacion y el mensaje mostrado arriba.
    pause
)
endlocal
