from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v343_version_stage():
    version = (ROOT / "core" / "version.py").read_text(encoding="utf-8")
    assert 'VERSION = "354"' in version
    assert 'GAMING_PROFILE_NAV_FIX' in version


def test_v343_gaming_header_has_no_outer_card_border():
    src = (ROOT / "gui" / "gaming_panel.py").read_text(encoding="utf-8")
    marker = '# V344 — cabecera compacta' if '# V344 — cabecera compacta' in src else '# V343 — la cabecera'
    block = src[src.index(marker):src.index('nav = ctk.CTkFrame', src.index(marker))]
    assert "header, fg_color='transparent', border_width=0" in block
    assert "text='CENTRO DE RENDIMIENTO'" in src
    assert "text='Gaming'" in src
    assert "GAMEPAD_GLYPH" in src


def test_v343_top_navigation_is_responsive_and_full_width():
    src = (ROOT / "gui" / "gaming_panel.py").read_text(encoding="utf-8")
    assert "nav_inner.pack(fill='x')" in src
    assert "uniform='gaming_top_nav'" in src
    assert "btn.grid(" in src
    assert ('height=34' in src or 'height=32' in src)


def test_v343_profiles_keep_visible_text_and_power_saver():
    src = (ROOT / "gui" / "health_center_panel.py").read_text(encoding="utf-8")
    marker = '# PERFIL — V344' if '# PERFIL — V344' in src else '# PERFIL — V343'
    start = src.index(marker)
    end = src.index("# V335 — Game Boost alineado", start)
    block = src[start:end]
    assert "profile_text = ctk.CTkFrame" in block
    assert "text=('✓ ' if active else '') + label" in block
    assert "text=detail" in block
    assert "'Ahorro de energía'" in block
    assert "('POWER_SAVER', 'Ahorro de energía'" in block
    assert 'AMBER' in block
    assert "corner_radius=0" in block


def test_v343_preserves_real_data_contracts():
    canonical = (ROOT / "COREPULSE_CANONICAL_BASE.md").read_text(encoding="utf-8")
    assert "REAL_OR_NA" in canonical
    assert "REAL_FPS_OR_NA_ONLY" in canonical
