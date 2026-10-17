"""Inventario y diagnóstico de red para CorePulse.

Política REAL_OR_NA:
- psutil entrega contadores, direcciones y estado del adaptador.
- Windows PowerShell completa gateway, DNS, descripción y velocidad de enlace.
- netsh wlan se usa sólo para datos Wi-Fi que Windows expone realmente.
- No se estiman SSID, señal, gateway, DNS, latencia ni pérdida de paquetes.
"""
from __future__ import annotations

import json
import os
import platform
import re
import socket
import subprocess
import time
from dataclasses import dataclass

import psutil

WINDOWS = platform.system().lower() == 'windows'


def _num(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except Exception:
        return None


def _safe_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _run(cmd, timeout=6):
    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0) if WINDOWS else 0,
            errors='replace',
        )
        return completed.returncode, completed.stdout or '', completed.stderr or ''
    except Exception as exc:
        return -1, '', str(exc)


def _powershell_json(script, timeout=7):
    if not WINDOWS:
        return None
    code, stdout, _stderr = _run(
        ['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-Command', script],
        timeout=timeout,
    )
    if code != 0 or not stdout.strip():
        return None
    try:
        return json.loads(stdout.strip())
    except Exception:
        return None


def _windows_network_inventory():
    """Obtiene metadatos nativos de Windows fuera del hilo UI."""
    script = r"""
$ErrorActionPreference='SilentlyContinue'
$adapters = @(Get-NetAdapter | ForEach-Object {
  [pscustomobject]@{
    Name=$_.Name
    InterfaceDescription=$_.InterfaceDescription
    InterfaceIndex=$_.ifIndex
    Status=$_.Status
    LinkSpeed=$_.LinkSpeed
    MediaConnectionState=$_.MediaConnectionState
    PhysicalMediaType=$_.PhysicalMediaType
    HardwareInterface=$_.HardwareInterface
  }
})
$configs = @(Get-NetIPConfiguration | ForEach-Object {
  [pscustomobject]@{
    InterfaceAlias=$_.InterfaceAlias
    InterfaceIndex=$_.InterfaceIndex
    IPv4Address=@($_.IPv4Address | ForEach-Object {$_.IPAddress})
    IPv6Address=@($_.IPv6Address | ForEach-Object {$_.IPAddress})
    IPv4DefaultGateway=@($_.IPv4DefaultGateway | ForEach-Object {$_.NextHop})
    IPv6DefaultGateway=@($_.IPv6DefaultGateway | ForEach-Object {$_.NextHop})
    DnsServers=@($_.DNSServer.ServerAddresses)
  }
})
[pscustomobject]@{Adapters=$adapters; Configs=$configs} | ConvertTo-Json -Depth 6 -Compress
"""
    data = _powershell_json(script)
    return data if isinstance(data, dict) else {}


def _parse_link_speed_mbps(text):
    raw = str(text or '').strip().replace(',', '.')
    if not raw:
        return None
    match = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*(Gbps|Mbps|Kbps|bps)', raw, re.I)
    if not match:
        return None
    value = float(match.group(1))
    unit = match.group(2).lower()
    if unit == 'gbps':
        return value * 1000.0
    if unit == 'mbps':
        return value
    if unit == 'kbps':
        return value / 1000.0
    return value / 1_000_000.0


