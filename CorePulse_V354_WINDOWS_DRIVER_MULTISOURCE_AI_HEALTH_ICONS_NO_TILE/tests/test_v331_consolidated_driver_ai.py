from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v331_contains_multisource_driver_hub_and_ai_chat():
    version = (ROOT / 'core' / 'version.py').read_text(encoding='utf-8')
    drivers = (ROOT / 'core' / 'driver_updates.py').read_text(encoding='utf-8')
    health_ui = (ROOT / 'gui' / 'health_center_panel.py').read_text(encoding='utf-8')
    dashboard = (ROOT / 'gui' / 'dashboard.py').read_text(encoding='utf-8')
    ai_panel = (ROOT / 'gui' / 'ai_panel.py').read_text(encoding='utf-8')
    assert 'VERSION = "354"' in version
    assert 'INTEL_BLUETOOTH_PAGE' in drivers
    assert '_vendor_update_for_device' in drivers
    assert 'DRIVER HUB 3.0' in health_ui
    assert 'Buscar seleccionados' in health_ui
    assert 'CorePulse AI' in dashboard
    assert 'Analizar ahora' in ai_panel or 'Enviar' in ai_panel


def test_v331_one_click_ai_and_real_data_contracts_remain():
    assert (ROOT / 'Iniciar_Todo_CorePulse_AI.bat').exists()
    assert (ROOT / 'CorePulse_AI_Server').is_dir()
    assert (ROOT / 'CorePulse_AI_Model_Host').is_dir()
    canonical = (ROOT / 'COREPULSE_CANONICAL_BASE.md').read_text(encoding='utf-8')
    assert 'REAL_OR_NA' in canonical
    assert 'REAL_FPS_OR_NA_ONLY' in canonical


def test_v331_client_has_no_direct_openai_or_groq_sdk_dependency():
    req = (ROOT / 'requirements-base.txt').read_text(encoding='utf-8').lower()
    spec = (ROOT / 'build' / 'CorePulse.spec').read_text(encoding='utf-8').lower()
    assert '\nopenai' not in '\n' + req
    assert '\ngroq' not in '\n' + req
    assert '"openai"' not in spec
    assert '"groq"' not in spec
