"""Rendimiento en Centro de Salud (Windows, REAL_OR_NA).

La V485 tenía estabilidad térmica, planes de energía y herramientas Gaming.
Esta migración recupera consulta/cambio/reversión de planes existentes y
observación de procesos de Steam/Epic/Riot/EA app/Microsoft Store/Xbox sin inventar FPS ni throttling.
Los planes manuales se mantienen separados de la conmutación automática por juegos:
solo usa planes ya disponibles, conserva el original y revierte condicionalmente.
"""
from __future__ import annotations

from concurrent.futures.thread import ThreadPoolExecutor
import threading
from datetime import datetime
from functools import lru_cache
from html.parser import HTMLParser
import time
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import urllib.request
import urllib.parse
import subprocess
import xml.etree.ElementTree as ET

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
    'riotclientservices.exe', 'riotclientux.exe', 'riotclientuxrender.exe',
    'riotclientcrashhandler.exe', 'riotclientuxhelper.exe',
    'leagueclientux.exe', 'leagueclientuxrender.exe',
    'leaguecrashhandler.exe', 'vgc.exe', 'vgtray.exe',
    'valorant.exe', 'eadesktop.exe', 'eabackgroundservice.exe', 'ealauncher.exe',
    'origin.exe', 'originwebhelperservice.exe', 'ealink.exe', 'easteamproxy.exe',
    'gamelaunchhelper.exe', 'gamingservices.exe', 'gamingservicesnet.exe',
    'xboxapp.exe', 'gamebar.exe', 'xboxgamebar.exe', 'gamingoverlay.exe',
}
_EXCLUDED_PARTS = (
    'crash', 'anti-cheat', 'anticheat', 'overlay', 'launcher', 'subprocess',
    'installer', 'uninstall', 'helper', 'bootstrap', 'updater',
)

# Solo ejecutables propios de juegos/cliente de juego y rutas compatibles.
# RiotClientServices, Vanguard, launchers, instaladores y anticheats nunca
# cuentan como juego en ejecución. Las rutas admiten otros discos o ubicaciones
# de instalación, sin exigir C:\Riot Games.
_RIOT_PROCESS_RULES = {
    'valorant-win64-shipping.exe': ('VALORANT', '/valorant/live/shootergame/binaries/win64/', 'En ejecución', 2),
    'league of legends.exe': ('League of Legends', '/league of legends/game/', 'En partida', 2),
    'leagueclient.exe': ('League of Legends', '/league of legends/leagueclient.exe', 'Cliente abierto', 1),
    'lor.exe': ('Legends of Runeterra', '/lor/live/game/', 'En ejecución', 2),
}


def _riot_process_game(process_name, executable):
    """Reconoce juegos Riot solo con el exe exacto y ruta de juego coherente.

    LeagueClient.exe es la aplicación de League, no implica estar en partida;
    se distingue explícitamente del ejecutable real de una partida.
    """
    filename = str(process_name or '').casefold().strip()
    path = str(executable or '').replace('\\', '/').casefold()
    spec = _RIOT_PROCESS_RULES.get(filename)
    if not spec or not path.endswith('/' + filename):
        return None
    title, fragment, state, priority = spec
    if fragment.endswith('.exe'):
        matches = path.endswith(fragment)
    else:
        matches = fragment in path
    return (title, state, priority) if matches else None


_EA_PATH_MARKERS = ('/ea games/', '/origin games/', '/electronic arts/', '/ea sports/')
_XBOX_MARKERS = ('/xboxgames/', '/modifiablewindowsapps/')
_STORE_GAME_HINTS = ('forzahorizon', 'forzamotorsport', 'haloinfinite',
                     'minecraft', 'flight simulator', 'flightsimulator', 'seaofthieves',
                     'ageofempires', 'gears', 'stateofdecay', 'hellblade', 'outerworlds',
                     'oriandthe', 'psychonauts', 'doom', 'grounded', 'pentiment')


