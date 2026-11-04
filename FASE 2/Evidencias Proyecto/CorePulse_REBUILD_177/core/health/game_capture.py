"""Diseños del OSD y registro local de problemas con fotogramas observados."""
from __future__ import annotations

from collections import deque
from datetime import datetime
import json
import math
import os
from pathlib import Path
import statistics
import time
import uuid

from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot, QUrl
from PySide6.QtGui import QDesktopServices

METRICS = ('fps', 'cpu', 'gpu', 'ram', 'disk')
DEFAULT_DESIGN = dict(scale=100, opacity=94, gap=8, x=1000, y=0,
                      metrics=['fps', 'cpu', 'gpu', 'ram'], frametime=True)


def normalize_design(value):
    value = value if isinstance(value, dict) else {}
    result = {}
    for key, low, high in (('scale', 60, 160), ('opacity', 25, 100),
                           ('gap', 0, 24), ('x', 0, 1000), ('y', 0, 1000)):
        number = value.get(key, DEFAULT_DESIGN[key])
        result[key] = max(low, min(high, round(number))) if (
            isinstance(number, (int, float)) and not isinstance(number, bool)
            and math.isfinite(number)) else DEFAULT_DESIGN[key]
    items = value.get('metrics', DEFAULT_DESIGN['metrics'])
    result['metrics'] = list(dict.fromkeys(item for item in items if item in METRICS)) if isinstance(items, list) else list(DEFAULT_DESIGN['metrics'])
    if not result['metrics']:
        result['metrics'] = ['fps']
    result['frametime'] = value.get('frametime', True) is not False
    return result


def frame_summary(rows):
    values = [r['ms'] for r in rows if isinstance(r.get('ms'), (int, float)) and 0 < r['ms'] < 10000]
    if not values:
        return dict(count=0, median=None, p99=None, maximum=None, slow=0, threshold=None)
    median = statistics.median(values)
    threshold = max(33.33, median * 2)
    return dict(count=len(values), median=round(median, 2),
                p99=round(sorted(values)[max(0, math.ceil(len(values) * .99)-1)], 2),
                maximum=round(max(values), 2), slow=sum(v >= threshold for v in values),
                threshold=round(threshold, 2))


def peak_series(rows, limit=500):
    """Reduce visualmente conservando el pico de cada bloque; JSON conserva todo."""
    if len(rows) <= limit:
        return rows
    step = math.ceil(len(rows) / limit)
    return [max(rows[i:i+step], key=lambda r: r['ms']) for i in range(0, len(rows), step)]


