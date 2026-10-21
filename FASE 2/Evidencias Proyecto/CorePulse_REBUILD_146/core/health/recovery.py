"""Recuperacion de Windows: lecturas reales, restauracion solo con consentimiento.

Los resultados de comandos se transportan en JSON UTF-8 y nunca se muestran
mensajes sin procesar de PowerShell en las tarjetas. No se infiere que la
proteccion esta activa simplemente por encontrar puntos de restauracion.
"""
from __future__ import annotations

import base64
from concurrent.futures import Future
from concurrent.futures.thread import ThreadPoolExecutor
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot


# Scripts PowerShell 5.1 compatibles, sin continuaciones con barra invertida ni
# Select-Object con expresiones multilínea ambiguas.
RESTORE_POINTS_QUERY = r'''
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$result = [ordered]@{
  available = $false
  pointCount = $null
  points = @()
  protectionState = 'unknown'
  errorKind = 'none'
}
try {
  $values = @(Get-ComputerRestorePoint -ErrorAction Stop | Sort-Object -Property SequenceNumber -Descending)
  $list = @()
  foreach ($point in ($values | Select-Object -First 12)) {
    $dateText = 'N/A'
    try {
      $dateText = [Management.ManagementDateTimeConverter]::ToDateTime([string]$point.CreationTime).ToString('yyyy-MM-dd HH:mm')
    } catch {
      try { $dateText = ([datetime]$point.CreationTime).ToString('yyyy-MM-dd HH:mm') } catch {}
    }
    $list += [pscustomobject]@{
      Description = [string]$point.Description
      SequenceNumber = [int]$point.SequenceNumber
      RestorePointType = [int]$point.RestorePointType
      CreationTime = $dateText
    }
  }
  $result.available = $true
  $result.pointCount = $values.Count
  $result.points = @($list)
} catch {
  $msg = [string]$_.Exception.Message
  if ($msg -match 'access is denied|acceso denegado|privileg|administrator|administrador') {
    $result.errorKind = 'permissions'
  } elseif ($msg -match 'not supported|no se admite') {
    $result.errorKind = 'unsupported'
  } elseif ($msg -match 'disabled|deshabilitad|turned off') {
    $result.errorKind = 'disabled'
  } else {
    $result.errorKind = 'query'
  }
}
try {
  $sr = Get-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\SystemRestore' -Name DisableSR -ErrorAction Stop
  if ([int]$sr.DisableSR -eq 1) { $result.protectionState = 'disabled' }
} catch {}
ConvertTo-Json -InputObject $result -Depth 6 -Compress
'''.strip()

# Se comprueba un numero de secuencia nuevo antes de informar exito.
CREATE_POINT_SCRIPT = r'''
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$result = [ordered]@{ ok = $false; verified = $false; errorKind = 'none' }
$prior = @()
$beforeOk = $false
try {
  $prior = @(Get-ComputerRestorePoint -ErrorAction Stop | ForEach-Object { [int]$_.SequenceNumber })
  $beforeOk = $true
} catch {
  $result.errorKind = 'before_check'
}
try {
  Checkpoint-Computer -Description 'CorePulse - Manual' -RestorePointType 'MODIFY_SETTINGS' -ErrorAction Stop | Out-Null
  try {
    $after = @(Get-ComputerRestorePoint -ErrorAction Stop | ForEach-Object { [int]$_.SequenceNumber })
    $fresh = @($after | Where-Object { $_ -notin $prior })
    if ($beforeOk -and $fresh.Count -gt 0) {
      $result.ok = $true
      $result.verified = $true
    } else {
      $result.errorKind = if ($beforeOk) { 'unverified' } else { 'before_check' }
    }
  } catch {
    $result.errorKind = 'after_check'
  }
} catch {
  $msg = [string]$_.Exception.Message
  if ($msg -match 'frequency|1440|24.hour|24 horas|cada 24') {
    $result.errorKind = 'frequency'
  } elseif ($msg -match 'disabled|deshabilitad|turned off') {
    $result.errorKind = 'disabled'
  } elseif ($msg -match 'access is denied|acceso denegado|privileg|administrator|administrador') {
    $result.errorKind = 'permissions'
  } else {
    $result.errorKind = 'operation'
  }
}
ConvertTo-Json -InputObject $result -Depth 5 -Compress
'''.strip()


