"""Ayudantes puros de V467: fotografía N/A, preflight y vinculación sin fugas."""
from __future__ import annotations
import copy
from core.ai_client import ENROLLMENT_NAME, TOKEN_NAME
from core.ai_credentials import read_secret


def request_snapshot(telemetry, disks, health, diagnostic_result, agent_state) -> dict:
    """Copias de un instante; None y valores ausentes no se rellenan."""
    return {
        'telemetry': copy.deepcopy(telemetry) if isinstance(telemetry, dict) else {},
        'disks': copy.deepcopy(disks) if isinstance(disks, list) else [],
        'health': copy.deepcopy(health) if isinstance(health, dict) else {},
        'diagnostic_result': copy.deepcopy(diagnostic_result) if isinstance(diagnostic_result, dict) else {},
        'agent_state': copy.deepcopy(agent_state) if isinstance(agent_state, dict) else {},
    }


def paired_for_endpoint(settings: dict, *, allow_enrollment: bool = False) -> bool:
    """El token sólo se acepta cuando está asociado al servidor actual."""
    from core.ai_client import load_ai_settings
    stored = load_ai_settings()
    base = str(settings.get('base_url') or '')
    if (base and stored.get('base_url') == base and stored.get('token_base_url') == base
            and read_secret(TOKEN_NAME)):
        return True
    return bool(allow_enrollment and base and read_secret(ENROLLMENT_NAME))


def describe_preflight(gate: dict) -> str:
    return {
        'DISABLED': 'CorePulse AI está apagada. Actívala para conversar.',
        'CLOUD_NOT_CONFIGURED': 'Selecciona Groq, un modelo alternativo o un servidor CorePulse HTTPS.',
        'CLOUD_INVALID_ENDPOINT': 'El servidor no es válido. Usa HTTPS o un puente local autorizado desde los botones.',
        'CLOUD_CONSENT_REQUIRED': 'Autoriza el envío al servidor y proveedor antes de usar el chat.',
    }.get(str(gate.get('state') or ''), 'No se puede conectar: revisa la configuración de nube.')


def safe_youtube_search_from_reply(text: str) -> str | None:
    """Solo URLs de búsqueda, nunca vídeos arbitrarios ni dominios parecidos."""
    import re
    from urllib.parse import urlsplit, parse_qs
    for match in re.finditer(r'https://[^\s<>\"\']+', str(text or '')):
        raw = match.group().rstrip('.,;!')
        try:
            u = urlsplit(raw)
            params = parse_qs(u.query, strict_parsing=True)
            if (u.scheme == 'https' and u.hostname == 'www.youtube.com'
                    and u.port in (None, 443) and u.username is None
                    and u.password is None and u.path == '/results'
                    and not u.fragment and set(params) == {'search_query'}
                    and len(params['search_query']) == 1 and 3 <= len(params['search_query'][0]) <= 150
                    and len(raw) <= 330):
                return raw
        except (ValueError, TypeError):
            continue
    return None


def display_reply_without_raw_youtube_search(text: str) -> str:
    """Muestra el botón validado y no una URL de búsqueda extensa en la burbuja.

    No oculta ni altera URL de otros dominios o búsquedas no reconocidas.
    """
    original = str(text or '')
    url = safe_youtube_search_from_reply(original)
    if not url:
        return original
    import re
    return re.sub(r'\n{3,}', '\n\n', original.replace(url, '')).strip()
