# CorePulse V478 — Organización de core/ y gui/

La versión anterior acumulaba 105 archivos en `core/` y 53 en `gui/`, todos en su nivel superior.
Se conservan los módulos: se **trasladaron**, no se borraron. Los nombres importables siguen siendo `core.nombre` y `gui.nombre`.

## Directorios temáticos

Los componentes críticos que buscan rutas físicas exactas (arranque, versión, algunos tests heredados y los paneles principales) permanecen en el directorio raíz.

**Core:**
- `core/ai_engine/`: 11 módulos
- `core/benchmarks/`: 6 módulos
- `core/diagnostics/`: 23 módulos
- `core/maintenance/`: 11 módulos
- `core/reports/`: 4 módulos
- `core/runtime/`: 16 módulos
- `core/sensors/`: 19 módulos
- `core/storage/`: 5 módulos

**Interfaz:**
- `gui/ai_widgets/`: 2 módulos
- `gui/components/`: 8 módulos
- `gui/dashboard_parts/`: 5 módulos
- `gui/navigation/`: 5 módulos
- `gui/panels/`: 15 módulos
- `gui/windowing/`: 5 módulos

## Compatibilidad y seguridad

- `core/__init__.py` y `gui/__init__.py` amplían rutas de módulos (`__path__`), para conservar importaciones históricas sin miles de wrappers.
- Las rutas raíz dependientes de `__file__` permanecen en su ubicación original.
- `build/CorePulse.spec` recolecta los submódulos tras la reorganización.
- La modificación es **estructural**, no implementa funciones nuevas, no cambia consentimiento ni telemetría.
- El EXE/instalador Windows requiere una compilación y prueba real de distribución antes de publicación.

## Estructura exacta (módulo → carpeta)

### Core
- `adaptive_diagnostic` → `core/diagnostics/adaptive_diagnostic.py`
- `agent_reaction` → `core/ai_engine/agent_reaction.py`
- `ai_action_intelligence` → `core/ai_engine/ai_action_intelligence.py`
- `ai_credentials` → `core/ai_engine/ai_credentials.py`
- `ai_investigation_history` → `core/ai_engine/ai_investigation_history.py`
- `ai_provider_binding` → `core/ai_engine/ai_provider_binding.py`
- `ai_query_context` → `core/ai_engine/ai_query_context.py`
- `ai_report_engine` → `core/ai_engine/ai_report_engine.py`
- `ai_runtime_manager` → `core/ai_engine/ai_runtime_manager.py`
- `ai_user_control` → `core/ai_engine/ai_user_control.py`
- `alert_engine` → `core/diagnostics/alert_engine.py`
- `alert_history_persistence` → `core/diagnostics/alert_history_persistence.py`
- `alert_history_store` → `core/diagnostics/alert_history_store.py`
- `audio_test` → `core/maintenance/audio_test.py`
- `battery_health` → `core/runtime/battery_health.py`
- `before_after` → `core/diagnostics/before_after.py`
- `benchmark_engine` → `core/benchmarks/benchmark_engine.py`
- `benchmark_presentation` → `core/benchmarks/benchmark_presentation.py`
- `benchmark_telemetry` → `core/benchmarks/benchmark_telemetry.py`
- `benchmark_version` → `core/benchmarks/benchmark_version.py`
- `cancellable_process` → `core/runtime/cancellable_process.py`
- `complete_diagnostic` → `core/diagnostics/complete_diagnostic.py`
- `corepulse_diagnostics` → `core/diagnostics/corepulse_diagnostics.py`
- `cpu_frequency` → `core/sensors/cpu_frequency.py`
- `device_identity` → `core/sensors/device_identity.py`
- `diagnostic_evidence` → `core/diagnostics/diagnostic_evidence.py`
- `diagnostic_explainer` → `core/diagnostics/diagnostic_explainer.py`
- `diagnostic_history` → `core/diagnostics/diagnostic_history.py`
- `diagnostic_lifecycle` → `core/diagnostics/diagnostic_lifecycle.py`
- `diagnostic_pipeline` → `core/diagnostics/diagnostic_pipeline.py`
- `diagnostic_session` → `core/diagnostics/diagnostic_session.py`
- `diagnostic_summary` → `core/diagnostics/diagnostic_summary.py`
- `directx_benchmark` → `core/benchmarks/directx_benchmark.py`
- `directx_scene` → `core/benchmarks/directx_scene.py`
- `driver_updates` → `core/maintenance/driver_updates.py`
- `env_config` → `core/runtime/env_config.py`
- `fps_certification` → `core/sensors/fps_certification.py`
- `frozen_selftest` → `core/runtime/frozen_selftest.py`
- `global_hotkeys` → `core/runtime/global_hotkeys.py`
- `gpu_display_logic` → `core/sensors/gpu_display_logic.py`
- `hardware_policy` → `core/diagnostics/hardware_policy.py`
- `health_engine` → `core/diagnostics/health_engine.py`
- `health_history` → `core/diagnostics/health_history.py`
- `health_intelligence` → `core/diagnostics/health_intelligence.py`
- `internet_speed_test` → `core/maintenance/internet_speed_test.py`
- `lhm_official` → `core/sensors/lhm_official.py`
- `lhm_provider` → `core/sensors/lhm_provider.py`
- `live_health` → `core/diagnostics/live_health.py`
- `network_details` → `core/maintenance/network_details.py`
- `nvme_smart_windows` → `core/storage/nvme_smart_windows.py`
- `overlay_preferences` → `core/runtime/overlay_preferences.py`
- `overlay_theme` → `core/runtime/overlay_theme.py`
- `pawnio_support` → `core/sensors/pawnio_support.py`
- `pdf_context` → `core/reports/pdf_context.py`
- `presentmon_fps` → `core/sensors/presentmon_fps.py`
- `presentmon_same_pid` → `core/sensors/presentmon_same_pid.py`
- `product_contract` → `core/runtime/product_contract.py`
- `pythonnet_shutdown` → `core/runtime/pythonnet_shutdown.py`
- `ram_optimizer` → `core/maintenance/ram_optimizer.py`
- `realtime_agent` → `core/ai_engine/realtime_agent.py`
- `recommendation_engine` → `core/diagnostics/recommendation_engine.py`
- `report_base` → `core/reports/report_base.py`
- `report_builder` → `core/reports/report_builder.py`
- `report_generator` → `core/reports/report_generator.py`
- `rtss_osd` → `core/sensors/rtss_osd.py`
- `rtss_overlay_service` → `core/runtime/rtss_overlay_service.py`
- `runtime_logging` → `core/runtime/runtime_logging.py`
- `safe_shutdown` → `core/runtime/safe_shutdown.py`
- `safe_storage_cleanup` → `core/storage/safe_storage_cleanup.py`
- `sensor_diagnostics` → `core/sensors/sensor_diagnostics.py`
- `sensor_stack_setup` → `core/sensors/sensor_stack_setup.py`
- `session_recovery` → `core/diagnostics/session_recovery.py`
- `session_trends` → `core/diagnostics/session_trends.py`
- `startup_analyzer` → `core/maintenance/startup_analyzer.py`
- `startup_profiler` → `core/runtime/startup_profiler.py`
- `startup_readiness` → `core/runtime/startup_readiness.py`
- `storage_details` → `core/storage/storage_details.py`
- `storage_health` → `core/storage/storage_health.py`
- `storage_summary_health` → `core/storage/storage_summary_health.py`
- `telemetry_background` → `core/sensors/telemetry_background.py`
- `telemetry_consistency` → `core/sensors/telemetry_consistency.py`
- `telemetry_full` → `core/sensors/telemetry_full.py`
- `telemetry_lhm` → `core/sensors/telemetry_lhm.py`
- `telemetry_reliable` → `core/sensors/telemetry_reliable.py`
- `telemetry_sampling` → `core/sensors/telemetry_sampling.py`
- `telemetry_storage_cache` → `core/sensors/telemetry_storage_cache.py`
- `theme_manager` → `core/runtime/theme_manager.py`
- `thermal_throttling` → `core/diagnostics/thermal_throttling.py`
- `tray_service` → `core/runtime/tray_service.py`
- `tutorial_research` → `core/ai_engine/tutorial_research.py`
- `windows_audio` → `core/maintenance/windows_audio.py`
- `windows_commands` → `core/maintenance/windows_commands.py`
- `windows_health` → `core/maintenance/windows_health.py`
- `windows_repair` → `core/maintenance/windows_repair.py`
- `windows_tweaks` → `core/maintenance/windows_tweaks.py`

