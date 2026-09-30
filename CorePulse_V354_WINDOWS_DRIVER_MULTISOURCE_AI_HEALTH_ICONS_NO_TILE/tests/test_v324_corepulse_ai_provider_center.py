from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def test_ai_navigation_is_integrated():
    nav = (ROOT / 'gui' / 'internal_navigation.py').read_text(encoding='utf-8')
    dashboard = (ROOT / 'gui' / 'dashboard.py').read_text(encoding='utf-8')
    main = (ROOT / 'main.py').read_text(encoding='utf-8')
    assert "'ai': '_ai_button'" in nav
    assert "'ai': 'ai_panel'" in nav
    assert 'CorePulse AI' in dashboard
    assert 'def open_ai_center' in main

def test_v326_supersedes_direct_provider_keys():
    provider = (ROOT / 'core' / 'ai_provider.py').read_text(encoding='utf-8').lower()
    panel = (ROOT / 'gui' / 'ai_panel.py').read_text(encoding='utf-8').lower()
    req = (ROOT / 'requirements-runtime-lock.txt').read_text(encoding='utf-8').lower()
    assert "read_secret('openai')" not in provider
    assert "read_secret('groq')" not in provider
    assert 'key_entry' not in panel
    assert 'provider_buttons' not in panel
    assert 'openai==' not in req
    assert 'groq==' not in req
    assert 'ollama' not in provider
