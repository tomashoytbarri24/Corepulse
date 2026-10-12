@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"
title CorePulse AI - Model Host

set "MODEL_NAME=Qwen/Qwen3-4B-GGUF:Q4_K_M"
set "LLAMAEXE="
for /f "usebackq delims=" %%L in (`call "%~dp0Localizar_Llama_Host.bat" 2^>nul`) do if not defined LLAMAEXE set "LLAMAEXE=%%L"

if not defined LLAMAEXE (
  echo [ERROR] No se encontro llama.cpp.
  echo Ejecuta primero Preparar_CorePulse_AI_Model.bat
  if /i not "%COREPULSE_AI_AUTOSTART%"=="1" pause
  exit /b 1
)

for %%F in ("%LLAMAEXE%") do set "LLAMA_NAME=%%~nxF"

echo ============================================================
echo  CorePulse AI Model Host V1
echo.
echo  Modelo: Qwen3-4B GGUF Q4_K_M
echo  API: http://127.0.0.1:8766/v1
echo  Motor: llama.cpp ^(sin Ollama^)
echo  Ejecutable: %LLAMA_NAME%
echo ============================================================
echo.
echo Iniciando modelo. En la primera ejecucion puede descargarse automaticamente...
echo.

if /i "%LLAMA_NAME%"=="llama.exe" (
  "%LLAMAEXE%" serve -hf %MODEL_NAME% --host 127.0.0.1 --port 8766
) else (
  "%LLAMAEXE%" -hf %MODEL_NAME% --host 127.0.0.1 --port 8766
)

if errorlevel 1 (
  set "MODEL_EXIT=!errorlevel!"
  echo.
  echo [ERROR] El host del modelo termino con codigo !MODEL_EXIT!.
  if /i not "%COREPULSE_AI_AUTOSTART%"=="1" pause
  exit /b !MODEL_EXIT!
)

exit /b 0
