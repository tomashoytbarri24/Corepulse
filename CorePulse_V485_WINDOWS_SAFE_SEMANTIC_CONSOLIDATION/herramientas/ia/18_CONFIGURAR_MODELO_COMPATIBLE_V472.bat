@echo off
setlocal
cd /d "%~dp0..\..\CorePulse_AI_Server"
echo [CorePulse V472] Configurar un modelo remoto de API compatible.
echo Solo destinos HTTPS de confianza. No instala ni contrata un servidor.
python -m app.compatible_setup configure
pause
