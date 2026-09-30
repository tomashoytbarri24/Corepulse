from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v353_version_and_stage():
    version = (ROOT / 'core' / 'version.py').read_text(encoding='utf-8')
    assert 'VERSION = "354"' in version
    assert 'GAMING_GAME_BOOST_CLEAN_ICON_FIX' in version


def test_v353_clean_icon_contract():
    panel = (ROOT / 'gui' / 'health_center_panel.py').read_text(encoding='utf-8')
    assert "GAME_BOOST_ICON_CYAN = '#21c7ff'" in panel
    assert 'wave_canvas.create_text(' in panel
    assert 'text=GAMEPAD_GLYPH' in panel
    assert 'fill=GAME_BOOST_ICON_CYAN' in panel
    assert 'button_w = max(94, min(126' not in panel
    assert 'health_button = Image.new' not in panel
    assert 'idraw.line(outline, fill=cyan' not in panel


def test_v353_preserves_ai_and_real_data_contracts():
    locator = (ROOT / 'CorePulse_AI_Model_Host' / 'Localizar_Llama_Host.ps1').read_text(encoding='utf-8').lower()
    contract = (ROOT / 'core' / 'product_contract.py').read_text(encoding='utf-8')
    assert 'llama.exe' in locator and 'llama-server.exe' in locator
    assert 'REAL_OR_NA' in contract
    assert 'REAL_FPS_OR_NA_ONLY' in contract
