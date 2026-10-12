"""Integridad y reparación manual de Windows con DISM/SFC.

Referencia de contratos: CorePulse V485, windows_repair.py. No copiar su
infraestructura obsoleta. REGLAS: REAL_OR_NA, diagnóstico explícito y
reparación sólo con consentimiento/elevación; salida y logs reales.
"""
from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime
import ctypes
import json
import locale
import os
from pathlib import Path
import shutil
import subprocess
import time

from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot

# Comandos cerrados; nunca aceptar parámetros provenientes de QML.
OPERATIONS = {
    "diagnostic": (
        ("dism_checkhealth", "DISM · Comprobación rápida", ("dism.exe", "/Online", "/Cleanup-Image", "/CheckHealth"), 180),
        ("dism_scanhealth", "DISM · Análisis completo", ("dism.exe", "/Online", "/Cleanup-Image", "/ScanHealth"), 2400),
        ("sfc_verifyonly", "SFC · Verificación", ("sfc.exe", "/verifyonly"), 2400),
    ),
    "repair": (
        ("dism_restorehealth", "DISM · Reparación de imagen", ("dism.exe", "/Online", "/Cleanup-Image", "/RestoreHealth"), 4800),
        ("sfc_scannow", "SFC · Reparación de archivos", ("sfc.exe", "/scannow"), 4800),
        ("dism_post_checkhealth", "DISM · Comprobación final", ("dism.exe", "/Online", "/Cleanup-Image", "/CheckHealth"), 180),
    ),
}


def has_admin_rights():
    if os.name != "nt":
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


def classify_integrity(step_key, returncode, output):
    """Nunca confundir un código 0 con ausencia de corrupción/reparación."""
    if returncode is None:
        return "ERROR", "Windows no devolvió un resultado válido."
    if returncode != 0:
        return "ERROR", f"Windows devolvió el código {returncode}."
    text = " ".join(str(output or "").lower().split())
    # Frases exactas conocidas del motor antiguo en EN/ES (mayúsculas normalizadas).
    if any(s in text for s in (
        "cannot be repaired", "no se puede reparar", "no se puede reparar el almacén")):
        return "ERROR", "El almacén de componentes no se puede reparar con este procedimiento."
    if any(s in text for s in (
        "unable to fix some of them", "no pudo reparar algunos", "no pudo corregir algunos")):
        return "ATENCION", "SFC encontró archivos que no pudo reparar."
    if any(s in text for s in (
        "successfully repaired them", "los reparó correctamente", "los reparo correctamente")):
        return "REPARADO", "SFC informó que reparó archivos dañados."
    if step_key == "dism_restorehealth" and any(s in text for s in (
        "the restore operation completed successfully", "la operación de restauración se completó correctamente",
        "la operacion de restauracion se completo correctamente")):
        return "COMPLETADO", "DISM completó la restauración de imagen."
    if any(s in text for s in (
        "did not find any integrity violations", "no encontró ninguna infracción de integridad",
        "no encontro ninguna infraccion de integridad", "no encontró infracciones de integridad")):
        return "SIN_DANOS", "SFC no encontró infracciones de integridad."
    if any(s in text for s in (
        "no component store corruption detected", "no se detectó ningún daño en el almacén",
        "no se detecto ningun daño en el almacen", "no se detectó corrupción en el almacén")):
        return "SIN_DANOS", "DISM no detectó corrupción del almacén."
    if any(s in text for s in (
        "component store is repairable", "component store corruption detected",
        "el almacén de componentes se puede reparar", "el almacen de componentes se puede reparar",
        "se detectó corrupción en el almacén", "se detecto corrupcion en el almacen",
        "integrity violations were found", "se encontraron infracciones de integridad")):
        return "ATENCION", "Windows detectó problemas de integridad."
    return "SIN_CLASIFICAR", "El comando terminó, pero su salida no permite asegurar un diagnóstico."


