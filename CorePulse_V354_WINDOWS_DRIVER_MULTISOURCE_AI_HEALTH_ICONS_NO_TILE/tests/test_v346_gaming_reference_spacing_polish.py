from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v346_spacing_polish_removes_profile_dead_strip():
    src = (ROOT / 'gui' / 'health_center_panel.py').read_text(encoding='utf-8')
    assert '# PERFIL — V347:' in src
    assert "modes.pack(fill='x', padx=0, pady=(12, 8))" in src
    assert "text='El plan seleccionado queda activo en Windows hasta que tú lo cambies.'" not in src
    assert 'profile_choice_h = 62' in src
    assert 'profile_choice_h = 56' in src


def test_v346_gaming_header_and_contracts_are_preserved():
    version = (ROOT / 'core' / 'version.py').read_text(encoding='utf-8')
    assert 'VERSION = "354"' in version
    panel = (ROOT / 'gui' / 'gaming_panel.py').read_text(encoding='utf-8')
    assert "titles, text='Gaming', font=(FONT, 25, 'bold')" in panel
    assert 'corner_radius=0, height=64' in panel
    contract = (ROOT / 'COREPULSE_CANONICAL_BASE.md').read_text(encoding='utf-8')
    assert 'REAL_OR_NA' in contract
    assert 'REAL_FPS_OR_NA_ONLY' in contract
