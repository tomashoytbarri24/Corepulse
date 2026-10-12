"""Recopila y analiza tendencias de diagnósticos realizados durante la sesión actual."""
from __future__ import annotations
# Código refactorizado: nombres estables y documentación en español.
import copy, json, os, threading, time, uuid
from pathlib import Path
from core.runtime_paths import data_path
from core.hardware_policy import select_representative_gpu_stats
SCHEMA_VERSION = 4
MAX_SESSION_TRENDS = 10

def _num(value):
    return isinstance(value, (int, float)) and (not isinstance(value, bool))

def _default_path():
    return data_path('session_trends.json')

def build_session_alert_summary(state):
    state = state or {}
    alerts = state.get('alerts') or {}
    episodes = {}
    for status, items in (('ACTIVE', alerts.get('active') or []), ('RESOLVED', alerts.get('history') or [])):
        for item in items:
            if not isinstance(item, dict):
                continue
            ident = (str(item.get('key') or ''), round(float(item.get('first_seen') or 0), 3))
            candidate = dict(item)
            candidate['_status'] = status
            if ident not in episodes or status == 'ACTIVE':
                episodes[ident] = candidate
    events = list(episodes.values())[-MAX_SESSION_TRENDS:]
    return {'active': sum((1 for x in events if x.get('_status') == 'ACTIVE')), 'resolved': sum((1 for x in events if x.get('_status') == 'RESOLVED')), 'critical': sum((1 for x in events if x.get('level') == 'CRITICAL')), 'warning': sum((1 for x in events if x.get('level') == 'WARNING')), 'info': sum((1 for x in events if x.get('level') == 'INFO')), 'event_count': len(events), 'source': 'CURRENT_AGENT_SESSION'}

def classify_session_profile(session):
    if not isinstance(session, dict):
        return 'LEGACY'
    profile = str(session.get('profile') or '').upper()
    if profile in {'GAME', 'DESKTOP'}:
        return profile
    context = str(session.get('final_context') or session.get('context') or '').upper()
    if context.startswith('GAME'):
        return 'GAME'
    if session.get('schema_version') in {2, 3, 4}:
        return 'DESKTOP'
    return 'LEGACY'

def _stat(stats, section, key, field):
    try:
        value = ((stats.get(section) or {}).get(key) or {}).get(field)
        return float(value) if _num(value) else None
    except Exception:
        return None

def _representative_gpu_stats(stats):
    """Obtiene la GPU representativa por actividad real, nunca por orden o fabricante."""
    gpus = (stats or {}).get('gpus') or {}
    _name, selected = select_representative_gpu_stats(gpus if isinstance(gpus, dict) else {})
    return selected


