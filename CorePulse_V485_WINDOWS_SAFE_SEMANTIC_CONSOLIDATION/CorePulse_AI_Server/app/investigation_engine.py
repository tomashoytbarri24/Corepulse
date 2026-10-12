"""V476 · investigación temporal acotada a lecturas de la sesión del chat.

El historial es declarado por el cliente, NO verificado por el servidor, y
NUNCA es autoridad para declarar nuevas alertas, daños o causalidad.
"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
import math

ENGINE_VERSION = '476.0'
MEASUREMENTS = {
    'cpu.temperature_c': ('°C', 0, 130),
    'cpu.usage_percent': ('%', 0, 100),
    'gpu.temperature_c': ('°C', 0, 130),
    'gpu.usage_percent': ('%', 0, 100),
    'ram.usage_percent': ('%', 0, 100),
}
MAX_HISTORY = 5


def _valid_stamp(raw):
    if not isinstance(raw, str) or len(raw) > 64:
        return None
    try:
        stamp = datetime.fromisoformat(raw.replace('Z', '+00:00'))
    except (ValueError, OverflowError):
        return None
    if stamp.tzinfo is None:
        return None
    utc = stamp.astimezone(timezone.utc)
    now = datetime.now(timezone.utc)
    if utc < now - timedelta(hours=24) or utc > now + timedelta(minutes=2):
        return None
    return utc


def _value(source, bounds):
    if isinstance(source, bool) or source is None:
        return None
    try:
        n = float(source)
    except (ValueError, TypeError, OverflowError):
        return None
    return round(n, 2) if math.isfinite(n) and bounds[1] <= n <= bounds[2] else None


def sanitize_session_history(raw):
    """Whitelist estricta: sin textos arbitrarios, IP, modelo, rutas o URLs."""
    if not isinstance(raw, list):
        return []
    result = {}
    for sample in raw[-MAX_HISTORY:]:
        if not isinstance(sample, dict) or sample.get('source') not in {'COREPULSE_QUERY_SNAPSHOT', 'CLIENT_REPORTED_SESSION_SAMPLE'}:
            continue
        stamp = _valid_stamp(sample.get('captured_at_utc'))
        if stamp is None:
            continue
        metrics = sample.get('metrics')
        if not isinstance(metrics, dict):
            continue
        clean = {}
        for key, bounds in MEASUREMENTS.items():
            section, field = key.split('.')
            value = _value((metrics.get(section) or {}).get(field) if isinstance(metrics.get(section), dict) else None, bounds)
            if value is not None:
                clean.setdefault(section, {})[field] = value
        if clean:
            alerts = sample.get('reported_thermal_alerts')
            thermal = sorted(set(str(x).upper().strip() for x in alerts
                                 if isinstance(x, str) and str(x).upper().strip() in {'CPU', 'GPU'})) if isinstance(alerts, list) else []
            result[stamp] = {'captured_at_utc': stamp.isoformat(timespec='seconds'),
                             'source': 'CLIENT_REPORTED_SESSION_SAMPLE', 'metrics': clean,
                             'reported_thermal_alerts': thermal}

    return [result[k] for k in sorted(result)][-MAX_HISTORY:]


def investigate_timeline(context):
    """Compara sólo lecturas repetidas con separación real, sin diagnóstico autónomo."""
    ctx = context if isinstance(context, dict) else {}
    rows = sanitize_session_history(ctx.get('observation_history'))
    now = ctx.get('evidence_snapshot') if isinstance(ctx.get('evidence_snapshot'), dict) else {}
    current = _valid_stamp(now.get('captured_at_utc'))
    output = {'engine_version': ENGINE_VERSION, 'source': 'CLIENT_REPORTED_CURRENT_CHAT_SESSION',
              'server_verified_sampling': False, 'status': 'INSUFFICIENT',
              'previous_samples': len(rows), 'comparisons': [], 'alert_correlations': [],
              'limitations': ['Lecturas previas declaradas por el cliente y no verificadas independientemente.',
                              'Sólo se comparan consultas de este chat; no hay monitoreo histórico continuo.',
                              'La variación no demuestra causalidad, daño físico ni alerta nueva.']}
    if current is None or not rows:
        return output
    prior = next((x for x in reversed(rows) if _valid_stamp(x['captured_at_utc']) < current - timedelta(seconds=14)), None)
    if prior is None:
        return output
    elapsed = int((current - _valid_stamp(prior['captured_at_utc'])).total_seconds())
    for name, bounds in MEASUREMENTS.items():
        section, field = name.split('.')
        old = _value((prior['metrics'].get(section) or {}).get(field), bounds)
        new = _value((ctx.get(section) or {}).get(field) if isinstance(ctx.get(section), dict) else None, bounds)
        if old is None or new is None:
            continue
        delta = round(new - old, 2)
        output['comparisons'].append({'metric': name, 'source_previous': 'observation_history',
            'source_current': name, 'previous': old, 'current': new, 'unit': bounds[0],
            'delta': delta, 'direction': ('SIN_CAMBIO' if delta == 0 else 'SUBE' if delta > 0 else 'BAJA'),
            'elapsed_seconds': elapsed, 'classification': 'VARIATION_ONLY'})
    declared_now = ctx.get('decision') if isinstance(ctx.get('decision'), dict) else {}
    current_alerts = {str(a).upper().strip() for a in (declared_now.get('thermal_alerts') or [])
                      if isinstance(a, str) and str(a).upper().strip() in {'CPU', 'GPU'}}
    older_alerts = set(prior.get('reported_thermal_alerts') or [])
    # Los estados de alerta son declaraciones originales, no se calculan a partir de °C.
    for component in ('CPU', 'GPU'):
        output['alert_correlations'].append({
            'component': component,
            'previous_declared': component in older_alerts,
            'current_declared': component in current_alerts,
            'source_previous': 'observation_history.reported_thermal_alerts',
            'source_current': 'decision.thermal_alerts',
            'classification': 'REPORTED_STATUS_ONLY',
        })
    if output['comparisons']:
        output['status'] = 'TWO_SNAPSHOTS_COMPARABLE'
    return output


def timeline_brief(info):
    if info.get('status') != 'TWO_SNAPSHOTS_COMPARABLE':
        return ('Historial temporal: aún no hay dos lecturas comparables de este chat '
                '(separadas al menos 15 segundos). No puedo confirmar una tendencia.')
    values = []
    for row in info['comparisons'][:5]:
        values.append(f"{row['metric']}: {row['previous']:g} a {row['current']:g} {row['unit']} "
                      f"(variación {row['delta']:+g} {row['unit']} en {row['elapsed_seconds']} s)")
    declared = [x['component'] for x in info.get('alert_correlations', [])
                if x['previous_declared'] and x['current_declared']]
    alert_note = (' CorePulse declaró alertas de ' + ', '.join(declared) + ' en ambas capturas.'
                  if declared else ' No se confirmó una alerta repetida en ambas capturas.')
    return ('Comparación entre consultas, no monitoreo continuo: ' + '; '.join(values) +
            '. Son variaciones observadas; no prueban la causa ni constituyen una alerta nueva.' + alert_note)



__all__ = ['sanitize_session_history','investigate_timeline','timeline_brief','ENGINE_VERSION']
