"""Centro de Salud / Batería: lecturas de Windows, solo lectura y REAL_OR_NA.

Estado instantáneo: GetSystemPowerStatus a través de psutil.sensors_battery.
Capacidades/ciclos: CIM root\\wmi y, si faltan, informe XML nativo powercfg.
Solo lectura: el reporte temporal de diagnóstico se elimina inmediatamente.
No modifica planes de energía ni configuraciones del equipo.
"""
from __future__ import annotations

from concurrent.futures import Future
from concurrent.futures.thread import ThreadPoolExecutor
from datetime import datetime
import json
import math
import os
import shutil
import subprocess
import tempfile
import time
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

import psutil
from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot


# Inventario SOLO LECTURA; timeout limitado para no bloquear CorePulse.
_BATTERY_CIM_SCRIPT = r'''
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
function Read-BatteryClass([string]$ns, [string]$name, [string[]]$fields) {
    try {
        @(Get-CimInstance -Namespace $ns -ClassName $name -ErrorAction Stop |
            Select-Object -Property $fields)
    } catch { @() }
}
$payload = [ordered]@{
    design = @(Read-BatteryClass 'root/wmi' 'BatteryStaticData' @('InstanceName','DesignedCapacity','DeviceName','ManufactureName'))
    full = @(Read-BatteryClass 'root/wmi' 'BatteryFullChargedCapacity' @('InstanceName','FullChargedCapacity'))
    cycles = @(Read-BatteryClass 'root/wmi' 'BatteryCycleCount' @('InstanceName','CycleCount'))
    win32 = @(Read-BatteryClass 'root/cimv2' 'Win32_Battery' @('Name','Manufacturer','DeviceID','DesignCapacity','FullChargeCapacity'))
}
ConvertTo-Json -InputObject $payload -Depth 6 -Compress
'''.strip()


def _number(value, minimum=0, maximum=math.inf):
    if isinstance(value, bool) or value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return result if math.isfinite(result) and minimum <= result <= maximum else None


def _rows(payload, name):
    raw = payload.get(name, []) if isinstance(payload, dict) else []
    if isinstance(raw, dict):
        return [raw]
    return [item for item in raw if isinstance(item, dict)] if isinstance(raw, list) else []


def _key(record):
    return str(record.get('InstanceName') or '').strip().casefold()


def parse_battery_specs(payload):
    """Une capacidades por InstanceName; N/A si una cifra no es comprobable.

    Para baterías múltiples únicamente calcula la salud agregada cuando TODAS
    tienen capacidad de diseño y plena comparables. No promedia ciclos distintos.
    """
    designs = { _key(r): r for r in _rows(payload, 'design') if _key(r) }
    fulls = { _key(r): r for r in _rows(payload, 'full') if _key(r) }
    cycles = { _key(r): r for r in _rows(payload, 'cycles') if _key(r) }
    win32 = _rows(payload, 'win32')
    answer = {
        'batteryFound': bool(designs or fulls or win32),
        'count': len(designs) or len(win32) or len(fulls),
        'designWh': None, 'fullWh': None, 'healthPct': None,
        'wearPct': None, 'cycles': None, 'model': None, 'manufacturer': None,
    }
    if len(win32) == 1:
        answer['model'] = str(win32[0].get('Name') or '').strip() or None
        answer['manufacturer'] = str(win32[0].get('Manufacturer') or '').strip() or None
    if not designs or set(designs) != set(fulls):
        # Algunos fabricantes publican ambos valores SOLO en Win32_Battery.
        # Aceptar este respaldo únicamente si hay una batería inequívoca.
        if len(win32) == 1 and len(designs) <= 1 and len(fulls) <= 1:
            design = _number(win32[0].get('DesignCapacity'), 1000, 2000000)
            full = _number(win32[0].get('FullChargeCapacity'), 1000, 2000000)
            if design is not None and full is not None and full <= design * 1.25:
                health = round(full / design * 100, 1)
                answer.update(designWh=round(design / 1000, 1),
                              fullWh=round(full / 1000, 1),
                              healthPct=health,
                              wearPct=round(max(0.0, 100.0 - health), 1))
        if len(cycles) == 1 and max(len(designs), len(fulls), len(win32)) <= 1:
            item = next(iter(cycles.values()))
            cycle = _number(item.get('CycleCount'), 0, 20000)
            answer['cycles'] = int(cycle) if cycle is not None else None
        return answer
    design_total = 0.0
    full_total = 0.0
    cycle_values = []
    for key, item in designs.items():
        design = _number(item.get('DesignedCapacity'), 1000, 2000000)
        full = _number(fulls[key].get('FullChargedCapacity'), 1000, 2000000)
        if design is None or full is None or full > design * 1.25:
            return answer
        design_total += design
        full_total += full
        cycle = _number(cycles[key].get('CycleCount'), 0, 20000) if key in cycles else None
        cycle_values.append(int(cycle) if cycle is not None else None)
    health = full_total / design_total * 100
    answer.update({
        'designWh': round(design_total / 1000, 1),
        'fullWh': round(full_total / 1000, 1),
        'healthPct': round(health, 1),
        'wearPct': round(max(0.0, 100.0 - health), 1),
        'cycles': cycle_values[0] if len(cycle_values) == 1 else None,
    })
    return answer


