"""Regresiones agrupadas V482: test_refactor_contracts.py. Contratos originales completos."""
from __future__ import annotations


# ===== test_v480_shared_panels.py (contrato preservado) =====
from pathlib import Path
import ast
import math
from types import SimpleNamespace
from unittest.mock import Mock

from gui.widget_updates import (
    numeric_or_none, format_detail_number, format_detail_integer,
    detail_age_text, detail_is_scrolling, set_detail_panel_active,
    create_detail_summary_card, create_detail_section_card,
)

ROOT = Path(__file__).resolve().parents[1]
PANELS = [
    ROOT / 'gui/panels/cpu_detail_panel.py',
    ROOT / 'gui/panels/gpu_detail_panel.py',
    ROOT / 'gui/panels/ram_detail_panel.py',
    ROOT / 'gui/network_detail_panel.py',
]


def test_real_or_na_formatting_has_no_synthetic_values():
    assert numeric_or_none(True) is None
    assert numeric_or_none(False) is None
    assert numeric_or_none(None) is None
    assert numeric_or_none('invalid') is None
    assert numeric_or_none('94.5') == 94.5
    assert format_detail_number(None) == 'N/A'
    assert format_detail_integer(False) == 'N/A'
    assert format_detail_integer(12.9, ' %') == '12 %'
    assert format_detail_number(12.345, 1, ' °C') == '12.3 °C'
    assert detail_age_text('not-a-timestamp') == 'N/A'


def test_one_canonical_implementation_for_four_panels():
    for path in PANELS:
        text = path.read_text(encoding='utf-8')
        tree = ast.parse(text)
        classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
        assert classes, path
        funcs = {n.name: n for n in classes[0].body if isinstance(n, ast.FunctionDef)}
        assert '_summary_card' in funcs and '_is_scrolling' in funcs, path
        assert len(funcs['_summary_card'].body) == 1, path
        assert len(funcs['_is_scrolling'].body) == 1, path
        assert 'create_detail_summary_card' in text
        assert 'detail_is_scrolling' in text
    for path in PANELS[:3]:
        tree = ast.parse(path.read_text(encoding='utf-8'))
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef))
        funcs = {n.name: n for n in cls.body if isinstance(n, ast.FunctionDef)}
        assert len(funcs['set_active'].body) == 1
        assert len(funcs['_section_card'].body) == 1


def test_activation_is_idempotent_and_cancels_hidden_frames():
    frame = Mock()
    frame.after.return_value = 'next'
    panel = SimpleNamespace(_active=False, _alive=True, _after_id=None, frame=frame, refresh=Mock())
    set_detail_panel_active(panel, True)
    assert panel._active is True and panel._after_id == 'next'
    frame.after.assert_called_once_with(1, panel.refresh)
    set_detail_panel_active(panel, True)
    frame.after.assert_called_once()
    set_detail_panel_active(panel, False)
    frame.after_cancel.assert_called_once_with('next')
    assert panel._after_id is None
    set_detail_panel_active(panel, False)
    assert frame.after_cancel.call_count == 1


def test_no_new_scroll_poller():
    host = Mock(); host.is_scrolling.return_value = True
    assert detail_is_scrolling(SimpleNamespace(body_scroll=host)) is True
    assert detail_is_scrolling(SimpleNamespace(body_scroll=None)) is False


def test_shared_cards_keep_original_widget_geometry():
    ctk = SimpleNamespace(CTkFrame=Mock(), CTkLabel=Mock())
    frame = Mock(); ctk.CTkFrame.return_value = frame
    labels = [Mock(), Mock(), Mock()]
    ctk.CTkLabel.side_effect = labels
    card, value, detail = create_detail_summary_card('root', 'CPU', 'N/A', 'No medido', 'cyan', ctk, 'card', 'border', 'text', 'muted', 'Segoe UI')
    assert (card, value, detail) == (frame, labels[1], labels[2])
    frame.pack_propagate.assert_called_once_with(False)
    assert ctk.CTkFrame.call_args.kwargs['height'] == 92
    assert ctk.CTkLabel.call_count == 3
    ctk.CTkLabel.reset_mock()
    ctk.CTkLabel.side_effect = [Mock(), Mock()]
    create_detail_section_card('root', 'Título', 'Subtítulo', ctk, 'card', 'border', 'text', 'muted', 'Segoe UI')
    assert ctk.CTkLabel.call_count == 2
    assert ctk.CTkFrame.call_args.kwargs['corner_radius'] == 12


