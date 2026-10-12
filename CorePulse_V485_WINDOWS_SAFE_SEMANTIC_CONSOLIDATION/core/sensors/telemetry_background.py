"""Mantiene un trabajador en segundo plano para adquirir telemetría sin bloquear la interfaz."""
from __future__ import annotations
# Código refactorizado: nombres estables y documentación en español.
import copy
import threading
import time
import psutil
from core.runtime_logging import get_logger
logger = get_logger('telemetry_background')
from core import telemetry_full as _telemetry_full
from core import telemetry_reliable as _telemetry_reliable
from core.hardware_policy import select_active_gpu
from core.device_identity import get_cpu_frequency_evidence
from core.cpu_temp_compat import query_packaged_cpu_temperature
from core.telemetry_storage_cache import get_all_disks_data, get_storage_cache_status, invalidate_storage_cache
calculate_preliminary_score = _telemetry_full.calculate_preliminary_score
get_hardware_names = _telemetry_full.get_hardware_names
get_system_chassis_and_bios = _telemetry_full.get_system_chassis_and_bios
WORKER_INTERVAL_SECONDS = 1.0
FIRST_SNAPSHOT_TIMEOUT_SECONDS = 6.0
_state_lock = threading.RLock()
_worker_stop = threading.Event()
_first_snapshot_ready = threading.Event()
_snapshot = None
_snapshot_at = 0.0
_last_refresh_started = 0.0
_last_refresh_finished = 0.0
_last_refresh_duration = None
_last_error = None
_refresh_count = 0
_worker_thread = None
_last_error_log_at = 0.0

def _number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None

def _round(value, digits=1):
    value = _number(value)
    return round(value, digits) if value is not None else None

def _temperature(value, digits=1, *, high=175.0):
    value = _number(value)
    if value is None or not (1.0 <= value <= float(high)):
        return None
    return round(value, digits)

def _metric(value, unit, source, sensor=None, error=None):
    return {'value': value, 'unit': unit, 'source': source, 'quality': 'VALID' if value is not None else 'UNAVAILABLE', 'sensor': sensor, 'timestamp': time.time(), 'error': error}

def _primary_gpu(gpus):
    return select_active_gpu(gpus)