class SessionTrendCollector:
    """Clase responsable de `SessionTrendCollector` dentro de CorePulse. Conserva los contratos de integridad del módulo."""

    def __init__(self, path=None, max_sessions=MAX_SESSION_TRENDS):
        self.path = Path(path) if path else _default_path()
        self.max_sessions = min(MAX_SESSION_TRENDS, max(1, int(max_sessions)))
        self.lock = threading.RLock()
        self.runtime_session_id = str(uuid.uuid4())
        self.started_at = time.time()
        self.sample_count = 0
        self._last_state = {}
        self._finalized = False
        self._save({'schema_version': SCHEMA_VERSION, 'runtime_session_id': self.runtime_session_id, 'sessions': []})

    def add_sample(self, telemetry, state=None):
        if isinstance(telemetry, dict):
            self.sample_count += 1
        if isinstance(state, dict):
            self._last_state = copy.deepcopy(state)

    def _load(self):
        try:
            raw = json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else {}
            if not isinstance(raw, dict) or raw.get('runtime_session_id') != self.runtime_session_id:
                return {'schema_version': SCHEMA_VERSION, 'runtime_session_id': self.runtime_session_id, 'sessions': []}
            raw.setdefault('sessions', [])
            if not isinstance(raw['sessions'], list):
                raw['sessions'] = []
            return raw
        except Exception:
            return {'schema_version': SCHEMA_VERSION, 'runtime_session_id': self.runtime_session_id, 'sessions': []}

    def _save(self, data):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + '.tmp')
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        os.replace(tmp, self.path)

    def record_diagnostic(self, diagnostic_result, state=None):
        if not isinstance(diagnostic_result, dict):
            return None
        state = state or self._last_state or {}
        stats = diagnostic_result.get('statistics') or {}
        gpu = _representative_gpu_stats(stats)
        context = str(state.get('context') or state.get('mode') or 'DESKTOP').upper()
        profile = 'GAME' if context.startswith('GAME') or str(state.get('mode') or '').upper() == 'GAME' else 'DESKTOP'
        alerts = build_session_alert_summary(state)
        now = time.time()
        record = {'schema_version': SCHEMA_VERSION, 'runtime_session_id': self.runtime_session_id, 'session_id': str(uuid.uuid4()), 'started_at': now - float(diagnostic_result.get('duration_seconds') or 0), 'ended_at': now, 'duration_seconds': float(diagnostic_result.get('duration_seconds') or 0), 'sample_count': int(diagnostic_result.get('sample_count') or 0), 'profile': profile, 'accuracy': 'DIAGNOSTIC_CERTIFIED', 'final_context': context, 'principal_game': (state.get('game') or {}).get('name') if isinstance(state.get('game'), dict) else None, 'total_game_seconds': float(diagnostic_result.get('duration_seconds') or 0) if profile == 'GAME' else 0.0, 'game_active_seconds': float(diagnostic_result.get('duration_seconds') or 0) if profile == 'GAME' else 0.0, 'averages': {'cpu_usage': _stat(stats, 'cpu', 'usage_percent', 'avg'), 'cpu_temp': _stat(stats, 'cpu', 'package_temp_c', 'avg'), 'ram_usage': _stat(stats, 'ram', 'usage_percent', 'avg'), 'gpu_usage': (gpu.get('usage_percent') or {}).get('avg') if isinstance(gpu.get('usage_percent'), dict) else None, 'gpu_temp': (gpu.get('temperature_c') or {}).get('avg') if isinstance(gpu.get('temperature_c'), dict) else None}, 'maxima': {'cpu_usage': _stat(stats, 'cpu', 'usage_percent', 'max'), 'cpu_temp': _stat(stats, 'cpu', 'package_temp_c', 'max'), 'ram_usage': _stat(stats, 'ram', 'usage_percent', 'max'), 'gpu_usage': (gpu.get('usage_percent') or {}).get('max') if isinstance(gpu.get('usage_percent'), dict) else None, 'gpu_temp': (gpu.get('temperature_c') or {}).get('max') if isinstance(gpu.get('temperature_c'), dict) else None}, 'game_averages': {}, 'game_maxima': {}, 'alerts': {**alerts, 'source': 'CURRENT_AGENT_SESSION'}, 'alerts_trusted': True, 'overall': diagnostic_result.get('overall_status') or state.get('overall') or 'UNKNOWN'}
        if profile == 'GAME':
            record['game_averages'] = copy.deepcopy(record['averages'])
            record['game_maxima'] = copy.deepcopy(record['maxima'])
        with self.lock:
            data = self._load()
            data['sessions'].append(record)
            data['sessions'] = data['sessions'][-self.max_sessions:]
            self._save(data)
        return copy.deepcopy(record)

    def snapshot(self, alert_summary=None, state=None):
        sessions = self.load_sessions(limit=1)
        return sessions[0] if sessions else None

    def finalize(self, alert_summary=None, state=None):
        sessions = self.load_sessions(limit=1)
        return sessions[0] if sessions else None

    def load_sessions(self, limit=MAX_SESSION_TRENDS):
        data = self._load()
        sessions = copy.deepcopy(data.get('sessions') or [])
        for session in sessions:
            session['profile'] = classify_session_profile(session)
            session['alerts_trusted'] = (session.get('alerts') or {}).get('source') == 'CURRENT_AGENT_SESSION'
        sessions.sort(key=lambda item: -float(item.get('ended_at') or 0) if _num(item.get('ended_at')) else 0)
        return sessions[:min(self.max_sessions, max(1, int(limit)))]

    def clear_session(self):
        with self.lock:
            for p in (self.path, self.path.with_suffix(self.path.suffix + '.tmp')):
                try:
                    if p.exists():
                        p.unlink()
                except Exception:
                    pass