@lru_cache(maxsize=64)
def _store_visual_manifest(executable):
    """Metadatos del paquete Appx local, nunca consulta remota."""
    path = Path(executable)
    for folder in path.parents:
        if folder.parent.name.casefold() != 'windowsapps':
            continue
        manifest = folder / 'AppxManifest.xml'
        try:
            root = ET.parse(manifest).getroot()
        except (OSError, ET.ParseError, ValueError):
            return None
        properties = next((node for node in root.iter() if node.tag.endswith('}Properties')), None)
        display_name = None
        if properties is not None:
            display_name = next((str(node.text or '').strip() for node in properties
                                 if node.tag.endswith('}DisplayName')), None)
        visual = next((node for node in root.iter() if node.tag.endswith('}VisualElements')), None)
        if visual is not None:
            shown = str(visual.attrib.get('DisplayName') or '').strip()
            if shown and not shown.lower().startswith('ms-resource:'):
                display_name = shown
        if not display_name or display_name.lower().startswith('ms-resource:'):
            display_name = re.split(r'_\d', folder.name, maxsplit=1)[0].replace('.', ' ')
        cover = ''
        if visual is not None:
            # El manifiesto verifica que el logo corresponde a este paquete.
            for key in ('Wide310x150Logo', 'Square310x310Logo', 'Square150x150Logo', 'Square44x44Logo'):
                relative = visual.attrib.get(key)
                if not relative or '..' in Path(relative).parts:
                    continue
                asset = folder / relative.replace('\\', '/')
                candidates = [asset]
                if asset.suffix:
                    candidates.extend(asset.parent.glob(asset.stem + '.scale-*' + asset.suffix))
                    candidates.extend(asset.parent.glob(asset.stem + '.targetsize-*' + asset.suffix))
                cover = _first_local_image(candidates)
                if cover:
                    break
        raw = ET.tostring(root, encoding='unicode').casefold()
        is_game = any(hint in (folder.name + ' ' + display_name).casefold().replace(' ', '')
                      for hint in _STORE_GAME_HINTS)
        is_game = is_game or 'category="windows.game"' in raw or 'xboxlive' in raw
        return {'name': display_name[:100], 'cover': cover, 'isGame': is_game}
    return None


def _first_local_image(paths):
    for candidate in paths:
        try:
            item = Path(candidate)
            if item.is_file() and item.stat().st_size > 300 and item.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp', '.bmp'):
                return item.resolve().as_uri()
        except OSError:
            continue
    return ''


def _local_game_cover(executable, game_root=None):
    """Solo imágenes con nombres de portada inequívocos dentro del juego."""
    root = Path(game_root) if game_root else Path(executable).parent
    names = ('cover.jpg', 'cover.png', 'header.jpg', 'header.png',
             'library_hero.jpg', 'library_hero.png', 'capsule.jpg',
             'artwork.jpg', 'artwork.png', 'poster.jpg', 'poster.png')
    paths = [root / n for n in names]
    paths.extend(root / 'Assets' / n for n in names)
    return _first_local_image(paths)


@lru_cache(maxsize=128)
def _executable_artwork(executable):
    """Icono asociado al exe de Windows como respaldo visual verificable.

    Se exporta por PowerShell/.NET a PNG en LocalAppData de CorePulse.
    Los parámetros pasan mediante variables de entorno, nunca se interpolan en
    el script, para que rutas con comillas/apóstrofos no ejecuten código.
    """
    if os.name != 'nt' or not executable:
        return ''
    path = Path(executable)
    try:
        if not path.is_file() or path.suffix.casefold() != '.exe':
            return ''
        signature = f'{str(path).casefold()}:{path.stat().st_mtime_ns}'
        key = hashlib.sha256(signature.encode('utf-8')).hexdigest()[:24]
        target_dir = Path(os.environ.get('LOCALAPPDATA') or Path.home()) / 'CorePulse' / 'game_art'
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / (key + '.png')
        if target.exists() and target.stat().st_size > 100:
            return target.resolve().as_uri()
        powershell = shutil.which('powershell.exe') or shutil.which('powershell')
        if not powershell:
            return ''
        env = os.environ.copy()
        env['COREPULSE_GAME_EXE'] = str(path)
        env['COREPULSE_GAME_ICON_OUT'] = str(target)
        script = ("Add-Type -AssemblyName System.Drawing; "
                  "$icon=[System.Drawing.Icon]::ExtractAssociatedIcon($env:COREPULSE_GAME_EXE); "
                  "if ($null -ne $icon) { "
                  "$bmp=$icon.ToBitmap(); "
                  "try { $bmp.Save($env:COREPULSE_GAME_ICON_OUT, [System.Drawing.Imaging.ImageFormat]::Png) } "
                  "finally { $bmp.Dispose(); $icon.Dispose() } }")
        result = subprocess.run([powershell, '-NoLogo', '-NoProfile', '-NonInteractive', '-Command', script],
                                env=env, capture_output=True, timeout=9, check=False,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode == 0 and target.is_file() and target.stat().st_size > 100:
            return target.resolve().as_uri()
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return ''
    return ''


def _game_source(executable, process_name):
    """Identifica la tienda solo por firma real de la ruta del ejecutable."""
    exe = str(executable or '').replace('\\', '/').casefold()
    name = str(process_name or '').casefold()
    if _riot_process_game(name, executable):
        return 'Riot Games'
    if _STEAM_PATH in exe:
        return 'Steam'
    if _EPIC_PATH in exe:
        return 'Epic Games'
    if any(part in exe for part in _EA_PATH_MARKERS):
        return 'EA app'
    if any(part in exe for part in _XBOX_MARKERS):
        return 'Microsoft Store / Xbox'
    if '/windowsapps/' in exe:
        return 'Microsoft Store / Xbox' if (meta := _store_visual_manifest(executable)) and meta['isGame'] else None
    return None


def _store_game_details(executable, origin):
    """Devuelve nombre, portada local y raíz de instalación verificables."""
    exe = str(executable).replace('\\', '/')
    segments = exe.split('/')
    lower = [part.casefold() for part in segments]
    if origin == 'Microsoft Store / Xbox' and 'windowsapps' in lower:
        meta = _store_visual_manifest(executable)
        if not meta or not meta['isGame']:
            return None
        return meta['name'], meta['cover'], ''
    markers = {'EA app': ('ea games', 'origin games', 'electronic arts', 'ea sports'),
               'Microsoft Store / Xbox': ('xboxgames', 'modifiablewindowsapps')}.get(origin, ())
    for idx, segment in enumerate(lower[:-1]):
        if segment in markers and idx + 1 < len(segments):
            title = segments[idx+1].replace('_',' ')
            game_root = '/'.join(segments[:idx+2])
            # Content/GDK has a few non-game launch helpers, already excluded.
            return title[:100], _local_game_cover(executable, game_root), game_root
    return None


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


# El plan de Windows Ultimate Performance no siempre existe (especialmente en portátiles).
# Nunca duplicarlo ni crearlo; High Performance es una alternativa explícita y verificable.
_ULTIMATE = 'e9a42b02-d5df-448d-aa00-03f14749eb61'
_HIGH_PERFORMANCE = '8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c'
_AUTO_POWER_LOCK = threading.RLock()


def _auto_power_backup_path():
    return _backup_path().with_name('auto_game_power_backup.json')


def _auto_power_settings_path():
    return _backup_path().with_name('auto_game_power_settings.json')


def _auto_power_enabled():
    try:
        payload = json.loads(_auto_power_settings_path().read_text(encoding='utf-8'))
        return payload.get('enabled') is not False if isinstance(payload, dict) else True
    except (OSError, ValueError, TypeError):
        return True


def _write_auto_power_enabled(enabled):
    path = _auto_power_settings_path()
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps({'enabled': bool(enabled)}), encoding='utf-8')
    os.replace(tmp, path)


