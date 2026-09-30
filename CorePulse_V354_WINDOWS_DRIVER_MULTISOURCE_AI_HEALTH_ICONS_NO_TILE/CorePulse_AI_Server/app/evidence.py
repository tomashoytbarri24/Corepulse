from __future__ import annotations
import math
from typing import Any


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


def sanitize_context(value: Any) -> dict:
    src = value if isinstance(value, dict) else {}
    health = src.get('health') if isinstance(src.get('health'), dict) else {}
    cpu = src.get('cpu') if isinstance(src.get('cpu'), dict) else {}
    ram = src.get('ram') if isinstance(src.get('ram'), dict) else {}
    gpu = src.get('gpu') if isinstance(src.get('gpu'), dict) else {}
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
        })
    return {
        'policy': 'REAL_OR_NA',
        'health': {
            'score': _num(health.get('score')),
            'status': _text(health.get('status'), 80),
            'severity': _text(health.get('severity'), 32),
            'reasons': [_text(x, 180) for x in list(health.get('reasons') or [])[:8] if _text(x, 180)],
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


def fallback_summary(ctx: dict) -> str:
    h = ctx['health']; cpu = ctx['cpu']; ram = ctx['ram']; gpu = ctx['gpu']; disks = ctx['storage']
    parts = []
    if h.get('score') is not None:
        status = h.get('status') or 'sin clasificación textual'
        parts.append(f"La salud del sistema es {h['score']:.0f}% ({status}).")
    else:
        parts.append('La salud del sistema no tiene una puntuación disponible en esta muestra.')
    reasons = h.get('reasons') or []
    if reasons:
        parts.append('Factores detectados por CorePulse: ' + '; '.join(reasons) + '.')
    if cpu.get('temperature_c') is not None:
        parts.append(f"CPU: {cpu['temperature_c']:.1f} °C y {cpu.get('usage_percent'):.1f}% de uso." if cpu.get('usage_percent') is not None else f"CPU: {cpu['temperature_c']:.1f} °C.")
    if ram.get('usage_percent') is not None:
        parts.append(f"RAM: {ram['usage_percent']:.1f}% en uso.")
    if gpu.get('temperature_c') is not None:
        parts.append(f"GPU: {gpu['temperature_c']:.1f} °C" + (f" y {gpu['usage_percent']:.1f}% de uso." if gpu.get('usage_percent') is not None else '.'))
    if disks:
        valid = [d for d in disks if d.get('health_percent') is not None]
        if valid:
            worst = min(valid, key=lambda d: d['health_percent'])
            parts.append(f"Almacenamiento: la salud SMART mínima reportada es {worst['health_percent']:.0f}%.")
    parts.append('El host generativo no está disponible; esta respuesta proviene únicamente del motor seguro de evidencia de CorePulse.')
    return ' '.join(parts)


def fallback_answer(ctx: dict, question: str) -> str:
    question = str(question or '').strip()
    if not question:
        return fallback_summary(ctx)
    if question.lower() in {'hola', 'hola!', 'buenas', 'buenos días', 'buenas tardes', 'buenas noches'}:
        return 'Hola. El servicio CorePulse AI está conectado, pero el host generativo todavía no está disponible. Puedo mostrar el resumen técnico seguro mientras se inicia el modelo.'
    return fallback_summary(ctx)