def _wifi_inventory():
    """Extrae datos Wi-Fi de netsh. Los nombres de campo contemplan EN/ES."""
    if not WINDOWS:
        return []
    code, stdout, _stderr = _run(['netsh', 'wlan', 'show', 'interfaces'], timeout=5)
    if code != 0 or not stdout.strip():
        return []
    aliases = {
        'name': ('name', 'nombre'),
        'description': ('description', 'descripción', 'descripcion'),
        'ssid': ('ssid',),
        'signal': ('signal', 'señal', 'senal'),
        'radio_type': ('radio type', 'tipo de radio'),
        'channel': ('channel', 'canal'),
        'receive_rate': ('receive rate (mbps)', 'velocidad de recepción (mbps)', 'velocidad de recepcion (mbps)'),
        'transmit_rate': ('transmit rate (mbps)', 'velocidad de transmisión (mbps)', 'velocidad de transmision (mbps)'),
        'state': ('state', 'estado'),
    }
    records = []
    current = {}
    for line in stdout.splitlines():
        if ':' not in line:
            continue
        key, value = line.split(':', 1)
        key_n = key.strip().lower()
        value = value.strip()
        canonical = None
        for name, options in aliases.items():
            if key_n in options:
                canonical = name
                break
        if canonical is None:
            continue
        if canonical == 'name' and current.get('name'):
            records.append(current)
            current = {}
        current[canonical] = value
    if current:
        records.append(current)
    for rec in records:
        sig = str(rec.get('signal') or '').replace('%', '').strip()
        rec['signal_percent'] = _num(sig)
        rec['receive_mbps'] = _num(rec.get('receive_rate'))
        rec['transmit_mbps'] = _num(rec.get('transmit_rate'))
    return records


def _addr_parts(addrs):
    # REBUILD 081: no se recolectan direcciones MAC (identificador único de
    # hardware que ninguna pantalla necesita).
    ipv4, ipv6 = [], []
    for addr in addrs or []:
        if addr.family == socket.AF_INET and addr.address:
            ipv4.append(addr.address)
        elif addr.family == socket.AF_INET6 and addr.address:
            ipv6.append(str(addr.address).split('%')[0])
    return ipv4, ipv6