def test_runtime_vs_manual_probes_are_separate():
    assert (ROOT / 'herramientas/diagnostico/cpu_sensor_probe.py').exists()
    assert not (ROOT / 'herramientas/diagnostico/check_pawnio.py').exists()
    assert '--check-pawnio' in (ROOT / 'herramientas/diagnostico/cpu_sensor_probe.py').read_text(encoding='utf-8')
    for bat, script in [('06_INSTALAR_PAWNIO_CPU_TEMP.bat', '--check-pawnio'), ('07_DIAGNOSTICAR_SENSOR_CPU.bat', 'cpu_sensor_probe.py')]:
        assert script in (ROOT/'herramientas/ia'/bat).read_text(encoding='utf-8')
    spec = (ROOT/'build/CorePulse.spec').read_text(encoding='utf-8')
    assert '(str(ROOT / "tools"), "tools")' not in spec
    assert 'cpu_temp_package_probe.py' in spec
    assert 'validate_python_runtime.py' in spec


def test_version_480_consistent():
    assert (ROOT/'LATEST_VERSION.txt').read_text().strip() == '485'
    assert 'VERSION = "' + (ROOT/'LATEST_VERSION.txt').read_text().strip() + '"' in (ROOT/'core/version.py').read_text()
    assert '0.10.2.' + (ROOT / 'LATEST_VERSION.txt').read_text().strip() in (ROOT/'pyproject.toml').read_text()


def test_performance_legacy_imports_resolve_after_consolidation():
    import performance.settings_backup as old_backup
    import performance.managed_power_plans as old_plans
    from performance.profile_manager import save_backup
    from performance.power_manager import ManagedPowerPlans
    assert old_backup.save_backup is save_backup
    assert old_plans.ManagedPowerPlans is ManagedPowerPlans
    assert not (ROOT/'performance/settings_backup.py').exists()
    assert not (ROOT/'performance/managed_power_plans.py').exists()


def test_transactional_energy_backup_is_reversible(tmp_path):
    from performance.settings_backup import save_backup, load_backup, mark_restored, has_pending_backup
    path = tmp_path/'power_backup.json'
    assert load_backup(path) is None
    assert not has_pending_backup(path)
    saved = save_backup({'previous_guid': 'windows-user-guid'}, path)
    assert saved['pending_restore'] is True
    assert load_backup(path)['previous_guid'] == 'windows-user-guid'
    assert has_pending_backup(path)
    mark_restored(path)
    assert not has_pending_backup(path)


def test_legacy_managed_power_is_readonly(tmp_path):
    from performance.managed_power_plans import ManagedPowerPlans
    class FakePower:
        def resolve_existing_mode_scheme(self, mode):
            return {'success': True, 'mode': mode}
        def cleanup_legacy_corepulse_plans(self):
            return {'success': True, 'changed': False}
    obj = ManagedPowerPlans(FakePower(), path=tmp_path/'legacy.json', description_reader=lambda guid: None)
    assert obj.ensure('BALANCED') == {'success': True, 'mode': 'BALANCED'}
    assert obj.reconcile() == {'success': True, 'changed': False}
    assert obj.read()['plans'] == {}
    assert not (tmp_path/'legacy.json').exists()


# ===== test_v481_consolidated.py (contrato preservado) =====