def _collect_snapshot():
    started = time.perf_counter()
    cpu_usage = _round(psutil.cpu_percent(interval=None), 1)
    memory = psutil.virtual_memory()
    ram_usage = _round(memory.percent, 1)
    ram_total_gb = round(memory.total / 1024 ** 3, 2)
    ram_used_gb = round(memory.used / 1024 ** 3, 2)
    ram_available_gb = round(memory.available / 1024 ** 3, 2)
    provider, sensors = _telemetry_full._sensors()
    cpu = _telemetry_full._cpu_details(sensors)
    gpus = _telemetry_full._gpu_details(sensors)
    storage = _telemetry_full._storage_details(sensors)
    battery = _telemetry_full._battery_details(sensors)

    # V373: LHM/PawnIO sigue siendo la fuente preferida, pero no debe ocultar
    # inventario ni métricas que Windows expone por otras fuentes reales.
    # Todos los fallbacks respetan REAL_OR_NA: si ninguna fuente real responde,
    # la métrica permanece en None/N/A.
    inventory_cpu = None
    inventory_gpu = None
    inventory_vram = None
    try:
        inventory_cpu, inventory_gpu, inventory_vram = get_hardware_names()
    except Exception:
        pass

    cpu_name = cpu.get('hardware')
    if not cpu_name and inventory_cpu and str(inventory_cpu).strip().casefold() not in {'procesador', 'cpu', 'processor'}:
        cpu_name = str(inventory_cpu).strip()
    cpu_name = cpu_name or 'CPU no identificado'
    if cpu_name != 'CPU no identificado' and not cpu.get('hardware'):
        cpu['hardware'] = cpu_name
        cpu['hardware_source'] = 'Win32_Processor'

    cpu_temp = _temperature(cpu.get('package_temp_c'), 1, high=150.0)
    provider_source = getattr(provider, 'source_name', None) or 'LibreHardwareMonitorLib'
    cpu_temp_source = provider_source
    cpu_temp_sensor = f'{cpu_name} / CPU Package'
    cpu_temp_timestamp = time.time()

    # V378: algunos portátiles publican la temperatura de CPU bajo EC/SuperIO o
    # Motherboard, no bajo HardwareType.Cpu. El proveedor LHM hace una segunda
    # búsqueda estricta por nombre/identifier para rescatar sólo un sensor CPU real.
    if cpu_temp is None:
        try:
            direct = provider.cpu_temperature() or {}
            direct_temp = _temperature(direct.get('value'), 1, high=150.0)
            if direct_temp is not None:
                cpu_temp = direct_temp
                cpu_temp_source = str(direct.get('source') or 'LibreHardwareMonitorLib')
                hw = str(direct.get('hardware') or cpu_name).strip()
                sn = str(direct.get('sensor') or 'CPU temperature').strip()
                cpu_temp_sensor = f'{hw} / {sn}' if hw else sn
                # Mantiene el valor en la vista CPU avanzada y conserva metadata
                # para la capa certificada, sin renombrarlo artificialmente.
                cpu['package_temp_c'] = cpu_temp
                cpu['package_temp_source'] = cpu_temp_source
                cpu['package_temp_sensor'] = cpu_temp_sensor
                cpu['package_temp_fallback'] = bool(direct.get('fallback'))
                cpu.setdefault('_metrics', {})['package_temp_c'] = {
                    'unit': '°C', 'source': cpu_temp_source, 'sensor': cpu_temp_sensor,
                    'sensor_timestamp': cpu_temp_timestamp, 'timestamp': cpu_temp_timestamp,
                    'derived_from_real': False, 'contributors': [{
                        'sensor': cpu_temp_sensor, 'identifier': direct.get('identifier'),
                        'sensor_timestamp': cpu_temp_timestamp,
                    }],
                }
        except Exception:
            pass

    # V381: compatibilidad con la ruta que usaba V362. Si la release oficial
    # no entrega una lectura CPU válida, consulta el paquete HardwareMonitor en
    # un proceso .NET limpio. Esto evita que dos assemblies LHM compitan en el
    # mismo proceso y recupera sensores que algunos Ryzen/OEM exponían antes.
    if cpu_temp is None:
        try:
            legacy = query_packaged_cpu_temperature() or {}
            legacy_temp = _temperature(legacy.get('value'), 1, high=115.0)
            if legacy_temp is not None:
                cpu_temp = legacy_temp
                cpu_temp_source = str(legacy.get('source') or 'HardwareMonitor compatibility subprocess')
                hw = str(legacy.get('hardware') or cpu_name).strip()
                sn = str(legacy.get('sensor') or 'CPU temperature').strip()
                cpu_temp_sensor = f'{hw} / {sn}' if hw else sn
                cpu_temp_timestamp = _number(legacy.get('timestamp')) or time.time()
                cpu['package_temp_c'] = cpu_temp
                cpu['package_temp_source'] = cpu_temp_source
                cpu['package_temp_sensor'] = cpu_temp_sensor
                cpu['package_temp_fallback'] = True
                cpu['package_temp_compatibility_path'] = str(legacy.get('compatibility_path') or 'V362 HardwareMonitor package')
                cpu.setdefault('_metrics', {})['package_temp_c'] = {
                    'unit': '°C', 'source': cpu_temp_source, 'sensor': cpu_temp_sensor,
                    'sensor_timestamp': cpu_temp_timestamp, 'timestamp': cpu_temp_timestamp,
                    'derived_from_real': False, 'contributors': [{
                        'sensor': cpu_temp_sensor, 'identifier': legacy.get('identifier'),
                        'sensor_timestamp': cpu_temp_timestamp,
                    }],
                }
        except Exception:
            pass

    if cpu_temp is None:
        try:
            fallback_temp, fallback_source, _fallback_error = _telemetry_reliable._get_cpu_temperature()
            fallback_temp = _temperature(fallback_temp, 1, high=150.0)
            if fallback_temp is not None:
                cpu_temp = fallback_temp
                cpu_temp_source = str(fallback_source or 'Windows hardware sensor')
                cpu_temp_sensor = f'{cpu_name} / CPU temperature'
                cpu['package_temp_c'] = cpu_temp
                cpu['package_temp_source'] = cpu_temp_source
                cpu['package_temp_sensor'] = cpu_temp_sensor
                cpu['package_temp_fallback'] = True
                cpu.setdefault('_metrics', {})['package_temp_c'] = {
                    'unit': '°C', 'source': cpu_temp_source, 'sensor': cpu_temp_sensor,
                    'sensor_timestamp': cpu_temp_timestamp, 'timestamp': cpu_temp_timestamp,
                    'derived_from_real': False, 'contributors': [],
                }
        except Exception:
            pass

    # Si LHM no enumera almacenamiento (por ejemplo, sin PawnIO), conserva las
    # unidades reales reportadas por Windows/psutil para no dejar el Dashboard vacío.
    if not storage:
        try:
            os_disks = get_all_disks_data() or []
        except Exception:
            os_disks = []
        for disk in os_disks:
            if not isinstance(disk, dict):
                continue
            total = _number(disk.get('total_gb'))
            used = _number(disk.get('used_percent'))
            free = None
            if total is not None and used is not None:
                free = max(0.0, total * (100.0 - used) / 100.0)
            storage.append({
                'name': disk.get('model') or disk.get('mount_points') or 'Unidad',
                'model': disk.get('model') or disk.get('mount_points') or 'Unidad',
                'temperature_c': disk.get('temperature_c'),
                'life_percent': disk.get('health'),
                'used_space_percent': used,
                'free_space_gb': round(free, 2) if free is not None else None,
                'total_space_gb': round(total, 2) if total is not None else None,
                'mount_points': disk.get('mount_points'),
                'source': disk.get('used_source') or 'psutil.disk_usage',
                'quality': 'VALID',
                'timestamp': time.time(),
                'os_inventory': {
                    'size_bytes_os': int(total * (1024 ** 3)) if total is not None else None,
                    'mount_points': disk.get('mount_points'),
                },
            })

    primary_gpu = _primary_gpu(gpus)

    # Frecuencia CPU universal REAL_OR_NA: LHM sigue siendo la fuente prioritaria.
    # Si un equipo no expone sensores Clock en LHM (caso común en algunos PCs OEM/
    # híbridos), usa una lectura real del SO en vez de convertir la métrica en N/A.
    cpu_ghz = _round(cpu.get('clock_avg_ghz'), 3)
    cpu_clock_source = provider_source
    cpu_clock_sensor = f'{cpu_name} / clocks'
    cpu_clock_timestamp = _number(cpu.get('timestamp')) or time.time()
    cpu_clock_derived = True
    cpu_clock_evidence = None
    if cpu_ghz is None:
        cpu_clock_evidence = get_cpu_frequency_evidence()
        if isinstance(cpu_clock_evidence, dict):
            cpu_ghz = _round(cpu_clock_evidence.get('ghz'), 3)
            if cpu_ghz is not None:
                cpu_clock_source = str(cpu_clock_evidence.get('source') or 'OS CPU frequency provider')
                cpu_clock_sensor = str(cpu_clock_evidence.get('sensor') or 'CPU frequency')
                cpu_clock_timestamp = _number(cpu_clock_evidence.get('timestamp')) or time.time()
                cpu_clock_derived = bool(cpu_clock_evidence.get('derived_from_real'))
                cpu['clock_avg_ghz'] = cpu_ghz
                cpu.setdefault('_metrics', {})['clock_avg_ghz'] = {
                    'unit': 'GHz',
                    'source': cpu_clock_source,
                    'sensor': cpu_clock_sensor,
                    'sensor_timestamp': cpu_clock_timestamp,
                    'derived_from_real': cpu_clock_derived,
                    'contributors': [],
                }
                cpu['_clock_fallback_evidence'] = dict(cpu_clock_evidence)

    gpu_name = primary_gpu.get('name')
    if not gpu_name and inventory_gpu and str(inventory_gpu).strip().casefold() not in {'gráfica', 'grafica', 'gpu', 'graphics'}:
        gpu_name = str(inventory_gpu).strip()
    gpu_name = gpu_name or 'GPU no identificada'

    gpu_usage = _round(primary_gpu.get('usage_percent'), 1)
    gpu_temp = _temperature(primary_gpu.get('temperature_c'), 1, high=150.0)
    gpu_usage_source = provider_source
    gpu_temp_source = provider_source
    gpu_vram_source = provider_source
    gpu_vram_gb = None
    memory_total_mb = _number(primary_gpu.get('memory_total_mb'))
    if memory_total_mb is not None:
        gpu_vram_gb = round(memory_total_mb / 1024.0, 2)

    # Fallback real: OpenHardwareMonitor WMI / nvidia-smi. No se estima nada.
    if gpu_usage is None or gpu_temp is None or gpu_vram_gb is None:
        try:
            fallback_gpu = _telemetry_reliable._get_gpu_telemetry() or {}
        except Exception:
            fallback_gpu = {}
        if gpu_usage is None:
            value = _round(fallback_gpu.get('usage'), 1)
            if value is not None:
                gpu_usage = value
                gpu_usage_source = str(fallback_gpu.get('usage_source') or 'GPU provider')
        if gpu_temp is None:
            value = _temperature(fallback_gpu.get('temperature'), 1, high=150.0)
            if value is not None:
                gpu_temp = value
                gpu_temp_source = str(fallback_gpu.get('temperature_source') or 'GPU provider')
        if gpu_vram_gb is None:
            value = _number(fallback_gpu.get('vram_gb'))
            if value is not None:
                gpu_vram_gb = round(value, 2)
                gpu_vram_source = str(fallback_gpu.get('vram_source') or 'GPU provider')
    if gpu_vram_gb is None and _number(inventory_vram) is not None:
        gpu_vram_gb = round(float(inventory_vram), 2)
        gpu_vram_source = 'Win32_VideoController'

    # Publica también un registro GPU mínimo cuando LHM no enumera el hardware
    # pero Windows/nvidia-smi sí lo hacen, para que las vistas de detalle no
    # confundan "sensor LHM ausente" con "GPU inexistente".
    if not gpus and gpu_name != 'GPU no identificada':
        gpus = [{
            'name': gpu_name,
            'hardware_type': 'GPU',
            'temperature_c': gpu_temp,
            'usage_percent': gpu_usage,
            'memory_total_mb': round(gpu_vram_gb * 1024.0, 1) if gpu_vram_gb is not None else None,
            'source': gpu_usage_source if gpu_usage is not None else gpu_temp_source if gpu_temp is not None else 'Win32_VideoController',
            'quality': 'VALID',
            'sensor_count': 0,
            'sensors': [],
            'timestamp': time.time(),
        }]
        primary_gpu = gpus[0]
    duration_ms = round((time.perf_counter() - started) * 1000.0, 2)
    snapshot = {'_telemetry_version': '0.8.4.4', '_background_worker': True, '_worker_refresh_duration_ms': duration_ms, '_snapshot_timestamp': time.time(), 'cpu_name': cpu_name, 'cpu_usage': cpu_usage, 'cpu_ghz': cpu_ghz, 'cpu_temp': cpu_temp, 'ram_usage': ram_usage, 'ram_total_gb': ram_total_gb, 'ram_used_gb': ram_used_gb, 'ram_available_gb': ram_available_gb, 'gpu_name': gpu_name, 'gpu_usage': gpu_usage, 'gpu_temp': gpu_temp, 'gpu_vram_gb': gpu_vram_gb, '_cpu': cpu, '_gpus': gpus, '_storage_devices': storage, '_battery': battery, '_metrics': {'cpu_usage': _metric(cpu_usage, '%', 'psutil.cpu_percent'), 'cpu_ghz': _metric(cpu_ghz, 'GHz', cpu_clock_source, sensor=cpu_clock_sensor), 'cpu_temp': _metric(cpu_temp, '°C', cpu_temp_source, sensor=cpu_temp_sensor), 'ram_usage': _metric(ram_usage, '%', 'psutil.virtual_memory'), 'gpu_usage': _metric(gpu_usage, '%', gpu_usage_source, sensor=f'{gpu_name} / GPU Core'), 'gpu_temp': _metric(gpu_temp, '°C', gpu_temp_source, sensor=f'{gpu_name} / GPU Core'), 'gpu_vram_gb': _metric(gpu_vram_gb, 'GB', gpu_vram_source, sensor=f'{gpu_name} / GPU Memory Total')}, '_sensor_summary': {'provider': f'{provider_source} + Windows real fallbacks', 'provider_available': provider.available, 'provider_error': provider.error, 'sensor_count': len(sensors), 'cpu_detected': cpu_name != 'CPU no identificado', 'gpu_count': len(gpus), 'storage_count': len(storage), 'battery_detected': battery is not None, 'timestamp': time.time(), 'background_worker': True, 'fallback_policy': 'REAL_OR_NA', 'lhm_engine': getattr(provider, 'engine_state', {})}}
    # Preserva timestamp/fuente reales del fallback para la capa certificada.
    cpu_metric = (snapshot.get('_metrics') or {}).get('cpu_ghz')
    if isinstance(cpu_metric, dict):
        cpu_metric['timestamp'] = cpu_clock_timestamp
        cpu_metric['derived_from_real'] = cpu_clock_derived
        cpu_metric['fallback_evidence'] = dict(cpu_clock_evidence) if isinstance(cpu_clock_evidence, dict) else None
    snapshot['_cpu_frequency_evidence'] = (
        dict(cpu_clock_evidence) if isinstance(cpu_clock_evidence, dict) else {
            'ghz': cpu_ghz, 'source': cpu_clock_source, 'sensor': cpu_clock_sensor,
            'timestamp': cpu_clock_timestamp, 'quality': 'VALID' if cpu_ghz is not None else 'UNAVAILABLE',
            'derived_from_real': cpu_clock_derived, 'synthetic_adjustment': False,
            'interpolation': False, 'offset_applied': 0.0,
        }
    )
    return snapshot

