"""Regresiones agrupadas V482: test_structure_fps_contracts.py. Contratos originales completos."""
from __future__ import annotations


# ===== test_v477_clean_structure.py (contrato preservado) =====
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_clean_root_and_runtime():
    assert int((ROOT/'LATEST_VERSION.txt').read_text().strip()) >= 477
    assert not (ROOT/'.corepulse_runtime_python.txt').exists()
    assert not (ROOT/'.corepulse_runtime_validation.json').exists()
    assert (ROOT/'Iniciar_CorePulse.bat').is_file()
    assert (ROOT/'core/telemetry.py').is_file()
    assert (ROOT/'gui/ai_panel.py').is_file()

def test_all_ai_scripts_resolve_root():
    scripts=sorted((ROOT/'herramientas'/'ia').glob('*.bat'))
    assert len(scripts)==19
    for f in scripts:
        t=f.read_text(encoding='utf-8')
        assert '%~dp0..\\..' in t
    assert not list(ROOT.glob('[0-2][0-9]_*.bat'))

def test_history_preserved_and_current_docs():
    for name in ('GUIAS_HISTORICAS.md','VALIDACIONES_HISTORICAS.md','PRUEBAS_HISTORICAS.md'):
        assert (ROOT/'docs/historico'/name).is_file()
    assert (ROOT/'docs/GUIA_IA_ACTUAL_V476.md').is_file()
    assert (ROOT/'build/CorePulse.spec').is_file()
    assert not (ROOT/'tools/presentmon/PresentMon.exe').exists()

def test_gui_launch_targets_relocated():
    text=(ROOT/'gui/ai_panel.py').read_text(encoding='utf-8')
    assert "root / 'herramientas' / 'ia' / '11_INICIAR_PUENTE_GROQ_V463.bat'" in text
    assert "script = root / 'herramientas' / 'ia' / (name or '')" in text


# ===== test_v478_modular_structure.py (contrato preservado) =====
import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_core_gui_grouped_and_importable():
    for pkg, maximum in (('core',16),('gui',17)):
        directory=ROOT/pkg
        modules=list(directory.glob('*.py'))
        assert len(modules)<=maximum, (pkg,len(modules))
        source_map={}
        for group in directory.iterdir():
            if not group.is_dir():
                continue
            for file in group.glob('*.py'):
                assert file.stem not in source_map, (pkg,file.stem)
                source_map[file.stem]=file
                spec=importlib.util.find_spec(f'{pkg}.{file.stem}')
                assert spec is not None and Path(spec.origin).resolve()==file.resolve(), (pkg,file.name,spec)
        assert len(source_map)>=20, (pkg,len(source_map))

def test_critical_legacy_paths_still_exist():
    for path in ('core/telemetry.py', 'core/runtime_paths.py', 'core/python_compat.py',
                 'core/version.py','core/ai_quick_connect.py','gui/ai_panel.py',
                 'gui/dashboard.py','gui/dashboard_layout.py', 'gui/chart_workspace_surface.py'):
        assert (ROOT/path).is_file(),path

def test_consent_and_cloud_modules_still_available():
    for name in ('core.ai_client','core.ai_user_control','core.ai_report_engine',
                 'core.ai_investigation_history','gui.ai_panel','gui.ai_status_card'):
        assert importlib.util.find_spec(name) is not None,name


# ===== test_v479_rtss_only.py (contrato preservado) =====
from pathlib import Path
import ast
import sys
import types

ROOT=Path(__file__).resolve().parents[1]

def test_no_legacy_binary_or_capture_modules():
    for rel in ('tools/presentmon/PresentMon.exe','core/sensors/presentmon_fps.py','core/sensors/presentmon_same_pid.py'):
        assert not (ROOT/rel).exists(),rel
    for rel in ('core/sensors/fps_certification.py','core/runtime/startup_readiness.py','build_exe.bat'):
        assert 'presentmon' not in (ROOT/rel).read_text(encoding='utf-8').lower(),rel

def test_no_direct_launch_or_import_anywhere_in_runtime():
    for base in ('core','gui','performance'):
        for f in (ROOT/base).rglob('*.py'):
            assert 'presentmon' not in f.read_text(encoding='utf-8').lower(),f

def test_version_and_syntax():
    assert int((ROOT/'LATEST_VERSION.txt').read_text().strip())>=479
    for base in ('core','gui','performance'):
        for f in (ROOT/base).rglob('*.py'):
            ast.parse(f.read_text(encoding='utf-8'),str(f))

def test_rtss_measurements_are_not_guessed(monkeypatch):
    # winreg existe sólo en Windows; stub de importación para analizar la política en CI Linux.
    if sys.platform!='win32':
        monkeypatch.setitem(sys.modules,'winreg',types.ModuleType('winreg'))
    import core.fps_certification as fp
    provider=object.__new__(fp.CertifiedFPSProvider)
    provider._lock=__import__('threading').RLock()
    provider.rtss=types.SimpleNamespace(available=False)
    valid={'quality':'VALID','fps_1s':120,'fps':125,'frametime_ms':8.0,'fps_1pct_low':75,'pid':400,'name':'Game.exe','age_ms':100}
    r=provider.get_snapshot(valid)
    assert r['fps']==120 and r['fps_instant']==125 and r['fps_1pct_low']==75
    assert r['source']=='RTSS Shared Memory' and r['quality']=='VALID_RTSS'
    assert r['crosscheck'] is None and r['source_crosscheck'] is None
    for patch in ({'quality':'UNAVAILABLE'},{'age_ms':3000},{'fps_1s':None,'fps':None},{'fps_1s':float('nan'),'fps':-1}):
        assert provider.get_snapshot(valid | patch)['fps'] is None
    assert provider.get_snapshot(None)['fps'] is None
