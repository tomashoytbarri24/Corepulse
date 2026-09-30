@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"
title CorePulse AI - Inicio completo

set "ROOT=%~dp0"
set "MODEL_DIR=%ROOT%CorePulse_AI_Model_Host"
set "SERVER_DIR=%ROOT%CorePulse_AI_Server"
set "MODEL_URL=http://127.0.0.1:8766/v1/models"
set "AI_STATUS_URL=http://127.0.0.1:8765/v1/status"
set "MODEL_NAME=Qwen/Qwen3-4B-GGUF:Q4_K_M"

cls
echo ============================================================
echo  CorePulse AI - INICIO COMPLETO EN UN SOLO CLIC
echo ============================================================
echo.
echo  Este archivo prepara e inicia automaticamente:
echo   1. llama.cpp / CorePulse AI Model Host
echo   2. CorePulse AI Server
echo   3. CorePulse Desktop
echo.
echo  La primera ejecucion puede tardar porque el host debe descargar
echo  el modelo. El modelo NO queda dentro del programa CorePulse.
echo ============================================================
echo.

rem ------------------------------------------------------------
rem 0) Validar estructura
rem ------------------------------------------------------------
if not exist "%SERVER_DIR%\requirements.txt" (
    echo [ERROR] No se encontro CorePulse_AI_Server\requirements.txt
    echo Extrae el ZIP completo antes de ejecutar este archivo.
    goto :fail
)
if not exist "%ROOT%CorePulse.vbs" (
    echo [ERROR] No se encontro CorePulse.vbs
    goto :fail
)

rem ------------------------------------------------------------
rem 1) Localizar Python para el backend de desarrollo
rem ------------------------------------------------------------
set "PYEXE="
for /f "usebackq delims=" %%P in (`py -3 -c "import sys; print(sys.executable)" 2^>nul`) do if not defined PYEXE set "PYEXE=%%P"
if not defined PYEXE (
    for /f "usebackq delims=" %%P in (`python -c "import sys; print(sys.executable)" 2^>nul`) do if not defined PYEXE set "PYEXE=%%P"
)
if not defined PYEXE (
    echo [ERROR] No se encontro Python para levantar el servidor local de CorePulse AI.
    echo En la version publica este backend vivira en nuestro servidor y el usuario no necesitara Python.
    goto :fail
)
echo [OK] Python: %PYEXE%

rem ------------------------------------------------------------
rem 2) Preparar entorno aislado del CorePulse AI Server
rem ------------------------------------------------------------
set "VENV_PY=%SERVER_DIR%\.venv\Scripts\python.exe"
set "DEPS_MARKER=%SERVER_DIR%\.venv\.corepulse_ai_deps_v12"
if not exist "%VENV_PY%" (
    echo [1/6] Creando entorno aislado del servidor AI...
    "%PYEXE%" -m venv "%SERVER_DIR%\.venv"
    if errorlevel 1 (
        echo [ERROR] No se pudo crear el entorno virtual del servidor.
        goto :fail
    )
)

if not exist "%DEPS_MARKER%" (
    echo [2/6] Instalando dependencias del servidor AI ^(solo primera vez^)...
    "%VENV_PY%" -m pip install --disable-pip-version-check -r "%SERVER_DIR%\requirements.txt"
    if errorlevel 1 (
        echo [ERROR] No se pudieron instalar las dependencias del servidor.
        goto :fail
    )
    >"%DEPS_MARKER%" echo CorePulse AI Server dependencies ready
) else (
    echo [OK] Dependencias del servidor ya preparadas.
)

rem ------------------------------------------------------------
rem 3) Localizar / instalar llama.cpp
rem ------------------------------------------------------------
set "LLAMAEXE="
set "LLAMA_KIND="
for /f "usebackq delims=" %%L in (`powershell -NoProfile -ExecutionPolicy Bypass -File "%MODEL_DIR%\Localizar_Llama_Host.ps1" -Quiet 2^>nul`) do if not defined LLAMAEXE set "LLAMAEXE=%%L"

if not defined LLAMAEXE (
    echo [3/6] llama.cpp no esta instalado. Preparando automaticamente...
    where winget >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] WinGet no esta disponible. No puedo instalar llama.cpp automaticamente.
        goto :fail
    )

    rem Identificador real del paquete en WinGet. El paquete portable expone
    rem llama-server.exe en versiones que no incluyen el frontend llama.exe.
    winget install --id ggml.llamacpp -e --source winget --accept-package-agreements --accept-source-agreements
    if errorlevel 1 (
        rem Fallback oficial por nombre por si el identificador cambia.
        winget install llama.cpp --accept-package-agreements --accept-source-agreements
        if errorlevel 1 (
            echo [ERROR] WinGet no pudo instalar llama.cpp.
            goto :fail
        )
    )

    rem No exigimos reiniciar la terminal: buscamos el enlace y el paquete
    rem portable directamente en disco inmediatamente despues de instalar.
    for /f "usebackq delims=" %%L in (`powershell -NoProfile -ExecutionPolicy Bypass -File "%MODEL_DIR%\Localizar_Llama_Host.ps1" -Quiet 2^>nul`) do if not defined LLAMAEXE set "LLAMAEXE=%%L"
)

