# División de CorePulse por áreas

**Versión de referencia:** REBUILD 177. **Equipo:** Agustín Valdés, Maximiliano Carrasco y Tomás Hoyt.

Cada integrante es responsable de corregir los bugs de su área. Esta división es una propuesta para acordar en equipo.

| Área | Responsable | Python | QML | Otro código |
|---|---|---|---|---|
| Juegos, interfaz y web | Agustín | 8.407 líneas | 5.045 líneas | Módulos nativos (3.394) y sitio web |
| Salud, mantenimiento y validación | Maximiliano | 7.729 líneas | 3.024 líneas | Matriz de pruebas |
| Sistema, datos e IA | Tomás | 8.822 líneas | 1.721 líneas | Nube de IA e instalador |

## Agustín: juegos, interfaz y web

**Funciones:** overlay, FPS, sesiones de juego, Game Boost, benchmark, navegación, temas, buscador, cuenta y sitio web.

**Archivos:**

- `core/overlay.py`, `core/benchmark.py`, `core/benchmark_gpu.py`, `core/directx_scene.py`, `core/cuenta.py`
- `core/health/`: `fps.py`, `game_capture.py`, `game_sessions.py`, `game_boost.py`, `performance.py`
- `native/`
- `ui/`: `Main`, `Overview`, `ThemesPage`, `GlobalSearch`, `OverlayPage`, `OverlayDesigner`, `GameSessionsPage`, `ProblemRecords`, `BenchmarkPage`, `FrametimeChart` y los componentes compartidos
- `FASE 2/Evidencias Proyecto/Evidencias de sistema/Aplicación/CorePulse-web/`

**Prioridades:**

1. Probar el overlay externo y el módulo interno en juegos reales a 1080p y 2,5K.
2. Revisar qué pasa en pantalla completa exclusiva, donde el overlay externo puede no verse.
3. Probar el flujo completo de inicio de sesión web en Windows.
4. Actualizar sus 24 pruebas fallidas.
5. Quitar los 188 archivos de ejemplo de ImGui que no se usan en `native/vendor/kiero`, después de confirmar que la compilación no los necesita.

## Maximiliano: salud, mantenimiento y validación

**Funciones:** Centro de Salud, batería, almacenamiento, reparación, recuperación, estabilidad, limpieza, red, prueba de velocidad, inicio de Windows, audio, informes PDF e historial de cambios.

**Archivos:**

- `core/health/`: `battery.py`, `storage.py`, `windows.py`, `recovery.py`, `repair.py`, `stability.py`, `history.py`, `report.py`
- `core/maintenance/`
- `ui/`: `HealthPage`, `CleanupPage`, `NetworkPage`, `StartupPage`, `ReportsPage`

**Prioridades:**

1. Ejecutar la matriz de pruebas en al menos tres equipos.
2. Revisar cada función de su área sin administrador, porque la 177 ya no lo exige al abrir. La limpieza profunda es la primera a revisar.
3. Revisar el PDF y sus datos sin permisos completos.
4. Actualizar sus 15 pruebas fallidas.

## Tomás: sistema, datos e IA

**Funciones:** arranque, permisos, telemetría, sensores, PawnIO, tweaks, CorePulse AI, tendencias, integración de versiones e instalador.

**Archivos:**

- `main.py`, `core/runtime.py`, `core/ai.py`, `core/monitoring/telemetry.py`
- `core/tweaks/`
- `core/health/`: `monitoring_insights.py`, `system_health.py`
- `cloud/corepulse-ai/`, `installer/`
- `ui/`: `AIPage`, `TweaksPage`, `InsightsPage`, `ComponentDetail`, `HistoryChart`

**Prioridades:**

1. Resolver la temperatura de CPU sin administrador, que hoy aparece como N/A.
2. Probar la instalación de PawnIO en un equipo que no lo tenga, usando el botón del Resumen.
3. Firmar el instalador, si el equipo decide pagar el certificado.
4. Investigar por qué se corta la ejecución de varias suites de pruebas juntas.
5. Actualizar sus 18 pruebas fallidas.

## Pruebas fallidas por área

Son las 57 fallas de `tests/test_rebuild.py`. Se repartieron según el nombre de cada prueba: quien la revise puede reasignarla si corresponde a otra área.

**Agustín (24)**

