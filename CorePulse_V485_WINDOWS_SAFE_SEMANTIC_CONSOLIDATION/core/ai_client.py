"""Cliente liviano para el backend propio de CorePulse AI.

El cliente NO contiene modelos, API keys de proveedores ni lógica de diagnóstico.
Envía sólo evidencia sanitizada de CorePulse y recibe una explicación del servidor.
"""
from __future__ import annotations

import json
import math
import os
import platform
import re
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from core.ai_credentials import read_secret, save_secret, delete_secret
from core.ai_user_control import load_ai_enabled
from core.ai_provider_binding import provider_identity
from core.runtime_paths import config_path
from core.version import VERSION

SETTINGS_PATH = config_path('ai_settings.json')
INSTALLATION_PATH = config_path('ai_installation.json')
DEFAULT_BASE_URL = ''  # cloud desactivada hasta configurar HTTPS
LOCAL_GROQ_BRIDGE_URL = 'http://127.0.0.1:8765'  # sólo pruebas explícitas
LOCAL_COMPAT_BRIDGE_URL = 'http://127.0.0.1:8766'  # segundo proveedor, aislado del vínculo Groq
TOKEN_NAME = 'corepulse_cloud_token'
ENROLLMENT_NAME = 'corepulse_cloud_enrollment'
DEFAULT_TIMEOUT = 105
STATUS_TIMEOUT = 3
REGISTRATION_TIMEOUT = 12


def _safe_text(value: Any) -> str:
    return str(value or '').strip()


def _allowed_base_url(value: str, *, allow_local_groq_bridge: bool = False, allow_local_compatible_bridge: bool = False) -> str:
    """HTTPS siempre; sólo excepción opt-in al puente exacto loopback V463."""
    raw = _safe_text(value).rstrip('/')
    if allow_local_groq_bridge and raw == LOCAL_GROQ_BRIDGE_URL:
        return raw
    if allow_local_compatible_bridge and raw == LOCAL_COMPAT_BRIDGE_URL:
        return raw
    if not raw:
        return ''
    try:
        parsed = urllib.parse.urlparse(raw)
        if (parsed.scheme != 'https' or not parsed.hostname or
                parsed.username is not None or parsed.password is not None or
                parsed.query or parsed.fragment or parsed.params or
                parsed.hostname.lower() in {'localhost', '127.0.0.1', '::1'} or
                not parsed.netloc):
            return ''
        return raw
    except (ValueError, TypeError):
        return ''


def _cloud_gate(settings: Optional[dict] = None) -> Dict[str, Any]:
    settings = settings or load_ai_settings()
    if not load_ai_enabled():
        return {'ok': False, 'state': 'DISABLED', 'error': 'CorePulse AI está apagada.'}
    if not settings.get('base_url'):
        return {'ok': False, 'state': 'CLOUD_NOT_CONFIGURED',
                'error': 'Configura primero un servidor CorePulse AI Cloud con HTTPS.'}
    if not _allowed_base_url(settings.get('base_url'),
            allow_local_groq_bridge=settings.get('local_groq_bridge') is True,
            allow_local_compatible_bridge=settings.get('local_compatible_bridge') is True):
        return {'ok': False, 'state': 'CLOUD_INVALID_ENDPOINT',
                'error': 'La dirección del servidor debe ser HTTPS válida.'}
    if settings.get('base_url') == LOCAL_COMPAT_BRIDGE_URL and (
            not provider_identity() or settings.get('consented_upstream') != provider_identity()):
        return {'ok': False, 'state': 'CLOUD_CONSENT_REQUIRED',
                'error': 'El servidor alternativo cambió. Se requiere permiso nuevo.'}
    if settings.get('cloud_telemetry_consent') is not True:
        return {'ok': False, 'state': 'CLOUD_CONSENT_REQUIRED',
                'error': 'Falta autorizar la conexión y el envío de datos al servidor configurado.'}
    return {'ok': True, 'state': 'CLOUD_AUTHORIZED'}


