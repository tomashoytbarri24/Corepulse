"""Prueba integrada de velocidad de Internet: solo Speedtest by Ookla.

La CLI oficial se comprueba/obtiene en Windows con SHA-256; la prueba comienza
únicamente tras aceptar una vez las condiciones de Ookla. La vista QML muestra los resultados
medidos localmente y nunca abre Speedtest.net al terminar.

REAL_OR_NA: una medición ausente queda como None, jamás se simula.
"""
from __future__ import annotations

from concurrent.futures.thread import ThreadPoolExecutor
import hashlib
import ipaddress
import json
import math
import os
import re
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time
import zipfile
from concurrent.futures import Future
from dataclasses import dataclass
from queue import Empty, Queue
from collections import deque
from threading import Thread
from typing import Callable
from urllib.request import Request, urlopen
from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot

def _num(value):
    try:
        if value is None or isinstance(value, bool):
            return None
        return float(value)
    except Exception:
        return None


def _ip_family_of(value):
    text = str(value or '').strip()
    if not text:
        return None
    # IPv6 de Windows puede incluir zone-id (fe80::1%12).
    text = text.split('%', 1)[0]
    try:
        parsed = ipaddress.ip_address(text)
    except Exception:
        return None
    return 'ipv4' if parsed.version == 4 else 'ipv6'


def _discover_source_ip(family):
    """Obtiene la IP local que Windows enrutaría para esa familia sin enviar datos."""
    family = str(family or '').strip().lower()
    if family not in ('ipv4', 'ipv6'):
        return None
    af = socket.AF_INET if family == 'ipv4' else socket.AF_INET6
    # UDP connect() solo consulta la ruta local; TEST-NET no requiere servidor externo.
    target = ('192.0.2.1', 443) if af == socket.AF_INET else ('2001:db8::1', 443, 0, 0)
    sock = None
    try:
        sock = socket.socket(af, socket.SOCK_DGRAM)
        sock.connect(target)
        candidate = sock.getsockname()[0]
        return candidate if _ip_family_of(candidate) == family else None
    except Exception:
        return None
    finally:
        try:
            if sock is not None:
                sock.close()
        except Exception:
            pass


def _safe_progress(callback, **payload):
    if not callable(callback):
        return
    try:
        callback(dict(payload))
    except Exception:
        pass


OOKLA_PROVIDER = 'ookla'
OOKLA_CLI_VERSION = '1.2.0'
OOKLA_CLI_URL = f'https://install.speedtest.net/app/cli/ookla-speedtest-{OOKLA_CLI_VERSION}-win64.zip'
# Hash del paquete oficial publicado en el manifiesto de Microsoft WinGet.
OOKLA_CLI_SHA256 = '13e3d888b845d301a556419e31f14ab9bff57e3f06089ef2fd3bdc9ba6841efa'
OOKLA_CLI_MAX_DOWNLOAD = 32 * 1024 * 1024


def _ookla_acceptance_path():
    """Preferencia local: no guarda IP, resultados ni identificadores personales."""
    base = Path(os.environ.get('LOCALAPPDATA') or (Path.home() / 'AppData' / 'Local'))
    return base / 'CorePulse' / 'ookla-acceptance.json'


def read_ookla_acceptance():
    try:
        value = json.loads(_ookla_acceptance_path().read_text(encoding='utf-8'))
        return isinstance(value, dict) and value.get('ookla_terms_accepted') is True
    except (OSError, ValueError, UnicodeError):
        return False


def save_ookla_acceptance(accepted):
    """Registra exclusivamente una aceptación explícita, o su revocación local."""
    try:
        target = _ookla_acceptance_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_suffix('.tmp')
        temp.write_text(json.dumps({'ookla_terms_accepted': bool(accepted)}, ensure_ascii=False), encoding='utf-8')
        temp.replace(target)
        return True
    except OSError:
        return False


def _subprocess_kwargs():
    kwargs = {
        'stdin': subprocess.DEVNULL,
        'stdout': subprocess.PIPE,
        'stderr': subprocess.PIPE,
        'text': True,
        'encoding': 'utf-8',
        'errors': 'replace',
    }
    if os.name == 'nt':
        kwargs['creationflags'] = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    return kwargs


