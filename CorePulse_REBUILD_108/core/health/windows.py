"""Centro de Salud / Análisis de Windows.

Inventario de SOLO LECTURA, inspirado en los analizadores de V485.
No altera servicios, drivers, entradas de inicio ni registro de eventos.
No confunde ausencia de datos con un sistema sano.
"""
from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime
import json
import os
import shutil
import subprocess

from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot


# Cada fuente se consulta independientemente: el fallo de una no borra las otras.
# Solo se extraen identificadores y estados, nunca líneas de comandos ni mensajes
# privados del Visor de eventos. No se requiere elevación ni ExecutionPolicy Bypass.
_WINDOWS_QUERIES = {
    "startup": r"""
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=[System.Text.Encoding]::UTF8
try {
  $a = @(Get-CimInstance -ClassName Win32_StartupCommand -ErrorAction Stop)
  $r = @{available=$true; count=$a.Count; items=@($a | Select-Object -First 12 Name,Location,User)}
} catch { $r = @{available=$false; count=$null; items=@()} }
ConvertTo-Json -InputObject $r -Depth 6 -Compress
""".strip(),
    "services": r"""
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=[System.Text.Encoding]::UTF8
try {
  $s = @(Get-CimInstance -ClassName Win32_Service -ErrorAction Stop)
  $running = @($s | Where-Object {$_.State -eq 'Running'})
  $stoppedAuto = @($s | Where-Object {$_.StartMode -eq 'Auto' -and $_.State -ne 'Running'})
  $r = @{available=$true; total=$s.Count; running=$running.Count; autoStopped=$stoppedAuto.Count; items=@($stoppedAuto | Select-Object -First 10 Name,DisplayName,State)}
} catch { $r = @{available=$false; total=$null; running=$null; autoStopped=$null; items=@()} }
ConvertTo-Json -InputObject $r -Depth 6 -Compress
""".strip(),
    "events": r"""
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=[System.Text.Encoding]::UTF8
try {
  $since = (Get-Date).AddDays(-7)
  $events = @(Get-WinEvent -FilterHashtable @{LogName=@('System','Application'); Level=@(1,2); StartTime=$since} -MaxEvents 80 -ErrorAction Stop)
  $r = @{available=$true; count=$events.Count; capped=($events.Count -eq 80); items=@($events | Select-Object -First 8 @{N='Source';E={$_.ProviderName}},Id,LevelDisplayName,@{N='When';E={$_.TimeCreated.ToString('yyyy-MM-dd HH:mm')}})}
} catch {
  if ($_.FullyQualifiedErrorId -match 'NoMatchingEventsFound') {
    $r = @{available=$true; count=0; capped=$false; items=@()}
  } else { $r = @{available=$false; count=$null; capped=$false; items=@()} }
}
ConvertTo-Json -InputObject $r -Depth 6 -Compress
""".strip(),
    "drivers": r"""
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=[System.Text.Encoding]::UTF8
try {
  $dev = @(Get-CimInstance -ClassName Win32_PnPEntity -ErrorAction Stop)
  $problems = @($dev | Where-Object {$null -ne $_.ConfigManagerErrorCode -and [int]$_.ConfigManagerErrorCode -ne 0})
  $r = @{available=$true; total=$dev.Count; problems=$problems.Count; items=@($problems | Select-Object -First 12 Name,ConfigManagerErrorCode)}
} catch { $r = @{available=$false; total=$null; problems=$null; items=@()} }
ConvertTo-Json -InputObject $r -Depth 6 -Compress
""".strip(),
}

_WINDOWS_ORDER = [("startup", "Consultando inicio de Windows…"),
                  ("services", "Revisando servicios del sistema…"),
                  ("events", "Leyendo eventos críticos y errores…"),
                  ("drivers", "Comprobando controladores y dispositivos…")]


