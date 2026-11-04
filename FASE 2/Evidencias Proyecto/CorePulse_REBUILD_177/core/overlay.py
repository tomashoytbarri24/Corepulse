"""Control del overlay propio de CorePulse y atajos globales de Windows.

El host nativo dibuja en escritorio y los módulos gráficos lo hacen dentro
del juego. PresentMon, incluido en la distribución, ofrece FPS por ETW.
"""
from __future__ import annotations

import ctypes
from collections import deque
import json
import math
import mmap
import os
import psutil
import queue
import re
import subprocess
import struct
import sys
import threading
import time
from concurrent.futures.thread import ThreadPoolExecutor
from ctypes import wintypes
from pathlib import Path

from PySide6.QtCore import QObject, Property, QSettings, QTimer, Signal, Slot
from PySide6.QtGui import QGuiApplication
from core.health.fps import PresentMonFPSReader
from core.health.game_capture import normalize_design, METRICS

MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_NOREPEAT = 0x0001, 0x0002, 0x0004, 0x4000
WM_HOTKEY, WM_APP_UPDATE = 0x0312, 0x8000 + 136
HOTKEY_SHOW, HOTKEY_HIDE, HOTKEY_QUICK = 0xB3A1, 0xB3A2, 0xB3A3
HOTKEY_IDS = {"show": HOTKEY_SHOW, "hide": HOTKEY_HIDE, "quick": HOTKEY_QUICK, "problem": 0xB3A4}
HOTKEY_ACTIONS = {value: key for key, value in HOTKEY_IDS.items()}
VALID_KEY = re.compile(r"^(?:[A-Z0-9]|F(?:[1-9]|1[0-2]))$")
HOST_PATH = Path(__file__).resolve().parents[1] / 'bin' / 'CorePulseOverlayHost.exe'
GAME_STATE_NAME = 'Local\\CorePulseOverlayStateV4'
GAME_ACTION_NAME = 'Local\\CorePulseOverlayActionsV4'
GAME_MAGIC = 0x43504F34
DIAGNOSTIC_PATH = Path(os.environ.get('LOCALAPPDATA') or Path.home()) / 'CorePulse' / 'overlay_diagnostics.log'
_TRACE_LOCK = threading.Lock()
_NON_GAME_PROCESSES = frozenset({
    'explorer.exe', 'applicationframehost.exe', 'corepulseoverlayhost.exe',
    'snippingtool.exe', 'searchhost.exe', 'steamwebhelper.exe',
    'code.exe', 'chatgpt.exe', 'chrome.exe', 'msedge.exe', 'firefox.exe',
    'discord.exe', 'obs64.exe', 'vlc.exe', 'taskmgr.exe',
})
# Cargar código en un juego protegido puede costarle la cuenta al usuario. Las
# tres listas se comprueban juntas y siempre antes de tocar el proceso.
_PROTECTED_GAMES = frozenset({
    'cs2.exe', 'csgo.exe', 'dota2.exe', 'valorant-win64-shipping.exe',
    'league of legends.exe', 'fortniteclient-win64-shipping.exe', 'r5apex.exe',
    'r5apex_dx12.exe', 'overwatch.exe', 'tslgame.exe', 'rainbowsix.exe',
    'rainbowsix_be.exe', 'destiny2.exe', 'escapefromtarkov.exe', 'rust.exe',
    'cod.exe', 'modernwarfare.exe', 'robloxplayerbeta.exe', 'genshinimpact.exe',
    'gta5.exe', 'gta5_enhanced.exe', 'thefinals.exe', 'bf2042.exe', 'naraka.exe',
})
_ANTICHEAT_PROCESSES = frozenset({
    'vgc.exe', 'vgtray.exe', 'easyanticheat.exe', 'easyanticheat_eos.exe',
    'beservice.exe', 'faceit.exe', 'faceitservice.exe', 'faceitclient.exe',
    'eaanticheat.gameservice.exe', 'eaanticheat.gameservicelauncher.exe',
    'pnkbstra.exe', 'pnkbstrb.exe', 'gameguard.exe', 'xigncode.exe', 'ace-tray.exe',
})
_ANTICHEAT_MARKERS = (
    'easyanticheat', 'eac_launcher', 'battleye', 'beclient', 'beservice',
    'eaanticheat', 'xigncode', 'gameguard', 'equ8', 'vanguard', 'punkbuster',
    'pnkbstr', 'nprotect', 'hackshield', 'wellbia', 'ricochet', 'mhyprot',
    'acebase', 'ace-base',
)


def _trace_overlay(event, **details):
    """Small local transition log; never stores game paths or telemetry values."""
    try:
        with _TRACE_LOCK:
            DIAGNOSTIC_PATH.parent.mkdir(parents=True, exist_ok=True)
            if DIAGNOSTIC_PATH.exists() and DIAGNOSTIC_PATH.stat().st_size > 256_000:
                DIAGNOSTIC_PATH.replace(DIAGNOSTIC_PATH.with_suffix('.old.log'))
            record = {'time': time.strftime('%Y-%m-%d %H:%M:%S'), 'event': event, **details}
            with DIAGNOSTIC_PATH.open('a', encoding='utf-8') as stream:
                stream.write(json.dumps(record, ensure_ascii=False) + '\n')
    except (OSError, ValueError, TypeError):
        pass


class _GamePlan(ctypes.Structure):
    _pack_ = 1
    _fields_ = [('guid', ctypes.c_char * 64), ('name', ctypes.c_char * 64),
                ('active', ctypes.c_int32)]


class _GameState(ctypes.Structure):
    _pack_ = 1
    _fields_ = [('seqBegin', ctypes.c_int32), ('magic', ctypes.c_uint32),
                ('targetPid', ctypes.c_uint32), ('flags', ctypes.c_uint32),
                ('tickMs', ctypes.c_uint64), ('corner', ctypes.c_int32),
                ('cpu', ctypes.c_char * 32), ('gpu', ctypes.c_char * 32),
                ('ram', ctypes.c_char * 32), ('fps', ctypes.c_char * 32),
                ('cpuTemp', ctypes.c_char * 32), ('gpuTemp', ctypes.c_char * 32),
                ('cpuRgb', ctypes.c_uint32), ('gpuRgb', ctypes.c_uint32),
                ('cpuName', ctypes.c_char * 96), ('gpuName', ctypes.c_char * 96),
                ('ramInfo', ctypes.c_char * 48), ('diskName', ctypes.c_char * 96),
                ('diskInfo', ctypes.c_char * 48), ('diskPercent', ctypes.c_char * 16),
                ('cpuBrand', ctypes.c_char * 16), ('gpuBrand', ctypes.c_char * 16),
                ('themeBase', ctypes.c_uint32), ('themeDepth', ctypes.c_uint32),
                ('themeAccent', ctypes.c_uint32),
                ('planCount', ctypes.c_int32), ('plans', _GamePlan * 4),
                ('designScale', ctypes.c_int32), ('designOpacity', ctypes.c_int32),
                ('designGap', ctypes.c_int32), ('designX', ctypes.c_int32),
                ('designY', ctypes.c_int32), ('metricCount', ctypes.c_int32),
                ('metricOrder', ctypes.c_int32 * 5), ('showFrametime', ctypes.c_int32),
                ('frameCount', ctypes.c_int32), ('frameMs', ctypes.c_float * 120),
                ('captureStatus', ctypes.c_char * 80),
                ('seqEnd', ctypes.c_int32)]


class _MonitorInfo(ctypes.Structure):
    _fields_ = [('cbSize', wintypes.DWORD), ('rcMonitor', wintypes.RECT),
                ('rcWork', wintypes.RECT), ('dwFlags', wintypes.DWORD)]


def _utf8_field(value, size):
    return str(value or '').encode('utf-8', 'replace')[:size - 1]


