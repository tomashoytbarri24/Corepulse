from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v335_version_stage_and_final_gaming_reference():
    version = (ROOT / 'core' / 'version.py').read_text(encoding='utf-8')
    ui = (ROOT / 'gui' / 'health_center_panel.py').read_text(encoding='utf-8')
    assert 'VERSION = "354"' in version
    assert 'WINDOWS_DRIVER_MULTISOURCE_AI_GAMING_SQUARE_CARDS_PROFILE_ACCENTS' in version
    marker = '# V335 — Game Boost alineado con la referencia final aprobada'
    assert marker in ui


def test_v335_right_column_order_is_current_game_then_resources():
    ui = (ROOT / 'gui' / 'health_center_panel.py').read_text(encoding='utf-8')
    start = ui.index('# V335 — Game Boost alineado con la referencia final aprobada')
    end = ui.index('    def _render_game_boost_config_section', start)
    block = ui[start:end]
    game = block.index('current_game_box = ctk.CTkFrame')
    resources = block.index("text='RECURSOS'")
    rows = block.index('for label, value, color, progress_value, icon in resource_specs')
    assert game < resources < rows


def test_v335_progress_values_come_only_from_real_usage_or_na():
    ui = (ROOT / 'gui' / 'health_center_panel.py').read_text(encoding='utf-8')
    start = ui.index('# V335 — Game Boost alineado con la referencia final aprobada')
    end = ui.index('    def _render_game_boost_config_section', start)
    block = ui[start:end]
    assert "metric_progress(cpu_usage)" in block
    assert "metric_progress(gpu_usage)" in block
    assert "ram_progress = metric_progress(ram_usage)" in block
    assert "bar.set(progress_value if value != 'N/A' else 0.0)" in block