def _xml_local(tag):
    """Extrae un nombre XML independientemente del namespace de Windows."""
    return str(tag).rsplit('}', 1)[-1].lower()


def _xml_field(battery, names):
    expected = {name.lower() for name in names}
    for child in battery:
        if _xml_local(child.tag) in expected:
            return (child.text or '').strip()
    return None


def parse_battery_report_xml(source):
    """Lee *solo* el inventario Batteries/Battery del XML powercfg.

    No mezcla capacidades de diferentes baterías ni utiliza el historial de
    porcentajes como capacidad de diseño. El ciclo 0 es válido si se reporta.
    """
    answer = {'batteryFound': False, 'count': 0,
              'designWh': None, 'fullWh': None, 'healthPct': None,
              'wearPct': None, 'cycles': None, 'model': None,
              'manufacturer': None, 'source': 'powercfg /batteryreport /xml'}
    try:
        root = ET.fromstring(source)
    except (ET.ParseError, TypeError, ValueError):
        return dict(answer, error='El informe XML de batería no es válido.')
    batteries = []
    for parent in root.iter():
        if _xml_local(parent.tag) in ('batteries', 'installedbatteries'):
            batteries.extend(child for child in parent if _xml_local(child.tag) == 'battery')
    if not batteries:
        return answer
    answer['batteryFound'] = True
    answer['count'] = len(batteries)
    if len(batteries) == 1:
        answer['model'] = _xml_field(batteries[0], ('Name', 'DeviceName', 'BatteryName')) or None
        answer['manufacturer'] = _xml_field(batteries[0], ('Manufacturer',)) or None
    designs = []
    fulls = []
    cycle_values = []
    valid_capacities = True
    for battery in batteries:
        d = _number(_xml_field(battery, ('DesignCapacity', 'DesignedCapacity')), 1000, 2000000)
        f = _number(_xml_field(battery, ('FullChargeCapacity', 'FullChargedCapacity')), 1000, 2000000)
        cycle = _number(_xml_field(battery, ('CycleCount',)), 0, 20000)
        # A value outside plausible ranges may mean unknown sentinel rather
        # than real health. Never present that value as a measurement.
        if d is None or f is None or f > 1.25*d:
            valid_capacities = False
        elif valid_capacities:
            designs.append(d)
            fulls.append(f)
        cycle_values.append(int(cycle) if cycle is not None else None)
    if valid_capacities and len(designs) == len(batteries) == len(fulls):
        total_design = sum(designs)
        total_full = sum(fulls)
        h = round(total_full / total_design * 100, 1)
        answer.update(designWh=round(total_design/1000, 1),
                      fullWh=round(total_full/1000, 1), healthPct=h,
                      wearPct=round(max(0.0, 100-h), 1))
    # A cycle total is not the sum of each independent battery's cycles.
    if len(batteries) == 1 and cycle_values[0] is not None:
        answer['cycles'] = cycle_values[0]
    return answer


