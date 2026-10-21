"""Benchmark CorePulse CPU/RAM/SSD y DirectX 11 V29 en proceso aislado.
No altera drivers, energía, reloj ni preferencias de Windows.
REAL_OR_NA: GPU sólo tiene FPS cuando DirectX presenta fotogramas reales.
"""
from __future__ import annotations

from concurrent.futures.thread import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import csv
import json
import math
import os
import sys
import subprocess
import queue
import uuid
from pathlib import Path
import tempfile
import threading
import time

import re

import psutil
from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot, QUrl

from core.monitoring.telemetry import nvidia_smi_executable


METHOD = 'COREPULSE_REBUILD_CPU_RAM_SSD_STAGE1_070'
# Debe ser idéntico a GPU_BENCHMARK_METHOD de core/benchmark_gpu.py (la GUI no
# importa el renderer nativo). Hasta V26 quedó en V25 y la app rechazaba todo
# resultado GPU válido; la prueba test_072 vigila que coincidan.
GPU_METHOD = 'COREPULSE_GPU_DIRECTX11_SCENES_V29_NEON_CITY_REFLECTIONS_HDR_MSAA_FIXED1080P_PRESENT_INTERVAL_WALLCLOCK_DETERMINISTIC'
GPU_SCRIPT = Path(__file__).with_name('benchmark_gpu.py')
GPU_PROFILES = ('quick', 'standard', 'extended')
HISTORY_LIMIT = 500
_HISTORY_LOCK = threading.Lock()

_NVIDIA_FIELDS = 'index,name,temperature.gpu,utilization.gpu,clocks.gr,clocks.max.gr,power.draw,power.limit,pstate,'
# Drivers 535+ renombraron throttle -> event; se prueba el nombre nuevo primero.
_NVIDIA_REASON_FIELDS = ('clocks_event_reasons.active', 'clocks_throttle_reasons.active')
# Bits NVML de motivos de reducción de reloj que sí indican un límite físico.
_NVIDIA_THERMAL_BITS = {0x20: 'límite térmico (software)', 0x40: 'límite térmico (hardware)'}
_NVIDIA_HW_BITS = {0x08: 'desaceleración por hardware', 0x80: 'freno de energía externo'}
_NVIDIA_POWER_CAP = 0x04  # Normal en carga máxima: GPU Boost llega a su objetivo de consumo.


def _nv_number(text):
    try:
        value = float(str(text).strip())
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def parse_nvidia_session_line(line):
    """Una línea CSV del bucle nvidia-smi -> muestra o None si no es de datos."""
    parts = [p.strip() for p in str(line or '').split(',')]
    if len(parts) != 10 or not parts[0].isdigit():
        return None
    reasons = None
    try:
        reasons = int(parts[9], 16) if parts[9].lower().startswith('0x') else None
    except ValueError:
        reasons = None
    return {'index': int(parts[0]), 'name': parts[1], 'temp_c': _nv_number(parts[2]),
            'util_pct': _nv_number(parts[3]), 'clock_mhz': _nv_number(parts[4]),
            'clock_max_mhz': _nv_number(parts[5]), 'power_w': _nv_number(parts[6]),
            'power_limit_w': _nv_number(parts[7]), 'pstate': parts[8] or None, 'reasons': reasons}


def _power_context():
    """Fuente de energía y plan activo. Solo lectura; nada se cambia."""
    context = {'has_battery': False, 'on_battery': False, 'battery_percent': None, 'power_plan': None}
    try:
        battery = psutil.sensors_battery()
    except (OSError, RuntimeError, AttributeError):
        battery = None
    if battery is not None:
        context.update(has_battery=True, on_battery=not bool(battery.power_plugged),
                       battery_percent=round(float(battery.percent), 1) if battery.percent is not None else None)
    if os.name == 'nt':
        try:
            out = subprocess.run(['powercfg', '/getactivescheme'], capture_output=True, text=True,
                                 timeout=4, check=False, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)).stdout
            match = re.search(r'\(([^()]+)\)\s*$', out.strip())
            context['power_plan'] = match.group(1).strip() if match else None
        except (OSError, subprocess.TimeoutExpired):
            pass
    return context


