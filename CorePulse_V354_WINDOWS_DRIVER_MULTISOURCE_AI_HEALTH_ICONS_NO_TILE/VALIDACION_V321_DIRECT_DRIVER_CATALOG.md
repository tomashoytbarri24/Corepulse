# VALIDACIÓN V321 — DIRECT DRIVER CATALOG

## Objetivo
Reemplazar el flujo de drivers basado en Windows Update Agent por un motor directo controlado por CorePulse.

## Flujo implementado
1. Inventario PnP real y Hardware ID.
2. Consulta online directa por Hardware ID.
3. Comparación de versión instalada y publicada.
4. Descarga directa del paquete.
5. Extracción del CAB.
6. Verificación de firma de catálogo.
7. Verificación del Hardware ID dentro del INF.
8. Confirmación de una versión INF superior.
9. Backup del driver actual y punto de restauración.
10. Instalación con pnputil.

## Seguridad
- BIOS/UEFI/firmware excluidos del modo automático.
- Paquetes sin firma válida se rechazan.
- Paquetes sin INF compatible se rechazan.
- Un paquete cuyo INF no confirme una versión superior se rechaza.

## Validación local
- compileall: PASS
- pytest: 51/51 PASS

## Nota
La consulta web real y la instalación de drivers sólo pueden validarse de extremo a extremo en Windows con conexión a Internet y privilegios administrativos.
