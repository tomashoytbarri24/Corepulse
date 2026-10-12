"""Comprueba la consistencia entre fuentes y conserva la trazabilidad de cada lectura."""
from __future__ import annotations
from core.version import VERSION_LABEL as VERSION
# Código refactorizado: nombres estables y documentación en español.
import copy, time
from core import telemetry_background as _base
MAX_EXPECTED_SNAPSHOT_AGE_SECONDS = 3.5
calculate_preliminary_score = _base.calculate_preliminary_score
get_all_disks_data = _base.get_all_disks_data
get_hardware_names = _base.get_hardware_names
get_system_chassis_and_bios = _base.get_system_chassis_and_bios
invalidate_storage_cache = _base.invalidate_storage_cache
get_storage_cache_status = _base.get_storage_cache_status
force_background_refresh = _base.force_background_refresh
get_background_telemetry_status = _base.get_background_telemetry_status

def _num(v):
    if isinstance(v, bool) or v is None:
        return None
    try:
        return float(v)
    except Exception:
        return None

def _temperature(v, *, high=150.0):
    value = _num(v)
    if value is None or not (1.0 <= value <= float(high)):
        return None
    return value

def _metric_meta(snapshot, key):
    m = (snapshot.get('_metrics') or {}).get(key) or {}
    return {'source': m.get('source'), 'sensor': m.get('sensor'), 'timestamp': m.get('timestamp'), 'quality': m.get('quality')}

def apply_source_consistency(snapshot):
    s = copy.deepcopy(snapshot) if isinstance(snapshot, dict) else {}
    cpu = s.get('_cpu') if isinstance(s.get('_cpu'), dict) else {}
    package = _temperature(cpu.get('package_temp_c'))
    core_max = _temperature(cpu.get('core_max_temp_c'))
    core_avg = _temperature(cpu.get('core_average_temp_c'))
    if package is not None:
        s['cpu_temp'] = round(package, 1)
        metric = s.setdefault('_metrics', {}).setdefault('cpu_temp', {})
        nested_meta = (cpu.get('_metrics') or {}).get('package_temp_c') or {}
        metric.update({
            'value': s['cpu_temp'], 'unit': '°C',
            'source': nested_meta.get('source') or cpu.get('package_temp_source') or 'LibreHardwareMonitorLib',
            'sensor': nested_meta.get('sensor') or cpu.get('package_temp_sensor') or f"{s.get('cpu_name') or 'CPU'} / CPU Package",
            'timestamp': nested_meta.get('sensor_timestamp') or nested_meta.get('timestamp') or metric.get('timestamp') or time.time(),
            'quality': 'VALID'
        })
    elif _temperature(s.get('cpu_temp')) is None:
        # Un 0 °C (u otro valor físicamente inválido) es ausencia de lectura,
        # no una medición real. REAL_OR_NA obliga a publicarlo como N/A.
        s['cpu_temp'] = None
        metric = s.setdefault('_metrics', {}).setdefault('cpu_temp', {})
        metric.update({
            'value': None, 'unit': '°C',
            'source': metric.get('source') or 'LibreHardwareMonitorLib',
            'quality': 'UNAVAILABLE',
            'error': 'Temperatura CPU no disponible: sensor devolvió un valor inválido.'
        })
    age = _num(s.get('_snapshot_age_seconds'))
    ts = _num(s.get('_snapshot_timestamp'))
    s['_telemetry_consistency'] = {'version': VERSION, 'policy': 'REAL_SOURCE_TRACEABILITY_NO_OFFSETS', 'canonical_cpu_temperature': 'CPU Package', 'cpu_package_c': package, 'cpu_core_max_c': core_max, 'cpu_core_average_c': core_avg, 'cpu_temp_display_c': _num(s.get('cpu_temp')), 'cpu_temp_metric': _metric_meta(s, 'cpu_temp'), 'cpu_usage_metric': _metric_meta(s, 'cpu_usage'), 'ram_usage_metric': _metric_meta(s, 'ram_usage'), 'gpu_usage_metric': _metric_meta(s, 'gpu_usage'), 'gpu_temp_metric': _metric_meta(s, 'gpu_temp'), 'snapshot_timestamp': ts, 'snapshot_age_seconds': age, 'stale': bool(age is not None and age > MAX_EXPECTED_SNAPSHOT_AGE_SECONDS), 'synthetic_adjustment': False, 'temperature_offset_c': 0.0}
    return s

def get_system_telemetry(wait_for_first=True):
    return apply_source_consistency(_base.get_system_telemetry(wait_for_first=wait_for_first))