def load_ai_settings() -> Dict[str, Any]:
    settings = {'base_url': _safe_text(os.getenv('COREPULSE_AI_BASE_URL')) or DEFAULT_BASE_URL,
                'timeout_seconds': DEFAULT_TIMEOUT, 'cloud_telemetry_consent': False,
                'token_base_url': '', 'local_groq_bridge': False, 'local_compatible_bridge': False, 'consented_upstream': ''}
    try:
        if SETTINGS_PATH.is_file():
            data = json.loads(SETTINGS_PATH.read_text(encoding='utf-8'))
            if isinstance(data, dict):
                settings.update({k: data[k] for k in ('base_url', 'timeout_seconds', 'cloud_telemetry_consent', 'token_base_url', 'local_groq_bridge', 'local_compatible_bridge', 'consented_upstream') if k in data})
    except Exception:
        pass
    settings['local_groq_bridge'] = settings.get('local_groq_bridge') is True
    settings['local_compatible_bridge'] = settings.get('local_compatible_bridge') is True
    settings['base_url'] = _allowed_base_url(settings.get('base_url'), allow_local_groq_bridge=settings['local_groq_bridge'],
        allow_local_compatible_bridge=settings['local_compatible_bridge'])
    settings['cloud_telemetry_consent'] = settings.get('cloud_telemetry_consent') is True
    settings['token_base_url'] = _safe_text(settings.get('token_base_url'))
    settings['consented_upstream'] = _safe_text(settings.get('consented_upstream'))
    if settings['base_url'] == LOCAL_COMPAT_BRIDGE_URL and settings['consented_upstream'] != provider_identity():
        # No sobrescribir consentimiento guardado sin acción del usuario.
        settings['cloud_telemetry_consent'] = False
        settings['token_base_url'] = '' 
    try:
        settings['timeout_seconds'] = max(5, min(120, int(settings.get('timeout_seconds') or DEFAULT_TIMEOUT)))
    except Exception:
        settings['timeout_seconds'] = DEFAULT_TIMEOUT
    return settings


def save_ai_settings(values: Dict[str, Any]) -> Dict[str, Any]:
    current = load_ai_settings()
    if 'local_groq_bridge' in values:
        current['local_groq_bridge'] = values['local_groq_bridge'] is True
    if 'local_compatible_bridge' in values:
        current['local_compatible_bridge'] = values['local_compatible_bridge'] is True
    if 'base_url' in values:
        candidate = _allowed_base_url(values.get('base_url'), allow_local_groq_bridge=current['local_groq_bridge'],
            allow_local_compatible_bridge=current['local_compatible_bridge'])
        if candidate != current.get('base_url'):
            current['cloud_telemetry_consent'] = False
            current['token_base_url'] = ''
            current['consented_upstream'] = ''
            # Nunca reutilizar credenciales de otro servidor (best effort).
            delete_secret(TOKEN_NAME)
            delete_secret(ENROLLMENT_NAME)
        current['base_url'] = candidate
        if candidate != LOCAL_GROQ_BRIDGE_URL:
            current['local_groq_bridge'] = False
        if candidate != LOCAL_COMPAT_BRIDGE_URL:
            current['local_compatible_bridge'] = False
    elif ((not current['local_groq_bridge'] and current['base_url'] == LOCAL_GROQ_BRIDGE_URL) or
          (not current['local_compatible_bridge'] and current['base_url'] == LOCAL_COMPAT_BRIDGE_URL)):
        current['base_url'] = ''
        current['cloud_telemetry_consent'] = False
    if current['base_url'] == LOCAL_COMPAT_BRIDGE_URL:
        actual = provider_identity()
        if actual != current.get('consented_upstream'):
            current['cloud_telemetry_consent'] = False
            current['token_base_url'] = ''
            delete_secret(TOKEN_NAME)
            delete_secret(ENROLLMENT_NAME)
            current['consented_upstream'] = ''
    if 'cloud_telemetry_consent' in values:
        allowed = values['cloud_telemetry_consent'] is True
        if current['base_url'] == LOCAL_COMPAT_BRIDGE_URL:
            allowed = allowed and bool(provider_identity())
            current['consented_upstream'] = provider_identity() if allowed else ''
        current['cloud_telemetry_consent'] = allowed
    if 'token_base_url' in values:
        candidate = _safe_text(values['token_base_url'])
        current['token_base_url'] = candidate if candidate == current.get('base_url') else ''
    if 'timeout_seconds' in values:
        try:
            current['timeout_seconds'] = max(5, min(120, int(values['timeout_seconds'])))
        except Exception:
            pass
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = SETTINGS_PATH.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(tmp, SETTINGS_PATH)
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


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _active_compatible_bridge_matches(settings: Dict[str, Any]) -> bool:
    """Preflight sin secretos ni sensores; impide el envío a un puente stale.

    Si el usuario cambia de modelo/host y no reinicia el puente 8766, no se
    transmiten ni preguntas ni datos al upstream anterior.
    """
    if settings.get('base_url') != LOCAL_COMPAT_BRIDGE_URL:
        return True
    identity = provider_identity()
    if not identity or settings.get('consented_upstream') != identity:
        return False
    try:
        req = urllib.request.Request(LOCAL_COMPAT_BRIDGE_URL + '/v1/status',
                headers={'Accept': 'application/json', 'User-Agent': f'CorePulse/{VERSION}'}, method='GET')
        opener = urllib.request.build_opener(_NoRedirect, urllib.request.ProxyHandler({}))
        with opener.open(req, timeout=STATUS_TIMEOUT) as response:
            value = json.loads(response.read(16 * 1024).decode('utf-8'))
        return bool(isinstance(value, dict) and value.get('ok') is True and
                    value.get('model_provider') == 'openai_compatible' and
                    value.get('model_binding') == identity)
    except Exception:
        return False


