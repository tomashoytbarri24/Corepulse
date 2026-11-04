"""Sesiones de juegos reales, perfiles y coincidencias técnicas locales.

Reutiliza el detector de juegos, la telemetría y la captura ETW del overlay.
Ninguna muestra ausente se convierte en cero ni una coincidencia en causa.
"""
from __future__ import annotations

from array import array
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import gc
import math
import os
from pathlib import Path
import shutil
import sqlite3
import statistics
import subprocess
import time

from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot, QUrl
from PySide6.QtGui import QDesktopServices

from core.runtime import quarantine_database
from .performance import game_profile_key
from .report import _PdfDocument, _output_dir, _number


def _database_path():
    local = Path(os.environ.get('LOCALAPPDATA') or (Path.home() / 'AppData' / 'Local'))
    return local / 'CorePulse' / 'rebuild' / 'game_sessions.sqlite3'


def _real(value, lower=0, upper=100000):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) and lower <= number <= upper else None


def _date(value):
    return datetime.fromtimestamp(float(value)).strftime('%d/%m/%Y %H:%M') if value else 'N/A'


def _duration(seconds):
    minutes, sec = divmod(max(0, int(seconds or 0)), 60)
    hours, minutes = divmod(minutes, 60)
    return f'{hours:02d}:{minutes:02d}:{sec:02d}'


def _one_percent_low(intervals):
    """FPS equivalentes al tiempo medio del 1 % de fotogramas más lentos."""
    if len(intervals) < 300:
        return None
    slowest = sorted((float(x) for x in intervals if 0 < x < 10000), reverse=True)
    if len(slowest) < 300:
        return None
    count = max(1, math.ceil(len(slowest) * .01))
    mean_ms = sum(slowest[:count]) / count
    return round(1000 / mean_ms, 1) if mean_ms > 0 else None