- `test_all_qml_components_exist`
- `test_sidebar_logo_removed_and_navigation_moves_up_without_losing_drag`
- `test_rebuild_008_direct_geometry_no_scaled_shape_and_sidebar_contract`
- `test_014_clicking_only_cpu_gpu_ram_icons_opens_real_component_page`
- `test_rebuild_032_scrollbars_are_custom_but_scrollable_and_reusable`
- `test_050_game_card_no_invented_data_and_update_while_visible`
- `test_themes_module_exists_and_shell_palette_is_switchable`
- `test_055_theme_catalog_has_ten_distinct_complete_palettes`
- `test_056_sidebar_collapsed_hover_is_animated_and_shows_tooltips`
- `test_060_session_storage_never_plaintext_outside_windows`
- `test_062_history_chart_smooth_and_honest`
- `test_overlay_page_exists_and_uses_real_metrics`
- `test_068_overlay_bindings_and_shared_memory_own_slot`
- `test_068_native_panel_has_theme_and_mouse_controls`
- `test_082_action_buttons_colored_text_and_solid_only_for_apply_update`
- `test_rebuild_089_gpu_brand_logo_follows_monitored_adapter`
- `test_rebuild_090_gpu_header_brand_badges`
- `test_rebuild_092_chart_legend_displays_vendor_icons_without_changing_data`
- `test_v131_sidebar_reveals_exactly_the_window_gradient`
- `test_v133_sidebar_divider_follows_current_theme_accent`
- `test_v155_popup_liquid_glass_is_app_level_and_dismissable`
- `test_v156_glass_notice_uses_live_theme_and_not_solid_gray`
- `test_v167_global_search_is_wired_into_sidebar_and_tweaks`
- `test_v171_sizes_and_icons_match_host_across_resolutions`

**Maximiliano (15)**

- `test_rebuild_026_deep_and_standby_actions`
- `test_rebuild_028_hover_dialogs_and_verified_success`
- `test_rebuild_029_ram_meter_updates_while_future_is_running_and_stops_on_res...`
- `test_rebuild_029_progress_modal_is_real_and_success_is_result_gated`
- `test_rebuild_030_cleanup_compact_by_default_and_results_accessible`
- `test_rebuild_033_ram_monitor_uses_corepulse_palette_not_sky_blue`
- `test_rebuild_033_no_changes_to_ram_data_or_interaction`
- `test_rebuild_034_all_cleanup_dialogs_use_same_corepulse_card_skin`
- `test_storage_data_does_not_claim_wear_percent_or_guess_smart`
- `test_windows_cards_details_raised_and_repair_ui_present`
- `test_history_044_qml_routes_without_duplicate_modules`
- `test_048_audio_stereo_channels_and_pcm_header`
- `test_rebuild_097_card_surfaces_match_cleanup_and_overview`
- `test_v142_cards_are_globally_consolidated_and_controls_preserved`
- `test_v145_diagnostic_main_cards_use_global_glass_without_nested_gray_plates`

**Tomás (18)**

- `test_minimal_tree_and_single_launcher`
- `test_rebuild_035_launcher_executes_from_its_own_absolute_paths`
- `test_cpu_clock_does_not_use_windows_base_clock_as_live_frequency`
- `test_cpu_temp_gpu_ram_and_disk_model_are_presented_without_undefined`
- `test_clock_reads_measured_cpu_sensor_before_windows_estimation`
- `test_telemetry_sources_explain_comparability_without_changing_layout`
- `test_classic_hardwaremonitor_cpu_route_is_brought_back_without_importing_le...`
- `test_classic_monitor_uses_separate_process_and_does_not_install_driver`
- `test_classic_cpu_temperature_selection_disallows_gpu_nvm_and_zero`
- `test_rebuild_013_cpu_clock_label_has_no_unusual_prefix_but_keeps_estimate_h...`
- `test_018_blocked_adjustment_never_writes`
- `test_rebuild_032_unmodified_windows_engines_and_coverage`
- `test_045_wiring_navigation_unique_and_inherited_engines_unchanged`
- `test_061_main_qml_still_loads_ai_page_and_labels_new_release`
- `test_062_rules_and_new_version_are_present`
- `test_064_settings_collapse_when_connected_but_user_can_reopen`
- `test_065_agustin_chart_and_cloud_ai_coexist`
- `test_v154_pawnio_shared_entrypoint_and_shell_elevation`

## Reglas para no pisarse

1. Cada integrante trabaja en su rama y en los archivos de su área.
2. Si un bug toca el área de otro, se avisa al responsable antes de cambiarlo.
3. `main.py` y `ui/Main.qml` conectan toda la aplicación: un cambio en ellos se coordina con Tomás o Agustín, según corresponda.
4. Tomás integra las versiones. Nadie fusiona en `main` sin revisión.
5. Toda corrección sigue las reglas del proyecto: leer el TXT y el historial, registrar el cambio y correr las pruebas.
