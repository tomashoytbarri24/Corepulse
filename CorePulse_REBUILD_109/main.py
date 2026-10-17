"""CorePulse REBUILD: arranque automático y aislado en Windows con Python 3.12 o posterior."""
from __future__ import annotations

import hashlib
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
                'panel': panel, 'panelRaised': raised, 'panelBorder': border,
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
    if os.name != "nt":
        print("CorePulse está diseñado para Windows 10/11. Entorno no compatible.", file=sys.stderr)
        return 2
    if sys.version_info < (3, 12) or struct.calcsize("P") != 8:
        print("[CorePulse] Se necesita Python 3.12 o superior de 64 bits para Windows.", file=sys.stderr)
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
        from core.health.game_boost import GameBoost
        from core.health.monitoring_insights import MonitoringInsights
        from core.health.report import ReportExporter
        from core.overlay import OverlayController
        from core.maintenance.network import NetworkHealth
        from core.maintenance.startup import StartupManager
        from core.maintenance.drivers import DriverUpdates
        from core.maintenance.speed_test import NetworkSpeedTest
        from core.benchmark import BenchmarkController
        from core.cuenta import CuentaManager
        from core.ai import make_ai_controller
    except (ImportError, OSError) as error:
        print(f"[CorePulse] No pudieron cargarse los módulos instalados: {error}", file=sys.stderr)
        return 1

    app = QApplication(sys.argv)
    theme_manager = make_theme_manager()
    tray_controller = make_tray_controller(app)
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
    corepulse_ai = make_ai_controller(telemetry, system_health)
    benchmark_controller = BenchmarkController()
    report_exporter = ReportExporter(telemetry, system_health, monitoring_insights, windows_health,
                                     ai_controller=corepulse_ai,
                                     benchmark_controller=benchmark_controller)
    overlay_controller = OverlayController(telemetry, performance_health)
    network_health = NetworkHealth()
    startup_manager = StartupManager()
    driver_updates = DriverUpdates()
    network_speed_test = NetworkSpeedTest()
    cuenta = CuentaManager()
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
    app.aboutToQuit.connect(overlay_controller.close)
    app.aboutToQuit.connect(network_health.close)
    app.aboutToQuit.connect(startup_manager.close)
    app.aboutToQuit.connect(driver_updates.close)
    app.aboutToQuit.connect(network_speed_test.close)
    app.aboutToQuit.connect(benchmark_controller.close)
    app.aboutToQuit.connect(performance_health.close)
    app.aboutToQuit.connect(game_boost.close)
    app.aboutToQuit.connect(monitoring_insights.close)
    app.aboutToQuit.connect(cuenta.close)
    app.aboutToQuit.connect(corepulse_ai.close)

    system_actions = make_system_actions()
    engine = QQmlApplicationEngine()
    context = engine.rootContext()
    context.setContextProperty("systemActions", system_actions)
    context.setContextProperty("themeManager", theme_manager)
    context.setContextProperty("trayController", tray_controller)
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
    context.setContextProperty("networkHealth", network_health)
    context.setContextProperty("startupManager", startup_manager)
    context.setContextProperty("driverUpdates", driver_updates)
    context.setContextProperty("networkSpeedTest", network_speed_test)
    context.setContextProperty("benchmarkController", benchmark_controller)
    context.setContextProperty("cuenta", cuenta)
    context.setContextProperty("corepulseAI", corepulse_ai)
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
    # Arranque condicionado: se observa la línea base de procesos existentes.
    # El watcher SOLO iniciará RTSS si posteriormente aparece un juego/launcher.
    QTimer.singleShot(0, overlay_controller.startAutoWatch)
    # Al volver del navegador con la sesión iniciada, traer CorePulse al frente.
    cuenta.sesionIniciada.connect(tray_controller.restore)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