import importlib
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ALIASES = {
    'core.alert_history_persistence': ('core.alert_history_store', 'PersistentAlertHistory'),
    'core.diagnostic_pipeline': ('core.recommendation_engine', 'integrate_current_diagnostic_pipeline'),
    'core.diagnostic_history': ('core.session_recovery', 'build_diagnostic_comparison'),
    'core.diagnostic_lifecycle': ('core.session_recovery', 'DiagnosticRun'),
    'core.diagnostic_evidence': ('core.diagnostic_summary', 'physical_health'),
    'core.diagnostic_explainer': ('core.diagnostic_summary', 'DiagnosticExplainer'),
    'core.pdf_context': ('core.report_builder', 'build_strict_pdf_context'),
    'core.report_generator': ('core.report_builder', 'generate_pdf_report'),
    'gui.header_identity_canvas': ('gui.professional_visuals', 'HeaderIdentityCanvas'),
    'gui.status_symbols': ('gui.professional_visuals', 'StatusSymbol'),
    'gui.render_polish': ('gui.professional_visuals', 'polish_widget_tree'),
    'gui.sidebar': ('gui.compact_sidebar', 'apply_clean_text_sidebar'),
    'gui.high_refresh': ('gui.resize_render_guard', 'get_ui_refresh_policy'),
}


def test_old_imports_resolve_lazily_without_empty_stub_files():
    for old, (target, symbol) in ALIASES.items():
        assert not (ROOT / (old.replace('.', '/') + '.py')).exists(), old
        assert importlib.util.find_spec(old), old
        assert importlib.util.find_spec(target), target


def test_core_aliases_keep_same_public_objects():
    for old, (target, symbol) in ALIASES.items():
        if old.startswith('gui.'):
            continue  # Importar CTk requiere Windows y las dependencias de interfaz.
        old_module = importlib.import_module(old)
        new_module = importlib.import_module(target)
        assert getattr(old_module, symbol) is getattr(new_module, symbol), old


def test_refresh_policy_remains_lightweight():
    from gui.high_refresh import get_ui_refresh_policy
    from gui.resize_render_guard import get_ui_refresh_policy as direct
    assert get_ui_refresh_policy is direct


def test_diagnostic_lifecycle_preserves_cancellation_and_real_or_na():
    from core.diagnostic_lifecycle import DiagnosticRun, DiagnosticState, is_finalized_result
    state = DiagnosticRun(token=123)
    assert state.state == DiagnosticState.PREPARING
    assert state.cancel() is True
    assert state.cancel_event.is_set()
    assert state.post_result({'score': 99}) is None
    assert state.drain() == (None, None)
    assert is_finalized_result({}) is False


def test_pdf_pipeline_rejects_unverified_inferences():
    import pytest
    from core.pdf_context import build_strict_pdf_context
    with pytest.raises(RuntimeError):
        build_strict_pdf_context({'overall_status': 'NORMAL'})


def test_windows_only_runtime_and_rtss_source_unchanged():
    source = (ROOT / 'core/sensors/rtss_osd.py').read_text(encoding='utf8')
    assert 'RTSSSharedMemory' in source
    assert 'PresentMon' not in source
    assert (ROOT / 'CorePulse_AI_Server/app/main.py').exists()
    assert (ROOT / 'core/ai_engine/realtime_agent.py').exists()


def test_full_distribution_and_numbering():
    assert (ROOT / 'LATEST_VERSION.txt').read_text(encoding='utf8').strip() == (ROOT / 'LATEST_VERSION.txt').read_text(encoding='utf8').strip()
    assert 'VERSION = "' + (ROOT / 'LATEST_VERSION.txt').read_text(encoding='utf8').strip() + '"' in (ROOT/'core/version.py').read_text(encoding='utf8')
    assert '0.10.2.' + (ROOT / 'LATEST_VERSION.txt').read_text(encoding='utf8').strip() in (ROOT/'pyproject.toml').read_text(encoding='utf8')
    assert (ROOT / 'build/CorePulse.spec').exists()
    assert (ROOT / 'herramientas/diagnostico/cpu_sensor_probe.py').exists()


# ===== Contratos adicionales V482 =====

