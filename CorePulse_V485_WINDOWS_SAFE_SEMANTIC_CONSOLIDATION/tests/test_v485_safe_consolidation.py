"""V485: no regressions from startup and longitudinal history module merges."""
import ast
import importlib
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]

def test_v485_version_and_canonical_locations():
    from core.version import VERSION, FPS_POLICY, REAL_DATA_POLICY
    assert VERSION == '485'
    assert FPS_POLICY == 'REAL_FPS_OR_NA_ONLY'
    assert REAL_DATA_POLICY == 'REAL_OR_NA'
    assert not (ROOT / 'core/runtime/frozen_selftest.py').exists()
    assert not (ROOT / 'core/diagnostics/health_history.py').exists()


def test_v485_legacy_module_aliases():
    s = importlib.import_module('core.startup_readiness')
    h = importlib.import_module('core.session_trends')
    for old in ('core.frozen_selftest', 'core.runtime.frozen_selftest'):
        legacy = importlib.import_module(old)
        assert legacy.run_self_test is s.run_self_test
        assert legacy._is_admin is s._selftest_is_admin
        assert legacy._find_rtss is s._selftest_find_rtss
    for old in ('core.health_history', 'core.diagnostics.health_history'):
        legacy = importlib.import_module(old)
        assert legacy.HealthHistoryStore is h.HealthHistoryStore
        assert legacy._num is h._health_history_num


def test_v485_health_history_unknown_values_preserved():
    h = importlib.import_module('core.health_history')
    assert h._num(None) is None
    assert h._num('abc') is None
    assert h._num('8.25') == 8.25
    assert h._storage_health([{'health': None}, {'health': 91}]) == 91.0


def test_v485_critical_runtime_entrypoint_imports_from_new_locations():
    launcher = (ROOT / 'corepulse_launcher.py').read_text('utf8')
    main = (ROOT / 'main.py').read_text('utf8')
    assert 'from core.startup_readiness import run_self_test' in launcher
    assert 'from core.session_trends import HealthHistoryStore' in main
    assert 'from core.frozen_selftest import' not in launcher


def test_v485_historical_audits_are_preserved_in_single_archive():
    content = (ROOT/'docs/historico/AUDITORIAS_V480_V484.md').read_text('utf8')
    for version in range(480,485):
        assert f'V{version}' in content
    assert 'REAL_FPS_OR_NA_ONLY' in content


def test_v485_merged_code_parses():
    for name in ('core/runtime/startup_readiness.py','core/diagnostics/session_trends.py'):
        ast.parse((ROOT/name).read_text('utf8'))


def test_v485_health_history_sqlite_schema_still_created(tmp_path):
    import sqlite3
    from core.session_trends import HealthHistoryStore
    store = HealthHistoryStore(tmp_path / 'history.db')
    assert store.path.is_file()
    with sqlite3.connect(str(store.path)) as conn:
        tables = {item[0] for item in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {'health_samples', 'benchmark_runs', 'benchmark_sessions', 'stability_snapshots'} <= tables
