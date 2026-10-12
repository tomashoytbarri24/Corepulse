"""Búsqueda opcional de tutoriales específicos para planes de acción CorePulse.

No inventa enlaces. Un URL directo sólo se publica como VERIFIED_EXACT cuando el
título devuelto por YouTube coincide con el modelo objetivo y la intención del
procedimiento. Si no se puede verificar, se entrega únicamente una búsqueda
preparada para que el usuario elija conscientemente.
"""
from __future__ import annotations

import html as _html
import json
import re
import unicodedata
import urllib.parse
import urllib.request
from typing import Any

YOUTUBE_SEARCH = 'https://www.youtube.com/results?search_query='


def _norm(value: Any) -> str:
    raw = unicodedata.normalize('NFD', str(value or '').lower())
    raw = ''.join(ch for ch in raw if unicodedata.category(ch) != 'Mn')
    return re.sub(r'[^a-z0-9]+', ' ', raw).strip()


def _tokens(value: Any) -> list[str]:
    stop = {'laptop','notebook','desktop','pc','computer','series','model','the','and','para','como','how','to'}
    return [x for x in _norm(value).split() if len(x) >= 3 and x not in stop]


def build_query(request: dict, inventory: dict) -> tuple[str, str]:
    request = request if isinstance(request, dict) else {}
    device = inventory.get('device') if isinstance(inventory.get('device'), dict) else {}
    target = str(request.get('target') or device.get('display_model') or device.get('support_target') or device.get('model') or '').strip()
    component = str(request.get('component') or '').strip()
    intent = str(request.get('intent') or '').strip().lower()
    phrases = {
        'thermal_service_cpu': 'disassembly clean fan thermal paste CPU',
        'thermal_service_gpu': 'disassembly clean fan thermal paste GPU',
        'ram_upgrade': 'RAM upgrade install memory',
        'ssd_upgrade': 'SSD upgrade install storage',
        'ssd_replace': 'SSD replacement install clone',
    }
    action = phrases.get(intent, 'repair upgrade tutorial')
    query = ' '.join(x for x in (target, component, action, 'tutorial') if x).strip()
    return query, target


def _decode_title(value: str) -> str:
    value = _html.unescape(value or '')
    try:
        return json.loads('"' + value.replace('"', '\\"') + '"')
    except Exception:
        return value.replace('\\u0026', '&').replace('\\n', ' ')


def _candidates(page: str) -> list[tuple[str, str]]:
    out = []
    seen = set()
    # YouTube incluye videoRenderer con videoId y title dentro de ytInitialData.
    pattern = re.compile(r'"videoRenderer":\{"videoId":"([A-Za-z0-9_-]{11})"(?:(?!"videoRenderer").){0,9000}?"title":\{"runs":\[\{"text":"((?:\\.|[^"\\])*)"', re.S)
    for video_id, raw_title in pattern.findall(page or ''):
        if video_id in seen:
            continue
        seen.add(video_id)
        out.append((video_id, _decode_title(raw_title)))
        if len(out) >= 12:
            break
    return out


def _score(title: str, target: str, intent: str) -> tuple[int, bool, bool]:
    nt = _norm(title)
    target_tokens = _tokens(target)
    matched = sum(1 for token in target_tokens if token in nt)
    target_ok = bool(target_tokens and matched >= min(2, len(target_tokens)))
    intent_words = {
        'thermal_service_cpu': ('thermal','paste','repaste','disassembly','clean','fan','cpu'),
        'thermal_service_gpu': ('thermal','paste','repaste','disassembly','clean','fan','gpu'),
        'ram_upgrade': ('ram','memory','upgrade','install'),
        'ssd_upgrade': ('ssd','m2','nvme','upgrade','install'),
        'ssd_replace': ('ssd','m2','nvme','replace','replacement','install'),
    }.get(intent, ('tutorial','repair','upgrade'))
    action_matches = sum(1 for word in intent_words if word in nt)
    action_ok = action_matches >= 2
    score = matched * 4 + action_matches * 2
    return score, target_ok, action_ok


