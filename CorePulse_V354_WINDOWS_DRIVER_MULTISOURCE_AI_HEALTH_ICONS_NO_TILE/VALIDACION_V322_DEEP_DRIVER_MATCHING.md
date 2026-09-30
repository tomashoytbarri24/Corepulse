# VALIDACIÓN V322 — DEEP DRIVER MATCHING

## Objetivo
Ampliar la cobertura de detección de actualizaciones frente a V321, que era demasiado estricta al consultar un solo Hardware ID por dispositivo.

## Flujo
1. Inventario PnP real.
2. Múltiples Hardware IDs por dispositivo.
3. Variante compatible menos específica cuando aplica.
4. Fallback de descubrimiento por proveedor + modelo/nombre.
5. Comparación de versión publicada vs instalada.
6. Antes de instalar: firma válida + INF con Hardware ID real + versión INF superior.

## Seguridad
Las coincidencias por modelo NO autorizan por sí solas la instalación. La instalación sólo continúa si el paquete descargado contiene un INF que coincide con los Hardware IDs reales del equipo.