def _run_command(args, timeout):
    """Captura stdout/stderr reales, sin shell ni ejecución silenciosa falsa."""
    exe = shutil.which(args[0])
    if not exe:
        return None, "", f"Windows no encuentra {args[0]}", False
    try:
        proc = subprocess.run(
            [exe, *args[1:]], stdin=subprocess.DEVNULL, capture_output=True,
            encoding=locale.getpreferredencoding(False), errors="replace",
            timeout=timeout, check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return proc.returncode, (proc.stdout or "")[-160000:], (proc.stderr or "")[-24000:], False
    except subprocess.TimeoutExpired as error:
        partial = error.stdout or b""
        if isinstance(partial, bytes):
            partial = partial.decode(locale.getpreferredencoding(False), "replace")
        return None, str(partial)[-24000:], "La operación agotó el tiempo de espera.", True
    except OSError as error:
        return None, "", f"{type(error).__name__}: {error}", False


def _log_path():
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    folder = Path(base) / "CorePulse" / "logs" / "reparacion_windows"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / ("integridad_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".json")


def run_integrity(kind, on_stage=None, on_progress=None):
    """Una operación iniciada por el usuario; ningún comando se ejecuta al entrar."""
    if kind not in OPERATIONS:
        return {"status": "ERROR", "summary": "Operación desconocida.", "steps": [], "logPath": "N/A"}
    if os.name != "nt":
        return {"status": "ERROR", "summary": "Solo disponible en Windows.", "steps": [], "logPath": "N/A"}
    if not has_admin_rights():
        return {"status": "ADMIN", "summary": "Se requieren permisos de administrador para DISM/SFC. Abre CorePulse como administrador.", "steps": [], "logPath": "N/A"}
    started = datetime.now().isoformat(timespec="seconds")
    rows, raw_rows = [], []
    total = len(OPERATIONS[kind])
    if on_progress:
        on_progress(4, "Preparando comprobaciones…")
    for index, (key, label, args, timeout) in enumerate(OPERATIONS[kind], start=1):
        start_pct = max(5, int(((index - 1) / total) * 100))
        done_pct = int((index / total) * 100)
        stage_label = f"{index}/{total} · {label} (Windows está trabajando…)"
        if on_stage:
            on_stage(stage_label)
        if on_progress:
            on_progress(start_pct, stage_label)
        t0 = time.monotonic()
        rc, stdout, stderr, expired = _run_command(args, timeout)
        status, message = classify_integrity(key, rc, stdout + "\n" + stderr)
        if expired:
            status, message = "ERROR", "Tiempo de espera agotado: comprueba el estado de Windows."
        row = {"title": label, "state": status, "message": message,
               "exitCode": rc if rc is not None else "N/A", "seconds": round(time.monotonic() - t0, 1)}
        if on_progress:
            on_progress(done_pct, stage_label)
        rows.append(row)
        raw_rows.append({**row, "command": list(args), "stdout": stdout, "stderr": stderr})
    statuses = [s["state"] for s in rows]
    if "ERROR" in statuses:
        result = "ERROR"
        summary = "Una etapa falló. Comprueba los resultados y el registro local."
    elif "ATENCION" in statuses:
        result = "ATENCION"
        summary = "Windows detectó incidencias que requieren revisión."
    elif "SIN_CLASIFICAR" in statuses or "COMPLETADO" in statuses:
        result = "TERMINADO"
        summary = "Operaciones terminadas. Consulta el detalle: no se puede garantizar que todo esté reparado."
    elif "REPARADO" in statuses:
        result = "REPARADO"
        summary = "SFC confirmó reparaciones. Revisa también los demás resultados."
    elif statuses and all(s == "SIN_DANOS" for s in statuses):
        result = "SIN_DANOS"
        summary = "Windows no informó daños en las verificaciones reconocidas."
    else:
        result = "N/A"
        summary = "Windows no proporcionó resultados concluyentes."
    path = "N/A"
    try:
        output = _log_path()
        payload = {"kind": kind, "started": started, "finished": datetime.now().isoformat(timespec="seconds"),
                   "state": result, "results": raw_rows}
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        path = str(output)
    except OSError:
        pass
    return {"status": result, "summary": summary, "steps": rows, "logPath": path, "progress": 100}


class RepairHealth(QObject):
    changed = Signal()
    stage = Signal(str)
    progress = Signal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._closed = False
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="corepulse-windows-repair")
        self._future: Future | None = None
        self._data = {"busy": False, "status": "N/A", "summary": "Sin comprobaciones ejecutadas.",
                      "stage": "", "steps": [], "kind": "", "logPath": "N/A", "isAdmin": has_admin_rights(), "progress": 0}
        self.stage.connect(self._set_stage)
        self.progress.connect(self._set_progress)
        self._poll = QTimer(self)
        self._poll.setInterval(250)
        self._poll.timeout.connect(self._finish_if_ready)

    @Property("QVariantMap", notify=changed)
    def data(self):
        return self._data

    @Slot(str)
    def _set_stage(self, label):
        if not self._closed and self._future is not None:
            self._data = {**self._data, "stage": label}
            self.changed.emit()

    @Slot(int, str)
    def _set_progress(self, value, label):
        if not self._closed and self._future is not None:
            self._data = {**self._data, "progress": max(0, min(100, int(value))), "stage": str(label or self._data.get("stage") or "Windows está trabajando…")}
            self.changed.emit()

    @Slot(str)
    def start(self, kind):
        if self._closed or self._future is not None or kind not in OPERATIONS:
            return
        if not has_admin_rights():
            self._data = {**self._data, "status": "ADMIN", "summary": "Abre CorePulse como administrador para ejecutar DISM/SFC.", "isAdmin": False, "progress": 0}
            self.changed.emit()
            return
        self._data = {"busy": True, "status": "EN_CURSO", "summary": "Windows está ejecutando los comandos…",
                      "stage": "Preparando comprobaciones…", "steps": [], "kind": kind,
                      "logPath": "N/A", "isAdmin": True, "progress": 4}
        self.changed.emit()
        self._future = self._pool.submit(run_integrity, kind, self.stage.emit, self.progress.emit)
        self._poll.start()

    def _finish_if_ready(self):
        if self._closed or self._future is None or not self._future.done():
            return
        try:
            result = self._future.result()
        except Exception as error:
            result = {"status": "ERROR", "summary": f"Error inesperado: {type(error).__name__}",
                      "steps": [], "logPath": "N/A"}
        self._future = None
        self._poll.stop()
        self._data = {**self._data, **result, "busy": False, "stage": self._data.get("stage", ""), "progress": result.get("progress", 100)}
        self.changed.emit()

    @Slot()
    def close(self):
        self._closed = True
        self._poll.stop()
        self._pool.shutdown(wait=False, cancel_futures=True)
