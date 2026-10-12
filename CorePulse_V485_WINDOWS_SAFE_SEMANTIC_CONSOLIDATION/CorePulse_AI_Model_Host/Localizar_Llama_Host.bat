@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "FOUND="

rem 1) PATH actual.
for /f "delims=" %%L in ('where llama-server.exe 2^>nul') do if not defined FOUND set "FOUND=%%L"
if not defined FOUND for /f "delims=" %%L in ('where llama.exe 2^>nul') do if not defined FOUND set "FOUND=%%L"
if defined FOUND goto :emit

rem 2) Enlaces portables de WinGet. No requiere reiniciar la terminal.
if defined LOCALAPPDATA (
    if exist "%LOCALAPPDATA%\Microsoft\WinGet\Links\llama-server.exe" set "FOUND=%LOCALAPPDATA%\Microsoft\WinGet\Links\llama-server.exe"
    if not defined FOUND if exist "%LOCALAPPDATA%\Microsoft\WinGet\Links\llama.exe" set "FOUND=%LOCALAPPDATA%\Microsoft\WinGet\Links\llama.exe"
)
if defined FOUND goto :emit

rem 3) Buscar directamente dentro de los paquetes WinGet del usuario.
if defined LOCALAPPDATA (
    if exist "%LOCALAPPDATA%\Microsoft\WinGet\Packages" (
        for /f "delims=" %%L in ('where /r "%LOCALAPPDATA%\Microsoft\WinGet\Packages" llama-server.exe 2^>nul') do if not defined FOUND set "FOUND=%%L"
        if not defined FOUND for /f "delims=" %%L in ('where /r "%LOCALAPPDATA%\Microsoft\WinGet\Packages" llama.exe 2^>nul') do if not defined FOUND set "FOUND=%%L"
    )
)
if defined FOUND goto :emit

rem 4) Fallback de instalación por máquina, si existe.
if defined ProgramFiles (
    if exist "%ProgramFiles%\WinGet\Packages" (
        for /f "delims=" %%L in ('where /r "%ProgramFiles%\WinGet\Packages" llama-server.exe 2^>nul') do if not defined FOUND set "FOUND=%%L"
        if not defined FOUND for /f "delims=" %%L in ('where /r "%ProgramFiles%\WinGet\Packages" llama.exe 2^>nul') do if not defined FOUND set "FOUND=%%L"
    )
)
if defined FOUND goto :emit

exit /b 1

:emit
echo(!FOUND!
exit /b 0
