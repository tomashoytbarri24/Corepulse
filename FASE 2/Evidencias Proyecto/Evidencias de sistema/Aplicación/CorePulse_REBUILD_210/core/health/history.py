"""Historial de cambios del Centro de salud (solo lectura).

Une fuentes existentes SIN inventar operaciones ni atribuir cambios ajenos a
CorePulse: auditoría de Tweaks, informes DISM/SFC, Windows Update (COM local)
y puntos de restauración registrados en Windows. Las fuentes son independientes;
un fallo nunca se convierte en cero eventos. No guarda datos personales ni
modifica la configuración de Windows.
"""
from __future__ import annotations

import base64
from collections import deque
from concurrent.futures import Future
from concurrent.futures.thread import ThreadPoolExecutor
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from PySide6.QtCore import QObject, Property, Signal, Slot, QTimer

from .recovery import RESTORE_POINTS_QUERY, _run_ps_json


SOURCE_LABELS = {
    'tweaks': 'Tweaks CorePulse',
    'repair': 'Integridad de Windows',
    'updates': 'Windows Update',
    'restore': 'Puntos de restauración',
}
SOURCE_HINTS = {
    'tweaks': 'Historial local de operaciones CorePulse',
    'repair': 'Informes de DISM y SFC guardados por CorePulse',
    'updates': 'Hasta 30 operaciones recientes del historial local de Windows Update',
    'restore': 'Últimos puntos registrados por Restaurar sistema',
}
UPDATE_HISTORY = r'''
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=[Text.Encoding]::UTF8
$r = [ordered]@{available=$false; entries=@()}
try {
  $session = New-Object -ComObject 'Microsoft.Update.Session' -ErrorAction Stop
  $searcher = $session.CreateUpdateSearcher()
  $count = [Math]::Min([int]$searcher.GetTotalHistoryCount(), 30)
  $items = @()
  if ($count -gt 0) {
    foreach ($item in $searcher.QueryHistory(0, $count)) {
      $items += [pscustomobject]@{
        Title = [string]$item.Title
        Date = $item.Date.ToString('o')
        Operation = [int]$item.Operation
        ResultCode = [int]$item.ResultCode
      }
    }
  }
  $r.available=$true
  $r.entries=@($items)
} catch {}
ConvertTo-Json -InputObject $r -Depth 5 -Compress
'''.strip()


def _short(value, limit=130):
    if value is None:
        return 'N/A'
    txt = ''.join(ch if ch.isprintable() else ' ' for ch in str(value)).strip()
    return (txt[:limit] if txt else 'N/A')