def _candidate_ookla_paths():
    """Rutas plausibles de la CLI oficial, sin descargar ni instalar nada."""
    seen = set()

    def emit(value):
        if not value:
            return
        try:
            path = Path(value).expanduser()
        except Exception:
            return
        key = str(path).lower()
        if key in seen:
            return
        seen.add(key)
        yield path

    configured = os.environ.get('COREPULSE_SPEEDTEST_CLI')
    yield from emit(configured)
    yield from emit(shutil.which('speedtest'))
    yield from emit(shutil.which('speedtest.exe'))

    for env_name in ('LOCALAPPDATA', 'ProgramFiles', 'ProgramFiles(x86)'):
        base = os.environ.get(env_name)
        if not base:
            continue
        base_path = Path(base)
        for relative in (
            Path('Ookla Speedtest CLI') / 'speedtest.exe',
            Path('Speedtest') / 'speedtest.exe',
            Path('Ookla') / 'Speedtest CLI' / 'speedtest.exe',
        ):
            yield from emit(base_path / relative)

    local = os.environ.get('LOCALAPPDATA')
    if local:
        yield from emit(Path(local) / 'CorePulse' / 'tools' / 'ookla' /
                        OOKLA_CLI_VERSION / 'speedtest.exe')
        # winget crea un alias/enlace aquí. El proceso actual puede usarlo
        # inmediatamente aunque su PATH todavía no se haya refrescado.
        yield from emit(Path(local) / 'Microsoft' / 'WinGet' / 'Links' / 'speedtest.exe')

        packages = Path(local) / 'Microsoft' / 'WinGet' / 'Packages'
        if packages.is_dir():
            try:
                for folder in packages.glob('Ookla.Speedtest.CLI_*'):
                    direct = folder / 'speedtest.exe'
                    yield from emit(direct)
                    # Algunas revisiones de winget dejan el binario en un
                    # subdirectorio de versión. El patrón queda deliberadamente
                    # limitado a este paquete para no recorrer todo LOCALAPPDATA.
                    try:
                        for candidate in folder.glob('**/speedtest.exe'):
                            yield from emit(candidate)
                    except Exception:
                        pass
            except Exception:
                pass


def _probe_ookla_cli(path, timeout=4):
    try:
        p = Path(path)
        if not p.is_file():
            return None
        completed = subprocess.run(
            [str(p), '--version'], timeout=timeout, **_subprocess_kwargs()
        )
        output = f"{completed.stdout or ''}\n{completed.stderr or ''}".strip()
        lowered = output.lower()
        if completed.returncode == 0 and 'speedtest' in lowered and 'ookla' in lowered and 'speedtest-cli' not in lowered:
            version_line = next((line.strip() for line in output.splitlines() if line.strip()), 'Speedtest by Ookla')
            return {'path': str(p), 'version': version_line, 'official': True}
    except Exception:
        pass
    return None


def find_ookla_cli():
    """Devuelve sólo una CLI verificada como Speedtest by Ookla oficial."""
    for candidate in _candidate_ookla_paths():
        status = _probe_ookla_cli(candidate)
        if status:
            return status
    return None


def ookla_cli_status():
    status = find_ookla_cli()
    if status:
        return {
            'available': True,
            'path': status.get('path'),
            'version': status.get('version'),
            'provider': 'Speedtest by Ookla',
            'official_engine': True,
        }
    return {
        'available': False,
        'path': None,
        'version': None,
        'provider': 'Speedtest by Ookla',
        'official_engine': False,
        'message': 'CLI oficial de Ookla no instalada o no detectada.',
    }


def ensure_ookla_cli():
    """Prepara la CLI oficial en datos locales, sin aceptar sus términos."""
    installed = find_ookla_cli()
    if installed:
        return {'available': True, 'path': installed['path'], 'version': installed['version'],
                'provider': 'Speedtest by Ookla', 'official_engine': True,
                'downloaded': False, 'message': 'CLI oficial detectada.'}
    if os.name != 'nt':
        return {'available': False, 'path': None, 'version': None,
                'message': 'La CLI automática está disponible solo en Windows x64.'}

    local = Path(os.environ.get('LOCALAPPDATA') or (Path.home() / 'AppData' / 'Local'))
    destination_dir = local / 'CorePulse' / 'tools' / 'ookla' / OOKLA_CLI_VERSION
    destination = destination_dir / 'speedtest.exe'
    destination_dir.mkdir(parents=True, exist_ok=True)
    try:
        # Directorios temporales únicos evitan colisiones si se abre CorePulse
        # dos veces mientras se prepara la primera instalación.
        with tempfile.TemporaryDirectory(prefix='ookla-', dir=str(destination_dir)) as temp_name:
            temp_dir = Path(temp_name)
            archive_path = temp_dir / 'ookla.zip'
            request = Request(OOKLA_CLI_URL, headers={'User-Agent': 'CorePulse/086'})
            digest = hashlib.sha256()
            downloaded = 0
            with urlopen(request, timeout=25) as response, archive_path.open('wb') as archive_file:
                if not str(response.geturl()).lower().startswith('https://'):
                    raise ValueError('El servidor de Ookla no mantuvo HTTPS.')
                content_length = response.headers.get('Content-Length')
                if content_length and int(content_length) > OOKLA_CLI_MAX_DOWNLOAD:
                    raise ValueError('El paquete oficial excede el tamaño permitido.')
                while True:
                    chunk = response.read(128 * 1024)
                    if not chunk:
                        break
                    downloaded += len(chunk)
                    if downloaded > OOKLA_CLI_MAX_DOWNLOAD:
                        raise ValueError('El paquete oficial excede el tamaño permitido.')
                    digest.update(chunk)
                    archive_file.write(chunk)
            if digest.hexdigest().casefold() != OOKLA_CLI_SHA256:
                raise ValueError('La verificación SHA-256 del paquete oficial falló.')
            with zipfile.ZipFile(archive_path, 'r') as package:
                member = next((item for item in package.infolist()
                               if item.filename.casefold() == 'speedtest.exe'), None)
                if member is None or member.file_size <= 0 or member.file_size > OOKLA_CLI_MAX_DOWNLOAD:
                    raise ValueError('El ZIP oficial no contiene una CLI válida.')
                staged = temp_dir / 'speedtest.exe'
                with staged.open('wb') as output:
                    output.write(package.read(member))
            verified = _probe_ookla_cli(staged, timeout=12)
            if not verified:
                raise ValueError('El ejecutable descargado no se identificó como Speedtest by Ookla.')
            staged.replace(destination)
            verified = _probe_ookla_cli(destination, timeout=12)
            if not verified:
                destination.unlink(missing_ok=True)
                raise ValueError('No se pudo verificar la CLI instalada.')
            return {'available': True, 'path': verified['path'], 'version': verified['version'],
                    'provider': 'Speedtest by Ookla', 'official_engine': True,
                    'downloaded': True, 'message': 'CLI oficial descargada y verificada.'}
    except Exception as error:
        return {'available': False, 'path': None, 'version': None,
                'provider': 'Speedtest by Ookla', 'official_engine': False,
                'downloaded': False,
                'message': f'No se pudo preparar Ookla: {type(error).__name__}: {error}'[:220]}