class GameSessionStore:
    """SQLite local: 100 sesiones, muestras cada cinco segundos y eventos."""

    def __init__(self, path=None):
        target = str(path or _database_path())
        if target != ':memory:':
            Path(target).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(target, timeout=2)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY, game_key TEXT NOT NULL, name TEXT NOT NULL,
                source TEXT NOT NULL, executable TEXT NOT NULL, started REAL NOT NULL,
                ended REAL, last_seen REAL NOT NULL, status TEXT NOT NULL,
                active_seconds INTEGER NOT NULL DEFAULT 0, fps_sum REAL NOT NULL DEFAULT 0,
                fps_count INTEGER NOT NULL DEFAULT 0, fps_min REAL, fps_max REAL,
                low_1 REAL, frame_count INTEGER NOT NULL DEFAULT 0,
                cpu_peak REAL, gpu_peak REAL, plan_name TEXT NOT NULL DEFAULT 'N/A');
            CREATE TABLE IF NOT EXISTS samples (
                id INTEGER PRIMARY KEY, session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                ts REAL NOT NULL, fps REAL, cpu REAL, gpu REAL, ram REAL,
                cpu_temp REAL, gpu_temp REAL);
            CREATE INDEX IF NOT EXISTS samples_session ON samples(session_id, ts);
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY, session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                ts REAL NOT NULL, kind TEXT NOT NULL, title TEXT NOT NULL, detail TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS events_session ON events(session_id, ts);
            CREATE TABLE IF NOT EXISTS profiles (
                game_key TEXT PRIMARY KEY, name TEXT NOT NULL, plan_guid TEXT NOT NULL DEFAULT '',
                corner TEXT NOT NULL DEFAULT 'inherit', temperatures TEXT NOT NULL DEFAULT 'inherit');
        ''')
        self.db.execute("UPDATE sessions SET status='interrumpida', ended=last_seen WHERE status='en curso'")
        self.db.commit()

    def profiles(self):
        return {row['game_key']: dict(row) for row in self.db.execute('SELECT * FROM profiles')}

    def save_profile(self, profile):
        with self.db:
            self.db.execute('''INSERT INTO profiles(game_key,name,plan_guid,corner,temperatures)
                VALUES(:game_key,:name,:plan_guid,:corner,:temperatures)
                ON CONFLICT(game_key) DO UPDATE SET name=excluded.name,
                plan_guid=excluded.plan_guid,corner=excluded.corner,temperatures=excluded.temperatures''', profile)

    def start(self, game, now, plan_name):
        with self.db:
            cur = self.db.execute('''INSERT INTO sessions(game_key,name,source,executable,started,last_seen,status,plan_name)
                VALUES(?,?,?,?,?,?,?,?)''', (game_profile_key(game), str(game.get('name') or '')[:120],
                str(game.get('source') or '')[:50], str(game.get('executable') or '')[:100],
                now, now, 'en curso', plan_name[:100]))
        return cur.lastrowid

    def sample(self, session_id, now, values, aggregates):
        with self.db:
            self.db.execute('''INSERT INTO samples(session_id,ts,fps,cpu,gpu,ram,cpu_temp,gpu_temp)
                VALUES(?,?,?,?,?,?,?,?)''', (session_id, now, values['fps'], values['cpu'],
                values['gpu'], values['ram'], values['cpu_temp'], values['gpu_temp']))
            self.db.execute('''UPDATE sessions SET last_seen=?,active_seconds=?,fps_sum=?,fps_count=?,
                fps_min=?,fps_max=?,frame_count=?,cpu_peak=?,gpu_peak=? WHERE id=?''',
                (now, aggregates['active_seconds'], aggregates['fps_sum'], aggregates['fps_count'],
                 aggregates['fps_min'], aggregates['fps_max'], aggregates['frame_count'],
                 aggregates['cpu_peak'], aggregates['gpu_peak'], session_id))

    def event(self, session_id, ts, kind, title, detail):
        with self.db:
            self.db.execute('INSERT INTO events(session_id,ts,kind,title,detail) VALUES(?,?,?,?,?)',
                            (session_id, ts, kind, title[:100], detail[:250]))

    def finish(self, session_id, now, low_1, frame_count):
        with self.db:
            self.db.execute("UPDATE sessions SET ended=?,last_seen=?,status='finalizada',low_1=?,frame_count=? WHERE id=?",
                            (now, now, low_1, frame_count, session_id))
            self.db.execute('''DELETE FROM sessions WHERE id NOT IN
                (SELECT id FROM sessions ORDER BY started DESC LIMIT 100)''')

    def summaries(self):
        return [self._summary(row) for row in self.db.execute(
            'SELECT * FROM sessions ORDER BY started DESC LIMIT 30')]

    @staticmethod
    def _summary(row):
        item = dict(row)
        item['averageFps'] = round(item['fps_sum'] / item['fps_count'], 1) if item['fps_count'] else None
        item['duration'] = _duration((item['ended'] or item['last_seen']) - item['started'])
        item['startedLabel'] = _date(item['started'])
        return item

    def detail(self, session_id):
        row = self.db.execute('SELECT * FROM sessions WHERE id=?', (session_id,)).fetchone()
        if row is None:
            return {}
        result = self._summary(row)
        result['samples'] = [dict(sample) for sample in self.db.execute(
            'SELECT ts,fps,cpu,gpu,ram,cpu_temp,gpu_temp FROM samples WHERE session_id=? ORDER BY ts', (session_id,))]
        result['events'] = [dict(event) for event in self.db.execute(
            'SELECT ts,kind,title,detail FROM events WHERE session_id=? ORDER BY ts', (session_id,))]
        return result

    def close(self):
        self.db.close()


def _windows_session_events(started, ended, executable):
    """Consulta tardía y acotada; solo fechas/códigos, nunca mensajes privados."""
    if os.name != 'nt' or not executable or ended <= started:
        return []
    power = shutil.which('powershell.exe') or shutil.which('powershell')
    if not power:
        return []
    exe = executable.replace("'", "''")
    script = ("$start=[DateTimeOffset]::FromUnixTimeSeconds(" + str(int(started)) + ").LocalDateTime;"
              "$end=[DateTimeOffset]::FromUnixTimeSeconds(" + str(int(ended + 10)) + ").LocalDateTime;"
              "$exe='" + exe + "';$rows=@();"
              "$w=@(Get-WinEvent -FilterHashtable @{LogName='System';ProviderName='Microsoft-Windows-WHEA-Logger';StartTime=$start;EndTime=$end} -MaxEvents 30 -ErrorAction SilentlyContinue);"
              "foreach($e in $w){$rows+=@{ts=([DateTimeOffset]$e.TimeCreated).ToUnixTimeSeconds();kind='whea';id=$e.Id}};"
              "$a=@(Get-WinEvent -FilterHashtable @{LogName='Application';ProviderName='Application Error';Id=1000;StartTime=$start;EndTime=$end} -MaxEvents 30 -ErrorAction SilentlyContinue);"
              "foreach($e in $a){if($e.Properties.Count -gt 0 -and [string]$e.Properties[0].Value -ieq $exe){$rows+=@{ts=([DateTimeOffset]$e.TimeCreated).ToUnixTimeSeconds();kind='app';id=$e.Id}}};"
              "ConvertTo-Json -InputObject @($rows) -Compress -Depth 3")
    try:
        result = subprocess.run([power, '-NoLogo', '-NoProfile', '-NonInteractive', '-Command', script],
                                capture_output=True, text=True, encoding='utf-8', errors='replace',
                                timeout=15, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode:
            return []
        import json
        rows = json.loads(result.stdout.lstrip('\ufeff') or '[]')
        return rows if isinstance(rows, list) else []
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return []


class GameSessionsController(QObject):
    changed = Signal()

    def __init__(self, telemetry, performance, overlay, parent=None, database_path=None):
        super().__init__(parent)
        self._telemetry, self._performance, self._overlay = telemetry, performance, overlay
        self._closed = False
        self._error = ''
        # Un historial dañado jamás impide abrir CorePulse. Se aparta para que
        # las sesiones nuevas vuelvan a guardarse; un bloqueo no lo daña.
        self._store = None
        damaged = False
        try:
            self._store = GameSessionStore(database_path)
        except sqlite3.OperationalError as error:
            self._use_temporary_sessions(error)
        except OSError as error:
            self._use_temporary_sessions(error)
        except sqlite3.DatabaseError:
            damaged = True
        if damaged:
            gc.collect()  # Windows no renombra un archivo con conexiones abiertas.
            try:
                moved = quarantine_database(database_path or _database_path())
                self._store = GameSessionStore(database_path)
                self._error = 'El historial estaba dañado; se apartó como ' + moved.name + '.'
            except (sqlite3.DatabaseError, OSError) as error:
                self._use_temporary_sessions(error)
        self._profiles = self._store.profiles()
        self._performance.setGamePlanProfiles({key: row['plan_guid'] for key, row in self._profiles.items()})
        self._active = None
        self._frames = array('f')
        self._frame_count = 0
        self._frame_overflow = False
        self._fps_recent = []
        self._last_drop = 0.0
        self._drop_streak = 0
        self._heat = {'cpu': [0.0, False], 'gpu': [0.0, False]}
        self._missing_since = 0.0
        self._last_tick = time.time()
        self._last_sample = 0.0
        self._last_values = None
        self._selected_id = 0
        self._comparison_id = 0
        self._profile_key = ''
        self._pdf_path = ''
        self._event_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='corepulse-game-events')
        self._event_futures = []
        self._data = {}
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)
        self._performance.startGameWatch('game-sessions')
        self._performance.changed.connect(self._refresh_view)
        self._timer.start()
        self._refresh_view()

    def _use_temporary_sessions(self, error):
        self._store = GameSessionStore(':memory:')
        self._error = 'Historial persistente no disponible (' + type(error).__name__ + '). Sesiones temporales.'

    @Property('QVariantMap', notify=changed)
    def data(self):
        return self._data

    def _choose_game(self):
        state = self._performance.data or {}
        games = [row for row in (state.get('probableGames') or [])
                 if isinstance(row, dict) and row.get('active') and game_profile_key(row)]
        target = int((self._overlay.data or {}).get('targetPid') or 0)
        for row in games:
            if target and row.get('pid') == target:
                return row
        if self._active:
            for row in games:
                if row.get('pid') == self._active['pid']:
                    return row
        return games[0] if games else None

    def _profile_for(self, key):
        return self._profiles.get(key) or {'game_key': key, 'name': '', 'plan_guid': '',
                                           'corner': 'inherit', 'temperatures': 'inherit'}

    def _apply_overlay_profile(self, key):
        profile = self._profile_for(key)
        self._overlay.setDesignGame(key)
        if profile['corner'] == 'inherit' and profile['temperatures'] == 'inherit':
            self._overlay.clearGameProfile()
        else:
            self._overlay.applyGameProfile(profile['corner'], profile['temperatures'])

    def _start(self, game, now):
        key = game_profile_key(game)
        plan = str((self._performance.data or {}).get('activeName') or 'N/A')
        session_id = self._store.start(game, now, plan)
        self._active = {'id': session_id, 'key': key, 'pid': int(game['pid']),
                        'name': game['name'], 'source': game['source'],
                        'executable': game['executable'], 'started': now,
                        'fps_sum': 0.0, 'fps_count': 0, 'fps_min': None, 'fps_max': None,
                        'active_seconds': 0, 'cpu_peak': None, 'gpu_peak': None}
        self._frames = array('f')
        self._frame_count = 0
        self._frame_overflow = False
        self._fps_recent = []
        self._last_drop = 0
        self._drop_streak = 0
        self._heat = {'cpu': [0.0, False], 'gpu': [0.0, False]}
        self._last_sample = 0.0
        self._last_values = None
        self._missing_since = 0.0
        self._selected_id = session_id
        self._profile_key = key
        self._overlay.setFrameHistoryEnabled(True)
        self._apply_overlay_profile(key)
        self._refresh_view()

    def _event(self, now, kind, title, detail):
        if self._active:
            self._store.event(self._active['id'], now, kind, title, detail)

    def _observe(self, now, dt):
        active = self._active
        metrics = self._telemetry.metrics or {}
        overlay = self._overlay.data or {}
        foreground = int(overlay.get('targetPid') or 0) == active['pid']
        if foreground:
            active['active_seconds'] += max(0, min(2, dt))
        fps = (_real(overlay.get('fps'), .1, 2000)
               if foreground and overlay.get('fpsQuality') in ('VALID_HOOK', 'VALID_ETW') else None)
        if fps is not None:
            baseline = statistics.median(self._fps_recent) if len(self._fps_recent) >= 12 else None
            self._drop_streak = self._drop_streak + 1 if baseline and baseline >= 30 and fps < baseline * .55 else 0
            if self._drop_streak >= 2 and now - self._last_drop > 20:
                self._event(now, 'fps', 'Caída de FPS observada',
                            f'{fps:.1f} FPS frente a una mediana reciente de {baseline:.1f} FPS.')
                self._last_drop = now
                self._drop_streak = 0
            self._fps_recent.append(fps)
            self._fps_recent = self._fps_recent[-40:]
            active['fps_sum'] += fps
            active['fps_count'] += 1
            active['fps_min'] = fps if active['fps_min'] is None else min(active['fps_min'], fps)
            active['fps_max'] = fps if active['fps_max'] is None else max(active['fps_max'], fps)
        elif not foreground:
            self._drop_streak = 0
        intervals = self._overlay.takeFrameIntervals(active['pid']) if foreground else []
        if intervals:
            self._frame_count += len(intervals)
            if not self._frame_overflow:
                if len(self._frames) + len(intervals) <= 2_000_000:
                    self._frames.extend(intervals)
                else:
                    self._frames = array('f')
                    self._frame_overflow = True
            median = statistics.median(intervals)
            threshold = max(50.0, median * 2.0)
            slow = [v for v in intervals if v >= threshold]
            if len(slow) >= 3 and now - self._last_drop > 20:
                self._event(now, 'frames', 'Fotogramas lentos',
                            f'{len(slow)} intervalos sobre {threshold:.0f} ms; máximo {max(slow):.1f} ms.')
                self._last_drop = now
        values = {
            'fps': fps, 'cpu': _real(metrics.get('cpuPercent'), 0, 100),
            'gpu': _real(metrics.get('gpuPercent'), 0, 100),
            'ram': _real(metrics.get('ramPercent'), 0, 100),
            'cpu_temp': _real(metrics.get('cpuTemp'), 1, 125),
            'gpu_temp': _real(metrics.get('gpuTemp'), 1, 125),
        }
        self._last_values = values
        for key, threshold, label in (('cpu', 90, 'CPU'), ('gpu', 85, 'GPU')):
            temp = values[key + '_temp']
            if temp is not None:
                active[key + '_peak'] = temp if active[key + '_peak'] is None else max(active[key + '_peak'], temp)
            state = self._heat[key]
            if foreground and temp is not None and temp >= threshold:
                if not state[0]:
                    state[0] = now
                if not state[1] and now - state[0] >= 20:
                    self._event(now, 'thermal', 'Temperatura elevada de ' + label,
                                f'{label} a {temp:.1f} °C durante al menos 20 segundos medidos.')
                    state[1] = True
            else:
                state[0], state[1] = 0.0, False
        if now - self._last_sample >= 5:
            self._store.sample(active['id'], now, values, {**active, 'frame_count': self._frame_count})
            self._last_sample = now
            self._refresh_view()

    def _finish(self, now):
        active = self._active
        if not active:
            return
        self._overlay.setFrameHistoryEnabled(False)
        self._overlay.clearGameProfile()
        self._overlay.setDesignGame('')
        if self._last_values is not None and now > self._last_sample:
            self._store.sample(active['id'], now, self._last_values,
                               {**active, 'frame_count': self._frame_count})
        low = None if self._frame_overflow else _one_percent_low(self._frames)
        self._store.finish(active['id'], now, low, self._frame_count)
        self._active = None
        self._event_futures.append((active['id'], self._event_pool.submit(
            _windows_session_events, active['started'], now, active['executable'])))
        self._refresh_view()

    def _finish_event_queries(self):
        for session_id, future in list(self._event_futures):
            if not future.done():
                continue
            self._event_futures.remove((session_id, future))
            try:
                rows = future.result()
            except Exception:
                rows = []
            for row in rows[:40]:
                if not isinstance(row, dict):
                    continue
                ts = _real(row.get('ts'), 1, 4102444800)
                if ts is None:
                    continue
                if row.get('kind') == 'whea':
                    self._store.event(session_id, ts, 'windows', 'Evento de hardware de Windows',
                                      'WHEA ID ' + str(row.get('id'))[:8] + ' registrado durante la sesión; coincidencia temporal, no causa confirmada.')
                elif row.get('kind') == 'app':
                    self._store.event(session_id, ts, 'windows', 'Cierre de aplicación registrado',
                                      'Application Error ID 1000 para el ejecutable de este juego.')
            if rows:
                self._refresh_view()

    def _tick(self):
        if self._closed:
            return
        now = time.time()
        dt = now - self._last_tick
        self._last_tick = now
        self._finish_event_queries()
        game = self._choose_game()
        if self._active:
            same = game and game_profile_key(game) == self._active['key'] and int(game['pid']) == self._active['pid']
            if not same:
                if not self._missing_since:
                    self._missing_since = now
                if now - self._missing_since >= 5:
                    self._finish(now)
            else:
                self._missing_since = 0.0
                self._observe(now, dt)
        elif game:
            self._start(game, now)

    def _refresh_view(self):
        sessions = self._store.summaries()
        if not self._selected_id and sessions:
            self._selected_id = sessions[0]['id']
        detail = self._store.detail(self._selected_id)
        comparison = self._store.detail(self._comparison_id) if self._comparison_id else {}
        if comparison and (not detail or comparison['game_key'] != detail['game_key'] or
                           comparison['id'] == detail['id']):
            self._comparison_id = 0
            comparison = {}
        choices = {}
        if self._active:
            choices[self._active['key']] = {'key': self._active['key'], 'name': self._active['name']}
        for row in sessions:
            choices.setdefault(row['game_key'], {'key': row['game_key'], 'name': row['name']})
        for key, row in self._profiles.items():
            choices.setdefault(key, {'key': key, 'name': row['name']})
        if not self._profile_key and choices:
            self._profile_key = next(iter(choices))
        self._data = {
            'active': bool(self._active), 'activeName': self._active['name'] if self._active else '',
            'sessions': sessions, 'detail': detail, 'selectedId': self._selected_id,
            'comparison': comparison, 'comparisonId': self._comparison_id,
            'gameChoices': list(choices.values()), 'profileGameKey': self._profile_key,
            'profile': self._profile_for(self._profile_key),
            'plans': (self._performance.data or {}).get('plans') or [],
            'autoPowerStatus': (self._performance.data or {}).get('autoPowerStatus') or '',
            'message': self._error, 'pdfPath': self._pdf_path,
        }
        self.changed.emit()

    @Slot()
    def refresh(self):
        self._performance.refresh()
        self._refresh_view()

    @Slot(int)
    def selectSession(self, session_id):
        self._selected_id = int(session_id)
        self._refresh_view()

    @Slot(int)
    def selectComparison(self, session_id):
        self._comparison_id = int(session_id)
        self._refresh_view()

    @Slot(str)
    def selectProfileGame(self, game_key):
        self._profile_key = str(game_key)
        self._refresh_view()

    @Slot(str, str, str, str)
    def saveProfile(self, game_key, plan_guid, corner, temperatures):
        choice = next((g for g in self._data.get('gameChoices', []) if g['key'] == game_key), None)
        allowed_plans = {p.get('guid') for p in (self._performance.data or {}).get('plans') or []}
        if not choice or (plan_guid and plan_guid not in allowed_plans) or corner not in (
                'inherit', 'top-left', 'top-right', 'bottom-left', 'bottom-right') or temperatures not in (
                'inherit', 'on', 'off'):
            self._error = 'Perfil no guardado: revisa el juego y el plan disponible en Windows.'
            self._refresh_view()
            return
        profile = {'game_key': game_key, 'name': choice['name'], 'plan_guid': plan_guid,
                   'corner': corner, 'temperatures': temperatures}
        try:
            self._store.save_profile(profile)
        except (sqlite3.DatabaseError, OSError):
            self._error = 'No se pudo guardar el perfil local.'
            self._refresh_view()
            return
        self._profiles[game_key] = profile
        self._performance.setGamePlanProfiles({key: row['plan_guid'] for key, row in self._profiles.items()})
        if self._active and self._active['key'] == game_key:
            self._apply_overlay_profile(game_key)
        self._error = 'Perfil guardado. Se aplicará al detectar ese juego y se restaurará al salir.'
        self._refresh_view()

    @Slot(int)
    def exportPdf(self, session_id):
        detail = self._store.detail(int(session_id or self._selected_id))
        if not detail:
            self._error = 'Selecciona una sesión para generar su informe.'
            self._refresh_view()
            return
        folder = _output_dir()
        try:
            folder.mkdir(parents=True, exist_ok=True)
            filename = f"CorePulse_Partida_{int(detail['id'])}_{datetime.now():%Y%m%d_%H%M%S}.pdf"
            path = folder / filename
            doc = _PdfDocument(path, 'Informe de partida', detail['name'][:70])
            try:
                doc.paragraph(detail['name'] + ' · ' + detail['source'], size=11, bold=True)
                doc.cards([
                    ('FPS medios', _number(detail['averageFps'], ' FPS'), 'muestras verificadas'),
                    ('1 % low', _number(detail['low_1'], ' FPS'), 'fotogramas ETW'),
                    ('Duración', detail['duration'], 'proceso observado'),
                    ('Tiempo activo', _duration(detail['active_seconds']), 'en primer plano'),
                ])
                doc.section('Sesión y fuentes')
                doc.table([('Inicio', detail['startedLabel']), ('Estado', detail['status']),
                           ('Origen del juego', detail['source']), ('Plan al iniciar', detail['plan_name']),
                           ('Muestras FPS', str(detail['fps_count'])),
                           ('Fotogramas ETW', str(detail['frame_count'])),
                           ('CPU máxima', _number(detail['cpu_peak'], ' °C')),
                           ('GPU máxima', _number(detail['gpu_peak'], ' °C'))])
                doc.note('El 1 % low se calcula solo con intervalos de fotogramas capturados por ETW. '
                         'Si no hay al menos 300 fotogramas válidos, aparece N/A. Un evento cercano '
                         'a una caída de FPS es una coincidencia temporal, no una causa demostrada.')
                comparison = self._store.detail(self._comparison_id) if self._comparison_id else {}
                if comparison and comparison['game_key'] == detail['game_key'] and comparison['id'] != detail['id']:
                    doc.section('Comparación con otra partida del mismo juego')
                    doc.table([('Partida de referencia', comparison['startedLabel']),
                               ('FPS medios', _number(comparison['averageFps'], ' FPS')),
                               ('1 % low', _number(comparison['low_1'], ' FPS')),
                               ('Duración', comparison['duration'])])
                    if detail['averageFps'] is not None and comparison['averageFps'] is not None:
                        doc.paragraph('Diferencia de FPS medios: ' +
                                      _number(detail['averageFps'] - comparison['averageFps'], ' FPS'))
                if detail['events']:
                    doc.section('Línea de tiempo de incidencias')
                    for event in detail['events'][:30]:
                        doc.paragraph(_date(event['ts']) + ' · ' + event['title'], bold=True, gap=1)
                        doc.paragraph(event['detail'], size=9, gap=7)
                valid = [s['fps'] for s in detail['samples'] if s['fps'] is not None]
                if valid:
                    step = max(1, math.ceil(len(valid) / 4))
                    chunks = [valid[i:i + step] for i in range(0, len(valid), step)][:4]
                    doc.section('Evolución de FPS')
                    doc.bar_chart('Promedios por tramo observado',
                                  [(f'Tramo {i + 1}', sum(chunk) / len(chunk)) for i, chunk in enumerate(chunks)])
            finally:
                doc.finish()
            self._pdf_path = str(path)
            self._error = 'Informe de partida generado.'
        except (OSError, ValueError) as error:
            self._error = 'No se pudo generar el PDF: ' + type(error).__name__
        self._refresh_view()

    @Slot()
    def openLastPdf(self):
        if self._pdf_path and Path(self._pdf_path).is_file():
            QDesktopServices.openUrl(QUrl.fromLocalFile(self._pdf_path))

    @Slot()
    def close(self):
        if self._closed:
            return
        self._timer.stop()
        self._finish(time.time())
        self._closed = True
        self._performance.stopGameWatch('game-sessions')
        self._event_pool.shutdown(wait=False, cancel_futures=True)
        self._store.close()
