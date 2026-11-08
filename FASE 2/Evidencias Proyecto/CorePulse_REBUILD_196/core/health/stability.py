"""Prueba manual de estabilidad CPU/RAM sin puntuaciones de benchmark."""
from __future__ import annotations

import concurrent.futures
from concurrent.futures.thread import ThreadPoolExecutor
import hashlib
import math
import os
import threading
import time
from datetime import datetime

import psutil
from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot


def _number(value):
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return result if math.isfinite(result) else None


def _stats(values):
    clean = [value for value in (_number(item) for item in values) if value is not None]
    if not clean:
        return {'samples': 0, 'min': None, 'max': None, 'avg': None}
    return {'samples': len(clean), 'min': round(min(clean), 1),
            'max': round(max(clean), 1), 'avg': round(sum(clean) / len(clean), 1)}


class _ThermalWatch:
    """Aplica cortes térmicos conservadores a la telemetría disponible."""

    def __init__(self, sampler):
        self._sampler = sampler
        self._last_sample = 0.0
        self._rows = []
        self._cpu_hits = 0
        self._gpu_hits = 0
        self.stop_reason = ''

    def sample(self):
        now = time.monotonic()
        if now - self._last_sample < 0.8:
            return
        self._last_sample = now
        try:
            metrics = self._sampler() or {}
        except Exception:
            metrics = {}
        if not isinstance(metrics, dict):
            return
        cpu_temp = _number(metrics.get('cpuTemp'))
        gpu_temp = _number(metrics.get('gpuTemp'))
        self._rows.append({
            'cpuTemp': cpu_temp,
            'gpuTemp': gpu_temp,
            'cpuPercent': _number(metrics.get('cpuPercent')),
            'gpuPercent': _number(metrics.get('gpuPercent')),
            'ramPercent': _number(metrics.get('ramPercent')),
        })
        self._cpu_hits = self._cpu_hits + 1 if cpu_temp is not None and cpu_temp >= 105.0 else 0
        self._gpu_hits = self._gpu_hits + 1 if gpu_temp is not None and gpu_temp >= 95.0 else 0
        if self._cpu_hits >= 3:
            self.stop_reason = f'Seguridad térmica: CPU permaneció en {cpu_temp:.1f} °C'
        elif self._gpu_hits >= 3:
            self.stop_reason = f'Seguridad térmica: GPU permaneció en {gpu_temp:.1f} °C'

    @property
    def should_stop(self):
        self.sample()
        return bool(self.stop_reason)

    def summary(self):
        return {
            'sampleCount': len(self._rows),
            'cpuTemp': _stats(row['cpuTemp'] for row in self._rows),
            'gpuTemp': _stats(row['gpuTemp'] for row in self._rows),
            'cpuPercent': _stats(row['cpuPercent'] for row in self._rows),
            'gpuPercent': _stats(row['gpuPercent'] for row in self._rows),
            'ramPercent': _stats(row['ramPercent'] for row in self._rows),
            'safetyStop': self.stop_reason,
        }


def _cpu_phase(seconds, monitor, cancel, report):
    workers = max(1, min(int(os.cpu_count() or 1), 24))
    block = (b'CorePulse CPU stress\0' * 16384)[:256 * 1024]
    stop = threading.Event()

    def worker():
        digest = b''
        while not stop.is_set():
            digest = hashlib.sha256(block + digest).digest()

    started = time.perf_counter()
    pool = ThreadPoolExecutor(
        max_workers=workers, thread_name_prefix='CorePulse-StabilityCPU')
    futures = [pool.submit(worker) for _ in range(workers)]
    try:
        deadline = started + seconds
        while time.perf_counter() < deadline and not monitor.should_stop and not cancel.is_set():
            fraction = min(1.0, (time.perf_counter() - started) / seconds)
            report(fraction, 'CPU', f'Carga multinúcleo · {workers} hilos')
            time.sleep(0.25)
    finally:
        stop.set()
        pool.shutdown(wait=True, cancel_futures=True)
    elapsed = round(time.perf_counter() - started, 2)
    status = 'CANCELLED' if cancel.is_set() else 'SAFETY_STOP' if monitor.stop_reason else 'OK'
    reason = 'Cancelada por el usuario' if cancel.is_set() else monitor.stop_reason
    return {'status': status, 'durationS': elapsed, 'threads': workers,
            'reason': reason, 'telemetry': monitor.summary()}


def _ram_phase(seconds, monitor, cancel, report):
    available_mb = int(psutil.virtual_memory().available / (1024 * 1024))
    if available_mb < 512:
        return {'status': 'NOT_RUN_LOW_MEMORY', 'durationS': 0,
                'reason': 'Memoria disponible insuficiente para reservar la prueba con seguridad.',
                'telemetry': monitor.summary()}
    size_mb = max(64, min(192, int(available_mb * 0.06)))
    size_bytes = size_mb * 1024 * 1024
    try:
        source = bytearray(size_bytes)
        target = bytearray(size_bytes)
    except MemoryError:
        return {'status': 'NOT_RUN_LOW_MEMORY', 'durationS': 0,
                'reason': 'Windows no pudo reservar el bloque de memoria de la prueba.',
                'telemetry': monitor.summary()}
    seed = b'CorePulse-RAM-Stress' * 4096
    source[:min(len(seed), size_bytes)] = seed[:min(len(seed), size_bytes)]
    view_source = memoryview(source)
    view_target = memoryview(target)
    started = time.perf_counter()
    try:
        while time.perf_counter() - started < seconds and not monitor.should_stop and not cancel.is_set():
            view_target[:] = view_source
            source, target = target, source
            view_source, view_target = memoryview(source), memoryview(target)
            fraction = min(1.0, (time.perf_counter() - started) / seconds)
            report(fraction, 'RAM', f'Presión sostenida · {size_mb} MB')
    finally:
        del view_source, view_target, source, target
    elapsed = round(time.perf_counter() - started, 2)
    status = 'CANCELLED' if cancel.is_set() else 'SAFETY_STOP' if monitor.stop_reason else 'OK'
    reason = 'Cancelada por el usuario' if cancel.is_set() else monitor.stop_reason
    return {'status': status, 'durationS': elapsed, 'workingSetMb': size_mb,
            'reason': reason, 'telemetry': monitor.summary()}


