@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title CorePulse AI Cloud - Inicio ligero
echo CorePulse AI V460 utiliza la nube.
echo No se iniciara llama.cpp ni se descargara ningun modelo local.
echo Configura servidor HTTPS y permisos dentro de la pestaña CorePulse AI.
start "" wscript.exe "%~dp0CorePulse.vbs"
exit /b 0