def _powershell_json(script, timeout=45):
    if os.name != 'nt':
        return None
    exe = shutil.which('powershell.exe') or shutil.which('powershell')
    if not exe:
        return None
    try:
        proc = subprocess.run(
            [exe, '-NoLogo', '-NoProfile', '-NonInteractive', '-Command', script],
            capture_output=True, text=True, encoding='utf-8', errors='replace',
            timeout=timeout, check=False,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return None
        return json.loads(proc.stdout.lstrip('\ufeff').strip())
    except (OSError, ValueError, TypeError, subprocess.TimeoutExpired):
        return None

def _int_count(value):
    if isinstance(value, bool):
        return None
    try:
        n = int(value)
    except (ValueError, TypeError, OverflowError):
        return None
    return n if 0 <= n <= 1000000 else None


def _short(value, limit=95):
    if value is None:
        return 'N/A'
    cleaned = ''.join(c if c.isprintable() else ' ' for c in str(value)).strip()
    return cleaned[:limit] if cleaned else 'N/A'


def _items(value):
    return value if isinstance(value, list) else ([value] if isinstance(value, dict) else [])


def _empty_section():
    return {'available': False, 'metric': 'N/A', 'caption': 'No disponible', 'items': []}


def parse_windows_report(raw):
    """Transforma datos CIM de Windows a objetos UI; no genera cifras estimadas."""
    result = {k: _empty_section() for k in ('startup', 'services', 'events', 'drivers')}
    if not isinstance(raw, dict):
        return result

    v = raw.get('startup')
    if isinstance(v, dict) and v.get('available') is True:
        n = _int_count(v.get('count'))
        if n is not None:
            result['startup'] = {
                'available': True, 'metric': str(n), 'caption': 'Entradas registradas de inicio',
                'items': [{'primary': _short(x.get('Name')),
                           'secondary': _short(x.get('Location'))}
                          for x in _items(v.get('items'))[:12] if isinstance(x, dict)],
            }

    v = raw.get('services')
    if isinstance(v, dict) and v.get('available') is True:
        total = _int_count(v.get('total'))
        running = _int_count(v.get('running'))
        stopped = _int_count(v.get('autoStopped'))
        if None not in (total, running, stopped) and running <= total and stopped <= total:
            result['services'] = {
                'available': True, 'metric': str(stopped),
                'caption': f'{running} de {total} servicios en ejecución · Automáticos detenidos (no siempre es error)',
                'items': [{'primary': _short(x.get('DisplayName') or x.get('Name')),
                           'secondary': _short(x.get('Name'))}
                          for x in _items(v.get('items'))[:10] if isinstance(x, dict)],
            }

    v = raw.get('events')
    if isinstance(v, dict) and v.get('available') is True:
        n = _int_count(v.get('count'))
        if n is not None:
            result['events'] = {
                'available': True, 'metric': f'{n}+' if v.get('capped') is True else str(n),
                'caption': 'Eventos críticos y errores · últimos 7 días · hasta 80 registros',
                'items': [{'primary': _short(x.get('Source')) + ' · ID ' + _short(x.get('Id'), 8),
                           'secondary': _short(x.get('When')) + ' · ' + _short(x.get('LevelDisplayName'))}
                          for x in _items(v.get('items'))[:8] if isinstance(x, dict)],
            }

    v = raw.get('drivers')
    if isinstance(v, dict) and v.get('available') is True:
        total = _int_count(v.get('total'))
        problems = _int_count(v.get('problems'))
        if None not in (total, problems) and problems <= total:
            result['drivers'] = {
                'available': True, 'metric': str(problems),
                'caption': f'{total} dispositivos enumerados · códigos PnP diferentes de cero',
                'items': [{'primary': _short(x.get('Name')),
                           'secondary': 'Código de dispositivo: ' + _short(x.get('ConfigManagerErrorCode'), 5)}
                          for x in _items(v.get('items'))[:12] if isinstance(x, dict)],
            }
    return result


def read_windows_report(on_progress=None):
    if os.name != 'nt':
        return None
    report = {}
    total = len(_WINDOWS_ORDER)
    for index, (key, label) in enumerate(_WINDOWS_ORDER, start=1):
        if on_progress:
            on_progress(max(1, int(((index - 1) / total) * 100)), label)
        report[key] = _powershell_json(_WINDOWS_QUERIES[key])
        if on_progress:
            on_progress(int((index / total) * 100), label)
    return report


class WindowsHealth(QObject):
    changed = Signal()
    progress = Signal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._closed = False
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='corepulse-windows-health')
        self._future: Future | None = None
        self._data = {'busy': False, 'lastUpdate': 'N/A', 'progress': 0, 'stage': 'Sin comprobaciones ejecutadas.',
                      **parse_windows_report(None)}
        self._poll = QTimer(self)
        self._poll.setInterval(350)
        self._poll.timeout.connect(self._check)
        self._auto = QTimer(self)
        self._auto.setInterval(300000)  # nada de consultas WMI repetidas cada segundo
        self._auto.timeout.connect(self.refresh)
        self.progress.connect(self._set_progress)
        # Consulta diferida hasta abrir la pestaña: no se sondea WMI en el inicio de CorePulse.

    @Property('QVariantMap', notify=changed)
    def data(self):
        return self._data

    @Slot(int, str)
    def _set_progress(self, value, label):
        if not self._closed and self._future is not None:
            self._data = {**self._data, 'progress': max(0, min(100, int(value))), 'stage': str(label or 'Analizando…')}
            self.changed.emit()

    @Slot()
    def refresh(self):
        if self._closed or self._future is not None:
            return
        if not self._auto.isActive():
            self._auto.start()
        self._data = {**self._data, 'busy': True, 'progress': 4, 'stage': 'Preparando análisis de Windows…'}
        self.changed.emit()
        self._future = self._executor.submit(read_windows_report, self.progress.emit)
        self._poll.start()

    def _check(self):
        if self._closed or self._future is None or not self._future.done():
            return
        try:
            report = self._future.result()
        except Exception:
            report = None
        self._future = None
        self._poll.stop()
        self._data = {'busy': False, 'lastUpdate': datetime.now().strftime('%H:%M:%S'), 'progress': 100, 'stage': 'Análisis completado.',
                      **parse_windows_report(report)}
        self.changed.emit()

    @Slot()
    def close(self):
        self._closed = True
        self._poll.stop()
        self._auto.stop()
        self._executor.shutdown(wait=False, cancel_futures=True)