def _foreground_fullscreen():
    if os.name != 'nt':
        return False
    user = ctypes.WinDLL('user32', use_last_error=True)
    user.GetForegroundWindow.restype = wintypes.HWND
    user.MonitorFromWindow.argtypes = (wintypes.HWND, wintypes.DWORD)
    user.MonitorFromWindow.restype = wintypes.HANDLE
    user.GetWindowRect.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.RECT))
    user.GetMonitorInfoW.argtypes = (wintypes.HANDLE, ctypes.POINTER(_MonitorInfo))
    hwnd = user.GetForegroundWindow()
    if not hwnd or user.IsIconic(hwnd):
        return False
    rect = wintypes.RECT()
    monitor = _MonitorInfo()
    monitor.cbSize = ctypes.sizeof(monitor)
    if not user.GetWindowRect(hwnd, ctypes.byref(rect)):
        return False
    screen = user.MonitorFromWindow(hwnd, 2)
    if not screen or not user.GetMonitorInfoW(screen, ctypes.byref(monitor)):
        return False
    target = monitor.rcMonitor
    return (abs(rect.left - target.left) <= 5 and
            abs(rect.top - target.top) <= 5 and
            abs(rect.right - target.right) <= 5 and
            abs(rect.bottom - target.bottom) <= 5)


def _renderer_candidates(modules):
    """A process may load several graphics DLLs; only one may present frames."""
    candidates = []
    if 'd3d12core.dll' in modules or 'd3d12.dll' in modules:
        candidates.append('D3D12')
    if 'd3d11.dll' in modules:
        candidates.append('D3D11')
    if 'd3d9.dll' in modules:
        candidates.append('D3D9')
    if 'd3d10.dll' in modules:
        candidates.append('D3D10')
    if 'opengl32.dll' in modules:
        candidates.append('OpenGL')
    return candidates


def _game_key(exe):
    """Permission applies to one installed executable, not to any homonym."""
    return os.path.normcase(str(exe or '')).strip()


def _folder_has_anticheat(exe):
    """Detect protection before its module is loaded, up to the game's root."""
    folder = Path(exe).parent
    for _ in range(4):
        if folder.parent == folder or folder.name.casefold() == 'common':
            return False
        try:
            with os.scandir(folder) as entries:
                if any(any(mark in entry.name.casefold() for mark in _ANTICHEAT_MARKERS)
                       for entry in entries):
                    return True
        except OSError:
            pass
        folder = folder.parent
    return False


def _anticheat_running():
    for process in psutil.process_iter(['name']):
        try:
            if str(process.info.get('name') or '').casefold() in _ANTICHEAT_PROCESSES:
                return True
        except (psutil.Error, TypeError):
            continue
    return False


def _game_is_protected(exe, modules=()):
    if Path(str(exe)).name.casefold() in _PROTECTED_GAMES:
        return True
    if any(any(mark in name for mark in _ANTICHEAT_MARKERS) for name in modules):
        return True
    return _folder_has_anticheat(exe) or _anticheat_running()


def _inject_game_hook(pid, tried=(), allowed=frozenset()):
    """Load one matching API only into a game the user authorized by path.

    The controller tries another API if it gets no frames. Authorization and
    protection are verified here, at the last step before opening the process.
    """
    try:
        process = psutil.Process(pid)
        if process.name().casefold() in _NON_GAME_PROCESSES:
            return 'NOT_GAME'
        exe = Path(process.exe())
        if _game_key(exe) not in allowed:
            return 'DESACTIVADO'
        modules = {Path(entry.path).name.casefold() for entry in process.memory_maps(grouped=False)
                   if entry.path}
        if _game_is_protected(exe, modules):
            return 'PROTECTED'
        candidates = _renderer_candidates(modules)
        if not candidates:
            return 'VULKAN_UNSUPPORTED' if 'vulkan-1.dll' in modules else 'NO_RENDERER'
        renderer = next((name for name in candidates if name not in tried), '')
        if not renderer:
            return 'NO_MORE_RENDERERS'
        _trace_overlay('renderer_selected', pid=pid, renderer=renderer,
                       candidates=candidates)
        with exe.open('rb') as stream:
            if stream.read(2) != b'MZ':
                return 'NO_PE'
            stream.seek(0x3c)
            offset = struct.unpack('<I', stream.read(4))[0]
            stream.seek(offset)
            if stream.read(4) != b'PE\0\0':
                return 'NO_PE'
            machine = struct.unpack('<H', stream.read(2))[0]
        arch = 'x64' if machine == 0x8664 else 'x86' if machine == 0x14c else ''
        if not arch:
            return 'ARCH_UNSUPPORTED'
        bin_dir = HOST_PATH.parent
        loader = bin_dir / f'CorePulseHookLoader-{arch}.exe'
        library = bin_dir / f'CorePulseGameHook{renderer}-{arch}.dll'
        if not loader.is_file() or not library.is_file():
            return 'COMPONENT_MISSING'
        result = subprocess.run([str(loader), str(pid), str(library)],
                                capture_output=True, timeout=12,
                                creationflags=subprocess.CREATE_NO_WINDOW, check=False)
        if result.returncode == 0:
            return f'LOADED_{renderer}'
        win_error = re.search(rb'WINERR=(\d+)', result.stderr or b'')
        suffix = f'_WINERR_{int(win_error.group(1))}' if win_error else ''
        return f'LOADER_{result.returncode}{suffix}'
    except (OSError, psutil.Error, ValueError, struct.error, subprocess.TimeoutExpired):
        return 'ACCESS_DENIED'


def _hook_description(status, error=0):
    if error:
        return {1: 'No se pudo conectar el dibujado al juego.',
                3: 'No se pudo iniciar la API gráfica dentro del juego.',
                4: 'La cola gráfica detectada no corresponde a la ventana del juego.',
                6: 'El juego cambió de contexto OpenGL; se detuvo el dibujo para no alterar su imagen.'}.get(
                    error, 'El módulo gráfico informó un error.')
    if status == 'CARGANDO':
        return 'Conectando el módulo gráfico al juego…'
    if status.startswith('LOADED_'):
        return 'Módulo cargado; esperando que el juego presente fotogramas.'
    loader_error = re.fullmatch(r'LOADER_(\d+)(?:_WINERR_(\d+))?', status)
    if loader_error:
        stage, win_error = loader_error.groups()
        description = {
            '7': 'Windows no permitió abrir el proceso del juego.',
            '8': 'El cargador y el juego tienen distinta arquitectura.',
            '9': 'Windows no permitió reservar memoria en el proceso del juego.',
            '10': 'Windows no permitió enviar la ruta del módulo al juego.',
            '12': 'Windows no permitió iniciar el módulo en el juego.',
            '13': 'Se agotó la espera al cargar el módulo.',
            '14': 'El juego rechazó la carga del módulo.',
        }.get(stage, 'No se pudo cargar el módulo gráfico en el juego.')
        return description + (f' Error de Windows {win_error}.' if win_error else '')
    return {
        'PENDIENTE': 'Abre un juego para iniciar la integración.',
        'DESACTIVADO': 'Módulo interno apagado: CorePulse no toca el proceso del juego y usa el overlay externo.',
        'PROTECTED': 'Antitrampas detectado: CorePulse no carga nada en este juego y usa el overlay externo.',
        'NO_RENDERER': 'No se detectó una API gráfica compatible.',
        'VULKAN_UNSUPPORTED': 'Vulkan aún no tiene módulo de dibujo propio.',
        'NOT_GAME': 'La ventana actual no es un juego.',
        'COMPONENT_MISSING': 'Falta un componente nativo del overlay.',
        'ARCH_UNSUPPORTED': 'La arquitectura del proceso no es compatible.',
        'NO_PE': 'No se pudo identificar el ejecutable del juego.',
        'ACCESS_DENIED': 'Windows no permitió inspeccionar o cargar el módulo.',
        'NO_FRAMES': 'El módulo se cargó, pero no recibió fotogramas de esa API gráfica.',
        'NO_MORE_RENDERERS': 'Se probaron las API gráficas detectadas sin recibir fotogramas.',
        'IPC_ERROR': 'No se pudo abrir la memoria compartida del overlay del juego.',
    }.get(status, 'No se pudo activar el módulo gráfico.')



