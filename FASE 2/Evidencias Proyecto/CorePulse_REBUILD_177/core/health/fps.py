"""FPS por eventos Present/ETW del juego en primer plano, sin RTSS.

El ejecutable oficial PresentMon se incluye con CorePulse bajo licencia MIT.
Un valor solo se publica si procede de fotogramas recientes del PID indicado.
"""
from __future__ import annotations

import csv
import codecs
import math
import os
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from collections import deque
from pathlib import Path


PRESENTMON = Path(__file__).resolve().parents[2] / "bin" / "PresentMon-2.5.1-x64.exe"
MAX_FRESHNESS_SECONDS = 2.5
CAPTURE_GUARD = PRESENTMON.with_name('CorePulseCaptureGuard.exe')


def _decoded_lines(stream):
    """PresentMon puede emitir UTF-16 al ejecutarse elevado y sin consola."""
    if not hasattr(stream, 'read'):
        yield from stream
        return
    first = stream.read(4)
    if isinstance(first, str):
        # Compatibilidad con flujos de texto de pruebas/consumidores anteriores.
        text = first + stream.read()
        yield from text.splitlines()
        return
    if first.startswith((b'\xff\xfe', b'\xfe\xff')):
        encoding = 'utf-16'
    elif len(first) >= 4 and first[1] == 0 and first[3] == 0:
        encoding = 'utf-16-le'
    elif len(first) >= 4 and first[0] == 0 and first[2] == 0:
        encoding = 'utf-16-be'
    else:
        encoding = 'utf-8-sig'
    decoder = codecs.getincrementaldecoder(encoding)(errors='replace')
    pending = decoder.decode(first)
    read = getattr(stream, 'read1', stream.read)
    while True:
        while '\n' in pending:
            line, pending = pending.split('\n', 1)
            yield line.rstrip('\r')
        block = read(8192)
        if not block:
            pending += decoder.decode(b'', final=True)
            if pending:
                yield pending.rstrip('\r\n')
            return
        pending += decoder.decode(block)


