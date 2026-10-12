"""V461: verificación determinista *posterior* al LLM.

No sustituye una revisión técnica ni puede garantizar que todo el lenguaje natural
sea correcto. Falla de manera conservadora en las afirmaciones cuantificables
que la evidencia de CorePulse no respalda. Nunca ejecuta comandos en Windows.
"""
from __future__ import annotations

import math
import re
import unicodedata
from typing import Any
from .educational_guide import educational_intent

POLICY_VERSION = '474.1'
_NUM_WITH_UNIT = re.compile(
    r'(?<![\w])(?P<num>\d{1,7}(?:[.,]\d{1,3})?)\s*'
    r'(?P<unit>°\s*C|grados?(?:\s+celsius)?|%|GHz|GB|FPS|MB/s|GB/s)(?![a-zA-Z0-9])',
    re.IGNORECASE,
)
_URL = re.compile(r'https?://[^\s<>"\')\]]+', re.IGNORECASE)
_TEMP_NO_UNIT = re.compile(
    r'\btemperatura\s+(?:de\s+(?:la|el)\s+)?(?:cpu|gpu|procesador|grafica)?\s*[:=]\s*\d+(?:[.,]\d+)?\b(?!\s*°)',
    re.IGNORECASE,
)
_UNVERIFIED_HEALTH = re.compile(
    r'\b(?:temperatura\s+(?:muy\s+)?(?:alta|critica)|sobrecalentamiento|'
    r'se\s+esta\s+sobrecalentando|throttling\s+(?:confirmado|detectado))\b',
    re.IGNORECASE,
)
_EXECUTED = re.compile(
    r'\b(?:ya\s+|he\s+|hemos\s+|se\s+ha\s+|fue\s+|han\s+)?'
    r'(?:instalado|desinstalado|actualizado|reparado|formateado|modificado|'
    r'configurado|aplicado|reiniciado)\s+(?:windows|el\s+(?:driver|controlador|sistema|equipo|pc)|'
    r'la\s+(?:bios|configuracion))\b',
    re.IGNORECASE,
)
_CONFIRMED_FAULT = re.compile(
    r'\b(?:falla\s+(?:fisica\s+)?confirmada|defecto\s+fisico\s+confirmado|'
    r'(?:cpu|gpu|ssd|disco|ram|procesador)\s+(?:esta\s+)?(?:danad[oa]|averiad[oa]|defectuos[oa]))\b',
    re.IGNORECASE,
)


def _normalize(s: str) -> str:
    src = unicodedata.normalize('NFKD', str(s or '').lower())
    return ''.join(c for c in src if unicodedata.category(c) != 'Mn')


def _valid(v: Any) -> float | None:
    try:
        if isinstance(v, bool) or v is None:
            return None
        x = float(v)
        return x if math.isfinite(x) else None
    except (ValueError, TypeError, OverflowError):
        return None


def _approx(observed: float, stated: float, literal: str) -> bool:
    # Por ejemplo, 89.64 de sensor puede aparecer como 89.6 o 90 redondeado.
    digits = len(literal.split('.')[-1].split(',')[-1]) if '.' in literal or ',' in literal else 0
    return abs(observed - stated) <= 0.5 * (10 ** -digits) + 1e-6


def _values(ctx: dict, unit: str) -> dict[str, list[float]]:
    cpu = ctx.get('cpu') or {}; gpu = ctx.get('gpu') or {}; ram = ctx.get('ram') or {}
    disks = ctx.get('storage') or []; health = ctx.get('health') or {}
    result: dict[str, list[float]] = {}
    def add(label: str, v: Any):
        n = _valid(v)
        if n is not None:
            result.setdefault(label, []).append(n)

    if unit == 'temp':
        add('cpu', cpu.get('temperature_c'))
        add('gpu', gpu.get('temperature_c'))
        for d in disks:
            add('storage', d.get('temperature_c'))
    elif unit == 'percent':
        add('cpu', cpu.get('usage_percent'))
        add('gpu', gpu.get('usage_percent'))
        add('ram', ram.get('usage_percent'))
        add('health', health.get('score'))
        for d in disks:
            add('storage', d.get('used_percent'))
            add('storage_usage', d.get('used_percent'))
            add('storage_health', d.get('health_percent'))
            add('storage', d.get('health_percent'))
    elif unit == 'ghz':
        add('cpu', cpu.get('frequency_ghz'))
    elif unit == 'gb':
        add('ram', ram.get('used_gb'))
        add('ram_used', ram.get('used_gb'))
        add('ram', ram.get('total_gb'))
        add('ram_total', ram.get('total_gb'))
        used, total = _valid(ram.get('used_gb')), _valid(ram.get('total_gb'))
        if used is not None and total is not None and 0 <= used <= total:
            add('ram', total - used)  # Cálculo simple autorizado, no telemetría inventada.
            add('ram_free', total - used)
        add('gpu', gpu.get('vram_gb'))
        for d in disks:
            add('storage', d.get('total_space_gb'))
    return result


