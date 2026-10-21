"""CorePulse/RTSS OSD + Windows global shortcuts.

Third-party RTSS stays installed/owned by its publisher; CorePulse never edits
RTSS configuration, game memory, or other OSD entries. Win32-only integration.
RTSS v2.x SharedMemoryV2 layout follows the public RTSS SDK header.
"""
from __future__ import annotations

import ctypes
import os
import queue
import re
import struct
import subprocess
import threading
import psutil
import time
from concurrent.futures.thread import ThreadPoolExecutor
from pathlib import Path
from ctypes import wintypes

from PySide6.QtCore import QObject, Property, QSettings, QTimer, Signal, Slot, QUrl
from core.health.fps import RTSSFPSReader

OSD_OWNER = b"CorePulse"
RTSS_SIGNATURE = 0x52545353  # MSVC DWORD literal 'RTSS'
FILE_MAP_ALL_ACCESS = 0x000F001F
RTSS_MEMORY_NAME = "RTSSSharedMemoryV2"
# Offsets verified against the public RTSS_SHARED_MEMORY v2 SDK header:
# DWORD dwOSDFrame at byte 32; LONG dwBusy at byte 36 (v2.14+).
RTSS_OSD_FRAME_OFFSET = 32
RTSS_BUSY_OFFSET = 36
MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_NOREPEAT = 0x0001, 0x0002, 0x0004, 0x4000
WM_HOTKEY, WM_APP_UPDATE = 0x0312, 0x8000 + 136
HOTKEY_SHOW, HOTKEY_HIDE = 0xB3A1, 0xB3A2
VALID_KEY = re.compile(r"^(?:[A-Z0-9]|F(?:[1-9]|1[0-2]))$")


def parse_shortcut(sequence):
    """Only two-modifier global hotkeys, no OS/Win reserved keys."""
    parts = [part.strip().upper() for part in str(sequence or "").split('+')]
    if len(parts) not in (3, 4) or len(set(parts)) != len(parts):
        raise ValueError("Usa dos o tres modificadores y una tecla, por ejemplo Ctrl+Shift+O.")
    key = parts[-1]
    modifiers = parts[:-1]
    names = {"CTRL": MOD_CONTROL, "ALT": MOD_ALT, "SHIFT": MOD_SHIFT}
    if any(m not in names for m in modifiers) or len(modifiers) < 2 or not VALID_KEY.fullmatch(key):
        raise ValueError("Atajo inválido: combina Ctrl/Alt/Shift con una letra, número o F1–F12.")
    vk = ord(key) if len(key) == 1 else 0x70 + int(key[1:]) - 1
    mask = MOD_NOREPEAT
    for item in modifiers:
        mask |= names[item]
    canonical = '+'.join(title for code, title in (("CTRL", "Ctrl"), ("ALT", "Alt"), ("SHIFT", "Shift")) if code in modifiers) + '+' + key
    return canonical, mask, vk


def locate_rtss(custom_path="", environ=None):
    """Search only known install folders and uninstall registry entries, no entire-disk scan."""
    if os.name != 'nt':
        return None
    env = environ or os.environ
    candidates = [Path(custom_path)] if custom_path else []
    for name in ('ProgramFiles(x86)', 'ProgramFiles'):
        parent = env.get(name)
        if parent:
            root = Path(parent)
            candidates.extend((root / 'RivaTuner Statistics Server' / 'RTSS.exe',
                               root / 'MSI Afterburner' / 'RTSS' / 'RTSS.exe',
                               root / 'RivaTuner Statistics Server' / 'RTSS' / 'RTSS.exe'))
    try:
        import winreg
        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            for suffix in (r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall',
                           r'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall'):
                try:
                    with winreg.OpenKey(hive, suffix) as base:
                        count = winreg.QueryInfoKey(base)[0]
                        for i in range(min(count, 400)):
                            try:
                                with winreg.OpenKey(base, winreg.EnumKey(base, i)) as entry:
                                    name, _ = winreg.QueryValueEx(entry, 'DisplayName')
                                    if 'rivatuner statistics server' in str(name).lower():
                                        install, _ = winreg.QueryValueEx(entry, 'InstallLocation')
                                        if str(install).strip():
                                            candidates.append(Path(install) / 'RTSS.exe')
                            except (OSError, ValueError):
                                continue
                except OSError:
                    continue
    except ImportError:
        pass
    for candidate in candidates:
        try:
            if candidate.is_file() and candidate.name.lower() == 'rtss.exe':
                return candidate.resolve()
        except (OSError, ValueError):
            continue
    return None