class PresentMonFPSReader:
    """Captura frametimes ETW del PID indicado y entrega un FPS de 1 segundo."""

    def __init__(self):
        self._lock = threading.Lock()
        self._process = None
        self._pid = 0
        self._samples = deque()
        # Intervalos por fotograma para el historial; independientes de la
        # ventana de un segundo usada por el OSD. Se consumen una sola vez.
        self._frame_intervals = deque(maxlen=20000)
        self._timeline_frames = deque(maxlen=20000)
        self._last = 0.0
        self._last_attempt = 0.0
        self._error = "Esperando un juego en primer plano."
        self._permission_blocked = False
        self._generation = 0
        self._worker = None
        self._orphans_checked = False

    def _guard(self, *args):
        if os.name == 'nt' and CAPTURE_GUARD.is_file():
            try:
                subprocess.run([str(CAPTURE_GUARD), *map(str,args)],stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=4,
                    creationflags=subprocess.CREATE_NO_WINDOW,check=False)
            except (OSError,subprocess.TimeoutExpired):
                pass

    def _dispose_process(self, process):
        try:
            process.terminate()
            process.wait(timeout=1)
        except (OSError,subprocess.TimeoutExpired):
            try:
                process.kill()
                process.wait(timeout=1)
            except (OSError,subprocess.TimeoutExpired):
                pass
        # TerminateProcess does not stop an ETW session; explicitly stop ours.
        self._guard('--stop-owner',os.getpid())

    def _consume(self, process, pid):
        columns = None
        timestamp_offset = None
        try:
            for raw in _decoded_lines(process.stdout):
                try:
                    row = next(csv.reader([raw.lstrip("\ufeff")]))
                except (csv.Error, StopIteration):
                    continue
                if columns is None:
                    names = {name.strip().casefold(): index for index, name in enumerate(row)}
                    if 'processid' in names and 'swapchainaddress' in names and (
                            'msbetweenpresents' in names or 'frametime' in names):
                        columns = names
                        delta_column = names.get('msbetweenpresents', names.get('frametime'))
                    continue
                try:
                    if int(row[columns['processid']]) != pid:
                        continue
                    delta = float(row[delta_column])
                    if not 0 < delta < 10000:
                        continue
                    swapchain = row[columns['swapchainaddress']]
                    present_mode = row[columns['presentmode']] if 'presentmode' in columns else 'N/A'
                    runtime_column = columns.get('presentruntime', columns.get('runtime'))
                    runtime = row[runtime_column] if runtime_column is not None else 'N/A'
                    now = time.monotonic()
                    event_time = now
                    if 'timeinseconds' in columns:
                        seconds = float(row[columns['timeinseconds']])
                        if math.isfinite(seconds) and seconds >= 0:
                            # Anchor PresentMon's event clock to the local
                            # monotonic clock once, preserving frame spacing.
                            if timestamp_offset is None:
                                timestamp_offset = now-seconds
                            event_time = min(now, seconds+timestamp_offset)
                    with self._lock:
                        if self._process is not process or self._pid != pid:
                            return
                        self._samples.append((now, delta, swapchain, present_mode, runtime))
                        self._frame_intervals.append((delta, swapchain))
                        self._timeline_frames.append((event_time, delta, swapchain))
                        self._last = now
                        while self._samples and self._samples[0][0] < now - 1.0:
                            self._samples.popleft()
                except (ValueError, IndexError, KeyError):
                    continue
        except (OSError, UnicodeError) as error:
            with self._lock:
                if self._process is process:
                    self._error = "Error de captura ETW: " + type(error).__name__
        finally:
            with self._lock:
                if self._process is process and process.poll() is not None:
                    if self._error == "Esperando los primeros fotogramas del juego.":
                        self._error = "La captura ETW terminó antes de recibir fotogramas."

    def _read_stderr(self, process):
        try:
            for line in _decoded_lines(process.stderr):
                message = line.strip()
                if not message:
                    continue
                with self._lock:
                    if self._process is process:
                        if "access denied" in message.casefold():
                            self._permission_blocked = True
                            self._error = ("Windows denegó la captura ETW. "
                                           "Se requiere administrador o el grupo Performance Log Users.")
                        elif 'events were lost' in message.casefold():
                            self._error = 'Windows perdió eventos ETW; la captura de fotogramas está incompleta.'
                        elif message.casefold().startswith("warning:"):
                            continue
                        elif not self._permission_blocked:
                            self._error = ("Captura ETW: " + message)[:180]
        except (OSError, UnicodeError):
            pass

    def _start(self, pid):
        self.close()
        with self._lock:
            self._last_attempt = time.monotonic()
            self._pid = pid
            generation = self._generation
            if self._worker is None:
                self._worker = ThreadPoolExecutor(max_workers=1,thread_name_prefix='CorePulse-Capture')
        self._worker.submit(self._launch,pid,generation)

    def _launch(self, pid, generation):
        with self._lock:
            if generation!=self._generation or self._pid!=pid:
                return
        if not self._orphans_checked:
            self._guard('--cleanup-stale')
            self._orphans_checked = True
        self._guard('--stop-owner',os.getpid())
        with self._lock:
            if generation!=self._generation or self._pid!=pid:
                return
        if os.name != "nt" or not PRESENTMON.is_file():
            self._error = "No se encontró el capturador de FPS incluido con CorePulse."
            return
        args = [str(PRESENTMON), "--process_id", str(pid), "--output_stdout", '--v1_metrics',
                "--no_console_stats", "--no_track_gpu", "--no_track_input",
                "--session_name", f"CorePulseOverlay_{os.getpid()}",
                "--stop_existing_session",
                "--terminate_on_proc_exit"]
        try:
            process = subprocess.Popen(args, stdin=subprocess.DEVNULL,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       creationflags=subprocess.CREATE_NO_WINDOW)
        except OSError as error:
            self._error = "No se pudo iniciar la captura ETW: " + type(error).__name__
            return
        with self._lock:
            outdated = generation!=self._generation or self._pid!=pid
            if not outdated:
                self._process = process
                self._samples.clear()
                self._frame_intervals.clear()
                self._last = 0.0
                self._error = "Esperando los primeros fotogramas del juego."
        if outdated:
            self._dispose_process(process)
            return
        threading.Thread(target=self._consume, args=(process, pid),
                         name="CorePulse-ETW-FPS", daemon=True).start()
        threading.Thread(target=self._read_stderr, args=(process,),
                         name="CorePulse-ETW-Errors", daemon=True).start()

    def snapshot(self, pid=None):
        try:
            pid = int(pid or 0)
        except (TypeError, ValueError):
            pid = 0
        if pid <= 0 or pid == os.getpid():
            self.close()
            with self._lock:
                blocked = self._permission_blocked
                reason = self._error if blocked else "Esperando un juego en primer plano."
            return {"quality": "UNAVAILABLE", "fps": None,
                    "reason": reason, "permissionRequired": blocked}
        with self._lock:
            if self._permission_blocked:
                return {"quality": "UNAVAILABLE", "fps": None, "pid": pid,
                        "reason": self._error, "permissionRequired": True}
        if pid != self._pid:
            self._start(pid)
        elif self._process is None or self._process.poll() is not None:
            if time.monotonic() - self._last_attempt >= 8.0:
                self._start(pid)
        with self._lock:
            now = time.monotonic()
            while self._samples and self._samples[0][0] < now - 1.0:
                self._samples.popleft()
            if self._samples and now - self._last <= MAX_FRESHNESS_SECONDS:
                counts = {}
                for sample in self._samples:
                    swapchain = sample[2]
                    counts[swapchain] = counts.get(swapchain, 0) + 1
                primary_swapchain = max(counts, key=counts.get)
                intervals = [sample[1] for sample in self._samples
                             if sample[2] == primary_swapchain]
                latest = next(sample for sample in reversed(self._samples)
                              if sample[2] == primary_swapchain)
                average_ms = sum(intervals) / len(intervals)
                if average_ms > 0:
                    return {"quality": "VALID_ETW", "fps": round(1000.0 / average_ms, 1),
                            "pid": pid, "presentMode": latest[3], "runtime": latest[4],
                            "exclusive": latest[3].startswith("Hardware: Legacy"),
                            "reason": "Fotogramas reales del proceso capturados por ETW."}
            return {"quality": "UNAVAILABLE", "fps": None, "pid": pid,
                    "reason": self._error if self._process is None or self._process.poll() is not None
                    else self._error if self._error != 'Esperando los primeros fotogramas del juego.'
                    else 'Windows aún no entrega fotogramas recientes de este proceso.'}

    def take_timed_frame_intervals(self, pid):
        # Independent subscriber: does not consume the session/1% low buffer.
        with self._lock:
            if pid != self._pid or not self._timeline_frames:
                return []
            rows = list(self._timeline_frames)
            self._timeline_frames.clear()
            counts = {}
            for _, _, chain, *_ in rows:
                counts[chain] = counts.get(chain, 0) + 1
            dominant = max(counts, key=counts.get)
            return [(stamp, delta) for stamp, delta, chain in rows if chain == dominant]

    def take_frame_intervals(self, pid):
        """Entrega intervalos ETW recientes de la cadena dominante del PID.

        No convierte promedios del OSD en fotogramas ni inventa 1 % low.
        """
        with self._lock:
            if pid != self._pid or not self._frame_intervals:
                return []
            rows = list(self._frame_intervals)
            self._frame_intervals.clear()
        counts = {}
        for _, chain in rows:
            counts[chain] = counts.get(chain, 0) + 1
        dominant = max(counts, key=counts.get)
        return [delta for delta, chain in rows if chain == dominant]

    def close(self):
        with self._lock:
            self._generation += 1
            process = self._process
            self._process = None
            self._pid = 0
            self._samples.clear()
            self._frame_intervals.clear()
            self._timeline_frames.clear()
            self._last = 0.0
        if process is not None:
            if self._worker is None:
                self._worker = ThreadPoolExecutor(max_workers=1,thread_name_prefix='CorePulse-Capture')
            self._worker.submit(self._dispose_process,process)

    def shutdown(self):
        self.close()
        if self._worker is not None:
            self._worker.shutdown(wait=False)