def parse_shortcut(sequence):
    parts = [part.strip().upper() for part in str(sequence or "").split('+')]
    if len(parts) not in (2, 3, 4) or len(set(parts)) != len(parts):
        raise ValueError("Usa uno o más modificadores y una tecla, por ejemplo Shift+P.")
    key = parts[-1]
    modifiers = parts[:-1]
    names = {"CTRL": MOD_CONTROL, "ALT": MOD_ALT, "SHIFT": MOD_SHIFT}
    if any(m not in names for m in modifiers) or not VALID_KEY.fullmatch(key):
        raise ValueError("Atajo inválido: combina Ctrl, Alt o Shift con una letra, número o F1–F12.")
    vk = ord(key) if len(key) == 1 else 0x70 + int(key[1:]) - 1
    mask = MOD_NOREPEAT
    for item in modifiers:
        mask |= names[item]
    canonical = '+'.join(title for code, title in (("CTRL", "Ctrl"), ("ALT", "Alt"), ("SHIFT", "Shift")) if code in modifiers) + '+' + key
    return canonical, mask, vk


def _foreground_process():
    if os.name != 'nt':
        return 0, ''
    try:
        user = ctypes.WinDLL('user32', use_last_error=True)
        user.GetForegroundWindow.restype = wintypes.HWND
        user.GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
        window = user.GetForegroundWindow()
        if not window:
            return 0, ''
        pid = wintypes.DWORD()
        user.GetWindowThreadProcessId(window, ctypes.byref(pid))
        if not pid.value or pid.value == os.getpid():
            return 0, ''
        try:
            name = psutil.Process(pid.value).name()
        except psutil.Error:
            name = ''
        return int(pid.value), name
    except (OSError, AttributeError):
        return 0, ''


def _keep_host_above_windowed_game():
    """Reassert topmost without activating CorePulse or taking game focus."""
    if os.name != 'nt':
        return
    try:
        user = ctypes.WinDLL('user32', use_last_error=True)
        user.FindWindowW.argtypes = (wintypes.LPCWSTR, wintypes.LPCWSTR)
        user.FindWindowW.restype = wintypes.HWND
        user.SetWindowPos.argtypes = (wintypes.HWND, wintypes.HWND, ctypes.c_int,
                                     ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT)
        host = user.FindWindowW('CorePulseOverlayHost', 'CorePulse Overlay')
        if host:
            user.SetWindowPos(host, wintypes.HWND(-1), 0, 0, 0, 0,
                              0x0001 | 0x0002 | 0x0010)  # NOMOVE, NOSIZE, NOACTIVATE
    except (OSError, ValueError):
        pass


def _clean(value, limit=90):
    return re.sub(r'[\t\r\n\x00-\x1f]', ' ', str(value or 'N/A'))[:limit]


def _metric(metrics, name, suffix='%'):
    value = metrics.get(name)
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        return 'N/A'
    return (f'{value:.1f}' if suffix == ' °C' else f'{value:.0f}') + suffix


def _brand_colors(metrics):
    cpu = str(metrics.get('cpuName') or '').lower()
    gpu = str(metrics.get('gpuName') or '').lower()
    cpu_amd = 'amd' in cpu or 'ryzen' in cpu
    cpu_color = 'ED4248' if cpu_amd else '259BEF' if 'intel' in cpu else '29B7F0'
    gpu_color = ('EF874A' if cpu_amd else 'ED4248') if ('amd' in gpu or 'radeon' in gpu) else '76B900' if 'nvidia' in gpu else '259BEF' if 'intel' in gpu else 'A66BD6'
    return cpu_color, gpu_color


def _brand_name(name):
    name = str(name or '').lower()
    if 'nvidia' in name or 'geforce' in name:
        return 'NVIDIA'
    if 'amd' in name or 'ryzen' in name or 'radeon' in name:
        return 'AMD'
    if 'intel' in name or 'xeon' in name:
        return 'INTEL'
    return ''


def _capacity_info(metrics, used_key, total_key):
    used, total = metrics.get(used_key), metrics.get(total_key)
    if all(isinstance(value, (int, float)) and not isinstance(value, bool) and
           math.isfinite(value) and value >= 0 for value in (used, total)) and total > 0:
        return f'{used:.1f} / {total:.1f} GB'
    return 'N/A'


def _overlay_disk_name(metrics, storage):
    """Use the physical model mapped to the same volume as disk usage."""
    mount = str(metrics.get('diskLabel') or os.environ.get('SystemDrive') or 'C:')
    mount = mount.rstrip('\\/').upper() + '\\'
    data = (storage.data or {}) if storage is not None else {}
    for volume in data.get('volumes') or []:
        if str(volume.get('mount') or '').upper() != mount:
            continue
        physical = str(volume.get('physicalName') or '').strip()
        if physical and physical.casefold() not in ('n/a', 'unknown', 'none'):
            return physical
    telemetry_name = str(metrics.get('diskName') or '').strip()
    if telemetry_name and telemetry_name.casefold() not in ('n/a', 'unknown', 'none'):
        return telemetry_name
    return f'Unidad {mount}'


