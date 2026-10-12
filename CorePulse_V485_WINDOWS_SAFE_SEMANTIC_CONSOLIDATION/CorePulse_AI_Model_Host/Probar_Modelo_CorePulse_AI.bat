@echo off
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "Unblock-File -LiteralPath '%~dp0Probar_Modelo_CorePulse_AI.ps1' -ErrorAction SilentlyContinue" >nul 2>&1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Probar_Modelo_CorePulse_AI.ps1"