def _dt(value):
    """Devuelve instante ordenable local; no fabrica fechas si son inválidas."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            return datetime.fromtimestamp(value).astimezone()
        except (ValueError, OverflowError, OSError):
            return None
    if not isinstance(value, str):
        return None
    try:
        obj = datetime.fromisoformat(value.strip().replace('Z', '+00:00'))
        return obj.astimezone() if obj.tzinfo else obj
    except (ValueError, OverflowError):
        return None


def _event(source, title, details, state, date):
    at = _dt(date)
    if at is None:
        return None
    return {
        'source': source, 'sourceTitle': SOURCE_LABELS[source],
        'title': _short(title, 145), 'details': _short(details, 200),
        'state': _short(state, 36),
        'date': at.strftime('%d/%m/%Y · %H:%M'),
        '_sort': at.timestamp(),
    }


def _result(items, available, caption=None):
    return {'available': bool(available), 'entries': items,
            'caption': caption or ('' if available else 'Consulta no disponible')}


def read_tweaks(data_dir):
    """Nunca consulta ni altera el estado de Tweaks; solo lee JSONL existente."""
    path = Path(data_dir) / 'windows_tweaks_history.jsonl'
    if not path.exists():
        return _result([], True, 'Sin operaciones registradas en este perfil')
    if path.is_symlink():
        return _result([], False)
    records = deque(maxlen=80)
    try:
        with path.open('r', encoding='utf-8', errors='replace') as handle:
            for line in handle:
                if len(line) > 16384:
                    continue
                try:
                    obj = json.loads(line)
                except (ValueError, TypeError):
                    continue
                if isinstance(obj, dict):
                    records.append(obj)
    except OSError:
        return _result([], False)
    events = []
    for row in records:
        action = str(row.get('action') or '').lower()
        if action not in ('apply', 'undo'):
            continue
        success = row.get('success') is True
        state = ('Aplicado' if action == 'apply' else 'Restaurado') if success else 'Falló'
        name = _short(row.get('tweak_id'), 85).replace('_', ' ')
        e = _event('tweaks', name, 'Acción: ' + ('Aplicar' if action == 'apply' else 'Restaurar'), state, row.get('timestamp'))
        if e:
            events.append(e)
    return _result(events, True, 'Auditoría persistente del motor de Tweaks')


def read_repairs(log_dir):
    folder = Path(log_dir)
    if not folder.exists():
        return _result([], True, 'Sin análisis ni reparaciones registrados')
    if folder.is_symlink():
        return _result([], False)
    try:
        paths = sorted((p for p in folder.glob('integridad_*.json') if p.is_file() and not p.is_symlink()), reverse=True)[:40]
    except OSError:
        return _result([], False)
    events = []
    for path in paths:
        try:
            if path.stat().st_size > 1_500_000:
                continue
            report = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError, TypeError):
            continue
        if not isinstance(report, dict):
            continue
        kind = report.get('kind')
        if kind not in ('repair', 'diagnostic'):
            continue
        summary = 'Reparación DISM/SFC' if kind == 'repair' else 'Comprobación de integridad DISM/SFC'
        stages = report.get('results')
        count = len(stages) if isinstance(stages, list) else 0
        state = _short(report.get('state'), 36)
        e = _event('repair', summary, f'{count} etapas registradas · Resultado: {state}', state, report.get('finished') or report.get('started'))
        if e:
            events.append(e)
    if paths and not events:
        return _result([], False, 'Los informes existentes no pudieron interpretarse')
    return _result(events, True, 'Registros locales de DISM/SFC')


def parse_updates(raw):
    if not isinstance(raw, dict) or raw.get('available') is not True:
        return _result([], False, 'Historial de Windows Update inaccesible')
    rows = raw.get('entries')
    if not isinstance(rows, list):
        return _result([], False, 'Datos del historial incompletos')
    events = []
    for row in rows[:30]:
        if not isinstance(row, dict):
            continue
        operation = row.get('Operation')
        if operation not in (1, 2):
            continue
        result = row.get('ResultCode')
        state = {2:'Correcto', 3:'Con errores', 4:'Falló', 5:'Cancelado'}.get(result, 'Sin clasificar')
        detail = ('Instalación' if operation == 1 else 'Desinstalación') + ' · ' + state
        event = _event('updates', row.get('Title'), detail, state, row.get('Date'))
        if event:
            events.append(event)
    if rows and not events:
        return _result([], False, 'No se pudieron interpretar las operaciones recientes')
    return _result(events, True, 'Últimas 30 operaciones registradas por Windows Update')


def read_updates():
    if os.name != 'nt':
        return _result([], False)
    exe = shutil.which('powershell.exe') or shutil.which('powershell')
    if not exe:
        return _result([], False)
    encoded = base64.b64encode(UPDATE_HISTORY.encode('utf-16le')).decode('ascii')
    try:
        proc = subprocess.run([exe, '-NoLogo', '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded],
                              stdin=subprocess.DEVNULL, capture_output=True, timeout=50, check=False,
                              creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if proc.returncode != 0:
            return _result([], False)
        return parse_updates(json.loads(proc.stdout.decode('utf-8-sig').strip()))
    except (OSError, ValueError, UnicodeError, subprocess.TimeoutExpired):
        return _result([], False)


def parse_restore(raw):
    if not isinstance(raw, dict) or raw.get('available') is not True or not isinstance(raw.get('pointCount'), int):
        return _result([], False, 'No se pudo consultar Restaurar sistema')
    rows = raw.get('points')
    if not isinstance(rows, (dict, list)):
        return _result([], False, 'Respuesta incompleta de Restaurar sistema')
    if isinstance(rows, dict):
        rows = [rows]
    events = []
    for row in rows[:12]:
        if not isinstance(row, dict):
            continue
        event = _event('restore', row.get('Description'),
                       'Punto de restauración registrado · Nº ' + _short(row.get('SequenceNumber'), 12),
                       'Registrado', row.get('CreationTime'))
        if event:
            events.append(event)
    if rows and not events:
        return _result([], False, 'No se pudieron interpretar las fechas de los puntos')
    return _result(events, True, 'Hasta 12 puntos de restauración disponibles')


def read_restore():
    if os.name != 'nt':
        return _result([], False)
    report, error = _run_ps_json(RESTORE_POINTS_QUERY, timeout=45)
    return parse_restore(report)


def read_history(on_progress=None, localappdata=None, readers=None):
    """Cuatro fuentes aisladas. Progreso por consultas finalizadas, no por reloj."""
    root = Path(localappdata or os.environ.get('LOCALAPPDATA') or Path.home() / 'AppData' / 'Local') / 'CorePulse'
    runners = readers or {
        'tweaks': lambda: read_tweaks(root / 'rebuild' / 'v485_tweaks'),
        'repair': lambda: read_repairs(root / 'logs' / 'reparacion_windows'),
        'updates': read_updates,
        'restore': read_restore,
    }
    sections = []
    events = []
    for index, (key, label) in enumerate(SOURCE_LABELS.items(), 1):
        if on_progress:
            on_progress(round((index - 1) / 4 * 100), f'Consultando {label}…')
        try:
            result = runners[key]()
        except Exception:
            result = _result([], False)
        if not isinstance(result, dict):
            result = _result([], False)
        available = result.get('available') is True
        rows = result.get('entries') if isinstance(result.get('entries'), list) else []
        valid = [e for e in rows if isinstance(e, dict) and e.get('source') == key and isinstance(e.get('_sort'), (int, float))]
        events.extend(valid)
        sections.append({
            'key': key, 'title': label,
            'metric': str(len(valid)) if available else 'N/A',
            'available': available,
            'caption': _short(result.get('caption') or SOURCE_HINTS[key], 130),
        })
        if on_progress:
            on_progress(round(index / 4 * 100), f'{label}: consulta finalizada')
    events.sort(key=lambda entry: entry['_sort'], reverse=True)
    timeline = [{key: val for key, val in row.items() if key != '_sort'} for row in events[:45]]
    accessible = sum(section['available'] for section in sections)
    return {
        'busy': False,
        'progress': 100,
        'stage': 'Consulta completada.' if accessible == 4 else 'Consulta parcial: una o más fuentes no disponibles.',
        'status': 'LISTO' if accessible == 4 else ('PARCIAL' if accessible else 'N/A'),
        'sourceCount': f'{accessible}/4',
        'sections': sections,
        'events': timeline,
        'shownCount': len(timeline),
        'lastUpdate': datetime.now().strftime('%H:%M:%S'),
    }


class ChangeHistory(QObject):
    changed = Signal()
    progressSignal = Signal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._closed = False
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='corepulse-change-history')
        self._future: Future | None = None
        self._data = {'busy': False, 'progress': 0, 'stage': 'Sin consultas ejecutadas.',
                      'status': 'N/A', 'sourceCount': 'N/A', 'sections': [],
                      'events': [], 'shownCount': 0, 'lastUpdate': 'N/A'}
        self.progressSignal.connect(self._on_progress)
        self._poll = QTimer(self)
        self._poll.setInterval(250)
        self._poll.timeout.connect(self._finish_if_ready)

    @Property('QVariantMap', notify=changed)
    def data(self):
        return self._data

    @Slot(int, str)
    def _on_progress(self, amount, label):
        if not self._closed and self._future is not None:
            self._data = {**self._data, 'progress': max(0, min(100, int(amount))), 'stage': _short(label)}
            self.changed.emit()

    @Slot()
    def refresh(self):
        if self._closed or self._future is not None:
            return
        self._data = {**self._data, 'busy': True, 'progress': 0, 'stage': 'Iniciando consultas…', 'status': 'EN_CURSO'}
        self.changed.emit()
        self._future = self._pool.submit(read_history, self.progressSignal.emit)
        self._poll.start()

    def _finish_if_ready(self):
        if self._closed or self._future is None or not self._future.done():
            return
        try:
            result = self._future.result()
        except Exception:
            result = {'busy': False, 'progress': 100, 'stage': 'Error al recopilar el historial.',
                      'status': 'ERROR', 'sourceCount': 'N/A', 'sections': [], 'events': [],
                      'shownCount': 0, 'lastUpdate': 'N/A'}
        self._future = None
        self._poll.stop()
        self._data = result
        self.changed.emit()

    @Slot()
    def close(self):
        self._closed = True
        self._poll.stop()
        self._pool.shutdown(wait=False, cancel_futures=True)
