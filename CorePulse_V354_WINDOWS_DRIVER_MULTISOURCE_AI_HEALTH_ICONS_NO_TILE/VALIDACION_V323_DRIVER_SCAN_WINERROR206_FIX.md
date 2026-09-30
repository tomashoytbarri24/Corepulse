# V323 — Driver Scan WinError 206 Fix

## Evidencia observada
En V322, al pulsar **Buscar actualizaciones**, Windows devolvía `WinError 206` porque el escaneo profundo serializaba cientos de consultas dentro del argumento `powershell.exe -Command`.

## Corrección
- El script PowerShell se escribe temporalmente en `%TEMP%` con nombre corto.
- PowerShell lo ejecuta mediante `-File`.
- Se elimina el límite práctico de longitud de la línea de comandos sin cambiar las consultas ni la política de validación.
- El archivo temporal se elimina siempre al finalizar.

## Seguridad
- Continúa siendo obligatorio verificar firma del paquete, INF compatible y Hardware ID real antes de instalar.
- BIOS/UEFI/firmware continúan fuera de actualización automática.
