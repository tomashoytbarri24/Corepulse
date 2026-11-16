"""REBUILD 193: one-time permission UX, no Qt dependency for local persistence tests."""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_functions(path, names):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    chosen = [item for item in tree.body
              if isinstance(item, ast.FunctionDef) and item.name in names]
    assert len(chosen) == len(names)
    context = {'Path': Path, 'json': json, 'os': os, 'hashlib': hashlib}
    exec(compile(ast.Module(body=chosen, type_ignores=[]), str(path), 'exec'), context)
    return context


def test_ookla_terms_remembered_once_and_can_be_revoked(tmp_path, monkeypatch):
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    names = ('_ookla_acceptance_path', 'read_ookla_acceptance', 'save_ookla_acceptance')
    ns = _load_functions(ROOT/'core/maintenance/speed_test.py', names)
    read, save = ns['read_ookla_acceptance'], ns['save_ookla_acceptance']
    assert read() is False
    assert save(True) is True
    assert read() is True
    content = json.loads((tmp_path/'CorePulse'/'ookla-acceptance.json').read_text('utf-8'))
    assert content == {'ookla_terms_accepted': True}
    assert save(False) is True
    assert read() is False
    (tmp_path/'CorePulse'/'ookla-acceptance.json').write_text('{not-json', encoding='utf-8')
    assert read() is False


def test_ai_hardware_permission_opt_in_is_per_account_and_persistent(tmp_path, monkeypatch):
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    names = ('_ai_telemetry_permissions_path', '_ai_permission_account_id',
             'read_ai_telemetry_permissions', 'save_ai_telemetry_permissions')
    ns = _load_functions(ROOT/'core/ai.py', names)
    read, save = ns['read_ai_telemetry_permissions'], ns['save_ai_telemetry_permissions']
    email_a, email_b = 'tester@example.com', 'another@example.com'
    assert read(email_a) == {'hardware': False, 'history': False}
    assert save(email_a, hardware=True, history=True) is True
    assert read(email_a) == {'hardware': True, 'history': True}
    assert read('TESTER@example.com') == {'hardware': True, 'history': True}
    assert read(email_b) == {'hardware': False, 'history': False}
    raw = (tmp_path/'CorePulse'/'ai-telemetry-permissions.json').read_text('utf-8')
    assert email_a not in raw and email_b not in raw
    assert save(email_a, hardware=False, history=True) is True
    assert read(email_a) == {'hardware': False, 'history': False}
    assert not save('', hardware=True, history=True)
    (tmp_path/'CorePulse'/'ai-telemetry-permissions.json').write_text('wrong-json', encoding='utf-8')
    assert read(email_a) == {'hardware': False, 'history': False}


def test_qml_direct_start_only_after_ookla_terms_and_still_exposes_revoke():
    qml = (ROOT/'ui/NetworkPage.qml').read_text('utf-8')
    backend = (ROOT/'core/maintenance/speed_test.py').read_text('utf-8')
    assert qml.count('onClicked: page.beginSpeedtest()') == 2
    assert 'if (speedInfo.termsAccepted)' in qml
    assert 'networkSpeedTest.start("ookla")' in qml
    assert 'page.confirmSpeedTest = true' in qml
    assert 'networkSpeedTest.startWithConsent("ookla",accepted)' in qml
    assert 'networkSpeedTest.forgetOoklaTerms()' in qml
    assert 'accepted = bool(ookla_terms_accepted) or read_ookla_acceptance()' in backend
    assert 'ookla_terms_accepted=accepted' in backend
    assert "'termsAccepted': read_ookla_acceptance()" in backend


def test_ai_restores_only_explicit_per_account_permissions_and_does_not_send_on_open():
    core = (ROOT/'core/ai.py').read_text('utf-8')
    ui = (ROOT/'ui/AIPage.qml').read_text('utf-8')
    assert 'self._restore_account_permissions()' in core
    assert 'self._save_account_permissions()' in core
    assert 'self._hardware = False' in core
    assert 'self._history_consent = False' in core
    assert '_ai_permission_account_id(email)' in core
    assert 'hardware=self._hardware' in core
    assert 'history=self._history_consent' in core
    assert 'authorized_snapshot(dict(telemetry.metrics), self._hardware)' in core
    assert 'self._history_consent and temporal_question' in core
    assert 'onToggled: corepulseAI.allowHardware(checked)' in ui
    assert 'onToggled: corepulseAI.allowHistory(checked)' in ui
    assert 'recordar decisión' in ui
