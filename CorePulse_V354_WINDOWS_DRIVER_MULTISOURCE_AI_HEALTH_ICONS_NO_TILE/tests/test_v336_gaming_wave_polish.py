from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v336_uses_antialiased_procedural_waiting_background():
    version = (ROOT / 'core' / 'version.py').read_text(encoding='utf-8')
    ui = (ROOT / 'gui' / 'health_center_panel.py').read_text(encoding='utf-8')
    assert 'VERSION = "354"' in version
    assert 'WINDOWS_DRIVER_MULTISOURCE_AI_GAMING_SQUARE_CARDS_PROFILE_ACCENTS' in version
    assert "scale = 4" in ui
    assert "Image.Resampling.LANCZOS" in ui
    assert "ImageFilter.GaussianBlur" in ui
    assert "wave_state = {'after': None, 'photo': None}" in ui
    assert "GAMEPAD_FONT = 'Segoe MDL2 Assets'" in ui
    assert "wave_canvas.create_text(" in ui
    assert 'text=GAMEPAD_GLYPH' in ui
    assert 'fill=GAME_BOOST_ICON_CYAN' in ui


def test_v336_preserves_real_only_metrics_and_no_inner_art_border():
    ui = (ROOT / 'gui' / 'health_center_panel.py').read_text(encoding='utf-8')
    start = ui.index('# V335 — Game Boost alineado con la referencia final aprobada')
    end = ui.index('    def _render_game_boost_config_section', start)
    block = ui[start:end]
    assert "border_width=0" in block
    assert "metric_progress(cpu_usage)" in block
    assert "metric_progress(gpu_usage)" in block
    assert "fps_text = f'{fps_value:.0f} FPS' if fps_value is not None and game_active else 'FPS N/A'" in block