def _request(method: str, path: str, *, payload: Optional[dict] = None, token: Optional[str] = None, settings: Optional[dict] = None, timeout_seconds: Optional[float] = None, enrollment: Optional[str] = None) -> Dict[str, Any]:
    settings = settings or load_ai_settings()
    gate = _cloud_gate(settings)
    if not gate['ok']:
        return gate
    if path != '/v1/status' and not _active_compatible_bridge_matches(settings):
        return {'ok': False, 'state': 'CLOUD_UPSTREAM_MISMATCH',
                'error': 'El puente alternativo no coincide con el modelo autorizado. Reinícialo.'}
    url = settings['base_url'] + path
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode('utf-8')
    headers = {'Accept': 'application/json', 'User-Agent': f'CorePulse/{VERSION}'}
    if data is not None:
        headers['Content-Type'] = 'application/json; charset=utf-8'
    if token:
        headers['Authorization'] = f'Bearer {token}'
    if enrollment and path == '/v1/register':
        headers['X-CorePulse-Enrollment'] = enrollment
    req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        # No seguir redirecciones: evita fuga de credenciales a otro destino o HTTP.
        opener = urllib.request.build_opener(_NoRedirect, urllib.request.ProxyHandler({}) if (settings.get('local_groq_bridge') or settings.get('local_compatible_bridge')) else urllib.request.ProxyHandler())
        with opener.open(req, timeout=float(timeout_seconds if timeout_seconds is not None else settings['timeout_seconds'])) as response:
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
    gate = _cloud_gate(settings)
    if not gate['ok']:
        return gate
    stored = load_ai_settings()
    if (stored.get('base_url') == settings.get('base_url') and
            stored.get('token_base_url') == settings.get('base_url')):
        token = read_secret(TOKEN_NAME)
        if token:
            return {'ok': True, 'token': token, 'registered': True}
    enrollment = read_secret(ENROLLMENT_NAME)
    if not enrollment:
        return {'ok': False, 'state': 'CLOUD_AUTH_REQUIRED',
                'error': 'Introduce un código de vinculación temporal creado en el servidor.'}
    payload = {
        'installation_id': _installation_id(),
        'client_version': VERSION,
        'platform': 'Windows',
        'python': platform.python_version(),
    }
    result = _request('POST', '/v1/register', payload=payload, settings=settings,
                      timeout_seconds=REGISTRATION_TIMEOUT, enrollment=enrollment)
    token = _safe_text(result.get('token')) if result.get('ok') else ''
    if not token:
        # /v1/register devuelve 403 si el código de un solo uso no fue aceptado.
        # Ese resultado NO significa que se haya revocado un token ya vinculado.
        if str(result.get('error') or '').startswith('HTTP 403:'):
            return {'ok': False, 'state': 'CLOUD_ENROLLMENT_REJECTED',
                    'error': ('Código de vinculación no aceptado: puede estar mal escrito, '
                              'caducado o ya utilizado. Crea un código nuevo e inténtalo otra vez.')}
        return {'ok': False, 'state': 'CLOUD_AUTH_ERROR',
                'error': result.get('error') or 'El servidor no autorizó la instalación.'}
    if save_secret(TOKEN_NAME, token):
        save_ai_settings({'token_base_url': settings['base_url']})
        # El código de vinculación es de un solo uso y no debe permanecer almacenado.
        delete_secret(ENROLLMENT_NAME)
        return {'ok': True, 'token': token, 'registered': True}
    if os.name != 'nt':
        return {'ok': True, 'token': token, 'registered': True, 'volatile': True}
    return {'ok': False, 'state': 'CLOUD_CREDENTIAL_ERROR',
            'error': 'No se pudo guardar la credencial en Windows Credential Manager.'}


