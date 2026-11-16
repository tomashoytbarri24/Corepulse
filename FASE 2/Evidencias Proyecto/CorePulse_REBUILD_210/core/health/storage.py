"""Centro de Salud / Almacenamiento: volúmenes reales y estado del hardware.

No deduce la salud de la ocupación, ni relaciona volúmenes con unidades físicas
sin identificadores comprobables. Windows puede omitir la salud del dispositivo.
Solo lectura. No ejecuta reparaciones ni escribe en el disco.
"""
from __future__ import annotations
from concurrent.futures import Future
from concurrent.futures.thread import ThreadPoolExecutor
from datetime import datetime
import ctypes
import json
import math
import os
import re
import shutil
import struct
from ctypes import wintypes
import subprocess
import time

import psutil
from PySide6.QtCore import QObject, Property, QSettings, QTimer, Signal, Slot


_PHYSICAL_DISK_SCRIPT = r'''
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$disks = @(Get-Disk -ErrorAction Stop)
$physical = @(Get-PhysicalDisk -ErrorAction Stop | ForEach-Object {
    $p = $_
    $disk = $null
    try {
        $disk = $disks | Where-Object {
            ($p.UniqueId -and $_.UniqueId -and $_.UniqueId -eq $p.UniqueId) -or
            ($p.SerialNumber -and $_.SerialNumber -and $_.SerialNumber.Trim() -eq $p.SerialNumber.Trim())
        } | Select-Object -First 1
    } catch {}
    [pscustomobject]@{
        DeviceId = [string]$p.DeviceId
        DiskNumber = if ($null -ne $disk) { [int]$disk.Number } else { $null }
        FriendlyName = $p.FriendlyName
        HealthStatus = $p.HealthStatus
        OperationalStatus = ($p.OperationalStatus -join ', ')
        MediaType = $p.MediaType
        Size = $p.Size
        SerialNumber = $p.SerialNumber
        FirmwareVersion = $p.FirmwareVersion
        BusType = if ($null -ne $disk) { $disk.BusType } else { $p.BusType }
    }
})
$partitions = @(Get-Partition -ErrorAction SilentlyContinue | Where-Object { $_.DriveLetter } | ForEach-Object {
    [pscustomobject]@{ Mount = ([string]$_.DriveLetter + ':\'); DiskNumber = [int]$_.DiskNumber }
})
ConvertTo-Json -InputObject @{ physical = $physical; partitions = $partitions } -Depth 6 -Compress
'''.strip()

_PHYSICAL_DISK_SCRIPT = r'''
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$physical = @(Get-PhysicalDisk -ErrorAction Stop | ForEach-Object {
    $p = $_
    $counter = $null
    try { $counter = $p | Get-StorageReliabilityCounter -ErrorAction Stop } catch {}
    $disk = $null
    try {
        $disk = Get-Disk -ErrorAction Stop | Where-Object {
            ($p.UniqueId -and $_.UniqueId -and $_.UniqueId -eq $p.UniqueId) -or
            ($p.SerialNumber -and $_.SerialNumber -and $_.SerialNumber.Trim() -eq $p.SerialNumber.Trim())
        } | Select-Object -First 1
    } catch {}
    [pscustomobject]@{
        DeviceId = [string]$p.DeviceId
        DiskNumber = if ($null -ne $disk) { [int]$disk.Number } else { $null }
        FriendlyName = $p.FriendlyName
        HealthStatus = $p.HealthStatus
        OperationalStatus = ($p.OperationalStatus -join ', ')
        MediaType = $p.MediaType
        Size = $p.Size
        SerialNumber = $p.SerialNumber
        FirmwareVersion = $p.FirmwareVersion
        BusType = $p.BusType
        Temperature = if ($null -ne $counter) { $counter.Temperature } else { $null }
        TemperatureMax = if ($null -ne $counter) { $counter.TemperatureMax } else { $null }
        Wear = if ($null -ne $counter) { $counter.Wear } else { $null }
        PowerOnHours = if ($null -ne $counter) { $counter.PowerOnHours } else { $null }
        PowerOnCount = if ($null -ne $counter) { $counter.PowerOnCount } else { $null }
        ReadErrorsTotal = if ($null -ne $counter) { $counter.ReadErrorsTotal } else { $null }
        ReadErrorsUncorrected = if ($null -ne $counter) { $counter.ReadErrorsUncorrected } else { $null }
        WriteErrorsTotal = if ($null -ne $counter) { $counter.WriteErrorsTotal } else { $null }
        WriteErrorsUncorrected = if ($null -ne $counter) { $counter.WriteErrorsUncorrected } else { $null }
    }
})
$partitions = @(Get-Partition -ErrorAction SilentlyContinue | Where-Object { $_.DriveLetter } | ForEach-Object {
    [pscustomobject]@{ Mount = ([string]$_.DriveLetter + ':\'); DiskNumber = [int]$_.DiskNumber }
})
ConvertTo-Json -InputObject @{ physical = $physical; partitions = $partitions } -Depth 6 -Compress
'''.strip()


