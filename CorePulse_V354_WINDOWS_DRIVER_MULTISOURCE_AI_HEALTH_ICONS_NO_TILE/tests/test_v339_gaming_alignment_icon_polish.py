from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v339_version_and_stage():
    version = (ROOT / 'core' / 'version.py').read_text(encoding='utf-8')
    assert 'VERSION = "354"' in version
    assert 'GAMING_SQUARE_CARDS_PROFILE_ACCENTS' in version


def test_v339_uses_same_clean_gamepad_glyph_in_header_and_waiting_visual():
    gaming = (ROOT / 'gui' / 'gaming_panel.py').read_text(encoding='utf-8')
    health = (ROOT / 'gui' / 'health_center_panel.py').read_text(encoding='utf-8')
    assert 'GAMEPAD_GLYPH' in gaming
    assert "GAMEPAD_FONT = 'Segoe MDL2 Assets'" in gaming
    assert 'text=GAMEPAD_GLYPH' in gaming
    assert 'GAMEPAD_GLYPH' in health
    assert "GAMEPAD_FONT = 'Segoe MDL2 Assets'" in health
    assert 'wave_canvas.create_text(' in health
    assert 'text=GAMEPAD_GLYPH' in health
    assert 'fill=GAME_BOOST_ICON_CYAN' in health


def test_v339_compacts_profile_card_and_aligns_home_cards():
    ui = (ROOT / 'gui' / 'health_center_panel.py').read_text(encoding='utf-8')
    block = ui[ui.index('def _render_gaming_comfort_home'):ui.index('    def _render_game_boost_config_section')]
    assert ('modes.configure(height=profile_section_h)' in block or 'modes.configure(height=118)' in block or 'modes.configure(height=102)' in block)
    assert ("modes.pack(fill='x', padx=0, pady=(0, 8))" in block or "modes.pack(fill='x', padx=0, pady=(12, 8))" in block)
    assert 'modes.pack_propagate(False)' in block
    assert "boost_card.pack(fill='x', padx=0, pady=(0, 10))" in block


def test_v339_preserves_real_only_metrics():
    ui = (ROOT / 'gui' / 'health_center_panel.py').read_text(encoding='utf-8')
    block = ui[ui.index('# V335 — Game Boost alineado'):ui.index('    def _render_game_boost_config_section')]
    assert "fps_text = f'{fps_value:.0f} FPS' if fps_value is not None and game_active else 'FPS N/A'" in block
    assert 'metric_progress(cpu_usage)' in block
    assert 'metric_progress(gpu_usage)' in block