class SessionTrendAnalyzer:

    def __init__(self, sessions):
        self.sessions = list(sessions or [])

    @staticmethod
    def _value(session, section, key):
        value = (session.get(section) or {}).get(key)
        return float(value) if _num(value) else None

    @staticmethod
    def _direction(new, old):
        if new is None or old is None:
            return {'status': 'INSUFFICIENT', 'delta': None}
        delta = round(new - old, 2)
        if abs(delta) < 1.0:
            status = 'STABLE'
        elif delta < 0:
            status = 'IMPROVING'
        else:
            status = 'WORSENING'
        return {'status': status, 'delta': delta}

    @staticmethod
    def _comparison_scope(session):
        return classify_session_profile(session)

    def _find_comparable_previous(self, sessions):
        if not sessions:
            return None
        newest = sessions[0]
        scope = self._comparison_scope(newest)
        if scope == 'LEGACY':
            return None
        for candidate in sessions[1:]:
            if self._comparison_scope(candidate) == scope:
                return candidate
        return None

    def summary(self, limit=10):
        sessions = self.sessions[:limit]
        if not sessions:
            return {'session_count': 0, 'validated_sessions': 0, 'legacy_sessions': 0, 'warning_sessions': 0, 'critical_sessions': 0, 'warning_events': 0, 'critical_events': 0, 'cpu_max_average': None, 'gpu_max_average': None, 'summary_cpu_value': None, 'summary_gpu_value': None, 'summary_profile': None, 'summary_basis': None, 'cpu_comparison': {'status': 'NO_DATA', 'delta': None}, 'gpu_comparison': {'status': 'NO_DATA', 'delta': None}, 'comparison_profile': None, 'game_sessions': 0}
        validated = [session for session in sessions if classify_session_profile(session) != 'LEGACY']
        trusted_alert_sessions = [session for session in validated if session.get('alerts_trusted', False)]
        cpu_values = [self._value(session, 'maxima', 'cpu_temp') for session in validated]
        cpu_values = [value for value in cpu_values if value is not None]
        gpu_values = [self._value(session, 'maxima', 'gpu_temp') for session in validated]
        gpu_values = [value for value in gpu_values if value is not None]

        def average(values):
            return round(sum(values) / len(values), 2) if values else None
        newest = sessions[0]
        newest_profile = self._comparison_scope(newest)
        previous = self._find_comparable_previous(sessions)
        if newest_profile == 'LEGACY' or previous is None:
            cpu_comparison = {'status': 'NOT_COMPARABLE', 'delta': None}
            gpu_comparison = {'status': 'NOT_COMPARABLE', 'delta': None}
        else:
            comparison_section = 'game_maxima' if newest_profile == 'GAME' else 'maxima'
            cpu_comparison = self._direction(self._value(newest, comparison_section, 'cpu_temp'), self._value(previous, comparison_section, 'cpu_temp'))
            gpu_comparison = self._direction(self._value(newest, comparison_section, 'gpu_temp'), self._value(previous, comparison_section, 'gpu_temp'))
        summary_section = 'game_maxima' if newest_profile == 'GAME' else 'maxima'
        summary_cpu_value = self._value(newest, summary_section, 'cpu_temp') if newest_profile != 'LEGACY' else None
        summary_gpu_value = self._value(newest, summary_section, 'gpu_temp') if newest_profile != 'LEGACY' else None
        return {'session_count': len(sessions), 'validated_sessions': len(validated), 'legacy_sessions': len(sessions) - len(validated), 'warning_sessions': sum((1 for session in trusted_alert_sessions if (session.get('alerts') or {}).get('warning', 0) > 0)), 'critical_sessions': sum((1 for session in trusted_alert_sessions if (session.get('alerts') or {}).get('critical', 0) > 0)), 'warning_events': sum((int((session.get('alerts') or {}).get('warning', 0) or 0) for session in trusted_alert_sessions)), 'critical_events': sum((int((session.get('alerts') or {}).get('critical', 0) or 0) for session in trusted_alert_sessions)), 'cpu_max_average': average(cpu_values), 'gpu_max_average': average(gpu_values), 'summary_cpu_value': summary_cpu_value, 'summary_gpu_value': summary_gpu_value, 'summary_profile': newest_profile if newest_profile != 'LEGACY' else None, 'summary_basis': ('GAME_ACTIVE' if newest_profile == 'GAME' else 'FULL_SESSION') if newest_profile != 'LEGACY' else None, 'cpu_comparison': cpu_comparison, 'gpu_comparison': gpu_comparison, 'comparison_profile': newest_profile if newest_profile != 'LEGACY' else None, 'comparison_basis': ('GAME_ACTIVE' if newest_profile == 'GAME' else 'FULL_SESSION') if newest_profile != 'LEGACY' else None, 'game_sessions': sum((1 for session in validated if classify_session_profile(session) == 'GAME'))}

# V484: consolidación de core/diagnostics/before_after.py. Ruta anterior resuelta de forma diferida.
import json

import threading

import time

import uuid

from pathlib import Path

from core.runtime_paths import data_path

from typing import Any, Dict

import psutil

PATH = data_path('before_after.json')

HISTORY_PATH = data_path('optimization_history.json')

_LOCK = threading.RLock()

MAX_HISTORY = 60

def _before_after_num(v):
    try:
        return float(v) if v is not None else None
    except Exception:
        return None

def _first_num(*values):
    for value in values:
        number = _before_after_num(value)
        if number is not None:
            return number
    return None

def _system_context(runtime_context=None):
    runtime_context = runtime_context if isinstance(runtime_context, dict) else {}
    ctx = dict(runtime_context)
    try:
        ctx.setdefault('process_count', len(psutil.pids()))
    except Exception:
        ctx.setdefault('process_count', None)
    try:
        boot = float(psutil.boot_time())
        ctx.setdefault('boot_time_epoch', boot)
        ctx.setdefault('uptime_hours', max(0.0, (time.time() - boot) / 3600.0))
    except Exception:
        ctx.setdefault('boot_time_epoch', None)
        ctx.setdefault('uptime_hours', None)
    try:
        vm = psutil.virtual_memory()
        ctx.setdefault('ram_available_gb', float(vm.available) / (1024 ** 3))
        ctx.setdefault('ram_used_percent', float(vm.percent))
    except Exception:
        pass
    return ctx

