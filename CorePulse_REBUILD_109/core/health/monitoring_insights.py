"""Persistencia local de tendencias y transiciones de alertas verificadas."""
from __future__ import annotations

from datetime import datetime, timezone
import math
import os
import psutil
import re
from pathlib import Path
import sqlite3
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET

from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot


def _database_path():
    local = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
    return local / "CorePulse" / "rebuild" / "monitoring_history.sqlite3"


def _valid_metric(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) and 0 <= number <= 100 else None


# Una sesion es un arranque del nucleo de Windows, no una apertura de CorePulse.
# Inicio rapido e hibernacion pueden conservar ese arranque entre encendidos.
RETENTION_DAYS = 90
CHART_POINT_LIMIT = 480
# psutil puede devolver la misma hora de arranque con diferencia de 1-2 s.
BOOT_TOLERANCE_SECONDS = 10


def _windows_boot_session(now=None, boot=None):
    """Identidad estable por arranque; nunca crea una sesion de Windows falsa."""
    now = time.time() if now is None else now
    try:
        boot = psutil.boot_time() if boot is None else boot
        if not isinstance(boot, (int, float)) or not math.isfinite(boot) or boot < 946684800 or boot > now + 60:
            return None, None
        rounded = int(round(boot))
        return f"winboot:{rounded}", float(rounded)
    except (OSError, RuntimeError, ValueError, AttributeError):
        return None, None


def _windows_shutdown_events():
    """Lee marcas de inicio/apagado registradas por Windows, no las estima.

    Kernel-General 12 = Windows inició; 13 y EventLog 6006 = inicio de apagado.
    La marca puede preceder unos segundos al corte eléctrico efectivo.
    Sin esos eventos el cierre permanece N/A.
    """
    if sys.platform != "win32":
        return []
    # Consulta acotada, sin privilegios de administrador ni dependencias extra.
    cmd = ["wevtutil.exe", "qe", "System",
           "/q:*[System[(EventID=12 or EventID=13 or EventID=6005 or EventID=6006)]]",
           "/rd:true", "/f:xml", "/c:900"]
    try:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        proc = subprocess.run(cmd, capture_output=True, timeout=12, check=False,
                              creationflags=flags)
        if proc.returncode != 0 or not proc.stdout:
            return []
        # wevtutil entrega varios <Event> contiguos, sin raíz XML común.
        data = proc.stdout
        raw = data.decode("utf-16") if data.startswith((b"\xff\xfe", b"\xfe\xff")) else data.decode("utf-8-sig", errors="replace")
        raw = re.sub(r"<\?xml[^>]*\?>", "", raw).strip("\ufeff \r\n\t")
        root = ET.fromstring("<Events>" + raw + "</Events>")
        ns = {"e": "http://schemas.microsoft.com/win/2004/08/events/event"}
        items = []
        for event in root.findall("e:Event", ns):
            system = event.find("e:System", ns)
            if system is None:
                continue
            eid = system.findtext("e:EventID", default="", namespaces=ns)
            provider = system.find("e:Provider", ns)
            provider_name = (provider.get("Name", "") if provider is not None else "").lower()
            if (eid in ("12", "13") and "kernel-general" not in provider_name) or (eid in ("6005", "6006") and provider_name != "eventlog"):
                continue
            if eid not in ("12", "13", "6005", "6006"):
                continue
            stamp = system.find("e:TimeCreated", ns)
            raw_time = stamp.get("SystemTime", "") if stamp is not None else ""
            if not raw_time:
                continue
            moment = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
            if moment.tzinfo is None:
                moment = moment.replace(tzinfo=timezone.utc)
            items.append((moment.timestamp(), eid))
        return sorted(set(items))
    except (OSError, ValueError, ET.ParseError, subprocess.TimeoutExpired):
        return []