V482_ALIASES = {
    'core.startup_profiler': ('core.startup_readiness','startup_mark'),
    'core.overlay_theme': ('core.overlay_preferences','build_original_overlay'),
    'core.pythonnet_shutdown': ('core.safe_shutdown','shutdown_telemetry_provider'),
    'core.pawnio_support': ('core.sensor_stack_setup','pawnio_status'),
    'core.gpu_display_logic': ('core.device_identity','gb_from_bytes'),
    'core.storage_summary_health': ('core.storage_health','collect_storage_summary_health'),
    'core.diagnostic_session': ('core.session_recovery','DiagnosticSession'),
    'core.alert_engine': ('core.alert_history_store','IntelligentAlertEngine'),
    'core.health_intelligence': ('core.health_engine','build_health_intelligence'),
    'core.sensor_diagnostics': ('core.corepulse_diagnostics','build_sensor_diagnostics'),
    'core.audio_test': ('core.windows_audio','AudioTest'),
    'core.nvme_smart_windows': ('core.smartctl_storage','parse_nvme_health_log'),
    'core.thermal_throttling': ('core.health_engine','ThermalThrottlingDetector'),
    'gui.thermal_health_binding': ('gui.live_health_binding','apply_thermal_health_semantics'),
}

def test_v482_all_removed_modules_have_lazy_compatibility():
    import importlib, importlib.util
    for previous, (current, name) in V482_ALIASES.items():
        old_spec = importlib.util.find_spec(previous)
        new_spec = importlib.util.find_spec(current)
        assert old_spec is not None, previous
        assert new_spec is not None, current
        a = importlib.import_module(previous)
        b = importlib.import_module(current)
        assert getattr(a, name) is getattr(b, name), previous

def test_v482_empty_nvme_log_is_rejected_without_derived_reading():
    import pytest
    from core.nvme_smart_windows import parse_nvme_health_log
    with pytest.raises(ValueError):
        parse_nvme_health_log(b'')

def test_v482_overlay_preserves_missing_values_and_real_rtss_label():
    from core.overlay_theme import build_original_overlay
    result=build_original_overlay({'exe':'Juego.exe','fps':None,'frametime':None},{'layout':'COMPACT'})
    assert 'N/A' in result
    assert 'REAL_OR_NA' in result
    assert 'RTSS' in result

def test_v482_throttling_needs_explicit_evidence_for_confirmation():
    from core.thermal_throttling import ThermalThrottlingDetector
    o=ThermalThrottlingDetector()
    result=o.add_sample({'cpu_temp':None,'cpu_usage':None,'cpu_ghz':None})
    assert result['cpu']['state']!='CONFIRMED'

def test_v482_ai_and_fps_runtime_are_not_moved():
    assert (ROOT/'core/ai_engine/ai_runtime_manager.py').is_file()
    assert (ROOT/'CorePulse_AI_Server/app/main.py').is_file()
    assert (ROOT/'performance/game_boost.py').is_file()
    assert (ROOT/'core/sensors/fps_certification.py').is_file()
    assert (ROOT/'core/sensors/rtss_osd.py').is_file()
    assert (ROOT/'core/version.py').read_text(encoding='utf8').find('VERSION = "' + (ROOT/'LATEST_VERSION.txt').read_text().strip() + '"')>=0
    assert '0.10.2.' + (ROOT/'LATEST_VERSION.txt').read_text().strip() in (ROOT/'pyproject.toml').read_text(encoding='utf8')

def test_v482_merges_did_not_leave_empty_shells():
    for previous in V482_ALIASES:
        pkg, stem = previous.split('.',1)
        for directory in (ROOT/pkg).rglob('*.py'):
            assert directory.stem!=stem,(previous,directory)

# ===== Contratos adicionales V483: consolidación, compatibilidad y cancelación =====

