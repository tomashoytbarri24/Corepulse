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

from PySide6.QtCore import QObject, Property, QSettings, QTimer, Signal, Slot, QUrl
from PySide6.QtGui import QDesktopServices

METRICS = ('fps', 'cpu', 'gpu', 'ram', 'disk')
DEFAULT_DESIGN = dict(scale=100, opacity=94, gap=8, x=1000, y=0,
                      metrics=['fps', 'cpu', 'gpu', 'ram'], frametime=True)
AUTO_WARMUP_SECONDS = 5
AUTO_COOLDOWN_SECONDS = 60


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

    def __init__(self, overlay, parent=None, folder=None, settings=None):
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
        self._settings = settings if settings is not None else QSettings('CorePulse', 'CorePulseRebuild')
        self._automatic = self._settings.value('records/automatic', True, type=bool)
        self._auto_frames = deque(maxlen=16000)
        self._auto_started_at = None
        self._auto_last_frame = None
        self._auto_last_capture = -math.inf
        self._auto_status = 'Esperando fotogramas del juego' if self._automatic else 'Desactivada'
        overlay.sampleObserved.connect(self.observe)
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
                             and isinstance(value.get('trigger', {}), dict)
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
            automatic = row.get('trigger', {}).get('kind') == 'automatic'
            captures.append(dict(id=path.stem, name=row['name'], label=row['label'] + (' · Automático' if automatic else ' · Manual'),
                                 frames=row['summary']['count'], partial=row['partial']))
            if not self._selected:
                self._selected = path.stem
            if path.stem == self._selected:
                selected = {**row, 'frames': peak_series(row['frames']), 'id': path.stem}
        self._data = dict(recording=self._pending is not None, captures=captures,
                          selected=selected, message=self._message, pdfPath=self._pdf,
                          automatic=self._automatic, autoStatus=self._auto_status,
                          remaining=max(0, math.ceil(self._pending['until']-time.monotonic())) if self._pending else 0)
        self.changed.emit()

    def _reset_detector(self):
        self._auto_frames.clear()
        self._auto_started_at = self._auto_last_frame = None

    def _set_auto_status(self, text):
        if text != self._auto_status:
            self._auto_status = text
            self._data['autoStatus'] = text
            self.changed.emit()

    @Slot(bool)
    def setAutomatic(self, enabled):
        self._automatic = bool(enabled)
        self._settings.setValue('records/automatic', self._automatic)
        self._reset_detector()
        self._auto_status = 'Esperando fotogramas del juego' if self._automatic else 'Desactivada'
        self._message = ''
        self._refresh()

    def _detect_stutter(self, frames, now, is_game):
        """Use measured intervals only; a spike is evidence of delay, not its cause."""
        if not self._automatic or not is_game:
            self._reset_detector()
            self._set_auto_status('Esperando fotogramas del juego' if self._automatic else 'Desactivada')
            return
        # One median per telemetry batch, rather than sorting on every frame.
        baseline = (statistics.median(ms for _, ms in self._auto_frames)
                    if len(self._auto_frames) >= 30 and
                    self._auto_frames[-1][0] - self._auto_frames[0][0] >= 2 else None)
        for frame in frames:
            stamp, ms = frame['time'], frame['ms']
            if stamp < now - 2 or stamp > now + .1 or (self._auto_last_frame is not None and stamp <= self._auto_last_frame):
                continue
            # A capture gap is not a measured slow frame. A long interval whose
            # duration explains the gap remains eligible (a real freeze).
            if self._auto_last_frame is not None and stamp - self._auto_last_frame - ms / 1000 > .5:
                self._reset_detector()
                baseline = None
            if self._auto_started_at is None:
                self._auto_started_at = stamp
            while self._auto_frames and self._auto_frames[0][0] < stamp - 3:
                self._auto_frames.popleft()
            threshold = max(50.0, baseline * 3) if baseline is not None else None
            if (threshold is not None and stamp - self._auto_started_at >= AUTO_WARMUP_SECONDS
                    and ms >= threshold and not self._pending
                    and now - self._auto_last_capture >= AUTO_COOLDOWN_SECONDS):
                self._start_capture(stamp, dict(frameMs=ms, baselineMs=round(baseline, 3), thresholdMs=round(threshold, 3)))
            self._auto_frames.append((stamp, ms))
            self._auto_last_frame = stamp
        if self._auto_last_frame is None or now - self._auto_last_frame > 2:
            self._reset_detector()
            self._set_auto_status('Esperando fotogramas del juego')
        elif self._pending:
            self._set_auto_status('Guardando el evento')
        elif now - self._auto_last_capture < AUTO_COOLDOWN_SECONDS:
            self._set_auto_status('Activa · evitando registros repetidos')
        else:
            self._set_auto_status('Activa · observando fotogramas' if baseline is not None and now - self._auto_started_at >= AUTO_WARMUP_SECONDS else 'Preparando medición')

    @Slot(object)
    def observe(self, sample):
        if self._closed:
            return
        now, pid = sample['time'], sample['pid']
        if pid != self._pid:
            if self._pending:
                self._finish('El juego dejó el primer plano antes de completar los 15 segundos posteriores.')
            self._history.clear()
            self._frames.clear()
            self._reset_detector()
            self._pid = pid
        if not pid:
            self._set_auto_status('Esperando fotogramas del juego' if self._automatic else 'Desactivada')
            return
        row = {k: (None if isinstance(v, (int, float)) and not math.isfinite(v) else v)
               for k, v in sample.items() if k != 'frames'}
        self._history.append(row)
        frames = [dict(time=t, ms=ms) for t, ms in sample.get('frames', [])
                  if all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in (t, ms))
                  and 0 < ms < 10000 and now - 30 <= t <= now + .1]
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
        self._detect_stutter(frames, now, sample.get('game', False) is True)

    def _start_capture(self, mark, details):
        now = time.monotonic()
        self._pending = dict(mark=mark, until=mark+15, wall=time.time()-(now-mark),
                             name=self._history[-1]['name'], samples=list(self._history),
                             frames=list(self._frames), truncated=False,
                             trigger=dict(kind='automatic', **details))
        self._auto_last_capture = now
        self._message = 'Pico detectado automáticamente. Guardando 15 segundos posteriores; puedes seguir jugando.'
        self._overlay.setCaptureStatus('Tirón detectado · guardando')
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
                   trigger=pending['trigger'],
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
            self._pdf = ''
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
                trigger = row.get('trigger', {})
                automatic = trigger.get('kind') == 'automatic'
                doc.paragraph(row['label'] + (' · Detectado automáticamente' if automatic else ' · Marcado manualmente'), size=9, bold=True)
                if trigger.get('kind') == 'automatic':
                    doc.paragraph('Se observó una imagen que tardó ' + _number(trigger.get('frameMs'), ' ms') +
                             ', frente a un tiempo habitual cercano a ' + _number(trigger.get('baselineMs'), ' ms') +
                             '.', size=9)
                doc.note('Cada punto mide cuánto tardó una imagen del juego (ms). Los picos pueden sentirse '
                         'como tirones. Mediana: tiempo habitual. P99: el 99 % de las imágenes tardó ese tiempo o menos.')
                doc.cards([('Mediana', _number(summary['median'], ' ms'), 'tiempo por fotograma'),
                           ('P99', _number(summary['p99'], ' ms'), 'percentil 99'),
                           ('Pico', _number(summary['maximum'], ' ms'), 'máximo observado'),
                           ('Fotogramas', str(summary['count']), 'intervalos registrados')])
                doc.section('Frametime alrededor del marcador')
                doc.line_chart(row['frames'], marker=0, marker_label='Pico detectado' if automatic else 'Marcador manual', height=145)
                doc.table([('Antes / después del marcador', f"{row['preSeconds']} s / {row['postSeconds']} s"),
                           ('Estado del registro', 'Parcial' if row['partial'] else 'Completo'),
                           ('Intervalos lentos', str(summary['slow'])),
                           ('Referencia de intervalos lentos', _number(summary['threshold'], ' ms'))])
                if row['note']:
                    doc.note(row['note'])
                doc.section('Lecturas cercanas al marcador')
                near = min(row['samples'], key=lambda r: abs(r['time'])) if row['samples'] else {}
                doc.table([(label, _number(near.get(key), suffix)) for key, label, suffix in
                           [('cpu', 'Uso CPU', ' %'), ('gpu', 'Uso GPU', ' %'), ('ram', 'RAM ocupada', ' %'),
                            ('cpuTemp', 'Temperatura CPU', ' °C'), ('gpuTemp', 'Temperatura GPU', ' °C'),
                            ('gpuMemoryUsed', 'VRAM usada', ' GiB'), ('cpuClock', 'Frecuencia CPU', ' GHz')]])
                doc.paragraph('Fuente de frecuencia CPU: '+str(near.get('cpuClockSource') or 'N/A'), size=8)
                doc.paragraph('Un pico puede coincidir con un tirón o una carga del juego; no confirma su causa ni una avería. '
                              'La línea resume los picos y el archivo local conserva los intervalos originales. '
                              'N/A significa que no hubo una lectura disponible.', size=8)
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
