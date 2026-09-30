from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v353_version_keeps_v350_ai_fix_and_uses_clean_game_boost_icon():
    version = (ROOT / 'core' / 'version.py').read_text(encoding='utf-8')
    assert 'VERSION = "354"' in version
    assert 'LLAMA_HOST_DISCOVERY_FIX' in version
    assert 'GAMING_GAME_BOOST_CLEAN_ICON_FIX' in version


def test_game_boost_has_no_capsule_or_custom_heavy_vector():
    panel = (ROOT / 'gui' / 'health_center_panel.py').read_text(encoding='utf-8')
    assert 'button_w = max(94, min(126' not in panel
    assert 'health_button = Image.new' not in panel
    assert 'accent_x = button_left' not in panel
    assert "GAME_BOOST_ICON_CYAN = '#21c7ff'" in panel
    assert 'icon_cx = int(w * 0.5)' not in panel
    assert 'idraw.line(outline, fill=cyan' not in panel
    assert 'wave_canvas.create_text' in panel
    assert 'text=GAMEPAD_GLYPH' in panel


def test_v350_llama_host_discovery_is_preserved():
    locator = (ROOT / 'CorePulse_AI_Model_Host' / 'Localizar_Llama_Host.ps1').read_text(encoding='utf-8').lower()
    bat = (ROOT / 'Iniciar_Todo_CorePulse_AI.bat').read_text(encoding='utf-8').lower()
    assert 'llama.exe' in locator
    assert 'llama-server.exe' in locator
    assert 'winget install --id ggml.llamacpp -e' in bat
    assert 'cierra esta ventana y ejecuta nuevamente' not in bat


def test_real_data_contracts_remain_untouched():
    contract = (ROOT / 'core' / 'product_contract.py').read_text(encoding='utf-8')
    assert 'REAL_OR_NA' in contract
    assert 'REAL_FPS_OR_NA_ONLY' in contract