def _run_ps_json(script: str, timeout: int = 45):
    """Entrega objeto y categoria de error sin mensajes localizados de consola."""
    if os.name != 'nt':
        return None, 'platform'
    exe = shutil.which('powershell.exe') or shutil.which('powershell')
    if not exe:
        return None, 'missing_powershell'
    # -EncodedCommand evita diferencias de interpretacion de comillas, acentos y
    # saltos de linea entre cmd.exe, PowerShell 5.1 y VS Code.
    encoded = base64.b64encode(script.encode('utf-16le')).decode('ascii')
    try:
        proc = subprocess.run(
            [exe, '-NoLogo', '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded],
            capture_output=True, timeout=timeout, check=False,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
    except subprocess.TimeoutExpired:
        return None, 'timeout'
    except OSError:
        return None, 'launch'
    if proc.returncode != 0:
        return None, 'command'
    try:
        out = proc.stdout.decode('utf-8-sig').strip()
        obj = json.loads(out)
    except (ValueError, UnicodeError, TypeError):
        return None, 'invalid_response'
    if not isinstance(obj, dict):
        return None, 'invalid_response'
    return obj, 'none'


def _run_reagentc():
    if os.name != 'nt':
        return None
    exe = shutil.which('reagentc.exe') or shutil.which('reagentc')
    if not exe:
        systemroot = os.environ.get('SystemRoot') or os.environ.get('WINDIR')
        if systemroot:
            candidate = Path(systemroot) / 'System32' / 'reagentc.exe'
            if candidate.is_file():
                exe = str(candidate)
    if not exe:
        return None
    try:
        proc = subprocess.run(
            [exe, '/info'], capture_output=True, timeout=30,
            check=False, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
        if proc.returncode != 0:
            return None
        for encoding in ('utf-8-sig', 'cp850', 'cp1252'):
            try:
                return proc.stdout.decode(encoding, errors='strict')
            except UnicodeError:
                pass
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def _parse_winre(value):
    if not value:
        return 'N/A'
    for line in str(value).splitlines():
        if not re.search(r'(?:windows\s*re|entorno\s+de\s+recuperaci[oó]n)', line, re.I):
            continue
        if not re.search(r'(?:windows\s*re\s*(?:status|estado)|(?:estado|status)\s+(?:de\s+)?windows\s*re)\s*:', line, re.I):
            continue
        status = line.split(':', 1)[-1].strip().lower()
        if re.search(r'^(?:enabled|habilitado|habilitada|activado|activada)\b', status):
            return 'Activa'
        if re.search(r'^(?:disabled|deshabilitado|deshabilitada|desactivado|desactivada)\b', status):
            return 'Desactivada'
    return 'N/A'


def _short(value, limit=90):
    cleaned = ''.join(char if char.isprintable() else ' ' for char in str(value if value is not None else '')).strip()
    return cleaned[:limit] if cleaned else 'N/A'


def _type_name(value):
    mapping = {0: 'Aplicacion instalada', 1: 'Aplicacion desinstalada', 10: 'Dispositivo',
               12: 'Modificacion', 13: 'Operacion cancelada', 16: 'Manual',
               17: 'Instalacion de actualizacion', 18: 'Windows Update'}
    try:
        integer = int(value)
    except (TypeError, ValueError):
        return 'N/A'
    return mapping.get(integer, f'Tipo {integer}')


def _failure_message(kind):
    return {
        'permissions': 'Windows no permitio consultar los puntos. Ejecuta CorePulse como administrador.',
        'disabled': 'La proteccion del sistema parece desactivada. Puedes revisarla en Windows.',
        'unsupported': 'Esta version de Windows no admite la consulta de puntos de restauracion.',
        'timeout': 'La consulta excedio el tiempo de espera.',
        'missing_powershell': 'PowerShell no esta disponible en este equipo.',
        'platform': 'Esta funcion requiere Windows.',
    }.get(kind, 'Windows no pudo completar la consulta de restauracion. Comprueba la configuracion del sistema.')


def has_admin_rights():
    if os.name != 'nt':
        return False
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


def _parse_restore_points(report):
    """Un fallo de consulta NO significa que haya cero puntos."""
    if not isinstance(report, dict):
        return [], 'N/A', 'N/A', 'N/A', False
    if report.get('available') is not True or not isinstance(report.get('pointCount'), int):
        return [], 'N/A', 'N/A', 'N/A', False
    count = report['pointCount']
    if count < 0:
        return [], 'N/A', 'N/A', 'N/A', False
    value = report.get('points')
    rows = value if isinstance(value, list) else ([value] if isinstance(value, dict) else [])
    points = []
    for row in rows[:12]:
        if not isinstance(row, dict):
            continue
        desc = _short(row.get('Description'), 120)
        when = _short(row.get('CreationTime'), 32)
        sequence = row.get('SequenceNumber')
        points.append({'primary': desc,
                       'secondary': f'{_type_name(row.get("RestorePointType"))} · {when} · Nº {_short(sequence, 12)}'})
    latest = points[0] if points else None
    latest_raw = rows[0] if rows and isinstance(rows[0], dict) else None
    return points, str(count), (latest['primary'] if latest else 'Sin puntos'), (
        _short(latest_raw.get('CreationTime')) if latest_raw else 'Sin puntos'), True


def read_recovery_report(on_progress=None):
    if os.name != 'nt':
        return None
    if on_progress:
        on_progress(10, 'Consultando puntos de restauracion…')
    restore, read_error = _run_ps_json(RESTORE_POINTS_QUERY)
    if on_progress:
        on_progress(60, 'Comprobando Windows RE…')
    recovery_env = _parse_winre(_run_reagentc())
    if on_progress:
        on_progress(90, 'Preparando resultados…')
    points, count, latest_description, latest_created, known = _parse_restore_points(restore)
    issue = restore.get('errorKind', 'query') if isinstance(restore, dict) else read_error
    protection_state = restore.get('protectionState', 'unknown') if isinstance(restore, dict) else 'unknown'
    protection_text = 'Desactivada' if protection_state == 'disabled' else 'No confirmada'
    if known:
        summary = 'Consulta de puntos completada.' if count != '0' else 'Consulta completada: no se encontraron puntos.'
        status = 'OK'
    else:
        summary = _failure_message(issue)
        status = 'PARCIAL' if recovery_env != 'N/A' else 'ERROR'
    if protection_state == 'disabled':
        protection_text = 'Desactivada'
        if known:
            summary = 'Se leyeron puntos, pero Windows informa una restriccion de proteccion.'
            status = 'PARCIAL'
    if on_progress:
        on_progress(100, 'Consulta finalizada.')
    return {
        'busy': False, 'status': status, 'summary': summary,
        'progress': 100, 'stage': 'Consulta finalizada.',
        'isAdmin': has_admin_rights(),
        'systemDrive': os.environ.get('SystemDrive') or 'N/A',
        'protectionText': protection_text,
        'protectionEnabled': False if protection_state == 'disabled' else None,
        'recoveryEnv': recovery_env,
        'pointCount': count, 'latestDescription': latest_description,
        'latestCreated': latest_created, 'points': points,
        'lastUpdate': datetime.now().strftime('%H:%M:%S'),
        'logPath': 'N/A',
        'details': 'Fuente: Get-ComputerRestorePoint / registro de Windows / reagentc.',
    }


def _creation_failure(kind):
    return {
        'frequency': 'Windows limita la creacion de puntos: espera al intervalo permitido.',
        'disabled': 'La proteccion del sistema esta desactivada. Activa la proteccion en Windows.',
        'permissions': 'Windows requiere permisos de administrador para crear un punto.',
        'unverified': 'Windows no mostro un punto nuevo. No se puede confirmar la creacion.',
        'after_check': 'Windows ejecuto la operacion, pero no se pudo verificar un punto nuevo.',
        'before_check': 'No se pudo obtener el estado anterior de los puntos de restauracion.',
    }.get(kind, 'Windows no confirmo la creacion del punto de restauracion.')


def create_restore_point():
    if not has_admin_rights():
        return False, 'Se requieren permisos de administrador para crear un punto de restauracion.'
    reply, error = _run_ps_json(CREATE_POINT_SCRIPT, timeout=300)
    if not isinstance(reply, dict):
        return False, _creation_failure(error)
    if reply.get('ok') is True and reply.get('verified') is True:
        return True, 'Punto de restauracion creado y verificado mediante Windows.'
    return False, _creation_failure(reply.get('errorKind', 'operation'))


class RecoveryHealth(QObject):
    changed = Signal()
    progress = Signal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._closed = False
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='corepulse-recovery-health')
        self._future: Future | None = None
        self._mode = 'refresh'
        self._data = {
            'busy': False, 'status': 'N/A', 'summary': 'Sin consultas ejecutadas.',
            'progress': 0, 'stage': 'Sin consultas ejecutadas.',
            'isAdmin': has_admin_rights(), 'systemDrive': os.environ.get('SystemDrive') or 'N/A',
            'protectionText': 'No confirmada', 'protectionEnabled': None,
            'recoveryEnv': 'N/A', 'pointCount': 'N/A',
            'latestDescription': 'N/A', 'latestCreated': 'N/A',
            'points': [], 'lastUpdate': 'N/A', 'logPath': 'N/A', 'details': 'N/A',
        }
        self.progress.connect(self._set_progress)
        self._poll = QTimer(self)
        self._poll.setInterval(300)
        self._poll.timeout.connect(self._check)
        self._auto = QTimer(self)
        self._auto.setInterval(300000)
        self._auto.timeout.connect(self.refresh)

    @Property('QVariantMap', notify=changed)
    def data(self):
        return self._data

    @Slot(int, str)
    def _set_progress(self, value, label):
        if not self._closed and self._future is not None:
            self._data = {**self._data, 'progress': max(0, min(100, int(value))),
                          'stage': str(label or 'Consultando…')}
            self.changed.emit()

    @Slot()
    def refresh(self):
        if self._closed or self._future is not None:
            return
        if not self._auto.isActive():
            self._auto.start()
        self._mode = 'refresh'
        self._data = {**self._data, 'busy': True, 'status': 'EN_CURSO',
                      'summary': 'Windows esta consultando Recuperacion…',
                      'progress': 5, 'stage': 'Preparando consulta…'}
        self.changed.emit()
        self._future = self._executor.submit(read_recovery_report, self.progress.emit)
        self._poll.start()

    @Slot()
    def createPoint(self):
        if self._closed or self._future is not None:
            return
        if not has_admin_rights():
            self._data = {**self._data, 'busy': False, 'status': 'ADMIN',
                          'summary': 'Abre CorePulse como administrador para crear un punto de restauracion.',
                          'isAdmin': False, 'progress': 0, 'stage': 'Permisos insuficientes.'}
            self.changed.emit()
            return
        self._mode = 'create'
        self._data = {**self._data, 'busy': True, 'status': 'EN_CURSO',
                      'summary': 'Windows esta creando un punto de restauracion…',
                      'progress': 8, 'stage': 'Solicitando creacion…', 'isAdmin': True}
        self.changed.emit()
        self._future = self._executor.submit(create_restore_point)
        self._poll.start()

    def _check(self):
        if self._closed or self._future is None or not self._future.done():
            return
        try:
            result = self._future.result()
        except Exception:
            result = None
        mode = self._mode
        self._future = None
        self._poll.stop()
        if mode == 'refresh':
            if isinstance(result, dict):
                self._data = result
            else:
                self._data = {**self._data, 'busy': False, 'status': 'ERROR',
                              'summary': 'No se pudo consultar la recuperacion del sistema.',
                              'progress': 0, 'stage': 'Consulta fallida.'}
            self.changed.emit()
            return
        ok, message = result if isinstance(result, tuple) and len(result) == 2 else (
            False, 'No se pudo crear el punto de restauracion.')
        self._data = {**self._data, 'busy': False, 'status': 'OK' if ok else 'ERROR',
                      'summary': message, 'progress': 100 if ok else 0,
                      'stage': 'Creacion finalizada.' if ok else 'No se pudo verificar la creacion.',
                      'lastUpdate': datetime.now().strftime('%H:%M:%S')}
        self.changed.emit()
        if ok:
            # Solo despues de confirmacion y comprobacion, refrescar el inventario.
            self.refresh()

    @Slot()
    def openSystemRestore(self):
        if os.name != 'nt':
            return
        exe = shutil.which('rstrui.exe') or shutil.which('rstrui')
        if not exe:
            return
        try:
            subprocess.Popen([exe], creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        except OSError:
            pass

    @Slot()
    def openRecoverySettings(self):
        if os.name != 'nt':
            return
        try:
            os.startfile('ms-settings:recovery')  # type: ignore[attr-defined]
            return
        except (OSError, AttributeError):
            pass
        exe = shutil.which('control.exe')
        if exe:
            try:
                subprocess.Popen([exe, '/name', 'Microsoft.Recovery'],
                                 creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            except OSError:
                pass

    @Slot()
    def close(self):
        self._closed = True
        self._poll.stop()
        self._auto.stop()
        self._executor.shutdown(wait=False, cancel_futures=True)