def read_battery_report():
    """Consulta powercfg con ruta única y elimina el XML en todos los casos."""
    if os.name != 'nt':
        return {'error': 'Informe de batería solo disponible en Windows.'}
    exe = shutil.which('powercfg.exe') or shutil.which('powercfg')
    if not exe:
        return {'error': 'Windows no encuentra powercfg.exe.'}
    output = Path(tempfile.gettempdir()) / f'corepulse_battery_{os.getpid()}_{uuid.uuid4().hex}.xml'
    try:
        result = subprocess.run(
            [exe, '/batteryreport', '/xml', '/output', str(output)],
            capture_output=True, text=True, encoding='utf-8', errors='replace',
            timeout=25, check=False,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
        if result.returncode != 0 or not output.is_file():
            return {'error': 'Windows no pudo generar el informe de batería.'}
        # Cap the memory read: battery reports normally occupy a few KiB.
        if output.stat().st_size > 4_000_000:
            return {'error': 'Informe de batería demasiado grande para procesar.'}
        return parse_battery_report_xml(output.read_bytes())
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return {'error': 'Windows no entregó el informe de batería.'}
    finally:
        try:
            output.unlink(missing_ok=True)
        except OSError:
            pass


def merge_battery_sources(cim, report):
    """Prioriza CIM; adopta pares completos del informe, nunca pares cruzados."""
    cim = dict(cim or {})
    report = dict(report or {})
    answer = dict(cim)
    for label in ('batteryFound', 'count', 'model', 'manufacturer'):
        if not answer.get(label) and report.get(label):
            answer[label] = report[label]
    if (cim.get('healthPct') is None and report.get('healthPct') is not None
            and (not cim.get('count') or cim.get('count') == report.get('count'))):
        # These capacities describe a *complete set* in the XML report.
        for label in ('designWh', 'fullWh', 'healthPct', 'wearPct'):
            answer[label] = report[label]
        answer['source'] = 'powercfg /batteryreport /xml'
    elif cim.get('healthPct') is not None:
        answer['source'] = 'Windows CIM / WMI'
    else:
        answer['source'] = None
    # Cycle counts can be transferred only if both inventories uniquely
    # represent a single battery, not from a different pack in a mixed system.
    if answer.get('cycles') is None and report.get('cycles') is not None:
        if report.get('count') == 1 and int(cim.get('count') or 0) <= 1:
            answer['cycles'] = report['cycles']
            answer['cyclesSource'] = 'powercfg /batteryreport /xml'
    if not answer.get('source') and not answer.get('error'):
        answer['error'] = 'Windows no proporciona capacidades verificables mediante CIM ni powercfg.'
    elif answer.get('source'):
        answer.pop('error', None)
    if not answer.get('source') and report.get('error'):
        answer['error'] = report['error']
    return answer


def read_windows_battery_specs():
    """Dos fuentes de lectura. Consultas en hilo y con límite de tiempo."""
    if os.name != 'nt':
        return {'error': 'Solo disponible en Windows.'}
    exe = shutil.which('powershell.exe') or shutil.which('powershell')
    result = {}
    if exe:
        try:
            run = subprocess.run(
                [exe, '-NoLogo', '-NoProfile', '-NonInteractive', '-Command', _BATTERY_CIM_SCRIPT],
                capture_output=True, text=True, encoding='utf-8', errors='replace',
                timeout=16, check=False,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            )
            if run.returncode == 0 and run.stdout.strip():
                payload = json.loads(run.stdout.lstrip('\ufeff').strip())
                result = parse_battery_specs(payload)
                result['source'] = 'Windows CIM / WMI'
            else:
                result = {'error': 'Windows no pudo consultar CIM de batería.'}
        except (OSError, subprocess.TimeoutExpired, ValueError, TypeError):
            result = {'error': 'Windows no entregó datos CIM válidos.'}
    else:
        result = {'error': 'PowerShell no disponible para consultar CIM.'}
    if result.get('healthPct') is not None and result.get('cycles') is not None:
        return result
    return merge_battery_sources(result, read_battery_report())


# Medición alternativa de descarga instantánea; nunca asignar un tiempo
# calculado a partir de tasas que no corresponden al mismo dispositivo.
_DISCHARGE_CIM_SCRIPT = r'''
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$rows = @(Get-CimInstance -Namespace 'root/wmi' -ClassName 'BatteryStatus' -ErrorAction Stop |
    Select-Object InstanceName, RemainingCapacity, DischargeRate, Discharging)
ConvertTo-Json -InputObject $rows -Depth 4 -Compress
'''.strip()


def estimate_runtime_from_rate(payload):
    """Segundos estimados usando mWh/mW reales (BatteryStatus, misma batería).

    Para varios packs exige que TODOS indiquen descarga y ambas medidas;
    no se mezcla la capacidad de uno con el consumo de otro.
    """
    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list) or not payload:
        return None
    remaining_sum, rate_sum = 0.0, 0.0
    keys = set()
    for entry in payload:
        if not isinstance(entry, dict) or entry.get('Discharging') is not True:
            return None
        key = str(entry.get('InstanceName') or '').strip().casefold()
        if not key or key in keys:
            return None
        keys.add(key)
        remaining = _number(entry.get('RemainingCapacity'), 100, 2_000_000)
        rate = _number(entry.get('DischargeRate'), 100, 250_000)
        if remaining is None or rate is None:
            return None
        remaining_sum += remaining
        rate_sum += rate
    seconds = remaining_sum * 3600 / rate_sum
    return int(seconds) if math.isfinite(seconds) and 60 <= seconds <= 604800 else None


