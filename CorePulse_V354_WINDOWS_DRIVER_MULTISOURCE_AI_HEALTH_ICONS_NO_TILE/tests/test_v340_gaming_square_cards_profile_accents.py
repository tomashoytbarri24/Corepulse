from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _home_block():
    ui = (ROOT / "gui" / "health_center_panel.py").read_text(encoding="utf-8")
    start = ui.index("def _render_gaming_comfort_home")
    end = ui.index("    def _render_game_boost_config_section", start)
    return ui[start:end]


def test_v340_version_and_stage():
    version = (ROOT / "core" / "version.py").read_text(encoding="utf-8")
    assert 'VERSION = "354"' in version
    assert 'GAMING_SQUARE_CARDS_PROFILE_ACCENTS' in version


def test_v340_game_and_resource_cards_are_square():
    block = _home_block()
    assert ("border_color=theme_color('#203b59'), corner_radius=0, height=current_game_h" in block or "border_color=theme_color('#203b59'), corner_radius=0, height=94" in block)
    assert ("border_color=theme_color('#1c3b56'), corner_radius=0, height=resource_row_h" in block or "border_color=theme_color('#1c3b56'), corner_radius=0, height=48" in block)


def test_v340_profiles_are_square_with_persistent_left_color_accent():
    block = _home_block()
    assert "profile_shell = ctk.CTkFrame(" in block
    assert "corner_radius=0," in block
    assert "profile_accent = ctk.CTkFrame(" in block
    assert "width=4, fg_color=accent, corner_radius=0" in block
    assert "border_color=accent if active else BORDER" in block
    assert "('BALANCED', 'Equilibrado', 'Uso diario y gaming estable', GREEN)" in block
    assert "('HIGH_PERFORMANCE', 'Rendimiento', 'Más respuesta durante el juego', CYAN)" in block
    assert "('MAXIMUM_PERFORMANCE', 'Máximo', 'Prioriza rendimiento disponible', PURPLE)" in block


def test_v340_preserves_real_metrics_contract():
    block = _home_block()
    assert "metric_progress(cpu_usage)" in block
    assert "metric_progress(gpu_usage)" in block
    assert "fps_text = f'{fps_value:.0f} FPS' if fps_value is not None and game_active else 'FPS N/A'" in block