def _is_windows_admin():
    if os.name != 'nt':
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (OSError, AttributeError):
        return False


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
        self._thread = threading.Thread(target=self._loop, name='CorePulse-OverlayHotkeys', daemon=True)
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
                    action = HOTKEY_ACTIONS.get(msg.wParam)
                    if action:
                        self._trigger(action)
                elif msg.message == WM_APP_UPDATE:
                    while not self._queue.empty():
                        action, seq = self._queue.get_nowait()
                        if action == 'quit':
                            return
                        ident = HOTKEY_IDS.get(action)
                        if ident is None:
                            continue
                        previous = self._sequences.get(action)
                        try:
                            canonical, flags, vk = parse_shortcut(seq)
                        except ValueError as error:
                            self._results(action, False, str(error), previous or '')
                            continue
                        conflict = next((other for other, value in self._sequences.items()
                                         if other != action and value == canonical), None)
                        if conflict:
                            self._results(action, False, 'Ese atajo ya está asignado a otra acción.', previous or '')
                            continue
                        if previous:
                            user.UnregisterHotKey(None, ident)
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
            for ident in HOTKEY_IDS.values():
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
    sampleObserved = Signal(object)
    problemRequested = Signal()
    openRequested = Signal()
    hotkeyTriggered = Signal(str)
    hotkeyRegistration = Signal(str, bool, str, str)
    hostAction = Signal(str, str)

    def __init__(self, telemetry, performance, cleanup=None, storage=None, parent=None):
        super().__init__(parent)
        self._telemetry = telemetry
        self._performance = performance
        self._cleanup = cleanup
        self._storage = storage
        self._elevated = _is_windows_admin()
        self._fps_reader = PresentMonFPSReader()
        self._frame_history_enabled = False
        self._game_profile_base = None
        self._settings = QSettings('CorePulse', 'CorePulseRebuild')
        try:
            saved = json.loads(self._settings.value('overlay/designs', '{}'))
        except (ValueError, TypeError):
            saved = {}
        self._design_base = normalize_design(saved.get('default')) if isinstance(saved, dict) else normalize_design({})
        if not isinstance(saved, dict) or 'default' not in saved:
            previous_corner = str(self._settings.value('overlay/corner', 'top-right'))
            self._design_base.update(x=0 if 'left' in previous_corner else 1000,
                                     y=0 if 'top' in previous_corner else 1000)
        self._design_games = saved.get('games', {}) if isinstance(saved, dict) and isinstance(saved.get('games'), dict) else {}
        self._design_game = ''
        self._design = dict(self._design_base)
        self._frame_line = deque(maxlen=120)
        self._frame_line_pid = 0
        self._capture_status = ''
        self._capture_status_at = 0.0
        self._theme_colors = ('0F1828', '1B1025', '28B6EA')
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix='corepulse-games')
        self._game_state_map = None
        self._game_actions_map = None
        self._ipc_last_attempt = 0.0
        self._ipc_error = ''
        self._game_seq = 0
        self._inject_future = None
        self._hook_attempted_pid = 0
        self._hook_attempted_at = 0.0
        self._inject_result = 'PENDIENTE'
        self._manual_target_pid = 0
        self._tried_renderers = set()
        try:
            hook_games = json.loads(self._settings.value('overlay/hookGames', '[]'))
        except (ValueError, TypeError):
            hook_games = []
        self._hook_games = ({_game_key(item) for item in hook_games if isinstance(item, str)}
                            if isinstance(hook_games, list) else set())
        self._target_key = (0, '')
        self._last_target_pid = 0
        self._last_hook_ready = False
        self._last_desktop_mode = ''
        self._last_fps_mode = None
        self._visible_fps_pid = 0
        self._visible_fps_value = None
        self._visible_fps_at = 0.0
        self._host_raised_at = 0.0
        self._fullscreen_pid = 0
        self._fullscreen_seen_at = 0.0
        self._ensure_game_ipc()
        self._closed = False
        self._enabled = False
        self._host = None
        self._host_lock = threading.Lock()
        self._quick_started_overlay = False
        self._launch_baseline = None
        self._launch_scan_future = None
        self._config = {
            'compact': self._settings.value('overlay/compact', True, type=bool),
            'temperatures': self._settings.value('overlay/temperatures', True, type=bool),
            'corner': self._settings.value('overlay/corner', 'top-right'),
            'showShortcut': self._settings.value('overlay/showShortcut', 'Ctrl+Shift+O'),
            'hideShortcut': self._settings.value('overlay/hideShortcut', 'Ctrl+Shift+P'),
            'quickPanelShortcut': self._settings.value('overlay/quickPanelShortcut', 'Shift+F2'),
            'problemShortcut': self._settings.value('overlay/problemShortcut', 'Ctrl+Shift+F8'),
        }
        always_admin = self._settings.value('overlay/alwaysAdmin', False, type=bool)
        self._data = {**self._config, 'design': self._design, 'designScope': 'General', 'frameTimes': [], 'captureStatus': '', 'available': os.name == 'nt' and HOST_PATH.is_file(),
                      'running': False, 'active': False, 'busy': False,
                      'osdPublished': False, 'quickPanelVisible': False,
                      'quickPanelMode': 'native', 'lastPublish': 'N/A',
                      'renderMode': 'desktop', 'inGameHook': 'PENDIENTE',
                      'hookDetail': _hook_description('PENDIENTE'),
                      'lastGameName': 'N/A', 'lastGamePid': 0,
                      'lastGameHook': 'PENDIENTE', 'lastGameKey': '',
                      'lastGameAllowed': False, 'hookGameCount': len(self._hook_games),
                      'elevated': self._elevated, 'alwaysAdmin': always_admin,
                      'diagnosticPath': str(DIAGNOSTIC_PATH),
                      'ipcReady': self._game_state_map is not None and
                                  self._game_actions_map is not None,
                      'ipcError': self._ipc_error,
                      'message': 'Overlay propio desactivado.',
                      'fps': None, 'fpsValue': 'N/A', 'fpsQuality': 'UNAVAILABLE',
                      'fpsPermissionRequired': False,
                      'fpsMessage': 'Esperando fotogramas ETW de un juego.',
                      'presentMode': 'N/A', 'graphicsRuntime': 'N/A', 'exclusivePresentation': False,
                      'hotkeyStatus': 'Registrando atajos…' if os.name == 'nt' else 'Atajos globales solo en Windows.'}
        self._push = QTimer(self)
        self._push.setInterval(250)
        self._push.timeout.connect(self._publish)
        self._launch_watch = QTimer(self)
        self._launch_watch.setInterval(4500)
        self._launch_watch.timeout.connect(self._scan_launches)
        self.hotkeyTriggered.connect(self._hotkey_triggered)
        self.hotkeyRegistration.connect(self._shortcut_result)
        self.hostAction.connect(self._host_action)
        self._hotkeys = GlobalHotkeys(self._emit_registration, self.hotkeyTriggered.emit)
        self._hotkeys.start()
        if os.name == 'nt':
            for action, key in (('show', 'showShortcut'), ('hide', 'hideShortcut'),
                                ('quick', 'quickPanelShortcut'), ('problem', 'problemShortcut')):
                self._hotkeys.change(action, self._config[key])

    @Property('QVariantMap', notify=changed)
    def data(self):
        return self._data

    def setThemePalette(self, palette):
        """Receive the selected QML palette without changing hardware brand colors."""
        def color(value, fallback):
            value = str(value or '').lstrip('#')
            return value.upper() if re.fullmatch(r'[0-9A-Fa-f]{6}', value) else fallback
        self._theme_colors = (
            color(palette.get('bgMid'), '0F1828'),
            color(palette.get('bgEnd'), '1B1025'),
            color(palette.get('accent'), '28B6EA'),
        )
        if self._enabled:
            self._publish()

    def _set(self, **values):
        self._data = {**self._data, **values}
        self.changed.emit()

    def _ensure_game_ipc(self):
        if os.name != 'nt':
            return False
        if self._game_state_map is not None and self._game_actions_map is not None:
            return True
        if time.monotonic() - self._ipc_last_attempt < 5:
            return False
        self._ipc_last_attempt = time.monotonic()
        try:
            if self._game_state_map is None:
                self._game_state_map = mmap.mmap(-1, ctypes.sizeof(_GameState),
                                                 tagname=GAME_STATE_NAME)
            if self._game_actions_map is None:
                self._game_actions_map = mmap.mmap(-1, 24, tagname=GAME_ACTION_NAME)
                self._game_actions_map[:] = bytes(24)
            self._ipc_error = ''
            _trace_overlay('ipc_ready', size=ctypes.sizeof(_GameState),
                           administrator=self._elevated)
            return True
        except OSError as error:
            if self._game_actions_map is not None:
                self._game_actions_map.close()
                self._game_actions_map = None
            self._ipc_error = f'{type(error).__name__}: {getattr(error, "winerror", None)}'
            _trace_overlay('ipc_error', error=self._ipc_error)
            return False

    def _emit_registration(self, action, ok, message, seq):
        self.hotkeyRegistration.emit(action, ok, message, seq)

    @Slot(str, bool, str, str)
    def _shortcut_result(self, action, ok, message, seq):
        if ok:
            key = {'show': 'showShortcut', 'hide': 'hideShortcut',
                   'quick': 'quickPanelShortcut', 'problem': 'problemShortcut'}.get(action)
            if key:
                self._config[key] = seq
                self._settings.setValue('overlay/' + key, seq)
                self._set(**{key: seq}, hotkeyStatus=message)
        else:
            self._set(hotkeyStatus=message)

    @Slot(str)
    def _hotkey_triggered(self, action):
        if action == 'problem':
            self.problemRequested.emit()
            return
        if action == 'show':
            # An explicit shortcut also works for games outside known stores.
            pid, name = _foreground_process()
            self._manual_target_pid = pid if name.casefold() not in _NON_GAME_PROCESSES else 0
            self.start()
        elif action == 'hide':
            self.hide()
        elif action == 'quick':
            if not self._data.get('quickPanelVisible'):
                pid, name = _foreground_process()
                self._manual_target_pid = pid if name.casefold() not in _NON_GAME_PROCESSES else 0
            self.toggleQuickPanel()

    @Slot(str, str)
    def setShortcut(self, action, value):
        if action not in ('show', 'hide', 'quick', 'problem'):
            return
        try:
            seq, _, _ = parse_shortcut(value)
        except ValueError as error:
            self._set(hotkeyStatus=str(error))
            return
        for other_action, other_key in (('show', 'showShortcut'), ('hide', 'hideShortcut'),
                                        ('quick', 'quickPanelShortcut'), ('problem', 'problemShortcut')):
            if other_action != action and seq == self._config[other_key]:
                self._set(hotkeyStatus='Cada acción necesita un atajo distinto.')
                return
        self._hotkeys.change(action, seq)

    def _read_host(self, process):
        try:
            for raw in process.stdout:
                action, _, value = raw.rstrip('\r\n').partition('\t')
                if action in ('APPLY', 'RAM', 'CLOSE', 'OPEN', 'RECORD'):
                    self.hostAction.emit(action, value)
        except (OSError, UnicodeError):
            pass

    @Slot(str, str)
    def _host_action(self, action, value):
        if action == 'CLOSE':
            self.setQuickPanelVisible(False)
        elif action == 'OPEN':
            self.setQuickPanelVisible(False)
            self.openRequested.emit()
        elif action == 'RECORD':
            self.problemRequested.emit()
        elif action == 'RAM' and self._cleanup is not None:
            if not (self._cleanup.data or {}).get('busy'):
                self._cleanup.cleanRamQuick()
        elif action == 'APPLY':
            performance = self._performance.data or {}
            allowed = {str(plan.get('guid')) for plan in performance.get('plans') or []
                       if isinstance(plan, dict)}
            if value in allowed and not performance.get('busy') and performance.get('autoPowerStatus') != 'ACTIVO':
                self._performance.applyPlan(value)
        self._publish()

    def _ensure_host(self):
        if self._host is not None and self._host.poll() is None:
            return True
        if os.name != 'nt' or not HOST_PATH.is_file():
            self._set(message='Falta el componente nativo CorePulseOverlayHost.exe.')
            return False
        try:
            self._host = subprocess.Popen([str(HOST_PATH)], stdin=subprocess.PIPE,
                                          stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                          text=True, encoding='utf-8', errors='replace',
                                          bufsize=1, creationflags=subprocess.CREATE_NO_WINDOW)
        except OSError as error:
            self._set(message='No se pudo iniciar el componente gráfico: ' + type(error).__name__)
            _trace_overlay('host_error', error=type(error).__name__)
            return False
        _trace_overlay('host_started', pid=self._host.pid)
        threading.Thread(target=self._read_host, args=(self._host,),
                         name='CorePulse-OverlayHost', daemon=True).start()
        return True

    def _send(self, line):
        process = self._host
        if process is None or process.poll() is not None:
            return False
        try:
            with self._host_lock:
                process.stdin.write(line + '\n')
                process.stdin.flush()
            return True
        except (OSError, ValueError):
            self._set(active=False, running=False, osdPublished=False,
                      message='Se perdió la conexión con el overlay propio.')
            return False

    def _game_actions(self, pid):
        actions = self._game_actions_map
        if actions is None:
            return False, None, 0, 0
        try:
            code, hooked, error, milli, frame_tick, source = struct.unpack_from('<iiiiii', actions)
            now = ctypes.windll.kernel32.GetTickCount64
            now.restype = ctypes.c_ulonglong
            age = (int(now()) - (frame_tick & 0xffffffff)) & 0xffffffff
            ready = hooked == pid and pid > 0 and age <= 1500
            if code:
                actions[0:4] = bytes(4)
                if hooked == pid:
                    self._dispatch_game_action(code)
            return ready, milli / 1000.0 if ready and 0 < milli < 1000000 else None, error, source
        except (OSError, ValueError, struct.error):
            return False, None, 0, 0

    def _dispatch_game_action(self, code):
        if code == 1:
            QTimer.singleShot(0, lambda: self.setQuickPanelVisible(False))
        elif code == 2:
            QTimer.singleShot(0, lambda: self._host_action('RAM', ''))
        elif code == 3:
            QTimer.singleShot(0, lambda: self._host_action('OPEN', ''))
        elif code == 4:
            QTimer.singleShot(0, self.problemRequested.emit)
        elif 100 <= code < 104:
            plans = [plan for plan in ((self._performance.data or {}).get('plans') or [])
                     if isinstance(plan, dict) and plan.get('guid')][:4]
            index = code - 100
            if index < len(plans):
                guid = str(plans[index].get('guid') or '')
                if guid:
                    QTimer.singleShot(0, lambda guid=guid: self._host_action('APPLY', guid))

    def _write_game_state(self, pid, metrics, fps_value, cpu_color, gpu_color, plans,
                          draw_inside=False):
        shared = self._game_state_map
        if shared is None:
            return
        snapshot = _GameState()
        self._game_seq = (self._game_seq + 2) & 0x7ffffffe
        snapshot.seqBegin = self._game_seq
        snapshot.seqEnd = self._game_seq
        snapshot.magic = GAME_MAGIC
        snapshot.targetPid = pid
        snapshot.flags = ((1 if self._enabled else 0) |
                          (2 if self._data.get('quickPanelVisible') else 0) |
                          (4 if self._config['temperatures'] else 0) |
                          (8 if self._config['compact'] else 0) |
                          (16 if draw_inside else 0))
        tick = ctypes.windll.kernel32.GetTickCount64
        tick.restype = ctypes.c_ulonglong
        snapshot.tickMs = int(tick())
        snapshot.corner = {'top-left': 0, 'top-right': 1,
                           'bottom-left': 2, 'bottom-right': 3}.get(self._config['corner'], 1)
        snapshot.cpu = _utf8_field(_metric(metrics, 'cpuPercent'), 32)
        snapshot.gpu = _utf8_field(_metric(metrics, 'gpuPercent'), 32)
        snapshot.ram = _utf8_field(_metric(metrics, 'ramPercent'), 32)
        snapshot.fps = _utf8_field(f'{fps_value:.1f}' if fps_value is not None else 'N/A', 32)
        snapshot.cpuTemp = _utf8_field(_metric(metrics, 'cpuTemp', ' °C'), 32)
        snapshot.gpuTemp = _utf8_field(_metric(metrics, 'gpuTemp', ' °C'), 32)
        snapshot.cpuRgb = int(cpu_color, 16)
        snapshot.gpuRgb = int(gpu_color, 16)
        snapshot.cpuName = _utf8_field(metrics.get('cpuName') or 'Procesador N/A', 96)
        snapshot.gpuName = _utf8_field(metrics.get('gpuName') or 'Gráfica N/A', 96)
        snapshot.ramInfo = _utf8_field(_capacity_info(metrics, 'ramUsed', 'ramTotal'), 48)
        snapshot.diskName = _utf8_field(_overlay_disk_name(metrics, self._storage), 96)
        snapshot.diskInfo = _utf8_field(_capacity_info(metrics, 'diskUsed', 'diskTotal'), 48)
        snapshot.diskPercent = _utf8_field(_metric(metrics, 'diskPercent'), 16)
        snapshot.cpuBrand = _utf8_field(_brand_name(metrics.get('cpuName')), 16)
        snapshot.gpuBrand = _utf8_field(_brand_name(metrics.get('gpuName')), 16)
        design = self._design
        snapshot.designScale = design['scale']
        snapshot.designOpacity = design['opacity']
        snapshot.designGap = design['gap']
        snapshot.designX, snapshot.designY = design['x'], design['y']
        snapshot.metricCount = len(design['metrics'])
        for index, key in enumerate(design['metrics']):
            snapshot.metricOrder[index] = METRICS.index(key)
        snapshot.showFrametime = int(design['frametime'])
        snapshot.frameCount = len(self._frame_line)
        for index, (_, ms) in enumerate(self._frame_line):
            snapshot.frameMs[index] = ms
        snapshot.captureStatus = _utf8_field(self._capture_status, 80)
        snapshot.themeBase = int(self._theme_colors[0], 16)
        snapshot.themeDepth = int(self._theme_colors[1], 16)
        snapshot.themeAccent = int(self._theme_colors[2], 16)
        usable = [plan for plan in plans if isinstance(plan, dict) and plan.get('guid')][:4]
        snapshot.planCount = len(usable)
        for index, plan in enumerate(usable):
            snapshot.plans[index].guid = _utf8_field(plan['guid'], 64)
            snapshot.plans[index].name = _utf8_field(plan.get('name') or 'Plan de Windows', 64)
            snapshot.plans[index].active = int(bool(plan.get('active')))
        raw = ctypes.string_at(ctypes.addressof(snapshot), ctypes.sizeof(snapshot))
        try:
            shared[0:4] = struct.pack('<i', self._game_seq | 1)
            shared[4:len(raw)-4] = raw[4:-4]
            shared[len(raw)-4:len(raw)] = raw[-4:]
            shared[0:4] = raw[0:4]
        except (OSError, ValueError):
            pass

    def _fps_for_display(self, pid, measured, now):
        """Keep an exact observed value readable; session samples stay live."""
        if (pid != self._visible_fps_pid or measured is None or
                self._visible_fps_value is None or now - self._visible_fps_at >= 1.2):
            self._visible_fps_pid = pid
            self._visible_fps_value = measured
            self._visible_fps_at = now
        return self._visible_fps_value

    def _schedule_game_hook(self, pid, failed=False):
        if (not pid or self._game_state_map is None or self._game_actions_map is None or
                self._inject_future is not None):
            return
        if self._hook_attempted_pid != pid:
            self._tried_renderers.clear()
            self._inject_result = 'PENDIENTE'
        else:
            elapsed = time.monotonic() - self._hook_attempted_at
            if self._inject_result.startswith('LOADED_'):
                if elapsed < 6 and not failed:
                    return
                self._tried_renderers.add(self._inject_result[7:])
                self._inject_result = 'NO_FRAMES'
            elif self._inject_result == 'NO_RENDERER':
                if elapsed < 15:
                    return
            elif self._inject_result not in ('PENDIENTE', 'NO_FRAMES'):
                return
        self._hook_attempted_pid = pid
        self._hook_attempted_at = time.monotonic()
        if self._game_actions_map is not None:
            self._game_actions_map[:] = bytes(24)
        self._inject_result = 'CARGANDO'
        _trace_overlay('hook_attempt', pid=pid, skip=sorted(self._tried_renderers))
        self._inject_future = self._executor.submit(_inject_game_hook, pid, tuple(self._tried_renderers),
                                                    frozenset(self._hook_games))
        QTimer.singleShot(300, self._finish_game_hook)

    def _finish_game_hook(self):
        future = self._inject_future
        if self._closed or future is None:
            return
        if not future.done():
            QTimer.singleShot(300, self._finish_game_hook)
            return
        self._inject_future = None
        try:
            self._inject_result = future.result()
        except Exception:
            self._inject_result = 'ERROR'
        _trace_overlay('hook_result', pid=self._hook_attempted_pid, result=self._inject_result)
        self._set(inGameHook=self._inject_result)

    @Slot()
    def startAutoWatch(self):
        if self._closed or os.name != 'nt':
            return
        # Keep the renderer ready even when the game was opened before CorePulse
        # or was installed outside one of the known launcher directories.
        self.start()
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
            return
        previous = self._launch_baseline
        self._launch_baseline = observed
        if previous is not None and observed.difference(previous) and not self._enabled:
            self.start()

    @Slot()
    def start(self):
        if self._closed or self._enabled:
            return
        if not self._ensure_host():
            return
        self._ensure_game_ipc()
        self._enabled = True
        self._performance.startGameWatch('overlay')
        self._push.start()
        self._set(running=True, active=True, message='Overlay propio activo.')
        self._publish()

    @Slot()
    def hide(self):
        self._enabled = False
        self._quick_started_overlay = False
        self._push.stop()
        self._performance.stopGameWatch('overlay')
        self._fps_reader.close()
        self._frame_line.clear()
        self.sampleObserved.emit(dict(time=time.monotonic(), pid=0, frames=[]))
        self._write_game_state(0, {}, None, '29B7F0', 'A66BD6', [])
        if self._game_actions_map is not None:
            self._game_actions_map[:] = bytes(24)
        self._send('MODE\tHIDDEN')
        self._set(active=False, osdPublished=False, quickPanelVisible=False,
                  fps=None, fpsValue='N/A', fpsQuality='UNAVAILABLE',
                  fpsMessage='Overlay oculto.', presentMode='N/A', graphicsRuntime='N/A',
                  exclusivePresentation=False, hookDetail='Overlay oculto.',
                  message='Overlay oculto.')

    @Slot()
    def toggleQuickPanel(self):
        self.setQuickPanelVisible(not self._data.get('quickPanelVisible', False))

    @Slot(bool)
    def setQuickPanelVisible(self, visible):
        visible = bool(visible)
        if visible == bool(self._data.get('quickPanelVisible', False)):
            return
        if visible:
            self._quick_started_overlay = not self._enabled
            if not self._enabled:
                self.start()
            if not self._enabled:
                self._quick_started_overlay = False
                return
            self._set(quickPanelVisible=True, quickPanelMode='native')
            performance = self._performance.data or {}
            if performance.get('lastUpdate') == 'N/A' and not performance.get('busy'):
                self._performance.refresh()
        else:
            temporary = self._quick_started_overlay
            self._quick_started_overlay = False
            self._set(quickPanelVisible=False)
            if temporary:
                self.hide()
        self._publish()

    @Slot(str, bool)
    def setOption(self, option, enabled):
        if option not in ('compact', 'temperatures'):
            return
        if self._game_profile_base is not None:
            self._game_profile_base[option] = bool(enabled)
        self._config[option] = bool(enabled)
        self._settings.setValue('overlay/' + option, bool(enabled))
        self._set(**{option: bool(enabled)})
        self._publish()

    @Slot(str)
    def setCorner(self, code):
        if code not in ('top-left', 'top-right', 'bottom-left', 'bottom-right'):
            return
        if self._game_profile_base is not None:
            self._game_profile_base['corner'] = code
        self._config['corner'] = code
        self._settings.setValue('overlay/corner', code)
        self._set(corner=code, message='Posición del overlay actualizada.')
        self._send('CORNER\t' + code)
        self.setDesign({**self._design, 'x': 0 if 'left' in code else 1000,
                        'y': 0 if 'top' in code else 1000})

    def setCaptureStatus(self, text):
        self._capture_status = text
        self._capture_status_at = time.monotonic()
        self._set(captureStatus=text)

    def setDesignGame(self, key):
        self._design_game = str(key or '')
        self._design = normalize_design(self._design_games.get(self._design_game, self._design_base))
        self._set(design=self._design, designScope='Juego actual' if self._design_game in self._design_games else 'General')

    @Slot(str)
    def previewDesignGame(self, key):
        self._design = normalize_design(self._design_games.get(key, self._design_base))
        self._set(design=self._design, designScope='Juego guardado' if key in self._design_games else 'General')
        self._publish()

    @Slot('QVariantMap')
    def setDesign(self, value):
        self._design = normalize_design(value)
        self._set(design=self._design, designScope='Sin guardar')
        self._publish()

    @Slot(str)
    def saveDesign(self, game_key):
        if game_key:
            if len(game_key) > 600:
                return
            self._design_games[game_key] = dict(self._design)
        else:
            self._design_base = dict(self._design)
        self._settings.setValue('overlay/designs', json.dumps(dict(default=self._design_base, games=self._design_games)))
        self._set(designScope='Juego guardado' if game_key else 'General guardado', message='Diseño de overlay guardado.')

    @Slot(str)
    def inheritDesign(self, game_key):
        if not game_key:
            return
        self._design_games.pop(game_key, None)
        self._settings.setValue('overlay/designs', json.dumps(dict(default=self._design_base, games=self._design_games)))
        self._design = dict(self._design_base)
        self._set(design=self._design, designScope='General', message='Este juego vuelve a usar el diseño general.')
        self._publish()

    @Slot()
    def resetDesign(self):
        self.setDesign(normalize_design({}))

    def setFrameHistoryEnabled(self, enabled):
        """Comparte la captura ETW existente con el historial de partidas."""
        self._frame_history_enabled = bool(enabled)

    def takeFrameIntervals(self, pid):
        return self._fps_reader.take_frame_intervals(int(pid or 0))

    def applyGameProfile(self, corner='', temperatures='inherit'):
        if self._game_profile_base is None:
            self._game_profile_base = {key: self._config[key]
                                       for key in ('corner', 'temperatures', 'compact')}
        base = self._game_profile_base
        chosen_corner = corner if corner in ('top-left', 'top-right', 'bottom-left', 'bottom-right') else base['corner']
        chosen_temp = base['temperatures'] if temperatures == 'inherit' else temperatures == 'on'
        self._config.update(corner=chosen_corner, temperatures=chosen_temp)
        if corner in ('top-left', 'top-right', 'bottom-left', 'bottom-right') and self._design_game not in self._design_games:
            self._design = {**self._design, 'x': 0 if 'left' in corner else 1000,
                            'y': 0 if 'top' in corner else 1000}
            self._data['design'] = self._design
        self._set(corner=chosen_corner, temperatures=chosen_temp)
        self._send('CORNER\t' + chosen_corner)

    def clearGameProfile(self):
        if self._game_profile_base is None:
            return
        base = self._game_profile_base
        self._game_profile_base = None
        self._config.update(base)
        self._set(corner=base['corner'], temperatures=base['temperatures'], compact=base['compact'])
        self._send('CORNER\t' + base['corner'])

    @Slot()
    def copyDiagnostics(self):
        """Copy the recent local transitions after leaving a game."""
        try:
            lines = DIAGNOSTIC_PATH.read_text(encoding='utf-8').splitlines()[-30:]
        except OSError:
            lines = []
        summary = ('CorePulse overlay\n' +
                   f'Último juego: {self._data.get("lastGameName")} '
                   f'PID {self._data.get("lastGamePid")} · '
                   f'{self._data.get("lastGameHook")}\n' +
                   '\n'.join(lines))
        clipboard = QGuiApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(summary)
            self._set(message='Diagnóstico del overlay copiado al portapapeles.')

    def _pid_game_key(self, pid):
        if self._target_key[0] != pid:
            try:
                key = _game_key(psutil.Process(pid).exe()) if pid else ''
            except (psutil.Error, OSError):
                key = ''
            self._target_key = (pid, key)
        return self._target_key[1]

    def _store_hook_games(self):
        self._settings.setValue('overlay/hookGames', json.dumps(sorted(self._hook_games)))
        self._inject_result = 'PENDIENTE'
        self._hook_attempted_pid = 0
        self._tried_renderers.clear()

    @Slot(bool)
    def setHookAllowed(self, allowed):
        """Explicit opt-in for the last game; a protected game is always refused."""
        key = str(self._data.get('lastGameKey') or '')
        if not key:
            self._set(message='Abre el juego una vez para poder elegirlo.')
            return
        if allowed and _game_is_protected(key):
            self._set(lastGameAllowed=False, lastGameHook='PROTECTED',
                      hookDetail=_hook_description('PROTECTED'),
                      message='Este juego tiene antitrampas; el módulo interno sigue bloqueado.')
            return
        if allowed:
            self._hook_games.add(key)
        else:
            self._hook_games.discard(key)
        self._store_hook_games()
        self._set(lastGameAllowed=bool(allowed), hookGameCount=len(self._hook_games),
                  message='Módulo interno permitido para este juego.' if allowed else
                          'Módulo interno apagado. Si ya estaba cargado, se retira al cerrar el juego.')

    @Slot()
    def clearHookGames(self):
        self._hook_games.clear()
        self._store_hook_games()
        self._set(lastGameAllowed=False, hookGameCount=0,
                  message='Se quitaron todos los permisos del módulo interno.')

    @Slot(bool)
    def setAlwaysAdmin(self, enabled):
        self._settings.setValue('overlay/alwaysAdmin', bool(enabled))
        self._settings.sync()
        self._set(alwaysAdmin=bool(enabled))

    @Slot()
    def restartElevated(self):
        """User-initiated UAC restart for ETW FPS, CPU sensors and deep cleanup."""
        if os.name != 'nt' or self._elevated:
            return
        project = Path(__file__).resolve().parents[1]
        shell = ctypes.WinDLL('shell32', use_last_error=True)
        shell.ShellExecuteW.argtypes = (wintypes.HWND, wintypes.LPCWSTR,
                                       wintypes.LPCWSTR, wintypes.LPCWSTR,
                                       wintypes.LPCWSTR, ctypes.c_int)
        shell.ShellExecuteW.restype = ctypes.c_void_p
        try:
            launched = shell.ShellExecuteW(None, 'runas', sys.executable,
                                            '' if getattr(sys, 'frozen', False) else subprocess.list2cmdline([str(project / 'main.py')]),
                                            str(project), 1)
        except (OSError, ValueError):
            launched = 0
        if launched and launched > 32:
            self._set(message='Reiniciando CorePulse con permisos completos…')
            QTimer.singleShot(500, QGuiApplication.quit)
        else:
            self._set(message='CorePulse sigue abierto; Windows no autorizó el reinicio.')

    def _publish(self):
        if self._closed or not self._enabled or not self._ensure_host():
            return
        ipc_ready = self._ensure_game_ipc()
        if ipc_ready != bool(self._data.get('ipcReady')) or self._ipc_error != self._data.get('ipcError'):
            self._set(ipcReady=ipc_ready, ipcError=self._ipc_error)
        metrics = self._telemetry.metrics or {}
        foreground_pid, foreground_name = _foreground_process()
        pid = 0 if foreground_name.casefold() in _NON_GAME_PROCESSES else foreground_pid
        raw_fullscreen = bool(pid and _foreground_fullscreen())
        now = time.monotonic()
        if raw_fullscreen:
            self._fullscreen_pid = pid
            self._fullscreen_seen_at = now
        # Some games briefly report a border or transition rect during Present.
        # Keep the in-game surface selected until the geometry settles; a
        # different foreground PID still switches immediately.
        fullscreen = raw_fullscreen or bool(pid and pid == self._fullscreen_pid and
                                            now - self._fullscreen_seen_at < 1.5)
        performance = self._performance.data or {}
        detected_game = any(isinstance(game, dict) and game.get('active') and
                            game.get('pid') == pid for game in
                            (performance.get('probableGames') or []))
        if pid != self._manual_target_pid:
            self._manual_target_pid = 0
        target_pid = pid if (fullscreen or detected_game or
                             (pid and pid == self._manual_target_pid)) else 0
        if target_pid != self._last_target_pid:
            _trace_overlay('target', pid=target_pid, name=foreground_name if target_pid else '',
                           fullscreen=fullscreen, detected=detected_game)
            self._last_target_pid = target_pid
            self._last_hook_ready = False
        hook_allowed = bool(target_pid and self._pid_game_key(target_pid) in self._hook_games)
        hook_ready, hook_fps, hook_error, hook_source = self._game_actions(target_pid)
        if not hook_allowed:
            # A revoked module stays loaded until the game exits, but inert.
            hook_ready, hook_fps, hook_error, hook_source = False, None, 0, 0
        if hook_ready != self._last_hook_ready:
            _trace_overlay('frames' if hook_ready else 'frames_lost', pid=target_pid,
                           error=hook_error)
            self._last_hook_ready = hook_ready
        if target_pid and not hook_ready and hook_allowed:
            self._schedule_game_hook(target_pid, failed=bool(hook_error))
        hook_state = ('CON FOTOGRAMAS' if hook_ready else
                      'IPC_ERROR' if not ipc_ready else
                      f'ERROR_{hook_error}' if hook_error else
                      self._inject_result if hook_allowed else 'DESACTIVADO')
        use_hook_fps = hook_ready and hook_fps is not None
        # The OSD may use the hook's FPS; ETW remains the independent source of
        # individual intervals for frametime, session 1% low and problem records.
        fps = self._fps_reader.snapshot(target_pid)
        fps_mode = (target_pid, 'VALID_HOOK' if use_hook_fps else fps.get('quality', 'UNAVAILABLE'),
                    fps.get('presentMode', 'N/A'), bool(fps.get('exclusive', False)),
                    bool(fps.get('permissionRequired', False)), fps.get('reason', ''))
        if target_pid and fps_mode != self._last_fps_mode:
            _trace_overlay('presentation', pid=target_pid, quality=fps_mode[1],
                           mode=fps_mode[2], exclusive=fps_mode[3],
                           permissionRequired=fps_mode[4], reason=fps_mode[5])
        self._last_fps_mode = fps_mode if target_pid else None
        value = hook_fps if use_hook_fps else (fps.get('fps') if fps.get('quality') == 'VALID_ETW' else None)
        visible_fps = self._fps_for_display(target_pid, value, now)
        quality = ('ESTIMATED_SCENE' if hook_source == 2 else 'VALID_HOOK') if use_hook_fps else fps.get('quality', 'UNAVAILABLE')
        reason = (('Estimación D3D9 por fin de escena; puede diferir de los FPS presentados.'
                   if hook_source == 2 else 'Medición dentro de la superficie del juego.') if use_hook_fps else
                  fps.get('reason') or 'Esperando fotogramas del juego.')
        # An exact-monitor window may be borderless or truly exclusive. Give
        # the in-game module a short chance to start; if loading fails, keep
        # the no-activate host available as a fallback instead of hiding both
        # the OSD and the panel for the rest of the session.
        exclusive_or_unknown = fullscreen and (
            bool(fps.get('exclusive', False)) or fps.get('quality') != 'VALID_ETW')
        hook_starting = hook_allowed and (self._inject_result in ('PENDIENTE', 'CARGANDO') or
                                          self._inject_result.startswith('LOADED_'))
        in_game_surface = bool(target_pid and (hook_ready or
                               (exclusive_or_unknown and hook_starting)))
        external_fallback = bool(target_pid and fullscreen and not in_game_surface)
        self._set(fps=value, fpsValue=f'{visible_fps:.1f} FPS' if visible_fps is not None else 'N/A',
                  fpsQuality=quality, fpsMessage=reason,
                  fpsPermissionRequired=bool(not use_hook_fps and fps.get('permissionRequired', False) and
                                             not self._elevated),
                  presentMode=fps.get('presentMode', 'N/A'), graphicsRuntime=fps.get('runtime', 'N/A'),
                  exclusivePresentation=bool(fps.get('exclusive', False)),
                  renderMode='juego' if hook_ready else
                             'respaldo externo' if external_fallback else
                             'ventana' if target_pid and not fullscreen else
                             'esperando juego' if fullscreen else 'escritorio',
                  foregroundName=foreground_name or 'N/A', targetPid=target_pid,
                  inGameHook=hook_state,
                  hookDetail=('Comandos enviados al juego; FPS estimados desde EndScene de Direct3D 9.'
                              if use_hook_fps and hook_source == 2 else
                              'FPS medidos dentro del juego; el host dibuja en su ventana.'
                              if use_hook_fps and not fullscreen else
                              'Comandos enviados al juego y FPS medidos; la visibilidad se comprueba en pantalla.'
                              if use_hook_fps else
                              'Comandos enviados al juego; los FPS se consultan por eventos de Windows.'
                              if hook_ready else _hook_description(
                                  'IPC_ERROR' if not ipc_ready else
                                  self._inject_result if hook_allowed else 'DESACTIVADO', hook_error)))
        frames = self._fps_reader.take_timed_frame_intervals(target_pid)
        if target_pid != self._frame_line_pid:
            self._frame_line.clear()
            self._frame_line_pid = target_pid
        self._frame_line.extend(frames)
        while self._frame_line and self._frame_line[0][0] < now - 3:
            self._frame_line.popleft()
        if self._capture_status and now - self._capture_status_at > 6:
            self._capture_status = ''
        self._data['frameTimes'] = [v for _, v in self._frame_line]
        self._data['captureStatus'] = self._capture_status
        game_label = next((g.get('name') for g in performance.get('probableGames') or []
                           if isinstance(g, dict) and g.get('pid') == target_pid and g.get('name')), None)
        self.sampleObserved.emit(dict(time=now, pid=target_pid, name=game_label or foreground_name or 'Juego',
            frames=frames, fps=value, cpu=metrics.get('cpuPercent'), gpu=metrics.get('gpuPercent'),
            ram=metrics.get('ramPercent'), cpuTemp=metrics.get('cpuTemp'), gpuTemp=metrics.get('gpuTemp'),
            gpuMemoryUsed=metrics.get('gpuVramUsed'), cpuClock=metrics.get('cpuGHz'),
            cpuClockSource=metrics.get('cpuClockSource') or 'N/A'))
        cpu_color, gpu_color = _brand_colors(metrics)
        cleanup = (self._cleanup.data or {}) if self._cleanup is not None else {}
        status = cleanup.get('status') if cleanup.get('busy') else performance.get('message', '')
        plans = [dict(plan, active=str(plan.get('guid')) == str(performance.get('activeGuid')))
                 for plan in (performance.get('plans') or [])
                 if isinstance(plan, dict) and plan.get('guid')][:4]
        # The injected renderer receives the same data as the desktop host.
        # Only the selected renderer may draw. In borderless mode a loaded DLL
        # can coexist with the external host while its first Present arrives;
        # giving both COREPULSE_OVERLAY_DRAW produced two Shift+F2 panels.
        # An inactive/other PID snapshot makes a previously loaded DLL inert.
        self._write_game_state(target_pid, metrics, visible_fps, cpu_color, gpu_color, plans,
                               draw_inside=bool(in_game_surface))
        fields = ['METRICS', _metric(metrics, 'cpuPercent'), _metric(metrics, 'gpuPercent'),
                  _metric(metrics, 'ramPercent'), f'{visible_fps:.1f}' if visible_fps is not None else 'N/A',
                  _metric(metrics, 'cpuTemp', ' °C') if self._config['temperatures'] else ' ',
                  _metric(metrics, 'gpuTemp', ' °C') if self._config['temperatures'] else ' ',
                  cpu_color, gpu_color, _clean(status, 85),
                  metrics.get('cpuName') or 'Procesador N/A',
                  metrics.get('gpuName') or 'Gráfica N/A',
                  _capacity_info(metrics, 'ramUsed', 'ramTotal'),
                  _overlay_disk_name(metrics, self._storage),
                  _capacity_info(metrics, 'diskUsed', 'diskTotal'),
                  _metric(metrics, 'diskPercent'),
                  _brand_name(metrics.get('cpuName')) or ' ',
                  _brand_name(metrics.get('gpuName')) or ' ',
                  *self._theme_colors]
        self._send('\t'.join(_clean(field, 90) for field in fields))
        self._send('CLEARPLANS')
        for plan in plans:
            self._send('\t'.join(('PLAN', _clean(plan['guid'], 80),
                                  _clean(plan.get('name') or 'Plan de Windows', 55),
                                  '1' if plan['active'] else '0')))
        self._send('CORNER\t' + self._config['corner'])
        self._send('OPTIONS\t' + ('1' if self._config['compact'] else '0'))
        d = self._design
        self._send('DESIGN\t' + '\t'.join(str(d[k]) for k in ('scale','opacity','gap','x','y')) +
                   '\t' + ','.join(str(METRICS.index(k)) for k in d['metrics']) + '\t' + str(int(d['frametime'])))
        self._send('FRAMES\t' + ','.join(f'{v:.3f}' for _, v in self._frame_line))
        self._send('CAPTURE\t' + _clean(self._capture_status or ' ', 79))
        # The host uses WS_EX_NOACTIVATE and SW_SHOWNOACTIVATE. When the
        # in-process renderer fails, expose it so borderless games can still
        # show the OSD and mouse panel without taking game focus.
        desktop_mode = ('HIDDEN' if in_game_surface else
                        'PANEL' if self._data.get('quickPanelVisible') else
                        'OSD' if target_pid else 'HIDDEN')
        if desktop_mode != self._last_desktop_mode:
            _trace_overlay('host_mode', mode=desktop_mode, pid=target_pid,
                           hook=self._inject_result)
            self._last_desktop_mode = desktop_mode
        self._send('MODE\t' + desktop_mode)
        if desktop_mode != 'HIDDEN' and target_pid and now - self._host_raised_at >= 1.0:
            _keep_host_above_windowed_game()
            self._host_raised_at = now
        if target_pid:
            self._data['lastGameName'] = foreground_name or 'N/A'
            self._data['lastGamePid'] = target_pid
            self._data['lastGameHook'] = hook_state
            self._data['lastGameKey'] = self._pid_game_key(target_pid)
            self._data['lastGameAllowed'] = hook_allowed
        self._set(osdPublished=hook_ready if in_game_surface else True,
                  lastPublish=time.strftime('%H:%M:%S'),
                  message=('Overlay dentro del juego activo.' if hook_ready and fullscreen else
                           'Preparando render dentro del juego.' if in_game_surface and self._inject_result == 'CARGANDO' else
                           'El render dentro de este juego aún no está disponible.' if in_game_surface else
                           'Overlay externo activo. En pantalla completa exclusiva usa modo sin bordes para verlo.' if external_fallback else
                           'Overlay propio activo.'))

    @Slot()
    def close(self):
        self._closed = True
        self.hide()
        self._launch_watch.stop()
        self._hotkeys.stop()
        self._fps_reader.shutdown()
        self._send('QUIT')
        self._executor.shutdown(wait=False, cancel_futures=True)
        if self._game_state_map is not None:
            self._game_state_map.close()
            self._game_state_map = None
        if self._game_actions_map is not None:
            self._game_actions_map.close()
            self._game_actions_map = None

