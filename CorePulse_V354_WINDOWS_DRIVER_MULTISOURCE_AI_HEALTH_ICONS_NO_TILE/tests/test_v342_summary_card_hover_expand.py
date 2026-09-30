from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / "gui" / "dashboard.py").read_text(encoding="utf-8")


def test_card_hover_supports_micro_expand():
    block = SRC[SRC.index("def _bind_card_hover("):SRC.index("def _bind_hover_tooltip(")]
    assert "expand_px=0" in block
    assert "grid_configure(padx=tuple(pair))" in block
    assert "pack_configure(padx=tuple(pair))" in block
    assert "steps = 5" in block
    assert "root.after(12, tick)" in block


def test_summary_status_cards_enable_expand():
    assert "_bind_card_hover(health_card, expand_px=5)" in SRC
    assert "_bind_card_hover(alerts, expand_px=5)" in SRC
    assert "_bind_card_hover(coverage, expand_px=5)" in SRC
    assert "_bind_card_hover(uptime, expand_px=5)" in SRC


def test_resource_cards_enable_expand_without_touching_data_contracts():
    assert SRC.count("expand_px=5") >= 7
    canonical = (ROOT / "COREPULSE_CANONICAL_BASE.md").read_text(encoding="utf-8")
    assert "REAL_OR_NA" in canonical
    assert "REAL_FPS_OR_NA_ONLY" in canonical