def capture_metrics(telemetry: Dict[str, Any] | None, disks=None, battery=None, label='snapshot', runtime_context=None):
    t = telemetry if isinstance(telemetry, dict) else {}
    cpu = t.get('_cpu') if isinstance(t.get('_cpu'), dict) else {}
    gpus = t.get('_gpus') if isinstance(t.get('_gpus'), list) else []
    gpu_detail = next((g for g in gpus if isinstance(g, dict) and (_before_after_num(g.get('temperature_c')) is not None or _before_after_num(g.get('usage_percent')) is not None)), {})
    ctx = _system_context(runtime_context)
    storage = []
    for d in disks or []:
        if isinstance(d, dict):
            storage.append({
                'index': d.get('index'), 'model': d.get('model'),
                'health': _before_after_num(d.get('health')),
                'used_percent': _before_after_num(d.get('used_percent')),
                'temperature_c': _before_after_num(d.get('temperature_c')),
            })
    cpu_usage = _first_num(t.get('cpu_usage'), cpu.get('total_load_percent'))
    ram_usage = _first_num(t.get('ram_usage'), ctx.get('ram_used_percent'))
    ram_available = _first_num(t.get('ram_available_gb'), ctx.get('ram_available_gb'))
    network_latency = _first_num(
        ctx.get('network_latency_ms'), ctx.get('latency_ms'),
        t.get('network_latency_ms'), t.get('latency_ms'),
    )
    fps = _first_num(ctx.get('fps'), t.get('fps'))
    fps_low = _first_num(ctx.get('fps_1pct_low'), t.get('fps_1pct_low'))
    return {
        'label': str(label),
        'timestamp': time.time(),
        'cpu_usage': cpu_usage,
        'cpu_idle_percent': (100.0 - cpu_usage) if cpu_usage is not None else None,
        'cpu_temp': _first_num(t.get('cpu_temp'), cpu.get('package_temp_c'), cpu.get('core_max_temp_c'), cpu.get('core_average_temp_c')),
        'cpu_ghz': _first_num(t.get('cpu_ghz'), cpu.get('clock_avg_ghz'), cpu.get('clock_max_ghz')),
        'cpu_power_w': _before_after_num(cpu.get('package_power_w')),
        'ram_usage': ram_usage,
        'ram_available_gb': ram_available,
        'process_count': _before_after_num(ctx.get('process_count')),
        'boot_time_epoch': _before_after_num(ctx.get('boot_time_epoch')),
        'uptime_hours': _before_after_num(ctx.get('uptime_hours')),
        'gpu_usage': _first_num(t.get('gpu_usage'), gpu_detail.get('usage_percent')),
        'gpu_temp': _first_num(t.get('gpu_temp'), gpu_detail.get('temperature_c'), gpu_detail.get('hotspot_c')),
        'fps': fps,
        'fps_1pct_low': fps_low,
        'network_latency_ms': network_latency,
        'storage': storage,
        'battery_health': _before_after_num((battery or {}).get('health_percent')) if isinstance(battery, dict) else None,
        'system_score': _before_after_num(t.get('system_score')),
        'policy': 'OBSERVED_VALUES_ONLY',
    }

def save_snapshot(snapshot, slot='before'):
    data = {}
    try:
        if PATH.exists():
            data = json.loads(PATH.read_text(encoding='utf-8'))
    except Exception:
        data = {}
    data[str(slot)] = snapshot
    PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = PATH.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(PATH)
    return snapshot

def load_snapshots():
    try:
        return json.loads(PATH.read_text(encoding='utf-8')) if PATH.exists() else {}
    except Exception:
        return {}

def compare(before=None, after=None):
    if before is None or after is None:
        d = load_snapshots(); before = before or d.get('before'); after = after or d.get('after')
    if not isinstance(before, dict) or not isinstance(after, dict):
        return {'available': False, 'deltas': {}}
    fields = (
        'cpu_usage', 'cpu_idle_percent', 'cpu_temp', 'cpu_ghz', 'cpu_power_w',
        'ram_usage', 'ram_available_gb', 'process_count', 'gpu_usage', 'gpu_temp',
        'fps', 'fps_1pct_low', 'network_latency_ms', 'battery_health', 'system_score',
    )
    deltas = {}
    for key in fields:
        a, b = _before_after_num(before.get(key)), _before_after_num(after.get(key))
        deltas[key] = {'before': a, 'after': b, 'delta': (b-a) if a is not None and b is not None else None}
    # Discos se comparan por índice/modelo, sin inventar equivalencias.
    storage_deltas = []
    before_disks = [x for x in (before.get('storage') or []) if isinstance(x, dict)]
    after_disks = [x for x in (after.get('storage') or []) if isinstance(x, dict)]
    for a_disk in before_disks:
        match = next((x for x in after_disks if x.get('index') == a_disk.get('index') and str(x.get('model') or '') == str(a_disk.get('model') or '')), None)
        if not match:
            continue
        storage_deltas.append({
            'index': a_disk.get('index'), 'model': a_disk.get('model'),
            'health': {'before': _before_after_num(a_disk.get('health')), 'after': _before_after_num(match.get('health'))},
            'used_percent': {'before': _before_after_num(a_disk.get('used_percent')), 'after': _before_after_num(match.get('used_percent'))},
            'temperature_c': {'before': _before_after_num(a_disk.get('temperature_c')), 'after': _before_after_num(match.get('temperature_c'))},
        })
        for metric in ('health', 'used_percent', 'temperature_c'):
            pair = storage_deltas[-1][metric]
            if pair['before'] is not None and pair['after'] is not None:
                pair['delta'] = pair['after'] - pair['before']
            else:
                pair['delta'] = None
    return {
        'available': True,
        'before_ts': before.get('timestamp'),
        'after_ts': after.get('timestamp'),
        'deltas': deltas,
        'storage_deltas': storage_deltas,
        'note': 'Diferencia observada; no implica causalidad por sí sola.',
    }