def _license_error(text):
    lowered = str(text or '').lower()
    markers = ('license', 'eula', 'gdpr', 'privacy policy', 'terms of use', 'accept-license', 'accept-gdpr')
    return any(marker in lowered for marker in markers)


def list_ookla_servers(cli_path=None, limit=12, timeout=18):
    """Lista servidores cercanos que la CLI oficial permite seleccionar."""
    status = _probe_ookla_cli(cli_path) if cli_path else find_ookla_cli()
    if not status:
        return {'ok': False, 'servers': [], 'error_code': 'OOKLA_CLI_NOT_FOUND', 'message': 'CLI oficial de Ookla no detectada.'}
    try:
        completed = subprocess.run(
            [status['path'], '--servers'], timeout=timeout, **_subprocess_kwargs()
        )
    except subprocess.TimeoutExpired:
        return {'ok': False, 'servers': [], 'error_code': 'OOKLA_TIMEOUT', 'message': 'La lista de servidores de Ookla tardó demasiado.'}
    except Exception as exc:
        return {'ok': False, 'servers': [], 'error_code': 'OOKLA_ERROR', 'message': str(exc)[:180]}

    output = str(stderr_output or '').strip()
    if return_code != 0:
        code = 'OOKLA_LICENSE_REQUIRED' if _license_error(output) else 'OOKLA_SERVER_LIST_FAILED'
        message = (
            'La CLI oficial necesita que aceptes sus términos una vez.'
            if code == 'OOKLA_LICENSE_REQUIRED'
            else (output.splitlines()[-1].strip() if output.splitlines() else 'No se pudo listar servidores.')
        )
        return {'ok': False, 'servers': [], 'error_code': code, 'message': message}

    servers = []
    for line in output.splitlines():
        line = line.strip()
        if not re.match(r'^\d+\s+', line):
            continue
        parts = re.split(r'\s{2,}', line, maxsplit=3)
        if len(parts) < 3:
            continue
        try:
            server_id = int(parts[0])
        except Exception:
            continue
        name = parts[1].strip() if len(parts) > 1 else ''
        location = parts[2].strip() if len(parts) > 2 else ''
        country = parts[3].strip() if len(parts) > 3 else ''
        servers.append({
            'id': server_id,
            'name': name or None,
            'location': location or None,
            'country': country or None,
        })
        if len(servers) >= max(1, int(limit)):
            break
    return {
        'ok': bool(servers),
        'servers': servers,
        'error_code': None if servers else 'OOKLA_NO_SERVERS',
        'message': None if servers else 'La CLI no devolvió servidores cercanos.',
        'cli': status,
    }


def _ookla_bandwidth_mbps(section):
    if not isinstance(section, dict):
        return None
    bandwidth = _num(section.get('bandwidth'))
    if bandwidth is None:
        return None
    # El JSON oficial usa bytes/s en formatos machine-readable.
    return bandwidth * 8.0 / 1_000_000.0


def _ookla_latency_detail(section):
    if not isinstance(section, dict):
        return None
    latency = section.get('latency')
    if not isinstance(latency, dict):
        return None
    result = {}
    for source, target in (('iqm', 'latency_ms'), ('low', 'low_ms'), ('high', 'high_ms'), ('jitter', 'jitter_ms')):
        value = _num(latency.get(source))
        result[target] = round(value, 2) if value is not None else None
    return result if any(value is not None for value in result.values()) else None


