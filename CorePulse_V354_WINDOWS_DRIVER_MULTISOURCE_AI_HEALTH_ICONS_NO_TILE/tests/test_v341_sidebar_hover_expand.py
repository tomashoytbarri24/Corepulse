from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / "gui" / "dashboard.py").read_text(encoding="utf-8")


def test_hover_expand_installed_after_sidebar_rebuild():
    assert "def _install_sidebar_hover_expand(app):" in SRC
    assert "_install_sidebar_hover_expand(app)" in SRC


def test_hover_expand_is_horizontal_and_non_reflowing():
    block = SRC[SRC.index("def _install_sidebar_hover_expand(app):"):SRC.index("def _status_color(score):")]
    assert "pack_configure(padx=value)" in block
    assert "height=" not in block
    assert "steps = 5" in block
    assert "button.after(12, tick)" in block


def test_hover_expand_respects_collapsed_sidebar():
    block = SRC[SRC.index("def _install_sidebar_hover_expand(app):"):SRC.index("def _status_color(score):")]
    assert "_sidebar_collapsed" in block
    assert "_theme_toggle_button" in block
    assert "_ai_button" in block
