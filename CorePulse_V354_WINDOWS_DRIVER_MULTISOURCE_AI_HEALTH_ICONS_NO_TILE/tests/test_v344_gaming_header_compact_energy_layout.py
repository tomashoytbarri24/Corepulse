from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v344_version_stage():
    version = (ROOT / 'core' / 'version.py').read_text(encoding='utf-8')
    assert 'VERSION = "354"' in version
    assert 'GAMING_HEADER_COMPACT_ENERGY_LAYOUT' in version


def test_v344_header_removes_loose_left_accent_and_moves_up():
    src = (ROOT / 'gui' / 'gaming_panel.py').read_text(encoding='utf-8')
    start = src.index('# V344 — cabecera compacta')
    end = src.index('# V344 — navegación compacta', start)
    block = src[start:end]
    assert "header_card" in block
    assert ('height=58' in block or 'height=64' in block)
    assert "accent = ctk.CTkFrame(header_card" not in block
    assert "pady=(4, 3)" in src
    assert ("pady=(0, 5)" in src or "pady=(0, 4)" in src)


def test_v344_energy_profiles_are_four_equal_visible_cards():
    src = (ROOT / 'gui' / 'health_center_panel.py').read_text(encoding='utf-8')
    start = src.index('# PERFIL — V344')
    end = src.index('# V335 — Game Boost alineado', start)
    block = src[start:end]
    assert "('POWER_SAVER', 'Ahorro de energía'" in block
    assert "uniform='gaming_profile_choices'" in block
    assert 'len(profile_specs) - 1' in block
    assert "fg_color=accent" in block
    assert "border_color=accent if active else BORDER" in block
    assert "corner_radius=0" in block


def test_v344_preserves_real_data_contracts():
    canonical = (ROOT / 'COREPULSE_CANONICAL_BASE.md').read_text(encoding='utf-8')
    assert 'REAL_OR_NA' in canonical
    assert 'REAL_FPS_OR_NA_ONLY' in canonical
