"""Cliente liviano para el backend propio de CorePulse AI.

El cliente NO contiene modelos, API keys de proveedores ni lógica de diagnóstico.
Envía sólo evidencia sanitizada de CorePulse y recibe una explicación del servidor.
"""
from __future__ import annotations

import json
import math
import os
import platform
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Any, Dict, Optional

from core.ai_credentials import read_secret, save_secret
from core.runtime_paths import config_path
from core.version import VERSION

SETTINGS_PATH = config_path('ai_settings.json')
INSTALLATION_PATH = config_path('ai_installation.json')
DEFAULT_BASE_URL = 'http://127.0.0.1:8765'
TOKEN_NAME = 'corepulse_server'
DEFAULT_TIMEOUT = 20


def _safe_text(value: Any) -> str:
    return str(value or '').strip()


def _allowed_base_url(value: str) -> str:
    raw = _safe_text(value).rstrip('/') or DEFAULT_BASE_URL
    parsed = urllib.parse.urlparse(raw)
    if parsed.scheme == 'https' and parsed.netloc:
        return raw
    if parsed.scheme == 'http' and (parsed.hostname or '').lower() in {'127.0.0.1', 'localhost', '::1'}:
        return raw
    return DEFAULT_BASE_URL


def load_ai_settings() -> Dict[str, Any]:
    settings = {'base_url': _safe_text(os.getenv('COREPULSE_AI_BASE_URL')) or DEFAULT_BASE_URL, 'timeout_seconds': DEFAULT_TIMEOUT}
    try:
        if SETTINGS_PATH.is_file():
            data = json.loads(SETTINGS_PATH.read_text(encoding='utf-8'))
            if isinstance(data, dict):
                settings.update({k: data[k] for k in ('base_url', 'timeout_seconds') if k in data})
    except Exception:
        pass
    settings['base_url'] = _allowed_base_url(settings.get('base_url'))
    try:
        settings['timeout_seconds'] = max(5, min(60, int(settings.get('timeout_seconds') or DEFAULT_TIMEOUT)))
    except Exception:
        settings['timeout_seconds'] = DEFAULT_TIMEOUT
    return settings


def save_ai_settings(values: Dict[str, Any]) -> Dict[str, Any]:
    current = load_ai_settings()
    if 'base_url' in values:
        current['base_url'] = _allowed_base_url(values.get('base_url'))
    if 'timeout_seconds' in values:
        try:
            current['timeout_seconds'] = max(5, min(60, int(values['timeout_seconds'])))
        except Exception:
            pass
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding='utf-8')
    return current


def _installation_id() -> str:
    try:
        if INSTALLATION_PATH.is_file():
            data = json.loads(INSTALLATION_PATH.read_text(encoding='utf-8'))
            value = _safe_text(data.get('installation_id')) if isinstance(data, dict) else ''
            if value:
                return value
    except Exception:
        pass
    value = str(uuid.uuid4())
    INSTALLATION_PATH.parent.mkdir(parents=True, exist_ok=True)
    INSTALLATION_PATH.write_text(json.dumps({'installation_id': value}, indent=2), encoding='utf-8')
    return value


def _request(method: str, path: str, *, payload: Optional[dict] = None, token: Optional[str] = None, settings: Optional[dict] = None) -> Dict[str, Any]:
    settings = settings or load_ai_settings()
    url = settings['base_url'] + path
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode('utf-8')
    headers = {'Accept': 'application/json', 'User-Agent': f'CorePulse/{VERSION}'}
    if data is not None:
        headers['Content-Type'] = 'application/json; charset=utf-8'
    if token:
        headers['Authorization'] = f'Bearer {token}'
    req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=float(settings['timeout_seconds'])) as response:
            raw = response.read().decode('utf-8', errors='replace')
        parsed = json.loads(raw) if raw else {}
        return parsed if isinstance(parsed, dict) else {'ok': False, 'error': 'Respuesta inválida del servicio.'}
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode('utf-8', errors='replace')
            parsed = json.loads(body)
            detail = parsed.get('detail') if isinstance(parsed, dict) else body
        except Exception:
            detail = str(exc)
        return {'ok': False, 'error': f'HTTP {exc.code}: {detail}'}
    except Exception as exc:
        return {'ok': False, 'error': f'{type(exc).__name__}: {exc}'}


def ensure_registration(settings: Optional[dict] = None) -> Dict[str, Any]:
    settings = settings or load_ai_settings()
    token = read_secret(TOKEN_NAME)
    if token:
        return {'ok': True, 'token': token, 'registered': True}
    payload = {
        'installation_id': _installation_id(),
        'client_version': VERSION,
        'platform': 'Windows',
        'python': platform.python_version(),
    }
    result = _request('POST', '/v1/register', payload=payload, settings=settings)
    token = _safe_text(result.get('token')) if result.get('ok') else ''
    if token:
        if save_secret(TOKEN_NAME, token):
            return {'ok': True, 'token': token, 'registered': True}
        # En ejecución de desarrollo no-Windows permitimos usar el token sólo en memoria.
        if os.name != 'nt':
            return {'ok': True, 'token': token, 'registered': True, 'volatile': True}
        return {'ok': False, 'error': 'No se pudo guardar el token del servicio en Windows Credential Manager.'}
    return {'ok': False, 'error': result.get('error') or 'El servidor no entregó un token.'}


