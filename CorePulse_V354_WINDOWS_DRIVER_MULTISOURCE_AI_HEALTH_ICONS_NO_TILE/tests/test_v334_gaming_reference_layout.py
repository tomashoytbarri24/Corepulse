from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v335_final_reference_supersedes_horizontal_resource_cards():
    ui = (ROOT / 'gui' / 'health_center_panel.py').read_text(encoding='utf-8')
    start = ui.index('# V335 — Game Boost alineado con la referencia final aprobada')
    end = ui.index('    def _render_game_boost_config_section', start)
    block = ui[start:end]
    assert "content.grid_columnconfigure(0, weight=6" in block
    assert "content.grid_columnconfigure(1, weight=5" in block
    assert "right_side = ctk.CTkFrame" in block
    assert "current_game_box = ctk.CTkFrame" in block
    assert "text='JUEGO ACTUAL'" in block
    assert "text='FPS'" in block
    assert "text='RECURSOS'" in block
    assert "for label, value, color, progress_value, icon in resource_specs" in block
    assert 'CTkProgressBar' in block
    assert 'right_panel = ctk.CTkFrame' not in block
    assert "for col in range(3)" not in block


def test_v335_waiting_visual_has_code_drawn_blue_cyan_waves_without_inner_border():
    ui = (ROOT / 'gui' / 'health_center_panel.py').read_text(encoding='utf-8')
    start = ui.index('# V335 — Game Boost alineado con la referencia final aprobada')
    end = ui.index('    def _render_game_boost_config_section', start)
    block = ui[start:end]
    assert "border_width=0" in block
    assert "wave_canvas = tk.Canvas" in block
    assert "Image.Resampling.LANCZOS" in block
    assert "ImageFilter.GaussianBlur" in block
    assert "rd.polygon" in block
    assert "td.line" in block
    assert "(16, 193, 255, 246)" in block
    assert "(23, 113, 255, 226)" in block


def test_v335_reference_layout_keeps_real_only_contracts():
    ui = (ROOT / 'gui' / 'health_center_panel.py').read_text(encoding='utf-8')
    canonical = (ROOT / 'COREPULSE_CANONICAL_BASE.md').read_text(encoding='utf-8')
    assert "fps_text = f'{fps_value:.0f} FPS' if fps_value is not None and game_active else 'FPS N/A'" in ui
    assert 'REAL_OR_NA' in canonical
    assert 'REAL_FPS_OR_NA_ONLY' in canonical
