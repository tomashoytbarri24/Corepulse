@echo off
setlocal
cd /d "%~dp0..\.."
echo ==========================================
echo CorePulse AI V462 - Benchmark CLOUD REAL
 echo Requiere servidor GPU YA CONFIGURADO.
echo SOLO envia los 30 casos SINTETICOS del benchmark.
echo No utiliza telemetria de tu PC.
echo ==========================================
echo Configura COREPULSE_MODEL_BASE_URL y COREPULSE_MODEL_NAME.
if "%COREPULSE_MODEL_BASE_URL%"=="" (
 echo ERROR: COREPULSE_MODEL_BASE_URL vacio.
 pause
 exit /b 1
)
if "%COREPULSE_MODEL_NAME%"=="" (
 echo ERROR: COREPULSE_MODEL_NAME vacio.
 pause
 exit /b 1
)
choice /C SN /M "Confirma que deseas enviar SOLO CASOS SINTETICOS al modelo remoto"
if errorlevel 2 exit /b 1
if not exist "resultados" mkdir "resultados"
python "CorePulse_AI_Server\evaluation\benchmark_v462.py" --live --confirm-synthetic-transmission --out "resultados\corepulse_ai_v462_modelo_real.json"
if errorlevel 1 (
 echo ERROR: Evaluacion interrumpida o configuracion invalida.
 pause
 exit /b 1
)
echo Resultados de inferencia guardados en resultados\corepulse_ai_v462_modelo_real.json
echo Cambia el nombre del archivo antes de evaluar otro modelo.
pause
