"""CORE: módulos agrupados conservando imports históricos ``core.nombre``.

La compatibilidad preserva las llamadas ya utilizadas por CorePulse y sus pruebas.
No se modifica ningún sensor ni se introduce lógica nueva de IA.
"""
from pathlib import Path as _Path

# Estas carpetas son *ubicaciones físicas*, no subpaquetes con APIs nuevas.
# Permite ``import core.telemetry_lhm`` aunque el archivo esté en sensors/.
_COMPAT_DIRECTORIES = ('ai_engine', 'benchmarks', 'diagnostics', 'maintenance', 'reports', 'runtime', 'sensors', 'storage')
for _part in _COMPAT_DIRECTORIES:
    _location = str(_Path(__file__).resolve().parent / _part)
    if _location not in __path__:
        __path__.append(_location)
del _part, _location, _Path

# Compatibilidad diferida V481–V485: imports históricos planos y con subcarpeta.
from _corepulse_compat_imports import install as _install_consolidated
_install_consolidated({
    'core.frozen_selftest': 'core.startup_readiness',
    'core.runtime.frozen_selftest': 'core.startup_readiness',
    'core.health_history': 'core.session_trends',
    'core.diagnostics.health_history': 'core.session_trends',
    'core.sensors.cpu_frequency': 'core.device_identity',
    'core.cpu_frequency': 'core.device_identity',
    'core.diagnostics.before_after': 'core.session_trends',
    'core.before_after': 'core.session_trends',
    'core.env_config': 'core.runtime_logging',
    'core.runtime.env_config': 'core.runtime_logging',
    'core.runtime.product_contract': 'core.version',
    'core.runtime.cancellable_process': 'core.windows_commands',
    'core.product_contract': 'core.version',
    'core.diagnostics.adaptive_diagnostic': 'core.session_recovery',
    'core.cancellable_process': 'core.windows_commands',
    'core.adaptive_diagnostic': 'core.session_recovery',
    'core.alert_engine': 'core.alert_history_store',
    'core.alert_history_persistence': 'core.alert_history_store',
    'core.audio_test': 'core.windows_audio',
    'core.diagnostic_evidence': 'core.diagnostic_summary',
    'core.diagnostic_explainer': 'core.diagnostic_summary',
    'core.diagnostic_history': 'core.session_recovery',
    'core.diagnostic_lifecycle': 'core.session_recovery',
    'core.diagnostic_pipeline': 'core.recommendation_engine',
    'core.diagnostic_session': 'core.session_recovery',
    'core.diagnostics.alert_engine': 'core.alert_history_store',
    'core.diagnostics.alert_history_persistence': 'core.alert_history_store',
    'core.diagnostics.diagnostic_evidence': 'core.diagnostic_summary',
    'core.diagnostics.diagnostic_explainer': 'core.diagnostic_summary',
    'core.diagnostics.diagnostic_history': 'core.session_recovery',
    'core.diagnostics.diagnostic_lifecycle': 'core.session_recovery',
    'core.diagnostics.diagnostic_pipeline': 'core.recommendation_engine',
    'core.diagnostics.diagnostic_session': 'core.session_recovery',
    'core.diagnostics.health_intelligence': 'core.health_engine',
    'core.diagnostics.thermal_throttling': 'core.health_engine',
    'core.gpu_display_logic': 'core.device_identity',
    'core.health_intelligence': 'core.health_engine',
    'core.maintenance.audio_test': 'core.windows_audio',
    'core.nvme_smart_windows': 'core.smartctl_storage',
    'core.overlay_theme': 'core.overlay_preferences',
    'core.pawnio_support': 'core.sensor_stack_setup',
    'core.pdf_context': 'core.report_builder',
    'core.pythonnet_shutdown': 'core.safe_shutdown',
    'core.report_generator': 'core.report_builder',
    'core.reports.pdf_context': 'core.report_builder',
    'core.reports.report_generator': 'core.report_builder',
    'core.runtime.overlay_theme': 'core.overlay_preferences',
    'core.runtime.pythonnet_shutdown': 'core.safe_shutdown',
    'core.runtime.startup_profiler': 'core.startup_readiness',
    'core.sensor_diagnostics': 'core.corepulse_diagnostics',
    'core.sensors.gpu_display_logic': 'core.device_identity',
    'core.sensors.pawnio_support': 'core.sensor_stack_setup',
    'core.sensors.sensor_diagnostics': 'core.corepulse_diagnostics',
    'core.startup_profiler': 'core.startup_readiness',
    'core.storage.nvme_smart_windows': 'core.smartctl_storage',
    'core.storage.storage_summary_health': 'core.storage_health',
    'core.storage_summary_health': 'core.storage_health',
    'core.thermal_throttling': 'core.health_engine',
})
del _install_consolidated
