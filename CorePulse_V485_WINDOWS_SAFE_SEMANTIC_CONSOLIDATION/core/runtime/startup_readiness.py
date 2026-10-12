"""Preflight de arranque de CorePulse.

El preflight de usuario NO sustituye al self-test de build. En una instalación
final permite abrir CorePulse aunque una capacidad externa no esté disponible,
pero registra con precisión qué subsistema queda N/A.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import ctypes
import importlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import struct
import sys

from core.runtime_paths import (
    executable_root, is_frozen, resource_path, state_path, state_dir,
)

ESSENTIAL_IMPORTS = (
    ("psutil", "psutil"),
    ("customtkinter", "CustomTkinter"),
    ("PIL", "Pillow"),
    ("matplotlib", "Matplotlib"),
    ("platformdirs", "platformdirs"),
    ("fastapi", "FastAPI / CorePulse AI Server"),
    ("uvicorn", "Uvicorn / CorePulse AI Server"),
    ("pydantic", "Pydantic / CorePulse AI Server"),
)

BUNDLED_CAPABILITY_IMPORTS = (
    ("reportlab", "Generación PDF"),
    ("send2trash", "Send2Trash"),
    ("dotenv", "python-dotenv"),
    ("pystray", "Icono de bandeja"),
)

WINDOWS_CAPABILITY_IMPORTS = (
    ("wmi", "WMI"),
    ("win32api", "pywin32"),
    ("clr", "pythonnet"),
)


@dataclass(frozen=True)
class ReadinessItem:
    id: str
    label: str
    status: str
    required: bool
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.status == "OK"


@dataclass
class ReadinessReport:
    generated_at: str
    version: str
    platform: str
    python: str
    architecture: str
    ready: bool
    frozen: bool
    items: list[ReadinessItem]

    def to_dict(self) -> dict:
        data = asdict(self)
        data["errors"] = [asdict(i) for i in self.items if i.required and not i.ok]
        data["warnings"] = [asdict(i) for i in self.items if not i.required and not i.ok]
        return data


def _module_check(name: str) -> tuple[bool, str]:
    try:
        if is_frozen():
            importlib.import_module(name)
            return True, "incluido y cargable desde CorePulse.exe"
        spec = importlib.util.find_spec(name)
        return bool(spec), f"módulo {name}" if spec else f"módulo {name} no instalado"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def _windows_check() -> tuple[bool, str]:
    if platform.system() != "Windows":
        return False, f"{platform.system()} no es plataforma objetivo"
    try:
        ver = sys.getwindowsversion()
        return int(ver.major) >= 10, f"Windows {ver.major}.{ver.minor} build {ver.build}"
    except Exception:
        return True, platform.platform()


def _is_admin() -> bool:
    if platform.system() != "Windows":
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _find_rtss() -> str | None:
    if platform.system() != "Windows":
        return None
    for path in (
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "RivaTuner Statistics Server" / "RTSS.exe",
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "RivaTuner Statistics Server" / "RTSS.exe",
    ):
        if path.is_file():
            return str(path)
    return None


def _find_speedtest() -> str | None:
    found = shutil.which("speedtest.exe") or shutil.which("speedtest")
    if found:
        return found
    for path in (
        resource_path("tools", "speedtest.exe"),
        resource_path("tools", "ookla", "speedtest.exe"),
        executable_root() / "speedtest.exe",
    ):
        if path.is_file():
            return str(path)
    return None


def _probe_hardwaremonitor() -> tuple[bool, str]:
    """Sondea HardwareMonitor sin permitir que pythonnet bloquee el arranque.

    En modo fuente el import se ejecuta en un proceso hijo con timeout. Algunas
    combinaciones de pythonnet/LHM pueden quedar esperando indefinidamente al
    inicializar CLR aunque no exista una excepción visible en la terminal.
    HardwareMonitor es una capacidad opcional: un timeout se reporta como N/A y
    nunca debe secuestrar la pantalla de preparación de CorePulse.
    """
    if not is_frozen():
        code = (
            "import HardwareMonitor; "
            "from HardwareMonitor.Hardware import Computer; "
            "print('COREPULSE_HM_OK')"
        )
        try:
            cp = subprocess.run(
                [sys.executable, '-c', code],
                capture_output=True,
                text=True,
                errors='replace',
                timeout=5,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            )
            if cp.returncode == 0 and 'COREPULSE_HM_OK' in (cp.stdout or ''):
                return True, "HardwareMonitor + LibreHardwareMonitorLib cargados"
            detail = (cp.stderr or cp.stdout or '').strip()
            return False, detail[-500:] if detail else f"proceso de comprobación terminó con código {cp.returncode}"
        except subprocess.TimeoutExpired:
            return False, "TIMEOUT: HardwareMonitor no respondió en 5 s; sensores profundos quedan N/A"
        except Exception as exc:
            return False, f"{type(exc).__name__}: {exc}"
    try:
        import HardwareMonitor  # noqa: F401
        from HardwareMonitor.Hardware import Computer  # noqa: F401
        return True, "HardwareMonitor + LibreHardwareMonitorLib cargados"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def collect_readiness(project_root=None, version: str = "unknown") -> ReadinessReport:
    items: list[ReadinessItem] = []
    win_ok, win_detail = _windows_check()
    items.append(ReadinessItem("windows", "Windows 10/11 x64", "OK" if win_ok else "ERROR", True, win_detail))

    py_ok = sys.version_info >= (3, 12)
    items.append(ReadinessItem(
        "python", "CPython 3.12+ x64 (minor adaptable)", "OK" if py_ok else "ERROR", True,
        ("runtime integrado " if is_frozen() else "") + sys.version.split()[0],
    ))
    bits = struct.calcsize("P") * 8
    items.append(ReadinessItem("runtime_x64", "Runtime x64", "OK" if bits == 64 else "ERROR", True, f"{bits}-bit"))

    for module, label in ESSENTIAL_IMPORTS:
        ok, detail = _module_check(module)
        items.append(ReadinessItem(f"import_{module}", label, "OK" if ok else "ERROR", True, detail))

    for module, label in BUNDLED_CAPABILITY_IMPORTS:
        ok, detail = _module_check(module)
        items.append(ReadinessItem(f"import_{module}", label, "OK" if ok else "N/A", False, detail))

    if platform.system() == "Windows":
        for module, label in WINDOWS_CAPABILITY_IMPORTS:
            ok, detail = _module_check(module)
            items.append(ReadinessItem(f"import_{module}", label, "OK" if ok else "N/A", False, detail))
        hm_ok, hm_detail = _probe_hardwaremonitor()
        items.append(ReadinessItem("hardwaremonitor", "LibreHardwareMonitor", "OK" if hm_ok else "N/A", False, hm_detail))

    try:
        folder = state_dir()
        probe = folder / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        writable, writable_detail = True, str(folder)
    except Exception as exc:
        writable, writable_detail = False, f"{type(exc).__name__}: {exc}"
    items.append(ReadinessItem("runtime_dir", "Estado de usuario escribible", "OK" if writable else "ERROR", True, writable_detail))

    speedtest = _find_speedtest()
    items.append(ReadinessItem("speedtest", "Ookla Speedtest CLI", "OK" if speedtest else "N/A", False, speedtest or "No instalado; se puede instalar desde Red avanzada"))

    rtss = _find_rtss()
    items.append(ReadinessItem("rtss", "RTSS para Overlay/FPS", "OK" if rtss else "N/A", False, rtss or "No detectado; FPS queda REAL_FPS_OR_NA_ONLY"))

    items.append(ReadinessItem("corepulse_ai", "CorePulse AI", "INFO", False, "Runtime local auto-preparable; el diagnóstico determinístico sigue funcionando si el modelo no está disponible"))
    items.append(ReadinessItem("admin", "Administrador", "OK" if _is_admin() else "INFO", False, "No es obligatorio; CorePulse eleva sólo acciones que lo necesitan"))

    ready = all(item.ok for item in items if item.required)
    return ReadinessReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
        version=str(version), platform=platform.platform(), python=sys.version.split()[0],
        architecture=f"{bits}-bit", ready=ready, frozen=is_frozen(), items=items,
    )



def collect_launch_gate(version: str = "unknown") -> ReadinessReport:
    """Gate mínimo para publicar la ventana lo antes posible.

    No importa Matplotlib, WMI, pythonnet, LHM, CorePulse AI, RTSS ni otras
    capacidades opcionales. La auditoría completa continúa en background.
    """
    items: list[ReadinessItem] = []
    win_ok, win_detail = _windows_check()
    items.append(ReadinessItem("windows", "Windows 10/11 x64", "OK" if win_ok else "ERROR", True, win_detail))
    py_ok = sys.version_info >= (3, 12)
    items.append(ReadinessItem("python", "CPython 3.12+ x64 (minor adaptable)", "OK" if py_ok else "ERROR", True, sys.version.split()[0]))
    bits = struct.calcsize("P") * 8
    items.append(ReadinessItem("runtime_x64", "Runtime x64", "OK" if bits == 64 else "ERROR", True, f"{bits}-bit"))
    ready = all(item.ok for item in items if item.required)
    return ReadinessReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
        version=str(version), platform=platform.platform(), python=sys.version.split()[0],
        architecture=f"{bits}-bit", ready=ready, frozen=is_frozen(), items=items,
    )

def persist_readiness(report: ReadinessReport) -> Path | None:
    try:
        path = state_path("startup_readiness.json")
        path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return path
    except Exception:
        return None


def update_first_run_state(version: str) -> tuple[bool, Path | None]:
    try:
        path = state_path("first_run_state.json")
        now = datetime.now(timezone.utc).isoformat()
        previous = {}
        if path.is_file():
            try:
                previous = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                previous = {}
        first = str(previous.get("last_version") or "") != str(version)
        path.write_text(json.dumps({
            "first_launch_at": previous.get("first_launch_at") or now,
            "last_launch_at": now,
            "last_version": str(version),
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        return first, path
    except Exception:
        return False, None


def format_blocking_message(report: ReadinessReport) -> str:
    failed = [i for i in report.items if i.required and not i.ok]
    lines = ["CorePulse no puede iniciar porque el núcleo de ejecución está incompleto.", ""]
    for item in failed[:12]:
        lines.append(f"• {item.label} — {item.detail}" if item.detail else f"• {item.label}")
    lines.append("")
    if report.frozen:
        lines.extend([
            "CorePulse.exe es autocontenido: no instales paquetes Python manualmente.",
            "Reinstala CorePulse o usa una compilación que haya superado el self-test de build.",
        ])
    else:
        lines.append("Cierra y vuelve a abrir CorePulse: el entorno fuente se reparará automáticamente.")
    return "\n".join(lines)


# V482: fusión sin cambios de lógica desde core/runtime/startup_profiler.py
from datetime import datetime, timezone
import json
import os
import threading
import time

_LOCK = threading.RLock()
_T0 = time.perf_counter()
_STAGES: list[dict] = []


def startup_mark(stage: str, **meta) -> dict:
    entry = {
        "stage": str(stage),
        "elapsed_ms": round((time.perf_counter() - _T0) * 1000.0, 3),
        "thread": threading.current_thread().name,
    }
    if meta:
        entry["meta"] = {str(k): v for k, v in meta.items()}
    with _LOCK:
        _STAGES.append(entry)
    return dict(entry)


def startup_snapshot() -> dict:
    with _LOCK:
        stages = [dict(item) for item in _STAGES]
    by_stage = {item["stage"]: item["elapsed_ms"] for item in stages}
    return {
        "schema": "corepulse.startup.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pid": os.getpid(),
        "stages": stages,
        "stage_ms": by_stage,
        "first_frame_ms": by_stage.get("first_frame_idle"),
        "charts_ready_ms": by_stage.get("charts_ready"),
        "services_ready_ms": by_stage.get("services_ready"),
        "first_telemetry_acquired_ms": by_stage.get("first_telemetry_acquired"),
        "first_telemetry_ui_ready_ms": by_stage.get("first_telemetry_ui_ready"),
        "runtime_integrity_ms": by_stage.get("runtime_integrity_ready"),
        "startup_gate_visible_ms": by_stage.get("startup_gate_visible"),
        "startup_gate_complete_ms": by_stage.get("startup_gate_complete"),
        "main_window_revealed_ms": by_stage.get("main_window_revealed"),
    }


def persist_startup_metrics(path=None):
    """Guarda la medición fuera de la ruta crítica del primer frame."""
    try:
        if path is None:
            from core.runtime_paths import state_path
            path = state_path("startup_metrics.json")
        payload = startup_snapshot()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path
    except Exception:
        return None


startup_mark("profiler_loaded")

# V485: implementación consolidada de core/runtime/frozen_selftest.py; conserva las rutas de importación anteriores.
from datetime import datetime, timezone

import ctypes

import importlib

import json

import os

from pathlib import Path

import platform

import shutil

import sqlite3

import struct

import subprocess

import sys

import tempfile

import traceback

from core.runtime_paths import (
    cache_dir, config_dir, data_dir, diagnostics_dir, executable_root, is_frozen,
    log_dir, resource_path, resource_root, state_dir,
)

from core.version import VERSION

def _item(name, critical, ok, detail=""):
    return {"name": name, "critical": bool(critical), "ok": bool(ok), "detail": str(detail or "")}

def _import_check(name, label=None):
    try:
        importlib.import_module(name)
        return _item(label or f"import:{name}", True, True, "OK")
    except Exception as exc:
        return _item(label or f"import:{name}", True, False, f"{type(exc).__name__}: {exc}")

def _selftest_is_admin():
    if os.name != "nt":
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False

def _selftest_find_rtss():
    if os.name != "nt":
        return None
    for path in (
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "RivaTuner Statistics Server" / "RTSS.exe",
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "RivaTuner Statistics Server" / "RTSS.exe",
    ):
        if path.is_file():
            return path
    return None

def _find_pawnio():
    if os.name != "nt":
        return None
    pf = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
    pf86 = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
    system = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    candidates = (
        pf / "PawnIO" / "PawnIO.exe",
        pf86 / "PawnIO" / "PawnIO.exe",
        system / "System32" / "drivers" / "PawnIO.sys",
    )
    for path in candidates:
        if path.is_file():
            return path
    # Consulta rápida del servicio/driver, sin recorrer Program Files completo.
    try:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        proc = subprocess.run(["sc.exe", "query", "PawnIO"], capture_output=True, text=True, timeout=4, creationflags=flags)
        if proc.returncode == 0:
            return Path("PawnIO(service)")
    except Exception:
        pass
    return None

def _same_exe_probe(items):
    out = state_dir() / "selftest_helper_probe.json"
    out.unlink(missing_ok=True)
    if is_frozen():
        cmd = [str(sys.executable), "--corepulse-helper-probe", "--output", str(out)]
    else:
        launcher = resource_path("corepulse_launcher.py")
        cmd = [str(sys.executable), str(launcher), "--corepulse-helper-probe", "--output", str(out)]
    try:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        proc = subprocess.run(cmd, timeout=30, creationflags=flags)
        payload = json.loads(out.read_text(encoding="utf-8")) if out.is_file() else {}
        ok = proc.returncode == 0 and payload.get("ok") is True and payload.get("version") == VERSION
        items.append(_item("same_exe_internal_cli", True, ok, f"returncode={proc.returncode}; output={out}"))
    except Exception as exc:
        items.append(_item("same_exe_internal_cli", True, False, f"{type(exc).__name__}: {exc}"))
    finally:
        out.unlink(missing_ok=True)

def run_self_test(output_path=None) -> tuple[int, dict]:
    items = []
    warnings = []

    items.append(_item("windows", True, platform.system() == "Windows", platform.platform()))
    items.append(_item("frozen_pyinstaller", True, is_frozen(), f"sys.frozen={getattr(sys, 'frozen', False)!r}"))
    items.append(_item("runtime_x64", True, struct.calcsize("P") * 8 == 64, f"{struct.calcsize('P')*8}-bit"))
    items.append(_item("python_runtime", True, sys.version_info[:2] == (3, 12), sys.version.split()[0]))

    # Separación recursos/estado: crítico para instalación y upgrades.
    try:
        rr = resource_root().resolve()
        ed = executable_root().resolve()
        dirs = [data_dir(), state_dir(), diagnostics_dir(), config_dir(), cache_dir(), log_dir()]
        writable = True
        detail = []
        for folder in dirs:
            probe = folder / ".corepulse_selftest_write"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            detail.append(str(folder))
        if is_frozen():
            # Ninguna carpeta mutable debe estar debajo de _internal/resource_root.
            for folder in dirs:
                try:
                    folder.resolve().relative_to(rr)
                    writable = False
                    detail.append(f"ERROR mutable dentro de bundle: {folder}")
                except ValueError:
                    pass
        items.append(_item("appdata_runtime_paths", True, writable, " | ".join(detail)))
    except Exception as exc:
        items.append(_item("appdata_runtime_paths", True, False, f"{type(exc).__name__}: {exc}"))

    required_resources = [
        ("app_icon", resource_path("assets", "CorePulseTaskbar.ico")),
        ("corepulse_icon", resource_path("assets", "CorePulseSymbol.png")),
        ("speedtest_installer", resource_path("Instalar_Speedtest_Ookla.bat")),
        ("ai_model_host", resource_path("CorePulse_AI_Model_Host", "Iniciar_Modelo_CorePulse_AI.bat")),
    ]
    for name, path in required_resources:
        items.append(_item(f"resource:{name}", True, path.is_file(), str(path)))
    # V410: capa visual programática; se valida el compositor, NO un PNG.
    try:
        from gui.workspace_background import render_native_workspace, WorkspaceBackground
        items.append(_item("native_workspace_renderer", True,
                           callable(render_native_workspace) and callable(WorkspaceBackground),
                           "Compositor Tk nativo cargado, sin wallpaper externo"))
    except Exception as exc:
        items.append(_item("native_workspace_renderer", True, False,
                           f"{type(exc).__name__}: {exc}"))

    for mod in (
        "psutil", "customtkinter", "PIL", "matplotlib", "reportlab", "platformdirs",
        "send2trash", "dotenv", "pystray", "wmi", "win32api", "pythoncom",
        "pywintypes", "clr", "pythonnet", "clr_loader",
        "fastapi", "uvicorn", "pydantic", "CorePulse_AI_Server.app.main",
    ):
        items.append(_import_check(mod))

    # HardwareMonitor: el bug concreto de 41b/41c queda convertido en check crítico.
    try:
        import HardwareMonitor  # noqa: F401
        from HardwareMonitor.Hardware import Computer
        items.append(_item("hardwaremonitor_clr_namespace", True, True, "Computer importado"))
        try:
            c = Computer()
            items.append(_item("hardwaremonitor_computer_ctor", True, c is not None, "Computer() creado"))
            # Open() valida que las dependencias CLR se pueden resolver. Una falta de
            # permisos/PawnIO no invalida el bundle; FileNotFound/DllNotFound sí.
            try:
                c.IsCpuEnabled = True
                c.IsGpuEnabled = True
                c.IsMemoryEnabled = True
                c.IsStorageEnabled = True
                c.Open()
                count = len(list(c.Hardware))
                warnings.append({"name": "sensor_open", "ok": True, "detail": f"Hardware enumerado: {count}"})
            except Exception as exc:
                text = f"{type(exc).__name__}: {exc}"
                assembly_broken = any(x in text.lower() for x in ("filenotfound", "dllnotfound", "could not load file", "assembly"))
                if assembly_broken:
                    items.append(_item("hardwaremonitor_open_assemblies", True, False, text))
                else:
                    warnings.append({"name": "sensor_open", "ok": False, "detail": text})
            finally:
                try: c.Close()
                except Exception: pass
        except Exception as exc:
            items.append(_item("hardwaremonitor_computer_ctor", True, False, f"{type(exc).__name__}: {exc}"))
    except Exception as exc:
        items.append(_item("hardwaremonitor_clr_namespace", True, False, f"{type(exc).__name__}: {exc}"))

    # ReportLab real: no basta con importar el paquete.
    try:
        from reportlab.pdfgen import canvas
        pdf = diagnostics_dir() / "selftest_reportlab.pdf"
        c = canvas.Canvas(str(pdf)); c.drawString(20, 20, "CorePulse self-test"); c.save()
        ok = pdf.is_file() and pdf.stat().st_size > 100
        items.append(_item("reportlab_pdf_write", True, ok, str(pdf)))
        pdf.unlink(missing_ok=True)
    except Exception as exc:
        items.append(_item("reportlab_pdf_write", True, False, f"{type(exc).__name__}: {exc}"))

    try:
        db = diagnostics_dir() / "selftest.sqlite3"
        con = sqlite3.connect(db); con.execute("create table if not exists t(v integer)"); con.execute("insert into t values (1)"); con.commit()
        value = con.execute("select count(*) from t").fetchone()[0]; con.close(); db.unlink(missing_ok=True)
        items.append(_item("sqlite_write_read", True, value >= 1, f"rows={value}"))
    except Exception as exc:
        items.append(_item("sqlite_write_read", True, False, f"{type(exc).__name__}: {exc}"))

    # Importa el grafo principal sin instanciar Tk. Detecta imports dinámicos faltantes.
    try:
        import main  # noqa: F401
        items.append(_item("main_module_graph", True, True, "main importado sin crear App"))
    except Exception as exc:
        items.append(_item("main_module_graph", True, False, f"{type(exc).__name__}: {exc}\n{traceback.format_exc(limit=3)}"))

    _same_exe_probe(items)

    # Condiciones externas: informativas, no pueden falsearse ni empaquetarse.
    warnings.extend([
        {"name": "admin", "ok": _selftest_is_admin(), "detail": "Algunas acciones elevan UAC sólo cuando corresponde"},
        {"name": "rtss", "ok": _selftest_find_rtss() is not None, "detail": str(_selftest_find_rtss() or "No detectado; FPS de juegos queda N/A")},
        {"name": "ookla_cli", "ok": bool(shutil.which("speedtest.exe") or shutil.which("speedtest")), "detail": "Instalable desde Red avanzada"},
        {"name": "corepulse_ai", "ok": True, "detail": "Servidor IA embebido; llama.cpp/modelo se preparan automáticamente en primer inicio"},
        {"name": "pawnio", "ok": _find_pawnio() is not None, "detail": str(_find_pawnio() or "No detectado; algunos sensores de placa pueden quedar N/A")},
    ])

    failed = [x for x in items if x["critical"] and not x["ok"]]
    report = {
        "schema": 1,
        "version": VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ready": not failed,
        "critical_total": sum(1 for x in items if x["critical"]),
        "critical_failed": len(failed),
        "items": items,
        "warnings": warnings,
        "resource_root": str(resource_root()),
        "executable_root": str(executable_root()),
    }
    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return (0 if report["ready"] else 10), report
