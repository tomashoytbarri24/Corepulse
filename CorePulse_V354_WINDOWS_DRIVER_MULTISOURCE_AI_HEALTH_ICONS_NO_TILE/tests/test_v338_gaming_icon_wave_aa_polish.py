from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v338_version_and_stage():
    version = (ROOT / 'core' / 'version.py').read_text(encoding='utf-8')
    assert 'VERSION = "354"' in version
    assert 'GAMING_SQUARE_CARDS_PROFILE_ACCENTS' in version


def test_v338_waiting_visual_uses_4x_supersampling_and_native_controller_overlay():
    ui = (ROOT / 'gui' / 'health_center_panel.py').read_text(encoding='utf-8')
    start = ui.index('def _render_waiting_wave_image(width, height):')
    end = ui.index('def _draw_waiting_waves():', start)
    block = ui[start:end]
    assert 'scale = 4' in block
    assert 'samples=420' in block
    assert 'Image.Resampling.LANCZOS' in block
    assert "text='🎮'" not in block
    assert 'Image.Resampling.LANCZOS' in block
    assert 'V353' in block
    assert 'glyph nativo Segoe MDL2' in block


def test_v338_preserves_real_data_contract():
    root_text = '\n'.join([
        (ROOT / 'gui' / 'health_center_panel.py').read_text(encoding='utf-8'),
        (ROOT / 'core' / 'version.py').read_text(encoding='utf-8'),
    ])
    assert 'REAL_OR_NA' in (ROOT / 'README.md').read_text(encoding='utf-8') or 'REAL_OR_NA' in root_text
