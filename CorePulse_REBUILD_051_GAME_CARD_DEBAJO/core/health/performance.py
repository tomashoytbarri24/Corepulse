"""Rendimiento en Centro de Salud (Windows, REAL_OR_NA).

La V485 tenía estabilidad térmica, planes de energía y herramientas Gaming.
Esta migración recupera consulta/cambio/reversión de planes existentes y
observación de procesos probables de Steam/Epic sin inventar FPS ni throttling.
Nunca crea planes, nunca modifica energía al consultar y no aplica Game Boost.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import lru_cache
import time
import ctypes
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

import psutil
from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot

_GUID = re.compile(r"\b[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}\b")
_STEAM_PATH = '/steamapps/common/'
_EPIC_PATH = '/epic games/'
_EXCLUDED_NAMES = {
    'steam.exe', 'steamwebhelper.exe', 'epicgameslauncher.exe',
    'epicwebhelper.exe', 'unrealenginelauncher.exe', 'unitycrashhandler64.exe',
    'unitycrashhandler32.exe', 'crashreportclient.exe', 'easyanticheat.exe',
    'eac_launcher.exe', 'beservice.exe', 'beservice_x64.exe', 'cefsubprocess.exe',
    'gameoverlayui.exe', 'steamservice.exe', 'steamerrorreporter.exe',
}
_EXCLUDED_PARTS = (
    'crash', 'anti-cheat', 'anticheat', 'overlay', 'launcher',
    'installer', 'uninstall', 'helper', 'bootstrap', 'updater',
)


def _guid(text):
    match = _GUID.search(str(text or ''))
    return match.group(0).lower() if match else None


def parse_power_schemes(output):
    """Parsea por GUID, independiente del idioma de powercfg."""
    found = []
    for line in str(output or '').splitlines():
        match = _GUID.search(line)
        if match is None:
            continue
        suffix = line[match.end():]
        name_match = re.search(r'\(([^()]*)\)', suffix)
        name = name_match.group(1).strip() if name_match else 'Plan ' + match.group(0)[:8]
        found.append({'guid': match.group(0).lower(), 'name': name[:100], 'active': '*' in suffix})
    return found


def parse_active_scheme(output):
    return _guid(output)


def _cmd(arguments, *, timeout=15):
    if os.name != 'nt':
        return False, '', 'Disponible únicamente en Windows.'
    exe = shutil.which('powercfg.exe') or shutil.which('powercfg')
    if not exe:
        return False, '', 'Windows no proporcionó powercfg.exe.'
    try:
        proc = subprocess.run(
            [exe, *arguments], capture_output=True, timeout=timeout,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), check=False,
        )
        # powercfg de Windows produce salida OEM localizada.
        def decode(value):
            # powercfg produce datos OEM; mbcs/ANSI suele corromper tildes.
            try:
                oem_encoding = 'cp' + str(ctypes.windll.kernel32.GetOEMCP())
            except (AttributeError, OSError, ValueError):
                oem_encoding = 'cp850'
            for encoding in ('utf-8-sig', oem_encoding, 'cp850', 'mbcs', 'cp1252'):
                try:
                    return value.decode(encoding, errors='strict')
                except (LookupError, UnicodeError):
                    pass
            return value.decode('utf-8', errors='replace')
        return proc.returncode == 0, decode(proc.stdout), decode(proc.stderr)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, '', type(exc).__name__


def _backup_path():
    root = Path(os.environ.get('LOCALAPPDATA') or Path.home()) / 'CorePulse' / 'health'
    root.mkdir(parents=True, exist_ok=True)
    return root / 'performance_power_backup.json'


def _read_backup():
    try:
        data = json.loads(_backup_path().read_text(encoding='utf-8'))
    except (OSError, ValueError, TypeError):
        return None
    if not isinstance(data, dict) or not _guid(data.get('originalGuid')):
        return None
    return data


def _write_backup(data):
    target = _backup_path()
    tmp = target.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(tmp, target)


def _clear_backup():
    try:
        _backup_path().unlink(missing_ok=True)
    except OSError:
        pass


def _installed_folder(executable, source):
    """Devuelve nombre de carpeta de instalación si la ruta es de tienda compatible."""
    parts = str(executable or '').replace('\\', '/').split('/')
    lower = [part.lower() for part in parts]
    if source == 'Steam':
        for i in range(len(parts)-2):
            if lower[i] == 'steamapps' and lower[i+1] == 'common':
                return parts[i+2] if parts[i+2] else None
    elif source == 'Epic Games':
        for i in range(len(parts)-1):
            if lower[i] == 'epic games':
                return parts[i+1] or None
    return None


def _steamapps_directory(executable):
    """Busca steamapps en padres de la ruta real, sin confiar en rutas arbitrarias."""
    for parent in Path(executable).parents:
        if parent.name.lower() == 'steamapps':
            return parent
    return None


@lru_cache(maxsize=96)
def _steam_manifest_details(directory, install_folder):
    """Lee solo metadatos de biblioteca local; el appid debe coincidir con la carpeta."""
    steamapps = Path(directory)
    for manifest in steamapps.glob('appmanifest_*.acf'):
        try:
            raw = manifest.read_text(encoding='utf-8-sig', errors='replace')[:200_000]
        except (OSError, UnicodeError):
            continue
        fields = {}
        for match in re.finditer(r'^\s*"(appid|installdir|name)"\s*"([^"\n]*)"', raw, re.I | re.M):
            fields[match.group(1).lower()] = match.group(2)
        appid = fields.get('appid', '')
        if fields.get('installdir', '').casefold() != install_folder.casefold():
            continue
        if not appid.isdigit() or len(appid) > 12 or manifest.stem != 'appmanifest_'+appid:
            continue
        return {'appid': appid, 'name': fields.get('name', '')[:100]}
    return {'appid': '', 'name': ''}


def _steam_artwork(steamapps, appid):
    """Solo carátulas locales; no transmitir bibliotecas ni IDs sin aprobación."""
    if not appid or not appid.isdigit():
        return ''
    steam_roots = [steamapps.parent]  # Cuando Steam y biblioteca están en el mismo disco.
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam') as key:
            install, _ = winreg.QueryValueEx(key, 'SteamPath')
            steam_roots.append(Path(install))
    except (ImportError, OSError, ValueError):
        pass
    for root in steam_roots:
        for cache in (root/'appcache'/'librarycache', root/'steamapps'/'librarycache'):
            paths = (
                cache/f'{appid}_library_hero.jpg', cache/f'{appid}_header.jpg',
                cache/appid/'library_hero.jpg', cache/appid/'header.jpg',
                cache/f'{appid}_library_600x900.jpg', cache/appid/'library_600x900.jpg',
            )
            for asset in paths:
                try:
                    if asset.is_file() and asset.stat().st_size > 300:
                        return asset.resolve().as_uri()
                except OSError:
                    pass
    return ''


def _steam_remote_art(appid):
    if not appid or not str(appid).isdigit():
        return ''
    return f'https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/header.jpg'


def _game_session_text(start):
    try:
        elapsed = max(0, int(time.time() - float(start)))
    except (ValueError, TypeError, OverflowError):
        return 'N/A'
    hours, rem = divmod(elapsed, 3600)
    minutes, seconds = divmod(rem, 60)
    return f'{hours:02d}:{minutes:02d}:{seconds:02d}'


def _detect_probable_games(allowed_online_art=()):
    """Sesión en vivo desde procesos Steam/Epic; no crea entradas ficticias ni FPS."""
    results = []
    try:
        iterator = psutil.process_iter(['name', 'exe', 'pid', 'create_time'])
        for proc in iterator:
            try:
                item = proc.info
                original = str(item.get('exe') or '')
                exe = original.replace('\\', '/').lower()
                name = str(item.get('name') or '').lower()
                if not exe.endswith('.exe') or name in _EXCLUDED_NAMES:
                    continue
                if any(token in name for token in _EXCLUDED_PARTS):
                    continue
                origin = 'Steam' if _STEAM_PATH in exe else 'Epic Games' if _EPIC_PATH in exe else None
                if not origin:
                    continue
                folder = _installed_folder(original, origin)
                if not folder:
                    continue
                steamapps = _steamapps_directory(original) if origin == 'Steam' else None
                manifest = (_steam_manifest_details(str(steamapps), folder) if steamapps else {'appid': '', 'name': ''})
                title = manifest['name'] if manifest['name'] else folder.replace('_', ' ')
                appid = manifest['appid']
                art = _steam_artwork(steamapps, appid) if steamapps else ''
                if not art and origin == 'Steam' and appid in allowed_online_art:
                    art = _steam_remote_art(appid)
                created = item.get('create_time')
                results.append({
                    'name': title, 'pid': int(item.get('pid') or 0),
                    'source': origin, 'appid': appid, 'artUrl': art,
                    'session': _game_session_text(created),
                    'createdAt': float(created or 0), 'executable': str(item.get('name') or ''),
                    'active': True,
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, OSError, ValueError, TypeError):
                continue
    except (psutil.Error, OSError):
        return []
    # Deduplicación por carpeta (juegos con múltiples procesos de soporte).
    by_title = {}
    for item in results:
        key = (item['source'], item['appid'] or item['name'].casefold())
        if key not in by_title or item['createdAt'] < by_title[key]['createdAt']:
            by_title[key] = item
    return sorted(by_title.values(), key=lambda row: row['createdAt'], reverse=True)[:5]


def _game_caption(games):
    if games:
        return 'Juego detectado mediante un proceso real. Arte y nombre obtenidos de la biblioteca de Steam cuando están disponibles.'
    return 'Aún no hay juego activo identificado en bibliotecas Steam o Epic. Se comprobará automáticamente.'


def _active_game(games):
    return games[0] if games else {'active': False, 'name': '', 'source': '', 'appid': '',
                                  'artUrl': '', 'session': 'N/A', 'pid': 0,
                                  'executable': ''}


def read_performance():
    ok_list, output, err = _cmd(['/list'])
    ok_active, active_output, active_err = _cmd(['/getactivescheme'])
    plans = parse_power_schemes(output) if ok_list else []
    active_guid = parse_active_scheme(active_output) if ok_active else None
    if ok_list and not active_guid:
        active_guid = next((p['guid'] for p in plans if p['active']), None)
    active_name = next((p['name'] for p in plans if p['guid'] == active_guid), 'N/A')
    backup = _read_backup()
    original_guid = str(backup.get('originalGuid')) if backup else None
    original_name = next((p['name'] for p in plans if p['guid'] == original_guid), 'N/A')
    games = _detect_probable_games()
    return {
        'available': bool(ok_list and ok_active and active_guid),
        'plans': plans, 'activeGuid': active_guid or '', 'activeName': active_name,
        'backupAvailable': bool(backup), 'originalName': original_name,
        'probableGames': games, 'activeGame': _active_game(games),
        'gameCaption': _game_caption(games),
        'status': 'LISTO' if ok_list and ok_active and active_guid else 'N/A',
        'message': 'Planes de energía leídos desde Windows.' if ok_list and ok_active and active_guid else
                   'Windows no proporcionó un inventario verificable de energía.',
        'lastUpdate': datetime.now().strftime('%H:%M:%S'),
    }


def apply_power_scheme(guid):
    if _GUID.fullmatch(str(guid or '')) is None:
        return False, 'GUID de plan inválido.'
    before = read_performance()
    if not before['available']:
        return False, 'No se pudo verificar el plan actual de Windows.'
    chosen = next((x for x in before['plans'] if x['guid'] == guid.lower()), None)
    if not chosen:
        return False, 'Este plan no figura en los planes existentes de Windows.'
    if before['activeGuid'] == chosen['guid']:
        return True, 'El plan ya estaba activo. No se realizaron cambios.'
    backup = _read_backup()
    if not backup:
        backup = {'originalGuid': before['activeGuid'], 'date': datetime.now().isoformat(timespec='seconds')}
        try:
            _write_backup(backup)
        except OSError:
            return False, 'No se pudo guardar el punto de reversión. No se aplicó el plan.'
    ok, _, _ = _cmd(['/setactive', chosen['guid']])
    after = read_performance()
    if not ok or after['activeGuid'] != chosen['guid']:
        return False, 'Windows no confirmó la activación del plan solicitado. La reversión sigue disponible.'
    return True, 'Windows confirmó el plan «' + chosen['name'] + '».'


def restore_power_scheme():
    backup = _read_backup()
    if backup is None:
        return False, 'No existe un plan previo de CorePulse para restaurar.'
    original = _guid(backup['originalGuid'])
    current = read_performance()
    if not current['available']:
        return False, 'No es posible verificar los planes disponibles.'
    if not any(item['guid'] == original for item in current['plans']):
        return False, 'El plan original ya no figura entre los planes de Windows.'
    if current['activeGuid'] != original:
        ok, _, _ = _cmd(['/setactive', original])
        if not ok:
            return False, 'Windows rechazó la restauración del plan anterior.'
    after = read_performance()
    if after['activeGuid'] != original:
        return False, 'La restauración no pudo verificarse.'
    _clear_backup()
    return True, 'Plan anterior restaurado y verificado.'


def _mutate_and_read(mode, guid=None):
    ok, message = apply_power_scheme(guid) if mode == 'apply' else restore_power_scheme()
    result = read_performance()
    result.update(status='OK' if ok else 'ERROR', message=message)
    return result


class PerformanceHealth(QObject):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix='corepulse-health-performance')
        self._future = None
        self._closed = False
        self._data = {
            'busy': False, 'available': False, 'plans': [], 'activeGuid': '',
            'activeName': 'N/A', 'backupAvailable': False, 'originalName': 'N/A',
            'probableGames': [], 'activeGame': _active_game([]),
            'gameCaption': 'Sin consulta de juegos.',
            'status': 'N/A', 'message': 'Aún no consultado.', 'lastUpdate': 'N/A',
        }
        self._timer = QTimer(self)
        self._timer.setInterval(220)
        self._timer.timeout.connect(self._finish)
        self._mode = 'refresh'
        self._game_future = None
        self._allowed_online_art = set()
        self._game_watch = QTimer(self)
        self._game_watch.setInterval(2500)
        self._game_watch.timeout.connect(self._scan_games)
        self._game_poll = QTimer(self)
        self._game_poll.setInterval(180)
        self._game_poll.timeout.connect(self._finish_games)

    @Property('QVariantMap', notify=changed)
    def data(self):
        return self._data

    @Slot()
    def startGameWatch(self):
        """La búsqueda en vivo solo funciona mientras Rendimiento esté abierto."""
        if self._closed:
            return
        if not self._game_watch.isActive():
            self._game_watch.start()
        self._scan_games()

    @Slot()
    def stopGameWatch(self):
        self._game_watch.stop()

    @Slot()
    def loadOnlineArtwork(self):
        """Solo por clic explícito del usuario se solicita una imagen de Steam."""
        game = self._data.get('activeGame') or {}
        appid = str(game.get('appid', ''))
        if not game.get('active') or game.get('source') != 'Steam' or not appid.isdigit():
            return
        self._allowed_online_art.add(appid)
        updated = {**game, 'artUrl': _steam_remote_art(appid)}
        games = [{**item, 'artUrl': _steam_remote_art(appid)} if item.get('appid') == appid else item
                 for item in self._data.get('probableGames', [])]
        self._data = {**self._data, 'activeGame': updated, 'probableGames': games}
        self.changed.emit()

    def _scan_games(self):
        if self._closed or self._game_future is not None:
            return
        self._game_future = self._executor.submit(_detect_probable_games, tuple(self._allowed_online_art))
        self._game_poll.start()

    def _finish_games(self):
        if self._game_future is None or not self._game_future.done():
            return
        try:
            games = self._game_future.result()
        except Exception:
            games = []
        self._game_future = None
        self._game_poll.stop()
        self._data = {**self._data, 'probableGames': games, 'activeGame': _active_game(games),
                      'gameCaption': _game_caption(games)}
        self.changed.emit()

    def _start(self, mode, target=None):
        if self._closed or self._future is not None:
            return
        self._mode = mode
        self._data = {**self._data, 'busy': True, 'message': 'Consultando Windows…' if mode == 'refresh' else 'Esperando confirmación de Windows…'}
        self.changed.emit()
        if mode == 'apply':
            self._future = self._executor.submit(_mutate_and_read, mode, target)
        elif mode == 'restore':
            self._future = self._executor.submit(_mutate_and_read, mode)
        else:
            self._future = self._executor.submit(read_performance)
        self._timer.start()

    @Slot()
    def refresh(self):
        self._start('refresh')

    @Slot(str)
    def applyPlan(self, guid):
        self._start('apply', guid)

    @Slot()
    def restorePrevious(self):
        self._start('restore')

    def _finish(self):
        if not self._future or not self._future.done():
            return
        try:
            result = self._future.result()
        except Exception as error:
            result = (False, type(error).__name__)
        self._future = None
        self._timer.stop()
        if isinstance(result, dict):
            # El sondeo en vivo tiene prioridad sobre la instantánea del powercfg.
            if self._game_watch.isActive():
                result.pop('probableGames', None)
                result.pop('activeGame', None)
                result.pop('gameCaption', None)
            self._data = {**self._data, **result, 'busy': False}
        else:
            self._data = {**self._data, 'busy': False, 'status': 'ERROR', 'message': 'No se pudo finalizar la consulta.'}
        self.changed.emit()

    @Slot()
    def close(self):
        self._closed = True
        self._timer.stop()
        self._game_watch.stop()
        self._game_poll.stop()
        self._executor.shutdown(wait=False, cancel_futures=True)
