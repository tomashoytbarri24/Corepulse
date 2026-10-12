"""Enumera sensores térmicos reales para diagnosticar CPU sin inventar valores."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.sensor_stack_setup import pawnio_status


def check_pawnio():
    """Equivalente al antiguo check_pawnio.py, sin iniciar proveedores térmicos."""
    status = pawnio_status()
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0 if status.get('installed') else 2


def main() -> int:
    from core.lhm_provider import get_lhm_provider
    from core.cpu_temp_compat import query_packaged_cpu_temperature
    provider = get_lhm_provider()
    sensors = provider.refresh(min_interval=0.0)
    temps = []
    cpu_related = []
    for s in sensors:
        if str(s.get('sensor_type') or '').casefold() == 'temperature':
            row = {
                'hardware_type': s.get('hardware_type'),
                'hardware_name': s.get('hardware_name'),
                'sensor_name': s.get('sensor_name'),
                'value': s.get('value'),
                'identifier': s.get('identifier'),
                'source': s.get('source'),
            }
            temps.append(row)
            text = ' '.join(str(row.get(k) or '') for k in ('hardware_type','hardware_name','sensor_name','identifier')).casefold()
            if any(token in text for token in ('cpu','ryzen','tctl','tdie','package','core')):
                cpu_related.append(row)

    selected = provider.cpu_temperature()
    compatibility_selected = query_packaged_cpu_temperature(force=True)
    payload = {
        'timestamp': time.time(),
        'provider_available': provider.available,
        'provider_error': provider.error,
        'pawnio': pawnio_status(),
        'selected_cpu_temperature': selected,
        'compatibility_cpu_temperature': compatibility_selected,
        'sensor_count': len(sensors),
        'temperature_sensor_count': len(temps),
        'cpu_related_temperature_sensor_count': len(cpu_related),
        'cpu_related_temperature_sensors': cpu_related,
        'all_temperature_sensors': temps,
        'real_or_na': True,
        'note': 'Este diagnóstico solo enumera sensores reales reportados por LibreHardwareMonitor; no estima temperaturas.',
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    print(text)
    out = ROOT / 'evidence' / 'cpu_sensor_probe.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding='utf-8')
    print(f'\nEvidencia: {out}')
    return 0

if __name__ == '__main__':
    raise SystemExit(check_pawnio() if '--check-pawnio' in sys.argv[1:] else main())
