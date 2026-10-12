"""GUI: módulos agrupados conservando imports históricos ``gui.nombre``.

La compatibilidad preserva las llamadas ya utilizadas por CorePulse y sus pruebas.
No se modifica ningún sensor ni se introduce lógica nueva de IA.
"""
from pathlib import Path as _Path

# Estas carpetas son *ubicaciones físicas*, no subpaquetes con APIs nuevas.
# Permite ``import gui.telemetry_lhm`` aunque el archivo esté en sensors/.
_COMPAT_DIRECTORIES = ('ai_widgets', 'components', 'dashboard_parts', 'navigation', 'panels', 'windowing')
for _part in _COMPAT_DIRECTORIES:
    _location = str(_Path(__file__).resolve().parent / _part)
    if _location not in __path__:
        __path__.append(_location)
del _part, _location, _Path

# Compatibilidad diferida V481–V484: imports históricos planos y con subcarpeta.
from _corepulse_compat_imports import install as _install_consolidated
_install_consolidated({
    'gui.navigation.compact_sidebar': 'gui.internal_navigation',
    'gui.compact_sidebar': 'gui.internal_navigation',
    'gui.dialogs': 'gui.integration',
    'gui.components.dialogs': 'gui.integration',
    'gui.chart_workspace_surface': 'gui.card_workspace_surface',
    'gui.components.thermal_health_binding': 'gui.live_health_binding',
    'gui.dashboard_parts.header_identity_canvas': 'gui.professional_visuals',
    'gui.dashboard_parts.render_polish': 'gui.professional_visuals',
    'gui.dashboard_parts.status_symbols': 'gui.professional_visuals',
    'gui.header_identity_canvas': 'gui.professional_visuals',
    'gui.high_refresh': 'gui.resize_render_guard',
    'gui.navigation.sidebar': 'gui.internal_navigation',
    'gui.navigation.sidebar_native_hover': 'gui.sidebar_native_hover',
    'gui.render_polish': 'gui.professional_visuals',
    'gui.sidebar': 'gui.internal_navigation',
    'gui.status_symbols': 'gui.professional_visuals',
    'gui.thermal_health_binding': 'gui.live_health_binding',
    'gui.windowing.high_refresh': 'gui.resize_render_guard',
})
del _install_consolidated