def _read_auto_power_backup():
    try:
        payload = json.loads(_auto_power_backup_path().read_text(encoding='utf-8'))
    except (OSError, ValueError, TypeError):
        return None
    if not isinstance(payload, dict):
        return None
    original, boosted = _guid(payload.get('originalGuid')), _guid(payload.get('boostGuid'))
    if original and boosted and original != boosted:
        return {'originalGuid': original, 'boostGuid': boosted}
    return None


def _save_auto_power_backup(original, boosted):
    path = _auto_power_backup_path()
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps({'originalGuid': original, 'boostGuid': boosted}, indent=2), encoding='utf-8')
    os.replace(tmp, path)


def _clear_auto_power_backup():
    _auto_power_backup_path().unlink(missing_ok=True)


def _preferred_game_power_scheme(plans):
    """Prefiere máximo rendimiento, después alto rendimiento, si YA existen."""
    tiers = (
        (_ULTIMATE, ('máximo rendimiento', 'maximo rendimiento', 'ultimate performance', 'rendimiento máximo')),
        (_HIGH_PERFORMANCE, ('alto rendimiento', 'high performance')),
    )
    for guid, names in tiers:
        found = next((p for p in plans if p['guid'] == guid), None)
        if found:
            return found
        found = next((p for p in plans if p['name'].casefold().strip() in names), None)
        if found:
            return found
    return None


def _power_state_only():
    ok, raw, _ = _cmd(['/list'])
    ok_current, raw_current, _ = _cmd(['/getactivescheme'])
    if not ok or not ok_current:
        return [], None
    plans = parse_power_schemes(raw)
    active = parse_active_scheme(raw_current) or next((p['guid'] for p in plans if p['active']), None)
    return plans, active