def _read_nvme_health_log(disk_number):
    """Lee la página SMART/Health estándar NVMe, solo lectura; None si no está expuesta."""
    if os.name != 'nt':
        return None
    try:
        disk_number = int(disk_number)
        if disk_number < 0 or disk_number > 4096:
            return None
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        create_file = kernel.CreateFileW
        create_file.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD,
                                wintypes.HANDLE]
        create_file.restype = wintypes.HANDLE
        device_io = kernel.DeviceIoControl
        device_io.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPVOID,
                              wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD,
                              ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID]
        device_io.restype = wintypes.BOOL
        close_handle = kernel.CloseHandle
        close_handle.argtypes = [wintypes.HANDLE]
        close_handle.restype = wintypes.BOOL

        invalid = ctypes.c_void_p(-1).value
        path = rf'\\.\PhysicalDrive{disk_number}'
        handle = None
        for access in (0, 0x80000000):
            candidate = create_file(path, access, 0x1 | 0x2, None, 3, 0, None)
            candidate_value = candidate.value if isinstance(candidate, ctypes.c_void_p) else candidate
            if candidate_value not in (None, invalid, -1):
                handle = candidate_value
                break
        if handle is None:
            return None

        try:
            # STORAGE_PROPERTY_QUERY (8 bytes) followed by
            # STORAGE_PROTOCOL_SPECIFIC_DATA (40 bytes) and the 512-byte log.
            log_size = 512
            data_offset = 40
            log_offset = 8 + data_offset
            buffer_size = log_offset + log_size
            buffer = ctypes.create_string_buffer(buffer_size)
            struct.pack_into('<II10I', buffer, 0,
                             50, 0,          # StorageDeviceProtocolSpecificProperty, StandardQuery
                             3, 2, 2, 0,    # NVMe, LogPage, SMART/Health page 02h
                             data_offset, log_size, 0, 0, 0, 0)
            returned = wintypes.DWORD()
            ok = device_io(handle, 0x2D1400, ctypes.byref(buffer), 48,
                           ctypes.byref(buffer), buffer_size, ctypes.byref(returned), None)
            if not ok or returned.value < buffer_size:
                return None
            version, descriptor_size = struct.unpack_from('<II', buffer.raw, 0)
            returned_offset, returned_length = struct.unpack_from('<II', buffer.raw, 24)
            if (version < 48 or descriptor_size < 48
                    or returned_offset < data_offset or returned_length < log_size):
                return None
            actual_log_offset = 8 + returned_offset
            if actual_log_offset + log_size > returned.value:
                return None
            log = bytes(buffer.raw[actual_log_offset:actual_log_offset + log_size])
            if len(log) != 512:
                return None

            def uint128(offset):
                value = int.from_bytes(log[offset:offset + 16], 'little')
                return None if value == (1 << 128) - 1 else value

            temperature_k = int.from_bytes(log[1:3], 'little')
            temperature_c = temperature_k - 273.15
            if temperature_k in (0, 0xFFFF) or not -20 <= temperature_c <= 150:
                temperature_c = None
            else:
                temperature_c = round(temperature_c, 1)
            return {
                'temperatureC': temperature_c,
                'wearPercent': int(log[5]),
                # NVMe SMART/Health cuenta unidades de host de 1000 × 512 B;
                # no equivale a errores separados de lectura/escritura.
                'nvmeDataUnitsRead': uint128(32),
                'nvmeDataUnitsWritten': uint128(48),
                'nvmeHostReadCommands': uint128(64),
                'nvmeHostWriteCommands': uint128(80),
                'nvmeControllerBusyMinutes': uint128(96),
                'powerOnCount': uint128(112),
                'powerOnHours': uint128(128),
                'nvmeCriticalWarning': int(log[0]),
                'nvmeAvailableSparePercent': int(log[3]),
                'nvmeUnsafeShutdowns': uint128(144),
                'nvmeMediaErrors': uint128(160),
                'nvmeErrorLogEntries': uint128(176),
            }
        finally:
            close_handle(handle)
    except (OSError, ValueError, TypeError, OverflowError, AttributeError,
            ctypes.ArgumentError, struct.error):
        return None


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