def rtss_mapping_ready():
    if os.name != 'nt':
        return False
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenFileMappingW.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR)
    kernel.OpenFileMappingW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    handle = kernel.OpenFileMappingW(FILE_MAP_ALL_ACCESS, False, RTSS_MEMORY_NAME)
    if handle:
        kernel.CloseHandle(handle)
    return bool(handle)


def launch_rtss(custom_path):
    """Run only verified RTSS.exe without elevation; wait for its shared memory."""
    if os.name != 'nt':
        return False, "La integración con RivaTuner requiere Windows.", ''
    if rtss_mapping_ready():
        return True, "RTSS ya está ejecutándose.", ''
    binary = locate_rtss(custom_path)
    if not binary:
        return False, "No se encontró RTSS.exe. Instala RivaTuner Statistics Server o indica su ruta.", ''
    try:
        subprocess.Popen([str(binary)], cwd=str(binary.parent), close_fds=True,
                         creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except (OSError, ValueError) as exc:
        return False, f"Windows no pudo iniciar RTSS: {type(exc).__name__}.", str(binary)
    for _ in range(25):
        if rtss_mapping_ready():
            return True, "RTSS iniciado y comunicación disponible.", str(binary)
        time.sleep(0.2)
    return False, "RTSS se inició, pero aún no publicó su memoria compartida. Comprueba RTSS y reintenta.", str(binary)


def _api():
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.OpenFileMappingW.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR)
    k.OpenFileMappingW.restype = wintypes.HANDLE
    k.MapViewOfFile.argtypes = (wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.c_size_t)
    k.MapViewOfFile.restype = ctypes.c_void_p
    k.UnmapViewOfFile.argtypes = (ctypes.c_void_p,)
    k.CloseHandle.argtypes = (wintypes.HANDLE,)
    k.VirtualQuery.argtypes = (ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t)
    k.VirtualQuery.restype = ctypes.c_size_t
    k.InterlockedCompareExchange.argtypes = (ctypes.POINTER(ctypes.c_long), ctypes.c_long, ctypes.c_long)
    k.InterlockedCompareExchange.restype = ctypes.c_long
    k.InterlockedExchange.argtypes = (ctypes.POINTER(ctypes.c_long), ctypes.c_long)
    k.InterlockedExchange.restype = ctypes.c_long
    return k


def _mapped_region_size(k, address):
    buffer = ctypes.create_string_buffer(64)
    if not k.VirtualQuery(address, buffer, len(buffer)):
        return 0
    ptr_size = ctypes.sizeof(ctypes.c_void_p)
    base = ctypes.c_void_p.from_buffer_copy(buffer.raw, 0).value
    region_off = 24 if ptr_size == 8 else 12
    region = ctypes.c_size_t.from_buffer_copy(buffer.raw, region_off).value
    return max(0, (base or 0) + region - address)