if not defined LLAMAEXE (
    echo [ERROR] llama.cpp se instalo, pero no pude localizar llama.exe ni llama-server.exe.
    echo Revisa la instalacion de WinGet y vuelve a ejecutar este BAT.
    goto :fail
)

for %%F in ("%LLAMAEXE%") do set "LLAMA_NAME=%%~nxF"
if /i "%LLAMA_NAME%"=="llama.exe" (
    set "LLAMA_KIND=UNIFIED"
) else (
    set "LLAMA_KIND=SERVER"
)
echo [OK] llama.cpp: %LLAMAEXE%

rem ------------------------------------------------------------
rem 4) Iniciar host de modelo si no esta activo
rem ------------------------------------------------------------
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $null=Invoke-RestMethod -Uri '%MODEL_URL%' -TimeoutSec 2; exit 0 } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
    echo [4/6] Iniciando CorePulse AI Model Host...
    echo       Primera ejecucion: el modelo puede descargar varios GB.
    if /i "%LLAMA_KIND%"=="UNIFIED" (
        start "CorePulse AI - Model Host" /D "%MODEL_DIR%" cmd /k ""%LLAMAEXE%" serve -hf %MODEL_NAME% --port 8766"
    ) else (
        start "CorePulse AI - Model Host" /D "%MODEL_DIR%" cmd /k ""%LLAMAEXE%" -hf %MODEL_NAME% --port 8766"
    )

    echo       Esperando al modelo generativo...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; for($i=0;$i -lt 180;$i++){ try { $null=Invoke-RestMethod -Uri '%MODEL_URL%' -TimeoutSec 3; exit 0 } catch {}; Start-Sleep -Seconds 5 }; exit 1"
    if errorlevel 1 (
        echo [ERROR] El modelo no quedo disponible dentro de 15 minutos.
        echo Revisa la ventana 'CorePulse AI - Model Host'.
        goto :fail
    )
) else (
    echo [OK] Model Host ya estaba activo.
)

rem ------------------------------------------------------------
rem 5) Iniciar API CorePulse AI si no esta activa
rem ------------------------------------------------------------
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r=Invoke-RestMethod -Uri '%AI_STATUS_URL%' -TimeoutSec 2; if($r.ok){exit 0}else{exit 1} } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
    echo [5/6] Iniciando CorePulse AI Server...
    start "CorePulse AI - Server" /D "%SERVER_DIR%" cmd /k ""%VENV_PY%" -m uvicorn app.main:app --host 127.0.0.1 --port 8765"

    powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; for($i=0;$i -lt 30;$i++){ try { $r=Invoke-RestMethod -Uri '%AI_STATUS_URL%' -TimeoutSec 2; if($r.ok){exit 0} } catch {}; Start-Sleep -Seconds 1 }; exit 1"
    if errorlevel 1 (
        echo [ERROR] CorePulse AI Server no respondio en el puerto 8765.
        echo Revisa la ventana 'CorePulse AI - Server'.
        goto :fail
    )
) else (
    echo [OK] CorePulse AI Server ya estaba activo.
)

rem Confirmar que el backend ve el modelo.
for /f "delims=" %%S in ('powershell -NoProfile -ExecutionPolicy Bypass -Command "$r=Invoke-RestMethod -Uri '%AI_STATUS_URL%' -TimeoutSec 3; if($r.model_ready){'READY'}else{'FALLBACK'}" 2^>nul') do set "AI_MODE=%%S"
if /i "%AI_MODE%"=="READY" (
    echo [OK] CorePulse AI generativa lista.
) else (
    echo [AVISO] El servidor responde, pero el modelo aun no figura listo.
    echo         CorePulse puede usar temporalmente Evidence Engine.
)

rem ------------------------------------------------------------
rem 6) Iniciar CorePulse
rem ------------------------------------------------------------
echo [6/6] Iniciando CorePulse...
start "" wscript.exe "%ROOT%CorePulse.vbs"

echo.
echo ============================================================
echo  TODO LISTO
echo  Model Host : http://127.0.0.1:8766
echo  AI Server  : http://127.0.0.1:8765
echo  CorePulse  : iniciado
echo ============================================================
echo.
timeout /t 3 /nobreak >nul
exit /b 0

:fail
echo.
echo CorePulse AI no pudo completar el inicio automatico.
echo Corrige el mensaje mostrado arriba y vuelve a ejecutar este mismo BAT.
echo.
pause
exit /b 1