def _auto_power_transition(enable_for_game):
    """Cambia solamente el plan existente; respeta modificaciones externas.

    El respaldo se escribe ANTES del cambio y permite restaurar tras un cierre
    inesperado, al siguiente arranque de CorePulse. Nunca cambia el plan al
    consultar el estado ni cuando ya está en máximo rendimiento.
    """
    with _AUTO_POWER_LOCK:
        backup = _read_auto_power_backup()
        if not enable_for_game and backup is None:
            return 'ESPERANDO', 'Plan automático en espera; Windows conserva su configuración.'
        plans, current = _power_state_only()
        if not current or not plans:
            return 'N/A', 'Windows no permitió comprobar los planes; no se efectuó ningún cambio.'
        valid = {row['guid'] for row in plans}
        if enable_for_game:
            if backup:
                if current == backup['boostGuid']:
                    return 'ACTIVO', 'Plan de máximo rendimiento activado mientras haya juegos reconocidos.'
                if current == backup['originalGuid']:
                    # Al restaurar manualmente el usuario, no se sobreescribe su decisión.
                    _clear_auto_power_backup()
                    return 'MANUAL', 'El usuario restableció el plan durante el juego; se respetó su elección.'
                _clear_auto_power_backup()
                return 'MANUAL', 'Windows cambió de plan externamente; CorePulse no lo sobreescribe.'
            # El respaldo manual (otro archivo) se conserva: la sesión de juego
            # restaura el plan que estaba activo JUSTO antes del lanzamiento.
            target = _preferred_game_power_scheme(plans)
            if not target:
                return 'N/A', 'No hay plan Máximo/Alto rendimiento disponible en Windows; no se crea uno.'
            if current == target['guid']:
                return 'ACTIVO', 'El plan de alto/máximo rendimiento ya estaba activo; no se modificó.'
            try:
                _save_auto_power_backup(current, target['guid'])
            except OSError:
                return 'ERROR', 'No se pudo conservar el plan original; no se aplicó ningún cambio.'
            ok, _, _ = _cmd(['/setactive', target['guid']])
            _, after = _power_state_only()
            if not ok or after != target['guid']:
                if after == current:
                    _clear_auto_power_backup()
                return 'ERROR', 'Windows no confirmó el plan solicitado. Reversión conservada si corresponde.'
            return 'ACTIVO', 'Juego detectado: plan «' + target['name'] + '» activado. Se restaurará al terminar.'
        # Restaurar únicamente si Windows sigue usando el plan establecido por CorePulse.
        if current != backup['boostGuid']:
            _clear_auto_power_backup()
            return 'MANUAL', 'Windows ya cambió el plan. Se respetó el cambio externo.'
        if backup['originalGuid'] not in valid:
            return 'N/A', 'No se encuentra el plan original para restaurarlo; se conserva el respaldo.'
        ok, _, _ = _cmd(['/setactive', backup['originalGuid']])
        _, after = _power_state_only()
        if not ok or after != backup['originalGuid']:
            return 'ERROR', 'No se confirmó la restauración del plan original; se conserva el respaldo.'
        _clear_auto_power_backup()
        return 'RESTAURADO', 'Juego cerrado: Windows volvió al plan de energía anterior.'


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


def _steam_cover_urls(appid):
    """Portadas oficiales por App ID exacto; nunca se adivina el juego."""
    if not str(appid or '').isdigit():
        return ()
    return (f'https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/library_hero.jpg',
            f'https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/capsule_616x353.jpg')




# Catálogo exacto de sitios publicados por Riot. NO se infiere una URL a partir del
# nombre de un proceso desconocido; el arte se consulta solo si se detecta el juego activo.
_OFFICIAL_RIOT_PAGES = {
    'valorant': 'https://playvalorant.com/en-us/',
    'league of legends': 'https://www.leagueoflegends.com/en-us/',
    'legends of runeterra': 'https://playruneterra.com/en-us/',
}
_OFFICIAL_PAGE_HOSTS = {'playvalorant.com', 'www.playvalorant.com', 'www.leagueoflegends.com',
                        'leagueoflegends.com', 'playruneterra.com', 'www.playruneterra.com'}
_OFFICIAL_IMAGE_HOSTS = _OFFICIAL_PAGE_HOSTS | {'images.contentstack.io', 'cmsassets.rgpub.io',
    'www.riotgames.com', 'riotgames.com', 'ddragon.leagueoflegends.com',
    'am-a.akamaihd.net', 'lolstatic-a.akamaihd.net', 'static-developers.riotgames.com'}
_MAX_ART_BYTES = 8 * 1024 * 1024
_STEAM_IMAGE_HOSTS = {'cdn.cloudflare.steamstatic.com', 'shared.akamai.steamstatic.com', 'shared.fastly.steamstatic.com'}
_STEAM_SEARCH_HOSTS = {'store.steampowered.com'}


class _OfficialSocialImage(HTMLParser):
    def __init__(self):
        super().__init__()
        self.image = ''
        self.page_title = ''

    def handle_starttag(self, tag, attrs):
        if tag.lower() != 'meta':
            return
        a = dict(attrs)
        prop = str(a.get('property') or a.get('name') or '').casefold()
        if prop in ('og:image', 'twitter:image') and not self.image:
            self.image = str(a.get('content') or '')
        if prop in ('og:title', 'twitter:title') and not self.page_title:
            self.page_title = str(a.get('content') or '')


