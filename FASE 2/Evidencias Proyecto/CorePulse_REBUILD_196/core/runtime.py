"""Entradas de procesos y recursos de CorePulse, en fuente y en el instalador."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
VERSION = "191"


def is_administrator():
    if os.name != 'nt':
        return False
    import ctypes
    return bool(ctypes.WinDLL('shell32', use_last_error=True).IsUserAnAdmin())


def _launch_as_administrator(executable, parameters, directory):
    import ctypes
    from ctypes import wintypes
    shell = ctypes.WinDLL('shell32', use_last_error=True)
    shell.ShellExecuteW.argtypes = (wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR,
                                   wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.c_int)
    shell.ShellExecuteW.restype = ctypes.c_void_p
    result = shell.ShellExecuteW(None, 'runas', executable, parameters, directory, 1)
    if result and result > 32:
        return 0
    return ctypes.get_last_error() or int(result or 1)


def always_administrator():
    """Preferencia opcional; se lee sin Qt porque decide antes de cargarlo."""
    if os.name != 'nt':
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r'Software\CorePulse\CorePulseRebuild\overlay') as key:
            return str(winreg.QueryValueEx(key, 'alwaysAdmin')[0]).casefold() == 'true'
    except OSError:
        return False


def ensure_administrator():
    """Elevar antes de cargar Qt solo si el usuario lo eligió; un único aviso UAC.

    CorePulse abre siempre: sin permisos, las funciones que los necesitan lo
    indican o piden UAC por acción. Los Worker heredan el token del padre.
    Retorna None para continuar, o 0 si la instancia elevada toma el relevo.
    """
    marker = '--corepulse-elevated'
    relaunched = marker in sys.argv[1:]
    if relaunched:
        sys.argv[:] = [arg for arg in sys.argv if arg != marker]
    if os.name != 'nt' or is_administrator():
        return None
    if relaunched:
        print('[CorePulse] Windows no concedió permisos; se abre sin administrador.', file=sys.stderr)
        return None
    if not always_administrator():
        return None
    import subprocess
    args = sys.argv[1:]
    if not getattr(sys, 'frozen', False):
        args = ['-B', str(ROOT / 'main.py'), *args]
    result = _launch_as_administrator(sys.executable,
        subprocess.list2cmdline([*args, marker]), str(ROOT))
    if result:
        print('[CorePulse] Sin permiso de Windows; se abre sin administrador.', file=sys.stderr)
        return None
    return 0


def quarantine_database(path):
    """Aparta una base SQLite dañada, con su WAL, sin borrar datos del usuario."""
    source = Path(path)
    moved = source.with_name(f"{source.name}.danada-{time.strftime('%Y%m%d-%H%M%S')}")
    os.replace(source, moved)
    for suffix in ('-wal', '-shm'):
        companion = Path(str(source) + suffix)
        if companion.exists():
            os.replace(companion, Path(str(moved) + suffix))
    return moved


def child_command(worker, *args):
    if worker not in {"cpu-probe", "cpu-stream", "gpu-probe", "benchmark-gpu", "tweak-apply", "tweak-rollback"}:
        raise ValueError("Trabajador desconocido")
    if getattr(sys, "frozen", False):
        return [str(Path(sys.executable).with_name("CorePulseWorker.exe")),
                "--corepulse-worker", worker, *map(str, args)]
    return [sys.executable, "-B", str(ROOT / "main.py"),
            "--corepulse-worker", worker, *map(str, args)]


def _tweak_request(mode, args):
    from core.tweaks import tweaks_engine as engine
    if len(args) != 2 or args[0] != "--request":
        raise ValueError("Solicitud de tweak inválida")
    request = Path(args[1]).resolve(strict=True)
    import re
    if not re.fullmatch(r"[a-f0-9]{32}\.request\.json", request.name) or request.stat().st_size > 4_000_000:
        raise ValueError("Archivo de solicitud inválido")
    payload = json.loads(request.read_text(encoding="utf-8"))
    result = request.with_name(request.name.replace(".request.json", ".result.json"))
    if Path(payload.get("result_path", "")).resolve() != result:
        raise ValueError("La salida no corresponde a esta solicitud")
    rows = payload.get("records")
    if not isinstance(rows, list) or len(rows) > len(engine.TWEAKS):
        raise ValueError("Lista de ajustes inválida")
    action = engine.apply_snapshot_records if mode == "tweak-apply" else engine.restore_snapshot_records
    results = action(rows)
    temporary = result.with_suffix(".tmp")
    temporary.write_text(json.dumps(results, ensure_ascii=False), encoding="utf-8")
    os.replace(temporary, result)
    return 0


def dispatch_worker(argv):
    if not argv or argv[0] != "--corepulse-worker":
        return None
    if len(argv) < 2:
        return 2
    mode, args = argv[1], argv[2:]
    for output in (sys.stdout, sys.stderr):
        if output is not None and hasattr(output, 'reconfigure'):
            output.reconfigure(encoding='utf-8', line_buffering=True)
    if mode == 'cpu-stream' and len(args) == 1 and args[0].isdigit() and int(args[0]) > 0:
        import threading
        from core.monitoring.telemetry import run_cpu_sensor_worker
        stop = threading.Event()
        def watch_input():
            sys.stdin.read()
            stop.set()
        threading.Thread(target=watch_input, daemon=True).start()
        run_cpu_sensor_worker(stream=True, parent_pid=int(args[0]), stop_event=stop)
        return 0
    if mode in {"cpu-probe", "gpu-probe"} and not args:
        from core.monitoring import telemetry
        if mode == 'cpu-probe':
            telemetry.run_cpu_sensor_worker()
            return 0
        source = telemetry._CPU_PACKAGE_PROBE if mode == "cpu-probe" else telemetry._GPU_PACKAGE_PROBE
        exec(compile(source, "<CorePulse sensor>", "exec"), {"__name__": "__main__"})
        return 0
    if mode == "benchmark-gpu":
        from core.benchmark_gpu import _gpu_cli
        sys.argv = [sys.argv[0], *args]
        _gpu_cli()
        return 0
    if mode in {"tweak-apply", "tweak-rollback"}:
        return _tweak_request(mode, args)
    return 2


def configure_gui_log():
    """El EXE sin consola conserva errores en el perfil del usuario."""
    if not getattr(sys, "frozen", False):
        return
    folder = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "CorePulse" / "logs"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "app.log"
    if path.exists() and path.stat().st_size > 2_000_000:
        os.replace(path, folder / "app.previous.log")
    stream = path.open("a", encoding="utf-8", buffering=1)
    sys.stdout = sys.stderr = stream


def installation_check(destination):
    """Diagnóstico sin cambios de Windows ni instalación de controladores."""
    import importlib
    checks = {}
    for name in ("PySide6.QtQuick", "PySide6.QtMultimedia", "psutil", "sqlite3",
                 "core.health.game_sessions", "core.health.report", "core.benchmark",
                 "core.overlay", "core.tweaks.tweaks", "pythonnet", "clr_loader", "HardwareMonitor"):
        try:
            importlib.import_module(name)
            checks[name] = "OK"
        except Exception as error:
            checks[name] = f"{type(error).__name__}: {error}"
    for name in ("ui/Main.qml", "bin/CorePulseOverlayHost.exe", "bin/PresentMon-2.5.1-x64.exe",
                 "bin/CorePulseCaptureGuard.exe"):
        checks[name] = "OK" if (ROOT / name).is_file() else "MISSING"
    dlls = list((ROOT / "bin").glob("CorePulseGameHook*.dll"))
    checks["native_modules"] = "OK" if len(dlls) == 10 else f"MISSING: {len(dlls)}/10"
    payload = {"version": VERSION, "frozen": bool(getattr(sys, "frozen", False)),
               "checks": checks, "ok": all(v == "OK" for v in checks.values())}
    Path(destination).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if payload["ok"] else 1