def pairing_status(settings: Optional[dict] = None) -> Dict[str, Any]:
    """Comprueba la vinculacion con el puente real, no solo un token local."""
    settings = settings or load_ai_settings()
    gate = _cloud_gate(settings)
    if not gate['ok']:
        return gate
    stored = load_ai_settings()
    if (stored.get('base_url') != settings.get('base_url') or
            stored.get('token_base_url') != settings.get('base_url')):
        return {'ok': False, 'state': 'CLOUD_PAIRING_REQUIRED',
                'error': 'Este servidor requiere vincular el equipo.'}
    token = read_secret(TOKEN_NAME)
    if not token:
        return {'ok': False, 'state': 'CLOUD_PAIRING_REQUIRED',
                'error': 'No hay vinculación vigente para este servidor.'}
    result = _request('GET', '/v1/session', token=token, settings=settings,
                      timeout_seconds=STATUS_TIMEOUT)
    if result.get('ok') and result.get('paired') is True:
        return {'ok': True, 'state': 'CLOUD_PAIRED'}
    if _http_unauthorized(result):
        delete_secret(TOKEN_NAME)
        return {'ok': False, 'state': 'CLOUD_PAIRING_REQUIRED',
                'error': 'El puente no reconoce esta vinculación. Crea un código y vuelve a vincular.'}
    return {'ok': False, 'state': 'CLOUD_PAIRING_UNCONFIRMED',
            'error': 'No se pudo verificar la vinculación. Revisa la conexión y vuelve a intentar.'}


def _http_unauthorized(result: Dict[str, Any]) -> bool:
    # Evitar coincidencias accidentales (p. ej. error 1401) con el texto '401'.
    return bool(re.match(r'^HTTP\s+401(?:\s|:|$)', str(result.get('error') or '')))