def _worker_loop():
    global _snapshot
    global _last_error_log_at
    global _snapshot_at
    global _last_refresh_started
    global _last_refresh_finished
    global _last_refresh_duration
    global _last_error
    global _refresh_count
    try:
        psutil.cpu_percent(interval=None)
    except Exception:
        logger.debug('No se pudo cebar psutil.cpu_percent', exc_info=True)
    while not _worker_stop.is_set():
        started_monotonic = time.monotonic()
        with _state_lock:
            _last_refresh_started = started_monotonic
        try:
            started_perf = time.perf_counter()
            fresh = _collect_snapshot()
            duration = time.perf_counter() - started_perf
            with _state_lock:
                _snapshot = fresh
                _snapshot_at = time.monotonic()
                _last_refresh_finished = _snapshot_at
                _last_refresh_duration = duration
                _last_error = None
                _refresh_count += 1
            _first_snapshot_ready.set()
        except Exception as exc:
            now = time.monotonic()
            with _state_lock:
                _last_error = f'{type(exc).__name__}: {exc}'
                _last_refresh_finished = now
            if now - _last_error_log_at >= 30.0:
                _last_error_log_at = now
                logger.exception('Fallo en el worker de telemetría; se conserva REAL_OR_NA')
        elapsed = time.monotonic() - started_monotonic
        wait_time = max(0.05, WORKER_INTERVAL_SECONDS - elapsed)
        _worker_stop.wait(wait_time)

