import json
from pathlib import Path
import subprocess
import sys

import pytest
from core import runtime


def test_sensor_child_runs_without_bootstrapping_or_opening_ui():
    result = subprocess.run(runtime.child_command('cpu-probe'), capture_output=True,
                            text=True, encoding='utf-8', errors='replace', timeout=20)
    assert result.returncode == 0, result.stderr
    sample = json.loads(result.stdout.strip().splitlines()[-1])
    assert 'temp' in sample


def test_installed_worker_uses_sibling_exe_without_python_flags(monkeypatch):
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, 'executable', str(Path('C:/Programs/Core Pulse/CorePulse.exe')))
    command = runtime.child_command('benchmark-gpu', '--profile', 'quick')
    assert Path(command[0]).name == 'CorePulseWorker.exe'
    assert Path(command[0]).parent == Path(sys.executable).parent
    assert '-B' not in command and '-m' not in command


def test_worker_rejects_unknown_entrypoints():
    with pytest.raises(ValueError):
        runtime.child_command('arbitrary-code')
    assert runtime.dispatch_worker(['--corepulse-worker', 'unknown']) == 2


def test_elevated_request_cannot_write_to_arbitrary_result(tmp_path):
    request = tmp_path / ('a' * 32 + '.request.json')
    output = tmp_path / 'unrelated.json'
    request.write_text(json.dumps({'result_path': str(output), 'records': []}), encoding='utf-8')
    with pytest.raises(ValueError):
        runtime._tweak_request('tweak-apply', ['--request', str(request)])
    assert not output.exists()


def test_empty_elevated_job_completes_without_system_changes(tmp_path):
    request = tmp_path / ('b' * 32 + '.request.json')
    output = tmp_path / ('b' * 32 + '.result.json')
    request.write_text(json.dumps({'result_path': str(output), 'records': []}), encoding='utf-8')
    assert runtime._tweak_request('tweak-rollback', ['--request', str(request)]) == 0
    assert json.loads(output.read_text(encoding='utf-8')) == []


def test_admin_startup_continues_without_another_uac(monkeypatch):
    monkeypatch.setattr(runtime, 'is_administrator', lambda: True)
    monkeypatch.setattr(runtime, '_launch_as_administrator', lambda *args: pytest.fail('Unexpected UAC'))
    assert runtime.ensure_administrator() is None


def test_default_startup_never_requests_uac(monkeypatch):
    monkeypatch.setattr(runtime, 'is_administrator', lambda: False)
    monkeypatch.setattr(runtime, 'always_administrator', lambda: False)
    monkeypatch.setattr(sys, 'argv', ['main.py'])
    monkeypatch.setattr(runtime, '_launch_as_administrator', lambda *args: pytest.fail('Unexpected UAC'))
    assert runtime.ensure_administrator() is None


@pytest.mark.parametrize('frozen', [False, True])
def test_chosen_admin_relaunch_preserves_quoted_arguments_and_exits_parent(monkeypatch, frozen):
    monkeypatch.setattr(runtime, 'is_administrator', lambda: False)
    monkeypatch.setattr(runtime, 'always_administrator', lambda: True)
    monkeypatch.setattr(sys, 'frozen', frozen, raising=False)
    monkeypatch.setattr(sys, 'argv', ['main.py', '--smoke-test', 'C:/Reporte con espacios/lectura á.json'])
    calls = []
    monkeypatch.setattr(runtime, '_launch_as_administrator', lambda *args: calls.append(args) or 0)
    assert runtime.ensure_administrator() == 0
    assert len(calls) == 1
    executable, parameters, directory = calls[0]
    assert executable == sys.executable and directory == str(runtime.ROOT)
    assert '"C:/Reporte con espacios/lectura á.json"' in parameters
    assert parameters.endswith('--corepulse-elevated')
    assert ('main.py' in parameters) is (not frozen)


def test_uac_cancellation_still_opens_without_administrator(monkeypatch, capsys):
    monkeypatch.setattr(runtime, 'is_administrator', lambda: False)
    monkeypatch.setattr(runtime, 'always_administrator', lambda: True)
    monkeypatch.setattr(sys, 'argv', ['main.py'])
    monkeypatch.setattr(runtime, '_launch_as_administrator', lambda *args: 1223)
    assert runtime.ensure_administrator() is None
    assert 'sin administrador' in capsys.readouterr().err


def test_admin_relaunch_cannot_loop_if_windows_refuses_the_token(monkeypatch):
    monkeypatch.setattr(runtime, 'is_administrator', lambda: False)
    monkeypatch.setattr(runtime, 'always_administrator', lambda: True)
    monkeypatch.setattr(sys, 'argv', ['main.py', '--corepulse-elevated'])
    monkeypatch.setattr(runtime, '_launch_as_administrator', lambda *args: pytest.fail('UAC loop'))
    assert runtime.ensure_administrator() is None
    assert '--corepulse-elevated' not in sys.argv


def test_packaged_app_does_not_demand_administrator():
    spec = (runtime.ROOT / 'installer' / 'CorePulse.spec').read_text(encoding='utf-8')
    setup = (runtime.ROOT / 'installer' / 'CorePulse.iss').read_text(encoding='utf-8')
    assert 'uac_admin=True' not in spec
    assert 'runas' not in setup


def test_damaged_database_moves_with_wal_and_keeps_its_bytes(tmp_path):
    database = tmp_path / 'datos.sqlite3'
    database.write_bytes(b'danada')
    (tmp_path / 'datos.sqlite3-wal').write_bytes(b'wal')
    moved = runtime.quarantine_database(database)
    assert not database.exists() and moved.read_bytes() == b'danada'
    assert '.danada-' in moved.name
    assert (tmp_path / (moved.name + '-wal')).read_bytes() == b'wal'


def test_admin_marker_is_removed_before_qt_and_smoke_argument_parsing(monkeypatch):
    monkeypatch.setattr(runtime, 'is_administrator', lambda: True)
    monkeypatch.setattr(sys, 'argv', ['main.py', '--smoke-test', 'out.json', '--corepulse-elevated'])
    assert runtime.ensure_administrator() is None
    assert sys.argv == ['main.py', '--smoke-test', 'out.json']
