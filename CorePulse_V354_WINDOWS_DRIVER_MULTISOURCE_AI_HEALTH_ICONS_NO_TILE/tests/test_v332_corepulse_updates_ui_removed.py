from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v332_version_and_updates_module_remain_removed():
    version = (ROOT / 'core' / 'version.py').read_text(encoding='utf-8')
    assert 'VERSION = "354"' in version
    assert not (ROOT / 'gui' / 'update_dialog.py').exists()
    assert not (ROOT / 'core' / 'update_manager.py').exists()


def test_personalization_has_only_themes_and_corepulse_ai_not_app_updates():
    dashboard = (ROOT / 'gui' / 'dashboard.py').read_text(encoding='utf-8')
    layout = (ROOT / 'gui' / 'dashboard_layout.py').read_text(encoding='utf-8')
    navigation = (ROOT / 'gui' / 'internal_navigation.py').read_text(encoding='utf-8')
    main = (ROOT / 'main.py').read_text(encoding='utf-8')

    assert "text='◉  Temas'" in dashboard
    assert "text='✦  CorePulse AI'" in dashboard
    assert "('themes', 'Temas')" not in navigation  # route table uses dict syntax, guard is below
    assert "'themes': 'Temas'" in navigation
    assert "'ai': 'CorePulse AI'" in navigation

    # No debe existir ningún control/ruta navegable de actualización de la app.
    for text in (dashboard, layout, navigation, main):
        assert "text='↻  Actualizaciones'" not in text
        assert "text='Actualizaciones'" not in text
        assert "'updates': 'Actualizaciones'" not in text
        assert 'open_updates' not in text
        assert 'open_update_center' not in text


def test_legacy_update_widgets_are_explicitly_cleared_on_sidebar_rebuild():
    dashboard = (ROOT / 'gui' / 'dashboard.py').read_text(encoding='utf-8')
    for name in ("'_updates_button'", "'_update_button'", "'btn_updates'", "'btn_update'"):
        assert name in dashboard