def read_mounted_volumes():
    """Volúmenes locales montados, incluidos discos USB extraíbles y fijos."""
    if os.name != 'nt':
        return []
    result = []
    visited = set()
    for part in psutil.disk_partitions(all=True):
        mount = str(part.mountpoint or '')
        if not re.fullmatch(r'[A-Za-z]:\\', mount) or mount.upper() in visited:
            continue
        try:
            # 2 = extraíble, 3 = fijo. Se excluyen red, CD y unidades RAM.
            drive_type = int(ctypes.windll.kernel32.GetDriveTypeW(mount))
            if drive_type not in (2, 3):
                continue
            usage = psutil.disk_usage(mount)
        except (OSError, PermissionError, AttributeError):
            continue
        total = _capacity(getattr(usage, 'total', None))
        free = getattr(usage, 'free', None)
        if total is None or not isinstance(free, (int, float)) or free < 0 or free > total:
            continue
        visited.add(mount.upper())
        used = total - free
        label = ''
        filesystem = str(getattr(part, 'fstype', '') or '').strip()
        volume_serial = ''
        try:
            get_volume_info = ctypes.windll.kernel32.GetVolumeInformationW
            get_volume_info.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD,
                                        ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD),
                                        ctypes.POINTER(wintypes.DWORD), wintypes.LPWSTR, wintypes.DWORD]
            get_volume_info.restype = wintypes.BOOL
            label_buffer = ctypes.create_unicode_buffer(261)
            filesystem_buffer = ctypes.create_unicode_buffer(261)
            serial_number = wintypes.DWORD()
            max_component = wintypes.DWORD()
            flags = wintypes.DWORD()
            if get_volume_info(mount, label_buffer, len(label_buffer), ctypes.byref(serial_number),
                               ctypes.byref(max_component), ctypes.byref(flags),
                               filesystem_buffer, len(filesystem_buffer)):
                label = label_buffer.value.strip()
                filesystem = filesystem_buffer.value.strip() or filesystem
                volume_serial = f'{serial_number.value:08X}'
        except (OSError, AttributeError, TypeError, ctypes.ArgumentError):
            pass
        result.append({'mount': mount, 'total': format_gib(total),
                       'used': format_gib(used), 'free': format_gib(free),
                       'usedPct': round(used * 100 / total, 1),
                       'volumeLabel': label or 'Sin etiqueta',
                       'volumeSerial': volume_serial,
                       'filesystem': filesystem or 'N/A',
                       'deviceType': 'Unidad extraíble' if drive_type == 2 else 'Disco local'})
    return sorted(result, key=lambda item: str(item.get('mount') or '').upper())


