"""Obtiene la identidad real del equipo y construye el inventario de hardware detectable."""
from __future__ import annotations
from core.version import VERSION_LABEL as VERSION
# Código refactorizado: nombres estables y documentación en español.
import json
import os
import platform
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
NA = 'N/A'
_PLACEHOLDERS = {'', 'none', 'null', 'unknown', 'unknown product', 'system product name', 'system manufacturer', 'to be filled by o.e.m.', 'to be filled by oem', 'default string', 'not applicable', 'not specified', 'n/a', 'cpu no identificado', 'gpu no identificada'}
_NON_PHYSICAL_GPU_MARKERS = ('microsoft basic display', 'microsoft remote display', 'remote display', 'parsec', 'virtual display', 'virtualbox', 'vmware svga', 'indirect display')

def _clean(value: Any) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip().strip('\x00')
    if not s or s.lower() in _PLACEHOLDERS:
        return None
    return re.sub('\\s+', ' ', s)

def _num(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except Exception:
        return None

def _ps_json(script: str, timeout: int=15) -> Any:
    if os.name != 'nt':
        return None
    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    cmd = ['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-Command', "$ProgressPreference='SilentlyContinue'; " + script + ' | ConvertTo-Json -Depth 8 -Compress']
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, creationflags=flags, encoding='utf-8', errors='replace')
        if p.returncode != 0 or not p.stdout.strip():
            return None
        return json.loads(p.stdout.strip())
    except Exception:
        return None

def _cim(class_name: str, props: List[str]) -> Any:
    return _ps_json(f"Get-CimInstance {class_name} -ErrorAction Stop | Select-Object {','.join(props)}")

def _as_list(value: Any) -> List[dict]:
    if isinstance(value, list):
        return [x for x in value if isinstance(x, dict)]
    if isinstance(value, dict):
        return [value]
    return []

def _first_row(class_name: str, props: List[str]) -> dict:
    rows = _as_list(_cim(class_name, props))
    return rows[0] if rows else {}

def _chassis_type() -> Dict[str, Any]:
    rows = _as_list(_cim('Win32_SystemEnclosure', ['ChassisTypes']))
    codes: List[int] = []
    for row in rows:
        raw = row.get('ChassisTypes')
        values = raw if isinstance(raw, list) else [raw]
        for value in values:
            if value is None:
                continue
            try:
                codes.append(int(value))
            except Exception:
                pass
    laptop_codes = {8, 9, 10, 11, 12, 14, 18, 21, 30, 31, 32}
    desktop_codes = {3, 4, 5, 6, 7, 13, 15, 16, 23, 24, 35, 36}
    if any((c in laptop_codes for c in codes)):
        kind = 'LAPTOP'
    elif any((c in desktop_codes for c in codes)):
        kind = 'DESKTOP'
    else:
        kind = 'UNKNOWN'
    return {'type': kind, 'chassis_codes': codes, 'source': 'Win32_SystemEnclosure' if codes else None}

