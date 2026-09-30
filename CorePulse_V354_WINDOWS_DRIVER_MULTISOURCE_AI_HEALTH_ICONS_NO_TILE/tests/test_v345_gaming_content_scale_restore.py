from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v345_version_and_adaptive_gaming_scale():
    version = (ROOT / 'core' / 'version.py').read_text(encoding='utf-8')
    assert 'VERSION = "354"' in version
    src = (ROOT / 'gui' / 'health_center_panel.py').read_text(encoding='utf-8')
    assert '# PERFIL — V347:' in src
    assert 'profile_section_h = 106' in src
    assert 'boost_visual_h = 410' in src
    assert 'current_game_h = 116' in src
    assert 'resource_row_h = 64' in src
    assert 'modes.configure(height=profile_section_h)' in src
    assert "height=boost_visual_h" in src


def test_v345_keeps_four_energy_profiles_and_real_data_contract():
    src = (ROOT / 'gui' / 'health_center_panel.py').read_text(encoding='utf-8')
    for label in ('Equilibrado', 'Rendimiento', 'Máximo', 'Ahorro de energía'):
        assert label in src
    main = (ROOT / 'main.py').read_text(encoding='utf-8')
    assert 'REAL_OR_NA' in main