def service_status(settings: Optional[dict] = None) -> Dict[str, Any]:
    settings = settings or load_ai_settings()
    result = _request('GET', '/v1/status', settings=settings)
    if not result.get('ok'):
        return {'ok': False, 'state': 'OFFLINE', 'base_url': settings['base_url'], 'error': result.get('error')}
    result['base_url'] = settings['base_url']
    return result


def _finite(value: Any):
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def build_runtime_context(telemetry: Any, disks: Any, health: Any) -> Dict[str, Any]:
    """Produce un esquema mínimo: sin seriales, rutas, usuario, IP, MAC ni IDs de hardware."""
    telemetry = telemetry if isinstance(telemetry, dict) else {}
    disks = disks if isinstance(disks, list) else []
    health = health if isinstance(health, dict) else {}
    safe_disks = []
    for item in disks[:8]:
        if not isinstance(item, dict):
            continue
        safe_disks.append({
            'model': _safe_text(item.get('model') or item.get('name'))[:120] or None,
            'used_percent': _finite(item.get('used_percent')),
            'health_percent': _finite(item.get('health')),
            'temperature_c': _finite(item.get('temperature') or item.get('temperature_c')),
        })
    return {
        'policy': 'REAL_OR_NA',
        'health': {
            'score': _finite(health.get('score')),
            'status': _safe_text(health.get('status'))[:80] or None,
            'severity': _safe_text(health.get('severity'))[:32] or None,
            'reasons': [_safe_text(x)[:180] for x in list(health.get('reasons') or [])[:8] if _safe_text(x)],
        },
        'cpu': {
            'name': _safe_text(telemetry.get('cpu_name'))[:120] or None,
            'usage_percent': _finite(telemetry.get('cpu_usage')),
            'temperature_c': _finite(telemetry.get('cpu_temp')),
            'frequency_ghz': _finite(telemetry.get('cpu_ghz')),
        },
        'ram': {
            'usage_percent': _finite(telemetry.get('ram_usage')),
            'used_gb': _finite(telemetry.get('ram_used_gb')),
            'total_gb': _finite(telemetry.get('ram_total_gb')),
        },
        'gpu': {
            'name': _safe_text(telemetry.get('gpu_name'))[:120] or None,
            'usage_percent': _finite(telemetry.get('gpu_usage')),
            'temperature_c': _finite(telemetry.get('gpu_temp')),
            'vram_gb': _finite(telemetry.get('gpu_vram_gb')),
        },
        'storage': safe_disks,
    }


def analyze_context(context: Dict[str, Any], *, question: str = '', settings: Optional[dict] = None) -> Dict[str, Any]:
    settings = settings or load_ai_settings()
    reg = ensure_registration(settings)
    if not reg.get('ok'):
        return {'ok': False, 'error': reg.get('error'), 'state': 'UNAVAILABLE'}
    payload = {'context': context, 'question': _safe_text(question)[:1200]}
    result = _request('POST', '/v1/analyze', payload=payload, token=reg['token'], settings=settings)
    if result.get('ok'):
        return result
    # Si el token expiró o fue revocado, se re-registra una sola vez.
    if '401' in _safe_text(result.get('error')):
        from core.ai_credentials import delete_secret
        delete_secret(TOKEN_NAME)
        reg = ensure_registration(settings)
        if reg.get('ok'):
            return _request('POST', '/v1/analyze', payload=payload, token=reg['token'], settings=settings)
    return result


def _clean_chat_history(history: Any) -> list[dict[str, str]]:
    clean: list[dict[str, str]] = []
    for item in list(history or [])[-8:]:
        if not isinstance(item, dict):
            continue
        role = _safe_text(item.get('role')).lower()
        if role not in {'user', 'assistant'}:
            continue
        content = _safe_text(item.get('content'))[:1800]
        if content:
            clean.append({'role': role, 'content': content})
    return clean


def chat_context(context: Dict[str, Any], *, question: str, history: Any = None, settings: Optional[dict] = None) -> Dict[str, Any]:
    settings = settings or load_ai_settings()
    question = _safe_text(question)[:1200]
    if not question:
        return {'ok': False, 'error': 'Escribe una pregunta para CorePulse AI.', 'state': 'EMPTY_QUESTION'}
    reg = ensure_registration(settings)
    if not reg.get('ok'):
        return {'ok': False, 'error': reg.get('error'), 'state': 'UNAVAILABLE'}
    payload = {'context': context, 'question': question, 'history': _clean_chat_history(history)}
    result = _request('POST', '/v1/chat', payload=payload, token=reg['token'], settings=settings)
    if result.get('ok'):
        return result
    if '401' in _safe_text(result.get('error')):
        from core.ai_credentials import delete_secret
        delete_secret(TOKEN_NAME)
        reg = ensure_registration(settings)
        if reg.get('ok'):
            return _request('POST', '/v1/chat', payload=payload, token=reg['token'], settings=settings)
    return result


__all__ = [
    'DEFAULT_BASE_URL', 'load_ai_settings', 'save_ai_settings', 'service_status',
    'ensure_registration', 'build_runtime_context', 'analyze_context', 'chat_context',
]