def _read_history():
    try:
        raw = json.loads(HISTORY_PATH.read_text(encoding='utf-8')) if HISTORY_PATH.exists() else []
        return raw if isinstance(raw, list) else []
    except Exception:
        return []

def _write_history(rows):
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = HISTORY_PATH.with_suffix('.tmp')
    tmp.write_text(json.dumps(list(rows)[-MAX_HISTORY:], ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    tmp.replace(HISTORY_PATH)

def start_operation(action: str, telemetry=None, disks=None, battery=None, *, runtime_context=None, metadata=None):
    """Crea una sesión en memoria; se persiste al finalizar o marcar pendiente."""
    return {
        'id': uuid.uuid4().hex,
        'action': str(action or 'optimización'),
        'started_at': time.time(),
        'finished_at': None,
        'status': 'running',
        'metadata': dict(metadata or {}),
        'before': capture_metrics(telemetry, disks, battery, label='before_operation', runtime_context=runtime_context),
        'after': None,
        'comparison': None,
        'policy': 'OBSERVED_VALUES_ONLY_NO_CAUSALITY',
    }

def finish_operation(session, telemetry=None, disks=None, battery=None, *, runtime_context=None, metadata=None, status='completed', note=None):
    if not isinstance(session, dict):
        return None
    row = dict(session)
    row['finished_at'] = time.time()
    row['status'] = str(status or 'completed')
    merged = dict(row.get('metadata') or {})
    merged.update(dict(metadata or {}))
    row['metadata'] = merged
    row['after'] = capture_metrics(telemetry, disks, battery, label='after_operation', runtime_context=runtime_context)
    row['comparison'] = compare(row.get('before'), row.get('after'))
    if note:
        row['note'] = str(note)
    with _LOCK:
        history = _read_history()
        history.append(row)
        _write_history(history)
    return row

def mark_operation(session, *, status='pending', note=None, metadata=None):
    """Persiste una sesión sin forzar una medición DESPUÉS inexistente.

    Se usa cuando el efecto requiere reinicio/reinicio de Explorer o la operación
    no terminó correctamente. CorePulse no simula un resultado posterior.
    """
    if not isinstance(session, dict):
        return None
    row = dict(session)
    row['finished_at'] = time.time()
    row['status'] = str(status or 'pending')
    merged = dict(row.get('metadata') or {})
    merged.update(dict(metadata or {}))
    row['metadata'] = merged
    row['after'] = None
    row['comparison'] = {'available': False, 'deltas': {}}
    if note:
        row['note'] = str(note)
    with _LOCK:
        history = _read_history()
        history.append(row)
        _write_history(history)
    return row

def latest_operations(limit=12):
    with _LOCK:
        history = _read_history()
    history.sort(key=lambda x: float(x.get('finished_at') or x.get('started_at') or 0), reverse=True)
    return history[:max(1, int(limit))]

# V485: implementación consolidada de core/diagnostics/health_history.py; conserva las rutas de importación anteriores.
import datetime as _dt

import json

import sqlite3

import threading

import time

from pathlib import Path

from core.runtime_paths import data_path

from typing import Any, Dict, List

DB_PATH = data_path('health_history.sqlite3')

def _health_history_num(value):
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None

def _storage_health(disks):
    vals = []
    for disk in disks or []:
        if isinstance(disk, dict):
            v = _health_history_num(disk.get('health'))
            if v is not None:
                vals.append(v)
    return min(vals) if vals else None

def _storage_temp(disks):
    vals = []
    for disk in disks or []:
        if isinstance(disk, dict):
            v = _health_history_num(disk.get('temperature_c'))
            if v is not None:
                vals.append(v)
    return max(vals) if vals else None

def _battery_health(telemetry):
    battery = (telemetry or {}).get('_battery') if isinstance(telemetry, dict) else None
    if not isinstance(battery, dict):
        return None
    design = _health_history_num(battery.get('designed_capacity_mwh'))
    full = _health_history_num(battery.get('full_charge_capacity_mwh'))
    degradation = _health_history_num(battery.get('degradation_percent'))
    if design and full and design > 0:
        return max(0.0, min(100.0, full / design * 100.0))
    if degradation is not None:
        return max(0.0, min(100.0, 100.0 - degradation))
    return None

def _battery_degradation(telemetry, health_override=None):
    health = _health_history_num(health_override)
    if health is None:
        health = _battery_health(telemetry)
    return max(0.0, min(100.0, 100.0 - health)) if health is not None else None

def _metric_stats(rows, keys):
    result = {}
    for key in keys:
        vals = [_health_history_num(r.get(key)) for r in rows]
        vals = [v for v in vals if v is not None]
        result[key] = {
            'count': len(vals),
            'min': min(vals) if vals else None,
            'max': max(vals) if vals else None,
            'avg': sum(vals) / len(vals) if vals else None,
            'first': vals[0] if vals else None,
            'latest': vals[-1] if vals else None,
            'change': (vals[-1] - vals[0]) if len(vals) >= 2 else None,
        }
    return result

class HealthHistoryStore:
    """SQLite thread-safe para muestras espaciadas, benchmarks y comparaciones."""

    METRIC_KEYS = (
        'cpu_temp', 'cpu_usage', 'cpu_clock', 'cpu_power',
        'ram_usage', 'ram_available_gb', 'process_count',
        'gpu_temp', 'gpu_usage', 'storage_health', 'storage_temp_max',
        'battery_health', 'battery_degradation', 'system_score',
    )

    def __init__(self, path: Path | str = DB_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(str(self.path), timeout=6.0)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _ensure_columns(conn, table: str, columns: Dict[str, str]):
        existing = {str(row[1]) for row in conn.execute(f'PRAGMA table_info({table})').fetchall()}
        for name, sql_type in columns.items():
            if name not in existing:
                conn.execute(f'ALTER TABLE {table} ADD COLUMN {name} {sql_type}')

    def _init_db(self):
        with self._lock, self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS health_samples (
                    ts REAL PRIMARY KEY,
                    cpu_temp REAL, cpu_usage REAL, cpu_clock REAL, cpu_power REAL,
                    ram_usage REAL,
                    gpu_temp REAL, gpu_usage REAL,
                    storage_health REAL, battery_health REAL,
                    system_score REAL,
                    payload_json TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_health_samples_ts ON health_samples(ts);
                CREATE TABLE IF NOT EXISTS benchmark_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts REAL NOT NULL,
                    kind TEXT NOT NULL,
                    value REAL,
                    unit TEXT,
                    provider TEXT,
                    duration_s REAL,
                    payload_json TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_benchmark_runs_ts ON benchmark_runs(ts);
                CREATE TABLE IF NOT EXISTS benchmark_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts REAL NOT NULL,
                    profile TEXT NOT NULL,
                    components_json TEXT NOT NULL,
                    suite_json TEXT NOT NULL,
                    compare_json TEXT,
                    hardware_json TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_benchmark_sessions_ts ON benchmark_sessions(ts);
                CREATE TABLE IF NOT EXISTS stability_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts REAL NOT NULL,
                    period_days INTEGER NOT NULL,
                    bsod_bugcheck INTEGER,
                    whea INTEGER,
                    power_incidents INTEGER,
                    app_error INTEGER,
                    app_hang INTEGER,
                    matched_total INTEGER,
                    payload_json TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_stability_snapshots_ts ON stability_snapshots(ts);
                """
            )
            self._ensure_columns(conn, 'health_samples', {
                'ram_available_gb': 'REAL',
                'process_count': 'REAL',
                'storage_temp_max': 'REAL',
                'battery_degradation': 'REAL',
            })

    def record_snapshot(self, telemetry: Dict[str, Any], disks=None, score=None, ts=None, battery_health_override=None, context=None):
        telemetry = telemetry if isinstance(telemetry, dict) else {}
        cpu = telemetry.get('_cpu') if isinstance(telemetry.get('_cpu'), dict) else {}
        context = context if isinstance(context, dict) else {}
        ts = float(ts or time.time())
        battery_health = _health_history_num(battery_health_override)
        if battery_health is None:
            battery_health = _battery_health(telemetry)
        row = (
            ts,
            _health_history_num(telemetry.get('cpu_temp')),
            _health_history_num(telemetry.get('cpu_usage')),
            _health_history_num(telemetry.get('cpu_ghz')),
            _health_history_num(cpu.get('package_power_w')),
            _health_history_num(telemetry.get('ram_usage')),
            _health_history_num(telemetry.get('ram_available_gb')),
            _health_history_num(context.get('process_count')),
            _health_history_num(telemetry.get('gpu_temp')),
            _health_history_num(telemetry.get('gpu_usage')),
            _storage_health(disks),
            _storage_temp(disks),
            battery_health,
            _battery_degradation(telemetry, battery_health),
            _health_history_num(score),
            json.dumps({'policy': 'REAL_OR_NA', 'telemetry_version': telemetry.get('_telemetry_version')}, ensure_ascii=False),
        )
        with self._lock, self._connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO health_samples
                (ts,cpu_temp,cpu_usage,cpu_clock,cpu_power,ram_usage,ram_available_gb,process_count,
                 gpu_temp,gpu_usage,storage_health,storage_temp_max,battery_health,battery_degradation,system_score,payload_json)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                row,
            )
        return ts

    def record_stability_snapshot(self, result: Dict[str, Any], period_days: int = 7, ts=None):
        """Guarda un resumen ya calculado por Análisis de Windows.

        No dispara consultas de eventos por su cuenta. Así el historial reutiliza
        trabajo que el usuario ya pidió y evita procesos repetidos al entrar.
        """
        if not isinstance(result, dict) or result.get('error'):
            return None
        counts = result.get('counts') if isinstance(result.get('counts'), dict) else {}
        if not counts:
            counts = result.get('Counts') if isinstance(result.get('Counts'), dict) else {}
        power_incidents = result.get('power_incident_count')
        if power_incidents is None:
            power_incidents = result.get('PowerIncidentCount')
        matched = result.get('matched_total')
        if matched is None:
            matched = result.get('MatchedTotal')
        stamp = float(ts or time.time())
        period_days = max(1, int(period_days or 7))
        # Como el análisis suele repetirse manualmente, sustituimos una captura muy
        # próxima del mismo período para no llenar la BD con duplicados idénticos.
        with self._lock, self._connect() as conn:
            recent = conn.execute(
                'SELECT id,ts FROM stability_snapshots WHERE period_days=? ORDER BY ts DESC LIMIT 1',
                (period_days,),
            ).fetchone()
            values = (
                int(counts.get('bsod_bugcheck') or 0),
                int(counts.get('whea') or 0),
                int(power_incidents or 0),
                int(counts.get('app_error') or 0),
                int(counts.get('app_hang') or 0),
                int(matched or 0),
                json.dumps(result, ensure_ascii=False, default=str),
            )
            if recent is not None and stamp - float(recent['ts']) < 1800:
                conn.execute(
                    """UPDATE stability_snapshots SET ts=?,bsod_bugcheck=?,whea=?,power_incidents=?,app_error=?,app_hang=?,matched_total=?,payload_json=? WHERE id=?""",
                    (stamp, *values, int(recent['id'])),
                )
                return int(recent['id'])
            cur = conn.execute(
                """INSERT INTO stability_snapshots(ts,period_days,bsod_bugcheck,whea,power_incidents,app_error,app_hang,matched_total,payload_json)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (stamp, period_days, *values),
            )
            return cur.lastrowid

    def latest_stability_snapshots(self, limit: int = 12, period_days: int | None = None):
        with self._lock, self._connect() as conn:
            if period_days is None:
                rows = conn.execute(
                    'SELECT * FROM stability_snapshots ORDER BY ts DESC,id DESC LIMIT ?',
                    (max(1, int(limit)),),
                ).fetchall()
            else:
                rows = conn.execute(
                    'SELECT * FROM stability_snapshots WHERE period_days=? ORDER BY ts DESC,id DESC LIMIT ?',
                    (max(1, int(period_days)), max(1, int(limit))),
                ).fetchall()
        return [dict(row) for row in rows]

    def record_benchmark(self, result: Dict[str, Any]):
        if not isinstance(result, dict):
            return None
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO benchmark_runs(ts,kind,value,unit,provider,duration_s,payload_json)
                VALUES (?,?,?,?,?,?,?)""",
                (
                    float(result.get('timestamp') or time.time()),
                    str(result.get('kind') or 'unknown'),
                    _health_history_num(result.get('value')),
                    str(result.get('unit') or ''),
                    str(result.get('provider') or ''),
                    _health_history_num(result.get('duration_s')),
                    json.dumps(result, ensure_ascii=False),
                ),
            )
            return cur.lastrowid

    def query_range(self, start_ts: float, end_ts: float, limit: int = 10000) -> List[Dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                'SELECT * FROM health_samples WHERE ts>=? AND ts<? ORDER BY ts ASC LIMIT ?',
                (float(start_ts), float(end_ts), max(1, int(limit))),
            ).fetchall()
        return [dict(r) for r in rows]

    def query(self, days: int = 7, limit: int = 5000) -> List[Dict[str, Any]]:
        since = time.time() - max(1, int(days)) * 86400
        return self.query_range(since, time.time() + 1.0, limit=limit)

    def latest_benchmarks(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute('SELECT * FROM benchmark_runs ORDER BY ts DESC LIMIT ?', (max(1, int(limit)),)).fetchall()
        out = []
        for row in rows:
            d = dict(row)
            try:
                d['payload'] = json.loads(d.pop('payload_json') or '{}')
            except Exception:
                d['payload'] = {}
            out.append(d)
        return out

    def record_benchmark_session(
        self,
        suite: Dict[str, Any],
        *,
        profile: str | None = None,
        components=None,
        comparison: Dict[str, Any] | None = None,
        hardware: Dict[str, Any] | None = None,
    ):
        if not isinstance(suite, dict):
            return None
        normalized_components = []
        source_components = components if components is not None else suite.get('selected_components')
        for item in source_components or []:
            key = str(item or '').strip().lower()
            if key and key not in normalized_components:
                normalized_components.append(key)
        profile_key = str(profile or suite.get('profile') or 'standard').strip().upper()
        ts = _health_history_num(suite.get('finished_at')) or _health_history_num(suite.get('started_at')) or time.time()
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO benchmark_sessions(ts,profile,components_json,suite_json,compare_json,hardware_json)
                VALUES (?,?,?,?,?,?)""",
                (
                    float(ts),
                    profile_key,
                    json.dumps(normalized_components, ensure_ascii=False),
                    json.dumps(suite, ensure_ascii=False, default=str),
                    json.dumps(comparison or {}, ensure_ascii=False, default=str),
                    json.dumps(hardware or {}, ensure_ascii=False, default=str),
                ),
            )
            return cur.lastrowid

    def benchmark_session_count(self) -> int:
        """Número real de sesiones completas persistidas en este perfil local."""
        with self._lock, self._connect() as conn:
            row = conn.execute('SELECT COUNT(*) AS total FROM benchmark_sessions').fetchone()
        try:
            return int(row['total'] if row is not None else 0)
        except Exception:
            return 0

    def latest_benchmark_sessions(self, limit: int = 12) -> List[Dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                'SELECT * FROM benchmark_sessions ORDER BY ts DESC, id DESC LIMIT ?',
                (max(1, int(limit)),),
            ).fetchall()
        out = []
        for row in rows:
            data = dict(row)
            for source_key, target_key, fallback in (
                ('components_json', 'components', []),
                ('suite_json', 'suite', {}),
                ('compare_json', 'comparison', {}),
                ('hardware_json', 'hardware', {}),
            ):
                raw = data.pop(source_key, None)
                try:
                    data[target_key] = json.loads(raw or ('[]' if isinstance(fallback, list) else '{}'))
                except Exception:
                    data[target_key] = fallback
            out.append(data)
        return out

    def summary_range(self, start_ts: float, end_ts: float, limit: int = 10000) -> Dict[str, Any]:
        rows = self.query_range(start_ts, end_ts, limit=limit)
        return {
            'samples': len(rows),
            'from_ts': rows[0]['ts'] if rows else None,
            'to_ts': rows[-1]['ts'] if rows else None,
            'metrics': _metric_stats(rows, self.METRIC_KEYS),
        }

    def summary(self, days: int = 7) -> Dict[str, Any]:
        days = max(1, int(days))
        result = self.summary_range(time.time() - days * 86400, time.time() + 1.0)
        result['days'] = days
        return result

    def daily_summary(self, days: int = 30) -> List[Dict[str, Any]]:
        """Agrupa muestras reales por día local para una cronología legible."""
        days = max(1, min(365, int(days)))
        rows = self.query(days=days, limit=50000)
        buckets: Dict[str, List[Dict[str, Any]]] = {}
        for row in rows:
            key = _dt.datetime.fromtimestamp(float(row['ts'])).date().isoformat()
            buckets.setdefault(key, []).append(row)
        out = []
        for day in sorted(buckets):
            items = buckets[day]
            out.append({
                'date': day,
                'samples': len(items),
                'from_ts': items[0]['ts'],
                'to_ts': items[-1]['ts'],
                'metrics': _metric_stats(items, self.METRIC_KEYS),
            })
        return out

    def compare_periods(self, days: int = 7) -> Dict[str, Any]:
        """Compara el período actual con el bloque inmediatamente anterior."""
        days = max(1, min(90, int(days)))
        now = time.time()
        current = self.summary_range(now - days * 86400, now + 1.0)
        previous = self.summary_range(now - 2 * days * 86400, now - days * 86400)
        metrics = {}
        for key in self.METRIC_KEYS:
            c = (current.get('metrics') or {}).get(key) or {}
            p = (previous.get('metrics') or {}).get(key) or {}
            metric = {'current': c, 'previous': p}
            for stat in ('avg', 'max', 'min', 'latest'):
                cv, pv = _health_history_num(c.get(stat)), _health_history_num(p.get(stat))
                metric[f'{stat}_delta'] = (cv - pv) if cv is not None and pv is not None else None
            metrics[key] = metric
        return {
            'days': days,
            'current': current,
            'previous': previous,
            'metrics': metrics,
            'comparable': bool(current.get('samples') and previous.get('samples')),
            'policy': 'OBSERVED_PERIODS_ONLY',
        }

    def trend_insights(self, days: int = 7) -> List[Dict[str, Any]]:
        """Genera frases a partir de deltas observados, sin afirmar causalidad."""
        comp = self.compare_periods(days)
        if not comp.get('comparable'):
            return []
        insights = []
        specs = (
            ('cpu_temp', 'Temperatura máxima CPU', 'max_delta', ' °C', 2.0),
            ('gpu_temp', 'Temperatura máxima GPU', 'max_delta', ' °C', 2.0),
            ('ram_usage', 'Uso medio de RAM', 'avg_delta', ' pp', 3.0),
            ('system_score', 'Índice medio del sistema', 'avg_delta', ' pts', 2.0),
        )
        for key, label, delta_key, unit, threshold in specs:
            delta = _health_history_num((comp.get('metrics') or {}).get(key, {}).get(delta_key))
            if delta is None or abs(delta) < threshold:
                continue
            insights.append({
                'metric': key,
                'label': label,
                'delta': delta,
                'unit': unit,
                'direction': 'up' if delta > 0 else 'down',
                'text': f'{label}: {delta:+.1f}{unit} frente a los {days} días anteriores.',
            })
        # Salud de batería/almacenamiento se expresa como cambio dentro del período,
        # no como diagnóstico de causa ni pronóstico de degradación.
        current_metrics = (comp.get('current') or {}).get('metrics') or {}
        for key, label in (('battery_health', 'Salud de batería'), ('storage_health', 'Salud de almacenamiento')):
            change = _health_history_num((current_metrics.get(key) or {}).get('change'))
            if change is not None and abs(change) >= 0.5:
                insights.append({
                    'metric': key,
                    'label': label,
                    'delta': change,
                    'unit': ' pp',
                    'direction': 'up' if change > 0 else 'down',
                    'text': f'{label}: {change:+.1f} pp entre la primera y la última lectura válida del período.',
                })
        return insights
