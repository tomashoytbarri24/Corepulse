"""CorePulse REBUILD: arranque automático y aislado en Windows con Python 3.12 o posterior."""
from __future__ import annotations

import hashlib
import json
import tempfile
import threading
import urllib.error
import urllib.request
from urllib.parse import urlsplit
import shutil
import os
from pathlib import Path
import struct
import subprocess
import sys
import time
import venv


PROJECT_DIR = Path(__file__).resolve().parent
REQUIREMENTS = PROJECT_DIR / "requirements.txt"
# La instalación vive fuera del ZIP y de OneDrive; nunca en la carpeta del proyecto.
RUNTIME_HOME = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")) / "CorePulse" / "runtime"


# REBUILD 154: PawnIO oficial, instalacion inicial compartida entre main.py y BAT.
# El driver es opcional: nunca se afirma disponibilidad si no fue verificada.
PAWNIO_HOME = RUNTIME_HOME.parent
PAWNIO_VERSION = "2.2.0"
PAWNIO_INSTALLER_URL = (
    "https://github.com/namazso/PawnIO.Setup/releases/download/2.2.0/PawnIO_setup.exe"
)
# Huella SHA-256 publicada para el instalador oficial 2.2.0 (WinGet).
PAWNIO_INSTALLER_SHA256 = "1f519a22e47187f70a1379a48ca604981c4fcf694f4e65b734aaa74a9fba3032"
PAWNIO_MAX_BYTES = 12 * 1024 * 1024
PAWNIO_RETRY_SECONDS = 12 * 60 * 60


def _pawnio_windows() -> bool:
    return os.name == "nt"


def _pawnio_installed_version() -> str | None:
    """Leer instalacion registrada en HKLM; no deducirla de una carpeta."""
    if not _pawnio_windows():
        return None
    try:
        import winreg
        key_name = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\PawnIO"
        for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_name,
                                    0, winreg.KEY_READ | view) as key:
                    try:
                        version = str(winreg.QueryValueEx(key, "DisplayVersion")[0]).strip()
                    except OSError:
                        version = ""
                    return version if version else "versión no indicada"
            except OSError:
                continue
    except (ImportError, OSError):
        pass
    return None


def _pawnio_log(message: str) -> None:
    """Log corto en el perfil, no en el ZIP ni en la carpeta sincronizada."""
    safe = str(message).replace("\r", " ").replace("\n", " ")[:500]
    print("[CorePulse][PawnIO] " + safe, flush=True)
    try:
        PAWNIO_HOME.mkdir(parents=True, exist_ok=True)
        with (PAWNIO_HOME / "pawnio_setup.log").open("a", encoding="utf-8") as file:
            file.write(time.strftime("%Y-%m-%d %H:%M:%S") + " " + safe + "\n")
    except OSError:
        pass


def _pawnio_recent_attempt() -> bool:
    if os.environ.get("COREPULSE_PAWNIO_RETRY", "") == "1":
        return False
    try:
        stamp = json.loads((PAWNIO_HOME / "pawnio_setup_state.json").read_text(encoding="utf-8"))
        return (stamp.get("version") == PAWNIO_VERSION
                and 0 <= time.time() - float(stamp.get("timestamp", 0)) < PAWNIO_RETRY_SECONDS)
    except (OSError, ValueError, TypeError, AttributeError):
        return False


def _pawnio_record_attempt(status: str) -> None:
    try:
        PAWNIO_HOME.mkdir(parents=True, exist_ok=True)
        destination = PAWNIO_HOME / "pawnio_setup_state.json"
        pending = destination.with_suffix(".tmp")
        pending.write_text(json.dumps({"version": PAWNIO_VERSION, "timestamp": time.time(),
                                       "status": status}), encoding="utf-8")
        os.replace(pending, destination)
    except OSError:
        pass


def _pawnio_download_installer(destination: Path) -> None:
    """Descarga oficial HTTPS fijada por version/hash, nunca ejecuta bytes ajenos."""
    request = urllib.request.Request(PAWNIO_INSTALLER_URL,
                                     headers={"User-Agent": "CorePulse-PawnIO-Setup/154"})
    with urllib.request.urlopen(request, timeout=25) as response:
        resolved = urlsplit(response.geturl())
        if resolved.scheme != "https" or resolved.hostname not in {
            "github.com", "release-assets.githubusercontent.com", "objects.githubusercontent.com"
        }:
            raise ValueError("La descarga salio de los dominios oficiales autorizados")
        h = hashlib.sha256()
        total = 0
        with destination.open("xb") as output:
            while True:
                chunk = response.read(65536)
                if not chunk:
                    break
                total += len(chunk)
                if total > PAWNIO_MAX_BYTES:
                    raise ValueError("Instalador PawnIO supera el tamaño permitido")
                output.write(chunk)
                h.update(chunk)
        if total < 100_000 or h.hexdigest() != PAWNIO_INSTALLER_SHA256:
            raise ValueError("Huella SHA-256 del instalador PawnIO no coincide")