def service_status(settings: Optional[dict] = None) -> Dict[str, Any]:
    settings = settings or load_ai_settings()
    gate = _cloud_gate(settings)
    if not gate['ok']:
        return gate
    result = _request('GET', '/v1/status', settings=settings, timeout_seconds=STATUS_TIMEOUT)
    if not result.get('ok'):
        return {'ok': False, 'state': 'OFFLINE', 'base_url': settings['base_url'], 'error': result.get('error')}
    if settings.get('base_url') == LOCAL_COMPAT_BRIDGE_URL and (
        result.get('model_binding') != provider_identity() or
        result.get('model_provider') != 'openai_compatible'):
        return {'ok': False, 'state': 'CLOUD_UPSTREAM_MISMATCH',
                'error': 'Puente alternativo distinto del modelo autorizado. Reinicia el puente.'}
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
    """Produce evidencia mínima y una barrera determinista contra inferencias de la IA."""
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
            'health_percent': _finite(item.get('health') if item.get('health') is not None else item.get('health_percent')),
            'temperature_c': _finite(item.get('temperature') or item.get('temperature_c')),
            'total_space_gb': _finite(item.get('total_space_gb') or item.get('size_gb') or item.get('total_gb')),
        })
    reasons = [_safe_text(x)[:180] for x in list(health.get('reasons') or [])[:8] if _safe_text(x)]
    reasons_norm = ' '.join(reasons).lower()
    health_severity = _safe_text(health.get('severity') or health.get('state')).upper()
    classified_attention = health_severity in {'ATTENTION', 'ELEVATED', 'WARNING', 'WARN', 'CRITICAL', 'ERROR'}
    attention = []
    thermal_alerts = []
    # V395: un número o una mención textual no crean una alerta. Sólo usamos
    # razones cuando CorePulse ya clasificó la condición como atención/alerta.
    if classified_attention and any(x in reasons_norm for x in ('cpu', 'procesador')):
        attention.append('CPU')
        if any(x in reasons_norm for x in ('temperatura', 'térmic', 'termic', 'throttl')):
            thermal_alerts.append('CPU')
    if classified_attention and any(x in reasons_norm for x in ('gpu', 'gráfica', 'grafica')):
        attention.append('GPU')
        if any(x in reasons_norm for x in ('temperatura', 'térmic', 'termic', 'throttl')):
            thermal_alerts.append('GPU')
    if classified_attention and any(x in reasons_norm for x in ('ram', 'memoria')):
        attention.append('RAM')
    if classified_attention and any(x in reasons_norm for x in ('ssd', 'disco', 'almacenamiento', 'smart')):
        attention.append('ALMACENAMIENTO')
    ram_usage = _finite(telemetry.get('ram_usage'))
    ram_usage_state = 'HIGH_USAGE' if ram_usage is not None and ram_usage >= 90 else 'ELEVATED_USAGE' if ram_usage is not None and ram_usage >= 85 else 'NORMAL_SAMPLE' if ram_usage is not None else 'N/A'
    return {
        'policy': 'REAL_OR_NA',
        'current_year': datetime.now().year,
        'health': {
            'score': _finite(health.get('score')),
            'status': _safe_text(health.get('status') or health.get('state'))[:80] or None,
            'severity': _safe_text(health.get('severity') or health.get('state'))[:32] or None,
            'reasons': reasons,
        },
        'decision': {
            'attention_areas': list(dict.fromkeys(attention)),
            'thermal_alerts': list(dict.fromkeys(thermal_alerts)),
            'ram_usage_state': ram_usage_state,
            'ram_usage_state_is_not_a_hardware_fault': True,
            'raw_temperature_numbers_are_not_authorized_for_ai_reclassification': True,
        },
        'cpu': {
            'name': _safe_text(telemetry.get('cpu_name'))[:120] or None,
            'usage_percent': _finite(telemetry.get('cpu_usage')),
            'temperature_c': _finite(telemetry.get('cpu_temp')),
            'frequency_ghz': _finite(telemetry.get('cpu_ghz')),
        },
        'ram': {
            'usage_percent': ram_usage,
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
        return {'ok': False, 'error': reg.get('error'), 'state': reg.get('state') or 'UNAVAILABLE'}
    payload = {'context': context, 'question': _safe_text(question)[:1200]}
    request_timeout = max(float(settings.get('timeout_seconds') or DEFAULT_TIMEOUT), float(DEFAULT_TIMEOUT))
    result = _request('POST', '/v1/analyze', payload=payload, token=reg['token'], settings=settings, timeout_seconds=request_timeout)
    if result.get('ok'):
        return result
    if _http_unauthorized(result):
        delete_secret(TOKEN_NAME)
        return {'ok': False, 'state': 'CLOUD_PAIRING_REQUIRED',
                'error': 'El puente no reconoce esta vinculación. Crea un código temporal y pulsa Vincular equipo.'}
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
        return {'ok': False, 'error': reg.get('error'), 'state': reg.get('state') or 'UNAVAILABLE'}
    payload = {'context': context, 'question': question, 'history': _clean_chat_history(history)}
    request_timeout = max(float(settings.get('timeout_seconds') or DEFAULT_TIMEOUT), float(DEFAULT_TIMEOUT))
    result = _request('POST', '/v1/chat', payload=payload, token=reg['token'], settings=settings, timeout_seconds=request_timeout)
    if result.get('ok'):
        return result
    if _http_unauthorized(result):
        delete_secret(TOKEN_NAME)
        return {'ok': False, 'state': 'CLOUD_PAIRING_REQUIRED',
                'error': 'El puente no reconoce esta vinculación. Crea un código temporal y pulsa Vincular equipo.'}
    return result


__all__ = [
    'DEFAULT_BASE_URL', 'LOCAL_GROQ_BRIDGE_URL', 'load_ai_settings', 'save_ai_settings', 'service_status',
    'ensure_registration', 'pairing_status', 'build_runtime_context', 'analyze_context', 'chat_context',
]