def _ookla_result(data, duration_s, cli_status, selected_server_id=None, link_speed_mbps=None, ip_family='auto', bind_ip=None):
    if not isinstance(data, dict):
        return None
    down = data.get('download') if isinstance(data.get('download'), dict) else {}
    up = data.get('upload') if isinstance(data.get('upload'), dict) else {}
    ping = data.get('ping') if isinstance(data.get('ping'), dict) else {}
    server = data.get('server') if isinstance(data.get('server'), dict) else {}
    interface = data.get('interface') if isinstance(data.get('interface'), dict) else {}
    internal_ip = interface.get('internalIp')
    external_ip = interface.get('externalIp')
    requested_family = str(ip_family or 'auto').strip().lower()
    network_family = _ip_family_of(external_ip) or _ip_family_of(internal_ip) or _ip_family_of(bind_ip)
    route_bound = requested_family in ('ipv4', 'ipv6') and _ip_family_of(bind_ip) == requested_family

    down_mbps = _ookla_bandwidth_mbps(down)
    up_mbps = _ookla_bandwidth_mbps(up)
    latency = _num(ping.get('latency'))
    jitter = _num(ping.get('jitter'))
    packet_loss = _num(data.get('packetLoss'))
    down_bytes = int(_num(down.get('bytes')) or 0)
    up_bytes = int(_num(up.get('bytes')) or 0)
    total_bytes = max(0, down_bytes) + max(0, up_bytes)

    notes = []
    link = _num(link_speed_mbps)
    for label, value in (('descarga', down_mbps), ('subida', up_mbps)):
        if link and value is not None and value > link * 1.05:
            notes.append(
                f'La {label} oficial ({value:.1f} Mbps) supera el enlace reportado por Windows ({link:.1f} Mbps); se conserva sin modificar por provenir de Ookla.'
            )

    server_id = server.get('id')
    try:
        server_id = int(server_id) if server_id is not None else None
    except Exception:
        pass
    locked = selected_server_id is not None
    return {
        'timestamp': time.time(),
        'download_mbps': round(down_mbps, 2) if down_mbps is not None else None,
        'upload_mbps': round(up_mbps, 2) if up_mbps is not None else None,
        'latency_ms': round(latency, 2) if latency is not None else None,
        'jitter_ms': round(jitter, 2) if jitter is not None else None,
        'packet_loss_percent': round(packet_loss, 2) if packet_loss is not None else None,
        'download_latency': _ookla_latency_detail(down),
        'upload_latency': _ookla_latency_detail(up),
        'latency_samples_ms': [],
        'download_points': [],
        'upload_points': [],
        'bytes_transferred': total_bytes,
        'data_mb': round(total_bytes / 1_000_000.0, 2),
        'duration_s': round(float(duration_s), 2),
        # REBUILD 081: sin IP pública/interna, proveedor, interfaz ni ubicación
        # del servidor (delata la ciudad): sólo lo necesario para la medición.
        'server': {'id': server_id,
                   'name': str(server.get('name') or '')[:90],
                   'location': str(server.get('location') or '')[:90]},
        'network_family': network_family,
        'requested_ip_family': requested_family,
        'route_bound': route_bound,
        'is_vpn': interface.get('isVpn'),
        'provider': 'Speedtest by Ookla',
        'provider_key': OOKLA_PROVIDER,
        'source': 'Official Speedtest CLI / Speedtest Server Network',
        'method': 'official Ookla Speedtest CLI result; machine-readable bandwidth converted from B/s to Mbps',
        'official_engine': True,
        'speedtest_net_comparable': True,
        'server_locked': locked,
        'comparability': (
            f'Motor oficial + servidor fijado + ruta {requested_family.upper()} fijada. Verifica que Speedtest.net use la misma familia/IP pública.'
            if locked and route_bound else
            'Motor y servidor fijados, pero la familia IP no está fijada; IPv4/IPv6 pueden tomar rutas distintas.'
            if locked else
            'Motor oficial de Ookla; servidor y/o ruta pueden diferir de otra ejecución de Speedtest.net.'
        ),
        'cli_path': cli_status.get('path') if isinstance(cli_status, dict) else None,
        'cli_version': cli_status.get('version') if isinstance(cli_status, dict) else None,
        'link_speed_mbps': link_speed_mbps,
        'validation_notes': notes,
        'active_test': True,
        'synthetic': False,
        'estimated': False,
        'ok': down_mbps is not None or up_mbps is not None,
    }