def collect_network_identity():
    """Devuelve adaptadores reales y selecciona la conexión primaria sin inferir por marca."""
    try:
        stats = psutil.net_if_stats()
    except Exception:
        stats = {}
    try:
        addrs = psutil.net_if_addrs()
    except Exception:
        addrs = {}
    try:
        counters = psutil.net_io_counters(pernic=True)
    except Exception:
        counters = {}

    win = _windows_network_inventory() if WINDOWS else {}
    win_adapters = _safe_list(win.get('Adapters')) if isinstance(win, dict) else []
    win_configs = _safe_list(win.get('Configs')) if isinstance(win, dict) else []
    by_name = {str(x.get('Name') or '').casefold(): x for x in win_adapters if isinstance(x, dict)}
    cfg_by_name = {str(x.get('InterfaceAlias') or '').casefold(): x for x in win_configs if isinstance(x, dict)}
    wifi = _wifi_inventory() if WINDOWS else []
    wifi_by_name = {str(x.get('name') or '').casefold(): x for x in wifi if isinstance(x, dict)}

    names = set(stats) | set(addrs) | set(counters)
    for item in win_adapters:
        if isinstance(item, dict) and item.get('Name'):
            names.add(str(item['Name']))

    adapters = []
    for name in sorted(names, key=lambda s: str(s).casefold()):
        stat = stats.get(name)
        nic_addrs = addrs.get(name) or []
        cnt = counters.get(name)
        ipv4, ipv6 = _addr_parts(nic_addrs)
        native = by_name.get(str(name).casefold(), {})
        cfg = cfg_by_name.get(str(name).casefold(), {})
        wlan = wifi_by_name.get(str(name).casefold(), {})
        native_speed = _parse_link_speed_mbps(native.get('LinkSpeed'))
        psutil_speed = _num(getattr(stat, 'speed', None))
        speed = native_speed if native_speed is not None and native_speed > 0 else psutil_speed if psutil_speed and psutil_speed > 0 else None
        gateways = [x for x in _safe_list(cfg.get('IPv4DefaultGateway')) + _safe_list(cfg.get('IPv6DefaultGateway')) if x]
        dns_servers = [x for x in _safe_list(cfg.get('DnsServers')) if x]
        actual_ipv4 = [x for x in _safe_list(cfg.get('IPv4Address')) if x] or ipv4
        actual_ipv6 = [x for x in _safe_list(cfg.get('IPv6Address')) if x] or ipv6
        is_up = bool(getattr(stat, 'isup', False))
        status_text = str(native.get('Status') or ('Up' if is_up else 'Down'))
        active = bool(is_up and (gateways or actual_ipv4))
        adapters.append({
            'name': str(name),
            'description': native.get('InterfaceDescription') or wlan.get('description') or None,
            'interface_index': native.get('InterfaceIndex') or cfg.get('InterfaceIndex'),
            'status': status_text,
            'is_up': is_up,
            'active_candidate': active,
            'link_speed_mbps': round(speed, 3) if speed is not None else None,
            'ipv4': actual_ipv4,
            'ipv6': actual_ipv6,
            'gateways': gateways,
            'dns_servers': dns_servers,
            'physical_media_type': native.get('PhysicalMediaType') or None,
            'media_state': native.get('MediaConnectionState') or None,
            'hardware_interface': native.get('HardwareInterface'),
            'ssid': wlan.get('ssid') or None,
            'wifi_signal_percent': wlan.get('signal_percent'),
            'wifi_radio_type': wlan.get('radio_type') or None,
            'wifi_channel': wlan.get('channel') or None,
            'wifi_receive_mbps': wlan.get('receive_mbps'),
            'wifi_transmit_mbps': wlan.get('transmit_mbps'),
            'bytes_sent_total': getattr(cnt, 'bytes_sent', None) if cnt else None,
            'bytes_recv_total': getattr(cnt, 'bytes_recv', None) if cnt else None,
            'packets_sent_total': getattr(cnt, 'packets_sent', None) if cnt else None,
            'packets_recv_total': getattr(cnt, 'packets_recv', None) if cnt else None,
            'errors_in_total': getattr(cnt, 'errin', None) if cnt else None,
            'errors_out_total': getattr(cnt, 'errout', None) if cnt else None,
            'drops_in_total': getattr(cnt, 'dropin', None) if cnt else None,
            'drops_out_total': getattr(cnt, 'dropout', None) if cnt else None,
            'sources': ['psutil.net_if_stats', 'psutil.net_if_addrs', 'psutil.net_io_counters'] + (['Windows Get-NetAdapter / Get-NetIPConfiguration'] if WINDOWS else []) + (['netsh wlan'] if wlan else []),
        })

    primary_index = None
    ranked = []
    for index, adapter in enumerate(adapters):
        score = 0
        if adapter.get('is_up'):
            score += 10
        if adapter.get('gateways'):
            score += 30
        if adapter.get('ipv4'):
            score += 10
        if adapter.get('ssid'):
            score += 2
        if str(adapter.get('name') or '').lower().startswith(('loopback', 'lo')):
            score -= 50
        ranked.append((score, index))
    if ranked:
        best_score, primary_index = max(ranked)
        if best_score <= 0:
            primary_index = None

    return {
        'timestamp': time.time(),
        'platform': platform.system(),
        'hostname': socket.gethostname() or None,
        'adapters': adapters,
        'primary_index': primary_index,
        'primary_name': adapters[primary_index]['name'] if primary_index is not None else None,
        'source': 'psutil + Windows networking APIs' if WINDOWS else 'psutil',
        'synthetic': False,
        'estimated': False,
    }