def _safe_remote_url(url, allowed_hosts):
    parsed = urllib.parse.urlparse(str(url or ''))
    return parsed.scheme == 'https' and parsed.hostname in allowed_hosts and not parsed.username and not parsed.password


def _get_limited_bytes(url, allowed_hosts, limit=_MAX_ART_BYTES):
    # Descarga controlada por dominio; solo desde un trabajador en segundo plano.
    if not _safe_remote_url(url, allowed_hosts):
        return None
    request = urllib.request.Request(url, headers={'User-Agent': 'CorePulse/1.0', 'Accept': 'image/jpeg,image/png,image/webp,text/html'})
    class _RestrictedRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, request, fp, code, msg, headers, newurl):
            if not _safe_remote_url(newurl, allowed_hosts):
                return None
            return super().redirect_request(request, fp, code, msg, headers, newurl)
    opener = urllib.request.build_opener(_RestrictedRedirect())
    with opener.open(request, timeout=10) as response:
        if not _safe_remote_url(response.geturl(), allowed_hosts):
            return None
        data = response.read(limit + 1)
    return data if len(data) <= limit else None


def _valid_wide_image(file_path):
    # Qt decodifica JPEG/PNG/WebP y comprueba dimensiones reales, no la extensión.
    from PySide6.QtGui import QImageReader
    reader = QImageReader(str(file_path))
    reader.setDecideFormatFromContent(True)
    size = reader.size()
    return size.isValid() and size.width() >= 600 and size.height() >= 300


def _cover_cache_file(source, name):
    label = source + ':' + name.casefold().strip()
    digest = hashlib.sha256(label.encode('utf-8')).hexdigest()[:24]
    root = Path(os.environ.get('LOCALAPPDATA') or Path.home()) / 'CorePulse' / 'game_art' / 'covers_auto'
    return root / (digest + '.png')


def _cached_cover(source, name):
    dest = _cover_cache_file(source, name)
    try:
        if dest.is_file() and dest.stat().st_size > 5000 and _valid_wide_image(dest):
            return dest.resolve().as_uri()
    except (OSError, ValueError):
        pass
    return ''


@lru_cache(maxsize=256)
def _wide_local_cover(uri):
    """Evita que logos pequeños del paquete Store se hagan pasar por banner."""
    if not str(uri or '').startswith('file:'):
        return False
    try:
        url = urllib.parse.urlparse(uri)
        if url.scheme != 'file' or url.netloc not in ('', 'localhost'):
            return False
        path = urllib.request.url2pathname(url.path)
        return _valid_wide_image(Path(path))
    except (OSError, ValueError, ImportError, AttributeError):
        return False


def _cache_verified_image(source, name, payload):
    if not payload or len(payload) < 5000 or len(payload) > _MAX_ART_BYTES:
        return ''
    dest = _cover_cache_file(source, name)
    download = dest.with_suffix('.download')
    converted = dest.with_suffix('.partial.png')
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        download.write_bytes(payload)
        if not _valid_wide_image(download):
            return ''
        # No escribir sobre el archivo que QImageReader está leyendo: en Windows
        # ese bloqueo puede hacer que solo aparezca el icono del ejecutable.
        from PySide6.QtGui import QImageReader
        reader = QImageReader(str(download))
        reader.setDecideFormatFromContent(True)
        image = reader.read()
        del reader  # Cierra el archivo de entrada antes de limpiar temporales en Windows.
        if image.isNull() or not image.save(str(converted), 'PNG'):
            return ''
        converted.replace(dest)
        return dest.resolve().as_uri()
    except (OSError, ValueError):
        return ''
    finally:
        for stale in (download, converted):
            try:
                stale.unlink(missing_ok=True)
            except OSError:
                pass


def _fetch_riot_cover(source, name):
    if source != 'Riot Games':
        return ''
    page = _OFFICIAL_RIOT_PAGES.get(str(name).casefold().strip())
    if not page:
        return ''
    cached = _cached_cover(source, name)
    if cached:
        return cached
    try:
        response = _get_limited_bytes(page, _OFFICIAL_PAGE_HOSTS, limit=2*1024*1024)
        if not response:
            return ''
        metadata = _OfficialSocialImage()
        metadata.feed(response.decode('utf-8', errors='replace'))
        if not metadata.image:
            return ''
        image_url = urllib.parse.urljoin(page, metadata.image)
        if not _safe_remote_url(image_url, _OFFICIAL_IMAGE_HOSTS):
            return ''
        # Evita asociar una portada de un artículo o juego diferente.
        if metadata.page_title and name.casefold() not in metadata.page_title.casefold():
            return ''
        data = _get_limited_bytes(image_url, _OFFICIAL_IMAGE_HOSTS)
        return _cache_verified_image(source, name, data)
    except (OSError, ValueError, UnicodeError, TimeoutError):
        return ''


