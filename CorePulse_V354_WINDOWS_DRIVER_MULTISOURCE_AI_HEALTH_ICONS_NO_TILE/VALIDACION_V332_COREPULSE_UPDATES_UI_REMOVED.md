# Validación V332 — CorePulse Updates UI Removed

## Objetivo
Corregir la consolidación para preservar la decisión de producto de eliminar el módulo interno **Actualizaciones de CorePulse**.

## Contrato visible
- En **Personalización** sólo aparecen **Temas** y **CorePulse AI**.
- No existe botón, ruta, diálogo ni módulo interno de actualización de la propia aplicación.
- El **Driver Hub** continúa pudiendo buscar/descargar/instalar controladores.
- La categoría **Actualizaciones** de Tweaks de Windows sigue disponible porque administra políticas de Windows, no actualizaciones de CorePulse.

## No regresión
- `REAL_OR_NA` y `REAL_FPS_OR_NA_ONLY` sin cambios.
- CorePulse AI consolidada sin cambios.
- Driver Hub multi-source sin cambios.