def read_discharge_runtime():
    """No modifica energía; usa WMI en worker, nunca en el hilo de Qt."""
    if os.name != 'nt':
        return None
    exe = shutil.which('powershell.exe') or shutil.which('powershell')
    if not exe:
        return None
    try:
        run = subprocess.run(
            [exe, '-NoLogo', '-NoProfile', '-NonInteractive', '-Command', _DISCHARGE_CIM_SCRIPT],
            capture_output=True, text=True, encoding='utf-8', errors='replace',
            timeout=9, check=False,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
        if run.returncode != 0 or not run.stdout.strip():
            return None
        return estimate_runtime_from_rate(json.loads(run.stdout.lstrip('\ufeff').strip()))
    except (OSError, ValueError, TypeError, subprocess.TimeoutExpired):
        return None


def estimate_runtime_from_samples(samples):
    """Estimación etiquetada basada en una caída real >= 1 % en >= 5 min."""
    if not isinstance(samples, list) or len(samples) < 2:
        return None
    start_time, start_pct = samples[0]
    stop_time, stop_pct = samples[-1]
    elapsed = stop_time - start_time
    drop = start_pct - stop_pct
    if elapsed < 300 or drop < 1 or stop_pct <= 0:
        return None
    seconds = stop_pct * elapsed / drop
    return int(seconds) if math.isfinite(seconds) and 60 <= seconds <= 604800 else None


def read_charge_state():
    """Porcentaje/corriente nativos obtenidos de Windows mediante psutil."""
    try:
        raw = psutil.sensors_battery()
    except (OSError, RuntimeError, AttributeError):
        return None
    if raw is None:
        return None
    percent = _number(getattr(raw, 'percent', None), 0, 100)
    plugged = getattr(raw, 'power_plugged', None)
    seconds = _number(getattr(raw, 'secsleft', None), 1, 604800)
    return {
        'percent': round(percent, 1) if percent is not None else None,
        'plugged': plugged if isinstance(plugged, bool) else None,
        'seconds': int(seconds) if seconds is not None and plugged is False else None,
    }


def format_duration(seconds):
    if not isinstance(seconds, int) or seconds < 60 or seconds > 604800:
        return 'N/A'
    hours, minutes = divmod(seconds // 60, 60)
    return f'{hours} h {minutes:02d} min' if hours else f'{minutes} min'


class BatteryHealth(QObject):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='corepulse-battery')
        self._future: Future | None = None
        self._last_specs_time = time.monotonic()
        self._specs = {}
        self._closed = False
        self._runtime_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='corepulse-autonomy')
        self._runtime_future: Future | None = None
        self._runtime_last_started = -1e9
        self._runtime_estimate = None
        self._runtime_timestamp = -1e9
        self._runtime_session = 0
        self._pending_runtime_session = None
        self._last_plugged = None
        self._samples = []
        self._data = {
            'hasBattery': False, 'chargePct': None, 'chargeText': 'N/A',
            'powerState': 'Consultando Windows…', 'remaining': 'N/A', 'remainingSource': '',
            'healthPct': None, 'healthText': 'N/A', 'healthLabel': 'No disponible',
            'wearText': 'N/A', 'designText': 'N/A', 'fullText': 'N/A',
            'cyclesText': 'N/A', 'model': 'N/A', 'manufacturer': 'N/A',
            'count': 0, 'source': 'Windows (psutil / WMI)', 'details': '',
            'busy': True, 'lastUpdate': 'N/A',
        }
        self._timer = QTimer(self)
        self._timer.setInterval(3000)
        self._timer.timeout.connect(self._tick)
        self._timer.start()
        self._tick()
        self.refresh()

    @Property('QVariantMap', notify=changed)
    def data(self):
        return self._data

    def _tick(self):
        if self._closed:
            return
        state = read_charge_state()
        next_data = dict(self._data)
        next_data['hasBattery'] = state is not None or bool(self._specs.get('batteryFound'))
        now = time.monotonic()
        plugged_now = state.get('plugged') if state else None
        if isinstance(plugged_now, bool) and plugged_now != self._last_plugged:
            # Nueva sesión: no reciclar la tasa medida antes de enchufar o quitar CA.
            self._runtime_session += 1
            self._runtime_estimate = None
            self._runtime_last_started = -1e9
            self._samples.clear()
        self._last_plugged = plugged_now
        if self._runtime_future is not None and self._runtime_future.done():
            try:
                measured = self._runtime_future.result()
            except Exception:
                measured = None
            if self._pending_runtime_session == self._runtime_session:
                self._runtime_estimate = measured
                self._runtime_timestamp = now
            self._runtime_future = None
        if state is None:
            next_data.update(chargePct=None, chargeText='N/A', remaining='N/A',
                             powerState='Batería detectada; carga N/A' if next_data['hasBattery'] else 'Sin batería detectada',
                             remainingSource='')
        else:
            pct = state['percent']
            plugged = state['plugged']
            runtime_seconds = state['seconds']
            runtime_source = 'Windows (autonomía actual)' if runtime_seconds is not None else ''
            if plugged is False:
                if pct is not None:
                    self._samples.append((now, pct))
                    # Solo ventana reciente; descarta lecturas antes de reconectar.
                    self._samples = [(t, p) for t, p in self._samples if now - t <= 1800]
                if runtime_seconds is None and self._runtime_estimate is not None and now - self._runtime_timestamp < 95:
                    runtime_seconds = self._runtime_estimate
                    runtime_source = 'Estimación según descarga actual (Windows WMI)'
                if runtime_seconds is None:
                    runtime_seconds = estimate_runtime_from_samples(self._samples)
                    if runtime_seconds is not None:
                        runtime_source = 'Estimación según descarga observada'
                if self._runtime_future is None and now - self._runtime_last_started >= 25:
                    self._runtime_last_started = now
                    self._pending_runtime_session = self._runtime_session
                    self._runtime_future = self._runtime_executor.submit(read_discharge_runtime)
                if runtime_seconds is None:
                    runtime_source = 'Calculando…' if now - self._runtime_last_started <= 35 or len(self._samples) < 2 else 'Windows no informa autonomía ni consumo'
            else:
                self._samples.clear()
                self._runtime_estimate = None
                runtime_source = ''
            next_data.update(
                chargePct=pct, chargeText=f'{pct:g} %' if pct is not None else 'N/A',
                powerState='Conectado a corriente' if plugged is True else
                           ('Funcionando con batería' if plugged is False else 'Fuente de energía N/A'),
                remaining=('Conectado a corriente' if plugged is True else
                           (format_duration(runtime_seconds) if runtime_seconds is not None else
                            ('Calculando…' if runtime_source == 'Calculando…' else 'N/A'))),
                remainingSource=runtime_source,
            )
        if self._future is not None and self._future.done():
            try:
                self._specs = self._future.result()
            except Exception:
                self._specs = {'error': 'Falló la consulta de capacidades.'}
            self._future = None
            next_data['hasBattery'] = state is not None or bool(self._specs.get('batteryFound'))
            next_data.update(self._spec_fields())
        # Las capacidades no cambian rápidamente; actualizar cada 10 min.
        if self._future is None and time.monotonic() - self._last_specs_time >= 600:
            self._last_specs_time = time.monotonic()
            self._future = self._executor.submit(read_windows_battery_specs)
        next_data['busy'] = self._future is not None
        next_data['lastUpdate'] = datetime.now().strftime('%H:%M:%S')
        if next_data != self._data:
            self._data = next_data
            self.changed.emit()

    def _spec_fields(self):
        specs = self._specs
        health = specs.get('healthPct')
        if health is None:
            label = 'No disponible'
        elif health >= 85:
            label = 'Buen estado'
        elif health >= 70:
            label = 'Desgaste moderado'
        else:
            label = 'Desgaste elevado'
        def wh(value):
            return f'{value:.1f} Wh' if isinstance(value, (int, float)) else 'N/A'
        return {
            'healthPct': health,
            'healthText': f'{health:.1f} %' if health is not None else 'N/A',
            'healthLabel': label,
            'wearText': f"{specs['wearPct']:.1f} %" if specs.get('wearPct') is not None else 'N/A',
            'designText': wh(specs.get('designWh')),
            'fullText': wh(specs.get('fullWh')),
            'cyclesText': str(specs['cycles']) if specs.get('cycles') is not None else 'N/A',
            'model': specs.get('model') or 'N/A',
            'manufacturer': specs.get('manufacturer') or 'N/A',
            'count': int(specs.get('count') or 0),
            'details': specs.get('error') or (
                'Windows no informa capacidades comprobables; N/A significa dato ausente.'
                if specs.get('healthPct') is None else
                ('Fuente: ' + (specs.get('source') or 'Windows') + '. Salud = capacidad plena / capacidad de diseño; no es una prueba física.')
            ),
        }

    @Slot()
    def refresh(self):
        if self._closed:
            return
        self._tick()
        if self._future is None:
            # Consulta bajo demanda; además se renueva cada diez minutos.
            self._last_specs_time = time.monotonic()
            self._future = self._executor.submit(read_windows_battery_specs)
            next_data = dict(self._data)
            next_data['busy'] = True
            self._data = next_data
            self.changed.emit()

    @Slot()
    def close(self):
        self._closed = True
        self._timer.stop()
        self._executor.shutdown(wait=False, cancel_futures=True)
        self._runtime_executor.shutdown(wait=False, cancel_futures=True)