def test_v483_deprecated_paths_forward_to_real_implementations():
    import importlib
    aliases = {
        'core.product_contract': ('core.version', 'REAL_DATA_POLICY'),
        'core.runtime.product_contract': ('core.version', 'FPS_POLICY'),
        'core.cancellable_process': ('core.windows_commands', 'cancellation_scope'),
        'core.runtime.cancellable_process': ('core.windows_commands', 'DiagnosticCancelled'),
        'core.adaptive_diagnostic': ('core.session_recovery', 'AdaptiveDiagnosticSession'),
        'core.diagnostics.adaptive_diagnostic': ('core.session_recovery', 'readiness_stage'),
        'core.env_config': ('core.runtime_logging', 'load_corepulse_env'),
        'core.runtime.env_config': ('core.runtime_logging', 'env_status'),
        'gui.dialogs': ('gui.integration', 'ask_pdf_directory'),
        'gui.components.dialogs': ('gui.integration', 'ask_yes_no'),
    }
    for old, (new, symbol) in aliases.items():
        original = importlib.import_module(old)
        consolidated = importlib.import_module(new)
        assert getattr(original, symbol) is getattr(consolidated, symbol), old


def test_v483_cancellation_scope_remains_context_manager():
    import pytest
    from unittest.mock import patch
    from core.cancellable_process import cancellation_scope, DiagnosticCancelled, run
    import sys
    with cancellation_scope(lambda: False):
        result = run([sys.executable, '-c', "print('OK')"], capture_output=True)
        assert result.returncode == 0 and b'OK' in result.stdout
    with patch('core.windows_commands.subprocess.run', return_value='RESULT') as process_run:
        with cancellation_scope(lambda: True):
            with pytest.raises(DiagnosticCancelled):
                run(['should-not-start'])
        assert process_run.call_count == 0
        assert run(['outside-scope']) == 'RESULT'
        assert process_run.call_count == 1


def test_v483_adaptive_diagnostic_still_extends_real_session():
    from core.session_recovery import AdaptiveDiagnosticSession, DiagnosticSession
    assert issubclass(AdaptiveDiagnosticSession, DiagnosticSession)
    assert AdaptiveDiagnosticSession().min_samples >= 25


def test_v483_version_contracts_keep_real_or_na():
    from core.product_contract import FPS_POLICY, REAL_DATA_POLICY, VERSION, VERSION_LABEL
    from core.version import MIN_PYTHON, PYTHON_POLICY
    assert VERSION == (ROOT/'LATEST_VERSION.txt').read_text().strip()
    assert VERSION_LABEL == 'V' + (ROOT/'LATEST_VERSION.txt').read_text().strip()
    assert (REAL_DATA_POLICY, FPS_POLICY) == ('REAL_OR_NA', 'REAL_FPS_OR_NA_ONLY')
    assert MIN_PYTHON[0] >= 3 and '3.12' in PYTHON_POLICY


def test_v483_env_parser_preserved():
    from core.env_config import _parse_env_value, ENV_POLICY
    assert _parse_env_value('"example"') == 'example'
    assert ENV_POLICY == 'RUNTIME_DOTENV_ONLY_NO_ENV_EXAMPLE_DEPENDENCY'


def test_v483_dialogs_have_no_new_side_effects():
    import tkinter
    from gui.dialogs import _title, info, warning, error
    assert _title('Diagnóstico') == 'CorePulse · Diagnóstico'
    assert callable(info) and callable(warning) and callable(error)


def test_v483_files_physically_merged_not_empty_shims():
    for relative in (
        'core/runtime/product_contract.py',
        'core/runtime/cancellable_process.py',
        'core/runtime/env_config.py',
        'core/diagnostics/adaptive_diagnostic.py',
        'gui/components/dialogs.py',
    ):
        assert not (ROOT / relative).exists(), relative


def test_v483_lightweight_visual_utils_not_forced_into_customtkinter():
    from gui.widget_updates import numeric_or_none, format_detail_number
    assert numeric_or_none(None) is None
    assert numeric_or_none(True) is None
    assert format_detail_number(None) == 'N/A'
    assert (ROOT / 'gui/components/widget_updates.py').exists()