def start_background_worker():
    global _worker_thread
    with _state_lock:
        if _worker_thread is not None and _worker_thread.is_alive():
            return _worker_thread
        _worker_stop.clear()
        _worker_thread = threading.Thread(target=_worker_loop, daemon=True, name='CorePulse-TelemetryWorker')
        _worker_thread.start()
        return _worker_thread

def stop_background_worker():
    _worker_stop.set()
    thread = _worker_thread
    if thread and thread.is_alive():
        try:
            thread.join(timeout=2.0)
        except Exception:
            logger.debug('No se pudo esperar el cierre del worker de telemetría', exc_info=True)

def get_system_telemetry(wait_for_first=True):
    """Obtiene la operación `get_system_telemetry` dentro de CorePulse sin alterar la evidencia real ni las reglas del módulo."""
    start_background_worker()
    with _state_lock:
        if _snapshot is not None:
            result = copy.deepcopy(_snapshot)
            result['_snapshot_age_seconds'] = round(max(0.0, time.monotonic() - _snapshot_at), 3)
            return result
    if wait_for_first:
        _first_snapshot_ready.wait(FIRST_SNAPSHOT_TIMEOUT_SECONDS)
    with _state_lock:
        if _snapshot is not None:
            result = copy.deepcopy(_snapshot)
            result['_snapshot_age_seconds'] = round(max(0.0, time.monotonic() - _snapshot_at), 3)
            return result
        return {'_telemetry_version': '0.8.4.4', '_background_worker': True, '_snapshot_pending': True, '_worker_error': _last_error, 'cpu_name': 'CPU no identificado', 'cpu_usage': None, 'cpu_ghz': None, 'cpu_temp': None, 'ram_usage': None, 'ram_total_gb': None, 'ram_used_gb': None, 'ram_available_gb': None, 'gpu_name': 'GPU no identificada', 'gpu_usage': None, 'gpu_temp': None, 'gpu_vram_gb': None, '_cpu': {}, '_gpus': [], '_storage_devices': [], '_battery': None, '_metrics': {}, '_sensor_summary': {'provider': 'LibreHardwareMonitorLib', 'provider_available': False, 'provider_error': _last_error, 'sensor_count': 0, 'cpu_detected': False, 'gpu_count': 0, 'storage_count': 0, 'battery_detected': False, 'timestamp': time.time(), 'background_worker': True}}

def force_background_refresh():
    """Gestiona la operación `force_background_refresh` dentro de CorePulse sin alterar la evidencia real ni las reglas del módulo."""
    global _last_refresh_finished
    with _state_lock:
        _last_refresh_finished = 0.0
    return True

def get_background_telemetry_status():
    with _state_lock:
        age = None
        if _snapshot is not None and _snapshot_at:
            age = max(0.0, time.monotonic() - _snapshot_at)
        return {'version': '0.8.4.4', 'worker_alive': bool(_worker_thread is not None and _worker_thread.is_alive()), 'worker_interval_seconds': WORKER_INTERVAL_SECONDS, 'snapshot_ready': _snapshot is not None, 'snapshot_age_seconds': round(age, 3) if age is not None else None, 'refresh_count': _refresh_count, 'last_refresh_duration_ms': round(_last_refresh_duration * 1000.0, 2) if _last_refresh_duration is not None else None, 'last_error': _last_error, 'storage_cache': get_storage_cache_status()}
start_background_worker()
