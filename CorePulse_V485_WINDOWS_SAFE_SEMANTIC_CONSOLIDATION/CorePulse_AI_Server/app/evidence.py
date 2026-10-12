from __future__ import annotations
import math
import unicodedata
from typing import Any
from .educational_guide import safe_educational_fallback
from .investigation_engine import sanitize_session_history


def _num(value: Any):
    if isinstance(value, bool):
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _text(value: Any, limit: int):
    value = str(value or '').strip()
    return value[:limit] or None


def _norm(value: str) -> str:
    raw = unicodedata.normalize('NFD', str(value or '').lower())
    return ''.join(ch for ch in raw if unicodedata.category(ch) != 'Mn').strip()


def sanitize_context(value: Any) -> dict:
    src = value if isinstance(value, dict) else {}
    health = src.get('health') if isinstance(src.get('health'), dict) else {}
    decision = src.get('decision') if isinstance(src.get('decision'), dict) else {}
    cpu = src.get('cpu') if isinstance(src.get('cpu'), dict) else {}
    ram = src.get('ram') if isinstance(src.get('ram'), dict) else {}
    gpu = src.get('gpu') if isinstance(src.get('gpu'), dict) else {}
    device = src.get('device') if isinstance(src.get('device'), dict) else {}
    assessment = src.get('deterministic_assessment') if isinstance(src.get('deterministic_assessment'), dict) else {}
    snapshot = src.get('evidence_snapshot') if isinstance(src.get('evidence_snapshot'), dict) else {}
    storage = src.get('storage') if isinstance(src.get('storage'), list) else []
    clean_storage = []
    for item in storage[:8]:
        if not isinstance(item, dict):
            continue
        clean_storage.append({
            'model': _text(item.get('model'), 120),
            'used_percent': _num(item.get('used_percent')),
            'health_percent': _num(item.get('health_percent')),
            'temperature_c': _num(item.get('temperature_c')),
            'total_space_gb': _num(item.get('total_space_gb')),
        })

    clean_relevance = []
    for item in list(assessment.get('hardware_relevance') or [])[:8]:
        if not isinstance(item, dict):
            continue
        axes = item.get('evidence_axes') if isinstance(item.get('evidence_axes'), dict) else {}
        clean_relevance.append({
            'component_type': _text(item.get('component_type'), 40),
            'detected_hardware': _text(item.get('detected_hardware'), 180),
            'classification': _text(item.get('classification'), 40),
            'confidence': _text(item.get('confidence'), 24),
            'reason': _text(item.get('reason'), 260),
            'evidence_axes': {
                key: (_num(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else _text(value, 80))
                for key, value in list(axes.items())[:12]
                if isinstance(value, (str, int, float)) and not isinstance(value, bool)
            },
        })
    clean_actions = []
    for item in list(assessment.get('problem_recommendations') or [])[:10]:
        if not isinstance(item, dict):
            continue
        tutorial = item.get('tutorial') if isinstance(item.get('tutorial'), dict) else {}
        corepulse_action = item.get('corepulse_action') if isinstance(item.get('corepulse_action'), dict) else {}
        clean_actions.append({
            'severity': _text(item.get('severity'), 32),
            'priority_level': _text(item.get('priority_level'), 48),
            'component_type': _text(item.get('component_type'), 48),
            'title': _text(item.get('title'), 140),
            'summary': _text(item.get('summary'), 300),
            'actions': [_text(x, 180) for x in list(item.get('actions') or [])[:5] if _text(x, 180)],
            'supplies': [_text(x, 140) for x in list(item.get('supplies') or [])[:6] if _text(x, 140)],
            'precautions': [_text(x, 160) for x in list(item.get('precautions') or [])[:5] if _text(x, 160)],
            'corepulse_action': {
                'id': _text(corepulse_action.get('id'), 64),
                'label': _text(corepulse_action.get('label'), 100),
            } if corepulse_action else None,
            'tutorial': {
                'status': _text(tutorial.get('status'), 32),
                'url': _text(tutorial.get('url'), 400),
                'search_url': _text(tutorial.get('search_url'), 500),
                'title': _text(tutorial.get('title'), 180),
                'query': _text(tutorial.get('query'), 260),
                'reason': _text(tutorial.get('reason'), 300),
            } if tutorial else None,
        })
    return {
        'policy': 'REAL_OR_NA',
        'observation_history': sanitize_session_history(src.get('observation_history')),
        'current_year': int(_num(src.get('current_year')) or 0) or None,
        'evidence_snapshot': {
            'captured_at_utc': _text(snapshot.get('captured_at_utc'), 64),
            'source': _text(snapshot.get('source'), 80),
            'policy': _text(snapshot.get('policy'), 100),
            'assessment_source': _text(snapshot.get('assessment_source'), 80),
            'telemetry_available': bool(snapshot.get('telemetry_available')),
            'storage_devices': int(_num(snapshot.get('storage_devices')) or 0),
        },
        'health': {
            'score': _num(health.get('score')),
            'status': _text(health.get('status'), 80),
            'severity': _text(health.get('severity'), 32),
            'reasons': [_text(x, 180) for x in list(health.get('reasons') or [])[:8] if _text(x, 180)],
        },
        'decision': {
            'attention_areas': [_text(x, 40) for x in list(decision.get('attention_areas') or [])[:8] if _text(x, 40)],
            'thermal_alerts': [_text(x, 40) for x in list(decision.get('thermal_alerts') or [])[:4] if _text(x, 40)],
            'ram_usage_state': _text(decision.get('ram_usage_state'), 32),
            'ram_usage_state_is_not_a_hardware_fault': bool(decision.get('ram_usage_state_is_not_a_hardware_fault', True)),
            'raw_temperature_numbers_are_not_authorized_for_ai_reclassification': bool(decision.get('raw_temperature_numbers_are_not_authorized_for_ai_reclassification', True)),
        },
        'device': {
            'form_factor': _text(device.get('form_factor'), 40),
            'manufacturer': _text(device.get('manufacturer'), 80),
            'model': _text(device.get('model'), 120),
            'display_model': _text(device.get('display_model'), 160),
            'motherboard': _text(device.get('motherboard'), 160),
        },
        'deterministic_assessment': {
            'current_year': int(_num(assessment.get('current_year')) or 0) or None,
            'baseline': {
                key: (_num(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else _text(value, 80))
                for key, value in list((assessment.get('baseline') if isinstance(assessment.get('baseline'), dict) else {}).items())[:12]
                if isinstance(value, (str, int, float)) and not isinstance(value, bool)
            },
            'attention_areas': [_text(x, 48) for x in list(assessment.get('attention_areas') or [])[:10] if _text(x, 48)],
            'hardware_relevance': clean_relevance,
            'problem_recommendations': clean_actions,
            'policy': _text(assessment.get('policy'), 120),
        },
        'cpu': {
            'name': _text(cpu.get('name'), 120),
            'usage_percent': _num(cpu.get('usage_percent')),
            'temperature_c': _num(cpu.get('temperature_c')),
            'frequency_ghz': _num(cpu.get('frequency_ghz')),
        },
        'ram': {
            'usage_percent': _num(ram.get('usage_percent')),
            'used_gb': _num(ram.get('used_gb')),
            'total_gb': _num(ram.get('total_gb')),
        },
        'gpu': {
            'name': _text(gpu.get('name'), 120),
            'usage_percent': _num(gpu.get('usage_percent')),
            'temperature_c': _num(gpu.get('temperature_c')),
            'vram_gb': _num(gpu.get('vram_gb')),
        },
        'storage': clean_storage,
    }


def _fmt(value, digits=1, suffix='') -> str:
    return 'N/A' if value is None else f'{float(value):.{digits}f}{suffix}'


def fallback_summary(ctx: dict) -> str:
    h = ctx['health']; cpu = ctx['cpu']; ram = ctx['ram']; gpu = ctx['gpu']; disks = ctx['storage']
    parts = []
    reasons = h.get('reasons') or []
    if reasons:
        parts.append('CorePulse detecta: ' + '; '.join(reasons) + '.')
    elif h.get('score') is not None:
        status = h.get('status') or 'sin clasificación textual'
        parts.append(f"Salud del sistema: {h['score']:.0f}% ({status}).")
    else:
        parts.append('CorePulse no tiene una puntuación global disponible en esta muestra.')

    evidence = []
    if cpu.get('usage_percent') is not None or cpu.get('temperature_c') is not None:
        evidence.append(f"CPU {_fmt(cpu.get('usage_percent'), 0, '% uso')} · {_fmt(cpu.get('temperature_c'), 1, ' °C')}")
    if gpu.get('usage_percent') is not None or gpu.get('temperature_c') is not None:
        evidence.append(f"GPU {_fmt(gpu.get('usage_percent'), 0, '% uso')} · {_fmt(gpu.get('temperature_c'), 1, ' °C')}")
    if ram.get('usage_percent') is not None:
        evidence.append(f"RAM {_fmt(ram.get('usage_percent'), 0, '% uso')}")
    if disks:
        d = disks[0]
        evidence.append(f"Almacenamiento {_fmt(d.get('used_percent'), 0, '% usado')} · SMART {_fmt(d.get('health_percent'), 0, '%')}")
    if evidence:
        parts.append('Lecturas disponibles: ' + ' | '.join(evidence) + '.')
    parts.append('El host generativo no está disponible; esta respuesta proviene del motor seguro de evidencia de CorePulse.')
    return ' '.join(parts)


def fallback_answer(ctx: dict, question: str) -> str:
    question = str(question or '').strip()
    q = _norm(question)
    if not q:
        return fallback_summary(ctx)

    if q in {'hola', 'hola!', 'buenas', 'buenos dias', 'buenas tardes', 'buenas noches', 'como estas', 'como estas?'}:
        return 'Hola. CorePulse AI está disponible en modo de evidencia segura. Puedes preguntarme por CPU, GPU, RAM, almacenamiento o temperaturas.'

    educational = safe_educational_fallback(question, ctx)
    if educational:
        return educational

    cpu = ctx['cpu']; gpu = ctx['gpu']; ram = ctx['ram']; disks = ctx['storage']

    if 'frecuencia' in q and ('cpu' in q or 'procesador' in q):
        value = cpu.get('frequency_ghz')
        if value is None:
            return 'Frecuencia actual de CPU: N/A. CorePulse no tiene una lectura válida de frecuencia en esta muestra.'
        extra = ''
        if cpu.get('usage_percent') is not None:
            extra = f" Uso actual: {cpu['usage_percent']:.0f}%."
        return f"Frecuencia actual de CPU: {value:.2f} GHz.{extra}"

    if 'ram' in q or 'memoria' in q:
        used = ram.get('used_gb'); total = ram.get('total_gb'); pct = ram.get('usage_percent')
        if used is None and total is None and pct is None:
            return 'RAM: N/A. CorePulse no tiene una lectura válida de memoria en esta muestra.'
        parts = [f"Uso de RAM: {_fmt(pct, 1, '%')}."]
        if used is not None and total is not None:
            available = max(0.0, total - used)
            parts.append(f"Memoria usada: {used:.1f} de {total:.1f} GB. Disponible calculada: {available:.1f} GB.")
        return ' '.join(parts)

    if any(k in q for k in ('ssd', 'disco', 'almacenamiento')):
        if not disks:
            return 'Almacenamiento: N/A. CorePulse no recibió una lectura de disco en esta muestra.'
        d = disks[0]
        parts = [f"Almacenamiento: {_fmt(d.get('used_percent'), 1, '% usado')}."]
        parts.append(f"Temperatura: {_fmt(d.get('temperature_c'), 1, ' °C')}.")
        if d.get('health_percent') is None:
            parts.append('Salud SMART: N/A; no puedo afirmar el estado de salud del SSD con esta muestra.')
        else:
            parts.append(f"Salud SMART reportada: {d['health_percent']:.0f}%.")
        return ' '.join(parts)

    if any(term in q for term in ('temperatura', 'temperaturas', 'caliente', 'calor', 'sobrecalent', 'termica', 'termico')):
        return (
            f"Temperatura CPU: {_fmt(cpu.get('temperature_c'), 1, ' °C')}. "
            f"Temperatura GPU: {_fmt(gpu.get('temperature_c'), 1, ' °C')}."
        )

    if 'gpu' in q or 'grafica' in q:
        return (
            f"GPU: {_fmt(gpu.get('usage_percent'), 1, '% uso')} · "
            f"{_fmt(gpu.get('temperature_c'), 1, ' °C')}."
        )

    if 'cpu' in q or 'procesador' in q:
        return (
            f"CPU: {_fmt(cpu.get('usage_percent'), 1, '% uso')} · "
            f"{_fmt(cpu.get('temperature_c'), 1, ' °C')} · "
            f"{_fmt(cpu.get('frequency_ghz'), 2, ' GHz')}."
        )

    return fallback_summary(ctx)
