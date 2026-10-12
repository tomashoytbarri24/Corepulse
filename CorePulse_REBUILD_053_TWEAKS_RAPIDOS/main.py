"""CorePulse REBUILD: arranque automático y aislado en Windows con Python 3.12."""
from __future__ import annotations

import hashlib
import math
import shutil
import os
from pathlib import Path
import struct
import subprocess
import sys
import time
import venv
import wave


PROJECT_DIR = Path(__file__).resolve().parent
REQUIREMENTS = PROJECT_DIR / "requirements.txt"
# La instalación vive fuera del ZIP y de OneDrive; nunca en la carpeta del proyecto.
RUNTIME_HOME = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")) / "CorePulse" / "runtime"


def _runtime_path() -> Path:
    """Identificador estable por requisitos, ABI y arquitectura (sin rutas CWD)."""
    key = hashlib.sha256(REQUIREMENTS.read_bytes()).hexdigest()[:12]
    bits = struct.calcsize("P") * 8
    return RUNTIME_HOME / f"rebuild-py{sys.version_info.major}{sys.version_info.minor}-{bits}bit-{key}"


def _runtime_python(runtime: Path) -> Path:
    return runtime / "Scripts" / "python.exe"


def _sanitized_env() -> dict[str, str]:
    env = os.environ.copy()
    # Evitar bibliotecas/plugins Qt de otros programas o venv de VS Code.
    for key in ("PYTHONHOME", "PYTHONPATH", "VIRTUAL_ENV", "QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH", "QML2_IMPORT_PATH", "QML_IMPORT_PATH"):
        env.pop(key, None)
    env["PYTHONNOUSERSITE"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def _runtime_healthy(executable: Path, env: dict[str, str]) -> bool:
    """Importar Qt real, psutil y comprobar los proveedores instalados."""
    if not executable.is_file():
        return False
    probe = (
        "from PySide6.QtCore import QObject; "
        "from PySide6.QtGui import QGuiApplication; "
        "from PySide6.QtQml import QQmlApplicationEngine; "
        "from PySide6.QtMultimedia import QSoundEffect; "
        "import psutil, importlib.metadata as m; "
        "m.version('pythonnet'); m.version('HardwareMonitor')"
    )
    try:
        result = subprocess.run(
            [str(executable), "-B", "-c", probe],
            cwd=str(PROJECT_DIR), env=env, capture_output=True,
            text=True, timeout=45, check=False,
        )
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _install_dependencies(executable: Path, env: dict[str, str], force: bool = False) -> int:
    command = [str(executable), "-B", "-m", "pip", "install", "--disable-pip-version-check", "--no-input", "--timeout", "25", "--retries", "2"]
    if force:
        command.append("--force-reinstall")
    command.extend(("-r", str(REQUIREMENTS)))
    print("[CorePulse] Instalando dependencias desde requirements.txt...", flush=True)
    try:
        return subprocess.run(command, cwd=str(PROJECT_DIR), env=env, check=False).returncode
    except OSError as error:
        print(f"[CorePulse] No se pudo ejecutar pip: {error}", file=sys.stderr)
        return 1


def _acquire_install_lock(folder: Path) -> None:
    """Evita que dos aperturas simultáneas instalen en el mismo venv."""
    started = time.monotonic()
    while True:
        try:
            folder.mkdir()
            return
        except FileExistsError:
            try:
                if time.time() - folder.stat().st_mtime > 1800:
                    folder.rmdir()  # Recupera un bloqueo abandonado, nunca borra dependencias.
                    continue
            except (OSError, FileNotFoundError):
                pass
            if time.monotonic() - started > 900:
                raise TimeoutError("Hay otra instalación de CorePulse en curso desde hace demasiado tiempo.")
            time.sleep(1)


def _prepare_runtime(runtime: Path) -> bool:
    """Instala una vez por versión de requisitos y repara un entorno incompleto."""
    executable = _runtime_python(runtime)
    ready = runtime / ".instalacion_correcta"
    env = _sanitized_env()
    lock = runtime.parent / f"{runtime.name}.instalando"
    runtime.parent.mkdir(parents=True, exist_ok=True)
    _acquire_install_lock(lock)
    try:
        if ready.is_file() and _runtime_healthy(executable, env):
            return True
        ready.unlink(missing_ok=True)
        if not executable.is_file():
            print(f"[CorePulse] Preparando entorno aislado: {runtime}", flush=True)
            venv.EnvBuilder(with_pip=True).create(str(runtime))
        # El primer intento repara dependencias ausentes o instalaciones interrumpidas.
        if not _runtime_healthy(executable, env):
            if _install_dependencies(executable, env) != 0:
                print("[CorePulse] Falló la instalación. Comprueba Internet, el acceso a PyPI y el espacio libre.", file=sys.stderr)
                return False
        if not _runtime_healthy(executable, env):
            print("[CorePulse] Qt o alguna dependencia no carga; intentando reparar el entorno...", flush=True)
            if _install_dependencies(executable, env, force=True) != 0 or not _runtime_healthy(executable, env):
                print("[CorePulse] La instalación no pudo verificarse; revisa Qt y los componentes de Windows.", file=sys.stderr)
                return False
        ready.write_text("CorePulse requirements verificados.\n", encoding="utf-8")
        return True
    except (OSError, TimeoutError, subprocess.SubprocessError) as error:
        print(f"[CorePulse] Error preparando las dependencias: {error}", file=sys.stderr)
        return False
    finally:
        try:
            lock.rmdir()
        except OSError:
            pass



def make_system_actions():
    from PySide6.QtCore import QObject, Property, Signal, Slot

    class Actions(QObject):
        statusChanged = Signal()

        def __init__(self):
            super().__init__()
            self._status = ""
            self._pending = False

        @Property(str, notify=statusChanged)
        def status(self):
            return self._status

        @Property(bool, notify=statusChanged)
        def pending(self):
            return self._pending

        def _set_status(self, value, pending):
            self._status = value
            self._pending = pending
            self.statusChanged.emit()

        @Slot(result=bool)
        def scheduleRestart(self):
            if os.name != "nt":
                self._set_status("Solo disponible en Windows.", False)
                return False
            exe = shutil.which("shutdown.exe")
            if not exe:
                self._set_status("Windows no encuentra shutdown.exe.", False)
                return False
            try:
                proc = subprocess.run(
                    [exe, "/r", "/t", "60", "/c", "Reinicio solicitado por el usuario desde CorePulse"],
                    capture_output=True, text=True, timeout=12, check=False,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            except (OSError, subprocess.TimeoutExpired):
                self._set_status("No se pudo solicitar el reinicio de Windows.", False)
                return False
            if proc.returncode == 0:
                self._set_status("Reinicio programado en 60 segundos. Puedes cancelarlo aquí.", True)
                return True
            self._set_status("Windows rechazó la solicitud de reinicio (código " + str(proc.returncode) + ").", False)
            return False

        @Slot(result=bool)
        def cancelRestart(self):
            if not self._pending or os.name != "nt":
                return False
            exe = shutil.which("shutdown.exe")
            if not exe:
                self._set_status("No se encontró shutdown.exe para cancelar.", self._pending)
                return False
            try:
                proc = subprocess.run(
                    [exe, "/a"], capture_output=True, text=True, timeout=12, check=False,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            except (OSError, subprocess.TimeoutExpired):
                self._set_status("No se pudo confirmar la cancelación del reinicio.", self._pending)
                return False
            if proc.returncode == 0:
                self._set_status("Reinicio cancelado correctamente.", False)
                return True
            self._set_status("Windows no confirmó la cancelación (código " + str(proc.returncode) + ").", self._pending)
            return False

    return Actions()

def steam_window_geometry(x: int, y: int, available_width: int, available_height: int) -> tuple[int, int, int, int]:
    """Ventana inicial centrada en el área útil, en píxeles lógicos Qt.

    1280×720 es el tamaño Steam de referencia. En monitores más pequeños
    usamos como máximo el 90 % del área de trabajo, sin tapar la barra de
    tareas y sin depender de resoluciones físicas o del escalado de Windows.
    """
    available_width = max(1, int(available_width))
    available_height = max(1, int(available_height))
    width = min(1280, max(1, int(available_width * .90)))
    height = min(720, max(1, int(available_height * .90)))
    return (
        int(x) + (available_width - width) // 2,
        int(y) + (available_height - height) // 2,
        width,
        height,
    )



def ensure_audio_test_tones() -> dict[str, str]:
    """Produce tonos estéreo cortos en LocalAppData con canales separados.

    No modifica controladores, volumen del sistema ni dispositivos predeterminados.
    """
    home = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
    target_dir = home / "CorePulse" / "audio_test"
    target_dir.mkdir(parents=True, exist_ok=True)
    sample_rate = 44100
    frames = int(0.7 * sample_rate)
    generated = {}
    for channel in ("left", "both", "right"):
        target = target_dir / f"stereo_660hz_{channel}_v1.wav"
        # A stereo 16-bit PCM recording should be larger than the 44-byte header.
        if not target.is_file() or target.stat().st_size != 44 + frames * 4:
            samples = bytearray()
            for i in range(frames):
                # 20 ms fade-in/out avoids sharp clicks. Peak below full scale.
                taper = min(1.0, i / (sample_rate * .02), (frames - i - 1) / (sample_rate * .02))
                amplitude = int(12500 * max(0.0, taper) * math.sin(2 * math.pi * 660 * i / sample_rate))
                left = amplitude if channel != "right" else 0
                right = amplitude if channel != "left" else 0
                samples.extend(struct.pack("<hh", left, right))
            with wave.open(str(target), "wb") as output:
                output.setnchannels(2)
                output.setsampwidth(2)
                output.setframerate(sample_rate)
                output.writeframes(samples)
        generated[channel] = target.resolve().as_uri()
    return generated

def main() -> int:
    if os.name != "nt":
        print("CorePulse está diseñado para Windows 10/11. Entorno no compatible.", file=sys.stderr)
        return 2
    if sys.version_info[:2] != (3, 12) or struct.calcsize("P") != 8:
        print("[CorePulse] Se necesita Python 3.12 de 64 bits para Windows.", file=sys.stderr)
        return 2
    if not REQUIREMENTS.is_file():
        print(f"[CorePulse] No se encuentra {REQUIREMENTS}. Extrae el ZIP completo.", file=sys.stderr)
        return 2

    runtime = _runtime_path()
    executable = _runtime_python(runtime)
    if os.path.normcase(os.path.abspath(sys.executable)) != os.path.normcase(os.path.abspath(executable)):
        # Python del sistema/VS Code: instala en el perfil y abre la app con ese venv.
        if not _prepare_runtime(runtime):
            return 1
        print("[CorePulse] Iniciando con dependencias verificadas...", flush=True)
        try:
            return subprocess.run(
                [str(executable), "-B", str(PROJECT_DIR / "main.py")],
                cwd=str(PROJECT_DIR), env=_sanitized_env(), check=False,
            ).returncode
        except OSError as error:
            print(f"[CorePulse] No se pudo iniciar el entorno: {error}", file=sys.stderr)
            return 1

    # Intérprete del entorno aislado: se importa Qt exclusivamente aquí.
    try:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtQml import QQmlApplicationEngine
        from core.monitoring.telemetry import Telemetry
        from core.tweaks.tweaks import TweaksManager
        from core.maintenance.cleanup import CleanupManager
        from core.health.battery import BatteryHealth
        from core.health.storage import StorageHealth
        from core.health.windows import WindowsHealth
        from core.health.repair import RepairHealth
        from core.health.recovery import RecoveryHealth
        from core.health.history import ChangeHistory
        from core.health.system_health import SystemHealth
        from core.health.performance import PerformanceHealth
    except (ImportError, OSError) as error:
        print(f"[CorePulse] No pudieron cargarse los módulos instalados: {error}", file=sys.stderr)
        return 1

    app = QGuiApplication(sys.argv)
    app.setApplicationName("CorePulse Rebuild")
    app.setOrganizationName("CorePulse")
    screen = app.primaryScreen()
    if screen is None:
        print("No se detectó una pantalla para abrir CorePulse.", file=sys.stderr)
        return 4
    area = screen.availableGeometry()
    initial_x, initial_y, initial_width, initial_height = steam_window_geometry(
        area.x(), area.y(), area.width(), area.height()
    )
    telemetry = Telemetry()
    tweaks = TweaksManager()
    cleanup = CleanupManager()
    battery_health = BatteryHealth()
    storage_health = StorageHealth()
    windows_health = WindowsHealth()
    repair_health = RepairHealth()
    recovery_health = RecoveryHealth()
    change_history = ChangeHistory()
    system_health = SystemHealth(telemetry, battery_health, storage_health, windows_health, recovery_health)
    performance_health = PerformanceHealth()
    app.aboutToQuit.connect(tweaks.close)
    app.aboutToQuit.connect(telemetry.close)
    app.aboutToQuit.connect(cleanup.close)
    app.aboutToQuit.connect(battery_health.close)
    app.aboutToQuit.connect(storage_health.close)
    app.aboutToQuit.connect(windows_health.close)
    app.aboutToQuit.connect(repair_health.close)
    app.aboutToQuit.connect(recovery_health.close)
    app.aboutToQuit.connect(change_history.close)
    app.aboutToQuit.connect(system_health.close)
    app.aboutToQuit.connect(performance_health.close)

    system_actions = make_system_actions()
    try:
        audio_tones = ensure_audio_test_tones()
    except OSError as error:
        print(f"[CorePulse] No se pudieron preparar los tonos de audio: {error}", file=sys.stderr)
        audio_tones = {"left": "", "both": "", "right": ""}
    engine = QQmlApplicationEngine()
    context = engine.rootContext()
    context.setContextProperty("systemActions", system_actions)
    context.setContextProperty("telemetry", telemetry)
    context.setContextProperty("tweaks", tweaks)
    context.setContextProperty("cleanup", cleanup)
    context.setContextProperty("batteryHealth", battery_health)
    context.setContextProperty("storageHealth", storage_health)
    context.setContextProperty("windowsHealth", windows_health)
    context.setContextProperty("repairHealth", repair_health)
    context.setContextProperty("recoveryHealth", recovery_health)
    context.setContextProperty("changeHistory", change_history)
    context.setContextProperty("systemHealth", system_health)
    context.setContextProperty("performanceHealth", performance_health)
    context.setContextProperty("initialWindowX", initial_x)
    context.setContextProperty("initialWindowY", initial_y)
    context.setContextProperty("initialWindowWidth", initial_width)
    context.setContextProperty("initialWindowHeight", initial_height)
    context.setContextProperty("audioToneLeft", audio_tones["left"])
    context.setContextProperty("audioToneBoth", audio_tones["both"])
    context.setContextProperty("audioToneRight", audio_tones["right"])
    qml_file = Path(__file__).resolve().parent / "ui" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_file)))
    if not engine.rootObjects():
        print("No se pudo cargar ui/Main.qml. Comprueba tu instalación de PySide6/QtQuick.", file=sys.stderr)
        return 3
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
