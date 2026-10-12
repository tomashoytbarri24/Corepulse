@echo off
setlocal
cd /d "%~dp0..\.."
echo ==========================================
echo CorePulse AI V462 - Evaluador OFFLINE
 echo Sin peticiones a la nube, sin LLM local.
echo ==========================================
if not exist "resultados" mkdir "resultados"
python "CorePulse_AI_Server\evaluation\benchmark_v462.py" --out "resultados\corepulse_ai_v462_dataset_validado.json"
if errorlevel 1 (
  echo ERROR: No se pudo validar el dataset.
  pause
  exit /b 1
)
echo Informe guardado en resultados\corepulse_ai_v462_dataset_validado.json
echo Nota: este informe NO contiene resultados de modelos reales.
pause
