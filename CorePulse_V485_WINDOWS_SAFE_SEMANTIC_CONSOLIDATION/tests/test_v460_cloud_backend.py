"""V460: pruebas reproducibles sin servidor remoto ni GPU.

No se requiere LLM para verificar la conexión/contrato del servicio: las
respuestas de inferencia se simulan separadamente del backend auténtico.
"""
from __future__ import annotations
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / 'CorePulse_AI_Server'
if str(SERVER) not in sys.path:
    sys.path.insert(0, str(SERVER))

from app import store, main
from core import ai_client


@pytest.fixture
def remote(tmp_path, monkeypatch):
    monkeypatch.setattr(store, 'DB_PATH', tmp_path / 'test_devices.sqlite3')
    monkeypatch.setattr(store, 'DAILY_LIMIT', 3)
    monkeypatch.setattr(main, 'DEDUP_SECONDS', 0)
    main._recent_responses.clear()
    with TestClient(main.app) as client:
        yield client


def _paired(remote, ident='device-v460'):
    code, _ = store.issue_pairing_code(minutes=5)
    r = remote.post('/v1/register', json={'installation_id': ident}, headers={'X-CorePulse-Enrollment': code})
    assert r.status_code == 200, r.text
    return code, r.json()['token']


def test_unauthorized_no_model_or_telemetry_access(remote):
    assert remote.post('/v1/register', json={'installation_id': 'device-v460'}, headers={'X-CorePulse-Enrollment': 'incorrecto'}).status_code == 403
    assert remote.post('/v1/chat', json={'context': {}, 'question': 'hola'}).status_code == 401
    assert remote.post('/v1/analyze', json={'context': {}}).status_code == 401


def test_pairing_consumed_and_expired(remote, monkeypatch):
    code, token = _paired(remote)
    assert token.startswith('_') or len(token) >= 35
    again = remote.post('/v1/register', json={'installation_id': 'another-device'}, headers={'X-CorePulse-Enrollment': code})
    assert again.status_code == 403
    with patch('app.store.time.time', return_value=20_000):
        short, expires = store.issue_pairing_code(minutes=1)
    with patch('app.store.time.time', return_value=expires):
        expired = remote.post('/v1/register', json={'installation_id': 'expired-device'}, headers={'X-CorePulse-Enrollment': short})
    assert expired.status_code == 403


def test_pairing_atomic_under_concurrent_redemption(remote):
    code, _ = store.issue_pairing_code(minutes=30)
    def use(i):
        return store.register_installation(f'device-concurrent-{i}', '460', 'Windows', code)
    with ThreadPoolExecutor(max_workers=2) as pool:
        values = list(pool.map(use, range(2)))
    assert sum(bool(v) for v in values) == 1


def test_real_or_na_and_no_original_extras(remote, monkeypatch):
    _, token = _paired(remote)
    with patch.object(main, 'model_ready', return_value=False):
        result = remote.post('/v1/chat', json={
            'question': '¿Cuál es la temperatura CPU?',
            'context': {'cpu': {'name': 'AMD Ryzen', 'temperature_c': None}, 'secret_home_path': 'C:/Users/private', 'ram': {'total_gb': 16}},
        }, headers={'Authorization': f'Bearer {token}'})
    assert result.status_code == 200
    assert result.json()['mode'] == 'evidence_fallback'
    assert 'N/A' in result.json()['text']
    assert 'private' not in result.text


def test_model_routing_and_daily_limit(remote):
    _, token = _paired(remote)
    with patch.object(main, 'model_ready', return_value=True), patch.object(main, 'generate', return_value='Temperatura CPU: N/A.') as generate:
        for i in range(3):
            result = remote.post('/v1/chat', json={'context': {'cpu': {}}, 'question': f'consulta {i}'}, headers={'Authorization': f'Bearer {token}'})
            assert result.status_code == 200
            assert result.json()['mode'] == 'model'
            assert result.json()['remaining_today'] == 2 - i
        assert generate.call_count == 3
    limited = remote.post('/v1/chat', json={'context': {}, 'question': 'otra'}, headers={'Authorization': f'Bearer {token}'})
    assert limited.status_code == 429


