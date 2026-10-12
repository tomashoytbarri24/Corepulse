"""Fallback de compatibilidad para temperatura CPU real.

V381 conserva LibreHardwareMonitor oficial como proveedor principal. Si ese
motor enumera la CPU pero no entrega una temperatura válida, se consulta en un
subproceso limpio el mismo paquete HardwareMonitor usado por bases históricas
de CorePulse. El subproceso evita conflictos entre dos versiones de la misma
assembly .NET cargadas en un único proceso.

REAL_OR_NA sigue siendo obligatorio: sólo se acepta una lectura física real y
trazable; 0 °C, valores fuera de rango, timeouts o errores producen None.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from typing import Any

_LOCK = threading.Lock()
_CACHE: dict[str, Any] = {"at": 0.0, "result": None}
VALID_CACHE_SECONDS = 2.5
EMPTY_CACHE_SECONDS = 8.0


def _valid_temperature(value: Any) -> float | None:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    if not (5.0 <= value <= 115.0):
        return None
    return round(value, 1)


def _helper_path() -> Path:
    return Path(__file__).resolve().parents[1] / "tools" / "cpu_temp_package_probe.py"


def _creationflags() -> int:
    return int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0


def query_packaged_cpu_temperature(*, force: bool = False, timeout: float = 5.0) -> dict[str, Any] | None:
    """Obtiene una lectura CPU real desde el proveedor histórico empaquetado."""
    if os.name != "nt":
        return None
    now = time.monotonic()
    with _LOCK:
        previous = _CACHE.get("result")
        age = now - float(_CACHE.get("at") or 0.0)
        ttl = VALID_CACHE_SECONDS if previous else EMPTY_CACHE_SECONDS
        if not force and age < ttl:
            return dict(previous) if isinstance(previous, dict) else None

        helper = _helper_path()
        if not helper.is_file():
            _CACHE.update(at=now, result=None)
            return None
        try:
            proc = subprocess.run(
                [sys.executable, str(helper), "--json-only"],
                cwd=str(helper.parents[1]),
                capture_output=True,
                text=True,
                timeout=float(timeout),
                creationflags=_creationflags(),
                check=False,
            )
            lines = [line.strip() for line in (proc.stdout or "").splitlines() if line.strip()]
            payload = json.loads(lines[-1]) if lines else {}
            value = _valid_temperature(payload.get("value"))
            if proc.returncode != 0 or value is None:
                _CACHE.update(at=time.monotonic(), result=None)
                return None
            result = {
                "value": value,
                "source": "LibreHardwareMonitorLib (HardwareMonitor compatibility subprocess)",
                "sensor": str(payload.get("sensor") or "CPU temperature"),
                "hardware": str(payload.get("hardware") or "CPU"),
                "identifier": payload.get("identifier"),
                "timestamp": payload.get("timestamp") or time.time(),
                "fallback": True,
                "compatibility_path": "V362 HardwareMonitor package",
            }
            _CACHE.update(at=time.monotonic(), result=result)
            return dict(result)
        except Exception:
            _CACHE.update(at=time.monotonic(), result=None)
            return None
