from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v349_lineage_remains_inside_v352():
    version = (ROOT / 'core' / 'version.py').read_text(encoding='utf-8')
    assert 'VERSION = "354"' in version
    assert 'RUNTIME_VALIDATOR_FIX' in version


def test_desktop_runtime_validator_does_not_require_provider_sdk():
    validator = (ROOT / 'tools' / 'validate_python_runtime.py').read_text(encoding='utf-8').lower()
    required_block = validator.split('required_imports = (', 1)[1].split(')', 1)[0]
    assert "'groq'" not in required_block
    assert "'openai'" not in required_block
    assert "'dotenv'" in required_block
    assert "'hardwaremonitor'" in required_block


def test_desktop_requirements_still_have_no_provider_sdks():
    for name in ('requirements-base.txt', 'requirements-runtime-flex.txt', 'requirements-runtime-lock.txt'):
        text = (ROOT / name).read_text(encoding='utf-8').lower()
        assert '\ngroq' not in '\n' + text
        assert '\nopenai' not in '\n' + text


def test_v352_visual_fix_supersedes_button_model_without_touching_runtime_fix():
    panel = (ROOT / 'gui' / 'health_center_panel.py').read_text(encoding='utf-8')
    assert "GAME_BOOST_ICON_CYAN = '#21c7ff'" in panel
    assert 'button_w = max(94, min(126' not in panel
    assert 'GAME_BOOST_TILE_BG' not in panel
