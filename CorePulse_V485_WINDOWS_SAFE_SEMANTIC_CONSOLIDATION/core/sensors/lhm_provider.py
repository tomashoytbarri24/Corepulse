"""Proveedor de sensores reales basado en LibreHardwareMonitor mediante HardwareMonitor y pythonnet."""
from __future__ import annotations
# Código refactorizado: nombres estables y documentación en español.
import threading
import time
from typing import Any

class LibreHardwareSensorProvider:

    def __init__(self):
        self._lock = threading.RLock()
        self._computer = None
        self._available = False
        self._error = None
        self._last_refresh = 0.0
        self._sensors = []
        self._source_name = 'LibreHardwareMonitorLib'
        self._engine_state = {}
        self._initialize()

    @property
    def available(self):
        return self._available

    @property
    def error(self):
        return self._error

    @property
    def source_name(self):
        return self._source_name

    @property
    def engine_state(self):
        return dict(self._engine_state)

    def _initialize(self):
        official_error = None
        Computer = None
        try:
            from core.lhm_official import load_official_computer_class
            Computer, state = load_official_computer_class(allow_download=True)
            self._engine_state = dict(state or {})
            if Computer is not None:
                self._source_name = f'LibreHardwareMonitor {state.get("version") or "official"} (official)'
            else:
                official_error = (state or {}).get('error')
        except Exception as exc:
            official_error = f'{type(exc).__name__}: {exc}'

        try:
            if Computer is None:
                import HardwareMonitor  # fallback: wrapper instalado en el runtime
                from HardwareMonitor.Hardware import Computer as PackagedComputer
                Computer = PackagedComputer
                self._source_name = 'LibreHardwareMonitorLib (HardwareMonitor package fallback)'
                self._engine_state = {
                    'ok': True, 'version': None, 'source': 'HardwareMonitor package fallback',
                    'official_error': official_error,
                }
            computer = Computer()
            computer.IsMotherboardEnabled = True
            computer.IsControllerEnabled = True
            computer.IsCpuEnabled = True
            computer.IsGpuEnabled = True
            computer.IsBatteryEnabled = True
            computer.IsMemoryEnabled = True
            computer.IsNetworkEnabled = False
            computer.IsStorageEnabled = True
            try:
                computer.IsPsuEnabled = True
            except Exception:
                pass
            computer.Open()
            self._computer = computer
            self._available = True
            self._error = None
        except Exception as exc:
            self._computer = None
            self._available = False
            detail = f'{type(exc).__name__}: {exc}'
            if official_error:
                detail += f' | official={official_error}'
            self._error = detail

    @staticmethod
    def _safe_value(value):
        if value is None:
            return None
        try:
            return float(value)
        except Exception:
            return None

    @staticmethod
    def _enum_name(value):
        try:
            text = str(value)
        except Exception:
            return ''
        if '.' in text:
            text = text.split('.')[-1]
        return text.strip()

    def _collect_hardware(self, hardware, result):
        try:
            hardware.Update()
        except Exception:
            pass
        hardware_name = str(getattr(hardware, 'Name', '') or '')
        hardware_type = self._enum_name(getattr(hardware, 'HardwareType', ''))
        try:
            sensors = list(hardware.Sensors)
        except Exception:
            sensors = []
        for sensor in sensors:
            value = self._safe_value(getattr(sensor, 'Value', None))
            if value is None:
                continue
            result.append({'hardware_name': hardware_name, 'hardware_type': hardware_type, 'sensor_name': str(getattr(sensor, 'Name', '') or ''), 'sensor_type': self._enum_name(getattr(sensor, 'SensorType', '')), 'value': value, 'identifier': str(getattr(sensor, 'Identifier', '') or ''), 'timestamp': time.time(), 'source': self._source_name})
        try:
            subhardware = list(hardware.SubHardware)
        except Exception:
            subhardware = []
        for child in subhardware:
            self._collect_hardware(child, result)

    def refresh(self, min_interval=0.35):
        with self._lock:
            now = time.monotonic()
            if self._sensors and now - self._last_refresh < min_interval:
                return list(self._sensors)
            if self._computer is None:
                self._initialize()
            if self._computer is None:
                return []
            result = []
            try:
                hardware_list = list(self._computer.Hardware)
                for hardware in hardware_list:
                    self._collect_hardware(hardware, result)
                self._sensors = result
                self._last_refresh = now
                self._available = True
                self._error = None
                return list(result)
            except Exception as exc:
                self._error = f'{type(exc).__name__}: {exc}'
                return list(self._sensors)

    def all_sensors(self):
        return self.refresh()

    def _temperatures(self, hardware_types):
        wanted = {x.lower() for x in hardware_types}
        values = []
        for sensor in self.refresh():
            if sensor['sensor_type'].lower() != 'temperature':
                continue
            hw_type = sensor['hardware_type'].lower()
            if hw_type not in wanted:
                continue
            value = sensor['value']
            if 0 < value < 125:
                values.append(sensor)
        return values

    @staticmethod
    def _cpu_temperature_score(sensor):
        """Puntúa sensores térmicos reales que pueden representar la CPU.

        En algunos portátiles el EC/SuperIO publica la temperatura de CPU bajo
        Motherboard en vez de HardwareType.Cpu. La puntuación permite usar ese
        sensor real sin confundirlo con GPU, SSD, batería o ambiente.
        """
        name = str(sensor.get('sensor_name') or '').strip().casefold()
        hw_name = str(sensor.get('hardware_name') or '').strip().casefold()
        hw_type = str(sensor.get('hardware_type') or '').strip().casefold()
        ident = str(sensor.get('identifier') or '').strip().casefold()
        text = f'{name} {hw_name} {hw_type} {ident}'

        # Descartes fuertes: nunca reutilizar otra temperatura como si fuera CPU.
        forbidden = ('gpu', 'nvidia', 'radeon gpu', 'nvme', 'ssd', 'hdd', 'storage',
                     'battery', 'bater', 'ambient', 'pch', 'vrm', 'mos', 'memory')
        if any(token in text for token in forbidden):
            return -1000

        score = 0
        if hw_type == 'cpu':
            score += 100
        if '/cpu/' in ident or ident.startswith('/cpu'):
            score += 90
        if 'ryzen' in hw_name or 'processor' in hw_name or 'cpu' in hw_name:
            score += 45

        exact = {
            'cpu package': 160, 'cpu (tctl/tdie)': 155, 'tctl/tdie': 150,
            'cpu tctl/tdie': 150, 'cpu core': 145, 'cpu': 140,
            'cpu temperature': 140, 'cpu temp': 140, 'core max': 120,
            'core average': 110, 'tdie': 110, 'tctl': 105,
        }
        score += exact.get(name, 0)
        for token, points in (
            ('cpu package', 130), ('tctl/tdie', 125), ('cpu core', 120),
            ('cpu temp', 115), ('cpu temperature', 115), ('cpu', 95),
            ('tdie', 80), ('tctl', 75), ('package', 55),
        ):
            if token in name:
                score = max(score, points + (100 if hw_type == 'cpu' else 0))
        return score

    def cpu_temperature(self):
        # 1) Ruta canónica: sensores bajo HardwareType.Cpu.
        sensors = self._temperatures({'Cpu'})
        priority = ('cpu package', 'package', 'core max', 'core average',
                    'cpu (tctl/tdie)', 'tctl/tdie', 'tdie', 'tctl')
        lowered = [(s['sensor_name'].lower(), s) for s in sensors]
        for wanted in priority:
            matches = [sensor for name, sensor in lowered if wanted == name or wanted in name]
            if matches:
                chosen = max(matches, key=lambda x: x['value'])
                return {'value': round(chosen['value'], 1), 'source': getattr(self, '_source_name', 'LibreHardwareMonitorLib'),
                        'sensor': chosen['sensor_name'], 'hardware': chosen['hardware_name'],
                        'identifier': chosen.get('identifier'), 'fallback': False}
        if sensors:
            chosen = max(sensors, key=lambda x: (self._cpu_temperature_score(x), x['value']))
            return {'value': round(chosen['value'], 1), 'source': getattr(self, '_source_name', 'LibreHardwareMonitorLib'),
                    'sensor': chosen['sensor_name'], 'hardware': chosen['hardware_name'],
                    'identifier': chosen.get('identifier'), 'fallback': False}

        # 2) Portátiles/OEM: el sensor CPU puede vivir bajo EmbeddedController,
        # SuperIO o Motherboard. Se busca por nombre/identifier y se conserva
        # trazabilidad completa. Sólo se aceptan valores físicos plausibles.
        candidates = []
        for sensor in self.refresh():
            if str(sensor.get('sensor_type') or '').casefold() != 'temperature':
                continue
            value = self._safe_value(sensor.get('value'))
            if value is None or not (5.0 <= value <= 115.0):
                continue
            score = self._cpu_temperature_score(sensor)
            if score >= 90:
                candidates.append((score, sensor))
        if not candidates:
            return None
        score, chosen = max(candidates, key=lambda item: (item[0], item[1]['value']))
        return {'value': round(chosen['value'], 1), 'source': getattr(self, '_source_name', 'LibreHardwareMonitorLib'),
                'sensor': chosen['sensor_name'], 'hardware': chosen['hardware_name'],
                'identifier': chosen.get('identifier'), 'fallback': True,
                'selection_score': score}

    def gpu_temperature(self):
        sensors = [s for s in self.refresh() if s['sensor_type'].lower() == 'temperature' and s['hardware_type'].lower().startswith('gpu') and 0 < s['value'] < 125]
        if not sensors:
            return None
        priority = ('gpu core', 'gpu temperature', 'core', 'temperature')
        for wanted in priority:
            matches = [s for s in sensors if wanted in s['sensor_name'].lower()]
            if matches:
                chosen = max(matches, key=lambda x: x['value'])
                return {'value': round(chosen['value'], 1), 'source': getattr(self, '_source_name', 'LibreHardwareMonitorLib'), 'sensor': chosen['sensor_name'], 'hardware': chosen['hardware_name']}
        chosen = max(sensors, key=lambda x: x['value'])
        return {'value': round(chosen['value'], 1), 'source': getattr(self, '_source_name', 'LibreHardwareMonitorLib'), 'sensor': chosen['sensor_name'], 'hardware': chosen['hardware_name']}

    def gpu_load(self):
        candidates = []
        for sensor in self.refresh():
            if sensor['sensor_type'].lower() != 'load':
                continue
            if not sensor['hardware_type'].lower().startswith('gpu'):
                continue
            value = sensor['value']
            if 0 <= value <= 100:
                candidates.append(sensor)
        if not candidates:
            return None
        preferred_names = ('gpu core', 'gpu d3d 3d', 'd3d 3d', 'core', 'gpu')
        for wanted in preferred_names:
            matches = [s for s in candidates if wanted == s['sensor_name'].lower() or wanted in s['sensor_name'].lower()]
            if matches:
                chosen = max(matches, key=lambda x: x['value'])
                return {'value': round(chosen['value'], 1), 'source': getattr(self, '_source_name', 'LibreHardwareMonitorLib'), 'sensor': chosen['sensor_name'], 'hardware': chosen['hardware_name']}
        chosen = max(candidates, key=lambda x: x['value'])
        return {'value': round(chosen['value'], 1), 'source': getattr(self, '_source_name', 'LibreHardwareMonitorLib'), 'sensor': chosen['sensor_name'], 'hardware': chosen['hardware_name']}

    def storage_temperatures(self):
        values = []
        for sensor in self._temperatures({'Storage'}):
            values.append({'value': round(sensor['value'], 1), 'source': self._source_name, 'sensor': sensor['sensor_name'], 'hardware': sensor['hardware_name'], 'identifier': sensor['identifier']})
        return values

    def close(self):
        with self._lock:
            if self._computer is not None:
                try:
                    self._computer.Close()
                except Exception:
                    pass
            self._computer = None
_PROVIDER = None
_PROVIDER_LOCK = threading.Lock()

def get_lhm_provider():
    global _PROVIDER
    with _PROVIDER_LOCK:
        if _PROVIDER is None:
            _PROVIDER = LibreHardwareSensorProvider()
        return _PROVIDER