def parse_physical_disks(payload):
    """Estado y contadores que Windows Storage informe; Unknown != Healthy."""
    if isinstance(payload, dict) and isinstance(payload.get('physical'), (dict, list)):
        payload = payload.get('physical')
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
        raw_status = str(item.get('HealthStatus') or '').strip().casefold()
        status_names = {'healthy': 0, 'warning': 1, 'unhealthy': 2, 'unknown': 5}
        try:
            status = int(item.get('HealthStatus'))
        except (ValueError, TypeError, OverflowError):
            status = status_names.get(raw_status, 5)
        raw_kind = str(item.get('MediaType') or '').strip().casefold()
        kind_names = {'hdd': 3, 'ssd': 4, 'scm': 5}
        try:
            kind = int(item.get('MediaType'))
        except (ValueError, TypeError, OverflowError):
            kind = kind_names.get(raw_kind, 0)
        def number(key, minimum=0, maximum=10**15):
            value = item.get(key)
            if isinstance(value, bool):
                return None
            try:
                parsed = float(value)
            except (ValueError, TypeError, OverflowError):
                return None
            return parsed if math.isfinite(parsed) and minimum <= parsed <= maximum else None

        def label(key, limit=90):
            value = item.get(key)
            return str(value).strip()[:limit] if value is not None and str(value).strip() else 'N/A'

        disk_number = number('DiskNumber', 0, 4096)
        result.append({'id': str(item.get('DeviceId') or name[:80]),
                       'diskNumber': int(disk_number) if disk_number is not None else None,
                       'name': name[:100], 'health': mapped_health.get(status, 'N/A'),
                       'media': mapped_type.get(kind, 'N/A'),
                       'capacity': format_gib(item.get('Size')),
                       'healthKnown': status in (0, 1, 2),
                       'operationalStatus': label('OperationalStatus'),
                       'serial': label('SerialNumber'), 'firmware': label('FirmwareVersion'),
                       'bus': label('BusType', 50),
                       'temperatureC': number('Temperature', -20, 150),
                       'temperatureMaxC': number('TemperatureMax', -20, 200),
                       'wearPercent': number('Wear', 0, 100),
                       'powerOnHours': number('PowerOnHours'),
                       'powerOnCount': number('PowerOnCount'),
                       'nvmeCriticalWarning': None, 'nvmeAvailableSparePercent': None,
                       'nvmeUnsafeShutdowns': None, 'nvmeMediaErrors': None,
                       'nvmeDataUnitsRead': None, 'nvmeDataUnitsWritten': None,
                       'nvmeHostReadCommands': None, 'nvmeHostWriteCommands': None,
                       'nvmeControllerBusyMinutes': None, 'nvmeErrorLogEntries': None,
                       'smartSource': 'Windows Storage',
                       'readErrorsTotal': number('ReadErrorsTotal'),
                       'readErrorsUncorrected': number('ReadErrorsUncorrected'),
                       'writeErrorsTotal': number('WriteErrorsTotal'),
                       'writeErrorsUncorrected': number('WriteErrorsUncorrected')})
    return result