def publish_osd(text, *, clear=False):
    """Own only CorePulse OSD slot; fails closed on missing/invalid RTSS mapping.

    Respects RTSS v2.14+ dwBusy lock. None means transient renderer busy.
    Never writes slot zero or another owner.
    """
    if os.name != 'nt':
        return False
    k = _api()
    mapping = k.OpenFileMappingW(FILE_MAP_ALL_ACCESS, False, RTSS_MEMORY_NAME)
    if not mapping:
        return False
    address = None
    try:
        address = k.MapViewOfFile(mapping, FILE_MAP_ALL_ACCESS, 0, 0, 0)
        if not address:
            return False
        available = _mapped_region_size(k, address)
        if available < 48:
            return False
        signature, version, _, _, _, size, offset, count, _ = struct.unpack_from('<9I', ctypes.string_at(address, 36))
        if signature != RTSS_SIGNATURE or version < 0x00020000 or version >= 0x00030000:
            return False
        if not (2 <= count <= 128 and 512 <= size <= 400000 and offset >= 36):
            return False
        if offset + count * size > available:
            return False
        extended = version >= 0x00020007 and size >= 4608
        cap = 4096 if extended else 256
        payload = str(text or '').encode('cp1252', errors='replace')[:cap-1] + b'\0'
        # Never wait on the RTSS renderer. If busy, try on next refresh.
        lock = ctypes.cast(address + RTSS_BUSY_OFFSET, ctypes.POINTER(ctypes.c_long)) if version >= 0x0002000e else None
        if lock is not None and k.InterlockedCompareExchange(lock, 1, 0) != 0:
            return None  # renderer currently owns the lock; retry next tick
        try:
            slot = 0
            for index in range(1, count):
                entry = address + offset + index * size
                owner = ctypes.string_at(entry + 256, 256).split(b'\0', 1)[0]
                if owner == OSD_OWNER:
                    slot = entry
                    break
            if slot == 0 and not clear:
                for index in range(1, count):
                    entry = address + offset + index * size
                    if not ctypes.string_at(entry + 256, 1).strip(b'\0'):
                        slot = entry
                        break
            if slot == 0:
                return bool(clear)   # already removed = hidden
            if clear:
                ctypes.memset(slot, 0, 512 if size < 4608 else 4608)
            else:
                ctypes.memmove(slot + (512 if extended else 0), payload, len(payload))
                ctypes.memmove(slot + 256, OSD_OWNER + b'\0', len(OSD_OWNER) + 1)
            frame = ctypes.c_uint32.from_address(address + RTSS_OSD_FRAME_OFFSET)
            frame.value = (frame.value + 1) & 0xFFFFFFFF
            return True
        finally:
            if lock is not None:
                k.InterlockedExchange(lock, 0)
    finally:
        if address:
            k.UnmapViewOfFile(address)
        k.CloseHandle(mapping)


def _format_metric(metrics, name, *, suffix='%', decimals=0):
    item = metrics.get(name)
    if isinstance(item, (float, int)) and not isinstance(item, bool) and item == item and 0 <= item <= (125 if 'Temp' in name else 100):
        return f'{item:.{decimals}f}{suffix}'
    return 'N/A'


def make_overlay_text(metrics, active_game, *, temperatures=True, compact=True, fps=None):
    """No guessed FPS. Readings only from Telemetry and PerformanceHealth."""
    metrics = metrics if isinstance(metrics, dict) else {}
    game = active_game if isinstance(active_game, dict) else {}
    title = re.sub(r'[<>\r\n\x00-\x1f]', ' ', str(game.get('name') or 'CorePulse'))[:54] if game.get('active') else 'CorePulse'
    cpu = f"CPU {_format_metric(metrics, 'cpuPercent')}"
    gpu = f"GPU {_format_metric(metrics, 'gpuPercent')}"
    ram = f"RAM {_format_metric(metrics, 'ramPercent')}"
    fps = fps if isinstance(fps, dict) and fps.get('quality') == 'VALID_RTSS' else {}
    fps_value = fps.get('fps')
    fps_text = f"FPS {fps_value:.1f}" if isinstance(fps_value, (int, float)) and not isinstance(fps_value, bool) else 'FPS N/A'
    fps_source = 'RTSS Shared Memory' if fps else 'RTSS sin muestra válida'
    if temperatures:
        cpu += f"  {_format_metric(metrics, 'cpuTemp', suffix='C', decimals=1)}"
        gpu += f"  {_format_metric(metrics, 'gpuTemp', suffix='C', decimals=1)}"
    if compact:
        return f'{title}\n{cpu} | {gpu}\n{ram} | {fps_text}'
    return f'{title}\n{cpu}\n{gpu}\n{ram}\n{fps_text} ({fps_source})'


