from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v354_version_and_stage():
    version = (ROOT / 'core' / 'version.py').read_text(encoding='utf-8')
    assert 'VERSION = "354"' in version
    assert 'HEALTH_ICONS_NO_TILE' in version


def test_health_center_module_icons_have_no_background_tile():
    panel = (ROOT / 'gui' / 'health_center_panel.py').read_text(encoding='utf-8')
    start = panel.index('def _health_module_card')
    end = panel.index('    def ', start + 10)
    block = panel[start:end]
    assert "fg_color='transparent'" in block
    assert 'corner_radius=0' in block
    assert "text_color=accent_color" in block
    assert "icon_bg = profile.get('bg')" not in block


def test_real_data_contracts_are_preserved():
    contract = (ROOT / 'core' / 'product_contract.py').read_text(encoding='utf-8')
    assert 'REAL_OR_NA' in contract
    assert 'REAL_FPS_OR_NA_ONLY' in contract