def collect_device_identity() -> Dict[str, Any]:
    cs = _first_row('Win32_ComputerSystem', ['Manufacturer', 'Model', 'SystemType', 'PCSystemType'])
    product = _first_row('Win32_ComputerSystemProduct', ['Vendor', 'Name', 'Version', 'IdentifyingNumber', 'UUID'])
    board = _first_row('Win32_BaseBoard', ['Manufacturer', 'Product', 'Version', 'SerialNumber'])
    bios = _first_row('Win32_BIOS', ['Manufacturer', 'SMBIOSBIOSVersion', 'ReleaseDate', 'SerialNumber'])
    chassis = _chassis_type()
    manufacturer = _clean(cs.get('Manufacturer')) or _clean(product.get('Vendor'))
    model = _clean(cs.get('Model')) or _clean(product.get('Name'))
    board_manufacturer = _clean(board.get('Manufacturer'))
    board_model = _clean(board.get('Product'))
    system_label = ' '.join(x for x in (manufacturer, model) if x).strip() or None
    board_label = ' '.join(x for x in (board_manufacturer, board_model) if x).strip() or None
    if chassis['type'] == 'DESKTOP':
        display_model = f'PC de escritorio · {board_label}' if board_label else (system_label or 'PC de escritorio')
        # En un PC ensamblado, un fabricante sin modelo de sistema no identifica una
        # plataforma física concreta. En ese caso la placa madre es un objetivo de
        # soporte más preciso para manuales/tareas de mantenimiento.
        support_target = system_label if model else (board_label or system_label)
    elif chassis['type'] == 'LAPTOP':
        display_model = system_label or model or manufacturer
        support_target = system_label
    else:
        display_model = system_label or board_label
        support_target = system_label or board_label
    return {'schema': 3, 'version': VERSION, 'captured_at': time.time(), 'platform': platform.system(), 'form_factor': chassis['type'], 'chassis_codes': chassis['chassis_codes'], 'manufacturer': manufacturer, 'model': model, 'display_model': display_model, 'support_target': support_target, 'system_type': _clean(cs.get('SystemType')), 'product': {'vendor': _clean(product.get('Vendor')), 'name': _clean(product.get('Name')), 'version': _clean(product.get('Version')), 'uuid': _clean(product.get('UUID')), 'identifying_number': _clean(product.get('IdentifyingNumber'))}, 'motherboard': {'manufacturer': board_manufacturer, 'model': board_model, 'version': _clean(board.get('Version')), 'serial': _clean(board.get('SerialNumber'))}, 'bios': {'manufacturer': _clean(bios.get('Manufacturer')), 'version': _clean(bios.get('SMBIOSBIOSVersion')), 'release_date': _clean(bios.get('ReleaseDate')), 'serial': _clean(bios.get('SerialNumber'))}, 'sources': {'system': 'Win32_ComputerSystem', 'product': 'Win32_ComputerSystemProduct', 'motherboard': 'Win32_BaseBoard', 'bios': 'Win32_BIOS', 'form_factor': chassis['source']}, 'policy': 'REAL_OR_NA_NO_INFERENCE'}

_SMBIOS_MEMORY_TYPES = {
    2: 'DRAM', 3: 'Synchronous DRAM', 17: 'SDRAM', 18: 'SGRAM', 19: 'RDRAM',
    20: 'DDR', 21: 'DDR2', 22: 'DDR2 FB-DIMM', 24: 'DDR3', 26: 'DDR4',
    27: 'LPDDR', 28: 'LPDDR2', 29: 'LPDDR3', 30: 'LPDDR4', 32: 'HBM',
    33: 'HBM2', 34: 'DDR5', 35: 'LPDDR5', 36: 'HBM3',
}

_MEMORY_FORM_FACTORS = {
    1: 'Other', 2: 'SIP', 3: 'DIP', 4: 'ZIP', 5: 'SOJ', 6: 'Propietario',
    7: 'SIMM', 8: 'DIMM', 9: 'TSOP', 10: 'PGA', 11: 'RIMM', 12: 'SODIMM',
    13: 'SRIMM', 14: 'SMD', 15: 'SSMP', 16: 'QFP', 17: 'TQFP', 18: 'SOIC',
    19: 'LCC', 20: 'PLCC', 21: 'BGA', 22: 'FPBGA', 23: 'LGA',
}

def _memory_voltage_v(value: Any) -> Optional[float]:
    raw = _num(value)
    if raw is None or raw <= 0:
        return None
    # Win32_PhysicalMemory documenta estos campos en milivoltios.
    return round(raw / 1000.0, 3)