def _component_near(text: str, start: int, end: int, unit: str) -> str | None:
    # Prioridad: etiqueta más cercana antes de la cifra, en la misma cláusula.
    # Luego una etiqueta a su derecha ("96 °C en CPU").
    before = _normalize(text[max(0, start - 90):start])
    after = _normalize(text[end:min(len(text), end + 35)])
    labels = {
        'cpu': r'\b(?:cpu|procesador)\b',
        'gpu': r'\b(?:gpu|grafica|vram)\b',
        'ram': r'\b(?:ram|memoria)\b',
        'storage': r'\b(?:ssd|hdd|disco|almacenamiento|smart)\b',
        'health': r'\b(?:salud\s+(?:global|del\s+sistema)|health\s+score)\b',
    }
    # Limitar el alcance al separador más reciente; puntos decimales no son separadores.
    before = re.split(r'[;\n|·]|(?<!\d)\.(?!\d)', before)[-1]
    hits = [(m.end(), label) for label, pat in labels.items() for m in re.finditer(pat, before)]
    if hits:
        comp = max(hits)[1]
    else:
        hits_right = [(m.start(), label) for label, pat in labels.items() for m in re.finditer(pat, after)]
        comp = min(hits_right)[1] if hits_right else None
    if comp == 'storage' and unit == 'percent':
        if re.search(r'\b(?:smart|salud|vida\s+util|desgaste)\b', before):
            return 'storage_health'
        if re.search(r'\b(?:ocupacion|usado|usada|utilizado|uso)\b', before):
            return 'storage_usage'
    if comp == 'ram' and unit == 'gb':
        if re.search(r'\b(?:libre|disponible|restante|restan)\b', before):
            return 'ram_free'
        if re.search(r'\b(?:usad[ao]|ocupad[ao]|consumid[ao])\b', before):
            return 'ram_used'
        if re.search(r'\b(?:total|instalad[ao]|capacidad)\b', before):
            return 'ram_total'
    return comp


def _unit(name: str) -> str:
    key = _normalize(name).replace(' ', '')
    if 'grado' in key or '°c' in key:
        return 'temp'
    if key == '%':
        return 'percent'
    if key == 'ghz':
        return 'ghz'
    if key == 'gb':
        return 'gb'
    return 'fps' if key == 'fps' else 'throughput'


def _approved_links(ctx: dict) -> dict[str, str]:
    approved = {}
    ass = ctx.get('deterministic_assessment') or {}
    for item in ass.get('problem_recommendations') or []:
        tutorial = item.get('tutorial') or {}
        status = tutorial.get('status')
        if status == 'VERIFIED_EXACT' and str(tutorial.get('url') or '').startswith('https://'):
            approved[tutorial['url'].rstrip('.,')] = 'verified'
        if status == 'SEARCH_ONLY' and str(tutorial.get('search_url') or '').startswith('https://'):
            approved[tutorial['search_url'].rstrip('.,')] = 'search'
    return approved


def _educational_product_percentage(text: str, position: int, unit: str, question: str) -> bool:
    """Permite solamente una concentración de alcohol explícita en una guía educativa.

    Una concentración química no es un sensor; todos los porcentajes atribuidos
    a CPU/GPU/RAM/SSD o al equipo continúan exigiendo evidencia REAL_OR_NA.
    Este permiso NO alcanza temperaturas, FPS, memoria ni porcentajes genéricos.
    """
    if unit != 'percent' or not educational_intent(question):
        return False
    preceding = _normalize(text[max(0, position - 85):position])
    # La cifra debe pertenecer gramaticalmente al alcohol, no al equipo.
    return bool(re.search(
        r'\b(?:alcohol(?:\s+isopropilico|\s+etilico)?|'
        r'concentracion\s+de\s+alcohol)\s+(?:al|de|del)\s*$',
        preceding,
    ))


