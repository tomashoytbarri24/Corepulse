"""V476 · muestras efímeras de consulta para investigar variaciones.

Sólo recibe el contexto YA creado por CorePulse al pulsar Enviar. No usa
sensores, red, archivo ni temporizadores. No conserva datos entre ejecuciones.
"""
from __future__ import annotations
from datetime import datetime, timezone
import math

FIELDS = {
    'cpu': {'temperature_c': (0, 130), 'usage_percent': (0, 100)},
    'gpu': {'temperature_c': (0, 130), 'usage_percent': (0, 100)},
    'ram': {'usage_percent': (0, 100)},
}


def query_sample(context: dict) -> dict | None:
    """Devuelve sólo métricas autorizadas, sin nombre del equipo ni credenciales."""
    if not isinstance(context, dict):
        return None
    stamp = (context.get('evidence_snapshot') or {}).get('captured_at_utc')
    if not isinstance(stamp, str):
        return None
    try:
        dt = datetime.fromisoformat(stamp.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            return None
        stamp = dt.astimezone(timezone.utc).isoformat(timespec='seconds')
    except (ValueError, OverflowError):
        return None
    metrics = {}
    for section, keys in FIELDS.items():
        source = context.get(section)
        if not isinstance(source, dict):
            continue
        values = {}
        for key, (lo, hi) in keys.items():
            v = source.get(key)
            if isinstance(v, bool):
                continue
            try:
                n = float(v)
            except (ValueError, TypeError, OverflowError):
                continue
            if math.isfinite(n) and lo <= n <= hi:
                values[key] = round(n, 2)
        if values:
            metrics[section] = values
    if not metrics:
        return None
    decision = context.get('decision') if isinstance(context.get('decision'), dict) else {}
    declared_thermal = []
    for item in (decision.get('thermal_alerts') or []) if isinstance(decision.get('thermal_alerts'), list) else []:
        if isinstance(item, str) and item.upper().strip() in ('CPU', 'GPU'):
            declared_thermal.append(item.upper().strip())
    return {'captured_at_utc': stamp, 'metrics': metrics, 'source': 'COREPULSE_QUERY_SNAPSHOT',
            'reported_thermal_alerts': sorted(set(declared_thermal))}



def append_sample(previous: list, sample: dict | None, limit: int = 5) -> list:
    """Sin duplicar instantáneas del mismo segundo; conserva sólo las últimas."""
    items = [dict(x) for x in (previous or []) if isinstance(x, dict)]
    if sample is None:
        return items[-limit:]
    items = [x for x in items if x.get('captured_at_utc') != sample['captured_at_utc']]
    items.append(dict(sample))
    return items[-limit:]


__all__ = ['query_sample', 'append_sample']