def _ram_modules() -> List[Dict[str, Any]]:
    props = [
        'DeviceLocator', 'BankLabel', 'Manufacturer', 'PartNumber', 'SerialNumber',
        'Capacity', 'Speed', 'ConfiguredClockSpeed', 'SMBIOSMemoryType', 'MemoryType',
        'FormFactor', 'DataWidth', 'TotalWidth', 'ConfiguredVoltage', 'MinVoltage',
        'MaxVoltage', 'InterleaveDataDepth', 'InterleavePosition',
    ]
    rows = _as_list(_cim('Win32_PhysicalMemory', props))
    out = []
    for index, row in enumerate(rows):
        capacity = _num(row.get('Capacity'))
        smbios_type = _num(row.get('SMBIOSMemoryType'))
        legacy_type = _num(row.get('MemoryType'))
        type_code = int(smbios_type) if smbios_type is not None else int(legacy_type) if legacy_type is not None else None
        form_code = _num(row.get('FormFactor'))
        configured = _num(row.get('ConfiguredClockSpeed'))
        rated = _num(row.get('Speed'))
        out.append({
            'index': index,
            'slot': _clean(row.get('DeviceLocator')),
            'bank': _clean(row.get('BankLabel')),
            'manufacturer': _clean(row.get('Manufacturer')),
            'part_number': _clean(row.get('PartNumber')),
            'serial_number': _clean(row.get('SerialNumber')),
            'capacity_gb': round(capacity / 1024 ** 3, 2) if capacity is not None and capacity > 0 else None,
            'configured_speed_mhz': configured if configured is not None and configured > 0 else None,
            'speed_mhz': rated if rated is not None and rated > 0 else None,
            'memory_type': _SMBIOS_MEMORY_TYPES.get(type_code),
            'memory_type_code': type_code,
            'form_factor': _MEMORY_FORM_FACTORS.get(int(form_code)) if form_code is not None else None,
            'form_factor_code': int(form_code) if form_code is not None else None,
            'data_width_bits': int(row['DataWidth']) if _num(row.get('DataWidth')) is not None else None,
            'total_width_bits': int(row['TotalWidth']) if _num(row.get('TotalWidth')) is not None else None,
            'configured_voltage_v': _memory_voltage_v(row.get('ConfiguredVoltage')),
            'min_voltage_v': _memory_voltage_v(row.get('MinVoltage')),
            'max_voltage_v': _memory_voltage_v(row.get('MaxVoltage')),
            'interleave_data_depth': int(row['InterleaveDataDepth']) if _num(row.get('InterleaveDataDepth')) is not None else None,
            'interleave_position': int(row['InterleavePosition']) if _num(row.get('InterleavePosition')) is not None else None,
            'source': 'Win32_PhysicalMemory',
            'quality': 'VALID',
        })
    return out

def collect_ram_identity() -> Dict[str, Any]:
    """Devuelve inventario RAM real de Windows/SMBIOS sin inferir SPD ausente.

    ``available_slots`` es una resta transparente entre dos contadores WMI reales;
    no se usa para deducir canales, timings, XMP/EXPO ni capacidades máximas.
    """
    modules = _ram_modules()
    arrays = _as_list(_cim('Win32_PhysicalMemoryArray', ['MemoryDevices', 'Location', 'Use']))
    slot_counts = []
    for row in arrays:
        count = _num(row.get('MemoryDevices'))
        if count is not None and count >= 0:
            slot_counts.append(int(count))
    slots_total = sum(slot_counts) if slot_counts else None
    module_count = len(modules)
    installed = _ram_total_from_modules(modules)
    available_slots = None
    if slots_total is not None and slots_total >= module_count:
        available_slots = slots_total - module_count
    memory_types = sorted({str(m.get('memory_type')) for m in modules if m.get('memory_type')})
    return {
        'installed_capacity_gb': installed,
        'module_count': module_count,
        'slots_total': slots_total,
        'slots_available': available_slots,
        'modules': modules,
        'memory_types': memory_types,
        'source': 'Win32_PhysicalMemory + Win32_PhysicalMemoryArray' if modules or arrays else None,
        'quality': 'VALID' if modules or arrays else 'UNAVAILABLE',
        'available_slots_derivation': 'MemoryDevices - módulos detectados' if available_slots is not None else None,
        'policy': 'REAL_OR_NA_NO_CHANNEL_OR_TIMING_INFERENCE',
    }