def _shutdown_for_boot(boot_ts, next_boot_ts, events):
    """Primera secuencia verificable de apagado del arranque seleccionado."""
    candidates = [(ts, eid) for ts, eid in events
                  if eid in ("13", "6006") and isinstance(ts, (int, float)) and boot_ts + 10 < ts
                  and (next_boot_ts is None or ts < next_boot_ts)]
    if not candidates:
        return None, None
    # Preferir la secuencia de Kernel-General 13, con 6006 de esa misma parada.
    # El servicio EventLog puede pararse por otras causas; evitar falsas horas.
    kernel = sorted((ts for ts, eid in candidates if eid == "13"))
    first_ts = kernel[0] if kernel else min(ts for ts, _ in candidates)
    close = [(ts, eid) for ts, eid in candidates if first_ts <= ts <= first_ts + 90]
    stamp, event_id = max(close, key=lambda item: item[0])
    return stamp, event_id


def _merge_nearby_boot_sessions(db, current_id, current_boot):
    """Unifica duplicados por redondeo de 1-2 segundos sin borrar las muestras."""
    rows = db.execute("SELECT id,boot_ts,first_seen,last_seen,end_ts,end_source "
                      "FROM windows_sessions ORDER BY boot_ts, first_seen").fetchall()
    canonicals = []
    for row in rows:
        sid, boot, first, last, end_ts, end_source = row
        matching = next((item for item in canonicals
                         if abs(float(boot) - float(item[1])) <= BOOT_TOLERANCE_SECONDS), None)
        if matching is None:
            canonicals.append(row)
        else:
            canonical_id = matching[0]
            db.execute("UPDATE samples SET session_id=? WHERE session_id=?", (canonical_id, sid))
            db.execute("UPDATE windows_sessions SET first_seen=MIN(first_seen,?), "
                       "last_seen=MAX(last_seen,?), "
                       "end_ts=COALESCE(end_ts,?), end_source=COALESCE(end_source,?) WHERE id=?",
                       (first, last, end_ts, end_source, canonical_id))
            db.execute("DELETE FROM windows_sessions WHERE id=?", (sid,))
    if current_id is None or current_boot is None:
        return current_id, current_boot
    # Un inicio de CorePulse nunca crea una sesión nueva si el arranque coincide.
    matched = next((row for row in canonicals
                    if abs(float(current_boot) - float(row[1])) <= BOOT_TOLERANCE_SECONDS), None)
    return (matched[0], float(matched[1])) if matched else (current_id, current_boot)


def _thin_real_samples(rows, limit=CHART_POINT_LIMIT):
    """Reduce puntos para QML eligiendo lecturas reales, jamas interpoladas."""
    if len(rows) <= limit:
        return [dict(row) for row in rows]
    step = math.ceil((len(rows) - 1) / (limit - 1))
    indices = list(range(0, len(rows), step))
    if indices[-1] != len(rows) - 1:
        indices.append(len(rows) - 1)
    return [dict(rows[i]) for i in indices]


