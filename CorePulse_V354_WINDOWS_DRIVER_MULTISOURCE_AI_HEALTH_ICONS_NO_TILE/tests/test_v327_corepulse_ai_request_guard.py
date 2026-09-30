from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_client_has_request_guard_and_remaining_quota_feedback():
    text = (ROOT / 'gui' / 'ai_panel.py').read_text(encoding='utf-8')
    assert '_last_submit_monotonic' in text
    assert '1.25' in text
    assert 'remaining_today' in text


def test_embedded_server_deduplicates_and_uses_dev_limit():
    config = (ROOT / 'CorePulse_AI_Server' / 'app' / 'config.py').read_text(encoding='utf-8')
    main = (ROOT / 'CorePulse_AI_Server' / 'app' / 'main.py').read_text(encoding='utf-8')
    assert "COREPULSE_AI_DAILY_LIMIT', '200'" in config
    assert 'COREPULSE_AI_DEDUP_SECONDS' in config
    assert '_cached_response' in main
    assert "out['deduplicated'] = True" in main