def _pawnio_run_official_installer(path: Path) -> int:
    """ShellExecuteEx(runas) solicita UAC sin elevar CorePulse por completo."""
    import ctypes
    from ctypes import wintypes

    class ShellExecuteInfo(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD), ("fMask", wintypes.ULONG),
            ("hwnd", wintypes.HWND), ("lpVerb", wintypes.LPCWSTR),
            ("lpFile", wintypes.LPCWSTR), ("lpParameters", wintypes.LPCWSTR),
            ("lpDirectory", wintypes.LPCWSTR), ("nShow", ctypes.c_int),
            ("hInstApp", wintypes.HINSTANCE), ("lpIDList", ctypes.c_void_p),
            ("lpClass", wintypes.LPCWSTR), ("hkeyClass", wintypes.HKEY),
            ("dwHotKey", wintypes.DWORD), ("hIcon", wintypes.HANDLE),
            ("hProcess", wintypes.HANDLE),
        ]

    api = ctypes.WinDLL("shell32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    api.ShellExecuteExW.argtypes = [ctypes.POINTER(ShellExecuteInfo)]
    api.ShellExecuteExW.restype = wintypes.BOOL
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel.GetExitCodeProcess.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    info = ShellExecuteInfo()
    info.cbSize = ctypes.sizeof(info)
    info.fMask = 0x00000040  # SEE_MASK_NOCLOSEPROCESS
    info.lpVerb = "runas"   # UAC nativo. Denegar -> ERROR_CANCELLED 1223.
    info.lpFile = str(path)
    info.lpParameters = "-install -silent"
    info.lpDirectory = str(path.parent)
    info.nShow = 0
    # ShellExecuteEx puede usar extensiones Shell con COM; inicializar el
    # apartamento en ESTE hilo, sin exigir elevación a toda la aplicación.
    ole32 = ctypes.WinDLL("ole32", use_last_error=True)
    ole32.CoInitializeEx.argtypes = [ctypes.c_void_p, wintypes.DWORD]
    ole32.CoInitializeEx.restype = ctypes.c_long
    ole32.CoUninitialize.argtypes = []
    init_result = ole32.CoInitializeEx(None, 0x2)  # COINIT_APARTMENTTHREADED
    must_uninitialize = init_result in (0, 1)  # S_OK / S_FALSE
    try:
        if not api.ShellExecuteExW(ctypes.byref(info)):
            return ctypes.get_last_error() or 1
        try:
            outcome = kernel.WaitForSingleObject(info.hProcess, 300_000)
            if outcome == 258:  # WAIT_TIMEOUT
                raise subprocess.TimeoutExpired(str(path), 300)
            if outcome != 0:  # WAIT_OBJECT_0
                raise OSError("No se pudo esperar el proceso del instalador")
            exit_code = wintypes.DWORD()
            if not kernel.GetExitCodeProcess(info.hProcess, ctypes.byref(exit_code)):
                raise OSError("Windows no devolvió el resultado del instalador")
            return exit_code.value
        finally:
            kernel.CloseHandle(info.hProcess)
    finally:
        if must_uninitialize:
            ole32.CoUninitialize()


def _pawnio_run_winget() -> int:
    executable = shutil.which("winget")
    if not executable:
        raise FileNotFoundError("WinGet no está disponible")
    result = subprocess.run([
        executable, "install", "--id", "namazso.PawnIO", "--exact", "--source", "winget",
        "--silent", "--accept-package-agreements", "--accept-source-agreements",
    ], timeout=360, capture_output=True, check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return result.returncode


def _pawnio_check() -> tuple[str, str]:
    """Al iniciar solo se consulta: un controlador de kernel no se instala sin pedirlo."""
    if not _pawnio_windows():
        return "unsupported", "PawnIO solo se instala en Windows"
    installed = _pawnio_installed_version()
    if installed is not None:
        return "installed", "PawnIO ya está registrado en Windows (" + installed + ")"
    return "missing", "PawnIO no está instalado; la temperatura de CPU puede no estar disponible"


def _pawnio_install_startup(retry: bool = False) -> tuple[str, str]:
    """Instala a pedido del usuario; idempotente y fuera del hilo de Qt."""
    if not _pawnio_windows():
        return "unsupported", "PawnIO solo se instala en Windows"
    installed = _pawnio_installed_version()
    if installed is not None:
        return "installed", "PawnIO ya está registrado en Windows (" + installed + ")"
    if not retry and _pawnio_recent_attempt():
        return "deferred", "Instalación pendiente; reintento después de 12 h o COREPULSE_PAWNIO_RETRY=1"
    PAWNIO_HOME.mkdir(parents=True, exist_ok=True)
    lock = PAWNIO_HOME / "pawnio_instalando.lock"
    try:
        lock.mkdir()
    except FileExistsError:
        try:
            if time.time() - lock.stat().st_mtime > 900:
                lock.rmdir()
                lock.mkdir()
            else:
                return "busy", "Otra instancia de CorePulse está preparando PawnIO"
        except OSError:
            return "busy", "Hay otra instalación PawnIO en curso"
    try:
        installed = _pawnio_installed_version()
        if installed is not None:
            return "installed", "PawnIO ya está registrado en Windows (" + installed + ")"
        _pawnio_log("PawnIO ausente: descargando instalador oficial verificado 2.2.0")
        # No reintentar por otra vía cuando un usuario rechazó UAC o falló el
        # instalador. El fallback WinGet se reserva para problemas de DESCARGA.
        try:
            with tempfile.TemporaryDirectory(prefix="pawnio-", dir=str(PAWNIO_HOME)) as folder:
                installer = Path(folder) / "PawnIO_setup.exe"
                try:
                    _pawnio_download_installer(installer)
                except ValueError as error:
                    _pawnio_record_attempt("unsafe_download")
                    _pawnio_log(str(error))
                    return "error", "Descarga PawnIO rechazada por seguridad; no se instaló"
                except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as error:
                    _pawnio_log("Descarga oficial no disponible (" + type(error).__name__ + "); usando WinGet")
                    try:
                        code = _pawnio_run_winget()
                    except (OSError, subprocess.TimeoutExpired) as winget_error:
                        _pawnio_record_attempt("no_download")
                        message = "Sin conexión/WinGet para instalar PawnIO (" + type(winget_error).__name__ + ")"
                        _pawnio_log(message)
                        return "error", message
                else:
                    code = _pawnio_run_official_installer(installer)
        except subprocess.TimeoutExpired:
            _pawnio_record_attempt("timeout")
            return "error", "La instalación de PawnIO agotó el tiempo permitido"
        installed = _pawnio_installed_version()
        if code in (0, 3010) and installed is not None:
            if code == 3010:
                result = ("reboot", "PawnIO registrado; Windows solicita reiniciar para terminar")
            else:
                result = ("installed", "PawnIO instalado y registrado (" + installed + ")")
            _pawnio_log(result[1])
            return result
        status = "reboot" if code == 3010 else "error"
        message = ("Instalación pendiente de reinicio; todavía no verificada" if code == 3010
                   else "Se rechazó el permiso UAC; PawnIO no fue instalado" if code == 1223
                   else "PawnIO no pudo verificarse después del instalador (código " + str(code) + ")")
        _pawnio_record_attempt("unverified")
        _pawnio_log(message)
        return status, message
    except OSError as error:
        _pawnio_record_attempt("exception")
        message = "No se pudo preparar PawnIO (" + type(error).__name__ + ")"
        _pawnio_log(message)
        return "error", message
    finally:
        try:
            lock.rmdir()
        except OSError:
            pass


def make_pawnio_setup(tray_controller):
    """Puente Qt: trabajador independiente y estado visible en el contexto QML."""
    from PySide6.QtCore import QObject, Property, Signal, Slot

    class PawnIOSetup(QObject):
        changed = Signal()
        finished = Signal(str, str)

        def __init__(self):
            super().__init__()
            self._status = "pendiente"
            self._message = "Comprobando si PawnIO está instalado..."
            self._thread = None
            self.finished.connect(self._on_finished)

        @Property(str, notify=changed)
        def status(self):
            return self._status

        @Property(str, notify=changed)
        def message(self):
            return self._message

        @Slot()
        def start(self):
            if self._thread is not None and self._thread.is_alive():
                return
            self._status = "checking"
            self._message = "Comprobando PawnIO..."
            self.changed.emit()
            self._thread = threading.Thread(target=self._worker, args=(_pawnio_check,),
                                            name="CorePulse-PawnIO", daemon=True)
            self._thread.start()

        @Slot()
        def install(self):
            if self._thread is not None and self._thread.is_alive():
                return
            self._status = "installing"
            self._message = "Instalando PawnIO; acepta el aviso de Windows..."
            self.changed.emit()
            self._thread = threading.Thread(target=self._worker,
                                            args=(lambda: _pawnio_install_startup(retry=True),),
                                            name="CorePulse-PawnIO", daemon=True)
            self._thread.start()

        def _worker(self, action):
            try:
                result = action()
            except Exception as error:
                result = ("error", "Error PawnIO: " + type(error).__name__)
                _pawnio_log(result[1])
            self.finished.emit(*result)

        @Slot(str, str)
        def _on_finished(self, status, message):
            self._status, self._message = status, message
            self.changed.emit()
            if status in ("error", "reboot", "installed"):
                if status != "installed" or message.startswith("PawnIO instalado"):
                    tray_controller.notifyOperation("PawnIO · CorePulse", message)

    return PawnIOSetup()


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
        "from PySide6.QtWidgets import QApplication, QSystemTrayIcon; "
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



# Tema persistente en el perfil de Windows. No se escribe nada en el proyecto.
# Esta base es parte fija de la interfaz, no un preset que las variantes puedan sustituir.
DEFAULT_THEME_ID = "corepulse"
COREPULSE_BASE_BACKDROP = ("#111319", "#14131E", "#201529")
COREPULSE_BASE_THEME = (
    DEFAULT_THEME_ID, "CorePulse", "Paleta original luminosa de REBUILD 065.",
    *COREPULSE_BASE_BACKDROP, "#14131D", "#1A1C26", "#242633", "#303647",
    "#4EDDC8", "#17B9F7", "#B756EA",
)
THEMES = [
    COREPULSE_BASE_THEME,
    ("aurora", "Acero Ártico", "Azul petróleo y acero frío sobre carbón.", "#071118", "#0B1720", "#102523", "#101820", "#17232B", "#23313B", "#3D5662", "#00BFA5", "#168BCE", "#8654C9"),
    ("violet", "Carbono", "Grafito, cobalto y acero oscuro.", "#080D14", "#0C1320", "#131B2B", "#11151B", "#191F27", "#262E39", "#414A56", "#267FC2", "#0FA7D4", "#8754B5"),
    ("ember", "Óxido", "Cobre quemado, bronce y acero oscuro.", "#120E0A", "#1A120C", "#26160D", "#18130F", "#211A14", "#30251B", "#594834", "#D87932", "#0E9A94", "#B64470"),
    ("glacier", "Cobalto", "Azul profundo, cobalto y acero.", "#07101D", "#0B1830", "#14274D", "#101622", "#172132", "#232F45", "#3D5273", "#2D6CDF", "#00A8C2", "#8854D1"),
    ("forest", "Bosque Táctico", "Verde pino, oliva y bronce apagado.", "#08120E", "#0C1A12", "#122319", "#101813", "#18231B", "#243329", "#405545", "#398F4A", "#0E9E89", "#B39426"),
    ("crimson", "Rojo Torque", "Granate profundo, rojo mineral y acero.", "#12090D", "#1C0D14", "#2B111B", "#191115", "#25171D", "#382329", "#62404A", "#D33B4D", "#228ABB", "#A444BA"),
    ("gold", "Titanio Ámbar", "Titanio oscuro, bronce y cobre.", "#120F09", "#1A150B", "#2A1B10", "#17150F", "#211E16", "#302B20", "#554A35", "#C38D20", "#2385A7", "#8D55BE"),
    ("sakura", "Acero Táctico", "Grafito, bronce y acero azulado sobre superficies profundas.", "#0A0E13", "#111923", "#182432", "#11161C", "#171E27", "#242D38", "#414B59", "#C67526", "#2083A3", "#8752B4"),
    ("cyber", "Verde Radar", "Verde militar y acero sobre carbón profundo.", "#0A120D", "#111A11", "#1C2513", "#0F1713", "#17211B", "#232F27", "#3F5144", "#659C28", "#0E9786", "#AA8422"),
    ("obsidian", "Obsidiana Azul", "Carbón azulado, acero oscuro y cian eléctrico.", "#070B12", "#0C1421", "#12243A", "#0D141D", "#151E2A", "#202D3B", "#394F62", "#25B6D6", "#358EE6", "#8863C7"),
    ("vortex", "Vórtice", "Verde profundo, petróleo y jade.", "#07110F", "#0A1B18", "#102823", "#101915", "#17221D", "#24332A", "#435449", "#45A86A", "#159C98", "#9D75BC"),
    ("forge", "Forja", "Grafito, hierro oscuro y cobre industrial.", "#110C09", "#1A110C", "#2A1810", "#19130F", "#211A15", "#30251D", "#534236", "#DB7737", "#198EA3", "#A75378"),
    ("tide", "Marea", "Azul marino, petróleo y turquesa.", "#071018", "#0A1822", "#0C2B35", "#0E171C", "#142129", "#1D2D36", "#3A515B", "#2AA7A0", "#238BC1", "#8562B8"),
    ("titanium", "Titanio", "Pizarra antracita, plata fría y azul acero.", "#090D13", "#111821", "#1A2631", "#11171D", "#1A222B", "#27323D", "#46535F", "#8296AA", "#2E8FB2", "#8B69B4"),
]

def make_theme_manager():
    from PySide6.QtCore import QObject, Property, Signal, Slot, QSettings

    class ThemeManager(QObject):
        changed = Signal()

        def __init__(self):
            super().__init__()
            self._store = QSettings('CorePulse', 'CorePulseRebuild')
            # Inyectar la base fija por separado impide que desaparezca al editar
            # o reordenar la colección de capas de color.
            records = [COREPULSE_BASE_THEME]
            records.extend(t for t in THEMES if t[0] != DEFAULT_THEME_ID)
            self._themes = [self._make_palette(t) for t in records]
            self._theme_ids = {t['id'] for t in self._themes}
            stored = str(self._store.value('theme/id', DEFAULT_THEME_ID))
            self._selected = stored if stored in self._theme_ids else DEFAULT_THEME_ID

        @staticmethod
        def _make_palette(t):
            key, title, desc, bg0, bg1, bg2, side, panel, raised, border, accent, cyan, purple = t
            return {
                'id': key, 'title': title, 'description': desc,
                'isBase': key == DEFAULT_THEME_ID,
                'layerType': 'Base permanente' if key == DEFAULT_THEME_ID else 'Capa de color',
                'bgStart': bg0,
                'bgMid': bg1,
                'bgEnd': bg2,
                'sidebar': side, 'sidebarBorder': border,
                'sidebarActive': raised, 'sidebarActiveIcon': panel,
                'sidebarActiveBorder': accent,
                # R142: bordes neutros armonizados con GlassPanel en todas las tarjetas.
                # Las superficies generales y elevadas usan el mismo lenguaje
                # translúcido, mientras los bordes dejan de depender del gris
                # del tema para evitar lineas duras en Windows.
                'panel': '#0AFFFFFF',
                'panelHover': '#14FFFFFF',
                'panelOpaque': panel, 'panelRaised': '#12FFFFFF', 'panelBorder': '#13FFFFFF',
                'accent': accent, 'cyan': cyan, 'purple': purple,
                'ink': '#F1F4FB', 'muted': '#B5C1D1',
                # Botones que ejecutan algo (REBUILD 082): relleno sólido como
                # «Aplicar» de Tweaks. Fijo en todos los temas para que siempre
                # se reconozca como acción.
                'action': '#17B9F7', 'actionText': '#0E1621',
                'actionMuted': '#303746', 'actionMutedText': '#8D9CB0',
            }

        @Property(str, notify=changed)
        def themeId(self):
            return self._selected

        @Property('QVariantList', constant=True)
        def themes(self):
            return self._themes

        @Property('QVariantMap', notify=changed)
        def palette(self):
            return next((p for p in self._themes if p['id'] == self._selected), self._themes[0])

        @Slot(str)
        def applyTheme(self, theme_id):
            if theme_id not in self._theme_ids or theme_id == self._selected:
                return
            self._selected = theme_id
            self._store.setValue('theme/id', theme_id)
            self._store.sync()
            self.changed.emit()

    return ThemeManager()


def make_tray_controller(app):
    from PySide6.QtCore import QObject, Property, Signal, Slot
    from PySide6.QtGui import QAction, QIcon, QPainter, QPixmap, QColor
    from PySide6.QtWidgets import QMenu, QSystemTrayIcon

    class TrayController(QObject):
        changed = Signal()
        ramCleanupRequested = Signal()

        def __init__(self):
            super().__init__()
            self._app = app
            self._window = None
            self._quitting = False
            self._available = bool(QSystemTrayIcon.isSystemTrayAvailable())
            self._icon = QIcon()
            self._tray = None
            if not self._available:
                return
            pix = QPixmap(64, 64)
            pix.fill(QColor('#00000000'))
            painter = QPainter(pix)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(QColor('#52E3C5'))
            painter.setBrush(QColor('#153E4A'))
            painter.drawRoundedRect(5, 5, 54, 54, 16, 16)
            painter.setPen(QColor('#F3F7FF'))
            font = painter.font()
            font.setBold(True)
            font.setPixelSize(39)
            painter.setFont(font)
            painter.drawText(pix.rect(), 0x84, 'C')
            painter.end()
            self._icon = QIcon(pix)
            self._tray = QSystemTrayIcon(self._icon, self)
            self._tray.setToolTip('CorePulse — en segundo plano')
            menu = QMenu()
            restore = QAction('Abrir CorePulse', menu)
            restore.triggered.connect(self.restore)
            ram = QAction('Limpieza completa de RAM…', menu)
            ram.triggered.connect(self.requestRamCleanup)
            quit_action = QAction('Salir de CorePulse', menu)
            quit_action.triggered.connect(self.quit)
            menu.addAction(restore)
            menu.addAction(ram)
            menu.addSeparator()
            menu.addAction(quit_action)
            self._menu = menu  # mantener QMenu vivo: QSystemTrayIcon no siempre asume su propiedad
            self._tray.setContextMenu(menu)
            self._tray.activated.connect(self._activated)
            self._tray.show()
            app.setQuitOnLastWindowClosed(False)
            self._app = app

        def bind_window(self, window):
            self._window = window
            if self._available:
                window.setIcon(self._icon)

        @Property(bool, notify=changed)
        def available(self):
            return self._available

        @Property(bool, notify=changed)
        def quitRequested(self):
            return self._quitting

        @Slot()
        def notifyHidden(self):
            if self._tray and QSystemTrayIcon.supportsMessages():
                self._tray.showMessage('CorePulse sigue activo',
                    'Haz doble clic en el icono de la bandeja para regresar.',
                    QSystemTrayIcon.Information, 3500)

        @Slot(str, str)
        def notifyOperation(self, title, message):
            if self._tray and QSystemTrayIcon.supportsMessages():
                self._tray.showMessage(str(title)[:80], str(message)[:220],
                    QSystemTrayIcon.Information, 5000)

        @Slot()
        def restore(self):
            if self._window:
                self._window.showNormal()
                self._window.raise_()
                self._window.requestActivate()

        @Slot()
        def requestRamCleanup(self):
            # No restaura la ventana ni abre confirmaciones/medidores QML.
            self.ramCleanupRequested.emit()

        def _activated(self, reason):
            if reason in (QSystemTrayIcon.DoubleClick, QSystemTrayIcon.Trigger):
                self.restore()

        @Slot()
        def quit(self):
            self._quitting = True
            self.changed.emit()
            if self._tray:
                self._tray.hide()
            self._app.quit()

    return TrayController()

def main() -> int:
    from core.runtime import dispatch_worker, configure_gui_log, installation_check, ensure_administrator
    worker_result = dispatch_worker(sys.argv[1:])
    if worker_result is not None:
        return worker_result
    if len(sys.argv) == 3 and sys.argv[1] == '--installation-check':
        return installation_check(sys.argv[2])
    elevation_result = ensure_administrator()
    if elevation_result is not None:
        return elevation_result
    configure_gui_log()
    if os.name != "nt":
        print("CorePulse está diseñado para Windows 10/11. Entorno no compatible.", file=sys.stderr)
        return 2
    if sys.version_info < (3, 12) or struct.calcsize("P") != 8:
        print("[CorePulse] Se necesita Python 3.12 o superior de 64 bits para Windows.", file=sys.stderr)
        return 2
    if not REQUIREMENTS.is_file():
        print(f"[CorePulse] No se encuentra {REQUIREMENTS}. Extrae el ZIP completo.", file=sys.stderr)
        return 2

    frozen = bool(getattr(sys, 'frozen', False))
    runtime = _runtime_path()
    executable = _runtime_python(runtime)
    if not frozen and os.path.normcase(os.path.abspath(sys.executable)) != os.path.normcase(os.path.abspath(executable)):
        # Python del sistema/VS Code: instala en el perfil y abre la app con ese venv.
        if not _prepare_runtime(runtime):
            return 1
        print("[CorePulse] Iniciando con dependencias verificadas...", flush=True)
        try:
            return subprocess.run(
                [str(executable), "-B", str(PROJECT_DIR / "main.py"), *sys.argv[1:]],
                cwd=str(PROJECT_DIR), env=_sanitized_env(), check=False,
            ).returncode
        except OSError as error:
            print(f"[CorePulse] No se pudo iniciar el entorno: {error}", file=sys.stderr)
            return 1

    # Intérprete del entorno aislado: se importa Qt exclusivamente aquí.
    try:
        from PySide6.QtCore import QUrl, QTimer
        from PySide6.QtWidgets import QApplication
        from PySide6.QtQml import QQmlApplicationEngine
        from core.monitoring.telemetry import Telemetry
        from core.tweaks.tweaks import TweaksManager
        from core.maintenance.cleanup import CleanupManager
        from core.maintenance.audio_test import AudioTestController
        from core.health.battery import BatteryHealth
        from core.health.storage import StorageHealth
        from core.health.windows import WindowsHealth
        from core.health.repair import RepairHealth
        from core.health.recovery import RecoveryHealth
        from core.health.history import ChangeHistory
        from core.health.system_health import SystemHealth
        from core.health.stability import StabilityHealth
        from core.health.performance import PerformanceHealth
        from core.health.game_sessions import GameSessionsController
        from core.health.game_boost import GameBoost
        from core.health.monitoring_insights import MonitoringInsights
        from core.health.report import ReportExporter
        from core.overlay import OverlayController
        from core.maintenance.network import NetworkHealth
        from core.maintenance.startup import StartupManager
        from core.maintenance.speed_test import NetworkSpeedTest
        from core.benchmark import BenchmarkController
        from core.cuenta import CuentaManager
        from core.ai import make_ai_controller, make_connectivity_controller
    except (ImportError, OSError) as error:
        print(f"[CorePulse] No pudieron cargarse los módulos instalados: {error}", file=sys.stderr)
        return 1

    app = QApplication(sys.argv)
    theme_manager = make_theme_manager()
    tray_controller = make_tray_controller(app)
    pawnio_setup = make_pawnio_setup(tray_controller)
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
    def start_tray_ram_cleanup():
        if cleanup.data.get('busy'):
            tray_controller.notifyOperation('Limpieza RAM no iniciada', 'Ya hay una operación de mantenimiento en curso.')
            return
        if cleanup.cleanRamDeepFromTray():
            tray_controller.notifyOperation('Limpieza RAM', 'Limpieza profunda iniciada en segundo plano.')
        else:
            tray_controller.notifyOperation('Limpieza RAM no iniciada', 'CorePulse no pudo iniciar la operación.')
    tray_controller.ramCleanupRequested.connect(start_tray_ram_cleanup)
    cleanup.trayNotification.connect(tray_controller.notifyOperation)
    audio_test = AudioTestController()
    battery_health = BatteryHealth()
    storage_health = StorageHealth()
    windows_health = WindowsHealth()
    repair_health = RepairHealth()
    recovery_health = RecoveryHealth()
    change_history = ChangeHistory()
    system_health = SystemHealth(telemetry, battery_health, storage_health, windows_health, recovery_health)
    stability_health = StabilityHealth(telemetry)
    performance_health = PerformanceHealth()
    game_boost = GameBoost(performance_health)
    monitoring_insights = MonitoringInsights(telemetry, system_health)
    # La cuenta debe existir antes del controlador AI: el modo Cloud se suscribe
    # a sus señales y utiliza su sesión autenticada.
    cuenta = CuentaManager()
    corepulse_ai = make_ai_controller(telemetry, system_health, cuenta, monitoring_insights)
    connectivity = make_connectivity_controller()
    connectivity.onlineChanged.connect(corepulse_ai.setInternetOnline)
    benchmark_controller = BenchmarkController()
    report_exporter = ReportExporter(telemetry, system_health, monitoring_insights, windows_health,
                                     ai_controller=corepulse_ai,
                                     benchmark_controller=benchmark_controller)
    overlay_controller = OverlayController(telemetry, performance_health, cleanup,
                                           storage=storage_health)
    from core.health.game_capture import ProblemCapture
    problem_capture = ProblemCapture(overlay_controller)
    game_sessions = GameSessionsController(telemetry, performance_health, overlay_controller)
    overlay_controller.setThemePalette(theme_manager.palette)
    theme_manager.changed.connect(
        lambda: overlay_controller.setThemePalette(theme_manager.palette))
    network_health = NetworkHealth()
    startup_manager = StartupManager()
    network_speed_test = NetworkSpeedTest()
    app.aboutToQuit.connect(tweaks.close)
    app.aboutToQuit.connect(telemetry.close)
    app.aboutToQuit.connect(cleanup.close)
    app.aboutToQuit.connect(audio_test.close)
    app.aboutToQuit.connect(battery_health.close)
    app.aboutToQuit.connect(storage_health.close)
    app.aboutToQuit.connect(windows_health.close)
    app.aboutToQuit.connect(repair_health.close)
    app.aboutToQuit.connect(recovery_health.close)
    app.aboutToQuit.connect(change_history.close)
    app.aboutToQuit.connect(system_health.close)
    app.aboutToQuit.connect(stability_health.close)
    app.aboutToQuit.connect(game_sessions.close)
    app.aboutToQuit.connect(problem_capture.close)
    app.aboutToQuit.connect(overlay_controller.close)
    app.aboutToQuit.connect(network_health.close)
    app.aboutToQuit.connect(startup_manager.close)
    app.aboutToQuit.connect(network_speed_test.close)
    app.aboutToQuit.connect(benchmark_controller.close)
    app.aboutToQuit.connect(performance_health.close)
    app.aboutToQuit.connect(game_boost.close)
    app.aboutToQuit.connect(monitoring_insights.close)
    app.aboutToQuit.connect(cuenta.close)
    app.aboutToQuit.connect(corepulse_ai.close)
    app.aboutToQuit.connect(connectivity.close)

    system_actions = make_system_actions()
    engine = QQmlApplicationEngine()
    qml_warnings = []
    engine.warnings.connect(lambda errors: qml_warnings.extend(str(error) for error in errors))
    context = engine.rootContext()
    context.setContextProperty("systemActions", system_actions)
    context.setContextProperty("themeManager", theme_manager)
    context.setContextProperty("trayController", tray_controller)
    context.setContextProperty("pawnioSetup", pawnio_setup)
    context.setContextProperty("telemetry", telemetry)
    context.setContextProperty("tweaks", tweaks)
    context.setContextProperty("cleanup", cleanup)
    context.setContextProperty("audioTest", audio_test)
    context.setContextProperty("batteryHealth", battery_health)
    context.setContextProperty("storageHealth", storage_health)
    context.setContextProperty("windowsHealth", windows_health)
    context.setContextProperty("repairHealth", repair_health)
    context.setContextProperty("recoveryHealth", recovery_health)
    context.setContextProperty("changeHistory", change_history)
    context.setContextProperty("systemHealth", system_health)
    context.setContextProperty("stabilityHealth", stability_health)
    context.setContextProperty("performanceHealth", performance_health)
    context.setContextProperty("gameBoost", game_boost)
    context.setContextProperty("monitoringInsights", monitoring_insights)
    context.setContextProperty("reportExporter", report_exporter)
    context.setContextProperty("overlayController", overlay_controller)
    context.setContextProperty("gameSessions", game_sessions)
    context.setContextProperty("problemCapture", problem_capture)
    context.setContextProperty("networkHealth", network_health)
    context.setContextProperty("startupManager", startup_manager)
    context.setContextProperty("networkSpeedTest", network_speed_test)
    context.setContextProperty("benchmarkController", benchmark_controller)
    context.setContextProperty("cuenta", cuenta)
    context.setContextProperty("corepulseAI", corepulse_ai)
    context.setContextProperty("connectivity", connectivity)
    context.setContextProperty("initialWindowX", initial_x)
    context.setContextProperty("initialWindowY", initial_y)
    context.setContextProperty("initialWindowWidth", initial_width)
    context.setContextProperty("initialWindowHeight", initial_height)
    qml_file = Path(__file__).resolve().parent / "ui" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_file)))
    if not engine.rootObjects():
        print("No se pudo cargar ui/Main.qml. Comprueba tu instalación de PySide6/QtQuick.", file=sys.stderr)
        return 3
    tray_controller.bind_window(engine.rootObjects()[0])
    overlay_controller.openRequested.connect(tray_controller.restore)
    # Punto único de arranque: el .bat invoca main.py, nunca instala dos veces.
    smoke_test = len(sys.argv) in (3, 4) and sys.argv[1] == '--smoke-test'
    if not smoke_test:
        QTimer.singleShot(0, pawnio_setup.start)
        # Preparar el motor aunque el juego ya estuviera abierto.
        QTimer.singleShot(0, overlay_controller.startAutoWatch)
        # Mantener detección y plan reversible fuera de la página de rendimiento.
        QTimer.singleShot(0, lambda: performance_health.startGameWatch('auto-power'))
    if smoke_test:
        smoke_page = sys.argv[3] if len(sys.argv) == 4 and sys.argv[3] in ('overlay', 'game_sessions') else 'summary'
        QTimer.singleShot(1800, lambda: engine.rootObjects()[0].setProperty('selectedPage', smoke_page))
        def finish_smoke_test():
            from core.runtime import is_administrator, VERSION
            Path(sys.argv[2]).write_text(json.dumps({'version': VERSION, 'qmlLoaded': bool(engine.rootObjects()),
                'administrator': is_administrator(),
                'page': smoke_page, 'qmlWarnings': qml_warnings,
                'frozen': frozen, 'sensorsPrepared': telemetry.startupReady,
                'cpuTemperatureAvailable': telemetry.metrics.get('cpuTemp') is not None}), encoding='utf-8')
            tray_controller.quit()
        QTimer.singleShot(4000, finish_smoke_test)
    # Al volver del navegador con la sesión iniciada, traer CorePulse al frente.
    cuenta.sesionIniciada.connect(tray_controller.restore)
    return app.exec()


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    raise SystemExit(main())