def _ookla_stream_event(event, callback):
    """Publica solo métricas observadas de eventos JSONL oficiales de Ookla.

    Los valores de bandwidth están en BYTES/segundo. El evento 'result'
    contiene el resultado final; nunca se usa un evento parcial como final.
    """
    if not isinstance(event, dict):
        return
    phase = event.get('type')
    if phase == 'testStart':
        server = event.get('server')
        name = str(server.get('name') or '').strip()[:90] if isinstance(server, dict) else ''
        if name:
            _safe_progress(callback, phase='preparing', message='Servidor Ookla seleccionado: ' + name,
                           live_server_name=name)
        return
    if phase not in ('ping', 'download', 'upload'):
        return
    payload = {
        'phase': phase,
        'message': {
            'ping': 'Midiendo ping y jitter con Ookla…',
            'download': 'Midiendo velocidad de descarga…',
            'upload': 'Midiendo velocidad de subida…',
        }[phase],
    }
    # Progreso real informado por la CLI; no inferimos porcentajes por tiempo.
    fraction = _num(event.get('progress'))
    if fraction is not None and math.isfinite(fraction) and 0 <= fraction <= 1:
        payload['percent'] = round(fraction * 100)
    section = event.get(phase)
    if isinstance(section, dict):
        if phase in ('download', 'upload'):
            mbps = _ookla_bandwidth_mbps(section)
            if mbps is not None and math.isfinite(mbps) and mbps >= 0:
                payload['live_rate_mbps'] = round(mbps, 2)
                payload['live_download_mbps' if phase == 'download' else 'live_upload_mbps'] = round(mbps, 2)
        elif phase == 'ping':
            for key, target in (('latency', 'live_ping_ms'), ('jitter', 'live_jitter_ms')):
                value = _num(section.get(key))
                if value is not None and math.isfinite(value) and value >= 0:
                    payload[target] = round(value, 2)
    _safe_progress(callback, **payload)


def _read_ookla_jsonl(args, timeout, progress):
    """Lee fases/velocidades en vivo sin bloquear la GUI ni perder el resultado.

    Lee stdout y stderr por separado para evitar interbloqueos con pipes,
    aplica timeout incluso si el proceso queda bloqueado en una lectura y
    limita el texto de errores. No almacena IP o datos identificables de eventos.
    """
    process = subprocess.Popen(args, bufsize=1, **_subprocess_kwargs())
    messages = Queue()
    errors = deque(maxlen=12)

    def stdout_reader():
        try:
            for line in process.stdout:
                messages.put(line[:65536])
        finally:
            messages.put(None)

    def stderr_reader():
        try:
            for line in process.stderr:
                errors.append(line.strip()[:500])
        finally:
            process.stderr.close()

    stdout_thread = Thread(target=stdout_reader, name='corepulse-ookla-jsonl', daemon=True)
    stderr_thread = Thread(target=stderr_reader, name='corepulse-ookla-stderr', daemon=True)
    stdout_thread.start()
    stderr_thread.start()
    deadline = time.monotonic() + max(1, float(timeout))
    ended = False
    final_data = None
    while not ended or process.poll() is None:
        if time.monotonic() >= deadline:
            process.kill()
            process.wait(timeout=5)
            stdout_thread.join(timeout=1)
            stderr_thread.join(timeout=1)
            raise subprocess.TimeoutExpired(args, timeout)
        try:
            line = messages.get(timeout=0.15)
        except Empty:
            continue
        if line is None:
            ended = True
            continue
        try:
            event = json.loads(line)
        except (ValueError, TypeError):
            continue
        if not isinstance(event, dict):
            continue
        if event.get('type') == 'result':
            final_data = event
        else:
            _ookla_stream_event(event, progress)

    stdout_thread.join(timeout=1)
    stderr_thread.join(timeout=1)
    return process.wait(timeout=5), final_data, '\n'.join(errors)