def _cpu_wmi() -> Dict[str, Any]:
    props = [
        'Name', 'Manufacturer', 'Description', 'SocketDesignation',
        'MaxClockSpeed', 'CurrentClockSpeed', 'NumberOfCores',
        'NumberOfLogicalProcessors', 'ProcessorId', 'Architecture',
        'AddressWidth', 'DataWidth', 'L2CacheSize', 'L3CacheSize',
        'VirtualizationFirmwareEnabled',
        'SecondLevelAddressTranslationExtensions',
        'VMMonitorModeExtensions', 'Family', 'Stepping', 'Revision',
    ]
    row = _first_row('Win32_Processor', props)
    max_mhz = _num(row.get('MaxClockSpeed'))
    current_mhz = _num(row.get('CurrentClockSpeed'))
    l2_kb = _num(row.get('L2CacheSize'))
    l3_kb = _num(row.get('L3CacheSize'))
    architecture_code = _num(row.get('Architecture'))
    architecture_map = {
        0: 'x86',
        1: 'MIPS',
        2: 'Alpha',
        3: 'PowerPC',
        5: 'ARM',
        6: 'IA64',
        9: 'x64',
        12: 'ARM64',
    }
    architecture = architecture_map.get(int(architecture_code)) if architecture_code is not None else None

    def _bool_or_none(value: Any) -> Optional[bool]:
        if isinstance(value, bool):
            return value
        if value is None:
            return None
        text = str(value).strip().lower()
        if text in {'true', '1'}:
            return True
        if text in {'false', '0'}:
            return False
        return None

    return {
        'name': _clean(row.get('Name')),
        'manufacturer': _clean(row.get('Manufacturer')),
        'description': _clean(row.get('Description')),
        'socket': _clean(row.get('SocketDesignation')),
        'max_clock_ghz': round(max_mhz / 1000.0, 3) if max_mhz else None,
        'current_clock_ghz_wmi': round(current_mhz / 1000.0, 3) if current_mhz else None,
        'cores': int(row['NumberOfCores']) if _num(row.get('NumberOfCores')) is not None else None,
        'threads': int(row['NumberOfLogicalProcessors']) if _num(row.get('NumberOfLogicalProcessors')) is not None else None,
        'processor_id': _clean(row.get('ProcessorId')),
        'architecture': architecture,
        'architecture_code': int(architecture_code) if architecture_code is not None else None,
        'address_width_bits': int(row['AddressWidth']) if _num(row.get('AddressWidth')) is not None else None,
        'data_width_bits': int(row['DataWidth']) if _num(row.get('DataWidth')) is not None else None,
        'l2_cache_kb': int(l2_kb) if l2_kb is not None else None,
        'l3_cache_kb': int(l3_kb) if l3_kb is not None else None,
        'virtualization_firmware_enabled': _bool_or_none(row.get('VirtualizationFirmwareEnabled')),
        'slat_supported': _bool_or_none(row.get('SecondLevelAddressTranslationExtensions')),
        'vm_monitor_mode_extensions': _bool_or_none(row.get('VMMonitorModeExtensions')),
        'family': int(row['Family']) if _num(row.get('Family')) is not None else None,
        'stepping': int(row['Stepping']) if _num(row.get('Stepping')) is not None else None,
        'revision': int(row['Revision']) if _num(row.get('Revision')) is not None else None,
        'source': 'Win32_Processor' if row else None,
        'quality': 'VALID' if row else 'UNAVAILABLE',
    }


def collect_cpu_identity() -> Dict[str, Any]:
    """Devuelve especificaciones CPU reales expuestas por Win32_Processor."""
    return _cpu_wmi()

def _is_physical_gpu(row: dict) -> bool:
    """Acepta controladores de vídeo físicos sin depender del fabricante.

    Win32_VideoController expone también adaptadores virtuales. Un PNPDeviceID PCI real
    es la señal principal; cuando falta, se exige información adicional del controlador
    y se excluyen nombres virtuales conocidos por su naturaleza, no por marca de GPU.
    """
    name = (_clean(row.get('Name')) or '').lower()
    if not name or any(marker in name for marker in _NON_PHYSICAL_GPU_MARKERS):
        return False
    pnp = (_clean(row.get('PNPDeviceID')) or '').upper()
    if pnp.startswith('PCI\\') and 'VEN_' in pnp:
        return True
    compatibility = _clean(row.get('AdapterCompatibility'))
    processor = _clean(row.get('VideoProcessor'))
    return bool(pnp and compatibility and processor)

