# Validación V341 — Sidebar Hover Expand

## Objetivo
Añadir un micro-efecto de ampliación horizontal al pasar el mouse por una opción del sidebar, inspirado en la referencia en video, sin reintroducir reflow vertical ni afectar la transición estable del sidebar.

## Implementación
- Animación por `pack_configure(padx=...)`.
- 5 pasos de 12 ms con easing cúbico de salida.
- Expansión aproximada total: 12 px.
- Sin modificación de altura, por lo que las filas vecinas permanecen estables.
- Aplicado a navegación principal, Temas y CorePulse AI.
- Deshabilitado durante modo colapsado.

## No regresión
- REAL_OR_NA intacto.
- REAL_FPS_OR_NA_ONLY intacto.
- V312 sidebar transition intacta.
- V340 Gaming Square Cards intacto.