def _run_suite(sampler, cancel, progress):
    started = time.perf_counter()
    watch = _ThermalWatch(sampler)
    components = {}
    phases = (('cpu', 10.0, 0.0, 0.59), ('ram', 7.0, 0.59, 1.0))
    for key, seconds, start, end in phases:
        if cancel.is_set():
            components[key] = {'status': 'CANCELLED', 'durationS': 0,
                               'reason': 'Cancelada por el usuario', 'telemetry': watch.summary()}
            continue
        if watch.should_stop:
            components[key] = {'status': 'SAFETY_STOP', 'durationS': 0,
                               'reason': watch.stop_reason, 'telemetry': watch.summary()}
            continue

        def report(fraction, phase, detail, _start=start, _end=end):
            progress(_start + (_end - _start) * fraction, phase, detail)

        result = (_cpu_phase(seconds, watch, cancel, report) if key == 'cpu'
                  else _ram_phase(seconds, watch, cancel, report))
        components[key] = result

    statuses = [components[key]['status'] for key in ('cpu', 'ram')]
    overall = ('CANCELLED' if 'CANCELLED' in statuses else
               'SAFETY_STOP' if 'SAFETY_STOP' in statuses else
               'PARTIAL' if any(status != 'OK' for status in statuses) else 'OK')
    progress(1.0, 'Finalizada', 'La prueba no calcula rendimiento ni puntuaciones.')
    return {
        'status': overall,
        'durationS': round(time.perf_counter() - started, 2),
        'components': components,
        'gpu': {'status': 'EXCLUDED',
                'reason': 'La carga GPU corresponde al benchmark, excluido de esta migración.'},
        'telemetry': watch.summary(),
        'policy': 'STABILITY_UNDER_LOAD_NO_PERFORMANCE_SCORE',
        'lastUpdate': datetime.now().strftime('%H:%M:%S'),
    }


class StabilityHealth(QObject):
    changed = Signal()

    def __init__(self, telemetry, parent=None):
        super().__init__(parent)
        self.telemetry = telemetry
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix='corepulse-stability')
        self._future = None
        self._cancel = threading.Event()
        self._closed = False
        self._lock = threading.Lock()
        self._latest_metrics = {}
        self._pending = None
        self._data = {
            'busy': False, 'status': 'NOT_RUN', 'progress': 0,
            'phase': 'Sin ejecutar', 'message': 'Prueba opcional; requiere confirmación.',
            'components': {}, 'gpu': {'status': 'EXCLUDED',
                                      'reason': 'Benchmark excluido de esta migración.'},
            'telemetry': {}, 'lastUpdate': 'N/A',
        }
        self._poll = QTimer(self)
        self._poll.setInterval(200)
        self._poll.timeout.connect(self._check)

    @Property('QVariantMap', notify=changed)
    def data(self):
        return self._data

    @Slot()
    def start(self):
        if self._closed or self._future is not None:
            return
        self._cancel.clear()
        self._data = {**self._data, 'busy': True, 'status': 'RUNNING', 'progress': 0,
                      'phase': 'Preparando CPU', 'message': 'La prueba puede ralentizar el equipo temporalmente.',
                      'components': {}, 'lastUpdate': 'N/A'}
        self.changed.emit()
        self._future = self._executor.submit(
            _run_suite, self._sample_metrics, self._cancel, self._report_progress)
        self._poll.start()

    def _sample_metrics(self):
        with self._lock:
            return dict(self._latest_metrics)

    def _report_progress(self, fraction, phase, detail):
        with self._lock:
            self._pending = {'progress': max(0, min(100, int(fraction * 100))),
                             'phase': str(phase), 'message': str(detail)}

    @Slot()
    def cancel(self):
        if self._future is not None:
            self._cancel.set()
            self._data = {**self._data, 'phase': 'Cancelando',
                          'message': 'La fase actual está terminando de forma segura.'}
            self.changed.emit()

    @Slot()
    def _check(self):
        try:
            metrics = self.telemetry.metrics
            if isinstance(metrics, dict):
                with self._lock:
                    self._latest_metrics = dict(metrics)
        except Exception:
            pass
        with self._lock:
            pending, self._pending = self._pending, None
        if pending:
            self._data = {**self._data, **pending}
            self.changed.emit()
        if self._future is None or not self._future.done():
            return
        try:
            result = self._future.result()
        except Exception as exc:
            result = {'status': 'ERROR', 'durationS': 0, 'components': {},
                      'gpu': {'status': 'EXCLUDED', 'reason': 'Benchmark excluido de esta migración.'},
                      'telemetry': {}, 'lastUpdate': datetime.now().strftime('%H:%M:%S'),
                      'message': f'La prueba no pudo completarse: {type(exc).__name__}.'}
        self._future = None
        self._poll.stop()
        self._data = {'busy': False, 'progress': 100, 'phase': 'Finalizada',
                      'message': result.pop('message', 'Prueba de estabilidad finalizada.'),
                      **result}
        self.changed.emit()

    @Slot()
    def close(self):
        self._closed = True
        self._cancel.set()
        self._poll.stop()
        self._executor.shutdown(wait=False, cancel_futures=True)