def _gpu_inventory_wmi() -> List[Dict[str, Any]]:
    rows = _as_list(_cim('Win32_VideoController', ['Name', 'AdapterRAM', 'DriverVersion', 'PNPDeviceID', 'AdapterCompatibility', 'VideoProcessor']))
    out = []
    seen = set()
    for row in rows:
        if not _is_physical_gpu(row):
            continue
        name = _clean(row.get('Name'))
        pnp = _clean(row.get('PNPDeviceID'))
        key = (name or '', pnp or '')
        if key in seen:
            continue
        seen.add(key)
        ram = _num(row.get('AdapterRAM'))
        out.append({'name': name, 'vram_gb_wmi': round(ram / 1024 ** 3, 2) if ram else None, 'driver_version': _clean(row.get('DriverVersion')), 'pnp_device_id': pnp, 'vendor': _clean(row.get('AdapterCompatibility')), 'video_processor': _clean(row.get('VideoProcessor')), 'hardware_type': 'WMI_PHYSICAL_DISPLAY_ADAPTER', 'source': 'Win32_VideoController', 'quality': 'VALID'})
    return out

def _storage_wmi() -> List[Dict[str, Any]]:
    rows = _as_list(_cim('Win32_DiskDrive', ['Index', 'Model', 'Manufacturer', 'SerialNumber', 'Size', 'InterfaceType', 'PNPDeviceID']))
    out = []
    for row in rows:
        model = _clean(row.get('Model'))
        if not model:
            continue
        size = _num(row.get('Size'))
        out.append({'index': int(row['Index']) if _num(row.get('Index')) is not None else None, 'name': model, 'model': model, 'manufacturer': _clean(row.get('Manufacturer')), 'serial': _clean(row.get('SerialNumber')), 'total_space_gb': round(size / 1024 ** 3, 2) if size else None, 'interface': _clean(row.get('InterfaceType')), 'pnp_device_id': _clean(row.get('PNPDeviceID')), 'temperature_c': None, 'life_percent': None, 'source': 'Win32_DiskDrive', 'quality': 'IDENTITY_ONLY'})
    return out

def _valid_telemetry_snapshot(t: Any) -> bool:
    if not isinstance(t, dict) or not t:
        return False
    if t.get('_snapshot_pending'):
        return False
    cpu = _clean(t.get('cpu_name'))
    ram = _num(t.get('ram_total_gb'))
    gpus = t.get('_gpus')
    storage = t.get('_storage_devices')
    evidence = 0
    if cpu:
        evidence += 1
    if ram and ram > 0:
        evidence += 1
    if isinstance(gpus, list) and gpus:
        evidence += 1
    if isinstance(storage, list) and storage:
        evidence += 1
    if isinstance(t.get('_battery'), dict):
        evidence += 1
    return evidence >= 2