def find_tutorial(request: dict, inventory: dict, *, timeout: float = 6.0) -> dict:
    query, target = build_query(request, inventory)
    if not query:
        return {'status': 'UNAVAILABLE', 'url': None, 'search_url': None, 'title': None, 'query': '', 'reason': 'No hay identidad suficiente para construir una búsqueda específica.'}
    search_url = YOUTUBE_SEARCH + urllib.parse.quote_plus(query)
    if not target or _norm(target) in {'na','n a','unknown','equipo detectado'}:
        return {'status': 'SEARCH_ONLY', 'url': None, 'search_url': search_url, 'title': None, 'query': query, 'reason': 'El modelo exacto del equipo no está disponible; CorePulse no selecciona un video genérico como exacto.'}
    req = urllib.request.Request(search_url, headers={'User-Agent': 'Mozilla/5.0 CorePulse/1.0', 'Accept-Language': 'es-ES,es;q=0.9,en;q=0.7'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            page = response.read().decode('utf-8', errors='replace')
    except Exception as exc:
        return {'status': 'SEARCH_ONLY', 'url': None, 'search_url': search_url, 'title': None, 'query': query, 'reason': f'No se pudo verificar un video exacto en línea ({type(exc).__name__}).'}
    intent = str((request or {}).get('intent') or '').strip().lower()
    ranked = []
    for video_id, title in _candidates(page):
        score, target_ok, action_ok = _score(title, target, intent)
        ranked.append((score, target_ok, action_ok, video_id, title))
    ranked.sort(reverse=True, key=lambda x: x[0])
    for score, target_ok, action_ok, video_id, title in ranked:
        if score >= 8 and target_ok and action_ok:
            return {
                'status': 'VERIFIED_EXACT',
                'url': f'https://www.youtube.com/watch?v={video_id}',
                'search_url': search_url,
                'title': title,
                'query': query,
                'verification': 'Coincidencia de modelo objetivo + intención del procedimiento en un resultado de YouTube.',
            }
    return {'status': 'SEARCH_ONLY', 'url': None, 'search_url': search_url, 'title': None, 'query': query, 'reason': 'No apareció un resultado con coincidencia suficientemente fuerte de modelo y procedimiento; no se inventó un enlace exacto.'}


def enrich_plans_with_tutorials(plans: list[dict], inventory: dict, *, max_lookups: int = 4, timeout: float = 6.0, allow_network: bool = False) -> list[dict]:
    """Por defecto no conecta a YouTube ni transmite el modelo del computador.

    Sólo una autorización explícita independiente puede activar búsquedas de red.
    CorePulse AI Cloud V461 llama siempre con allow_network=False.
    """
    out = []
    lookups = 0
    for plan in list(plans or []):
        if not isinstance(plan, dict):
            continue
        row = dict(plan)
        request = row.pop('tutorial_request', None)
        if isinstance(request, dict):
            if not allow_network:
                query, _target = build_query(request, inventory)
                row['tutorial'] = {
                    'status': 'SEARCH_ONLY' if query else 'UNAVAILABLE',
                    'url': None,
                    'search_url': (YOUTUBE_SEARCH + urllib.parse.quote_plus(query)) if query else None,
                    'title': None,
                    'query': query,
                    'reason': 'Búsqueda preparada localmente. CorePulse no contactó YouTube ni verificó un video exacto.',
                }
            elif lookups < max_lookups:
                row['tutorial'] = find_tutorial(request, inventory, timeout=timeout)
                lookups += 1
            else:
                query, _target = build_query(request, inventory)
                row['tutorial'] = {'status': 'SEARCH_ONLY', 'url': None, 'search_url': YOUTUBE_SEARCH + urllib.parse.quote_plus(query), 'title': None, 'query': query, 'reason': 'Límite de búsquedas por diagnóstico alcanzado.'}
        out.append(row)
    return out


__all__ = ['build_query', 'find_tutorial', 'enrich_plans_with_tutorials']