class ProblemCapture(QObject):
    changed = Signal()

    def __init__(self, overlay, parent=None, folder=None):
        super().__init__(parent)
        self._overlay = overlay
        self._folder = Path(folder) if folder else Path(os.environ.get('LOCALAPPDATA') or Path.home()) / 'CorePulse' / 'registros'
        self._history = deque(maxlen=220)
        self._frames = deque(maxlen=80000)
        self._pid = 0
        self._pending = None
        self._selected = ''
        self._pdf = ''
        self._message = ''
        self._closed = False
        self._data = {}
        overlay.sampleObserved.connect(self.observe)
        overlay.problemRequested.connect(self.record)
        self._timer = QTimer(self)
        self._timer.setInterval(500)
        self._timer.timeout.connect(self._tick)
        self._timer.start()
        self._refresh()

    @Property('QVariantMap', notify=changed)
    def data(self):
        return self._data

    def _paths(self):
        if not self._folder.is_dir():
            return []
        return sorted(self._folder.glob('CorePulse_Problema_*.json'), reverse=True)[:20]

    def _load(self, path):
        try:
            if path.stat().st_size > 20_000_000:
                return None
            value = json.loads(path.read_text(encoding='utf-8'))
            return value if (value.get('schema') == 1 and isinstance(value.get('samples'), list)
                             and isinstance(value.get('frames'), list) and isinstance(value.get('summary'), dict)
                             and all(k in value for k in ('name','label','partial','preSeconds','postSeconds','note'))
                             and all(k in value['summary'] for k in ('count','median','p99','maximum','slow','threshold'))) else None
        except (OSError, ValueError, TypeError, AttributeError):
            return None

    def _refresh(self):
        captures, selected = [], {}
        for path in self._paths():
            row = self._load(path)
            if not row:
                continue
            captures.append(dict(id=path.stem, name=row['name'], label=row['label'],
                                 frames=row['summary']['count'], partial=row['partial']))
            if not self._selected:
                self._selected = path.stem
            if path.stem == self._selected:
                selected = {**row, 'frames': peak_series(row['frames']), 'id': path.stem}
        self._data = dict(recording=self._pending is not None, captures=captures,
                          selected=selected, message=self._message, pdfPath=self._pdf,
                          remaining=max(0, math.ceil(self._pending['until']-time.monotonic())) if self._pending else 0)
        self.changed.emit()

    @Slot(object)
    def observe(self, sample):
        now, pid = sample['time'], sample['pid']
        if pid != self._pid:
            if self._pending:
                self._finish('El juego dejó el primer plano antes de completar los 15 segundos posteriores.')
            self._history.clear()
            self._frames.clear()
            self._pid = pid
        if not pid:
            return
        row = {k: (None if isinstance(v, (int, float)) and not math.isfinite(v) else v)
               for k, v in sample.items() if k != 'frames'}
        self._history.append(row)
        frames = [dict(time=t, ms=ms) for t, ms in sample.get('frames', [])]
        self._frames.extend(frames)
        while self._history and self._history[0]['time'] < now-30:
            self._history.popleft()
        while self._frames and self._frames[0]['time'] < now-30:
            self._frames.popleft()
        if self._pending:
            self._pending['samples'].append(row)
            self._pending['frames'].extend(frames)
            if len(self._pending['frames']) > 120000:
                self._pending['frames'] = self._pending['frames'][:120000]
                self._pending['truncated'] = True

    @Slot()
    def record(self):
        if self._pending:
            self._message = 'Ya se está registrando un problema; espera a que termine.'
            self._refresh()
            return
        if not self._pid or not self._history or time.monotonic()-self._history[-1]['time'] > 2:
            self._message = 'Abre un juego y activa el overlay para registrar lecturas recientes.'
            self._refresh()
            return
        now = time.monotonic()
        self._pending = dict(mark=now, until=now+15, wall=time.time(),
                             name=self._history[-1]['name'], samples=list(self._history),
                             frames=list(self._frames), truncated=False)
        self._message = 'Guardando 15 segundos posteriores; puedes seguir jugando.'
        self._overlay.setCaptureStatus('Registrando problema · 15 s')
        self._refresh()

    def _tick(self):
        if self._pending:
            left = math.ceil(self._pending['until']-time.monotonic())
            if left <= 0:
                self._finish('')
            else:
                self._overlay.setCaptureStatus(f'Registrando problema · {left} s')
                self._data['remaining'] = left
                self.changed.emit()

    def _finish(self, reason):
        pending, self._pending = self._pending, None
        if not pending:
            return
        mark = pending['mark']
        samples = [{**r, 'time': round(r['time']-mark, 3)} for r in pending['samples']]
        frames = [dict(time=round(r['time']-mark, 4), ms=round(r['ms'], 4)) for r in pending['frames']]
        pre = max(0, -samples[0]['time']) if samples else 0
        post = max(0, samples[-1]['time']) if samples else 0
        summary = frame_summary(frames)
        stamp = datetime.fromtimestamp(pending['wall'])
        row = dict(schema=1, name=pending['name'], label=stamp.strftime('%d/%m/%Y %H:%M:%S'),
                   recorded=pending['wall'], samples=samples, frames=frames, summary=summary,
                   preSeconds=round(pre, 1), postSeconds=round(post, 1),
                   partial=bool(reason or pre < 29 or post < 14 or pending['truncated'] or not frames),
                   note=reason or ('Límite de fotogramas alcanzado.' if pending['truncated'] else
                                   'No se recibieron fotogramas ETW; solo hay lecturas de sensores.' if not frames else ''),
                   source='ETW · intervalos reales entre presentaciones; sin reconstruir desde FPS')
        try:
            self._folder.mkdir(parents=True, exist_ok=True)
            name = f'CorePulse_Problema_{stamp:%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:8]}'
            path = self._folder / (name+'.json')
            temporary = path.with_suffix('.tmp')
            temporary.write_text(json.dumps(row, ensure_ascii=False, allow_nan=False), encoding='utf-8')
            temporary.replace(path)
            self._selected = name
            for old in sorted(self._folder.glob('CorePulse_Problema_*.json'), reverse=True)[20:]:
                old.unlink()
            self._message = 'Problema registrado. Disponible en Sesiones de juego → Registros.'
            self._overlay.setCaptureStatus('Problema guardado')
        except (OSError, ValueError):
            self._message = 'No se pudo guardar el registro en el disco.'
            self._overlay.setCaptureStatus('Error al guardar registro')
        self._refresh()

    @Slot(str)
    def select(self, identifier):
        if any(p.stem == identifier for p in self._paths()):
            self._selected = identifier
            self._pdf = ''
            self._refresh()

    @Slot()
    def openFolder(self):
        try:
            self._folder.mkdir(parents=True, exist_ok=True)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._folder)))
        except OSError:
            self._message = 'No se pudo abrir la carpeta de registros.'
            self._refresh()

    @Slot()
    def exportPdf(self):
        # Reuse the report engine used by diagnostic/benchmark/session PDFs.
        from core.health.report import _PdfDocument, _output_dir, _number
        row = self._data.get('selected')
        if not row:
            return
        try:
            folder = _output_dir()
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / (self._selected+'.pdf')
            doc = _PdfDocument(path, 'Registro de problema', row['name'][:70])
            try:
                summary = row['summary']
                doc.paragraph(row['label']+' · '+row['name'], bold=True)
                doc.cards([('Mediana', _number(summary['median'], ' ms'), 'tiempo por fotograma'),
                           ('P99', _number(summary['p99'], ' ms'), 'percentil 99'),
                           ('Pico', _number(summary['maximum'], ' ms'), 'máximo observado'),
                           ('Fotogramas', str(summary['count']), 'intervalos ETW')])
                doc.section('Frametime alrededor del marcador')
                doc.line_chart(row['frames'], marker=0)
                doc.table([('Antes / después del atajo', f"{row['preSeconds']} s / {row['postSeconds']} s"),
                           ('Estado del registro', 'Parcial' if row['partial'] else 'Completo'),
                           ('Intervalos lentos', str(summary['slow'])),
                           ('Umbral observado', _number(summary['threshold'], ' ms'))])
                if row['note']:
                    doc.note(row['note'])
                doc.section('Lecturas cercanas al atajo')
                near = min(row['samples'], key=lambda r: abs(r['time'])) if row['samples'] else {}
                doc.table([(label, _number(near.get(key), suffix)) for key, label, suffix in
                           [('cpu', 'Uso CPU', ' %'), ('gpu', 'Uso GPU', ' %'), ('ram', 'RAM ocupada', ' %'),
                            ('cpuTemp', 'Temperatura CPU', ' °C'), ('gpuTemp', 'Temperatura GPU', ' °C'),
                            ('gpuMemoryUsed', 'VRAM usada', ' GiB'), ('cpuClock', 'Frecuencia CPU', ' GHz')]])
                doc.note('Fuente de frecuencia CPU: '+str(near.get('cpuClockSource') or 'N/A'))
                doc.note('Los picos y las lecturas coinciden en el tiempo; no demuestran una causa. '
                         'La línea resume los picos por bloque para ser legible. El JSON local conserva '
                         'los intervalos originales. Sin ETW disponible, frametime aparece como N/A.')
            finally:
                doc.finish()
            self._pdf = str(path)
            self._message = 'Informe del problema generado.'
        except (OSError, ValueError):
            self._message = 'No se pudo generar el informe del problema.'
        self._refresh()

    @Slot()
    def openPdf(self):
        if self._pdf and Path(self._pdf).is_file():
            QDesktopServices.openUrl(QUrl.fromLocalFile(self._pdf))

    @Slot()
    def close(self):
        if self._closed:
            return
        self._closed = True
        self._timer.stop()
        self._finish('CorePulse se cerró antes de terminar el registro.')
