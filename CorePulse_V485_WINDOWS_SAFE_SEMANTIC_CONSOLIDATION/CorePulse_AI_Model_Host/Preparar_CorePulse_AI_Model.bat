@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"
title Preparar CorePulse AI Model Host

echo ============================================================
echo  CorePulse AI Model Host - Preparacion
echo.
echo  Este componente NO usa Ollama.
echo ============================================================
echo.

set "LLAMAEXE="
for /f "usebackq delims=" %%L in (`call "%~dp0Localizar_Llama_Host.bat" 2^>nul`) do if not defined LLAMAEXE set "LLAMAEXE=%%L"
if defined LLAMAEXE goto :ready

set "WINGETEXE="
for /f "usebackq delims=" %%W in (`where winget.exe 2^>nul`) do if not defined WINGETEXE set "WINGETEXE=%%W"
if not defined WINGETEXE if exist "%LOCALAPPDATA%\Microsoft\WindowsApps\winget.exe" set "WINGETEXE=%LOCALAPPDATA%\Microsoft\WindowsApps\winget.exe"
if not defined WINGETEXE (
  echo [ERROR] WinGet no esta disponible en este Windows.
  echo El inicio normal de CorePulse V399 intentara ademas un runtime portable oficial.
  if /i not "%COREPULSE_AI_AUTOSTART%"=="1" pause
  exit /b 1
)

echo llama.cpp no esta instalado. Se instalara con WinGet.
echo.
"%WINGETEXE%" install --id ggml.llamacpp -e --source winget --accept-package-agreements --accept-source-agreements --disable-interactivity --silent
if errorlevel 1 (
  "%WINGETEXE%" install llama.cpp --accept-package-agreements --accept-source-agreements --disable-interactivity --silent
  if errorlevel 1 (
    echo.
    echo [ERROR] No se pudo instalar llama.cpp.
    if /i not "%COREPULSE_AI_AUTOSTART%"=="1" pause
    exit /b 1
  )
)

rem Localizarlo en esta misma consola; no hace falta cerrarla para refrescar PATH.
for /f "usebackq delims=" %%L in (`call "%~dp0Localizar_Llama_Host.bat" 2^>nul`) do if not defined LLAMAEXE set "LLAMAEXE=%%L"
if not defined LLAMAEXE (
  echo.
  echo [ERROR] llama.cpp fue instalado, pero no se encontro llama.exe ni llama-server.exe.
  if /i not "%COREPULSE_AI_AUTOSTART%"=="1" pause
  exit /b 1
)

:ready
echo.
echo [OK] llama.cpp disponible: %LLAMAEXE%
echo La primera ejecucion del modelo puede descargar varios GB en el host de IA.
echo Eso NO aumenta el peso de CorePulse Desktop.
if /i not "%COREPULSE_AI_AUTOSTART%"=="1" pause