def validate_model_response(ctx: dict, text: str, *, question: str = '') -> dict:
    """Devuelve códigos estables (no el texto rechazado). Nunca corrige inventos con un LLM."""
    out = str(text or '').strip()
    failures: list[str] = []
    if not out or len(out) > 11000:
        failures.append('INVALID_MODEL_TEXT')
    normalized = _normalize(out)
    # No exponer variables internas como explicación de una petición educativa.
    if re.search(r'\b(?:problem_recommendations|deterministic_assessment|evidence_snapshot|hardware_relevance|telemetry_available)\b', normalized):
        failures.append('INTERNAL_IMPLEMENTATION_LEAK')
    if _EXECUTED.search(normalized) or re.search(
        r'\b(?:ya|he|hemos)\s+(?:ejecutado|cambiado|instalado|reiniciado|optimizado|aplicado)\b', normalized):
        failures.append('UNAUTHORIZED_ACTION_CLAIM')
    if _CONFIRMED_FAULT.search(normalized):
        failures.append('UNVERIFIED_HARDWARE_FAULT')
    if re.search(r'\b(?:ram|memoria)\b.{0,65}\b(?:falla\s+fisica|defecto\s+fisico|modulo\s+danado)\b', normalized):
        failures.append('RAM_USAGE_IS_NOT_HARDWARE_FAILURE')
    if re.search(r'\b(?:cpu|gpu|ram|ssd|disco|procesador)\b.{0,40}\b(?:esta|se\s+encuentra|funciona)\s+(?:perfect[oa]|optim[oa]|san[oa])\b', normalized):
        # Sin diagnóstico específico y verificable, una cifra no demuestra "salud perfecta".
        failures.append('UNVERIFIED_PERFECT_HEALTH')
    thermal = [str(x).upper() for x in ((ctx.get('decision') or {}).get('thermal_alerts') or [])]
    for match in _UNVERIFIED_HEALTH.finditer(normalized):
        comp = _component_near(normalized, match.start(), match.end(), 'temp')
        if (not thermal) or (comp and comp.upper() not in thermal):
            failures.append('UNVERIFIED_THERMAL_CLASSIFICATION')
    if _TEMP_NO_UNIT.search(normalized):
        failures.append('UNVERIFIABLE_TEMPERATURE')

    supported_links = _approved_links(ctx)
    for match in _URL.finditer(out):
        link = match.group().rstrip('.,;')
        origin = supported_links.get(link)
        if not origin:
            failures.append('UNVERIFIED_LINK')
        elif origin == 'search':
            near = _normalize(out[max(0, match.start()-110):match.start()])
            if not re.search(r'\b(?:busqueda|buscar|resultados\s+de\s+busqueda)\b', near):
                failures.append('SEARCH_PRESENTED_AS_EXACT')

    for m in _NUM_WITH_UNIT.finditer(out):
        literal = m.group('num')
        number = float(literal.replace(',', '.'))
        kind = _unit(m.group('unit'))
        if kind == 'fps':
            # V461 no recibe la fuente real de FPS; jamás afirmar FPS numéricos.
            failures.append('FPS_WITHOUT_REAL_MEASUREMENT')
            continue
        if kind == 'throughput':
            failures.append('UNVERIFIED_THROUGHPUT')
            continue
        if _educational_product_percentage(out, m.start(), kind, question):
            continue
        sources = _values(ctx, kind)
        comp = _component_near(out, m.start(), m.end(), kind)
        # Una etiqueta explícita NUNCA puede ser sustituida por una lectura de otro componente.
        if comp is not None:
            vals = sources.get(comp, [])
        else:
            vals = [x for v in sources.values() for x in v]
        if not any(_approx(x, number, literal) for x in vals):
            failures.append('UNSUPPORTED_' + kind.upper())

    assessment = ctx.get('deterministic_assessment') or {}
    relevance = assessment.get('hardware_relevance') or []
    unavailable = {_normalize(i.get('component_type') or '') for i in relevance
                   if str(i.get('classification') or '').upper() == 'NO_EVALUABLE'}
    if unavailable:
        for comp in ('cpu', 'gpu'):
            if comp in unavailable and re.search(
                rf'\b{comp}\b.{{0,45}}\b(?:obsolet[oa]|vigente|desactualizad[oa]|actualizad[oa]|no\s+vigente)\b', normalized):
                failures.append('UNVERIFIED_YEAR_CLASSIFICATION')

    flags = list(dict.fromkeys(failures))
    return {'allowed': not flags, 'codes': flags, 'policy_version': POLICY_VERSION}


def evidence_fields(ctx: dict) -> list[str]:
    """Índice pequeño de origen de datos, sin devolver información personal."""
    fields = []
    for comp in ('cpu', 'gpu', 'ram'):
        for key, val in (ctx.get(comp) or {}).items():
            if _valid(val) is not None:
                fields.append(f'{comp}.{key}')
    for idx, d in enumerate(ctx.get('storage') or []):
        for key in ('used_percent', 'health_percent', 'temperature_c', 'total_space_gb'):
            if _valid(d.get(key)) is not None:
                fields.append(f'storage[{idx}].{key}')
    if _valid((ctx.get('health') or {}).get('score')) is not None:
        fields.append('health.score')
    return fields[:45]