class MonitoringInsights(QObject):
    changed = Signal()
    shutdownEventsReady = Signal(object)

    def __init__(self, telemetry, system_health, parent=None):
        super().__init__(parent)
        self.telemetry = telemetry
        self.system_health = system_health
        self.path = _database_path()
        self._closed = False
        self._suppressed_alerts = {}
        self._session_id, self._boot_ts = _windows_boot_session()
        self._registered_boot = None
        self._selected_session_id = ""
        self._comparison_session_id = ""
        self._revision = 0
        self._cached_timestamp = None
        self._cached_sessions = []
        self._cached_samples = {}
        self._alert_history_status = ""
        self._data = {"samples": [], "comparisonSamples": [], "sessions": [],
                      "selectedSessionId": "", "comparisonSessionId": "",
                      "events": [], "active": [], "lastUpdate": "N/A",
                      "source": "N/A", "status": "Sin muestras"}
        self._ensure_schema()
        self.shutdownEventsReady.connect(self._apply_shutdown_events)
        self._timer = QTimer(self)
        self._timer.setInterval(30_000)
        self._timer.timeout.connect(self._record)
        self._timer.start()
        self.telemetry.metricsChanged.connect(self._record_if_due)
        self.system_health.changed.connect(self._record_alert_transitions)
        self._record(force=True)
        if sys.platform == "win32":
            threading.Thread(target=self._read_shutdown_events, daemon=True).start()

    @Property("QVariantMap", notify=changed)
    def data(self):
        return self._data

    def _connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(str(self.path), timeout=5)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    def _ensure_schema(self):
        with self._connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS samples (ts REAL PRIMARY KEY, cpu REAL, gpu REAL, ram REAL, disk REAL)")
            db.execute("CREATE TABLE IF NOT EXISTS alert_events (id INTEGER PRIMARY KEY, ts REAL NOT NULL, key TEXT NOT NULL, title TEXT NOT NULL, state TEXT NOT NULL, value TEXT NOT NULL, detail TEXT NOT NULL, source TEXT NOT NULL)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_alert_events_ts ON alert_events(ts DESC)")
            # Migracion in-place: las muestras previas quedan sin identificador verificable.
            columns = {row[1] for row in db.execute("PRAGMA table_info(samples)")}
            if "session_id" not in columns:
                db.execute("ALTER TABLE samples ADD COLUMN session_id TEXT")
            db.execute("CREATE TABLE IF NOT EXISTS windows_sessions (id TEXT PRIMARY KEY, boot_ts REAL NOT NULL, first_seen REAL NOT NULL, last_seen REAL NOT NULL)")
            session_columns = {row[1] for row in db.execute("PRAGMA table_info(windows_sessions)")}
            if "end_ts" not in session_columns:
                db.execute("ALTER TABLE windows_sessions ADD COLUMN end_ts REAL")
            if "end_source" not in session_columns:
                db.execute("ALTER TABLE windows_sessions ADD COLUMN end_source TEXT")
            self._session_id, self._boot_ts = _merge_nearby_boot_sessions(db, self._session_id, self._boot_ts)
            db.execute("CREATE INDEX IF NOT EXISTS idx_samples_session_ts ON samples(session_id,ts)")

    def _adopt_registered_boot(self, db, registered_boot):
        """Vincula muestras recientes al arranque EventLog sin perder historia previa."""
        if not (946684800 < registered_boot <= time.time() + 60):
            return
        # Si el evento 12 / 6005 está dentro de 10 s del dato de psutil,
        # conservar el ID para evitar cambios innecesarios.
        if self._boot_ts is not None and abs(registered_boot - self._boot_ts) <= BOOT_TOLERANCE_SECONDS:
            return
        existing = db.execute("SELECT id,boot_ts FROM windows_sessions "
                              "WHERE ABS(boot_ts - ?) <= ? ORDER BY first_seen LIMIT 1",
                              (registered_boot, BOOT_TOLERANCE_SECONDS)).fetchone()
        session_id = existing[0] if existing else f"winboot:{int(round(registered_boot))}"
        first_row = db.execute("SELECT MIN(ts),MAX(ts) FROM samples WHERE session_id=? AND ts>=?",
                               (self._session_id, registered_boot)).fetchone()
        if first_row is None or first_row[0] is None:
            return
        previous_id = self._session_id
        db.execute("INSERT INTO windows_sessions(id,boot_ts,first_seen,last_seen) VALUES(?,?,?,?) "
                   "ON CONFLICT(id) DO UPDATE SET first_seen=MIN(first_seen,excluded.first_seen), "
                   "last_seen=MAX(last_seen,excluded.last_seen)",
                   (session_id, registered_boot, first_row[0], first_row[1]))
        db.execute("UPDATE samples SET session_id=? WHERE session_id=? AND ts>=?",
                   (session_id, previous_id, registered_boot))
        if previous_id != session_id:
            prev_span = db.execute("SELECT MIN(ts),MAX(ts) FROM samples WHERE session_id=?", (previous_id,)).fetchone()
            if prev_span[0] is None:
                db.execute("DELETE FROM windows_sessions WHERE id=?", (previous_id,))
            else:
                db.execute("UPDATE windows_sessions SET first_seen=?,last_seen=? WHERE id=?",
                           (prev_span[0], prev_span[1], previous_id))
            if self._selected_session_id == previous_id:
                self._selected_session_id = session_id
        self._session_id = session_id
        self._boot_ts = registered_boot

    def _read_shutdown_events(self):
        records = _windows_shutdown_events()
        if not self._closed:
            self.shutdownEventsReady.emit(records)

    def _apply_shutdown_events(self, records):
        if self._closed or not records:
            return
        try:
            with self._connect() as db:
                # Usar el último arranque de Windows registrado, incluso cuando
                # Inicio rápido conserva psutil.boot_time() entre encendidos.
                starts = sorted(ts for ts, eid in records if eid == "12")
                if not starts:
                    starts = sorted(ts for ts, eid in records if eid == "6005")
                if starts:
                    self._registered_boot = starts[-1]
                    self._adopt_registered_boot(db, self._registered_boot)
                sessions = db.execute("SELECT id,boot_ts FROM windows_sessions "
                                      "ORDER BY boot_ts").fetchall()
                for index, (sid, boot) in enumerate(sessions):
                    if sid == self._session_id:
                        continue  # El arranque vigente NO ha terminado.
                    next_boot = sessions[index + 1][1] if index + 1 < len(sessions) else None
                    close_ts, source = _shutdown_for_boot(boot, next_boot, records)
                    if close_ts is not None:
                        db.execute("UPDATE windows_sessions SET end_ts=?,end_source=? WHERE id=?",
                                   (close_ts, source, sid))
            self._cached_timestamp = None
            self._publish()
        except (sqlite3.Error, OSError):
            return

    def _current_checks(self):
        summary = getattr(self.system_health, "data", {}) or {}
        checks = summary.get("checks") if isinstance(summary, dict) else []
        return [item for item in checks or [] if isinstance(item, dict)]

    def _record_alert_transitions(self, *_args):
        if self._closed:
            return
        now = time.time()
        active = {}
        for check in self._current_checks():
            state = str(check.get("state") or "").lower()
            if state not in ("critical", "attention"):
                continue
            key = str(check.get("key") or check.get("title") or "unknown")[:120]
            active[key] = check
        try:
            with self._connect() as db:
                rows = db.execute("SELECT key, title, state, value, detail, source FROM alert_events WHERE state IN ('critical','attention') AND id IN (SELECT MAX(id) FROM alert_events GROUP BY key)").fetchall()
                previous = {row[0]: row for row in rows}
                for key in list(self._suppressed_alerts):
                    if key not in active:
                        self._suppressed_alerts.pop(key, None)
                for key, check in active.items():
                    state = str(check.get("state") or "attention").lower()
                    title = str(check.get("title") or key)[:180]
                    value = str(check.get("value") or "N/A")[:180]
                    detail = str(check.get("detail") or "")[:400]
                    source = str(check.get("source") or "N/A")[:180]
                    signature = (title, state, value, detail, source)
                    if self._suppressed_alerts.get(key) == signature:
                        continue
                    self._suppressed_alerts.pop(key, None)
                    old = previous.get(key)
                    if old and old[1:3] == (title, state) and old[3:] == (value, detail, source):
                        continue
                    db.execute("INSERT INTO alert_events(ts,key,title,state,value,detail,source) VALUES(?,?,?,?,?,?,?)",
                               (now, key, title, state, value, detail, source))
                for key, old in previous.items():
                    if key not in active:
                        db.execute("INSERT INTO alert_events(ts,key,title,state,value,detail,source) VALUES(?,?,?,?,?,?,?)",
                                   (now, key, old[1], "resolved", old[3], old[4], old[5]))
                db.execute("DELETE FROM alert_events WHERE ts < ?", (now - 90 * 86400,))
        except (OSError, sqlite3.Error):
            self._data = {**self._data, "status": "Historial local no disponible"}
        self._publish()

    def _record_if_due(self, *_args):
        if not self._closed and time.time() - getattr(self, "_last_sample", 0) >= 30:
            self._record()

    @Slot()
    def _record(self, force=False):
        if self._closed:
            return
        metrics = getattr(self.telemetry, "metrics", {}) or {}
        now = time.time()
        if not force and now - getattr(self, "_last_sample", 0) < 30:
            return
        values = tuple(_valid_metric(metrics.get(key)) for key in
                       ("cpuPercent", "gpuPercent", "ramPercent", "diskPercent"))
        if not any(value is not None for value in values):
            self._publish()
            return
        try:
            with self._connect() as db:
                if self._session_id is not None:
                    db.execute("INSERT INTO windows_sessions(id,boot_ts,first_seen,last_seen) VALUES(?,?,?,?) "
                               "ON CONFLICT(id) DO UPDATE SET first_seen=MIN(first_seen,excluded.first_seen),last_seen=MAX(last_seen,excluded.last_seen)",
                               (self._session_id, self._boot_ts, now, now))
                db.execute("INSERT OR REPLACE INTO samples(ts,cpu,gpu,ram,disk,session_id) VALUES(?,?,?,?,?,?)",
                           (now, *values, self._session_id))
                if self._registered_boot is not None and self._session_id is not None:
                    self._adopt_registered_boot(db, self._registered_boot)
                db.execute("DELETE FROM samples WHERE ts < ?", (now - RETENTION_DAYS * 86400,))
                db.execute("DELETE FROM windows_sessions WHERE id NOT IN (SELECT DISTINCT session_id FROM samples WHERE session_id IS NOT NULL)")
        except (OSError, sqlite3.Error):
            self._data = {**self._data, "status": "Historial local no disponible"}
        else:
            self._last_sample = now
        self._record_alert_transitions()
        self._publish()

    def _session_rows(self, db):
        rows = db.execute("""SELECT s.session_id AS id, m.boot_ts AS bootTs, m.end_ts AS endTs,
                    MIN(s.ts) AS firstSample, MAX(s.ts) AS lastSample, COUNT(*) AS count,
                    AVG(s.cpu) AS cpuAvg, AVG(s.gpu) AS gpuAvg,
                    AVG(s.ram) AS ramAvg, AVG(s.disk) AS diskAvg,
                    MAX(s.cpu) AS cpuMax, MAX(s.gpu) AS gpuMax, MAX(s.ram) AS ramMax
                    FROM samples s JOIN windows_sessions m ON m.id=s.session_id
                    GROUP BY s.session_id ORDER BY lastSample DESC LIMIT 60""").fetchall()
        result = []
        for row in rows:
            entry = dict(row)
            entry["current"] = entry["id"] == self._session_id
            # El apagado se muestra solo cuando existe un evento verificable de Windows.
            entry["recordedSpanSeconds"] = max(0, round(entry["lastSample"] - entry["firstSample"]))
            entry["sinceBootSeconds"] = max(0, round(entry["lastSample"] - entry["bootTs"]))
            result.append(entry)
        return result

    def _session_samples(self, db, session_id):
        if not session_id:
            return []
        info = db.execute("SELECT MIN(ts), MAX(ts), COUNT(*) FROM samples WHERE session_id=?", (session_id,)).fetchone()
        if not info or not info[2]:
            return []
        if info[2] <= CHART_POINT_LIMIT:
            rows = db.execute("SELECT ts,cpu,gpu,ram,disk FROM samples WHERE session_id=? ORDER BY ts", (session_id,)).fetchall()
        else:
            # Buckets temporales: SQLite elige una fila REAL de cada uno, no promedia
            # valores para dibujarlos. Limita el traslado a QML en sesiones largas.
            bucket = max(0.001, (info[1] - info[0]) / (CHART_POINT_LIMIT - 2))
            rows = db.execute("""SELECT s.ts,s.cpu,s.gpu,s.ram,s.disk FROM samples s JOIN
                (SELECT MIN(ts) AS real_ts FROM samples WHERE session_id=?
                 GROUP BY CAST((ts - ?)/? AS INTEGER)
                 UNION SELECT MAX(ts) FROM samples WHERE session_id=?) picked
                 ON picked.real_ts=s.ts ORDER BY s.ts""",
                (session_id, info[0], bucket, session_id)).fetchall()
        return _thin_real_samples(rows)

    def _publish(self):
        try:
            with self._connect() as db:
                db.row_factory = sqlite3.Row
                # Evitar releer miles de muestras en cada cambio de alerta (~1 s).
                database_stamp = db.execute("SELECT MAX(ts) FROM samples").fetchone()[0]
                if database_stamp != self._cached_timestamp:
                    self._cached_timestamp = database_stamp
                    self._cached_sessions = self._session_rows(db)
                    self._cached_samples.clear()
                sessions = self._cached_sessions
                valid = {row["id"] for row in sessions}
                if self._selected_session_id not in valid:
                    self._selected_session_id = self._session_id if self._session_id in valid else (sessions[0]["id"] if sessions else "")
                if self._comparison_session_id not in valid or self._comparison_session_id == self._selected_session_id:
                    self._comparison_session_id = ""
                for session_id in (self._selected_session_id, self._comparison_session_id):
                    if session_id and session_id not in self._cached_samples:
                        self._cached_samples[session_id] = self._session_samples(db, session_id)
                samples = self._cached_samples.get(self._selected_session_id, [])
                comparison_samples = self._cached_samples.get(self._comparison_session_id, [])
                event_rows = db.execute("SELECT ts,key,title,state,value,detail,source FROM alert_events ORDER BY ts DESC LIMIT 300").fetchall()
                latest = db.execute("SELECT MAX(ts) FROM samples WHERE session_id IS NOT NULL").fetchone()[0]
                legacy_count = db.execute("SELECT COUNT(*) FROM samples WHERE session_id IS NULL").fetchone()[0]
            events = [dict(row) for row in event_rows]
            active_rows = [dict(row) for row in self._current_checks()
                           if str(row.get('state') or '').lower() in ('critical', 'attention')]
            stamp = datetime.fromtimestamp(latest).astimezone().strftime("%Y-%m-%d %H:%M:%S") if latest else "N/A"
            selected = next((row for row in sessions if row["id"] == self._selected_session_id), {})
            compared = next((row for row in sessions if row["id"] == self._comparison_session_id), {})
            status = "Listo" if sessions else "Esperando lecturas asociadas a un arranque de Windows"
            if self._session_id is None:
                status = "No se pudo verificar el arranque de Windows: sesiones N/A"
            self._revision += 1
            self._data = {"samples": samples, "comparisonSamples": comparison_samples,
                          "sessions": sessions, "selectedSession": selected, "comparisonSession": compared,
                          "selectedSessionId": self._selected_session_id, "comparisonSessionId": self._comparison_session_id,
                          "legacyCount": legacy_count, "revision": self._revision,
                          "events": events, "active": active_rows,
                          "lastUpdate": stamp, "source": str(self.path), "status": status,
                          "alertHistoryStatus": self._alert_history_status}
        except (OSError, sqlite3.Error, ValueError, OverflowError):
            self._revision += 1
            self._data = {"samples": [], "comparisonSamples": [], "sessions": [],
                          "selectedSessionId": "", "comparisonSessionId": "", "legacyCount": 0,
                          "revision": self._revision, "events": [], "active": [], "lastUpdate": "N/A",
                          "source": "N/A", "status": "Historial local no disponible"}
        self.changed.emit()

    @Slot(str)
    def selectSession(self, session_id):
        if self._closed:
            return
        if any(row.get("id") == session_id for row in self._data.get("sessions", [])):
            self._selected_session_id = session_id
            if self._comparison_session_id == session_id:
                self._comparison_session_id = ""
            self._publish()

    @Slot(str)
    def compareSession(self, session_id):
        if self._closed:
            return
        if session_id != self._selected_session_id and any(row.get("id") == session_id for row in self._data.get("sessions", [])):
            self._comparison_session_id = session_id
            self._publish()

    @Slot()
    def clearComparison(self):
        if not self._closed:
            self._comparison_session_id = ""
            self._publish()

    @Slot()
    def refresh(self):
        self._record(force=True)

    @Slot()
    def clearAlertHistory(self):
        if self._closed:
            return
        current = {}
        for check in self._current_checks():
            state = str(check.get('state') or '').lower()
            if state not in ('critical', 'attention'):
                continue
            key = str(check.get('key') or check.get('title') or 'unknown')[:120]
            current[key] = (str(check.get('title') or key)[:180], state,
                            str(check.get('value') or 'N/A')[:180],
                            str(check.get('detail') or '')[:400],
                            str(check.get('source') or 'N/A')[:180])
        try:
            with self._connect() as db:
                db.execute('DELETE FROM alert_events')
        except (OSError, sqlite3.Error):
            self._data = {**self._data, 'status': 'No se pudo limpiar el historial local'}
            self.changed.emit()
            return
        self._suppressed_alerts = current
        self._alert_history_status = 'Historial de alertas limpiado.'
        self._publish()

    @Slot()
    def close(self):
        self._closed = True
        self._timer.stop()
        for signal, slot in ((self.telemetry.metricsChanged, self._record_if_due),
                             (self.system_health.changed, self._record_alert_transitions)):
            try:
                signal.disconnect(slot)
            except (RuntimeError, TypeError):
                pass
