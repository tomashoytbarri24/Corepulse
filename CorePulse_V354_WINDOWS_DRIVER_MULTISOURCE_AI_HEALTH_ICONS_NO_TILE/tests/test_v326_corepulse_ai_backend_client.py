from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def test_backend_client_and_server_exist():
    assert (ROOT / 'core' / 'ai_client.py').exists()
    assert (ROOT / 'CorePulse_AI_Server' / 'app' / 'main.py').exists()
    assert (ROOT / 'CorePulse_AI_Server' / 'app' / 'evidence.py').exists()
    assert (ROOT / 'CorePulse_AI_Server' / 'app' / 'model_gateway.py').exists()

def test_client_is_thin_and_real_or_na():
    src = (ROOT / 'core' / 'ai_client.py').read_text(encoding='utf-8')
    assert "'policy': 'REAL_OR_NA'" in src
    assert '/v1/register' in src
    assert '/v1/analyze' in src
    assert 'openai import' not in src.lower()
    assert 'groq import' not in src.lower()
    assert 'ollama' not in src.lower()

def test_backend_re_sanitizes_evidence_and_rate_limits():
    evidence = (ROOT / 'CorePulse_AI_Server' / 'app' / 'evidence.py').read_text(encoding='utf-8')
    store = (ROOT / 'CorePulse_AI_Server' / 'app' / 'store.py').read_text(encoding='utf-8')
    main = (ROOT / 'CorePulse_AI_Server' / 'app' / 'main.py').read_text(encoding='utf-8')
    assert "'policy': 'REAL_OR_NA'" in evidence
    assert 'DAILY_LIMIT' in store
    assert "@app.post('/v1/register')" in main
    assert "@app.post('/v1/analyze')" in main

def test_desktop_requirements_have_no_provider_sdks():
    for name in ('requirements-base.txt', 'requirements-runtime-flex.txt', 'requirements-runtime-lock.txt'):
        text = (ROOT / name).read_text(encoding='utf-8').lower()
        assert '\nopenai' not in '\n' + text
        assert '\ngroq' not in '\n' + text


def test_report_ai_uses_corepulse_backend_not_vendor_sdks():
    report = (ROOT / 'core' / 'ai_report_engine.py').read_text(encoding='utf-8').lower()
    readiness = (ROOT / 'core' / 'startup_readiness.py').read_text(encoding='utf-8').lower()
    assert 'from groq import' not in report
    assert 'from openai import' not in report
    assert 'groq_api_key' not in report
    assert 'sdk groq' not in readiness
    assert 'sdk openai' not in readiness
