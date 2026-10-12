"""Recuperación de sesión tras cierres no limpios de CorePulse.

Este módulo NO revierte tweaks persistentes elegidos por el usuario. Su trabajo es:
- detectar si la sesión anterior terminó sin pasar por el cierre normal;
- conservar evidencia local del incidente;
- exponer el estado para UI/diagnóstico;
- registrar recuperaciones seguras que otros subsistemas ya realizan (Game Boost,
  energía temporal, etc.).

El marcador vive en AppData y no contiene datos personales ni telemetría sensible.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import threading
import time
from typing import Any, Dict

import psutil

from core.runtime_paths import state_path, diagnostics_dir
from core.version import VERSION_LABEL

SESSION_FILE = state_path('active_session.json')
HISTORY_FILE = state_path('recovery_history.json')
_LOCK = threading.RLock()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path, default):
    try:
        if path.is_file():
            value = json.loads(path.read_text(encoding='utf-8'))
            return value
    except Exception:
        pass
    return default


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(path)


def _same_process_alive(payload: Dict[str, Any]) -> bool:
    try:
        pid = int(payload.get('pid') or 0)
        expected = float(payload.get('process_create_time') or 0.0)
        if pid <= 0 or not psutil.pid_exists(pid):
            return False
        proc = psutil.Process(pid)
        actual = float(proc.create_time())
        if expected > 0 and abs(actual - expected) > 2.0:
            return False
        return proc.is_running()
    except Exception:
        return False


def _append_history(entry: Dict[str, Any]) -> None:
    rows = _read_json(HISTORY_FILE, [])
    if not isinstance(rows, list):
        rows = []
    rows.append(dict(entry))
    rows = rows[-40:]
    _write_json(HISTORY_FILE, rows)


class SessionRecoveryManager:
    """Autoridad del marcador de sesión de CorePulse."""

    def __init__(self, session_path: Path | None = None, history_path: Path | None = None, crash_dir: Path | None = None):
        self.session_path = Path(session_path) if session_path else SESSION_FILE
        self.history_path = Path(history_path) if history_path else HISTORY_FILE
        self.crash_dir = Path(crash_dir) if crash_dir else (Path(diagnostics_dir()) / 'crash_reports')
        self.current: Dict[str, Any] = {}
        self.previous_abnormal: Dict[str, Any] | None = None
        self.recovery_actions: list[dict] = []
        self.last_crash_report_path: str | None = None
        self._clean = False

    def _write_crash_report(self, abnormal: Dict[str, Any]) -> str | None:
        try:
            folder = self.crash_dir
            folder.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            path = folder / f'Crash_CorePulse_{stamp}.json'
            payload = {
                'schema': 'corepulse.crash_report.v1',
                'generated_at': _utc_now(),
                'abnormal_session': dict(abnormal),
                'recovery_actions': list(self.recovery_actions),
                'policy': 'LOCAL_TECHNICAL_METADATA_ONLY',
            }
            _write_json(path, payload)
            self.last_crash_report_path = str(path)
            return str(path)
        except Exception:
            return None

    def _refresh_crash_report_actions(self) -> None:
        path = Path(self.last_crash_report_path) if self.last_crash_report_path else None
        if path is None or not path.is_file():
            return
        try:
            payload = _read_json(path, {})
            if not isinstance(payload, dict):
                payload = {}
            payload['recovery_actions'] = list(self.recovery_actions)
            payload['updated_at'] = _utc_now()
            _write_json(path, payload)
        except Exception:
            pass

    def begin_session(self) -> Dict[str, Any]:
        with _LOCK:
            previous = _read_json(self.session_path, {})
            abnormal = None
            if isinstance(previous, dict) and previous.get('active'):
                # Si el PID anterior sigue siendo exactamente el mismo proceso,
                # no lo clasificamos como crash: puede existir una segunda instancia.
                if not _same_process_alive(previous):
                    abnormal = {
                        'detected': True,
                        'previous_version': previous.get('version'),
                        'previous_pid': previous.get('pid'),
                        'started_at': previous.get('started_at'),
                        'last_heartbeat_at': previous.get('last_heartbeat_at'),
                        'detected_at': _utc_now(),
                        'reason': 'La sesión anterior no alcanzó el cierre normal de CorePulse.',
                    }
                    self.previous_abnormal = abnormal
                    report_path = self._write_crash_report(abnormal)
                    if report_path:
                        abnormal['report_path'] = report_path
                        self.previous_abnormal = abnormal
                    # Usamos la ruta configurable del objeto para permitir pruebas.
                    old_history = _read_json(self.history_path, [])
                    if not isinstance(old_history, list):
                        old_history = []
                    old_history.append({'type': 'abnormal_shutdown', **abnormal})
                    _write_json(self.history_path, old_history[-40:])

            try:
                create_time = float(psutil.Process(os.getpid()).create_time())
            except Exception:
                create_time = time.time()
            self.current = {
                'schema': 'corepulse.session.v1',
                'active': True,
                'clean_shutdown': False,
                'version': VERSION_LABEL,
                'pid': os.getpid(),
                'process_create_time': create_time,
                'started_at': _utc_now(),
                'last_heartbeat_at': _utc_now(),
                'recovery_actions': [],
            }
            _write_json(self.session_path, self.current)
            self._clean = False
            return self.status()

    def heartbeat(self) -> None:
        with _LOCK:
            if not self.current or self._clean:
                return
            self.current['last_heartbeat_at'] = _utc_now()
            _write_json(self.session_path, self.current)

    def record_recovery_action(self, component: str, success: bool, message: str, **meta) -> Dict[str, Any]:
        entry = {
            'component': str(component or 'CorePulse'),
            'success': bool(success),
            'message': str(message or ''),
            'timestamp': _utc_now(),
        }
        if meta:
            entry['meta'] = {str(k): v for k, v in meta.items()}
        with _LOCK:
            self.recovery_actions.append(entry)
            if self.current and not self._clean:
                self.current['recovery_actions'] = list(self.recovery_actions[-20:])
                _write_json(self.session_path, self.current)
            self._refresh_crash_report_actions()
        return dict(entry)

    def mark_clean_shutdown(self) -> Dict[str, Any]:
        with _LOCK:
            if self._clean:
                return self.status()
            self._clean = True
            if self.current:
                self.current.update({
                    'active': False,
                    'clean_shutdown': True,
                    'closed_at': _utc_now(),
                    'last_heartbeat_at': _utc_now(),
                    'recovery_actions': list(self.recovery_actions[-20:]),
                })
                # Guardamos el cierre limpio en historial y retiramos el marcador
                # activo para que un arranque futuro no pueda confundirlo con crash.
                history = _read_json(self.history_path, [])
                if not isinstance(history, list):
                    history = []
                history.append({
                    'type': 'clean_shutdown',
                    'version': self.current.get('version'),
                    'started_at': self.current.get('started_at'),
                    'closed_at': self.current.get('closed_at'),
                })
                _write_json(self.history_path, history[-40:])
            try:
                self.session_path.unlink(missing_ok=True)
            except Exception:
                pass
            return self.status()

    def history(self, limit: int = 12) -> list[dict]:
        rows = _read_json(self.history_path, [])
        if not isinstance(rows, list):
            return []
        return [dict(x) for x in rows[-max(1, int(limit)):][::-1] if isinstance(x, dict)]

    def status(self) -> Dict[str, Any]:
        return {
            'previous_abnormal': dict(self.previous_abnormal) if isinstance(self.previous_abnormal, dict) else None,
            'current_active': bool(self.current and not self._clean),
            'current_version': self.current.get('version') if self.current else VERSION_LABEL,
            'recovery_actions': list(self.recovery_actions),
            'history': self.history(8),
            'crash_report_path': self.last_crash_report_path,
            'policy': 'DETECT_ABNORMAL_CLOSE_RESTORE_ONLY_TEMPORARY_STATE',
        }


__all__ = ['SessionRecoveryManager', 'SESSION_FILE', 'HISTORY_FILE']


# V481 · Implementación consolidada desde core/diagnostics/diagnostic_history.py (sin cambio de contrato público).
import json
from pathlib import Path
from typing import Any, Dict, Optional

from core.diagnostic_summary import build_component_assessments
from core.runtime_paths import diagnostics_dir


def load_previous_complete_result(current_path: str | None = None) -> Optional[Dict[str, Any]]:
    root = Path(diagnostics_dir())
    try:
        files = sorted(root.glob('diagnostic_complete_*.json'), key=lambda p: p.stat().st_mtime, reverse=True)
    except Exception:
        return None
    current = Path(current_path).resolve() if current_path else None
    for path in files:
        try:
            if current is not None and path.resolve() == current:
                continue
            payload = json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            continue
        complete = payload.get('complete_diagnostic') if isinstance(payload, dict) else None
        if not isinstance(complete, dict):
            continue
        if (str(complete.get('status') or '').upper() not in {'COMPLETE', 'PARTIAL'}
                or complete.get('finalized') is False or complete.get('cancelled_by_user')):
            continue
        return payload
    return None


def _status_map(result: Dict[str, Any]) -> Dict[str, str]:
    return {
        str(item.get('key')): str(item.get('status') or 'NO_EVALUABLE').upper()
        for item in build_component_assessments(result if isinstance(result, dict) else {})
        if isinstance(item, dict) and item.get('key')
    }


def build_diagnostic_comparison(current: Dict[str, Any], previous: Dict[str, Any] | None) -> Dict[str, Any]:
    if not isinstance(previous, dict):
        return {
            'available': False,
            'policy': 'INFORMATIONAL_ONLY_NOT_CURRENT_FAULT_SOURCE',
            'component_changes': [],
        }
    now_map = _status_map(current)
    prev_map = _status_map(previous)
    labels = {
        'cpu': 'CPU', 'gpu': 'GPU', 'ram': 'RAM', 'storage': 'Almacenamiento',
        'battery': 'Batería', 'windows': 'Windows',
    }
    changes = []
    for key in ('cpu', 'gpu', 'ram', 'storage', 'battery', 'windows'):
        before = prev_map.get(key, 'NO_EVALUABLE')
        after = now_map.get(key, 'NO_EVALUABLE')
        if before != after:
            changes.append({
                'key': key,
                'title': labels[key],
                'previous': before,
                'current': after,
            })
    previous_complete = previous.get('complete_diagnostic') if isinstance(previous.get('complete_diagnostic'), dict) else {}
    return {
        'available': True,
        'previous_started_at': previous.get('started_at'),
        'previous_overall_status': str(previous.get('overall_status') or 'NO_EVALUABLE').upper(),
        'current_overall_status': str(current.get('overall_status') or 'NO_EVALUABLE').upper(),
        'previous_complete_status': str(previous_complete.get('status') or 'UNKNOWN').upper(),
        'component_changes': changes,
        'unchanged_components': max(0, 6 - len(changes)),
        'policy': 'INFORMATIONAL_ONLY_NOT_CURRENT_FAULT_SOURCE',
        'history_used_as_current_fault_source': False,
    }


# V481 · Implementación consolidada desde core/diagnostics/diagnostic_lifecycle.py (sin cambio de contrato público).
import threading
from dataclasses import dataclass, field
from enum import Enum


class DiagnosticState(str, Enum):
    IDLE = 'IDLE'
    PREPARING = 'PREPARING'
    RUNNING_BASELINE = 'RUNNING_BASELINE'
    RUNNING_HARDWARE = 'RUNNING_HARDWARE'
    RUNNING_WINDOWS = 'RUNNING_WINDOWS'
    RUNNING_INTEGRITY = 'RUNNING_INTEGRITY'
    RUNNING_BENCHMARK = 'RUNNING_BENCHMARK'
    ANALYZING_BENCHMARK = 'ANALYZING_BENCHMARK'
    RUNNING_STRESS_CPU = 'RUNNING_STRESS_CPU'
    RUNNING_STRESS_RAM = 'RUNNING_STRESS_RAM'
    RUNNING_STRESS_GPU = 'RUNNING_STRESS_GPU'
    RUNNING_FANS = 'RUNNING_FANS'
    RUNNING_AUDIO = 'RUNNING_AUDIO'
    RUNNING_CLEANUP = 'RUNNING_CLEANUP'
    CORRELATING = 'CORRELATING'
    RUNNING_AI = 'RUNNING_AI'
    COOLDOWN = 'COOLDOWN'
    COMPLETED = 'COMPLETED'
    CANCELLING = 'CANCELLING'
    CANCELLED = 'CANCELLED'
    ERROR = 'ERROR'


_ORDER = list(DiagnosticState)
_TERMINAL = {DiagnosticState.COMPLETED, DiagnosticState.CANCELLED, DiagnosticState.ERROR}


@dataclass
class DiagnosticRun:
    token: int
    cancel_event: threading.Event = field(default_factory=threading.Event)
    worker: threading.Thread | None = None
    state: DiagnosticState = DiagnosticState.PREPARING
    _lock: threading.RLock = field(default_factory=threading.RLock, repr=False)
    _progress: tuple | None = None
    _result: tuple | None = None

    def transition(self, state):
        state = DiagnosticState(state)
        with self._lock:
            if self.state in _TERMINAL or self.state == DiagnosticState.CANCELLING:
                return False
            if state not in _TERMINAL and _ORDER.index(state) < _ORDER.index(self.state):
                return False
            self.state = state
            return True

    def cancel(self):
        with self._lock:
            if self.state in _TERMINAL:
                return False
            self.state = DiagnosticState.CANCELLING
            self.cancel_event.set()
            self._progress = self._result = None
            self.state = DiagnosticState.CANCELLED
            return True

    def post_progress(self, fraction, stage, detail=''):
        with self._lock:
            if not self.cancel_event.is_set() and self.state not in _TERMINAL:
                # La carga RAM produce miles de avances: conservar sólo el último.
                self._progress = (fraction, stage, detail)

    def post_result(self, result, error=None, state=None):
        with self._lock:
            if not self.cancel_event.is_set() and self.state not in _TERMINAL:
                self._result = (result, error, state)

    def drain(self):
        with self._lock:
            messages = self._progress, self._result
            self._progress = self._result = None
            return messages


def is_finalized_result(result):
    if not isinstance(result, dict):
        return False
    block = result.get('complete_diagnostic')
    return (isinstance(block, dict) and block.get('finalized') is True
            and block.get('status') in {'COMPLETE', 'PARTIAL'}
            and not block.get('cancelled_by_user'))


def is_completed_benchmark(benchmark):
    if not isinstance(benchmark, dict) or benchmark.get('cancelled') or benchmark.get('safety_stop'):
        return False
    if benchmark.get('status') not in {'OK', 'COMPLETE'}:
        return False
    selected = benchmark.get('selected_components') or ('cpu', 'ram', 'ssd', 'gpu')
    return all(isinstance(benchmark.get(k), dict) and benchmark[k].get('status') == 'OK'
               for k in selected)


# V482: fusión sin cambios de lógica desde core/diagnostics/diagnostic_session.py
# Código refactorizado: nombres estables y documentación en español.
import json
import math
import os
import statistics
import threading
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from core.runtime_paths import diagnostics_dir
SESSION_SECONDS = 120
SAMPLE_INTERVAL_SECONDS = 1.0

@dataclass
class Finding:
    component: str
    status: str
    title: str
    explanation: str
    evidence: list[str]
    rule_source: str

def _number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        value = float(value)
        if math.isfinite(value):
            return value
    return None

def _stats(values):
    clean = [_number(v) for v in values]
    clean = [v for v in clean if v is not None]
    if not clean:
        return {'samples': 0, 'min': None, 'max': None, 'avg': None, 'median': None}
    return {'samples': len(clean), 'min': round(min(clean), 3), 'max': round(max(clean), 3), 'avg': round(sum(clean) / len(clean), 3), 'median': round(statistics.median(clean), 3)}

class DiagnosticSession:

    def __init__(self, duration_seconds=SESSION_SECONDS):
        self.duration_seconds = int(duration_seconds)
        self._lock = threading.RLock()
        self._active = False
        self._completed = False
        self._started_monotonic = None
        self._started_wall = None
        self._ended_wall = None
        self._last_sample_monotonic = 0.0
        self._samples = []
        self._result = None

    @property
    def active(self):
        with self._lock:
            return self._active

    @property
    def completed(self):
        with self._lock:
            return self._completed

    @property
    def result(self):
        with self._lock:
            return self._result

    def start(self):
        with self._lock:
            self._samples = []
            self._result = None
            self._active = True
            self._completed = False
            self._started_monotonic = time.monotonic()
            self._started_wall = datetime.now().astimezone().isoformat()
            self._ended_wall = None
            self._last_sample_monotonic = 0.0

    def cancel(self):
        """Cancela la sesión sin convertir evidencia parcial en diagnóstico final."""
        with self._lock:
            self._active = False
            self._completed = False
            self._started_monotonic = None
            self._started_wall = None
            self._ended_wall = None
            self._last_sample_monotonic = 0.0
            self._samples = []
            self._result = None

    def elapsed_seconds(self):
        with self._lock:
            if self._started_monotonic is None:
                return 0.0
            if self._active:
                return max(0.0, time.monotonic() - self._started_monotonic)
            if self._result:
                return float(self._result.get('duration_seconds', 0))
            return 0.0

    def remaining_seconds(self):
        return max(0, self.duration_seconds - int(self.elapsed_seconds()))

    def should_finish(self):
        return self.active and self.elapsed_seconds() >= self.duration_seconds

    def add_sample(self, telemetry, disks=None):
        now = time.monotonic()
        with self._lock:
            if not self._active:
                return False
            if now - self._last_sample_monotonic < SAMPLE_INTERVAL_SECONDS:
                return False
            self._last_sample_monotonic = now
            cpu = telemetry.get('_cpu') or {}
            gpus = telemetry.get('_gpus') or []
            storage = telemetry.get('_storage_devices') or []
            battery = telemetry.get('_battery')
            sample = {'timestamp': datetime.now().astimezone().isoformat(), 'elapsed_seconds': round(self.elapsed_seconds(), 3), 'cpu_usage_percent': _number(telemetry.get('cpu_usage')), 'cpu_package_temp_c': _number(cpu.get('package_temp_c') or telemetry.get('cpu_temp')), 'cpu_core_max_temp_c': _number(cpu.get('core_max_temp_c')), 'cpu_core_average_temp_c': _number(cpu.get('core_average_temp_c')), 'cpu_distance_to_tjmax_min_c': _number(cpu.get('distance_to_tjmax_min_c')), 'cpu_clock_avg_ghz': _number(cpu.get('clock_avg_ghz') or telemetry.get('cpu_ghz')), 'cpu_package_power_w': _number(cpu.get('package_power_w')), 'ram_usage_percent': _number(telemetry.get('ram_usage')), 'gpus': [], 'storage': [], 'battery': battery.copy() if isinstance(battery, dict) else None}
            for gpu in gpus:
                sample['gpus'].append({'name': gpu.get('name'), 'hardware_type': gpu.get('hardware_type'), 'temperature_c': _number(gpu.get('temperature_c')), 'hotspot_c': _number(gpu.get('hotspot_c')), 'usage_percent': _number(gpu.get('usage_percent')), 'memory_usage_percent': _number(gpu.get('memory_usage_percent')), 'power_w': _number(gpu.get('power_w')), 'core_clock_mhz': _number(gpu.get('core_clock_mhz'))})
            for drive in storage:
                sample['storage'].append({'name': drive.get('name'), 'temperature_c': _number(drive.get('temperature_c')), 'warning_temperature_c': _number(drive.get('warning_temperature_c')), 'critical_temperature_c': _number(drive.get('critical_temperature_c')), 'life_percent': _number(drive.get('life_percent')), 'used_space_percent': _number(drive.get('used_space_percent')), 'power_on_hours': _number(drive.get('power_on_hours'))})
            self._samples.append(sample)
            return True

    def finish(self):
        with self._lock:
            if not self._active:
                return self._result
            self._active = False
            self._completed = True
            self._ended_wall = datetime.now().astimezone().isoformat()
            duration = max(0, int(round(time.monotonic() - self._started_monotonic)))
            statistics_data = self._build_statistics()
            findings = self._build_findings(statistics_data)
            overall = self._overall_status(findings)
            self._result = {'corepulse_version': '0.6', 'session_valid': duration >= self.duration_seconds, 'required_duration_seconds': self.duration_seconds, 'duration_seconds': duration, 'sample_interval_seconds': SAMPLE_INTERVAL_SECONDS, 'sample_count': len(self._samples), 'started_at': self._started_wall, 'ended_at': self._ended_wall, 'overall_status': overall, 'statistics': statistics_data, 'findings': [asdict(f) for f in findings], 'data_policy': {'missing_values': 'UNAVAILABLE / no evaluable', 'fabricated_sensor_values': False, 'statistics': 'derived only from collected numeric samples'}}
            return self._result

    def _build_statistics(self):
        samples = list(self._samples)
        result = {'cpu': {'usage_percent': _stats([s['cpu_usage_percent'] for s in samples]), 'package_temp_c': _stats([s['cpu_package_temp_c'] for s in samples]), 'core_max_temp_c': _stats([s['cpu_core_max_temp_c'] for s in samples]), 'core_average_temp_c': _stats([s['cpu_core_average_temp_c'] for s in samples]), 'distance_to_tjmax_min_c': _stats([s['cpu_distance_to_tjmax_min_c'] for s in samples]), 'clock_avg_ghz': _stats([s['cpu_clock_avg_ghz'] for s in samples]), 'package_power_w': _stats([s['cpu_package_power_w'] for s in samples]), 'seconds_within_5c_tjmax': 0, 'seconds_within_10c_tjmax': 0}, 'ram': {'usage_percent': _stats([s['ram_usage_percent'] for s in samples]), 'seconds_over_85_percent': 0, 'seconds_over_90_percent': 0, 'seconds_over_95_percent': 0}, 'gpus': {}, 'storage': {}, 'battery': None}
        for s in samples:
            d = s['cpu_distance_to_tjmax_min_c']
            if d is not None:
                if d <= 5:
                    result['cpu']['seconds_within_5c_tjmax'] += 1
                if d <= 10:
                    result['cpu']['seconds_within_10c_tjmax'] += 1
            ram = s['ram_usage_percent']
            if ram is not None:
                if ram >= 85:
                    result['ram']['seconds_over_85_percent'] += 1
                if ram >= 90:
                    result['ram']['seconds_over_90_percent'] += 1
                if ram >= 95:
                    result['ram']['seconds_over_95_percent'] += 1
        gpu_names = []
        storage_names = []
        for s in samples:
            for gpu in s['gpus']:
                name = gpu.get('name')
                if name and name not in gpu_names:
                    gpu_names.append(name)
            for drive in s['storage']:
                name = drive.get('name')
                if name and name not in storage_names:
                    storage_names.append(name)
        for name in gpu_names:
            records = []
            for s in samples:
                records.extend([g for g in s['gpus'] if g.get('name') == name])
            result['gpus'][name] = {'usage_percent': _stats([r['usage_percent'] for r in records]), 'temperature_c': _stats([r['temperature_c'] for r in records]), 'hotspot_c': _stats([r['hotspot_c'] for r in records]), 'memory_usage_percent': _stats([r['memory_usage_percent'] for r in records]), 'power_w': _stats([r['power_w'] for r in records]), 'core_clock_mhz': _stats([r.get('core_clock_mhz') for r in records])}
        for name in storage_names:
            records = []
            for s in samples:
                records.extend([d for d in s['storage'] if d.get('name') == name])
            current = records[-1] if records else {}
            warning = current.get('warning_temperature_c')
            critical = current.get('critical_temperature_c')
            seconds_warning = 0
            seconds_critical = 0
            for r in records:
                temp = r['temperature_c']
                if temp is None:
                    continue
                if warning is not None and temp >= warning:
                    seconds_warning += 1
                if critical is not None and temp >= critical:
                    seconds_critical += 1
            result['storage'][name] = {'temperature_c': _stats([r['temperature_c'] for r in records]), 'warning_temperature_c': warning, 'critical_temperature_c': critical, 'seconds_at_or_above_warning': seconds_warning, 'seconds_at_or_above_critical': seconds_critical, 'life_percent': current.get('life_percent'), 'used_space_percent': current.get('used_space_percent'), 'power_on_hours': current.get('power_on_hours')}
        batteries = [s['battery'] for s in samples if isinstance(s.get('battery'), dict)]
        if batteries:
            result['battery'] = batteries[-1]
        return result

    def _build_findings(self, stats):
        findings = []
        cpu = stats['cpu']
        tj = cpu['distance_to_tjmax_min_c']
        if tj['samples'] > 0:
            near5 = cpu['seconds_within_5c_tjmax']
            near10 = cpu['seconds_within_10c_tjmax']
            if near5 >= 30:
                findings.append(Finding('CPU', 'CRITICAL', 'CPU sostenidamente muy cerca de TjMax', 'Durante una parte importante de la sesión el procesador estuvo a 5 °C o menos de su TjMax reportado.', [f'Tiempo ≤5 °C de TjMax: {near5} s', f"Distancia mínima registrada: {tj['min']} °C", f"CPU Package máximo: {cpu['package_temp_c']['max']} °C"], 'CorePulse policy based on hardware-reported Distance to TjMax'))
            elif near10 >= 30:
                findings.append(Finding('CPU', 'WARNING', 'CPU permaneció cerca de TjMax', 'El procesador pasó al menos 30 segundos a 10 °C o menos de su TjMax.', [f'Tiempo ≤10 °C de TjMax: {near10} s', f"Distancia mínima registrada: {tj['min']} °C", f"CPU Package promedio: {cpu['package_temp_c']['avg']} °C"], 'CorePulse policy based on hardware-reported Distance to TjMax'))
            else:
                findings.append(Finding('CPU', 'NORMAL', 'Sin proximidad térmica sostenida a TjMax', 'La sesión no mostró una permanencia prolongada dentro de 10 °C de TjMax.', [f'Tiempo ≤10 °C de TjMax: {near10} s', f"CPU Package promedio: {cpu['package_temp_c']['avg']} °C", f"CPU Package máximo: {cpu['package_temp_c']['max']} °C"], 'CorePulse policy based on hardware-reported Distance to TjMax'))
        else:
            findings.append(Finding('CPU', 'NO_EVALUABLE', 'Temperatura CPU no evaluable', 'No hubo suficientes muestras de Distance to TjMax para evaluar la condición térmica de CPU.', [], 'Availability rule'))
        ram = stats['ram']
        if ram['usage_percent']['samples'] > 0:
            valid = int(ram['usage_percent']['samples'] or 0)
            over85 = int(ram.get('seconds_over_85_percent') or 0)
            over90 = int(ram.get('seconds_over_90_percent') or 0)
            over95 = int(ram.get('seconds_over_95_percent') or 0)
            # Política CorePulse de presión de memoria adaptada a diagnósticos de 30-90 s.
            # No representa un límite físico del fabricante: describe presión sostenida de uso.
            extreme_required = max(12, min(30, int(round(valid * 0.40))))
            high_required = max(15, min(35, int(round(valid * 0.50))))
            elevated_required = max(18, min(45, int(round(valid * 0.60))))
            if over95 >= extreme_required:
                findings.append(Finding('RAM', 'WARNING', 'Presión extrema sostenida de memoria', 'La RAM permaneció en 95% o más durante una parte material de la sesión. Esto describe presión de memoria y posible paginación, no un fallo físico del módulo.', [f'Tiempo ≥95%: {over95} s', f"Uso promedio: {ram['usage_percent']['avg']}%", f"Uso máximo: {ram['usage_percent']['max']}%"], 'CorePulse RAM pressure policy: >=95% sustained'))
            elif over90 >= high_required:
                findings.append(Finding('RAM', 'WARNING', 'Uso alto sostenido de memoria', 'La RAM permaneció en 90% o más durante una parte importante de la sesión. CorePulse recomienda identificar la carga responsable y comprobar si la presión persiste en el uso habitual.', [f'Tiempo ≥90%: {over90} s', f"Uso promedio: {ram['usage_percent']['avg']}%", f"Uso máximo: {ram['usage_percent']['max']}%"], 'CorePulse RAM pressure policy: >=90% sustained'))
            elif over85 >= elevated_required:
                findings.append(Finding('RAM', 'INFO', 'Uso de RAM elevado pero no crítico', 'Se observó uso de RAM en 85% o más de forma sostenida, pero sin alcanzar el criterio de advertencia de CorePulse.', [f'Tiempo ≥85%: {over85} s', f"Uso promedio: {ram['usage_percent']['avg']}%", f"Uso máximo: {ram['usage_percent']['max']}%"], 'CorePulse RAM advisory policy: >=85% sustained'))
            else:
                findings.append(Finding('RAM', 'NORMAL', 'Sin presión sostenida de RAM', 'La sesión no mostró presión de memoria suficiente para activar una advertencia.', [f"Uso promedio: {ram['usage_percent']['avg']}%", f"Uso máximo: {ram['usage_percent']['max']}%"], 'CorePulse RAM pressure policy'))
        else:
            findings.append(Finding('RAM', 'NO_EVALUABLE', 'RAM no evaluable', 'No se recopilaron muestras válidas de uso de RAM.', [], 'Availability rule'))
        for name, drive in stats['storage'].items():
            used = _number(drive.get('used_space_percent'))
            if used is not None:
                free = max(0.0, 100.0 - used)
                if used >= 95.0:
                    findings.append(Finding(f'STORAGE:{name}', 'WARNING', 'Espacio libre críticamente reducido', 'La unidad alcanzó 95% o más de ocupación. Esta es una política de capacidad de CorePulse; no implica por sí sola degradación SMART.', [f'Espacio usado: {round(used, 1)}%', f'Espacio libre estimado por porcentaje: {round(free, 1)}%'], 'CorePulse storage capacity policy: >=95% used'))
                elif used >= 90.0:
                    findings.append(Finding(f'STORAGE:{name}', 'WARNING', 'Poco espacio libre en almacenamiento', 'La unidad alcanzó 90% o más de ocupación. CorePulse recomienda recuperar margen para actualizaciones, temporales y paginación.', [f'Espacio usado: {round(used, 1)}%', f'Espacio libre estimado por porcentaje: {round(free, 1)}%'], 'CorePulse storage capacity policy: >=90% used'))
                elif used >= 85.0:
                    findings.append(Finding(f'STORAGE:{name}', 'INFO', 'Margen de almacenamiento reducido', 'La unidad supera 85% de ocupación, pero todavía no alcanza el criterio de advertencia de CorePulse.', [f'Espacio usado: {round(used, 1)}%', f'Espacio libre estimado por porcentaje: {round(free, 1)}%'], 'CorePulse storage capacity advisory: >=85% used'))
            if drive['temperature_c']['samples'] == 0:
                findings.append(Finding(f'STORAGE:{name}', 'NO_EVALUABLE', 'Temperatura de almacenamiento no evaluable', 'El dispositivo no entregó temperatura actual válida durante la sesión.', [], 'Availability rule'))
                continue
            if drive['seconds_at_or_above_critical'] > 0:
                status = 'CRITICAL'
                title = 'Almacenamiento alcanzó el umbral crítico reportado'
            elif drive['seconds_at_or_above_warning'] >= 30:
                status = 'WARNING'
                title = 'Almacenamiento permaneció sobre su umbral de advertencia'
            else:
                status = 'NORMAL'
                title = 'Temperatura de almacenamiento dentro de sus umbrales reportados'
            evidence = [f"Temperatura promedio: {drive['temperature_c']['avg']} °C", f"Temperatura máxima: {drive['temperature_c']['max']} °C"]
            if drive['warning_temperature_c'] is not None:
                evidence.append(f"Umbral warning del dispositivo: {drive['warning_temperature_c']} °C")
            if drive['critical_temperature_c'] is not None:
                evidence.append(f"Umbral crítico del dispositivo: {drive['critical_temperature_c']} °C")
            if drive['life_percent'] is not None:
                evidence.append(f"Life reportado: {drive['life_percent']}%")
            findings.append(Finding(f'STORAGE:{name}', status, title, 'La clasificación térmica usa los umbrales que el propio dispositivo/proveedor reporta.', evidence, 'Device-reported storage thresholds'))
        for name, gpu in stats['gpus'].items():
            if gpu['temperature_c']['samples'] == 0:
                findings.append(Finding(f'GPU:{name}', 'NO_EVALUABLE', 'Temperatura GPU no evaluable', 'No se obtuvo temperatura GPU válida durante la sesión.', [], 'Availability rule'))
            else:
                findings.append(Finding(f'GPU:{name}', 'INFO', 'Telemetría GPU recopilada', 'CorePulse conserva temperatura, hotspot y uso, pero V0.6 no declara salud térmica GPU sin un límite específico del modelo/proveedor.', [f"Temperatura promedio: {gpu['temperature_c']['avg']} °C", f"Temperatura máxima: {gpu['temperature_c']['max']} °C", f"Hotspot máximo: {gpu['hotspot_c']['max']} °C", f"Uso máximo: {gpu['usage_percent']['max']}%"], 'Evidence-only GPU rule'))
        battery = stats.get('battery')
        if battery:
            degradation = _number(battery.get('degradation_percent'))
            if degradation is not None:
                findings.append(Finding('BATTERY', 'INFO', 'Desgaste de batería reportado', 'Se registra la degradación que expone el proveedor. V0.6 no la interpreta como fallo automático.', [f'Degradación reportada: {degradation}%', f"Capacidad de diseño: {battery.get('designed_capacity_mwh')} mWh", f"Capacidad carga completa: {battery.get('full_charge_capacity_mwh')} mWh"], 'Provider-reported battery degradation'))
        return findings

    @staticmethod
    def _overall_status(findings):
        statuses = {f.status for f in findings}
        if 'CRITICAL' in statuses:
            return 'CRITICAL'
        if 'WARNING' in statuses:
            return 'WARNING'
        evaluable = [f for f in findings if f.status not in {'INFO', 'NO_EVALUABLE'}]
        if evaluable and all((f.status == 'NORMAL' for f in evaluable)):
            return 'NORMAL'
        return 'NO_EVALUABLE'

    def save_json(self, path=None):
        with self._lock:
            if self._result is None:
                return None
            if path is None:
                output_root = diagnostics_dir()
                output_root.mkdir(parents=True, exist_ok=True)
                path = output_root / f'CorePulse_Diagnostic_{datetime.now():%Y%m%d_%H%M%S}.json'
            else:
                path = Path(path)
                path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(self._result, indent=2, ensure_ascii=False), encoding='utf-8')
            return str(path)

# V483: fusión conservadora desde core/diagnostics/adaptive_diagnostic.py; importar módulo antiguo sigue funcionando.
from core.version import VERSION_LABEL as VERSION

import time

POLICY = 'FAST_ADAPTIVE_EVIDENCE'

DEFAULT_MIN_SECONDS = 30

DEFAULT_MAX_SECONDS = 90

DEFAULT_MIN_SAMPLES = 25

DEFAULT_CONTEXT_STABILITY_SECONDS = 8

DEFAULT_ALERT_STABILITY_SECONDS = 12

def readiness_stage(info):
    """Gestiona la operación `readiness_stage` dentro de CorePulse sin alterar la evidencia real ni las reglas del módulo."""
    if not isinstance(info, dict):
        return 'Preparando evidencia'
    if info.get('ready'):
        return 'Evidencia suficiente'
    waiting = list(info.get('waiting_for') or [])
    if 'confirmando alertas' in waiting:
        return 'Confirmando condición'
    if 'observación de juego' in waiting or 'estabilizando contexto' in waiting:
        return 'Estabilizando contexto'
    if 'cobertura de sensores' in waiting:
        return 'Validando sensores'
    if 'muestras válidas' in waiting:
        return 'Recopilando muestras'
    return 'Analizando evidencia'

class AdaptiveDiagnosticSession(DiagnosticSession):
    """Clase responsable de `AdaptiveDiagnosticSession` dentro de CorePulse. Conserva los contratos de integridad del módulo."""

    def __init__(self, min_seconds=DEFAULT_MIN_SECONDS, max_seconds=DEFAULT_MAX_SECONDS, min_samples=DEFAULT_MIN_SAMPLES, context_stability_seconds=DEFAULT_CONTEXT_STABILITY_SECONDS, alert_stability_seconds=DEFAULT_ALERT_STABILITY_SECONDS):
        super().__init__(duration_seconds=max_seconds)
        self.min_seconds = max(30, int(min_seconds))
        self.max_seconds = max(self.min_seconds + 30, int(max_seconds))
        self.min_samples = max(DEFAULT_MIN_SAMPLES, int(min_samples))
        self.context_stability_seconds = max(5, int(context_stability_seconds))
        self.alert_stability_seconds = max(5, int(alert_stability_seconds))
        self._last_context = None
        self._context_since = None
        self._last_alert_signature = None
        self._alert_signature_since = None
        self._last_readiness = None

    def start(self):
        super().start()
        now = time.monotonic()
        self._last_context = None
        self._context_since = now
        self._last_alert_signature = None
        self._alert_signature_since = now
        self._last_readiness = None

    @staticmethod
    def _num(value):
        return isinstance(value, (int, float)) and (not isinstance(value, bool))

    def _samples_copy(self):
        with self._lock:
            return list(self._samples)

    def _coverage(self, samples):
        total = max(1, len(samples))
        cpu = sum((1 for sample in samples if self._num(sample.get('cpu_usage_percent')) or self._num(sample.get('cpu_package_temp_c')))) / total
        ram = sum((1 for sample in samples if self._num(sample.get('ram_usage_percent')))) / total
        return {'cpu': cpu, 'ram': ram}

    @staticmethod
    def _context(state):
        if not isinstance(state, dict):
            return 'UNKNOWN'
        return str(state.get('context') or state.get('mode') or 'UNKNOWN').upper()

    @staticmethod
    def _alert_signature(state):
        if not isinstance(state, dict):
            return ()
        alerts = state.get('alerts') or {}
        active = alerts.get('active') if isinstance(alerts, dict) else []
        output = []
        if isinstance(active, list):
            for item in active:
                if not isinstance(item, dict):
                    continue
                level = str(item.get('level') or '').upper()
                if level in {'WARNING', 'CRITICAL'}:
                    output.append((str(item.get('key') or item.get('title') or ''), level))
        return tuple(sorted(output))

    def _update_stability(self, state, now):
        context = self._context(state)
        if context != self._last_context:
            self._last_context = context
            self._context_since = now
        signature = self._alert_signature(state)
        if signature != self._last_alert_signature:
            self._last_alert_signature = signature
            self._alert_signature_since = now
        return (context, signature)

    def _target_seconds(self, context, alert_signature):
        target = self.min_seconds
        if context.startswith('GAME'):
            target = max(target, self.min_seconds + 15)
        if alert_signature:
            target = max(target, self.min_seconds + 30)
        return min(target, self.max_seconds)

    def readiness(self, state=None):
        now = time.monotonic()
        elapsed = float(self.elapsed_seconds())
        samples = self._samples_copy()
        coverage = self._coverage(samples)
        context, alert_signature = self._update_stability(state, now)
        context_stable = max(0.0, now - (self._context_since or now))
        alert_stable = max(0.0, now - (self._alert_signature_since or now))
        target = self._target_seconds(context, alert_signature)
        observation = (state or {}).get('observation') if isinstance(state, dict) else {}
        observation = observation if isinstance(observation, dict) else {}
        game_ok = True
        game_remaining = 0.0
        if context == 'GAME_OBSERVING':
            game_ok = False
            game_remaining = float(observation.get('remaining_seconds') or 0.0)
        elif context == 'GAME_ACTIVE' and observation:
            game_ok = bool(observation.get('complete', False))
            game_remaining = float(observation.get('remaining_seconds') or 0.0)
        context_ok = context in {'UNKNOWN', 'DESKTOP'} or context_stable >= self.context_stability_seconds
        if context == 'GAME_OBSERVING':
            context_ok = False
        alert_ok = not alert_signature or alert_stable >= self.alert_stability_seconds
        time_ok = elapsed >= target
        samples_ok = len(samples) >= self.min_samples
        cpu_ok = coverage['cpu'] >= 0.75
        ram_ok = coverage['ram'] >= 0.75
        ready = time_ok and samples_ok and cpu_ok and ram_ok and game_ok and context_ok and alert_ok
        max_reached = elapsed >= self.max_seconds
        p_time = min(1.0, elapsed / max(1, target))
        p_samples = min(1.0, len(samples) / max(1, self.min_samples))
        p_coverage = min(coverage['cpu'], coverage['ram'])
        p_context = 1.0 if game_ok and context_ok else 0.35
        p_alert = 1.0 if alert_ok else min(0.95, alert_stable / self.alert_stability_seconds)
        progress = 0.35 * p_time + 0.25 * p_samples + 0.2 * p_coverage + 0.1 * p_context + 0.1 * p_alert
        if ready:
            progress = 1.0
        elif max_reached:
            progress = max(progress, 0.99)
        remains = [max(0.0, target - elapsed), max(0.0, self.min_samples - len(samples)), max(0.0, self.context_stability_seconds - context_stable) if not context_ok else 0.0, max(0.0, self.alert_stability_seconds - alert_stable) if not alert_ok else 0.0, game_remaining]
        waiting = []
        if not time_ok:
            waiting.append('acumulando evidencia')
        if not samples_ok:
            waiting.append('muestras válidas')
        if not cpu_ok or not ram_ok:
            waiting.append('cobertura de sensores')
        if not game_ok:
            waiting.append('observación de juego')
        if not context_ok:
            waiting.append('estabilizando contexto')
        if not alert_ok:
            waiting.append('confirmando alertas')
        info = {'ready': ready, 'max_reached': max_reached, 'progress': round(max(0.0, min(1.0, progress)), 4), 'confidence_percent': round(max(0.0, min(100.0, progress * 100)), 1), 'eta_seconds': 0 if ready else int(round(max(remains))), 'elapsed_seconds': round(elapsed, 1), 'target_seconds': int(target), 'sample_count': len(samples), 'minimum_samples': int(self.min_samples), 'coverage': coverage, 'context': context, 'active_sustained_alerts': len(alert_signature), 'waiting_for': waiting, 'stage': readiness_stage({'ready': ready, 'waiting_for': waiting})}
        self._last_readiness = info
        return info

    def should_finish(self, state=None):
        if not self.active:
            return False
        info = self.readiness(state)
        return bool(info['ready'] or info['max_reached'])

    def remaining_seconds(self, state=None):
        return int(self.readiness(state)['eta_seconds'])

    def finish(self, state=None):
        info = self.readiness(state)
        actual = max(1, int(round(self.elapsed_seconds())))
        old_duration = self.duration_seconds
        self.duration_seconds = actual
        try:
            result = super().finish()
        finally:
            self.duration_seconds = old_duration
        if isinstance(result, dict):
            result['corepulse_version'] = VERSION
            result['session_valid'] = bool(info['ready'])
            result['completion_status'] = 'EVIDENCE_READY' if info['ready'] else 'SAFETY_CAP_PARTIAL'
            result['required_duration_seconds'] = None
            result['duration_policy'] = POLICY
            result['report_unlock_policy'] = 'EVIDENCE_READY_OR_SAFETY_CAP'
            result['adaptive_diagnostic'] = {**info, 'min_seconds': self.min_seconds, 'max_seconds': self.max_seconds, 'min_samples': self.min_samples, 'finish_reason': 'EVIDENCE_READY' if info['ready'] else 'MAX_TIME_REACHED'}
        return result
