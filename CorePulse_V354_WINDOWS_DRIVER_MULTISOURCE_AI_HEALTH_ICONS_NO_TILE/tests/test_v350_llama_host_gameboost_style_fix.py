from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v350_lineage_is_preserved_inside_v352():
    version = (ROOT / 'core' / 'version.py').read_text(encoding='utf-8')
    assert 'VERSION = "354"' in version
    assert 'LLAMA_HOST_DISCOVERY_FIX' in version


def test_llama_locator_supports_both_windows_distributions():
    locator = (ROOT / 'CorePulse_AI_Model_Host' / 'Localizar_Llama_Host.ps1').read_text(encoding='utf-8')
    low = locator.lower()
    assert 'llama.exe' in low
    assert 'llama-server.exe' in low
    assert 'microsoft\winget\links' in low
    assert 'microsoft\winget\packages' in low


def test_one_click_uses_real_winget_id_and_does_not_require_terminal_restart():
    bat = (ROOT / 'Iniciar_Todo_CorePulse_AI.bat').read_text(encoding='utf-8')
    low = bat.lower()
    assert 'winget install --id ggml.llamacpp -e' in low
    assert 'localizar_llama_host.ps1' in low
    assert 'llama_kind=unified' in low
    assert 'llama_kind=server' in low
    assert 'cierra esta ventana y ejecuta nuevamente' not in low


def test_model_launcher_supports_unified_frontend_and_llama_server_binary():
    bat = (ROOT / 'CorePulse_AI_Model_Host' / 'Iniciar_Modelo_CorePulse_AI.bat').read_text(encoding='utf-8')
    low = bat.lower()
    assert '"%llamaexe%" serve -hf %model_name% --port 8766' in low
    assert '"%llamaexe%" -hf %model_name% --port 8766' in low


def test_game_boost_now_uses_icon_only_reference_without_capsule():
    panel = (ROOT / 'gui' / 'health_center_panel.py').read_text(encoding='utf-8')
    assert "GAME_BOOST_ICON_CYAN = '#21c7ff'" in panel
    assert 'button_radius' not in panel
    assert 'fill=(22, 79, 125, 246)' not in panel


def test_real_data_contracts_remain():
    contract = (ROOT / 'core' / 'product_contract.py').read_text(encoding='utf-8')
    assert 'REAL_OR_NA' in contract
    assert 'REAL_FPS_OR_NA_ONLY' in contract