class _Point(ctypes.Structure):
    _fields_ = [('x', ctypes.c_long), ('y', ctypes.c_long)]


class _Msg(ctypes.Structure):
    _fields_ = [('hwnd', wintypes.HWND), ('message', wintypes.UINT),
                ('wParam', ctypes.c_size_t), ('lParam', ctypes.c_ssize_t),
                ('time', wintypes.DWORD), ('pt', _Point), ('lPrivate', wintypes.DWORD)]


class GlobalHotkeys:
    """RegisterHotKey worker with its own message queue, no hooks/administrator."""

    def __init__(self, on_result, on_trigger):
        self._results = on_result
        self._trigger = on_trigger
        self._queue = queue.Queue()
        self._thread_id = None
        self._ready = threading.Event()
        self._thread = None
        self._sequences = {}

    def start(self):
        if os.name != 'nt':
            return
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._loop, name='CorePulse-RTSSHotkeys', daemon=True)
        self._thread.start()
        self._ready.wait(timeout=2)

    def change(self, action, sequence):
        self._queue.put((action, sequence))
        if os.name == 'nt' and self._thread_id:
            ctypes.windll.user32.PostThreadMessageW(self._thread_id, WM_APP_UPDATE, 0, 0)

    def _loop(self):
        user = ctypes.WinDLL('user32', use_last_error=True)
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        user.RegisterHotKey.argtypes = (wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT)
        user.RegisterHotKey.restype = wintypes.BOOL
        user.UnregisterHotKey.argtypes = (wintypes.HWND, ctypes.c_int)
        user.PostThreadMessageW.argtypes = (wintypes.DWORD, wintypes.UINT, ctypes.c_size_t, ctypes.c_ssize_t)
        user.PeekMessageW.argtypes = (ctypes.POINTER(_Msg), wintypes.HWND, wintypes.UINT, wintypes.UINT, wintypes.UINT)
        user.GetMessageW.argtypes = (ctypes.POINTER(_Msg), wintypes.HWND, wintypes.UINT, wintypes.UINT)
        user.GetMessageW.restype = wintypes.BOOL
        self._thread_id = kernel.GetCurrentThreadId()
        msg = _Msg()
        user.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)
        self._ready.set()
        try:
            while user.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == WM_HOTKEY:
                    self._trigger('show' if msg.wParam == HOTKEY_SHOW else 'hide')
                elif msg.message == WM_APP_UPDATE:
                    while not self._queue.empty():
                        action, seq = self._queue.get_nowait()
                        if action == 'quit':
                            return
                        ident = HOTKEY_SHOW if action == 'show' else HOTKEY_HIDE
                        previous = self._sequences.get(action)
                        if previous:
                            user.UnregisterHotKey(None, ident)
                        try:
                            canonical, flags, vk = parse_shortcut(seq)
                        except ValueError as e:
                            self._results(action, False, str(e), previous or '')
                            if previous:
                                _, old_flags, old_vk = parse_shortcut(previous)
                                user.RegisterHotKey(None, ident, old_flags, old_vk)
                            continue
                        if user.RegisterHotKey(None, ident, flags, vk):
                            self._sequences[action] = canonical
                            self._results(action, True, "Atajo global registrado.", canonical)
                        else:
                            error = ctypes.get_last_error()
                            if previous:
                                _, old_flags, old_vk = parse_shortcut(previous)
                                user.RegisterHotKey(None, ident, old_flags, old_vk)
                            self._results(action, False, "Windows rechazó el atajo (ocupado o reservado). Error %d." % error, previous or '')
        finally:
            for ident in (HOTKEY_SHOW, HOTKEY_HIDE):
                user.UnregisterHotKey(None, ident)
            self._thread_id = None

    def stop(self):
        if os.name != 'nt' or not self._thread_id:
            return
        self.change('quit', '')
        thread = self._thread
        if thread and thread is not threading.current_thread():
            thread.join(timeout=1)


