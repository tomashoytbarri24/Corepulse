from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v337_vector_controller_and_balanced_waiting_visual():
    version = (ROOT / 'core' / 'version.py').read_text(encoding='utf-8')
    ui = (ROOT / 'gui' / 'health_center_panel.py').read_text(encoding='utf-8')
    assert 'VERSION = "354"' in version
    assert 'WINDOWS_DRIVER_MULTISOURCE_AI_GAMING_SQUARE_CARDS_PROFILE_ACCENTS' in version
    assert "text='🎮'" not in ui[ui.index('# V335 — Game Boost alineado'):ui.index('    def _render_game_boost_config_section')]
    assert 'GAMEPAD_GLYPH' in ui
    assert "GAMEPAD_FONT = 'Segoe MDL2 Assets'" in ui
    assert "content.grid_rowconfigure(0, weight=0)" in ui


def test_v337_keeps_real_metrics_contract():
    ui = (ROOT / 'gui' / 'health_center_panel.py').read_text(encoding='utf-8')
    block = ui[ui.index('# V335 — Game Boost alineado'):ui.index('    def _render_game_boost_config_section')]
    assert "metric_progress(cpu_usage)" in block
    assert "metric_progress(gpu_usage)" in block
    assert "fps_text = f'{fps_value:.0f} FPS' if fps_value is not None and game_active else 'FPS N/A'" in block