def run_ookla_speedtest(cli_path=None, server_id=None, progress=None, link_speed_mbps=None, timeout=150, ip_family='auto', bind_ip=None, accepted_terms=False):
    if not accepted_terms:
        return {
            'timestamp': time.time(), 'ok': False,
            'download_mbps': None, 'upload_mbps': None, 'latency_ms': None, 'jitter_ms': None,
            'provider': 'Speedtest by Ookla', 'provider_key': OOKLA_PROVIDER,
            'official_engine': False, 'speedtest_net_comparable': False,
            'error_code': 'OOKLA_CONSENT_REQUIRED',
            'error': 'Revisa y acepta los términos y el aviso de privacidad de Ookla antes de iniciar la prueba.',
            'active_test': False, 'synthetic': False, 'estimated': False,
            'server': {}, 'validation_notes': [],
        }
    status = _probe_ookla_cli(cli_path) if cli_path else find_ookla_cli()
    if not status:
        return {
            'timestamp': time.time(), 'ok': False,
            'download_mbps': None, 'upload_mbps': None, 'latency_ms': None, 'jitter_ms': None,
            'provider': 'Speedtest by Ookla', 'provider_key': OOKLA_PROVIDER,
            'official_engine': False, 'speedtest_net_comparable': False,
            'error_code': 'OOKLA_CLI_NOT_FOUND',
            'error': 'No se detectó la CLI oficial de Speedtest by Ookla.',
            'action': 'Instala/configura la CLI oficial de Ookla y vuelve a intentar.',
            'active_test': False, 'synthetic': False, 'estimated': False,
            'server': {}, 'validation_notes': [],
        }

    requested_family = str(ip_family or 'auto').strip().lower()
    if requested_family not in ('auto', 'ipv4', 'ipv6'):
        requested_family = 'auto'
    source_ip = str(bind_ip or '').strip() or None
    if requested_family == 'auto':
        source_ip = None
    if requested_family in ('ipv4', 'ipv6'):
        if _ip_family_of(source_ip) != requested_family:
            source_ip = _discover_source_ip(requested_family)
        if _ip_family_of(source_ip) != requested_family:
            return {
                'timestamp': time.time(), 'ok': False,
                'download_mbps': None, 'upload_mbps': None, 'latency_ms': None, 'jitter_ms': None,
                'provider': 'Speedtest by Ookla', 'provider_key': OOKLA_PROVIDER,
                'official_engine': True, 'speedtest_net_comparable': False,
                'error_code': 'OOKLA_ROUTE_UNAVAILABLE',
                'error': f'No se encontró una ruta {requested_family.upper()} utilizable para ejecutar Speedtest.',
                'action': 'Elige Ruta automática o revisa la configuración IP del adaptador.',
                'active_test': False, 'synthetic': False, 'estimated': False,
                'server': {}, 'validation_notes': [],
                'requested_ip_family': requested_family, 'route_bound': False,
            }

    args = [status['path'], '--format=jsonl', '--accept-license', '--accept-gdpr']
    if source_ip is not None:
        # La CLI oficial permite fijar la IP de origen con --ip; esto evita que
        # Windows elija IPv6 mientras el navegador está usando IPv4 (o viceversa).
        args.append(f'--ip={source_ip}')
    if server_id is not None:
        try:
            args.append(f'--server-id={int(server_id)}')
        except Exception:
            pass
    _safe_progress(progress, phase='preparing', message='Conectando con Speedtest by Ookla…')
    started = time.perf_counter()
    try:
        return_code, data, stderr_output = _read_ookla_jsonl(args, timeout, progress)
    except subprocess.TimeoutExpired:
        return {
            'timestamp': time.time(), 'ok': False,
            'download_mbps': None, 'upload_mbps': None, 'latency_ms': None, 'jitter_ms': None,
            'provider': 'Speedtest by Ookla', 'provider_key': OOKLA_PROVIDER,
            'official_engine': True, 'speedtest_net_comparable': True,
            'error_code': 'OOKLA_TIMEOUT', 'error': 'La prueba oficial agotó el tiempo de espera.',
            'active_test': True, 'synthetic': False, 'estimated': False,
            'server': {}, 'validation_notes': [],
        }
    except Exception as exc:
        return {
            'timestamp': time.time(), 'ok': False,
            'download_mbps': None, 'upload_mbps': None, 'latency_ms': None, 'jitter_ms': None,
            'provider': 'Speedtest by Ookla', 'provider_key': OOKLA_PROVIDER,
            'official_engine': True, 'speedtest_net_comparable': True,
            'error_code': 'OOKLA_ERROR', 'error': str(exc)[:180],
            'active_test': False, 'synthetic': False, 'estimated': False,
            'server': {}, 'validation_notes': [],
        }

    elapsed = time.perf_counter() - started
    output = str(stderr_output or '').strip()
    if return_code != 0:
        license_required = _license_error(output)
        return {
            'timestamp': time.time(), 'ok': False,
            'download_mbps': None, 'upload_mbps': None, 'latency_ms': None, 'jitter_ms': None,
            'provider': 'Speedtest by Ookla', 'provider_key': OOKLA_PROVIDER,
            'official_engine': True, 'speedtest_net_comparable': True,
            'error_code': 'OOKLA_LICENSE_REQUIRED' if license_required else 'OOKLA_TEST_FAILED',
            'error': (
                'La CLI oficial necesita que aceptes sus términos una vez.'
                if license_required else
                (output.splitlines()[-1].strip() if output.splitlines() else 'Speedtest by Ookla no pudo completar la prueba.')
            ),
            'action': 'Ejecuta speedtest una vez en una consola para revisar y aceptar los términos de Ookla.' if license_required else None,
            'active_test': False, 'synthetic': False, 'estimated': False,
            'server': {}, 'validation_notes': [],
        }

    result = _ookla_result(
        data, elapsed, status,
        selected_server_id=server_id,
        link_speed_mbps=link_speed_mbps,
        ip_family=requested_family,
        bind_ip=source_ip,
    )
    if result is None:
        return {
            'timestamp': time.time(), 'ok': False,
            'download_mbps': None, 'upload_mbps': None, 'latency_ms': None, 'jitter_ms': None,
            'provider': 'Speedtest by Ookla', 'provider_key': OOKLA_PROVIDER,
            'official_engine': True, 'speedtest_net_comparable': True,
            'error_code': 'OOKLA_INVALID_OUTPUT', 'error': 'La CLI oficial no devolvió un resultado JSON válido.',
            'active_test': True, 'synthetic': False, 'estimated': False,
            'server': {}, 'validation_notes': [],
        }
    _safe_progress(progress, phase='done', percent=100, message='Speedtest by Ookla completado', result=result)
    return result


