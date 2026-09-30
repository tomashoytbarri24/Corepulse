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
for /f "usebackq delims=" %%L in (`powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Localizar_Llama_Host.ps1" -Quiet 2^>nul`) do if not defined LLAMAEXE set "LLAMAEXE=%%L"
if defined LLAMAEXE goto :ready

where winget >nul 2>nul
if errorlevel 1 (
  echo [ERROR] WinGet no esta disponible en este Windows.
  echo Instala llama.cpp manualmente y vuelve a ejecutar este archivo.
  pause
  exit /b 1
)

echo llama.cpp no esta instalado. Se instalara con WinGet.
echo.
winget install --id ggml.llamacpp -e --source winget --accept-package-agreements --accept-source-agreements
if errorlevel 1 (
  winget install llama.cpp --accept-package-agreements --accept-source-agreements
  if errorlevel 1 (
    echo.
    echo [ERROR] No se pudo instalar llama.cpp.
    pause
    exit /b 1
  )
)

rem Localizarlo en esta misma consola; no hace falta cerrarla para refrescar PATH.
for /f "usebackq delims=" %%L in (`powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Localizar_Llama_Host.ps1" -Quiet 2^>nul`) do if not defined LLAMAEXE set "LLAMAEXE=%%L"
if not defined LLAMAEXE (
  echo.
  echo [ERROR] llama.cpp fue instalado, pero no se encontro llama.exe ni llama-server.exe.
  pause
  exit /b 1
)

:ready
echo.
echo [OK] llama.cpp disponible: %LLAMAEXE%
echo La primera ejecucion del modelo puede descargar varios GB en el host de IA.
echo Eso NO aumenta el peso de CorePulse Desktop.
pause
