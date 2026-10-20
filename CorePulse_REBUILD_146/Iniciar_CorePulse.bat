@echo off
setlocal EnableExtensions
cd /d "%~dp0"
rem Selecciona un interprete 64 bits funcional; no basta con que py lo registre.
rem Preferir Python 3.12 estable. Python 3.15 sigue sin validacion de
rem compatibilidad con PySide6 / concurrent.futures en Windows (V119).
call :probar_py -3.12
if not errorlevel 1 goto iniciar
call :probar_py -3.14
if not errorlevel 1 goto iniciar
call :probar_py -3.13
if not errorlevel 1 goto iniciar
call :probar_python python
if not errorlevel 1 goto iniciar
call :probar_python python3
if not errorlevel 1 goto iniciar
echo.
echo [CorePulse] Se requiere Python 3.12, 3.13 o 3.14 de 64 bits.
echo [CorePulse] Python 3.15 no se selecciona temporalmente: no esta validado.
echo [CorePulse] Instala Python 3.12 x64 y ejecuta este archivo otra vez.
pause
exit /b 2

:probar_py
py %1 -I -c "import sys,struct,encodings;sys.exit(0 if (3,12) <= sys.version_info[:2] < (3,15) and struct.calcsize('P')==8 else 1)" >nul 2>nul
if errorlevel 1 exit /b 1
set "COREPULSE_PY=py"
set "COREPULSE_VER=%1"
exit /b 0

:probar_python
%1 -I -c "import sys,struct,encodings;sys.exit(0 if (3,12) <= sys.version_info[:2] < (3,15) and struct.calcsize('P')==8 else 1)" >nul 2>nul
if errorlevel 1 exit /b 1
set "COREPULSE_PY=%1"
set "COREPULSE_VER="
exit /b 0

:iniciar
echo [CorePulse] Iniciando con %COREPULSE_PY% %COREPULSE_VER% ...
%COREPULSE_PY% %COREPULSE_VER% -B "%~dp0main.py"
set "COREPULSE_EXIT=%ERRORLEVEL%"
if not "%COREPULSE_EXIT%"=="0" (
    echo.
    echo [CorePulse] Inicio fallido ^(codigo %COREPULSE_EXIT%^).
    echo [CorePulse] Verifica dependencias, acceso a Internet y mensajes anteriores.
    pause
)
exit /b %COREPULSE_EXIT%