# Solo interfaces visibles de tiendas de juegos, no servicios genéricos de Windows.
_LAUNCHER_EXES = frozenset({
    'steam.exe', 'epicgameslauncher.exe', 'riotclientservices.exe',
    'eadesktop.exe', 'origin.exe', 'xboxpcapp.exe', 'xboxapp.exe',
    'battle.net.exe', 'ubisoftconnect.exe', 'upc.exe', 'goggalaxy.exe',
})


def _interesting_process(info):
    """Señal de inicio de tienda/juego, no indicador de FPS ni juego en primer plano."""
    name = str(info.get('name') or '').casefold().strip()
    if name in _LAUNCHER_EXES:
        return True
    exe = str(info.get('exe') or '').replace('\\', '/').casefold()
    if not exe:
        return False
    # Usa el detector validado de Rendimiento: nunca trata launchers/anticheat
    # como juegos. Reconoce Steam, Epic, Riot, EA y Xbox por ruta+exe.
    try:
        from core.health.performance import _game_source, _EXCLUDED_NAMES, _EXCLUDED_PARTS
        if name in _EXCLUDED_NAMES or any(marker in name for marker in _EXCLUDED_PARTS):
            return False
        return _game_source(exe, name) is not None
    except (ImportError, OSError, ValueError):
        return False


def _scan_launch_triggers():
    """Observación ligera en trabajador: lista de procesos exactos nuevos."""
    found = set()
    for proc in psutil.process_iter(['pid', 'name', 'exe', 'create_time']):
        try:
            info = proc.info
            if _interesting_process(info):
                found.add((int(info['pid']), float(info.get('create_time') or 0)))
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, TypeError, ValueError):
            continue
    return found


