from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v352_lineage_is_superseded_by_v353_clean_icon():
    version = (ROOT / 'core' / 'version.py').read_text(encoding='utf-8')
    assert 'VERSION = "354"' in version
    assert 'GAMING_GAME_BOOST_CLEAN_ICON_FIX' in version


def test_game_boost_icon_is_native_clean_and_centered_without_extra_model():
    panel = (ROOT / 'gui' / 'health_center_panel.py').read_text(encoding='utf-8')
    assert 'wave_canvas.create_text' in panel
    assert 'width * 0.5, height * 0.42' in panel
    assert 'text=GAMEPAD_GLYPH, fill=GAME_BOOST_ICON_CYAN' in panel
    assert "font=(GAMEPAD_FONT, glyph_size)" in panel
    assert 'health_button = Image.new' not in panel
    assert 'idraw.line(outline, fill=cyan' not in panel
