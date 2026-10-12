@echo off
setlocal
cd /d "%~dp0..\.."
echo [CorePulse V472] Pruebas locales sin necesidad de proveedor externo.
python -m pytest -q tests/test_v472_provider_independence.py
pause