def test_revocation_blocks_existing_token(remote):
    _, token = _paired(remote)
    assert store.token_valid(token)
    assert store.revoke_installation('device-v460')
    assert not store.token_valid(token)
    assert remote.post('/v1/chat', json={'context': {}, 'question': 'hola'}, headers={'Authorization': f'Bearer {token}'}).status_code == 401


def test_maximum_request_size_and_server_status(remote):
    assert remote.get('/v1/status').status_code == 200
    oversized = {'context': {'internal_dump': 'X' * 180_000}, 'question': 'hola'}
    result = remote.post('/v1/chat', json=oversized)
    assert result.status_code == 413
    # Sin Content-Length: el middleware protege igualmente bodies fragmentados.
    with patch.object(main, 'model_reachable', return_value=False):
        response = remote.get('/v1/status')
        # La versión del servidor avanza; se conserva el contrato V460.
        assert response.json()['service_version'] in {'1.7.0', '1.8.0'}


def test_desktop_refuses_unauthorized_transmission():
    s = {'base_url': 'https://corepulse.example', 'cloud_telemetry_consent': False, 'timeout_seconds': 5}
    with patch('core.ai_client.urllib.request.build_opener', side_effect=AssertionError('Network forbidden')):
        assert ai_client.service_status(s)['state'] == 'CLOUD_CONSENT_REQUIRED'
        assert ai_client.chat_context({}, question='hola', settings=s)['state'] == 'CLOUD_CONSENT_REQUIRED'


def test_desktop_pairing_code_erased_once_token_saved():
    settings = {'base_url': 'https://corepulse.example', 'cloud_telemetry_consent': True, 'timeout_seconds': 5, 'token_base_url': ''}
    response = {'ok': True, 'token': 'issued-device-token'}
    with patch('core.ai_client.load_ai_settings', return_value=settings), \
         patch('core.ai_client.read_secret', return_value='cp-single-use'), \
         patch('core.ai_client.save_secret', return_value=True) as save, \
         patch('core.ai_client.delete_secret') as delete, \
         patch('core.ai_client.save_ai_settings', return_value=settings), \
         patch('core.ai_client._request', return_value=response) as request:
        assert ai_client.ensure_registration(settings)['ok']
    assert save.call_args.args == (ai_client.TOKEN_NAME, 'issued-device-token')
    delete.assert_called_once_with(ai_client.ENROLLMENT_NAME)
    assert request.call_args.kwargs['enrollment'] == 'cp-single-use'


def test_no_automatic_reuse_of_shared_pairing_code_on_revocation():
    settings = {'base_url': 'https://corepulse.example', 'cloud_telemetry_consent': True, 'timeout_seconds': 5, 'token_base_url': 'https://corepulse.example'}
    with patch('core.ai_client.load_ai_settings', return_value=settings), \
         patch('core.ai_client.read_secret', return_value='revoked-device-token'), \
         patch('core.ai_client._request', return_value={'ok': False, 'error': 'HTTP 401: Invalid'}), \
         patch('core.ai_client.delete_secret') as delete, \
         patch('core.ai_client.ensure_registration', return_value={'ok': True, 'token': 'revoked-device-token'}) as registration:
        result = ai_client.chat_context({}, question='hola', settings=settings)
    assert result['state'] == 'CLOUD_PAIRING_REQUIRED'
    assert registration.call_count == 1
    delete.assert_called_once_with(ai_client.TOKEN_NAME)


def test_cloud_files_no_open_inference_ports():
    deploy = (ROOT / 'CorePulse_AI_Cloud_Deployment/compose.yaml').read_text(encoding='utf8')
    assert 'gpus: all' in deploy
    assert deploy.count('    ports:\n') == 1
    assert 'COREPULSE_MODEL_API_KEY:' in deploy
    assert 'COREPULSE_MODEL_BASE_URL: http://model:8000/v1' in deploy
    assert 'request_body' in (ROOT / 'CorePulse_AI_Cloud_Deployment/Caddyfile').read_text(encoding='utf8')