@dataclass
class InternetSpeedTest:
    """Runner síncrono del motor oficial; la pantalla no abre navegador."""

    link_speed_mbps: float | None = None
    provider: str = OOKLA_PROVIDER
    server_id: int | None = None
    ookla_cli_path: str | None = None
    ip_family: str = 'auto'
    bind_ip: str | None = None
    ookla_terms_accepted: bool = False

    def cli_status(self):
        return _probe_ookla_cli(self.ookla_cli_path) if self.ookla_cli_path else ookla_cli_status()

    def list_servers(self, limit=12):
        return list_ookla_servers(self.ookla_cli_path, limit=limit)

    def run(self, progress: Callable[[dict], None] | None = None):
        if self.provider != OOKLA_PROVIDER:
            return {'ok': False, 'error_code': 'PROVIDER_DISABLED',
                    'error': 'El único proveedor disponible es Speedtest by Ookla.',
                    'active_test': False, 'download_mbps': None, 'upload_mbps': None,
                    'latency_ms': None, 'jitter_ms': None}
        return run_ookla_speedtest(
            cli_path=self.ookla_cli_path, server_id=self.server_id,
            progress=progress, link_speed_mbps=self.link_speed_mbps,
            ip_family=self.ip_family, bind_ip=self.bind_ip,
            accepted_terms=self.ookla_terms_accepted,
        )