def _matching_store_appid(title):
    """Resuelve identificador público de Steam SOLO por nombre exactamente igual.

    Utilizable para un juego de EA/Epic/Xbox si también figura en Steam.
    Nunca usa coincidencias parciales, primera posición o título aproximado.
    """
    title = str(title or '').strip()
    if not 2 <= len(title) <= 120:
        return ''
    url = 'https://store.steampowered.com/api/storesearch/?' + urllib.parse.urlencode({
        'term': title, 'l': 'english', 'cc': 'US'})
    raw = _get_limited_bytes(url, _STEAM_SEARCH_HOSTS, limit=300_000)
    if not raw:
        return ''
    try:
        payload = json.loads(raw.decode('utf-8'))
    except (ValueError, UnicodeError, TypeError):
        return ''
    if not isinstance(payload, dict):
        return ''
    def canonical(name):
        # Únicamente símbolos de marca, espacios y mayúsculas; NUNCA
        # elimina edición, año, numeración, subtítulos o DLC.
        return ' '.join(str(name or '').replace('®','').replace('™','').casefold().split())
    items = payload.get('items')
    if not isinstance(items, list):
        return ''
    matches = [str(entry.get('id')) for entry in items[:30]
               if isinstance(entry,dict) and canonical(entry.get('name')) == canonical(title)
               and str(entry.get('id', '')).isdigit()]
    return matches[0] if len(set(matches)) == 1 else ''


def _fetch_steam_cover(source, title, appid):
    if not str(appid or '').isdigit():
        return ''
    for url in _steam_cover_urls(appid):
        try:
            data = _get_limited_bytes(url, _STEAM_IMAGE_HOSTS)
            cover = _cache_verified_image(source, title, data) if data else ''
            if cover:
                return cover
        except (OSError, ValueError, TimeoutError):
            continue
    return ''


def _resolve_game_cover(source, title, appid):
    """Portada automática verificable, guardada localmente por tienda/título.

    Solo sale el juego concreto (título para coincidencia exacta, App ID si Steam),
    sin ruta, PID, lista de procesos ni telemetría de hardware.
    """
    stored = _cached_cover(source, title)
    if stored:
        return stored
    if source == 'Riot Games':
        return _fetch_riot_cover(source, title)
    if source == 'Steam':
        return _fetch_steam_cover(source, title, appid)
    if source in ('Epic Games', 'EA app', 'Microsoft Store/Xbox'):
        try:
            matching_id = _matching_store_appid(title)
            return _fetch_steam_cover(source, title, matching_id) if matching_id else ''
        except (OSError, ValueError, TimeoutError):
            return ''
    return ''


def _game_session_text(start):
    try:
        elapsed = max(0, int(time.time() - float(start)))
    except (ValueError, TypeError, OverflowError):
        return 'N/A'
    hours, rem = divmod(elapsed, 3600)
    minutes, seconds = divmod(rem, 60)
    return f'{hours:02d}:{minutes:02d}:{seconds:02d}'