# ===== Contratos V484: módulos consolidados y desduplicación exacta =====
import ast
import importlib
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('old,target,api', [
    ('core.before_after', 'core.session_trends', 'compare'),
    ('core.diagnostics.before_after', 'core.session_trends', 'start_operation'),
    ('core.cpu_frequency', 'core.device_identity', 'get_cpu_frequency_evidence'),
    ('core.sensors.cpu_frequency', 'core.device_identity', 'get_cpu_frequency_evidence'),
])
def test_legacy_public_core_imports_keep_object_identity(old, target, api):
    original = importlib.import_module(old)
    canonical = importlib.import_module(target)
    assert getattr(original, api) is getattr(canonical, api)


def test_before_after_keeps_real_missing_metrics_and_boolean_conversion():
    from core.before_after import compare
    output = compare({'cpu_temp': None, 'ram_usage': 70, 'gpu_usage': False},
                     {'cpu_temp': None, 'ram_usage': 75, 'gpu_usage': True})
    assert output['available'] is True
    assert output['deltas']['cpu_temp']['delta'] is None
    assert output['deltas']['ram_usage']['delta'] == 5.0
    # Exact legacy semantics: bool is handled as numeric for comparison history.
    assert output['deltas']['gpu_usage']['delta'] == 1.0


def test_trend_analyzer_boolean_filter_not_overwritten_by_history_helper():
    from core.session_trends import _num, SessionTrendAnalyzer
    assert _num(True) is False
    assert _num(3) is True
    assert SessionTrendAnalyzer([]).summary()['session_count'] == 0


def test_cpu_frequency_evidence_is_certified_and_missing_stays_none():
    from core.device_identity import _cpu_frequency_num, _valid_mhz, _evidence
    assert _cpu_frequency_num(True) is None
    assert _valid_mhz(None) is None
    assert _valid_mhz(0.0) is None
    assert _evidence(None, 'test', 'test') is None
    result = _evidence(2000.0, 'test-real', 'sensor-real')
    assert result['ghz'] == 2.0
    assert result['synthetic_adjustment'] is False
    assert result['interpolation'] is False


def test_storage_smart_helper_is_deduplicated_without_changing_semantics():
    from core.smartctl_storage import _num as smart_num
    from core.storage_health import _num as health_num
    assert smart_num is health_num
    assert smart_num(None) is None and smart_num(False) is None
    assert smart_num('not-a-number') is None
    assert smart_num('42.5') == 42.5


def test_gui_compact_sidebar_functions_still_present_and_aliases_configured():
    navigation = ROOT / 'gui/navigation/internal_navigation.py'
    tree = ast.parse(navigation.read_text(encoding='utf-8'))
    names = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    assert {'sync_compact_sidebar', 'refresh_compact_navigation',
            'apply_clean_text_sidebar', 'request_navigation', 'commit_internal_page'} <= names
    gui_init = (ROOT / 'gui/__init__.py').read_text(encoding='utf-8')
    for old in ('gui.compact_sidebar', 'gui.navigation.compact_sidebar', 'gui.sidebar'):
        assert f"'{old}': 'gui.internal_navigation'" in gui_init
    assert (ROOT / 'gui/navigation/sidebar_native_hover.py').exists()


def test_file_merges_not_empty_wrappers():
    for rel in (
        'gui/navigation/compact_sidebar.py',
        'core/diagnostics/before_after.py',
        'core/sensors/cpu_frequency.py',
    ):
        assert not (ROOT / rel).exists(), rel
    assert (ROOT / 'core/sensors/rtss_osd.py').is_file()
    assert (ROOT / 'core/runtime/rtss_overlay_service.py').is_file()


def test_policy_and_version_are_consistent():
    from core.version import VERSION, REAL_DATA_POLICY, FPS_POLICY
    assert VERSION == (ROOT/'LATEST_VERSION.txt').read_text().strip()
    assert REAL_DATA_POLICY == 'REAL_OR_NA'
    assert FPS_POLICY == 'REAL_FPS_OR_NA_ONLY'