### GUI
- `adaptive_window` → `gui/windowing/adaptive_window.py`
- `ai_native_status_canvas` → `gui/ai_widgets/ai_native_status_canvas.py`
- `ai_status_card` → `gui/ai_widgets/ai_status_card.py`
- `alert_history_panel` → `gui/panels/alert_history_panel.py`
- `alert_panel` → `gui/panels/alert_panel.py`
- `audio_test_panel` → `gui/panels/audio_test_panel.py`
- `benchmark_history_panel` → `gui/panels/benchmark_history_panel.py`
- `card_workspace_surface` → `gui/dashboard_parts/card_workspace_surface.py`
- `cleaning_actions` → `gui/panels/cleaning_actions.py`
- `compact_sidebar` → `gui/navigation/compact_sidebar.py`
- `cpu_detail_panel` → `gui/panels/cpu_detail_panel.py`
- `dialogs` → `gui/components/dialogs.py`
- `flat_workspace_page` → `gui/components/flat_workspace_page.py`
- `gpu_detail_panel` → `gui/panels/gpu_detail_panel.py`
- `hardware_storage_view` → `gui/panels/hardware_storage_view.py`
- `header_identity_canvas` → `gui/dashboard_parts/header_identity_canvas.py`
- `health_center_panel` → `gui/panels/health_center_panel.py`
- `high_refresh` → `gui/windowing/high_refresh.py`
- `integration` → `gui/components/integration.py`
- `internal_navigation` → `gui/navigation/internal_navigation.py`
- `live_health_binding` → `gui/components/live_health_binding.py`
- `overlay` → `gui/windowing/overlay.py`
- `overlay_config_panel` → `gui/panels/overlay_config_panel.py`
- `professional_visuals` → `gui/dashboard_parts/professional_visuals.py`
- `ram_detail_panel` → `gui/panels/ram_detail_panel.py`
- `render_polish` → `gui/dashboard_parts/render_polish.py`
- `resize_render_guard` → `gui/windowing/resize_render_guard.py`
- `session_trends_panel` → `gui/panels/session_trends_panel.py`
- `sidebar` → `gui/navigation/sidebar.py`
- `sidebar_native_hover` → `gui/navigation/sidebar_native_hover.py`
- `stable_scroll` → `gui/navigation/stable_scroll.py`
- `startup_gate` → `gui/windowing/startup_gate.py`
- `status_symbols` → `gui/dashboard_parts/status_symbols.py`
- `storage_detail_panel` → `gui/panels/storage_detail_panel.py`
- `telemetry_detail_panel` → `gui/panels/telemetry_detail_panel.py`
- `theme_panel` → `gui/panels/theme_panel.py`
- `thermal_health_binding` → `gui/components/thermal_health_binding.py`
- `tweak_restore_center` → `gui/components/tweak_restore_center.py`
- `ui_consistency` → `gui/components/ui_consistency.py`
- `widget_updates` → `gui/components/widget_updates.py`