class OverlayController(QObject):
    changed = Signal()
    hotkeyTriggered = Signal(str)
    hotkeyRegistration = Signal(str, bool, str, str)

    def __init__(self, telemetry, performance, parent=None):
        super().__init__(parent)
        self._telemetry = telemetry
        self._performance = performance
        self._fps_reader = RTSSFPSReader()
        self._settings = QSettings('CorePulse', 'CorePulseRebuild')
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='corepulse-rtss')
        self._future = None
        self._enabled = False
        self._closed = False
        self._launch_cancelled = False
        self._config = {
            'compact': self._settings.value('overlay/compact', True, type=bool),
            'temperatures': self._settings.value('overlay/temperatures', True, type=bool),
            'corner': self._settings.value('overlay/corner', 'top-right'),
            'showShortcut': self._settings.value('overlay/showShortcut', 'Ctrl+Shift+O'),
            'hideShortcut': self._settings.value('overlay/hideShortcut', 'Ctrl+Shift+P'),
            'rtssPath': self._settings.value('overlay/rtssPath', ''),
        }
        self._data = {**self._config, 'available': os.name == 'nt', 'running': False,
                      'active': False, 'busy': False, 'osdPublished': False, 'lastPublish': 'N/A', 'message': 'Overlay desactivado.',
                      'fps': None, 'fpsValue': 'N/A', 'fpsQuality': 'UNAVAILABLE',
                      'fpsMessage': 'Esperando una muestra fresca del proceso del juego desde RTSS.',
                      'hotkeyStatus': 'Registrando atajos…' if os.name == 'nt' else 'Atajos globales solo en Windows.'}
        self._poll = QTimer(self)
        self._poll.setInterval(250)
        self._poll.timeout.connect(self._complete_launch)
        self._push = QTimer(self)
        self._push.setInterval(1000)
        self._push.timeout.connect(self._publish)
        # El watcher solo prepara RTSS cuando *aparece* un launcher/juego nuevo.
        # Primera instantánea = baseline; abrir CorePulse no lanza RTSS.
        self._launch_watch = QTimer(self)
        self._launch_watch.setInterval(4500)
        self._launch_watch.timeout.connect(self._scan_launches)
        self._launch_scan_future = None
        self._launch_baseline = None
        self.hotkeyTriggered.connect(self._hotkey_triggered)
        self.hotkeyRegistration.connect(self._shortcut_result)
        self._hotkeys = GlobalHotkeys(self._emit_registration, self.hotkeyTriggered.emit)
        self._hotkeys.start()
        if os.name == 'nt':
            self._hotkeys.change('show', self._config['showShortcut'])
            self._hotkeys.change('hide', self._config['hideShortcut'])

    @Slot()
    def startAutoWatch(self):
        """Registrar lo que ya estaba abierto antes de activar el lanzamiento."""
        if self._closed or os.name != 'nt':
            return
        if not self._launch_watch.isActive():
            self._launch_watch.start()
        self._scan_launches()

    def _scan_launches(self):
        if self._closed or self._launch_scan_future is not None:
            return
        self._launch_scan_future = self._executor.submit(_scan_launch_triggers)
        QTimer.singleShot(250, self._finish_launch_scan)

    def _finish_launch_scan(self):
        future = self._launch_scan_future
        if self._closed or future is None:
            return
        if not future.done():
            QTimer.singleShot(250, self._finish_launch_scan)
            return
        self._launch_scan_future = None
        try:
            observed = future.result()
        except Exception:
            # No lanzar RTSS si una consulta de procesos falló.
            return
        previous = self._launch_baseline
        self._launch_baseline = observed
        if previous is None:
            return  # Nunca arrancar RTSS solo porque CorePulse acaba de abrir.
        if observed.difference(previous) and not self._enabled and not self._future:
            self.start()

    @Property('QVariantMap', notify=changed)
    def data(self):
        return self._data

    def _set(self, **values):
        self._data = {**self._data, **values}
        self.changed.emit()

    def _emit_registration(self, action, ok, message, seq):
        self.hotkeyRegistration.emit(action, ok, message, seq)

    @Slot(str, bool, str, str)
    def _shortcut_result(self, action, ok, message, seq):
        if ok:
            key = 'showShortcut' if action == 'show' else 'hideShortcut'
            self._config[key] = seq
            self._settings.setValue('overlay/' + key, seq)
            self._set(**{key: seq}, hotkeyStatus=message)
        else:
            self._set(hotkeyStatus=message)

    @Slot(str)
    def _hotkey_triggered(self, action):
        if action == 'show':
            self.start()
        elif action == 'hide':
            self.hide()

    @Slot(str, str)
    def setShortcut(self, action, value):
        if action not in ('show', 'hide'):
            return
        try:
            seq, _, _ = parse_shortcut(value)
        except ValueError as error:
            self._set(hotkeyStatus=str(error))
            return
        other = self._config['hideShortcut' if action == 'show' else 'showShortcut']
        if seq == other:
            self._set(hotkeyStatus='Mostrar y ocultar no pueden tener el mismo atajo.')
            return
        if os.name != 'nt':
            self._set(hotkeyStatus='Atajos globales solo disponibles en Windows.')
            return
        self._hotkeys.change(action, seq)

    @Slot(str)
    def setRtssPath(self, path):
        path = str(path or '').strip()
        if path.startswith('file:'):
            path = QUrl(path).toLocalFile()
        if Path(path).name.casefold() != 'rtss.exe' or not Path(path).is_file():
            self._set(message='Selecciona RTSS.exe de la instalación oficial de RivaTuner.')
            return
        self._config['rtssPath'] = path
        self._settings.setValue('overlay/rtssPath', path)
        self._set(rtssPath=path, message='Ubicación de RTSS guardada.')

    @Slot(str, bool)
    def setOption(self, option, enabled):
        if option not in ('compact', 'temperatures'):
            return
        self._config[option] = bool(enabled)
        self._settings.setValue('overlay/' + option, bool(enabled))
        self._set(**{option: bool(enabled)})
        if self._enabled:
            self._publish()

    @Slot(str)
    def setCorner(self, code):
        if code not in ('top-left', 'top-right', 'bottom-left', 'bottom-right'):
            return
        self._config['corner'] = code
        self._settings.setValue('overlay/corner', code)
        self._set(corner=code, message='Posición actualizada en vista previa. RTSS controla la posición final del OSD.')

    @Slot()
    def start(self):
        if self._closed:
            return
        if self._enabled:
            self._publish()
            return
        if self._future:
            return
        self._launch_cancelled = False
        self._set(busy=True, message='Iniciando RivaTuner Statistics Server…')
        self._future = self._executor.submit(launch_rtss, self._config['rtssPath'])
        self._poll.start()

    @Slot()
    def hide(self):
        self._launch_cancelled = True
        self._enabled = False
        self._push.stop()
        self._performance.stopGameWatch('overlay')
        published = publish_osd('', clear=True)
        self._fps_reader.close()
        self._set(fps=None, fpsValue='N/A', fpsQuality='UNAVAILABLE',
                  fpsMessage='Overlay oculto; esperando la próxima muestra de RTSS.')
        if published is None:
            QTimer.singleShot(100, lambda: not self._enabled and publish_osd('', clear=True))
        self._set(active=False, busy=False, osdPublished=False, message='Overlay oculto. RTSS sigue disponible en segundo plano.')

    def _complete_launch(self):
        if not self._future or not self._future.done():
            return
        try:
            ok, message, rtss_path = self._future.result()
        except Exception as error:
            ok, message, rtss_path = False, 'No se pudo iniciar RTSS (%s).' % type(error).__name__, ''
        self._future = None
        self._poll.stop()
        if self._closed:
            return
        if self._launch_cancelled:
            self._set(busy=False, running=bool(ok), active=False, osdPublished=False, message='Overlay oculto. RTSS permanece en segundo plano.')
            return
        self._enabled = bool(ok)
        self._set(busy=False, running=bool(ok), active=bool(ok), osdPublished=False, message=message, rtssPath=rtss_path or self._config['rtssPath'])
        if ok:
            self._performance.startGameWatch('overlay')
            self._push.start()
            self._publish()

    def _publish(self):
        if not self._enabled or self._closed:
            return
        metrics = self._telemetry.metrics or {}
        game = (self._performance.data or {}).get('activeGame') or {}
        fps = self._fps_reader.snapshot(game.get('pid') if game.get('active') else None)
        fps_value = fps.get('fps') if fps.get('quality') == 'VALID_RTSS' else None
        self._set(fps=fps_value, fpsValue=f'{fps_value:.1f} FPS' if fps_value is not None else 'N/A',
                  fpsQuality=fps.get('quality', 'UNAVAILABLE'), fpsMessage=fps.get('reason') or 'Medición directa de RTSS.')
        text = make_overlay_text(metrics, game, temperatures=self._config['temperatures'], compact=self._config['compact'], fps=fps)
        result = publish_osd(text)
        if result is None:  # RTSS renderer is temporarily busy; do not disconnect.
            return
        if result and not self._data.get('osdPublished'):
            self._set(osdPublished=True, lastPublish=time.strftime('%H:%M:%S'),
                      message='OSD publicado en RTSS. Si no se ve en el juego, revisa detección e inyección de RTSS.')
        if not result:
            # Do not fake success when RTSS mapping disappears / is not available.
            self._set(active=False, running=False, osdPublished=False, message='No fue posible publicar en RTSS. Comprueba que esté ejecutándose.')
            self._enabled = False
            self._push.stop()
            self._performance.stopGameWatch('overlay')

    @Slot()
    def close(self):
        self._closed = True
        self._push.stop()
        self._poll.stop()
        self._launch_watch.stop()
        self._performance.stopGameWatch('overlay')
        if self._enabled:
            publish_osd('', clear=True)
        self._enabled = False
        self._hotkeys.stop()
        self._fps_reader.close()
        self._executor.shutdown(wait=False, cancel_futures=True)
