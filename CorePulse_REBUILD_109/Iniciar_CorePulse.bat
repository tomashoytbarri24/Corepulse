@echo off
setlocal EnableExtensions
cd /d "%~dp0"
rem Selecciona un interprete 64 bits funcional; no basta con que py lo registre.
rem Se prueba primero la version mas reciente y luego versiones alternativas.
call :probar_py -3
if not errorlevel 1 goto iniciar
call :probar_py -3.14
if not errorlevel 1 goto iniciar
call :probar_py -3.13
if not errorlevel 1 goto iniciar
call :probar_py -3.12
if not errorlevel 1 goto iniciar
call :probar_python python
if not errorlevel 1 goto iniciar
call :probar_python python3
if not errorlevel 1 goto iniciar
echo.
echo [CorePulse] No se encontro Python 3.12 o superior de 64 bits en buen estado.
echo [CorePulse] Repara la instalacion de Python o instala una compatible.
pause
exit /b 2

:probar_py
py %1 -I -c "import sys,struct,encodings;sys.exit(0 if sys.version_info >= (3,12) and struct.calcsize('P')==8 else 1)" >nul 2>nul
if errorlevel 1 exit /b 1
set "COREPULSE_PY=py"
set "COREPULSE_VER=%1"
exit /b 0

:probar_python
%1 -I -c "import sys,struct,encodings;sys.exit(0 if sys.version_info >= (3,12) and struct.calcsize('P')==8 else 1)" >nul 2>nul
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