class GpuSessionMonitor:
    """Sensores durante la prueba GPU, tomados en el proceso de CorePulse.

    El worker DirectX no lee sensores (V26 los dejaba vacíos). Aquí se usa un
    único proceso ``nvidia-smi --loop-ms`` en lugar de lanzar uno por muestra,
    para no robar CPU a la medición. AMD/Intel no exponen estos datos sin
    drivers extra: quedan N/A. No se deduce throttling de los FPS porque el
    contenido de cada escena varía a lo largo del recorrido de cámara.
    """

    def __init__(self, interval_ms=1000):
        self.interval_ms = int(interval_ms)
        self.samples = []
        self.stage = ''
        self.power_start = {}
        self.power_end = {}
        self.sensor_reason = None
        self._process = None
        self._thread = None
        self._lock = threading.Lock()
        self._t0 = time.monotonic()

    def _fields(self, executable):
        for reason_field in _NVIDIA_REASON_FIELDS:
            try:
                probe = subprocess.run([executable, '--query-gpu=' + _NVIDIA_FIELDS + reason_field,
                                        '--format=csv,noheader,nounits'], capture_output=True, text=True,
                                       timeout=4, check=False, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            except (OSError, subprocess.TimeoutExpired):
                return None
            if probe.returncode == 0 and any(parse_nvidia_session_line(l) for l in probe.stdout.splitlines()):
                return _NVIDIA_FIELDS + reason_field
        return None

    def start(self):
        self._t0 = time.monotonic()
        self.power_start = _power_context()
        executable = nvidia_smi_executable()
        fields = self._fields(executable) if executable else None
        if not fields:
            self.sensor_reason = 'nvidia-smi no disponible: sensores en vivo solo para NVIDIA'
            return self
        try:
            self._process = subprocess.Popen(
                [executable, '--query-gpu=' + fields, '--format=csv,noheader,nounits', f'--loop-ms={self.interval_ms}'],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding='utf-8', errors='replace',
                bufsize=1, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        except OSError as error:
            self.sensor_reason = 'nvidia-smi no se pudo iniciar: ' + str(error)[:80]
            return self
        def reader():
            for line in self._process.stdout:
                sample = parse_nvidia_session_line(line)
                if sample:
                    with self._lock:
                        sample.update(t=round(time.monotonic() - self._t0, 2), stage=self.stage)
                        self.samples.append(sample)
        self._thread = threading.Thread(target=reader, daemon=True, name='corepulse-gpu-sensors')
        self._thread.start()
        return self

    def set_stage(self, stage):
        with self._lock:
            self.stage = str(stage or '')[:80]

    def stop(self):
        if self._process is not None and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._process.kill()
        if self._thread is not None:
            self._thread.join(timeout=1)
        self.power_end = _power_context()
        return self

    def summary(self, result):
        with self._lock:
            samples = list(self.samples)
        return summarize_gpu_session(result or {}, samples, self.power_start, self.power_end, self.sensor_reason)


def _pick_gpu_samples(samples, renderer):
    """Filas de nvidia-smi que corresponden a la GPU que renderizó."""
    renderer = str(renderer or '').lower()
    if not samples or 'nvidia' not in renderer:
        return []
    names = {s['index']: s['name'].lower() for s in samples}
    match = [i for i, name in names.items() if name and (name in renderer or renderer in name)]
    if not match and len(names) == 1:
        match = list(names)
    return [s for s in samples if s['index'] in match[:1]]


def summarize_gpu_session(result, samples, power_start, power_end, sensor_reason=None):
    """Condiciones de la prueba y veredicto de estabilidad, sin inventar datos."""
    renderer = result.get('renderer') or ''
    rows = _pick_gpu_samples(samples, renderer)
    loaded = [s for s in rows if (s.get('util_pct') or 0) >= 50] or rows
    def values(key, source=loaded):
        return [s[key] for s in source if isinstance(s.get(key), (int, float))]
    temps, clocks, powers = values('temp_c', rows), values('clock_mhz'), values('power_w')
    reason_rows = [s for s in loaded if isinstance(s.get('reasons'), int)]
    def share(bits):
        return (sum(1 for s in reason_rows if s['reasons'] & bits) / len(reason_rows)) if reason_rows else None
    thermal_bits = sum(_NVIDIA_THERMAL_BITS); hw_bits = sum(_NVIDIA_HW_BITS)
    seen = sorted({label for s in reason_rows for bit, label in {**_NVIDIA_THERMAL_BITS, **_NVIDIA_HW_BITS}.items() if s['reasons'] & bit})
    if rows:
        sensor_status = 'NVIDIA_SMI'
    elif 'nvidia' in renderer.lower():
        sensor_status = 'N/A: ' + (sensor_reason or 'sin muestras de nvidia-smi')
    else:
        sensor_status = 'N/A: temperatura y relojes en vivo solo para NVIDIA (nvidia-smi)'
    # Relojes con la GPU al 90 %+: si quedan muy por debajo del máximo sin que
    # el driver informe motivo, suele ser una curva/límite de software de
    # terceros, el modo de energía del driver o un perfil del fabricante.
    full = [s for s in rows if (s.get('util_pct') or 0) >= 90 and s.get('clock_mhz') and s.get('clock_max_mhz')]
    clock_ratio = (sum(s['clock_mhz'] for s in full) / sum(s['clock_max_mhz'] for s in full)) if len(full) >= 5 else None
    thermal_share, hw_share = share(thermal_bits), share(hw_bits)
    if (thermal_share or 0) >= 0.10 or (hw_share or 0) >= 0.10:
        verdict = 'THROTTLING'
    elif clock_ratio is not None and clock_ratio < 0.75 and not (share(_NVIDIA_POWER_CAP) or 0) >= 0.5:
        verdict = 'RELOJ_BAJO'
    elif rows:
        verdict = 'ESTABLE'
    else:
        verdict = 'SIN_DATOS'
    on_battery = bool(power_start.get('on_battery') or power_end.get('on_battery'))
    plan = power_start.get('power_plan') or ''
    warnings = []
    if on_battery:
        warnings.append('Notebook con batería durante la prueba: Windows y el fabricante limitan la GPU. Conecta el cargador para un resultado representativo.')
    if power_start.get('has_battery') and power_end and power_start.get('on_battery') != power_end.get('on_battery'):
        warnings.append('La fuente de energía cambió durante la prueba.')
    if re.search(r'ahorro|saver|economizador', plan, re.I):
        warnings.append('Plan de energía «' + plan + '»: limita el rendimiento. Usa Equilibrado o Alto rendimiento.')
    adapters = [a for a in (result.get('adapters_detected') or []) if isinstance(a, dict) and not a.get('software')]
    if result.get('adapter_selection') == 'WINDOWS_DEFAULT' and len(adapters) > 1:
        warnings.append('No se pudo elegir la GPU de alto rendimiento; Windows usó su adaptador predeterminado.')
    if verdict == 'THROTTLING':
        warnings.append('La GPU redujo relojes por ' + ', '.join(seen) + (f' (máx. {max(temps):.0f} °C)' if temps else '') + '. Revisa ventilación, polvo o base refrigerante en notebooks.')
    elif verdict == 'RELOJ_BAJO':
        max_clock = max(s['clock_max_mhz'] for s in full)
        warnings.append(f'Con la GPU al máximo, el reloj promedió {clock_ratio * 100:.0f} % de sus {max_clock:.0f} MHz sin motivo informado por el driver. '
                        'Revisa curvas o límites de MSI Afterburner u otro software, el modo de energía del panel NVIDIA o el perfil del fabricante.')
    if result.get('window_mode') == 'BORDERLESS_FULLSCREEN_SCALED':
        warnings.append('Pantalla menor que 1920×1080: se renderiza igual a 1920×1080 y se escala a la pantalla; el resultado sigue siendo comparable.')
    if result.get('dpi_awareness') in ('UNAWARE', 'N/A') and os.name == 'nt':
        warnings.append('Windows no aceptó el modo DPI real; la ventana puede verse escalada.')
    if result.get('bottleneck') == 'CPU_O_SISTEMA':
        warnings.append('En la escena principal la GPU estuvo ociosa parte del tiempo: el resultado depende también de la CPU o del sistema.')
    return {
        'sensor_status': sensor_status, 'samples': len(rows),
        'gpu_temp_start_c': temps[0] if temps else None, 'gpu_temp_max_c': max(temps) if temps else None,
        'gpu_clock_avg_mhz': round(sum(clocks) / len(clocks)) if clocks else None,
        'gpu_clock_min_mhz': min(clocks) if clocks else None,
        'gpu_power_avg_w': round(sum(powers) / len(powers), 1) if powers else None,
        'gpu_power_limit_w': next((s['power_limit_w'] for s in rows if s.get('power_limit_w')), None),
        'throttle_thermal_share': thermal_share, 'throttle_hardware_share': hw_share,
        'power_cap_share': share(_NVIDIA_POWER_CAP), 'throttle_reasons_seen': seen,
        'gpu_clock_to_max_ratio': clock_ratio, 'stability': verdict,
        'has_battery': bool(power_start.get('has_battery')), 'on_battery': on_battery,
        'battery_percent': power_start.get('battery_percent'), 'power_plan': plan or None,
        'device_class': 'NOTEBOOK' if power_start.get('has_battery') else 'ESCRITORIO',
        'warnings': warnings,
        'timeline': [{k: s.get(k) for k in ('t', 'stage', 'temp_c', 'util_pct', 'clock_mhz', 'power_w', 'reasons')} for s in rows][-600:],
    }


def _speed(measured_bytes, elapsed):
    return round(measured_bytes / (1024 * 1024) / elapsed, 2) if elapsed > 0 and measured_bytes > 0 else None


def _cpu_workload(duration, cancel):
    """Trabajo aritmético determinista. Mide bloques enteros completados/segundo."""
    completed, checksum = 0, 0
    started = time.perf_counter()
    while time.perf_counter() - started < duration:
        if cancel.is_set():
            return None
        accumulator = 0
        for i in range(60000):
            accumulator = (accumulator * 1664525 + 1013904223 + i) & 0xFFFFFFFF
        checksum ^= accumulator
        completed += 60000
    elapsed = time.perf_counter() - started
    return {'operations': completed, 'seconds': round(elapsed, 3),
            'operationsPerSecond': round(completed / elapsed) if elapsed > 0 else None,
            'checksum': checksum, 'unit': 'iteraciones enteras/s',
            'method': 'Bucle entero Python de 60 000 iteraciones por bloque'}


def _ram_workload(duration, cancel):
    """Copias verificadas de 8 MiB; NO afirma ser ancho de banda físico de RAM."""
    size = 8 * 1024 * 1024
    source = bytes((i % 251 for i in range(251))) * (size // 251) + bytes(i % 251 for i in range(size % 251))
    destination = bytearray(size)
    copied = 0
    started = time.perf_counter()
    while time.perf_counter() - started < duration:
        if cancel.is_set():
            return None
        destination[:] = source
        if destination[:512] != source[:512] or destination[-512:] != source[-512:]:
            raise RuntimeError('La verificación de copia RAM no coincidió.')
        copied += size
    elapsed = time.perf_counter() - started
    return {'bytesCopied': copied, 'seconds': round(elapsed, 3), 'mibPerSecond': _speed(copied, elapsed),
            'unit': 'MiB/s de copia desde Python', 'method': 'Bloques verificados de 8 MiB (influido por cachés)'}


def _ssd_workload(cancel, *, folder=None, size=16 * 1024 * 1024):
    """Archivo temporal real con flush/fsync y lectura, borrado incluso en error.

    Las lecturas pueden beneficiarse de caché OS. Se informa como I/O de archivo,
    no como velocidad física sin caché ni métrica CrystalDiskMark.
    """
    if cancel.is_set():
        return None
    block = b'CorePulse-Real-IO\x00' * 4096
    bytes_written = 0
    digest = hashlib.sha256()
    location = folder or tempfile.gettempdir()
    filename = None
    try:
        with tempfile.NamedTemporaryFile(prefix='corepulse_bench_', suffix='.dat', dir=location, delete=False) as f:
            filename = Path(f.name)
            start_write = time.perf_counter()
            while bytes_written < size:
                if cancel.is_set():
                    return None
                chunk = block[:min(len(block), size - bytes_written)]
                f.write(chunk)
                digest.update(chunk)
                bytes_written += len(chunk)
            f.flush()
            os.fsync(f.fileno())
            write_elapsed = time.perf_counter() - start_write
        if cancel.is_set():
            return None
        start_read = time.perf_counter()
        count_read = 0
        check = hashlib.sha256()
        with open(filename, 'rb', buffering=0) as f:
            while True:
                if cancel.is_set():
                    return None
                chunk = f.read(len(block))
                if not chunk:
                    break
                count_read += len(chunk)
                check.update(chunk)
        read_elapsed = time.perf_counter() - start_read
        if count_read != bytes_written or check.digest() != digest.digest():
            raise RuntimeError('Los datos escritos y leídos del archivo temporal no coinciden.')
        return {'bytesWritten': bytes_written, 'writeMiBPerSecond': _speed(bytes_written, write_elapsed),
                'readMiBPerSecond': _speed(count_read, read_elapsed), 'integrity': 'PASS',
                'writeSeconds': round(write_elapsed, 3), 'readSeconds': round(read_elapsed, 3),
                'unit': 'MiB/s de E/S de archivo',
                'method': 'Escritura temporal con fsync y lectura verificada; caché del SO posible'}
    finally:
        if filename is not None:
            try:
                filename.unlink(missing_ok=True)
            except OSError:
                pass


def run_quick_benchmark(cancel, report=None, *, cpu_seconds=2.0, ram_seconds=1.5,
                        disk_bytes=16 * 1024 * 1024, disk_folder=None):
    """Progreso por etapa COMPLETADA, no estimación por temporizador."""
    result = {'method': METHOD, 'startedAt': datetime.now(timezone.utc).isoformat(),
              'completedAt': None, 'status': 'running', 'cpu': None, 'ram': None,
              'ssd': None, 'gpu': None, 'gpuStatus': 'No incluido en esta ejecución; disponible como prueba independiente DirectX 11 V29',
              'score': None, 'caveat': 'Resultados locales por metodología; no son puntuaciones comparables entre versiones.'}
    stages = [('cpu', 'CPU · Cálculo entero', lambda: _cpu_workload(cpu_seconds, cancel)),
              ('ram', 'RAM · Copias verificadas', lambda: _ram_workload(ram_seconds, cancel)),
              ('ssd', 'SSD · Archivo temporal', lambda: _ssd_workload(cancel, folder=disk_folder, size=disk_bytes))]
    for index, (name, label, fn) in enumerate(stages):
        if cancel.is_set():
            result.update(status='cancelled', completedAt=datetime.now(timezone.utc).isoformat())
            return result
        if report:
            report(index, len(stages), 'Ejecutando ' + label)
        try:
            measured = fn()
        except (OSError, RuntimeError, MemoryError) as error:
            result[name] = {'status': 'N/A', 'reason': type(error).__name__ + ': ' + str(error)[:160]}
        else:
            if measured is None:
                result.update(status='cancelled', completedAt=datetime.now(timezone.utc).isoformat())
                return result
            result[name] = {'status': 'OK', **measured}
        if report:
            report(index + 1, len(stages), label + ' finalizado')
    result.update(status='complete', completedAt=datetime.now(timezone.utc).isoformat())
    return result


def results_path():
    base = Path(os.environ.get('LOCALAPPDATA') or Path.home()) / 'CorePulse' / 'resultados'
    return base / 'benchmark_rebuild_070_ultimo_resultado.json'


def save_result(data, filename=None):
    target = Path(filename) if filename else results_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    # Evita dejar JSON parcial si CorePulse se cierra durante el guardado.
    temporary = target.with_suffix('.tmp')
    try:
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return str(target)



def gpu_results_path():
    # Archivo nuevo por metodología: un resultado anterior no se muestra como V28.
    return results_path().parent / 'benchmark_gpu_v29_ultimo_resultado.json'


def benchmark_history_path():
    """Archivo local append-only con las sesiones verificadas de benchmark."""
    return results_path().parent / 'benchmark_historial.jsonl'


def _finite_number(value):
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def _history_summary(kind, data):
    if kind == 'GPU':
        scenes = [row for row in (data.get('scenes') or [])
                  if isinstance(row, dict) and row.get('status') == 'OK']
        fps = [_finite_number(row.get('frames_per_s')) for row in scenes]
        lows = [_finite_number(row.get('one_percent_low_fps')) for row in scenes]
        fps = [value for value in fps if value is not None]
        lows = [value for value in lows if value is not None]
        return {
            'gpu_fps': sum(fps) / len(fps) if fps else _finite_number(data.get('value') or data.get('frames_per_s')),
            'gpu_low_fps': sum(lows) / len(lows) if lows else _finite_number(data.get('one_percent_low_fps')),
        }
    cpu, ram, ssd = data.get('cpu') or {}, data.get('ram') or {}, data.get('ssd') or {}
    return {
        'cpu_ops_s': _finite_number(cpu.get('operationsPerSecond')),
        'ram_mib_s': _finite_number(ram.get('mibPerSecond')),
        'ssd_read_mib_s': _finite_number(ssd.get('readMiBPerSecond')),
        'ssd_write_mib_s': _finite_number(ssd.get('writeMiBPerSecond')),
    }


def _make_history_entry(kind, data, *, profile=None):
    """Crea una entrada solo si contiene mediciones reales de un método conocido."""
    if not isinstance(data, dict):
        return None
    if kind == 'GPU':
        if data.get('benchmark_method') != GPU_METHOD or data.get('status') not in ('OK', 'PARTIAL'):
            return None
        summary = _history_summary('GPU', data)
        if summary['gpu_fps'] is None:
            # En perfiles parciales el FPS principal puede faltar; conservar la
            # sesión solo si al menos una escena tiene FPS medidos reales.
            scenes = data.get('scenes') or []
            fps = [_finite_number(scene.get('frames_per_s')) for scene in scenes
                   if isinstance(scene, dict) and scene.get('status') == 'OK']
            fps = [value for value in fps if value is not None]
            if not fps:
                return None
            summary['gpu_fps'] = sum(fps) / len(fps)
        actual_profile = str(profile or data.get('profile') or 'unknown').lower()
        renderer = str(data.get('renderer') or 'N/A')
        method = GPU_METHOD
        kind_label = 'GPU'
        entry_status = str(data.get('status') or 'OK')
        result = dict(data)
        result['profile'] = actual_profile
        if isinstance(result.get('session'), dict):
            # El historial no necesita cientos de muestras temporales por GPU;
            # conserva el resumen de condiciones y las cuatro escenas medidas.
            result['session'] = {key: value for key, value in result['session'].items()
                                 if key != 'timeline'}
    else:
        if data.get('method') != METHOD or data.get('status') != 'complete':
            return None
        summary = _history_summary('CPU_RAM_SSD', data)
        if not any(value is not None for value in summary.values()):
            return None
        actual_profile = 'standard'
        renderer = ''
        method = METHOD
        kind_label = 'CPU_RAM_SSD'
        entry_status = 'OK' if all(value is not None for value in summary.values()) else 'PARTIAL'
        result = data
    return {
        'schemaVersion': 1,
        'id': uuid.uuid4().hex,
        'timestamp': str(data.get('completedAt') or datetime.now(timezone.utc).isoformat()),
        'kind': kind_label,
        'status': entry_status,
        'method': method,
        'profile': actual_profile,
        'renderer': renderer,
        'summary': summary,
        'result': result,
    }


def _read_benchmark_history():
    entries = []
    try:
        with benchmark_history_path().open('r', encoding='utf-8') as stream:
            for line in stream:
                try:
                    row = json.loads(line)
                except (ValueError, TypeError):
                    continue
                if (isinstance(row, dict) and row.get('schemaVersion') == 1
                        and row.get('kind') in ('GPU', 'CPU_RAM_SSD')
                        and isinstance(row.get('summary'), dict)):
                    entries.append(row)
    except OSError:
        pass
    entries.sort(key=lambda row: str(row.get('timestamp') or ''), reverse=True)
    return entries[:HISTORY_LIMIT]


def _history_for_ui(entries):
    """Publica metadatos resumidos; no envía escenas/sensores completos cada tick QML."""
    fields = ('schemaVersion', 'id', 'timestamp', 'kind', 'status', 'method', 'profile', 'renderer', 'summary')
    return [{key: row.get(key) for key in fields} for row in entries]


def _store_history_entry(entry):
    if not entry:
        return _read_benchmark_history()
    target = benchmark_history_path()
    with _HISTORY_LOCK:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('a', encoding='utf-8', newline='') as stream:
            stream.write(json.dumps(entry, ensure_ascii=False, separators=(',', ':')) + '\n')
        entries = _read_benchmark_history()
        if len(entries) >= HISTORY_LIMIT:
            temporary = target.with_suffix('.tmp')
            try:
                temporary.write_text(''.join(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n'
                                              for row in entries), encoding='utf-8')
                temporary.replace(target)
            except OSError:
                # El append ya quedó guardado; el siguiente guardado reintentará compactar.
                pass
            finally:
                temporary.unlink(missing_ok=True)
        return entries


def _seed_history_from_latest(cpu_saved, gpu_saved):
    """Conserva el último resultado previo al historial en la primera ejecución."""
    if _read_benchmark_history():
        return _read_benchmark_history()
    entries = []
    cpu_entry = _make_history_entry('CPU_RAM_SSD', cpu_saved)
    gpu_entry = _make_history_entry('GPU', gpu_saved)
    with _HISTORY_LOCK:
        target = benchmark_history_path()
        try:
            if target.exists() and target.stat().st_size > 0:
                return []
        except OSError:
            return []
        if cpu_entry:
            entries.append(cpu_entry)
        if gpu_entry:
            entries.append(gpu_entry)
        if entries:
            temporary = target.with_suffix('.tmp')
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                temporary.write_text(''.join(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n'
                                              for row in entries), encoding='utf-8')
                temporary.replace(target)
            except OSError:
                return []
            finally:
                temporary.unlink(missing_ok=True)
    return sorted(entries, key=lambda row: str(row.get('timestamp') or ''), reverse=True)


_HISTORY_METRICS = {
    'CPU_RAM_SSD': (
        ('cpu_ops_s', 'CPU', 'iter/s'),
        ('ram_mib_s', 'RAM', 'MiB/s'),
        ('ssd_read_mib_s', 'SSD lectura', 'MiB/s'),
        ('ssd_write_mib_s', 'SSD escritura', 'MiB/s'),
    ),
    'GPU': (
        ('gpu_fps', 'FPS promedio de escenas', 'FPS'),
        ('gpu_low_fps', '1 % Low promedio', 'FPS'),
    ),
}


def _compare_history_entries(first, second):
    if not first or not second:
        return {'ok': False, 'message': 'Selecciona dos sesiones para comparar.', 'metrics': []}
    if first.get('id') == second.get('id'):
        return {'ok': False, 'message': 'Elige dos sesiones distintas.', 'metrics': []}
    if (first.get('kind') != second.get('kind') or first.get('method') != second.get('method')
            or first.get('profile') != second.get('profile')):
        return {'ok': False, 'message': 'Las sesiones usan métodos o perfiles distintos y no son comparables.', 'metrics': []}
    if first.get('kind') == 'GPU' and first.get('renderer') != second.get('renderer'):
        return {'ok': False, 'message': 'Las sesiones GPU corresponden a adaptadores distintos.', 'metrics': []}
    metrics = []
    first_summary, second_summary = first.get('summary') or {}, second.get('summary') or {}
    for key, label, unit in _HISTORY_METRICS.get(first.get('kind'), ()):
        before = _finite_number(first_summary.get(key))
        after = _finite_number(second_summary.get(key))
        if before is None or after is None:
            continue
        delta = ((after - before) / abs(before) * 100.0) if before else None
        metrics.append({'key': key, 'label': label, 'unit': unit, 'before': before,
                        'after': after, 'deltaPct': delta})
    return {'ok': bool(metrics), 'message': '' if metrics else 'No hay lecturas comunes para comparar.',
            'firstLabel': first.get('kind'), 'firstTimestamp': first.get('timestamp'),
            'secondLabel': second.get('kind'), 'secondTimestamp': second.get('timestamp'),
            'metrics': metrics}


def _export_history_csv(path, entries, kind_filter='all'):
    target_url = QUrl(str(path or ''))
    target = Path(target_url.toLocalFile()) if target_url.isLocalFile() else Path(str(path or ''))
    if not str(target) or not target.name:
        raise ValueError('Selecciona una ruta de archivo CSV.')
    if target.suffix.lower() != '.csv':
        target = target.with_suffix('.csv')
    selected = [row for row in entries if kind_filter == 'all'
                or (kind_filter == 'gpu' and row.get('kind') == 'GPU')
                or (kind_filter == 'cpu' and row.get('kind') == 'CPU_RAM_SSD')]
    columns = ['fecha', 'tipo', 'estado', 'metodo', 'perfil', 'adaptador',
               'cpu_iter_s', 'ram_mib_s', 'ssd_lectura_mib_s', 'ssd_escritura_mib_s',
               'gpu_fps', 'gpu_1_percent_low_fps']
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction='ignore', lineterminator='\n')
        writer.writeheader()
        for row in reversed(selected):
            summary = row.get('summary') or {}
            writer.writerow({
                'fecha': row.get('timestamp', ''), 'tipo': row.get('kind', ''),
                'estado': row.get('status', ''), 'metodo': row.get('method', ''),
                'perfil': row.get('profile', ''), 'adaptador': row.get('renderer', ''),
                'cpu_iter_s': summary.get('cpu_ops_s', ''), 'ram_mib_s': summary.get('ram_mib_s', ''),
                'ssd_lectura_mib_s': summary.get('ssd_read_mib_s', ''),
                'ssd_escritura_mib_s': summary.get('ssd_write_mib_s', ''),
                'gpu_fps': summary.get('gpu_fps', ''), 'gpu_1_percent_low_fps': summary.get('gpu_low_fps', ''),
            })
    return str(target), len(selected)


def _read_last_json(path):
    try:
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def run_gpu_isolated(profile, cancel, report=None, *, python_path=None, script_path=None, monitor_factory=None):
    """Run historical native D3D11 in a CHILD process so COM failures cannot kill Qt.

    The GUI never imports the native renderer, and no GPU timings/FPS are
    synthesized. Cancellation terminates the subprocess, including during
    initialization when it has not published its first progress line.
    ``monitor_factory`` (GpuSessionMonitor) samples sensors from this process
    while the child renders; its summary is attached as ``session``.
    """
    monitor = monitor_factory().start() if monitor_factory else None
    try:
        data = _run_gpu_child(profile, cancel, report, python_path=python_path,
                              script_path=script_path, monitor=monitor)
    finally:
        if monitor is not None:
            monitor.stop()
    if monitor is not None and data.get('status') in ('OK', 'PARTIAL'):
        data = {**data, 'session': monitor.summary(data)}
    return data


def _run_gpu_child(profile, cancel, report=None, *, python_path=None, script_path=None, monitor=None):
    profile = str(profile or '').strip().lower()
    if profile not in GPU_PROFILES:
        raise ValueError('Perfil de GPU no permitido')
    if os.name != 'nt':
        return {'kind':'GPU','status':'UNAVAILABLE','value':None,
                'reason':'DirectX 11 solo está disponible en Windows',
                'benchmark_method':GPU_METHOD, 'scenes':[]}
    import tempfile
    from queue import Empty, Queue
    executable = str(python_path or sys.executable)
    script = Path(script_path) if script_path else GPU_SCRIPT
    if not script.is_file():
        return {'kind':'GPU','status':'UNAVAILABLE','value':None,
                'reason':'El motor DirectX 11 no está disponible en esta instalación.',
                'benchmark_method':GPU_METHOD, 'scenes':[]}
    with tempfile.TemporaryDirectory(prefix='corepulse_dx11_') as folder:
        target = Path(folder) / 'gpu_result.json'
        command = [executable, '-B', '-m', 'core.benchmark_gpu', '--profile', profile, '--output', str(target)]
        env = os.environ.copy()
        env['PYTHONNOUSERSITE'] = '1'
        process = subprocess.Popen(command, cwd=str(script.parent.parent), env=env,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, encoding='utf-8', errors='replace', bufsize=1,
                                   creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        output = Queue()
        def reader():
            for line in process.stdout:
                output.put(line.strip())
        io = threading.Thread(target=reader, daemon=True, name='corepulse-gpu-output')
        io.start()
        log = []
        was_cancelled = False
        while process.poll() is None or not output.empty():
            if cancel.is_set() and process.poll() is None:
                was_cancelled = True
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=3)
            try:
                line = output.get(timeout=.12)
            except Empty:
                continue
            try:
                row = json.loads(line)
            except (ValueError, TypeError):
                log.append(line[:180])
                continue
            if row.get('event') == 'progress':
                if monitor is not None:
                    monitor.set_stage(row.get('stage', ''))
                if report:
                    report(row.get('progress',0), 100, (row.get('stage','GPU') + ' · ' + row.get('detail',''))[:210])
        io.join(timeout=1)
        if was_cancelled or cancel.is_set():
            return {'kind':'GPU','status':'CANCELLED','value':None,'scenes':[],
                    'benchmark_method':GPU_METHOD}
        data = _read_last_json(target)
        if (data.get('kind') == 'GPU' and data.get('benchmark_method') == GPU_METHOD
                and data.get('status') in ('OK','PARTIAL','ERROR','UNAVAILABLE','CANCELLED')):
            if data.get('status') == 'OK':
                scenes = data.get('scenes') or []
                expected = 3 if profile == 'quick' else 4
                complete = (len(scenes) == expected and all(
                    row.get('status') == 'OK'
                    and isinstance(row.get('frames'), int) and row['frames'] > 0
                    and isinstance(row.get('frames_per_s'), (int,float))
                    and row['frames_per_s'] > 0 and math.isfinite(row['frames_per_s'])
                    for row in scenes if isinstance(row, dict)))
                if not complete or any(not isinstance(row, dict) for row in scenes):
                    return {'kind':'GPU','status':'ERROR','value':None,'scenes':[],
                            'reason':'La medición DirectX no confirmó todas las escenas y frames reales.',
                            'benchmark_method':GPU_METHOD}
            return {**data, 'profile': profile}
        return {'kind':'GPU','status':'ERROR','value':None,'scenes':[],
                'reason':'El proceso DirectX no entregó un resultado válido (código ' + str(process.returncode) + '). ' + ' '.join(log[-2:])[:200],
                'benchmark_method':GPU_METHOD}


class BenchmarkController(QObject):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='corepulse-benchmark')
        self._future = None
        self._cancel = threading.Event()
        self._lock = threading.Lock()
        self._pending = None
        self._mode = 'cpu'
        cpu_saved = _read_last_json(results_path())
        gpu_saved = _read_last_json(gpu_results_path())
        history = _read_benchmark_history()
        if not history:
            history = _seed_history_from_latest(cpu_saved, gpu_saved)
        self._data = {'busy': False, 'stage': 'Listo para iniciar', 'progress': 0,
                      'status': 'Sin ejecutar', 'mode': 'cpu', 'gpuProfile':'standard',
                      'result': cpu_saved, 'gpuResult': gpu_saved,
                      'resultFile': str(results_path()) if cpu_saved else '',
                      'gpuResultFile': str(gpu_results_path()) if gpu_saved else '',
                      'history': _history_for_ui(history), 'historyFile': str(benchmark_history_path()),
                      'historyMessage': '', 'error': ''}
        self._timer = QTimer(self)
        self._timer.setInterval(150)
        self._timer.timeout.connect(self._finish)

    @Property('QVariantMap', notify=changed)
    def data(self):
        return self._data

    @Slot(str, str, result='QVariantMap')
    def compareHistory(self, first_id, second_id):
        by_id = {str(row.get('id')): row for row in self._data.get('history', [])}
        return _compare_history_entries(by_id.get(str(first_id)), by_id.get(str(second_id)))

    @Slot(str, str, result=bool)
    def exportHistory(self, path, kind_filter='all'):
        try:
            target, count = _export_history_csv(path, self._data.get('history', []), kind_filter)
            self._data = {**self._data, 'historyMessage': f'CSV guardado ({count} sesiones): {target}'}
            self.changed.emit()
            return True
        except (OSError, ValueError, TypeError) as error:
            self._data = {**self._data, 'historyMessage': 'No se pudo exportar: ' + str(error)[:180]}
            self.changed.emit()
            return False

    @Slot()
    def refreshHistory(self):
        self._data = {**self._data, 'history': _history_for_ui(_read_benchmark_history()), 'historyMessage': ''}
        self.changed.emit()

    def _progress(self, done, total, label):
        with self._lock:
            self._pending = {'progress': int(100 * done / total) if total else 0, 'stage': str(label)}

    def _start_job(self, mode, title, fn):
        if self._future is not None:
            return
        self._mode = mode
        self._cancel.clear()
        with self._lock:
            self._pending = None
        self._data = {**self._data, 'busy': True, 'mode':mode, 'status':'Ejecutando',
                      'stage':title, 'progress':0, 'error':''}
        self.changed.emit()
        self._future = self._executor.submit(fn)
        self._timer.start()

    @Slot()
    def start(self):
        self._start_job('cpu', 'Preparando CPU, RAM y SSD…',
                        lambda: run_quick_benchmark(self._cancel,self._progress))

    @Slot(str)
    def startGpu(self, profile):
        profile = str(profile or '').lower()
        if profile not in GPU_PROFILES:
            return
        if self._future is not None:
            return
        self._data = {**self._data, 'gpuProfile':profile}
        self._start_job('gpu', 'Preparando DirectX 11 V29…',
                        lambda: run_gpu_isolated(profile,self._cancel,self._progress,
                                                 monitor_factory=GpuSessionMonitor))

    @Slot()
    def cancel(self):
        if self._future is not None:
            self._cancel.set()
            self._data = {**self._data, 'stage': 'Cancelando prueba…'}
            self.changed.emit()

    def _finish(self):
        with self._lock:
            pending, self._pending = self._pending, None
        if pending:
            self._data = {**self._data, **pending}
            self.changed.emit()
        if self._future is None or not self._future.done():
            return
        try:
            result = self._future.result()
            if self._mode == 'gpu':
                status = result.get('status','ERROR')
                path = save_result(result,gpu_results_path()) if status == 'OK' else ''
                history = self._data.get('history', [])
                history_message = ''
                if status in ('OK', 'PARTIAL'):
                    entry = _make_history_entry('GPU', result, profile=result.get('profile') or self._data.get('gpuProfile'))
                    if entry:
                        try:
                            history = _history_for_ui(_store_history_entry(entry))
                        except (OSError, TypeError, ValueError) as error:
                            history_message = 'Benchmark finalizado; no se pudo guardar el historial local: ' + str(error)[:100]
                state = 'Completado' if status == 'OK' else 'Cancelado' if status == 'CANCELLED' else 'No disponible' if status == 'UNAVAILABLE' else 'Parcial' if status == 'PARTIAL' else 'Error'
                self._data = {**self._data,'busy':False,'status':state,'gpuResult':result,
                              'gpuResultFile':path or self._data.get('gpuResultFile',''),
                              'history':history,'historyMessage':history_message,
                              'stage':'GPU finalizado.' if path else (result.get('reason') or 'GPU no completado.'),
                              'progress':100 if path else self._data['progress'], 'error':''}
            else:
                path = save_result(result) if result['status'] == 'complete' else ''
                history = self._data.get('history', [])
                history_message = ''
                if result.get('status') == 'complete':
                    entry = _make_history_entry('CPU_RAM_SSD', result)
                    if entry:
                        try:
                            history = _history_for_ui(_store_history_entry(entry))
                        except (OSError, TypeError, ValueError) as error:
                            history_message = 'Benchmark finalizado; no se pudo guardar el historial local: ' + str(error)[:100]
                state = 'Completado' if result['status'] == 'complete' else 'Cancelado'
                self._data = {**self._data,'busy':False,'status':state,'result':result,
                              'resultFile':path or self._data.get('resultFile',''),
                              'history':history,'historyMessage':history_message,
                              'stage':'Pruebas finalizadas.' if path else 'Prueba cancelada.',
                              'progress':100 if path else self._data['progress'], 'error':''}
        except Exception as exc:
            self._data = {**self._data,'busy':False,'status':'ERROR','stage':'No se pudo completar.',
                          'error':type(exc).__name__ + ': ' + str(exc)[:160]}
        self._future = None
        self._timer.stop()
        self.changed.emit()

    @Slot()
    def close(self):
        self._cancel.set()
        self._timer.stop()
        self._executor.shutdown(wait=False, cancel_futures=True)
