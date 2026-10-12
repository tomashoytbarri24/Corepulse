"""Centro de Salud / Almacenamiento: volúmenes reales y estado del hardware.

No deduce la salud de la ocupación, ni relaciona volúmenes con unidades físicas
sin identificadores comprobables. Windows puede omitir la salud del dispositivo.
Solo lectura. No ejecuta reparaciones ni escribe en el disco.
"""
from __future__ import annotations
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime
import ctypes
import json
import math
import os
import re
import shutil
import subprocess
import time

import psutil
from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot


_PHYSICAL_DISK_SCRIPT = r'''
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$items = @(Get-CimInstance -Namespace 'root/Microsoft/Windows/Storage' -ClassName 'MSFT_PhysicalDisk' -ErrorAction Stop |
    Select-Object FriendlyName, HealthStatus, OperationalStatus, MediaType, Size)
ConvertTo-Json -InputObject $items -Depth 5 -Compress
'''.strip()


def _capacity(value):
    if isinstance(value, bool):
        return None
    try:
        v = float(value)
    except (ValueError, TypeError, OverflowError):
        return None
    return v if math.isfinite(v) and v > 0 else None


def format_gib(value):
    if isinstance(value, bool):
        return 'N/A'
    try:
        val = float(value)
    except (ValueError, TypeError, OverflowError):
        return 'N/A'
    return f'{val / 1024**3:.1f} GB' if math.isfinite(val) and val >= 0 else 'N/A'


def read_fixed_volumes():
    """Uso del sistema de archivos; excluye particiones de red/removibles."""
    if os.name != 'nt':
        return []
    result = []
    visited = set()
    for part in psutil.disk_partitions(all=False):
        mount = str(part.mountpoint or '')
        if not re.fullmatch(r'[A-Za-z]:\\', mount) or mount.upper() in visited:
            continue
        visited.add(mount.upper())
        try:
            # GetDriveTypeW: 3 = fixed; evita mostrar pendrives y unidades de red.
            if ctypes.windll.kernel32.GetDriveTypeW(mount) != 3:
                continue
            usage = psutil.disk_usage(mount)
        except (OSError, PermissionError, AttributeError):
            continue
        total = _capacity(getattr(usage, 'total', None))
        free = getattr(usage, 'free', None)
        if total is None or not isinstance(free, (int, float)) or free < 0 or free > total:
            continue
        used = total - free
        result.append({'mount': mount, 'total': format_gib(total),
                       'used': format_gib(used), 'free': format_gib(free),
                       'usedPct': round(used * 100 / total, 1)})
    return result


def parse_physical_disks(payload):
    """Estados reportados por MSFT_PhysicalDisk; Unknown != Healthy."""
    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list):
        return []
    mapped_health = {0: 'Correcto', 1: 'Advertencia', 2: 'Crítico', 5: 'N/A'}
    mapped_type = {3: 'HDD', 4: 'SSD', 5: 'SCM'}
    result = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        name = str(item.get('FriendlyName') or '').strip()
        if not name:
            continue
        try:
            status = int(item.get('HealthStatus'))
        except (ValueError, TypeError, OverflowError):
            status = 5
        try:
            kind = int(item.get('MediaType'))
        except (ValueError, TypeError, OverflowError):
            kind = 0
        result.append({'name': name[:100], 'health': mapped_health.get(status, 'N/A'),
                       'media': mapped_type.get(kind, 'N/A'),
                       'capacity': format_gib(item.get('Size')),
                       'healthKnown': status in (0, 1, 2)})
    return result


def read_physical_disks():
    if os.name != 'nt':
        return []
    exe = shutil.which('powershell.exe') or shutil.which('powershell')
    if not exe:
        return []
    try:
        r = subprocess.run([exe, '-NoLogo', '-NoProfile', '-NonInteractive', '-Command',
                            _PHYSICAL_DISK_SCRIPT], capture_output=True, text=True,
                           encoding='utf-8', errors='replace', timeout=18, check=False,
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        return parse_physical_disks(json.loads(r.stdout.lstrip('\ufeff').strip())) if r.returncode == 0 and r.stdout.strip() else []
    except (OSError, ValueError, TypeError, subprocess.TimeoutExpired):
        return []


class StorageHealth(QObject):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._closed = False
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='corepulse-storage')
        self._future: Future | None = None
        self._last_disks = -1e9
        self._physical = []
        self._data = {'volumes': [], 'physical': [], 'busy': True, 'lastUpdate': 'N/A'}
        self._timer = QTimer(self)
        self._timer.setInterval(12000)
        self._timer.timeout.connect(self._tick)
        self._timer.start()
        self.refresh()

    @Property('QVariantMap', notify=changed)
    def data(self):
        return self._data

    def _tick(self):
        if self._closed:
            return
        now = time.monotonic()
        if self._future is not None and self._future.done():
            try:
                self._physical = self._future.result()
            except Exception:
                self._physical = []
            self._future = None
        if self._future is None and now - self._last_disks >= 600:
            self._last_disks = now
            self._future = self._executor.submit(read_physical_disks)
        next_data = {'volumes': read_fixed_volumes(), 'physical': self._physical,
                     'busy': self._future is not None,
                     'lastUpdate': datetime.now().strftime('%H:%M:%S')}
        if next_data != self._data:
            self._data = next_data
            self.changed.emit()

    @Slot()
    def refresh(self):
        if self._closed:
            return
        self._last_disks = -1e9
        self._tick()

    @Slot()
    def close(self):
        self._closed = True
        self._timer.stop()
        self._executor.shutdown(wait=False, cancel_futures=True)
