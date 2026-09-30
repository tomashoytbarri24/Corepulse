from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_client_exposes_chat_endpoint_without_provider_sdk():
    client = (ROOT / 'core' / 'ai_client.py').read_text(encoding='utf-8').lower()
    assert 'def chat_context' in client
    assert "'/v1/chat'" in client
    assert "'policy': 'real_or_na'" in client
    assert 'from openai import' not in client
    assert 'from groq import' not in client
    assert 'ollama' not in client


def test_ai_panel_is_conversational_and_keeps_request_guard():
    panel = (ROOT / 'gui' / 'ai_panel.py').read_text(encoding='utf-8')
    assert 'Conversación con CorePulse AI' in panel
    assert '_conversation' in panel
    assert 'chat_context' in panel
    assert '_last_submit_monotonic' in panel
    assert '1.25' in panel


def test_embedded_server_has_chat_and_self_hosted_model_gateway():
    main = (ROOT / 'CorePulse_AI_Server' / 'app' / 'main.py').read_text(encoding='utf-8')
    gateway = (ROOT / 'CorePulse_AI_Server' / 'app' / 'model_gateway.py').read_text(encoding='utf-8')
    config = (ROOT / 'CorePulse_AI_Server' / 'app' / 'config.py').read_text(encoding='utf-8')
    assert "@app.post('/v1/chat')" in main
    assert 'model_reachable' in main
    assert '/chat/completions' in gateway
    assert 'REAL_OR_NA' in gateway
    assert '127.0.0.1:8766/v1' in config
    assert 'ollama' not in gateway.lower()