class NetworkSpeedTest(QObject):
    """QML adapter; starts external network traffic only after an explicit click."""
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix='corepulse-speed-test')
        self._future: Future | None = None
        self._provision_future: Future | None = None
        self._mode = ""
        self._progress_queue: Queue = Queue()
        self._closed = False
        self._data = {'busy': False, 'phase': 'idle', 'percent': 0,
                      'termsAccepted': read_ookla_acceptance(),
                      'message': 'La prueba no se ejecuta al abrir esta pantalla.',
                      'result': {}, 'ooklaAvailable': False, 'ooklaChecked': False,
                      'ooklaDownloading': False, 'ooklaVersion': 'N/A',
                      'status': 'Listo', 'live_rate_mbps': None,
                      'live_download_mbps': None, 'live_upload_mbps': None,
                      'live_ping_ms': None, 'live_jitter_ms': None,
                      'live_server_name': ''}
        self._poll = QTimer(self)
        self._poll.setInterval(160)
        self._poll.timeout.connect(self._finish)
        if os.name == 'nt':
            self._data.update(ooklaDownloading=True,
                              message='Preparando la CLI oficial de Ookla en segundo plano…')
            self._provision_future = self._executor.submit(ensure_ookla_cli)
            self._poll.start()
        else:
            self._data.update(ooklaChecked=True,
                              message='La CLI oficial automática solo está disponible en Windows x64.')

    @Property('QVariantMap', notify=changed)
    def data(self):
        return self._data

    def _progress(self, payload):
        try:
            self._progress_queue.put_nowait(dict(payload or {}))
        except Exception:
            pass

    @Slot()
    def checkOokla(self):
        """Reintenta preparar la CLI oficial cuando el inicio no pudo descargarla."""
        if self._closed or self._provision_future is not None:
            return
        if self._data.get('ooklaAvailable'):
            return
        self._data = {**self._data, 'ooklaDownloading': True, 'ooklaChecked': False,
                      'message': 'Descargando y verificando la CLI oficial de Ookla…',
                      'status': 'Preparando Ookla…'}
        self.changed.emit()
        self._provision_future = self._executor.submit(ensure_ookla_cli)
        self._poll.start()

    @Slot(str)
    def start(self, provider=OOKLA_PROVIDER):
        # Solo funciona sin diálogo cuando ya hubo aceptación explícita previa.
        self._start(provider, False)

    @Slot(str, bool)
    def startWithConsent(self, provider, ookla_terms_accepted):
        self._start(provider, bool(ookla_terms_accepted))

    @Slot()
    def forgetOoklaTerms(self):
        # Restablece permiso local; no modifica preferencias externas de Ookla.
        if self._future is not None or self._closed:
            return
        if save_ookla_acceptance(False):
            self._data = {**self._data, 'termsAccepted': False,
                          'message': 'Las condiciones volverán a solicitarse antes de otra prueba.'}
            self.changed.emit()

    def _start(self, provider, ookla_terms_accepted):
        if self._closed or self._future is not None:
            return
        provider = str(provider or OOKLA_PROVIDER).strip().lower()
        if provider != OOKLA_PROVIDER:
            self._data = {**self._data, 'status': 'Proveedor no admitido', 'message': 'Solo Ookla está disponible.'}
            self.changed.emit()
            return
        if provider == OOKLA_PROVIDER and self._data.get('ooklaDownloading'):
            self._data = {**self._data, 'status': 'Ookla preparándose', 'message': 'Espera a que termine la descarga verificada de la CLI oficial.'}
            self.changed.emit()
            return
        if provider == OOKLA_PROVIDER and not self._data.get('ooklaAvailable'):
            self._data = {**self._data, 'status': 'Ookla no disponible', 'message': 'La descarga automática no terminó. Usa «Preparar Ookla» para reintentar.'}
            self.changed.emit()
            return
        accepted = bool(ookla_terms_accepted) or read_ookla_acceptance()
        if not accepted:
            self._data = {**self._data, 'termsAccepted': False,
                          'status': 'Falta aceptar los términos',
                          'message': 'Acepta las condiciones de Ookla una sola vez para iniciar pruebas futuras sin diálogos.'}
            self.changed.emit()
            return
        # Al confirmar por primera vez se guarda el permiso. Nunca se da por aceptado en silencio.
        if ookla_terms_accepted and not save_ookla_acceptance(True):
            self._data = {**self._data, 'status': 'Error de preferencias',
                          'message': 'No se pudo recordar tu aceptación de Ookla; revisa los permisos de escritura.'}
            self.changed.emit()
            return
        self._data = {**self._data, 'termsAccepted': True,
                      'busy': True, 'phase': 'preparing', 'percent': 0,
                      'message': 'Preparando una prueba activa de descarga y subida…',
                      'status': 'En curso', 'result': {},
                      'live_rate_mbps': None, 'live_download_mbps': None,
                      'live_upload_mbps': None, 'live_ping_ms': None,
                      'live_jitter_ms': None, 'live_server_name': ''}
        self._mode = "speed_test"
        self.changed.emit()
        runner = InternetSpeedTest(provider=provider,
                                   ookla_terms_accepted=accepted)
        self._future = self._executor.submit(runner.run, self._progress)
        self._poll.start()

    def _finish(self):
        if self._provision_future is not None and self._provision_future.done():
            future = self._provision_future
            self._provision_future = None
            try:
                result = future.result()
            except Exception as error:
                result = {'available': False,
                          'message': f'No se pudo preparar Ookla: {type(error).__name__}: {error}'}
            available = bool(result.get('available')) if isinstance(result, dict) else False
            status_text = 'Ookla disponible' if available else 'Ookla no disponible'
            message_text = str(result.get('message') or ('CLI oficial lista.' if available else 'Ookla no disponible.'))
            self._data = {**self._data, 'ooklaDownloading': False, 'ooklaChecked': True,
                          'ooklaAvailable': available,
                          'ooklaVersion': str(result.get('version') or 'N/A') if available else 'N/A',
                          'message': self._data.get('message') if self._data.get('busy') else message_text,
                          'status': self._data.get('status') if self._data.get('busy') else status_text}
            self.changed.emit()
        latest = None
        updates = {}
        try:
            while True:
                item = self._progress_queue.get_nowait()
                latest = item
                # No descartar el ping al consumir la primera muestra de descarga.
                # Las fases posteriores sustituyen la tasa de la fase anterior.
                if item.get('phase') in ('ping', 'download', 'upload'):
                    updates['phase'] = item['phase']
                for key in ('percent', 'message', 'live_rate_mbps', 'live_download_mbps',
                            'live_upload_mbps', 'live_ping_ms', 'live_jitter_ms', 'live_server_name'):
                    if key in item:
                        updates[key] = item[key]
        except Empty:
            pass
        if latest:
            self._data = {**self._data, **updates}
        if self._future is None:
            if self._provision_future is None:
                self._poll.stop()
            if latest:
                self.changed.emit()
            return
        if not self._future.done():
            if latest:
                self.changed.emit()
            return
        mode = self._mode
        self._mode = ""
        try:
            result = self._future.result()
        except Exception as error:
            result = {'ok': False, 'download_mbps': None, 'upload_mbps': None,
                      'latency_ms': None, 'jitter_ms': None,
                      'error': f'{type(error).__name__}: {error}', 'synthetic': False, 'estimated': False}
        self._future = None
        # El resultado permanece dentro de CorePulse, sin abrir URL externa.
        if isinstance(result, dict):
            result.pop('_official_web_link', None)
        if self._provision_future is None:
            self._poll.stop()
        self._data = {**self._data, 'busy': False, 'phase': 'done', 'percent': 100,
                      'status': 'Completada' if result.get('ok') else 'N/A',
                      'message': str(result.get('error') or result.get('comparability') or 'Prueba finalizada.'),
                      'result': result}
        self.changed.emit()

    @Slot()
    def close(self):
        self._closed = True
        self._poll.stop()
        self._executor.shutdown(wait=False, cancel_futures=True)
