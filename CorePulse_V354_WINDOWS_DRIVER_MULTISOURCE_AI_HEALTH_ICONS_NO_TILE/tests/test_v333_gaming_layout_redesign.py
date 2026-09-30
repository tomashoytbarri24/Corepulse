from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v335_gaming_layout_keeps_large_left_visual_and_right_status_stack():
    version = (ROOT / 'core' / 'version.py').read_text(encoding='utf-8')
    ui = (ROOT / 'gui' / 'health_center_panel.py').read_text(encoding='utf-8')
    assert 'VERSION = "354"' in version
    assert "visual_shell = ctk.CTkFrame" in ui
    assert "right_side = ctk.CTkFrame" in ui
    assert "current_game_box = ctk.CTkFrame" in ui
    assert "row_card = ctk.CTkFrame" in ui
    assert "CTkProgressBar" in ui
    assert "size=(art_w, art_h)" in ui


def test_v335_keeps_real_fps_and_real_telemetry_contracts():
    ui = (ROOT / 'gui' / 'health_center_panel.py').read_text(encoding='utf-8')
    canonical = (ROOT / 'COREPULSE_CANONICAL_BASE.md').read_text(encoding='utf-8')
    assert "fps_text = f'{fps_value:.0f} FPS' if fps_value is not None and game_active else 'FPS N/A'" in ui
    assert 'REAL_OR_NA' in canonical
    assert 'REAL_FPS_OR_NA_ONLY' in canonical