def read_fast_physical_snapshot():
    """Read volume-to-disk mapping and interface directly through Windows IOCTLs."""
    if os.name != 'nt':
        return [], {}
    try:
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        handle_type = wintypes.HANDLE
        dword = wintypes.DWORD
        kernel32.CreateFileW.argtypes = [wintypes.LPCWSTR, dword, dword,
            wintypes.LPVOID, dword, dword, handle_type]
        kernel32.CreateFileW.restype = handle_type
        kernel32.DeviceIoControl.argtypes = [handle_type, dword, wintypes.LPVOID, dword,
            wintypes.LPVOID, dword, ctypes.POINTER(dword), wintypes.LPVOID]
        kernel32.DeviceIoControl.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [handle_type]
        kernel32.CloseHandle.restype = wintypes.BOOL
        kernel32.GetLogicalDrives.argtypes = []
        kernel32.GetLogicalDrives.restype = dword

        invalid_handle = ctypes.c_void_p(-1).value
        share = 0x1 | 0x2  # FILE_SHARE_READ | FILE_SHARE_WRITE
        open_existing = 3
        volume_extents_ioctl = (0x56 << 16) | (0 << 2)  # IOCTL_VOLUME_GET_VOLUME_DISK_EXTENTS
        storage_query_ioctl = (0x2D << 16) | (0x500 << 2)  # IOCTL_STORAGE_QUERY_PROPERTY

        def ioctl(path, code, input_data=b'', output_size=4096):
            handle = kernel32.CreateFileW(path, 0, share, None, open_existing, 0, None)
            if handle in (None, invalid_handle):
                return None
            try:
                output = ctypes.create_string_buffer(output_size)
                returned = dword()
                source = ctypes.create_string_buffer(input_data) if input_data else None
                ok = kernel32.DeviceIoControl(handle, code, source, len(input_data),
                    output, output_size, ctypes.byref(returned), None)
                return output.raw[:returned.value] if ok else None
            finally:
                kernel32.CloseHandle(handle)

        disk_cache = {}
        volume_map = {}
        physical = []
        logical_mask = int(kernel32.GetLogicalDrives())
        bus_names = {0:'Unknown', 1:'SCSI', 2:'ATAPI', 3:'ATA', 4:'IEEE1394',
                     5:'SSA', 6:'Fibre', 7:'USB', 8:'RAID', 9:'iSCSI',
                     10:'SAS', 11:'SATA', 12:'SD', 13:'MMC', 14:'Virtual',
                     15:'FileBackedVirtual', 16:'StorageSpaces', 17:'NVMe', 18:'SCM', 19:'UFS'}
        device_prefix = '\\\\.' + '\\'
        for index in range(26):
            if not (logical_mask & (1 << index)):
                continue
            letter = chr(ord('A') + index)
            mount = letter + ':\\'
            extents = ioctl(device_prefix + letter + ':', volume_extents_ioctl, output_size=4096)
            if not extents or len(extents) < 12:
                continue
            disk_number = struct.unpack_from('<I', extents, 8)[0]
            if disk_number not in disk_cache:
                descriptor = ioctl(device_prefix + 'PhysicalDrive' + str(disk_number), storage_query_ioctl,
                                   struct.pack('<II', 0, 0) + b'\0', output_size=4096)
                if not descriptor or len(descriptor) < 36:
                    disk_cache[disk_number] = None
                else:
                    bus_value = struct.unpack_from('<I', descriptor, 28)[0]
                    product_offset = struct.unpack_from('<I', descriptor, 16)[0]
                    vendor_offset = struct.unpack_from('<I', descriptor, 12)[0]
                    def read_c_string(offset):
                        if offset <= 0 or offset >= len(descriptor):
                            return ''
                        end = descriptor.find(b'\0', offset)
                        if end < 0:
                            end = len(descriptor)
                        return descriptor[offset:end].decode('ascii', errors='replace').strip()
                    product = read_c_string(product_offset)
                    vendor = read_c_string(vendor_offset)
                    model = product or vendor or ('Disco físico ' + str(disk_number))
                    media = 'N/A'
                    seek_query = struct.pack('<II', 7, 0) + b'\0'
                    seek = ioctl(device_prefix + 'PhysicalDrive' + str(disk_number), storage_query_ioctl,
                                 seek_query, output_size=64)
                    if seek and len(seek) >= 5:
                        media = 'HDD' if seek[4] else 'SSD'
                    disk_id = 'physical-drive-' + str(disk_number)
                    disk_cache[disk_number] = {
                        'id': disk_id, 'diskNumber': disk_number, 'name': model[:100],
                        'health': 'N/A', 'healthKnown': False, 'operationalStatus': 'N/A',
                        'media': media, 'capacity': 'N/A', 'serial': 'N/A',
                        'firmware': 'N/A', 'bus': bus_names.get(bus_value, str(bus_value)),
                        'temperatureC': None, 'temperatureMaxC': None, 'wearPercent': None,
                        'powerOnHours': None, 'powerOnCount': None,
                        'nvmeCriticalWarning': None, 'nvmeAvailableSparePercent': None,
                        'nvmeUnsafeShutdowns': None, 'nvmeMediaErrors': None,
                        'nvmeDataUnitsRead': None, 'nvmeDataUnitsWritten': None,
                        'nvmeHostReadCommands': None, 'nvmeHostWriteCommands': None,
                        'nvmeControllerBusyMinutes': None, 'nvmeErrorLogEntries': None,
                        'smartSource': 'Windows · identificación directa de bus',
                        'readErrorsTotal': None, 'readErrorsUncorrected': None,
                        'writeErrorsTotal': None, 'writeErrorsUncorrected': None,
                    }
                if disk_cache[disk_number]:
                    physical.append(disk_cache[disk_number])
            disk = disk_cache.get(disk_number)
            if disk:
                volume_map[mount.upper()] = disk['id']
        return physical, volume_map
    except (AttributeError, OSError, TypeError, ValueError, struct.error):
        return [], {}