@dataclass
class NetworkTrafficSampler:
    """Calcula tasas sólo desde deltas de contadores reales de psutil."""
    previous: dict | None = None
    previous_ts: float | None = None

    def sample(self, interface_name=None):
        now = time.time()
        try:
            counters = psutil.net_io_counters(pernic=True)
        except Exception:
            counters = {}
        selected = counters.get(interface_name) if interface_name else None
        if selected is None and counters:
            # Sin interfaz primaria conocida no inventamos cuál es la conexión principal.
            current = None
        else:
            current = selected
        out = {
            'timestamp': now,
            'interface': interface_name,
            'download_bps': None,
            'upload_bps': None,
            'bytes_recv_total': getattr(current, 'bytes_recv', None) if current else None,
            'bytes_sent_total': getattr(current, 'bytes_sent', None) if current else None,
            'packets_recv_total': getattr(current, 'packets_recv', None) if current else None,
            'packets_sent_total': getattr(current, 'packets_sent', None) if current else None,
            'errors_in_total': getattr(current, 'errin', None) if current else None,
            'errors_out_total': getattr(current, 'errout', None) if current else None,
            'drops_in_total': getattr(current, 'dropin', None) if current else None,
            'drops_out_total': getattr(current, 'dropout', None) if current else None,
            'source': 'psutil.net_io_counters',
            'synthetic': False,
        }
        if current is not None and self.previous is not None and self.previous_ts is not None:
            old = self.previous.get(interface_name)
            elapsed = now - self.previous_ts
            if old is not None and elapsed > 0.05:
                recv_delta = max(0, int(current.bytes_recv) - int(old.bytes_recv))
                sent_delta = max(0, int(current.bytes_sent) - int(old.bytes_sent))
                out['download_bps'] = recv_delta / elapsed
                out['upload_bps'] = sent_delta / elapsed
        self.previous = counters
        self.previous_ts = now
        return out


def _ping_once(host, timeout_ms=900):
    if not host:
        return {'ok': False, 'latency_ms': None, 'error': 'Sin destino'}
    if WINDOWS:
        cmd = ['ping', '-n', '1', '-w', str(int(timeout_ms)), str(host)]
    else:
        timeout_s = max(1, int(round(timeout_ms / 1000.0)))
        cmd = ['ping', '-c', '1', '-W', str(timeout_s), str(host)]
    started = time.perf_counter()
    code, stdout, stderr = _run(cmd, timeout=max(2, timeout_ms / 1000.0 + 1.5))
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    if code != 0:
        return {'ok': False, 'latency_ms': None, 'error': (stderr or stdout or 'Sin respuesta').strip()[:180]}
    match = re.search(r'(?:time|tiempo)[=<]\s*([0-9]+(?:[\.,][0-9]+)?)\s*ms', stdout, re.I)
    latency = float(match.group(1).replace(',', '.')) if match else elapsed_ms
    return {'ok': True, 'latency_ms': round(latency, 2), 'error': None}


# QML adapter: keep the V485 collectors (psutil, PowerShell and netsh) as the
# source of truth; never block the Qt UI with native Windows commands.
from concurrent.futures import ThreadPoolExecutor
from PySide6.QtCore import QObject, Property, Signal, Slot, QTimer


def _display_value(value):
    if value is None or value == '' or value == []:
        return 'N/A'
    if isinstance(value, list):
        return ', '.join(str(x) for x in value if x) or 'N/A'
    return str(value)


def _flatten_network(snapshot):
    """Presentation-only projection, never invent missing adapter properties."""
    adapters = snapshot.get('adapters') or []
    index = snapshot.get('primary_index')
    primary = adapters[index] if isinstance(index, int) and 0 <= index < len(adapters) else {}
    compact = []
    for adapter in adapters:
        compact.append({
            'name': _display_value(adapter.get('name')),
            'status': _display_value(adapter.get('status')),
            'ipv4': _display_value(adapter.get('ipv4')),
            'ipv6': _display_value(adapter.get('ipv6')),
            'gateway': _display_value(adapter.get('gateways')),
            'dns': _display_value(adapter.get('dns_servers')),
            'ssid': _display_value(adapter.get('ssid')),
            'signal': (f"{adapter['wifi_signal_percent']:.0f}%" if adapter.get('wifi_signal_percent') is not None else 'N/A'),
            'linkSpeed': (f"{adapter['link_speed_mbps']:.0f} Mbps" if adapter.get('link_speed_mbps') is not None else 'N/A'),
            'isUp': bool(adapter.get('is_up')),
            'source': _display_value(adapter.get('sources')),
        })
    return {
        'adapters': compact,
        'total': len(compact),
        'primary': _display_value(primary.get('name')),
        'ipv4': _display_value(primary.get('ipv4')),
        'ipv6': _display_value(primary.get('ipv6')),
        'gateway': _display_value(primary.get('gateways')),
        'dns': _display_value(primary.get('dns_servers')),
        'ssid': _display_value(primary.get('ssid')),
        'signal': (f"{primary['wifi_signal_percent']:.0f}%" if primary.get('wifi_signal_percent') is not None else 'N/A'),
        'linkSpeed': (f"{primary['link_speed_mbps']:.0f} Mbps" if primary.get('link_speed_mbps') is not None else 'N/A'),
        'source': snapshot.get('source') or 'N/A',
    }


