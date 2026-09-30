from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v347_profile_cards_close_after_content():
    src = (ROOT / 'gui' / 'health_center_panel.py').read_text(encoding='utf-8')
    assert '# PERFIL — V347:' in src
    assert 'profile_section_h = 112' in src
    assert 'profile_choice_h = 62' in src
    assert 'profile_section_h = 106' in src
    assert 'profile_choice_h = 56' in src
    assert "row.pack(fill='x', padx=10, pady=(0, 3))" in src
    assert "mhead.pack(fill='x', padx=14, pady=(7, 3))" in src


def test_v347_preserves_gaming_scale_and_contracts():
    version = (ROOT / 'core' / 'version.py').read_text(encoding='utf-8')
    assert 'VERSION = "354"' in version
    src = (ROOT / 'gui' / 'health_center_panel.py').read_text(encoding='utf-8')
    assert 'boost_visual_h = 410' in src
    for label in ('Equilibrado', 'Rendimiento', 'Máximo', 'Ahorro de energía'):
        assert label in src
    canonical = (ROOT / 'COREPULSE_CANONICAL_BASE.md').read_text(encoding='utf-8')
    assert 'REAL_OR_NA' in canonical
    assert 'REAL_FPS_OR_NA_ONLY' in canonical