def _detect_probable_games():
    """Detecta juegos desde procesos y rutas verificables de cinco ecosistemas.

    Carátulas: archivos locales del juego/biblioteca o caché verificada.
    Si no hay portada, el controlador lanza una única búsqueda remota en
    segundo plano, sin bloquear este sondeo; el icono no es una portada.
    """
    results = []
    try:
        iterator = psutil.process_iter(['name', 'exe', 'pid', 'create_time'])
        for proc in iterator:
            try:
                item = proc.info
                original = str(item.get('exe') or '')
                exe = original.replace('\\', '/').casefold()
                name = str(item.get('name') or '').casefold()
                if not exe.endswith('.exe') or name in _EXCLUDED_NAMES:
                    continue
                if any(token in name for token in _EXCLUDED_PARTS):
                    continue
                riot = _riot_process_game(name, original)
                origin = _game_source(original, name)
                if not origin:
                    continue
                art = ''
                art_kind = ''
                if riot:
                    title, state, priority = riot
                    appid = ''
                    # Portadas oficiales Riot se guardan en caché en otro hilo.
                    art = _cached_cover(origin, title) or _local_game_cover(original)
                    art_kind = 'cover' if art else ''
                elif origin in ('Steam', 'Epic Games'):
                    folder = _installed_folder(original, origin)
                    if not folder:
                        continue
                    steamapps = _steamapps_directory(original) if origin == 'Steam' else None
                    manifest = (_steam_manifest_details(str(steamapps), folder) if steamapps
                                else {'appid': '', 'name': ''})
                    title = manifest['name'] if manifest['name'] else folder.replace('_', ' ')
                    appid = manifest['appid']
                    art = _cached_cover(origin, title) or (_steam_artwork(steamapps, appid) if steamapps else '')
                    if not art:
                        art = _cached_cover(origin, title) or _local_game_cover(original, next((str(parent) for parent in Path(original).parents if parent.name.casefold() == folder.casefold()), None))
                    art_kind = 'cover' if art else ''
                    state, priority = 'En ejecución', 2
                else:
                    meta = _store_game_details(original, origin)
                    if not meta:
                        continue
                    title, art, _ = meta
                    art = _cached_cover(origin, title) or art
                    appid = ''
                    art_kind = 'cover' if art else ''
                    state, priority = 'En ejecución', 2
                if art:
                    art_kind = 'cover' if _wide_local_cover(art) else 'icon'
                if not art:
                    art = _executable_artwork(original)
                    art_kind = 'icon' if art else ''
                created = item.get('create_time')
                results.append({
                    'name': title, 'pid': int(item.get('pid') or 0),
                    'source': origin, 'appid': appid, 'artUrl': art,
                    'artKind': art_kind, 'session': _game_session_text(created),
                    'createdAt': float(created or 0), 'executable': str(item.get('name') or ''),
                    'active': True, 'state': state, '_priority': priority,
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, OSError, ValueError, TypeError):
                continue
    except (psutil.Error, OSError):
        return []
    # El ejecutable de la partida de League prevalece sobre su cliente.
    by_title = {}
    for item in results:
        key = (item['source'], item['appid'] or item['name'].casefold())
        existing = by_title.get(key)
        if existing is None or item['_priority'] > existing['_priority'] or (
            item['_priority'] == existing['_priority'] and item['createdAt'] < existing['createdAt']
        ):
            by_title[key] = item
    selected = sorted(by_title.values(), key=lambda row: row['createdAt'], reverse=True)[:5]
    for item in selected:
        item.pop('_priority', None)
    return selected


def _game_caption(games):
    if games:
        return 'Juego identificado por un proceso real. Portada verificada si está disponible; ícono real como respaldo.'
    return 'Aún no hay juego activo reconocido de Steam, Epic, Riot Games, EA app o Microsoft Store/Xbox.'


def _active_game(games):
    return games[0] if games else {'active': False, 'name': '', 'source': '', 'appid': '',
                                  'artUrl': '', 'session': 'N/A', 'pid': 0,
                                  'executable': '', 'state': '', 'artKind': ''}


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
    if _read_auto_power_backup():
        return False, 'Hay una sesión de juego con plan automático. Desactívala antes de cambiar el plan manualmente.'
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
    if _read_auto_power_backup():
        return False, 'Hay una sesión de juego con plan automático. Espera la restauración automática o desactívala.'
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
            'autoPowerEnabled': _auto_power_enabled(), 'autoPowerStatus': 'ESPERANDO',
            'autoPowerMessage': 'Cuando se detecte un juego, CorePulse intentará usar un plan de alto rendimiento existente.',
        }
        self._timer = QTimer(self)
        self._timer.setInterval(220)
        self._timer.timeout.connect(self._finish)
        self._mode = 'refresh'
        self._game_future = None
        self._art_attempts = {}  # (tienda, juego, appid) -> último intento; evita tráfico por sondeo
        self._art_future = None
        self._art_target = None
        self._art_poll = QTimer(self)
        self._art_poll.setInterval(180)
        self._art_poll.timeout.connect(self._finish_artwork)
        self._game_clients = set()
        self._auto_power_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='corepulse-game-power')
        self._auto_power_future = None
        self._auto_power_desired = None
        self._auto_power_applied_desired = None
        self._no_game_scans = 0
        self._auto_power_poll = QTimer(self)
        self._auto_power_poll.setInterval(180)
        self._auto_power_poll.timeout.connect(self._finish_auto_power)
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
    @Slot(str)
    def startGameWatch(self, client="health"):
        """Shared watch: Health and Overlay cannot disable one another's polling."""
        if self._closed:
            return
        self._game_clients.add(client or "health")
        if not self._game_watch.isActive():
            self._game_watch.start()
        self._scan_games()

    @Slot()
    @Slot(str)
    def stopGameWatch(self, client="health"):
        self._game_clients.discard(client or "health")
        if not self._game_clients:
            self._game_watch.stop()

    def _automatic_artwork(self, game):
        """Busca arte automáticamente, sin controles manuales ni tráfico repetido."""
        if not game.get('active') or game.get('artKind') == 'cover' or self._art_future is not None or self._closed:
            return
        source, name, appid = game.get('source', ''), game.get('name', ''), str(game.get('appid') or '')
        if not source or not name:
            return
        key = (source, name, appid)
        now = time.monotonic()
        if now - self._art_attempts.get(key, -float('inf')) < 300:
            return
        self._art_attempts[key] = now
        self._art_target = (game.get('pid'), source, name)
        self._art_future = self._executor.submit(_resolve_game_cover, source, name, appid)
        self._data = {**self._data, 'artworkMessage': 'Buscando portada verificada automáticamente…'}
        self.changed.emit()
        self._art_poll.start()

    def _update_game_cover(self, game, art, kind):
        if not art:
            return
        key = (game.get('source'), game.get('name'))
        current = self._data.get('activeGame') or {}
        if (current.get('source'), current.get('name')) != key:
            return
        updated = {**current, 'artUrl': art, 'artKind': kind}
        games = [{**item, 'artUrl': art, 'artKind': kind}
                 if (item.get('source'), item.get('name')) == key else item
                 for item in self._data.get('probableGames', [])]
        self._data = {**self._data, 'activeGame': updated, 'probableGames': games,
                      'artworkMessage': 'Portada oficial identificada automáticamente.'}
        self.changed.emit()

    def _finish_artwork(self):
        if self._art_future is None or not self._art_future.done():
            return
        try:
            artwork = self._art_future.result()
        except Exception:
            artwork = ''
        key = self._art_target
        self._art_future = None
        self._art_target = None
        self._art_poll.stop()
        current = self._data.get('activeGame') or {}
        if key and (current.get('pid'), current.get('source'), current.get('name')) == key:
            if artwork:
                self._update_game_cover(current, artwork, 'cover')
            else:
                self._data = {**self._data, 'artworkMessage': 'Portada no disponible en fuentes verificables. Se conserva el ícono del juego.'}
                self.changed.emit()

    def _scan_games(self):
        if self._closed or self._game_future is not None:
            return
        self._game_future = self._executor.submit(_detect_probable_games)
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
        # El cambio energético depende del detector de juegos y no de la pestaña abierta.
        self._consider_auto_power(games)
        # Nunca iniciar HTTP desde el hilo QML: solo programar trabajo en el executor.
        # Solo buscar imágenes remotas cuando el usuario abre Rendimiento;
        # ni el observador de energía ni el OSD envían títulos al exterior.
        if 'health' in self._game_clients:
            self._automatic_artwork(_active_game(games))

    @Slot(bool)
    def setAutoPowerEnabled(self, enabled):
        if self._closed:
            return
        try:
            _write_auto_power_enabled(bool(enabled))
        except OSError:
            self._data = {**self._data, 'autoPowerStatus': 'ERROR',
                          'autoPowerMessage': 'No se pudo guardar el ajuste; no se cambió.'}
            self.changed.emit()
            return
        self._data = {**self._data, 'autoPowerEnabled': bool(enabled)}
        self.changed.emit()
        # Activar/desactivar solicita transición sin bloquear Qt ni elevar permisos.
        self._consider_auto_power(self._data.get('probableGames') or [], force=True)

    def _consider_auto_power(self, games, force=False):
        active = bool(games) and bool(self._data.get('autoPowerEnabled'))
        if not games:
            self._no_game_scans += 1
        else:
            self._no_game_scans = 0
        # Evitar falsos cierres por una lectura transitoria de psutil.
        if not active and self._no_game_scans < 2 and not force:
            return
        self._auto_power_desired = active
        self._queue_auto_power()

    def _queue_auto_power(self):
        if self._closed or self._auto_power_future is not None:
            return
        if self._auto_power_applied_desired is self._auto_power_desired:
            return
        self._auto_power_applied_desired = self._auto_power_desired
        self._auto_power_future = self._auto_power_pool.submit(_auto_power_transition, self._auto_power_desired)
        self._auto_power_poll.start()

    def _finish_auto_power(self):
        future = self._auto_power_future
        if future is None or not future.done():
            return
        self._auto_power_future = None
        self._auto_power_poll.stop()
        try:
            status, message = future.result()
        except Exception as error:
            status, message = 'ERROR', 'Error de control de energía: ' + type(error).__name__
        self._data = {**self._data, 'autoPowerStatus': status, 'autoPowerMessage': message}
        self.changed.emit()
        if status in ('ACTIVO', 'RESTAURADO') and self._future is None:
            self.refresh()
        self._queue_auto_power()

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
        self._auto_power_poll.stop()
        # Esperar a que termine una transición en curso y restaurar en salida normal.
        # Si Windows niega el cambio o el proceso cae, el JSON permite recuperar
        # el plan anterior en el siguiente arranque con el watcher global.
        self._auto_power_pool.shutdown(wait=True, cancel_futures=True)
        try:
            _auto_power_transition(False)
        except (OSError, ValueError):
            pass
        self._art_poll.stop()
        self._executor.shutdown(wait=False, cancel_futures=True)