# --- Privacidad en pantalla (REBUILD 081) ---------------------------------
# Lo identificable no se envía a QML hasta que el usuario toca el ojo.
# - Ocultos por completo: SSID (ubicable en bases públicas como WiGLE) e IPv6
#   (suele ser pública y única; algunas incluyen la MAC).
# - Parciales: IPv4, gateway y DNS muestran el rango pero no el último tramo;
#   si una dirección IPv4 es pública se ocultan los dos últimos tramos.
HIDDEN_MARK = '••••••••'
SENSITIVE_FIELDS = ('ipv4', 'ipv6', 'gateway', 'dns', 'ssid')
FULLY_HIDDEN = ('ipv6', 'ssid')
REVEAL_SECONDS = 30


def _mask_ip(text):
    import ipaddress
    raw = str(text).strip()
    try:
        ip = ipaddress.ip_address(raw.split('%')[0])
    except ValueError:
        return HIDDEN_MARK
    if ip.version == 4:
        parts = str(ip).split('.')
        keep = 3 if (ip.is_private or ip.is_loopback or ip.is_link_local) else 2
        return '.'.join(parts[:keep] + ['•••'] * (4 - keep))
    return 'fe80:••••' if ip.is_link_local else '••••:••••:••••'


def _mask_value(field, value):
    if value in (None, '', 'N/A'):
        return 'N/A'
    if field in FULLY_HIDDEN:
        return HIDDEN_MARK
    return ', '.join(_mask_ip(item) for item in str(value).split(',') if item.strip()) or 'N/A'


def _present_network(flat, revealed):
    """Vista para QML: valores sensibles enmascarados salvo los revelados.

    ``revealed`` contiene campos de la conexión principal ('ssid', 'ipv4'…)
    y adaptadores revelados como 'adapter:<índice>'.
    """
    revealed = set(revealed or ())
    view = dict(flat)
    for field in SENSITIVE_FIELDS:
        if field not in revealed:
            view[field] = _mask_value(field, flat.get(field))
    adapters = []
    for index, adapter in enumerate(flat.get('adapters') or []):
        shown = f'adapter:{index}' in revealed
        row = dict(adapter)
        if not shown:
            for field in SENSITIVE_FIELDS:
                row[field] = _mask_value(field, adapter.get(field))
        row['revealed'] = shown
        row['hasSensitive'] = any(adapter.get(f) not in (None, '', 'N/A') for f in SENSITIVE_FIELDS)
        adapters.append(row)
    view['adapters'] = adapters
    view['revealed'] = {field: field in revealed for field in SENSITIVE_FIELDS}
    view['hasSensitive'] = {field: flat.get(field) not in (None, '', 'N/A') for field in SENSITIVE_FIELDS}
    return view


def _rate_label(value):
    if value is None:
        return 'N/A'
    if value >= 1024 * 1024:
        return f'{value / (1024 * 1024):.2f} MB/s'
    if value >= 1024:
        return f'{value / 1024:.1f} KB/s'
    return f'{value:.0f} B/s'