def acquire_aligned_telemetry(timeout_seconds: float=12.0, poll_seconds: float=0.35) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Adquiere la operación `acquire_aligned_telemetry` dentro de CorePulse sin alterar la evidencia real ni las reglas del módulo."""
    try:
        from core.telemetry_background import get_system_telemetry
    except Exception as exc:
        return ({}, {'ready': False, 'source': 'core.telemetry_background', 'error': f'{type(exc).__name__}: {exc}', 'attempts': 0})
    deadline = time.monotonic() + max(0.5, float(timeout_seconds))
    attempts = 0
    last: Dict[str, Any] = {}
    while time.monotonic() < deadline:
        attempts += 1
        try:
            sample = get_system_telemetry(wait_for_first=True)
        except TypeError:
            sample = get_system_telemetry()
        except Exception as exc:
            return (last, {'ready': False, 'source': 'core.telemetry_background', 'error': f'{type(exc).__name__}: {exc}', 'attempts': attempts})
        if isinstance(sample, dict):
            last = sample
        if _valid_telemetry_snapshot(last):
            return (last, {'ready': True, 'source': 'core.telemetry_background', 'attempts': attempts, 'snapshot_age_seconds': last.get('_snapshot_age_seconds'), 'worker_refresh_duration_ms': last.get('_worker_refresh_duration_ms'), 'sensor_summary': last.get('_sensor_summary')})
        time.sleep(max(0.05, float(poll_seconds)))
    return (last, {'ready': False, 'source': 'core.telemetry_background', 'attempts': attempts, 'snapshot_pending': bool(last.get('_snapshot_pending')) if isinstance(last, dict) else None, 'worker_error': last.get('_worker_error') if isinstance(last, dict) else None})

def _normalize_lhm_gpus(raw: Any) -> List[Dict[str, Any]]:
    out = []
    if not isinstance(raw, list):
        return out
    seen = set()
    for gpu in raw:
        if not isinstance(gpu, dict):
            continue
        name = _clean(gpu.get('name'))
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        item = dict(gpu)
        item['name'] = name
        item.setdefault('source', 'LibreHardwareMonitorLib')
        item.setdefault('quality', 'VALID')
        out.append(item)
    return out

def _merge_gpu_inventory(lhm: List[dict], wmi: List[dict]) -> List[dict]:
    """Gestiona la operación `merge_gpu_inventory` dentro de CorePulse sin alterar la evidencia real ni las reglas del módulo."""
    out: List[dict] = []
    names = set()
    for gpu in lhm:
        name = (_clean(gpu.get('name')) or '').lower()
        if not name:
            continue
        out.append(dict(gpu))
        names.add(name)
    for gpu in wmi:
        name = (_clean(gpu.get('name')) or '').lower()
        if not name:
            continue
        if any((name in existing or existing in name for existing in names)):
            continue
        out.append(dict(gpu))
        names.add(name)
    return out

def _ram_total_from_modules(modules: List[dict]) -> Optional[float]:
    capacities = [_num(m.get('capacity_gb')) for m in modules if isinstance(m, dict)]
    valid = [v for v in capacities if v is not None and v > 0]
    return round(sum(valid), 2) if valid else None

def collect_hardware_inventory(telemetry: Optional[dict]=None, disks: Optional[list]=None) -> Dict[str, Any]:
    identity = collect_device_identity()
    t = telemetry if isinstance(telemetry, dict) else {}
    d = disks if isinstance(disks, list) else []
    modules = _ram_modules()
    module_total = _ram_total_from_modules(modules)
    cpu_wmi = _cpu_wmi()
    cpu_name = _clean(t.get('cpu_name')) or cpu_wmi.get('name')
    ram_total = _num(t.get('ram_total_gb'))
    if ram_total is None or ram_total <= 0:
        ram_total = module_total
    lhm_gpus = _normalize_lhm_gpus(t.get('_gpus'))
    wmi_gpus = _gpu_inventory_wmi()
    gpus = _merge_gpu_inventory(lhm_gpus, wmi_gpus)
    telemetry_storage = t.get('_storage_devices') if isinstance(t.get('_storage_devices'), list) else []
    storage = telemetry_storage or d or _storage_wmi()
    battery = t.get('_battery') if isinstance(t.get('_battery'), dict) else None
    cpu_source = 'core.telemetry_background/LibreHardwareMonitorLib' if _clean(t.get('cpu_name')) else cpu_wmi.get('source')
    ram_source = 'core.telemetry_background/psutil.virtual_memory' if _num(t.get('ram_total_gb')) is not None else 'Win32_PhysicalMemory'
    storage_source = 'core.telemetry_background/_storage_devices' if telemetry_storage else 'core.telemetry_background/get_all_disks_data' if d else 'Win32_DiskDrive'
    return {'schema': 2, 'version': VERSION, 'captured_at': time.time(), 'identity': identity, 'cpu': {'name': cpu_name, 'telemetry_name': _clean(t.get('cpu_name')), 'wmi': cpu_wmi, 'current_ghz': _num(t.get('cpu_ghz')), 'source': cpu_source}, 'ram': {'total_gb': round(ram_total, 2) if ram_total is not None else None, 'telemetry_total_gb': _num(t.get('ram_total_gb')), 'module_total_gb': module_total, 'modules': modules, 'module_count': len(modules), 'source': ram_source}, 'gpus': gpus, 'gpu_count': len(gpus), 'gpu_sources': {'lhm_count': len(lhm_gpus), 'wmi_physical_count': len(wmi_gpus)}, 'storage': storage, 'storage_count': len(storage), 'storage_source': storage_source, 'battery': battery, 'battery_source': 'core.telemetry_background/_battery' if battery else None, 'telemetry_alignment': {'snapshot_pending': bool(t.get('_snapshot_pending')), 'telemetry_version': t.get('_telemetry_version'), 'sensor_summary': t.get('_sensor_summary'), 'policy': 'PREFER_LIVE_TELEMETRY_THEN_REAL_OS_IDENTITY_FALLBACK'}, 'policy': 'REAL_OR_NA_NO_INFERENCE'}

def save_inventory(path: str | Path, inventory: Dict[str, Any]) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(f'{p.name}.{os.getpid()}.tmp')
    tmp.write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(tmp, p)
    return p


# V482: fusión sin cambios de lógica desde core/sensors/gpu_display_logic.py
def _number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except Exception:
        return None


def gb_from_mb(value):
    number = _number(value)
    return None if number is None else number / 1024.0


def gb_from_bytes(value):
    number = _number(value)
    return None if number is None else number / (1024.0 ** 3)


def windows_status_text(value):
    raw = str(value or '').strip()
    if not raw:
        return 'N/A'
    labels = {
        'ok': 'Funcionando correctamente',
        'degraded': 'Rendimiento degradado',
        'error': 'Error reportado por Windows',
        'pred fail': 'Posible fallo reportado',
        'starting': 'Iniciando',
        'stopping': 'Deteniéndose',
        'stressed': 'Bajo carga',
        'nonrecover': 'Error no recuperable',
        'no contact': 'Sin comunicación',
        'lost comm': 'Comunicación perdida',
        'unknown': 'Estado desconocido',
    }
    return labels.get(raw.casefold(), raw)


def human_gpu_hardware_type(value):
    raw = str(value or '').strip()
    if not raw:
        return 'N/A'
    known = {
        'gpunvidia': 'NVIDIA · LibreHardwareMonitor',
        'gpuamd': 'AMD · LibreHardwareMonitor',
        'gpuintel': 'Intel · LibreHardwareMonitor',
    }
    key = raw.casefold()
    if key in known:
        return known[key]
    if key.startswith('gpu') and len(raw) > 3:
        return f'{raw[3:]} · LibreHardwareMonitor'
    return raw


def wmi_vram_presentation(os_bytes, sensor_total_mb=None):
    """Retorna ``(texto, limitado)`` sin promover AdapterRAM sobre un sensor real.

    ``Win32_VideoController.AdapterRAM`` es un entero de 32 bits y puede quedarse
    alrededor de 4 GiB en adaptadores con más memoria. La limitación sólo se
    declara cuando una lectura real del mismo adaptador demuestra una capacidad
    claramente superior.
    """
    wmi_gb = gb_from_bytes(os_bytes)
    sensor_gb = gb_from_mb(sensor_total_mb)
    if wmi_gb is None:
        return 'N/A', False
    limited = (
        sensor_gb is not None
        and sensor_gb > 4.25
        and wmi_gb <= 4.01
        and sensor_gb > wmi_gb + 0.5
    )
    if limited:
        return f'{wmi_gb:.2f} GB · limitado por WMI', True
    return f'{wmi_gb:.2f} GB', False


def active_display_on_other_gpu(selected_gpu, all_gpus):
    """True si Windows expone un modo de pantalla activo en otro adaptador."""
    for gpu in all_gpus or []:
        if gpu is selected_gpu:
            continue
        os_inv = gpu.get('os_inventory') if isinstance(gpu, dict) and isinstance(gpu.get('os_inventory'), dict) else {}
        width = _number(os_inv.get('current_horizontal_resolution'))
        height = _number(os_inv.get('current_vertical_resolution'))
        mode = str(os_inv.get('video_mode_description') or '').strip()
        if (width is not None and height is not None) or mode:
            return True
    return False


__all__ = [
    'active_display_on_other_gpu',
    'gb_from_bytes',
    'gb_from_mb',
    'human_gpu_hardware_type',
    'windows_status_text',
    'wmi_vram_presentation',
    "get_cpu_frequency_evidence"
]

# V484: consolidación de core/sensors/cpu_frequency.py. Ruta anterior resuelta de forma diferida.
import json

import math

import os

import platform

import subprocess

import threading

import time

import psutil

_CACHE_LOCK = threading.RLock()

_CACHE = {"at": 0.0, "value": None}

_CACHE_SECONDS = 1.0

def _cpu_frequency_num(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except Exception:
        return None
    if not math.isfinite(number):
        return None
    return number

def _valid_mhz(value):
    value = _cpu_frequency_num(value)
    if value is None or not (50.0 <= value <= 20000.0):
        return None
    return value

def _evidence(mhz, source, sensor, *, derived=False, detail=None):
    mhz = _valid_mhz(mhz)
    if mhz is None:
        return None
    return {
        "ghz": round(mhz / 1000.0, 3),
        "mhz": round(mhz, 3),
        "source": source,
        "sensor": sensor,
        "timestamp": time.time(),
        "quality": "VALID",
        "derived_from_real": bool(derived),
        "synthetic_adjustment": False,
        "interpolation": False,
        "offset_applied": 0.0,
        "detail": detail,
    }

def _from_psutil():
    try:
        freq = psutil.cpu_freq()
    except Exception:
        return None
    current = _valid_mhz(getattr(freq, "current", None) if freq else None)
    if current is None:
        return None
    return _evidence(
        current,
        "psutil.cpu_freq",
        "psutil.cpu_freq().current",
        detail="Frecuencia actual reportada por psutil/Windows",
    )

def _powershell_json(script, timeout=5):
    if os.name != "nt" and platform.system() != "Windows":
        return None
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    cmd = [
        "powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
        "-Command", "$ProgressPreference='SilentlyContinue'; " + script + " | ConvertTo-Json -Depth 5 -Compress",
    ]
    try:
        cp = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout, creationflags=flags,
        )
        if cp.returncode != 0 or not cp.stdout.strip():
            return None
        return json.loads(cp.stdout.strip())
    except Exception:
        return None

def _as_rows(value):
    if isinstance(value, list):
        return [row for row in value if isinstance(row, dict)]
    if isinstance(value, dict):
        return [value]
    return []

def _from_windows_perf_cim():
    data = _powershell_json(
        "Get-CimInstance Win32_PerfFormattedData_Counters_ProcessorInformation -ErrorAction Stop "
        "| Where-Object { $_.Name -eq '_Total' } "
        "| Select-Object -First 1 Name,ProcessorFrequency,PercentProcessorPerformance"
    )
    rows = _as_rows(data)
    if not rows:
        return None
    row = rows[0]
    base = _valid_mhz(row.get("ProcessorFrequency"))
    perf = _cpu_frequency_num(row.get("PercentProcessorPerformance"))
    if base is not None and perf is not None and 1.0 <= perf <= 1000.0:
        effective = base * perf / 100.0
        if _valid_mhz(effective) is not None:
            return _evidence(
                effective,
                "Win32_PerfFormattedData_Counters_ProcessorInformation",
                "_Total / ProcessorFrequency × PercentProcessorPerformance / 100",
                derived=True,
                detail=f"ProcessorFrequency={base:.0f} MHz; PercentProcessorPerformance={perf:.1f}%",
            )
    if base is not None:
        return _evidence(
            base,
            "Win32_PerfFormattedData_Counters_ProcessorInformation",
            "_Total / ProcessorFrequency",
            detail="Frecuencia reportada por contador CIM de Windows",
        )
    return None

def _from_win32_processor():
    data = _powershell_json(
        "Get-CimInstance Win32_Processor -ErrorAction Stop "
        "| Select-Object Name,CurrentClockSpeed"
    )
    rows = _as_rows(data)
    values = [_valid_mhz(row.get("CurrentClockSpeed")) for row in rows]
    values = [v for v in values if v is not None]
    if not values:
        return None
    mhz = sum(values) / len(values)
    return _evidence(
        mhz,
        "Win32_Processor.CurrentClockSpeed",
        "Win32_Processor / CurrentClockSpeed",
        derived=len(values) > 1,
        detail="Frecuencia actual reportada por CIM de Windows",
    )

def get_cpu_frequency_evidence(force=False):
    """Devuelve evidencia real de frecuencia CPU o None.

    La lectura psutil se intenta siempre porque es barata y refleja el estado actual.
    Las consultas CIM se cachean brevemente para no lanzar PowerShell cada frame.
    """
    ps = _from_psutil()
    if ps is not None:
        return ps

    now = time.monotonic()
    with _CACHE_LOCK:
        if not force and _CACHE["value"] is not None and now - _CACHE["at"] <= _CACHE_SECONDS:
            return dict(_CACHE["value"])

    value = _from_windows_perf_cim() or _from_win32_processor()
    with _CACHE_LOCK:
        _CACHE["at"] = now
        _CACHE["value"] = dict(value) if isinstance(value, dict) else None
    return value
