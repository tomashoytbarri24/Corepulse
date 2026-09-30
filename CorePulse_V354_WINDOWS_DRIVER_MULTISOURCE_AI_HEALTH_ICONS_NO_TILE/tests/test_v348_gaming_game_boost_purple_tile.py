from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v348_lineage_is_absorbed_by_v353():
    version = (ROOT / 'core' / 'version.py').read_text(encoding='utf-8')
    assert 'VERSION = "354"' in version
    assert 'GAMING_GAME_BOOST_CLEAN_ICON_FIX' in version


def test_v353_keeps_background_and_changes_only_the_icon_model():
    ui = (ROOT / 'gui' / 'health_center_panel.py').read_text(encoding='utf-8')
    assert 'GAME_BOOST_ICON_CYAN' in ui
    assert 'health_button = Image.new' not in ui
    assert 'button_w = max(94, min(126' not in ui
    assert 'wave_canvas.create_text' in ui
    assert 'text=GAMEPAD_GLYPH' in ui
    assert 'Image.Resampling.LANCZOS' in ui


def test_v348_preserves_real_data_contracts():
    contract = (ROOT / 'core' / 'product_contract.py').read_text(encoding='utf-8')
    assert 'REAL_OR_NA' in contract
    assert 'REAL_FPS_OR_NA_ONLY' in contract