class NetworkHealth(QObject):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix='corepulse-network')
        self._future = None
        self._mode = ''
        self._inventory = None
        self._flat = None          # inventario completo; nunca se expone tal cual
        self._revealed = set()
        self._sampler = NetworkTrafficSampler()
        self._closed = False
        self._data = {'busy': False, 'phase': 'Sin consultar',
                      'lastUpdate': 'N/A', 'primary': 'N/A', 'total': 0,
                      'adapters': [], 'ipv4': 'N/A', 'ipv6': 'N/A', 'gateway': 'N/A',
                      'dns': 'N/A', 'ssid': 'N/A', 'signal': 'N/A',
                      'linkSpeed': 'N/A', 'download': 'N/A', 'upload': 'N/A',
                      'source': 'N/A', 'revealed': {}, 'hasSensitive': {}}
        self._poll = QTimer(self)
        self._poll.setInterval(200)
        self._poll.timeout.connect(self._finish)
        self._traffic = QTimer(self)
        self._traffic.setInterval(1200)
        self._traffic.timeout.connect(self.sampleTraffic)
        # Lo revelado vuelve a ocultarse solo, para que no quede en pantalla.
        self._autohide = QTimer(self)
        self._autohide.setSingleShot(True)
        self._autohide.setInterval(REVEAL_SECONDS * 1000)
        self._autohide.timeout.connect(self.hideSensitive)

    @Property('QVariantMap', notify=changed)
    def data(self):
        return self._data

    def _set(self, **kwargs):
        self._data = {**self._data, **kwargs}
        self.changed.emit()

    @Slot()
    def startWatch(self):
        if self._closed:
            return
        self._traffic.start()
        self.sampleTraffic()
        if self._inventory is None:
            self.refresh()

    @Slot()
    def stopWatch(self):
        self._traffic.stop()
        self.hideSensitive()

    def _publish_identity(self):
        if self._flat is not None:
            self._set(**_present_network(self._flat, self._revealed))

    @Slot(str)
    def toggleReveal(self, key):
        """Muestra u oculta un dato: 'ssid', 'ipv4', 'ipv6', 'gateway', 'dns' o 'adapter:N'."""
        key = str(key or '')
        valid = key in SENSITIVE_FIELDS or (key.startswith('adapter:') and key[8:].isdigit())
        if not valid or self._flat is None:
            return
        if key in self._revealed:
            self._revealed.discard(key)
        else:
            self._revealed.add(key)
        if self._revealed:
            self._autohide.start()
        else:
            self._autohide.stop()
        self._publish_identity()

    @Slot()
    def hideSensitive(self):
        self._autohide.stop()
        if self._revealed:
            self._revealed.clear()
            self._publish_identity()

    @Slot()
    def refresh(self):
        if self._closed or self._future:
            return
        self._mode = 'inventory'
        self._set(busy=True, phase='Consultando adaptadores reales de Windows…')
        self._future = self._executor.submit(collect_network_identity)
        self._poll.start()

    @Slot()
    def sampleTraffic(self):
        if self._closed or self._inventory is None:
            return
        raw = self._sampler.sample(self._inventory.get('primary_name'))
        download = _rate_label(raw.get('download_bps'))
        upload = _rate_label(raw.get('upload_bps'))
        if (download, upload) != (self._data.get('download'), self._data.get('upload')):
            self._set(download=download, upload=upload)

    def _finish(self):
        if self._future is None or not self._future.done():
            return
        try:
            result = self._future.result()
        except Exception:
            result = None
        mode = self._mode
        self._future = None
        self._poll.stop()
        if mode == 'inventory' and isinstance(result, dict):
            self._inventory = result
            # Reset baseline to avoid rates calculated across adapter changes.
            self._sampler = NetworkTrafficSampler()
            self._flat = _flatten_network(result)
            self._revealed.clear(); self._autohide.stop()
            self._set(**_present_network(self._flat, self._revealed), busy=False,
                      phase='Inventario completado', lastUpdate=time.strftime('%H:%M:%S'),
                      download='N/A', upload='N/A')
        else:
            self._set(busy=False, phase='Consulta no disponible: Windows no devolvió datos válidos.')

    @Slot()
    def close(self):
        self._closed = True
        self._traffic.stop()
        self._autohide.stop()
        self._poll.stop()
        self._executor.shutdown(wait=False, cancel_futures=True)
