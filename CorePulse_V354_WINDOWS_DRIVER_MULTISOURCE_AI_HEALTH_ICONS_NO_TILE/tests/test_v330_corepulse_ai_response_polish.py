from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_model_prompt_preserves_corepulse_severity_and_plain_text():
    text = (ROOT / 'CorePulse_AI_Server' / 'app' / 'model_gateway.py').read_text(encoding='utf-8')
    low = text.lower()
    assert 'no eleves ni rebajes la severidad' in low
    assert 'no uses markdown' in low
    assert 'bios, voltajes o firmware' in low
    assert 'def _normalize_visible_text' in text


def test_ui_has_last_plain_text_guard():
    text = (ROOT / 'gui' / 'ai_panel.py').read_text(encoding='utf-8')
    assert 'def _plain_ai_text' in text
    assert "answer = _plain_ai_text" in text


def test_server_version_and_response_budget():
    main = (ROOT / 'CorePulse_AI_Server' / 'app' / 'main.py').read_text(encoding='utf-8')
    config = (ROOT / 'CorePulse_AI_Server' / 'app' / 'config.py').read_text(encoding='utf-8')
    assert "version='1.3.0'" in main
    assert "'service_version': '1.3.0'" in main
    assert "COREPULSE_MODEL_MAX_TOKENS', '650'" in config


def test_plain_text_normalizer_removes_common_markdown():
    import sys
    sys.path.insert(0, str(ROOT / 'CorePulse_AI_Server'))
    from app.model_gateway import _normalize_visible_text
    out = _normalize_visible_text('## Estado\n**CPU:** `83 C`\n\n\n- Atención')
    assert out == 'Estado\nCPU: 83 C\n\n- Atención'
