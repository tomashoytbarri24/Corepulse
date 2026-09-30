# VALIDACIÓN V320 — Driver Update Center

## Objetivo
Agregar búsqueda e instalación real de controladores sin convertir la edad del paquete en una falsa afirmación de actualización disponible.

## Fuente
- Microsoft Windows Update Agent (COM local de Windows).
- Inventario: Win32_PnPSignedDriver + Win32_PnPEntity HardwareID.

## Seguridad
- Sólo se muestran actualizaciones que Windows Update considera aplicables al PC actual.
- Hardware ID exacto se marca sólo cuando hay coincidencia real.
- La instalación revalida UpdateID + RevisionNumber antes de descargar/instalar.
- Se intenta exportar el INF instalado y crear punto de restauración antes del cambio.
- No se instalan BIOS/firmware desde este flujo ni se usa catálogo genérico de terceros.

## Política
- REAL_OR_NA preservado.
- Ninguna actualización se inventa o infiere por antigüedad.
