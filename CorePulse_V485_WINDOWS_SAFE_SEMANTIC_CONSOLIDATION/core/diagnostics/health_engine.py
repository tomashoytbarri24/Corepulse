"""Calcula el estado técnico actual a partir de evidencia térmica y métricas certificadas."""
from __future__ import annotations
from core.version import VERSION_LABEL as VERSION

# Código refactorizado: nombres estables y documentación en español.
POLICY = 'REAL_SENSOR_SEVERITY_GUARD'


def _num(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        value = float(value)
    except Exception:
        return None
    if value != value or value in (float('inf'), float('-inf')):
        return None
    return value


def _quality_valid(meta):
    if not isinstance(meta, dict):
        return True
    q = str(meta.get('quality') or '').upper()
    return q in ('', 'VALID')


def _certified_metric_value(obj, key):
    if not isinstance(obj, dict):
        return None
    certs = obj.get('_certified_metrics')
    if isinstance(certs, dict):
        meta = certs.get(key)
        if isinstance(meta, dict) and _quality_valid(meta):
            v = _num(meta.get('value'))
            if v is not None:
                return v
    return _num(obj.get(key))


def _cpu_distance_to_tjmax(telemetry):
    if not isinstance(telemetry, dict):
        return None
    cpu = telemetry.get('_cpu')
    if isinstance(cpu, dict):
        for key in ('distance_to_tjmax_min_c', 'distance_to_tjmax_c', 'distance_to_tjmax'):
            v = _certified_metric_value(cpu, key)
            if v is not None:
                return v
    for key in ('cpu_distance_to_tjmax_min_c', 'cpu_distance_to_tjmax_c', 'distance_to_tjmax_min_c'):
        v = _num(telemetry.get(key))
        if v is not None:
            return v
    return None


def _cap_score(score, cap):
    return min(score, cap) if score is not None else None


RANK = {'NORMAL': 0, 'ELEVATED': 1, 'WARNING': 2, 'CRITICAL': 3, 'NO_EVALUABLE': -1}


def _raise_severity(current, candidate):
    current = str(current or 'NORMAL').upper()
    candidate = str(candidate or 'NORMAL').upper()
    return candidate if RANK.get(candidate, -1) > RANK.get(current, -1) else current


def _append_reason(reasons, text):
    text = str(text or '').strip()
    if text and text not in reasons:
        reasons.append(text)


def _disk_label(disk, index):
    if not isinstance(disk, dict):
        return f'Disco {index + 1}'
    for key in ('model', 'name', 'friendly_name'):
        value = str(disk.get(key) or '').strip()
        if value:
            return value
    mount = str(disk.get('mount_points') or '').strip()
    return mount or f'Disco {index + 1}'


def _score_status(score, severity, *, thermal_critical=False):
    if score is None:
        return 'NO EVALUABLE'
    if str(severity or '').upper() == 'CRITICAL' and thermal_critical:
        return 'TEMPERATURA CRÍTICA'
    if score >= 90.0:
        return 'ÓPTIMO'
    if score >= 75.0:
        return 'BUEN ESTADO'
    if score >= 55.0:
        return 'ESTADO MEDIO'
    if score >= 40.0:
        return 'REQUIERE REVISIÓN'
    return 'CRÍTICO'


def evaluate_current_health(telemetry, disks=None, preliminary_score=None):
    """Evalúa la salud global real sin inventar métricas ni reemplazar sensores.

    El porcentaje parte de la puntuación preliminar calculada por CorePulse y se
    reinterpreta junto a la evidencia instantánea: temperatura CPU/GPU, presión
    de RAM, llenado del almacenamiento y salud SMART cuando está disponible.
    """
    telemetry = telemetry if isinstance(telemetry, dict) else {}
    score = _num(preliminary_score)
    if score is None:
        try:
            from core.telemetry_reliable import calculate_preliminary_score
            score = calculate_preliminary_score(
                telemetry.get('cpu_usage'),
                telemetry.get('ram_usage'),
                telemetry.get('cpu_temp'),
                telemetry.get('gpu_temp'),
                disks or [],
            )
        except Exception:
            score = None
    score = None if score is None else max(0.0, min(100.0, score))

    reasons = []
    severity = 'NORMAL'
    evidence_available = score is not None

    cpu_temp = _num(telemetry.get('cpu_temp'))
    gpu_temp = _num(telemetry.get('gpu_temp'))
    ram_usage = _num(telemetry.get('ram_usage'))
    cpu_distance = _cpu_distance_to_tjmax(telemetry)

    if cpu_distance is not None:
        evidence_available = True
        if cpu_distance <= 5.0:
            severity = _raise_severity(severity, 'CRITICAL')
            _append_reason(reasons, f'Temperatura CPU muy cerca del máximo: {cpu_distance:.1f} °C de margen')
            score = _cap_score(score, 39.0)
        elif cpu_distance <= 10.0:
            severity = _raise_severity(severity, 'WARNING')
            _append_reason(reasons, f'Temperatura CPU cerca del máximo: {cpu_distance:.1f} °C de margen')
            score = _cap_score(score, 54.0)
        elif cpu_distance <= 20.0:
            severity = _raise_severity(severity, 'ELEVATED')
            _append_reason(reasons, f'Temperatura CPU elevada: {cpu_distance:.1f} °C de margen hasta el máximo')
            score = _cap_score(score, 74.0)
    elif cpu_temp is not None:
        evidence_available = True
        if cpu_temp >= 95.0:
            severity = _raise_severity(severity, 'CRITICAL')
            _append_reason(reasons, f'CPU caliente: {cpu_temp:.1f} °C')
            score = _cap_score(score, 39.0)
        elif cpu_temp >= 90.0:
            severity = _raise_severity(severity, 'WARNING')
            _append_reason(reasons, f'CPU alta: {cpu_temp:.1f} °C')
            score = _cap_score(score, 54.0)
        elif cpu_temp >= 80.0:
            severity = _raise_severity(severity, 'ELEVATED')
            _append_reason(reasons, f'CPU elevada: {cpu_temp:.1f} °C')
            score = _cap_score(score, 74.0)

    if gpu_temp is not None:
        evidence_available = True
        if gpu_temp >= 95.0:
            severity = _raise_severity(severity, 'CRITICAL')
            _append_reason(reasons, f'GPU caliente: {gpu_temp:.1f} °C')
            score = _cap_score(score, 39.0)
        elif gpu_temp >= 88.0:
            severity = _raise_severity(severity, 'WARNING')
            _append_reason(reasons, f'GPU alta: {gpu_temp:.1f} °C')
            score = _cap_score(score, 54.0)
        elif gpu_temp >= 80.0:
            severity = _raise_severity(severity, 'ELEVATED')
            _append_reason(reasons, f'GPU elevada: {gpu_temp:.1f} °C')
            score = _cap_score(score, 74.0)

    if ram_usage is not None:
        evidence_available = True
        if ram_usage >= 95.0:
            severity = _raise_severity(severity, 'WARNING')
            _append_reason(reasons, f'RAM casi saturada: {ram_usage:.1f}% en uso')
            score = _cap_score(score, 54.0)
        elif ram_usage >= 90.0:
            severity = _raise_severity(severity, 'ELEVATED')
            _append_reason(reasons, f'RAM exigida: {ram_usage:.1f}% en uso')
            score = _cap_score(score, 69.0)
        elif ram_usage >= 85.0:
            severity = _raise_severity(severity, 'ELEVATED')
            _append_reason(reasons, f'RAM alta: {ram_usage:.1f}% en uso')
            score = _cap_score(score, 79.0)

    for index, disk in enumerate(disks or []):
        if not isinstance(disk, dict):
            continue
        label = _disk_label(disk, index)
        used = _num(disk.get('used_percent'))
        health = _num(disk.get('health'))
        if used is not None:
            evidence_available = True
            if used >= 95.0:
                severity = _raise_severity(severity, 'WARNING')
                _append_reason(reasons, f'{label} muy lleno: {used:.0f}% ocupado')
                score = _cap_score(score, 54.0)
            elif used >= 90.0:
                severity = _raise_severity(severity, 'ELEVATED')
                _append_reason(reasons, f'{label} con poco espacio: {used:.0f}% ocupado')
                score = _cap_score(score, 69.0)
            elif used >= 85.0:
                severity = _raise_severity(severity, 'ELEVATED')
                _append_reason(reasons, f'{label} cargado: {used:.0f}% ocupado')
                score = _cap_score(score, 79.0)
        if health is not None:
            evidence_available = True
            if health < 50.0:
                severity = _raise_severity(severity, 'CRITICAL')
                _append_reason(reasons, f'{label} con salud baja: {health:.0f}%')
                score = _cap_score(score, 39.0)
            elif health < 70.0:
                severity = _raise_severity(severity, 'WARNING')
                _append_reason(reasons, f'{label} con salud reducida: {health:.0f}%')
                score = _cap_score(score, 54.0)
            elif health < 85.0:
                severity = _raise_severity(severity, 'ELEVATED')
                _append_reason(reasons, f'{label} con desgaste perceptible: {health:.0f}%')
                score = _cap_score(score, 79.0)

    if not evidence_available:
        severity = 'NO_EVALUABLE'

    # Si no hubo una causa dominante, el propio porcentaje ordena el bucket
    # visual de la tarjeta de salud para que 66% se interprete como un estado
    # intermedio y no como "óptimo".
    if severity == 'NORMAL' and score is not None:
        if score < 40.0:
            severity = 'CRITICAL'
        elif score < 55.0:
            severity = 'WARNING'
        elif score < 75.0:
            severity = 'ELEVATED'

    thermal_critical = bool(
        severity == 'CRITICAL' and (
            (cpu_distance is not None and cpu_distance <= 5.0)
            or (cpu_temp is not None and cpu_temp >= 95.0)
            or (gpu_temp is not None and gpu_temp >= 95.0)
        )
    )

    status = _score_status(score, severity, thermal_critical=thermal_critical)
    if score is not None and not reasons and status in {'ÓPTIMO', 'BUEN ESTADO'}:
        _append_reason(reasons, 'No se detectan señales relevantes de RAM saturada, SSD lleno, desgaste crítico ni temperatura alta.')

    return {
        'version': VERSION,
        'policy': POLICY,
        'score': round(score, 1) if score is not None else None,
        'severity': severity,
        'status': status,
        'reasons': reasons,
        'cpu_temp_c': cpu_temp,
        'gpu_temp_c': gpu_temp,
        'ram_usage_percent': ram_usage,
        'cpu_distance_to_tjmax_c': cpu_distance,
        'thermal_critical': thermal_critical,
        'sensor_values_unchanged': True,
        'synthetic': False,
        'estimated': False,
    }


# V482: fusión sin cambios de lógica desde core/diagnostics/health_intelligence.py
from typing import Any, Dict, Iterable





def _count_crashes(crashes: Dict[str, Any] | None, *keys: str) -> int:
    if not isinstance(crashes, dict):
        return 0
    counts = crashes.get('counts') if isinstance(crashes.get('counts'), dict) else {}
    total = 0
    for key in keys:
        try:
            total += int(counts.get(key) or 0)
        except Exception:
            pass
    return total


def build_health_intelligence(
    telemetry: Dict[str, Any] | None,
    disks: Iterable[Dict[str, Any]] | None = None,
    *,
    preliminary_score=None,
    battery: Dict[str, Any] | None = None,
    throttling: Dict[str, Any] | None = None,
    crashes: Dict[str, Any] | None = None,
    active_alerts: Iterable[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    telemetry = telemetry if isinstance(telemetry, dict) else {}
    disk_rows = [x for x in (disks or []) if isinstance(x, dict)]
    base = evaluate_current_health(telemetry, disk_rows, preliminary_score=preliminary_score)

    rank = {'NO_EVALUABLE': 0, 'NORMAL': 1, 'ATTENTION': 2, 'WARNING': 3, 'CRITICAL': 4}
    state = 'NO_EVALUABLE'
    factors: list[dict] = []
    coverage: list[str] = []

    severity = str(base.get('severity') or 'NO_EVALUABLE').upper()
    if severity == 'CRITICAL':
        state = 'CRITICAL'
    elif severity == 'WARNING':
        state = 'WARNING'
    elif severity == 'ELEVATED':
        state = 'ATTENTION'
    elif severity == 'NORMAL':
        state = 'NORMAL'

    if base.get('cpu_temp_c') is not None:
        coverage.append('CPU')
    if base.get('gpu_temp_c') is not None:
        coverage.append('GPU')
    if disk_rows:
        coverage.append('Almacenamiento')

    for reason in base.get('reasons') or []:
        factors.append({'level': severity, 'area': 'Telemetría', 'text': str(reason), 'source': 'Lectura actual'})

    throttle = throttling if isinstance(throttling, dict) else {}
    cpu_thr = throttle.get('cpu') if isinstance(throttle.get('cpu'), dict) else {}
    thr_state = str(cpu_thr.get('state') or '').upper()
    if thr_state == 'CONFIRMED':
        state = max((state, 'WARNING'), key=lambda x: rank[x])
        factors.append({'level': 'WARNING', 'area': 'CPU', 'text': 'CorePulse detectó throttling confirmado por evidencia explícita.', 'source': 'Detector térmico'})
        coverage.append('Throttling')
    elif thr_state in {'SUSPECTED', 'WATCHING'}:
        state = max((state, 'ATTENTION'), key=lambda x: rank[x])
        factors.append({'level': 'ATTENTION', 'area': 'CPU', 'text': 'Hay indicios que conviene seguir observando antes de confirmar throttling.', 'source': 'Detector térmico'})
        coverage.append('Throttling')

    batt = battery if isinstance(battery, dict) else {}
    if batt.get('present'):
        coverage.append('Batería')
        hp = _num(batt.get('health_percent'))
        if hp is not None:
            if hp < 60:
                state = max((state, 'WARNING'), key=lambda x: rank[x])
                factors.append({'level': 'WARNING', 'area': 'Batería', 'text': f'La capacidad útil reportada es {hp:.0f}% de la capacidad de diseño.', 'source': 'Salud de batería'})
            elif hp < 80:
                state = max((state, 'ATTENTION'), key=lambda x: rank[x])
                factors.append({'level': 'ATTENTION', 'area': 'Batería', 'text': f'La batería reporta {hp:.0f}% de salud; conviene seguir su evolución.', 'source': 'Salud de batería'})

    # Sólo usamos salud de disco cuando existe porcentaje real. N/A no penaliza.
    for row in disk_rows:
        hp = _num(row.get('health'))
        if hp is None:
            continue
        name = str(row.get('name') or row.get('model') or 'Unidad')
        if hp < 60:
            state = max((state, 'WARNING'), key=lambda x: rank[x])
            factors.append({'level': 'WARNING', 'area': 'Almacenamiento', 'text': f'{name}: salud reportada {hp:.0f}%.', 'source': 'SMART/telemetría disponible'})
        elif hp < 80:
            state = max((state, 'ATTENTION'), key=lambda x: rank[x])
            factors.append({'level': 'ATTENTION', 'area': 'Almacenamiento', 'text': f'{name}: salud reportada {hp:.0f}%; conviene seguir su evolución.', 'source': 'SMART/telemetría disponible'})

    if isinstance(crashes, dict) and not crashes.get('error'):
        coverage.append('Estabilidad de Windows')
        critical_events = _count_crashes(crashes, 'whea', 'bsod_bugcheck')
        unexpected = _count_crashes(crashes, 'kernel_power', 'unexpected_shutdown')
        if critical_events > 0:
            state = max((state, 'WARNING'), key=lambda x: rank[x])
            factors.append({'level': 'WARNING', 'area': 'Windows', 'text': f'El análisis reciente encontró {critical_events} evento(s) crítico(s) de hardware/bugcheck.', 'source': 'Registro de eventos'})
        elif unexpected > 0:
            state = max((state, 'ATTENTION'), key=lambda x: rank[x])
            factors.append({'level': 'ATTENTION', 'area': 'Windows', 'text': f'Windows registró {unexpected} apagado(s) o reinicio(s) inesperado(s) en el período analizado.', 'source': 'Registro de eventos'})

    alerts = [x for x in (active_alerts or []) if isinstance(x, dict)]
    if alerts:
        coverage.append('Alertas activas')
        critical = any(str(x.get('level') or '').upper() == 'CRITICAL' for x in alerts)
        warning = any(str(x.get('level') or '').upper() in {'WARNING', 'WARN'} for x in alerts)
        if critical:
            state = 'CRITICAL'
        elif warning:
            state = max((state, 'WARNING'), key=lambda x: rank[x])

    coverage = list(dict.fromkeys(coverage))
    labels = {
        'CRITICAL': ('Atención prioritaria', 'Hay evidencia actual que conviene revisar antes de continuar con cargas exigentes.'),
        'WARNING': ('Requiere atención', 'Se detectaron condiciones reales que merecen revisión.'),
        'ATTENTION': ('Seguimiento recomendado', 'El equipo funciona con normalidad, pero hay una señal real cuya evolución conviene observar.'),
        'NORMAL': ('Todo en orden', 'Con las lecturas disponibles no se detectan condiciones que requieran intervención.'),
        'NO_EVALUABLE': ('Aún sin evaluación', 'Todavía no hay lecturas suficientes para emitir una conclusión general.'),
    }
    title, summary = labels[state]

    if state == 'NORMAL' and not factors:
        factors.append({'level': 'NORMAL', 'area': 'Sistema', 'text': 'No se detectaron advertencias con las fuentes disponibles en esta sesión.', 'source': 'Resumen determinista'})

    return {
        'state': state,
        'title': title,
        'summary': summary,
        'factors': factors[:8],
        'coverage': coverage,
        'coverage_count': len(coverage),
        'score': base.get('score'),
        'policy': 'EXPLAINABLE_REAL_DATA_ONLY_NO_SYNTHETIC_SCORE',
        'synthetic': False,
    }


__all__ = ['build_health_intelligence']


# V482: integrado sin cambiar algoritmos desde core/diagnostics/thermal_throttling.py
import time
from collections import deque
from typing import Any, Dict


def _throttling_number(v):
    try:
        return float(v) if v is not None else None
    except Exception:
        return None


class ThermalThrottlingDetector:
    def __init__(self, max_samples: int = 60):
        self.samples = deque(maxlen=max(12, int(max_samples)))

    def add_sample(self, telemetry: Dict[str, Any] | None):
        t = telemetry if isinstance(telemetry, dict) else {}
        cpu = t.get('_cpu') if isinstance(t.get('_cpu'), dict) else {}
        gpus = t.get('_gpus') if isinstance(t.get('_gpus'), list) else []
        sample = {
            'ts': time.time(),
            'cpu_usage': _throttling_number(t.get('cpu_usage')),
            'cpu_temp': _throttling_number(t.get('cpu_temp')),
            'cpu_clock': _throttling_number(t.get('cpu_ghz')) or _throttling_number(cpu.get('clock_avg_ghz')),
            'cpu_max_observed': _throttling_number(cpu.get('clock_max_ghz')),
            'cpu_power': _throttling_number(cpu.get('package_power_w')),
            'cpu_tj_distance': _throttling_number(cpu.get('distance_to_tjmax_min_c')),
            'cpu_sensors': cpu.get('sensors') if isinstance(cpu.get('sensors'), list) else [],
            'gpus': gpus,
        }
        self.samples.append(sample)
        return self.evaluate()

    @staticmethod
    def _explicit_reason(sensors):
        for s in sensors or []:
            if not isinstance(s, dict):
                continue
            name = str(s.get('name') or s.get('sensor_name') or '').lower()
            value = _throttling_number(s.get('value'))
            if value is None or value <= 0:
                continue
            if 'thermal thrott' in name or 'thermal limit' in name:
                return 'THERMAL', str(s.get('name') or s.get('sensor_name'))
            if 'power limit' in name or 'power thrott' in name:
                return 'POWER', str(s.get('name') or s.get('sensor_name'))
        return None, None

    def evaluate(self):
        if not self.samples:
            return {'cpu': {'state': 'N/A'}, 'gpu': {'state': 'N/A'}, 'policy': 'EVIDENCE_FIRST'}
        cur = self.samples[-1]
        reason, sensor = self._explicit_reason(cur.get('cpu_sensors'))
        cpu = {'state': 'NO_EVIDENCE', 'reason': None, 'confidence': 'LOW', 'evidence': [], 'explicit_sensor': sensor}
        if reason:
            cpu.update(state='CONFIRMED', reason=reason, confidence='HIGH')
            cpu['evidence'].append(f'Sensor explícito: {sensor}')
        else:
            usage = cur.get('cpu_usage')
            temp = cur.get('cpu_temp')
            dist = cur.get('cpu_tj_distance')
            clock = cur.get('cpu_clock')
            recent_clocks = [s.get('cpu_clock') for s in list(self.samples)[-15:] if s.get('cpu_clock') is not None]
            peak = max(recent_clocks) if recent_clocks else cur.get('cpu_max_observed')
            clock_drop = (clock is not None and peak and peak > 0 and clock < peak * 0.78)
            hot = (dist is not None and dist <= 5.0) or (temp is not None and temp >= 95.0)
            warm = (dist is not None and dist <= 10.0) or (temp is not None and temp >= 90.0)
            loaded = usage is not None and usage >= 65.0
            if hot and loaded and clock_drop:
                cpu.update(state='SUSPECTED', reason='THERMAL', confidence='MEDIUM')
                cpu['evidence'] += ['Carga elevada', 'Margen térmico crítico', 'Caída de frecuencia respecto al pico reciente']
            elif warm and loaded:
                cpu.update(state='WATCHING', reason='THERMAL_HEADROOM', confidence='MEDIUM')
                cpu['evidence'] += ['Carga elevada', 'Margen térmico reducido']
            elif loaded and clock_drop and not hot:
                cpu.update(state='SUSPECTED', reason='POWER_OR_PLATFORM_LIMIT', confidence='LOW')
                cpu['evidence'] += ['Carga elevada', 'Frecuencia reducida sin evidencia térmica suficiente']

        gpu = {'state': 'NO_EVIDENCE', 'reason': None, 'confidence': 'LOW', 'devices': []}
        recent = list(self.samples)[-15:]
        for idx, g in enumerate(cur.get('gpus') or []):
            if not isinstance(g, dict):
                continue
            sensors = g.get('sensors') if isinstance(g.get('sensors'), list) else []
            greason, gsensor = self._explicit_reason(sensors)
            name = g.get('name') or g.get('hardware')
            item = {'index': idx, 'name': name, 'state': 'NO_EVIDENCE', 'reason': None, 'confidence': 'LOW', 'explicit_sensor': gsensor, 'evidence': []}
            if greason:
                item.update(state='CONFIRMED', reason=greason, confidence='HIGH')
                item['evidence'].append(f'Sensor explícito: {gsensor}')
            else:
                usage = _throttling_number(g.get('usage_percent')); temp = _throttling_number(g.get('temperature_c')); hotspot = _throttling_number(g.get('hotspot_c')); clock = _throttling_number(g.get('core_clock_mhz'))
                clocks=[]
                for smp in recent:
                    for oldg in smp.get('gpus') or []:
                        if isinstance(oldg,dict) and (oldg.get('name') or oldg.get('hardware')) == name:
                            val=_throttling_number(oldg.get('core_clock_mhz'))
                            if val is not None: clocks.append(val)
                peak=max(clocks) if clocks else None
                drop=clock is not None and peak and peak>0 and clock < peak*0.78
                hot=(hotspot is not None and hotspot>=100) or (temp is not None and temp>=88)
                loaded=usage is not None and usage>=75
                if hot and loaded and drop:
                    item.update(state='SUSPECTED',reason='THERMAL',confidence='MEDIUM')
                    item['evidence'] += ['Carga GPU elevada','Temperatura alta','Caída de core clock respecto al pico reciente']
                elif loaded and drop:
                    item.update(state='SUSPECTED',reason='POWER_OR_PLATFORM_LIMIT',confidence='LOW')
                    item['evidence'] += ['Carga GPU elevada','Core clock reducido sin sensor de causa explícito']
            gpu['devices'].append(item)
        if any(d.get('state') == 'CONFIRMED' for d in gpu['devices']):
            gpu.update(state='CONFIRMED', confidence='HIGH')
        elif any(d.get('state') == 'SUSPECTED' for d in gpu['devices']):
            gpu.update(state='SUSPECTED', confidence='MEDIUM')
        return {'cpu': cpu, 'gpu': gpu, 'policy': 'CONFIRMED_ONLY_WITH_EXPLICIT_SENSOR_OTHERWISE_SUSPECTED'}