def read_physical_snapshot(quick=False):
    if os.name != 'nt':
        return [], {}
    if quick:
        return read_fast_physical_snapshot()
    exe = shutil.which('powershell.exe') or shutil.which('powershell')
    if not exe:
        return [], {}
    try:
        r = subprocess.run([exe, '-NoLogo', '-NoProfile', '-NonInteractive', '-Command',
                            _PHYSICAL_DISK_SCRIPT], capture_output=True, text=True,
                           encoding='utf-8', errors='replace', timeout=18, check=False,
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if r.returncode != 0 or not r.stdout.strip():
            return [], {}
        payload = json.loads(r.stdout.lstrip('\ufeff').strip())
        physical = parse_physical_disks(payload)
        for disk in physical:
            if 'nvme' not in str(disk.get('bus') or '').casefold():
                continue
            number = disk.get('diskNumber')
            smart = _read_nvme_health_log(number) if isinstance(number, int) else None
            if smart:
                disk.update({key: value for key, value in smart.items() if value is not None})
                disk['smartSource'] = 'NVMe SMART directo · Windows Storage'
            else:
                disk['smartSource'] = 'Windows Storage · NVMe directo no disponible'
        raw_partitions = payload.get('partitions', []) if isinstance(payload, dict) else []
        if isinstance(raw_partitions, dict):
            raw_partitions = [raw_partitions]
        by_number = {item['diskNumber']: item['id'] for item in physical
                     if isinstance(item.get('diskNumber'), int)}
        mapping = {}
        for row in raw_partitions if isinstance(raw_partitions, list) else []:
            if not isinstance(row, dict):
                continue
            mount = str(row.get('Mount') or '').upper()
            try:
                number = int(row.get('DiskNumber'))
            except (ValueError, TypeError, OverflowError):
                continue
            if re.fullmatch(r'[A-Z]:\\', mount) and number in by_number:
                mapping[mount] = by_number[number]
        return physical, mapping
    except (OSError, ValueError, TypeError, subprocess.TimeoutExpired):
        return [], {}


def read_physical_disks():
    return read_physical_snapshot()[0]


class StorageHealth(QObject):
    changed = Signal()
    _physicalSnapshotReady = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._closed = False
        self._physicalSnapshotReady.connect(self._tick)
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='corepulse-storage')
        self._future: Future | None = None
        self._last_disks = -1e9
        self._physical = []
        self._volume_disk_map = {}
        self._observed_mounts = None
        self._physical_refresh_pending = False
        self._initial_quick_pending = True
        self._physical_details_pending = False
        self._picker_open = False
        self._volumes_ready = False
        settings = QSettings('CorePulse', 'CorePulse Rebuild')
        self._selected_mount = str(settings.value('storage/selectedMount', '') or '').upper()
        self._data = {'volumes': [], 'physical': [], 'busy': True,
                      'physicalBusy': True, 'lastUpdate': 'N/A'}
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
                physical, volume_disk_map = self._future.result()
                if not self._physical_refresh_pending:
                    self._physical, self._volume_disk_map = physical, volume_disk_map
            except Exception:
                # If the detailed SMART pass fails, keep the faster physical
                # identity already fetched so its SATA/NVMe type stays visible.
                if self._physical_refresh_pending:
                    self._physical = []
                    self._volume_disk_map = {}
            self._future = None

        volumes = read_mounted_volumes()
        mount_signature = tuple((str(item.get('mount') or '').upper(),
                                 str(item.get('deviceType') or ''),
                                 str(item.get('filesystem') or ''),
                                 str(item.get('volumeLabel') or ''),
                                 str(item.get('volumeSerial') or ''),
                                 str(item.get('total') or '')) for item in volumes)
        if self._observed_mounts is not None and mount_signature != self._observed_mounts:
            # Quita de inmediato datos físicos que podrían pertenecer a un disco
            # retirado o a otro que reutilizó su número. El volumen sigue visible.
            self._physical = []
            self._volume_disk_map = {}
            self._physical_refresh_pending = True
        self._observed_mounts = mount_signature
        self._volumes_ready = True

        if self._future is None and self._initial_quick_pending:
            # First fetch only the physical model/interface. Avoid waiting for
            # reliability counters and SMART before identifying SATA vs NVMe.
            self._initial_quick_pending = False
            self._physical_details_pending = True
            self._future = self._executor.submit(read_physical_snapshot, True)
        elif self._future is None and (self._physical_refresh_pending or self._physical_details_pending or now - self._last_disks >= 600):
            self._last_disks = now
            self._physical_refresh_pending = False
            self._physical_details_pending = False
            self._future = self._executor.submit(read_physical_snapshot)
        if self._future is not None:
            # Publish physical identity as soon as each worker completes instead
            # of waiting up to 12 s for the regular polling timer.
            self._future.add_done_callback(lambda _future: self._physicalSnapshotReady.emit())

        physical_by_id = {disk.get('id'): disk for disk in self._physical}
        for volume in volumes:
            disk_id = self._volume_disk_map.get(str(volume.get('mount') or '').upper(), '')
            disk = physical_by_id.get(disk_id, {})
            volume['physicalId'] = disk_id
            volume['physicalName'] = disk.get('name', '')
            volume['media'] = disk.get('media', 'N/A')
            bus = str(disk.get('bus') or '').strip()
            if bus and bus.casefold() != 'unknown':
                volume['bus'] = bus
                if bus.casefold() == 'usb':
                    volume['deviceType'] = 'Almacenamiento USB'
            else:
                volume['bus'] = 'N/A'
        selected = next((volume for volume in volumes if str(volume.get('mount', '')).upper() == self._selected_mount), None)
        if selected is None and volumes:
            selected = volumes[0]
            self._selected_mount = str(selected.get('mount') or '').upper()
        selected_disk = physical_by_id.get((selected or {}).get('physicalId'), {})
        next_data = {'volumes': volumes, 'physical': self._physical,
                     'selectedMount': self._selected_mount,
                     'selectedVolume': dict(selected) if selected else {},
                     'selectedPhysical': dict(selected_disk) if selected_disk else {},
                     'busy': not self._volumes_ready,
                     'physicalBusy': self._future is not None or self._physical_refresh_pending,
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

    @Slot(bool)
    def setPickerOpen(self, opened):
        if self._closed:
            return
        self._picker_open = bool(opened)
        self._timer.setInterval(900 if self._picker_open else 12000)
        self._tick()

    @Slot(str)
    def selectVolume(self, mount):
        requested = str(mount or '').strip().upper()
        if not re.fullmatch(r'[A-Z]:\\', requested):
            return
        if not any(str(volume.get('mount') or '').upper() == requested for volume in self._data.get('volumes', [])):
            return
        if self._selected_mount == requested:
            return
        self._selected_mount = requested
        QSettings('CorePulse', 'CorePulse Rebuild').setValue('storage/selectedMount', requested)
        self._tick()

    @Slot()
    def close(self):
        self._closed = True
        self._timer.stop()
        self._executor.shutdown(wait=False, cancel_futures=True)

