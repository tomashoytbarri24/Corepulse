"""Actualización directa de controladores para CorePulse.

V321 elimina la dependencia del Windows Update Agent. El flujo es:

1. inventario PnP real del equipo;
2. búsqueda online por Hardware ID exacto;
3. comparación de versión instalada vs paquete publicado;
4. descarga directa del paquete desde el catálogo;
5. validación de firma y Hardware ID dentro del INF;
6. respaldo del INF actual + punto de restauración;
7. instalación mediante pnputil.

La fuente inicial de cobertura amplia es Microsoft Update Catalog, pero CorePulse
no usa el servicio local Windows Update ni pide a Windows que seleccione/instale
el controlador. CorePulse hace la búsqueda, descarga, validación e instalación.
"""
from __future__ import annotations

import base64
import ctypes
import json
import logging
import os
import platform
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse, unquote

from core.cancellable_process import run as run_cancellable
from core.runtime_paths import data_path

logger = logging.getLogger('CorePulse.DriverUpdates')

POLICY = 'DIRECT_CATALOG_EXACT_HWID + VERSION_NEWER + SIGNATURE_VERIFY + INF_HWID_VERIFY + PNPUTIL'
CATALOG_BASE = 'https://www.catalog.update.microsoft.com'
MAX_SCAN_DEVICES = 128
MAX_RESULTS_PER_DEVICE = 12
MAX_QUERIES_PER_DEVICE = 6


def _friendly_error(raw: str) -> str:
    text = str(raw or '').strip()
    low = text.casefold()
    if 'access is denied' in low or 'acceso denegado' in low or 'unauthorized' in low:
        return 'Windows rechazó la operación por permisos. Ejecuta CorePulse como administrador.'
    if 'timed out' in low or 'tiempo de espera' in low or 'timeout' in low:
        return 'La consulta del catálogo superó el tiempo límite. Revisa Internet e inténtalo nuevamente.'
    if 'winerror 206' in low or 'demasiado largo' in low or 'filename or extension is too long' in low:
        return 'El escaneo generó una solicitud demasiado grande para la línea de comandos de Windows. CorePulse la ejecutará mediante un script temporal seguro.'
    if 'name resolution' in low or 'resolve' in low or 'connection' in low or 'conexión' in low:
        return 'No se pudo conectar al catálogo de controladores. Revisa la conexión a Internet.'
    return text or 'No se pudo completar la operación de controladores.'


def _run_powershell_json(script: str, timeout: int = 300) -> tuple[list[dict[str, Any]], str | None]:
    """Ejecuta PowerShell sin transportar el script por la línea de comandos.

    V322 amplió mucho el payload del escaneo profundo (múltiples Hardware IDs
    por dispositivo). Pasarlo con ``powershell -Command <script>`` puede superar
    el límite de CreateProcess de Windows y producir ``WinError 206``. Desde
    V323 el script se materializa temporalmente como ``.ps1`` y PowerShell recibe
    sólo una ruta corta mediante ``-File``. El contenido y la política del
    escaneo no cambian; únicamente se elimina el límite de longitud del comando.
    """
    if platform.system() != 'Windows':
        return [], 'Windows requerido'
    prefix = (
        "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; "
        "$OutputEncoding=[System.Text.Encoding]::UTF8; "
        "$ProgressPreference='SilentlyContinue'; "
        "$ErrorActionPreference='Stop'; "
    )
    wrapped = prefix + f"""
{script}
if ($null -eq $result) {{ Write-Output '[]' }} else {{ ConvertTo-Json -InputObject @($result) -Depth 8 -Compress }}
"""

    ps1_path = None
    try:
        # Nombre corto en %TEMP% para mantener también el propio path muy por
        # debajo de MAX_PATH. utf-8-sig añade BOM, compatible con Windows
        # PowerShell 5.1 cuando se usa -File.
        fd, raw_path = tempfile.mkstemp(prefix='cpdrv_', suffix='.ps1')
        os.close(fd)
        ps1_path = Path(raw_path)
        ps1_path.write_text(wrapped, encoding='utf-8-sig')

        cmd = [
            'powershell.exe', '-NoLogo', '-NoProfile', '-NonInteractive',
            '-ExecutionPolicy', 'Bypass', '-File', str(ps1_path),
        ]
        cp = run_cancellable(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=timeout,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            shell=False,
        )
    except subprocess.TimeoutExpired:
        return [], 'La operación superó el tiempo límite.'
    except Exception as exc:
        logger.exception('[DRIVER_CATALOG] PowerShell falló')
        return [], _friendly_error(str(exc))
    finally:
        if ps1_path is not None:
            try:
                ps1_path.unlink(missing_ok=True)
            except Exception:
                pass

    if cp.returncode != 0:
        raw = (cp.stderr or cp.stdout or '').strip()
        logger.error('[DRIVER_CATALOG] PowerShell rc=%s: %s', cp.returncode, raw[:6000])
        return [], _friendly_error(raw)
    out = (cp.stdout or '').strip()
    if not out:
        return [], None
    try:
        obj = json.loads(out)
    except Exception:
        logger.error('[DRIVER_CATALOG] JSON inválido: %s', out[:6000])
        return [], 'El catálogo respondió con datos que CorePulse no pudo interpretar.'
    rows = obj if isinstance(obj, list) else [obj]
    return [x for x in rows if isinstance(x, dict)], None


def _normalize_hwid(value: Any) -> str:
    return str(value or '').strip().upper().replace('/', '\\')


def _hardware_ids(item: dict[str, Any]) -> list[str]:
    raw = item.get('HardwareIds')
    if isinstance(raw, str):
        values = [x for x in raw.split(';;') if x.strip()]
    elif isinstance(raw, (list, tuple)):
        values = list(raw)
    else:
        values = []
    out: list[str] = []
    for value in values:
        norm = _normalize_hwid(value)
        if norm and norm not in out:
            out.append(norm)
    device_id = _normalize_hwid(item.get('DeviceID'))
    if device_id and '\\' in device_id:
        prefix = device_id.rsplit('\\', 1)[0]
        if prefix and prefix not in out:
            out.append(prefix)
    return out


def _match_update(update: dict[str, Any], installed_items: Iterable[dict[str, Any]]) -> dict[str, Any] | None:
    target = _normalize_hwid(update.get('hardware_id'))
    if not target:
        return None
    for item in installed_items or []:
        if isinstance(item, dict) and target in _hardware_ids(item):
            return item
    return None


def _version_tuple(value: Any) -> tuple[int, ...]:
    parts = [int(x) for x in re.findall(r'\d+', str(value or ''))]
    return tuple(parts[:8])


def _version_from_title(title: str) -> str | None:
    matches = re.findall(r'(?<!\d)(\d+(?:\.\d+){2,})(?!\d)', str(title or ''))
    return matches[-1] if matches else None


def _is_newer(candidate: Any, installed: Any) -> bool:
    cand = _version_tuple(candidate)
    inst = _version_tuple(installed)
    if not cand or not inst:
        return False
    length = max(len(cand), len(inst))
    return cand + (0,) * (length - len(cand)) > inst + (0,) * (length - len(inst))


def _is_firmware_title(title: str) -> bool:
    low = f" {str(title or '').casefold()} "
    return any(token in low for token in (' firmware ', ' bios ', ' uefi '))


def _target_hwid(item: dict[str, Any]) -> str | None:
    ids = _hardware_ids(item)
    if not ids:
        return None
    preferred = ('PCI\\', 'HDAUDIO\\', 'USB\\', 'ACPI\\', 'BTH\\', 'HID\\', 'MONITOR\\', 'ROOT\\')
    for prefix in preferred:
        for hwid in ids:
            if hwid.startswith(prefix):
                return hwid
    return ids[0]


def _query_terms_for_target(item: dict[str, Any]) -> list[dict[str, str]]:
    """Genera consultas amplias sin relajar la validación final del INF.

    Driver Booster puede apoyarse en una base privada propia. CorePulse compensa
    consultando varias identidades reales del mismo dispositivo: todos los
    Hardware IDs expuestos por Windows y, como fallback de descubrimiento,
    nombre/proveedor. La instalación sigue exigiendo coincidencia exacta dentro
    del INF descargado.
    """
    terms: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(value: Any, kind: str):
        raw = str(value or '').strip()
        key = raw.casefold()
        if not raw or key in seen or len(terms) >= MAX_QUERIES_PER_DEVICE:
            return
        seen.add(key)
        terms.append({'query': raw, 'kind': kind})

    for hwid in _hardware_ids(item):
        add(hwid, 'HARDWARE_ID')
        # También consulta una variante menos específica quitando REV/SUBSYS
        # cuando existe. Sigue siendo sólo búsqueda; el INF se valida después.
        generic = re.sub(r'&REV_[0-9A-F]{2,4}', '', hwid, flags=re.I)
        generic = re.sub(r'&SUBSYS_[0-9A-F]{8}', '', generic, flags=re.I)
        if generic != hwid:
            add(generic, 'COMPATIBLE_ID')

    name = str(item.get('DeviceName') or '').strip()
    provider = str(item.get('DriverProviderName') or '').strip()
    if name:
        add(f'{provider} {name}'.strip(), 'DEVICE_MODEL')
        add(name, 'DEVICE_NAME')
    return terms


def _scan_targets(installed_items: Iterable[dict[str, Any]], limit: int = MAX_SCAN_DEVICES) -> list[dict[str, Any]]:
    rows = [x for x in (installed_items or []) if isinstance(x, dict)]
    targets: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in rows:
        hwid = _target_hwid(item)
        if not hwid or hwid in seen:
            continue
        seen.add(hwid)
        provider = str(item.get('DriverProviderName') or '').strip()
        name = str(item.get('DeviceName') or '').strip()
        priority = int(item.get('hardware_priority') or 0)
        inbox = bool(item.get('microsoft_inbox_generic'))
        # Evita gastar consultas en dispositivos virtuales/inbox de Windows,
        # pero conserva hardware físico aunque su prioridad aún no esté clasificada.
        if inbox:
            continue
        physical_hint = hwid.startswith(('PCI\\', 'HDAUDIO\\', 'USB\\', 'ACPI\\', 'BTH\\', 'HID\\', 'MONITOR\\', 'ROOT\\'))
        if priority <= 0 and not physical_hint:
            continue
        targets.append({
            'hardware_id': hwid,
            'hardware_ids': _hardware_ids(item),
            'device_name': name or 'Controlador',
            'installed_version': str(item.get('DriverVersion') or '').strip() or None,
            'installed_provider': provider or None,
            'installed_inf': str(item.get('InfName') or '').strip() or None,
            'device_id': str(item.get('DeviceID') or '').strip() or None,
            'hardware_category': item.get('hardware_category'),
            'hardware_priority': priority,
            'query_terms': _query_terms_for_target(item),
        })
    targets.sort(key=lambda x: (int(x.get('hardware_priority') or 0), bool(x.get('installed_provider'))), reverse=True)
    return targets[: max(1, int(limit))]


def _catalog_search_batch(targets: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str | None]:
    if not targets:
        return [], None

    expanded = []
    for index, target in enumerate(targets):
        target_key = str(target.get('device_id') or target.get('hardware_id') or f'target-{index}')
        terms = list(target.get('query_terms') or [])
        if not terms:
            terms = [{'query': str(target.get('hardware_id') or ''), 'kind': 'HARDWARE_ID'}]
        for term in terms[:MAX_QUERIES_PER_DEVICE]:
            query = str(term.get('query') or '').strip()
            if not query:
                continue
            expanded.append({
                'target_key': target_key,
                'query': query,
                'query_kind': str(term.get('kind') or 'HARDWARE_ID'),
                'device_name': target.get('device_name'),
                'installed_version': target.get('installed_version'),
                'installed_provider': target.get('installed_provider'),
                'installed_inf': target.get('installed_inf'),
                'device_id': target.get('device_id'),
                'hardware_category': target.get('hardware_category'),
            })

    payload = base64.b64encode(json.dumps(expanded, ensure_ascii=False).encode('utf-8')).decode('ascii')
    script = rf"""
$raw=[System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('{payload}'))
$targets=ConvertFrom-Json $raw
$result=@()
$headers=@{{'User-Agent'='Mozilla/5.0 CorePulse/322';'Accept-Language'='en-US,en;q=0.8'}}
foreach($t in @($targets)) {{
  $query=[string]$t.query
  if([string]::IsNullOrWhiteSpace($query)) {{ continue }}
  try {{
    $url='{CATALOG_BASE}/Search.aspx?q=' + [uri]::EscapeDataString($query)
    $resp=Invoke-WebRequest -Uri $url -UseBasicParsing -Headers $headers -TimeoutSec 35
    $guids=@($resp.InputFields | Where-Object {{ $_.type -eq 'Button' -and $_.Value -eq 'Download' }} | ForEach-Object {{ [string]$_.id }} | Where-Object {{ $_ -match '^[0-9a-fA-F-]{{36}}$' }} | Select-Object -Unique)
    $take=0
    foreach($guid in $guids) {{
      if($take -ge {MAX_RESULTS_PER_DEVICE}) {{ break }}
      $take++
      $title=''
      try {{
        $link=$resp.Links | Where-Object {{ [string]$_.id -eq ($guid + '_link') }} | Select-Object -First 1
        if($null -ne $link) {{ $title=[string]$link.InnerText }}
      }} catch {{}}
      if([string]::IsNullOrWhiteSpace($title)) {{
        try {{
          $escaped=[regex]::Escape($guid + '_link')
          $m=[regex]::Match($resp.Content, '(?is)<a[^>]+id=["'']' + $escaped + '["''][^>]*>(.*?)</a>')
          if($m.Success) {{
            $title=[System.Net.WebUtility]::HtmlDecode(([regex]::Replace($m.Groups[1].Value,'<[^>]+>',''))).Trim()
          }}
        }} catch {{}}
      }}
      if(-not [string]::IsNullOrWhiteSpace($title)) {{
        $result += [pscustomobject]@{{
          TargetKey=[string]$t.target_key
          SearchQuery=$query
          QueryKind=[string]$t.query_kind
          UpdateID=$guid
          Title=$title.Trim()
          DeviceName=[string]$t.device_name
          InstalledVersion=[string]$t.installed_version
          InstalledProvider=[string]$t.installed_provider
          InstalledInf=[string]$t.installed_inf
          DeviceID=[string]$t.device_id
          HardwareCategory=[string]$t.hardware_category
        }}
      }}
    }}
  }} catch {{
    # Una consulta individual no aborta el escaneo profundo.
  }}
}}
"""
    timeout = max(240, min(1800, 12 * len(expanded)))
    return _run_powershell_json(script, timeout=timeout)

def scan_driver_updates(installed_items: Iterable[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Escaneo profundo tipo catálogo: múltiples IDs/modelo, con validación exacta al instalar."""
    started = time.time()
    installed = [x for x in (installed_items or []) if isinstance(x, dict)]
    targets = _scan_targets(installed)
    rows, error = _catalog_search_batch(targets)

    target_map: dict[str, dict[str, Any]] = {}
    for index, target in enumerate(targets):
        key = str(target.get('device_id') or target.get('hardware_id') or f'target-{index}')
        target_map[key] = target

    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        key = str(row.get('TargetKey') or '').strip()
        if key in target_map:
            grouped.setdefault(key, []).append(row)

    updates: list[dict[str, Any]] = []
    checked = 0
    no_newer = 0
    excluded_firmware = 0
    exact_count = 0
    model_count = 0

    for key, target in target_map.items():
        checked += 1
        installed_version = str(target.get('installed_version') or '').strip()
        candidates: list[dict[str, Any]] = []
        seen_updates: set[str] = set()
        for row in grouped.get(key, []):
            uid = str(row.get('UpdateID') or '').strip()
            if not uid or uid in seen_updates:
                continue
            seen_updates.add(uid)
            title = str(row.get('Title') or '').strip()
            if not title:
                continue
            if _is_firmware_title(title):
                excluded_firmware += 1
                continue
            version = _version_from_title(title)
            if not version or not installed_version or not _is_newer(version, installed_version):
                continue
            kind = str(row.get('QueryKind') or 'HARDWARE_ID').upper()
            quality = 'EXACT_HARDWARE_ID_CATALOG' if kind == 'HARDWARE_ID' else 'COMPATIBLE_ID_CATALOG' if kind == 'COMPATIBLE_ID' else 'DEVICE_MODEL_CATALOG'
            rank = {'EXACT_HARDWARE_ID_CATALOG': 3, 'COMPATIBLE_ID_CATALOG': 2, 'DEVICE_MODEL_CATALOG': 1}.get(quality, 0)
            candidates.append({
                'update_id': uid,
                'title': title,
                'hardware_id': target.get('hardware_id'),
                'hardware_ids': list(target.get('hardware_ids') or []),
                'device_name': target.get('device_name') or title,
                'installed_version': installed_version,
                'available_version': version,
                'installed_provider': target.get('installed_provider'),
                'provider': target.get('installed_provider') or title.split(' - ', 1)[0].strip(),
                'installed_inf': target.get('installed_inf'),
                'device_id': target.get('device_id'),
                'hardware_category': target.get('hardware_category'),
                'match_quality': quality,
                'match_rank': rank,
                'search_query': row.get('SearchQuery'),
                'source': 'CorePulse Deep Driver Catalog',
                'catalog_source': 'Microsoft Update Catalog · descarga directa',
                'policy': POLICY,
            })
        if not candidates:
            no_newer += 1
            continue
        candidates.sort(key=lambda x: (int(x.get('match_rank') or 0), _version_tuple(x.get('available_version'))), reverse=True)
        best = candidates[0]
        if best.get('match_quality') == 'EXACT_HARDWARE_ID_CATALOG':
            exact_count += 1
        else:
            model_count += 1
        updates.append(best)

    updates.sort(key=lambda x: (int(target_map.get(str(x.get('device_id') or x.get('hardware_id') or ''), {}).get('hardware_priority') or 0), int(x.get('match_rank') or 0), _version_tuple(x.get('available_version'))), reverse=True)
    return {
        'updates': updates,
        'available_count': len(updates),
        'exact_match_count': exact_count,
        'compatible_or_model_count': model_count,
        'checked_device_count': checked,
        'query_count': sum(len(t.get('query_terms') or []) for t in targets),
        'no_newer_count': no_newer,
        'excluded_firmware_count': excluded_firmware,
        'error': error,
        'source': 'CorePulse Deep Driver Catalog',
        'catalog_source': 'Microsoft Update Catalog · acceso web directo',
        'policy': POLICY,
        'scanned_at': time.time(),
        'elapsed_seconds': round(time.time() - started, 2),
        'note': 'Escaneo profundo por múltiples Hardware IDs y modelo. Las coincidencias por modelo no se instalan a ciegas: el INF descargado debe contener un Hardware ID real del equipo.',
    }

def is_admin() -> bool:
    if platform.system() != 'Windows':
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _safe_filename(value: str) -> str:
    value = re.sub(r'[^A-Za-z0-9._-]+', '_', str(value or '').strip())
    return value[:120] or 'driver'


def backup_installed_driver(update: dict[str, Any]) -> dict[str, Any]:
    inf = str((update or {}).get('installed_inf') or '').strip()
    if not inf:
        return {'ok': False, 'skipped': True, 'reason': 'INF instalado no disponible', 'path': None}
    if platform.system() != 'Windows':
        return {'ok': False, 'skipped': True, 'reason': 'Windows requerido', 'path': None}
    stamp = time.strftime('%Y%m%d_%H%M%S')
    target = data_path('driver_backups', f'{stamp}_{_safe_filename(inf)}')
    target.mkdir(parents=True, exist_ok=True)
    try:
        cp = run_cancellable(
            ['pnputil.exe', '/export-driver', inf, str(target)],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=90,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            shell=False,
        )
        ok = cp.returncode == 0
        return {'ok': ok, 'skipped': False, 'reason': None if ok else (cp.stderr or cp.stdout or 'No se pudo exportar el driver.'), 'path': str(target)}
    except Exception as exc:
        logger.exception('[DRIVER_CATALOG] backup falló')
        return {'ok': False, 'skipped': False, 'reason': str(exc), 'path': str(target)}


def _download_links(update_id: str) -> tuple[list[str], str | None]:
    guid = str(update_id or '').strip()
    if not re.fullmatch(r'[0-9a-fA-F-]{36}', guid):
        return [], 'ID de catálogo inválido.'
    script = rf"""
$post=@{{size=0;updateID='{guid}';uidInfo='{guid}'}} | ConvertTo-Json -Compress
$body=@{{updateIDs="[$post]"}}
$resp=Invoke-WebRequest -Uri '{CATALOG_BASE}/DownloadDialog.aspx' -Method Post -Body $body -ContentType 'application/x-www-form-urlencoded' -UseBasicParsing -Headers @{{'User-Agent'='Mozilla/5.0 CorePulse/322'}} -TimeoutSec 60
$matches=[regex]::Matches($resp.Content, "downloadInformation\[\d+\]\.files\[\d+\]\.url\s*=\s*'([^']+)'")
$result=@()
foreach($m in $matches) {{
  $u=[System.Net.WebUtility]::HtmlDecode([string]$m.Groups[1].Value)
  if(-not [string]::IsNullOrWhiteSpace($u)) {{ $result += [pscustomobject]@{{Url=$u}} }}
}}
"""
    rows, error = _run_powershell_json(script, timeout=120)
    urls = []
    for row in rows:
        url = str(row.get('Url') or '').strip()
        if url.startswith('https://') and url not in urls:
            urls.append(url)
    return urls, error


def _download_file(url: str, target: Path) -> tuple[bool, str | None]:
    target.parent.mkdir(parents=True, exist_ok=True)
    escaped_url = str(url).replace("'", "''")
    escaped_target = str(target).replace("'", "''")
    script = rf"""
$source='{escaped_url}'
$dest='{escaped_target}'
try {{
  Import-Module BitsTransfer -ErrorAction SilentlyContinue
  if(Get-Command Start-BitsTransfer -ErrorAction SilentlyContinue) {{
    Start-BitsTransfer -Source $source -Destination $dest -DisplayName 'CorePulse Driver Download' -ErrorAction Stop
  }} else {{
    Invoke-WebRequest -Uri $source -OutFile $dest -UseBasicParsing -TimeoutSec 600 -Headers @{{'User-Agent'='Mozilla/5.0 CorePulse/322'}}
  }}
  $result=@([pscustomobject]@{{Ok=$true;Path=$dest}})
}} catch {{
  $result=@([pscustomobject]@{{Ok=$false;Error=$_.Exception.Message}})
}}
"""
    rows, error = _run_powershell_json(script, timeout=900)
    if error:
        return False, error
    row = rows[0] if rows else {}
    ok = bool(row.get('Ok')) and target.exists() and target.stat().st_size > 0
    return ok, None if ok else str(row.get('Error') or 'No se pudo descargar el paquete.')


def _extract_package(package: Path, target: Path) -> tuple[bool, str | None]:
    target.mkdir(parents=True, exist_ok=True)
    suffix = package.suffix.casefold()
    if suffix == '.cab':
        try:
            cp = run_cancellable(
                ['expand.exe', '-F:*', str(package), str(target)],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=180,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
                shell=False,
            )
            if cp.returncode == 0:
                return True, None
            return False, (cp.stderr or cp.stdout or 'No se pudo extraer el CAB.')
        except Exception as exc:
            return False, str(exc)
    return False, 'El paquete publicado no es un CAB instalable de forma segura por el motor automático.'


def _matching_infs(root: Path, hardware_ids: Iterable[str]) -> list[Path]:
    needles = []
    for hwid in hardware_ids or []:
        norm = _normalize_hwid(hwid)
        if norm:
            try:
                needles.append(norm.encode('ascii'))
            except Exception:
                pass
    matches: list[Path] = []
    if not needles:
        return matches
    for inf in root.rglob('*.inf'):
        try:
            data = inf.read_bytes().upper()
        except Exception:
            continue
        if any(needle in data for needle in needles):
            matches.append(inf)
    return matches


def _inf_driver_version(inf: Path) -> str | None:
    try:
        raw = inf.read_bytes()
        text = raw.decode('utf-16', errors='ignore') if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else raw.decode('latin-1', errors='ignore')
    except Exception:
        return None
    match = re.search(r'(?im)^\s*DriverVer\s*=\s*[^,]+,\s*([0-9.]+)\s*$', text)
    return match.group(1).strip() if match else None


def _verify_catalog_signatures(root: Path) -> tuple[bool, list[dict[str, Any]], str | None]:
    cats = list(root.rglob('*.cat'))
    if not cats:
        return False, [], 'El paquete no contiene catálogo de firma (.cat).'
    payload = base64.b64encode(json.dumps([str(x) for x in cats], ensure_ascii=False).encode('utf-8')).decode('ascii')
    script = rf"""
$raw=[System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('{payload}'))
$paths=ConvertFrom-Json $raw
$result=@()
foreach($p in @($paths)) {{
  $s=Get-AuthenticodeSignature -FilePath ([string]$p)
  $result += [pscustomobject]@{{Path=[string]$p;Status=[string]$s.Status;Signer=if($s.SignerCertificate){{$s.SignerCertificate.Subject}}else{{''}}}}
}}
"""
    rows, error = _run_powershell_json(script, timeout=120)
    if error:
        return False, rows, error
    valid = any(str(x.get('Status') or '').upper() == 'VALID' for x in rows)
    return valid, rows, None if valid else 'Windows no confirmó una firma válida para el catálogo del driver.'


def _install_inf(inf: Path) -> tuple[bool, str]:
    try:
        cp = run_cancellable(
            ['pnputil.exe', '/add-driver', str(inf), '/install'],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=240,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            shell=False,
        )
        return cp.returncode == 0, (cp.stdout or cp.stderr or '').strip()
    except Exception as exc:
        return False, str(exc)


def _package_filename(url: str, update_id: str, index: int) -> str:
    try:
        name = unquote(Path(urlparse(url).path).name)
    except Exception:
        name = ''
    if not name:
        name = f'{update_id}_{index}.cab'
    return _safe_filename(name)


def install_driver_updates(updates: Iterable[dict[str, Any]], *, create_restore_point: bool = True) -> dict[str, Any]:
    """Descarga, valida e instala paquetes directos del catálogo sin Windows Update Agent."""
    selected = [x for x in (updates or []) if isinstance(x, dict) and str(x.get('update_id') or '').strip()]
    if not selected:
        return {'ok': False, 'error': 'No hay actualizaciones seleccionadas.', 'installed': [], 'reboot_required': False}
    if platform.system() != 'Windows':
        return {'ok': False, 'error': 'Windows requerido', 'installed': [], 'reboot_required': False}
    if not is_admin():
        return {'ok': False, 'admin_required': True, 'error': 'Ejecuta CorePulse como administrador para instalar controladores.', 'installed': [], 'reboot_required': False}

    backups = [backup_installed_driver(item) for item in selected]
    restore = {'ok': False, 'skipped': True, 'error': None}
    if create_restore_point:
        try:
            from core.windows_health import create_restore_point as _create_restore_point
            restore = _create_restore_point('CorePulse - antes de actualizar drivers')
            restore['skipped'] = False
        except Exception as exc:
            logger.exception('[DRIVER_CATALOG] punto de restauración falló')
            restore = {'ok': False, 'skipped': False, 'error': str(exc)}

    session_root = data_path('driver_downloads', time.strftime('%Y%m%d_%H%M%S'))
    session_root.mkdir(parents=True, exist_ok=True)
    installed_results: list[dict[str, Any]] = []
    overall_ok = True
    reboot_required = False

    for update in selected:
        uid = str(update.get('update_id') or '').strip()
        title = str(update.get('title') or update.get('device_name') or 'Controlador').strip()
        hwids = list(update.get('hardware_ids') or []) or [str(update.get('hardware_id') or '')]
        installed_version = str(update.get('installed_version') or '').strip()
        result = {'update_id': uid, 'title': title, 'ok': False, 'stage': 'catalog', 'reboot_required': False}

        urls, err = _download_links(uid)
        if err or not urls:
            result['error'] = err or 'El catálogo no devolvió un enlace de descarga.'
            installed_results.append(result); overall_ok = False; continue

        # Los drivers del catálogo suelen ser CAB. Priorizamos CAB explícitamente.
        urls = sorted(urls, key=lambda u: (not str(u).lower().split('?', 1)[0].endswith('.cab'), len(u)))
        package = None
        download_error = None
        for idx, url in enumerate(urls[:4]):
            filename = _package_filename(url, uid, idx)
            candidate = session_root / _safe_filename(uid) / filename
            ok, derr = _download_file(url, candidate)
            if ok:
                package = candidate
                break
            download_error = derr
        if package is None:
            result['stage'] = 'download'; result['error'] = download_error or 'No se pudo descargar el paquete.'
            installed_results.append(result); overall_ok = False; continue

        extract_root = package.parent / 'extracted'
        if extract_root.exists():
            shutil.rmtree(extract_root, ignore_errors=True)
        ok, err = _extract_package(package, extract_root)
        if not ok:
            result['stage'] = 'extract'; result['error'] = err
            installed_results.append(result); overall_ok = False; continue

        sig_ok, sig_rows, sig_err = _verify_catalog_signatures(extract_root)
        result['signature'] = sig_rows
        if not sig_ok:
            result['stage'] = 'signature'; result['error'] = sig_err
            installed_results.append(result); overall_ok = False; continue

        infs = _matching_infs(extract_root, hwids)
        if not infs:
            result['stage'] = 'hardware_id'; result['error'] = 'El paquete descargado no contiene un INF que coincida con los Hardware ID reales de este dispositivo.'
            installed_results.append(result); overall_ok = False; continue

        # Seguridad adicional: el INF real debe confirmar que la versión sigue
        # siendo más nueva que la instalada antes de tocar Driver Store.
        newer_infs = []
        for inf in infs:
            ver = _inf_driver_version(inf)
            if ver and installed_version and _is_newer(ver, installed_version):
                newer_infs.append((inf, ver))
        if not newer_infs:
            result['stage'] = 'version'; result['error'] = 'El INF descargado no confirmó una versión superior a la instalada.'
            installed_results.append(result); overall_ok = False; continue

        install_logs = []
        item_ok = False
        for inf, ver in newer_infs:
            ok, output = _install_inf(inf)
            install_logs.append({'inf': str(inf), 'version': ver, 'ok': ok, 'output': output[-3000:]})
            item_ok = item_ok or ok
        result.update({'stage': 'install', 'ok': item_ok, 'package': str(package), 'install_logs': install_logs})
        if not item_ok:
            result['error'] = 'pnputil no pudo instalar un INF compatible del paquete.'
            overall_ok = False
        installed_results.append(result)

    return {
        'ok': overall_ok and bool(installed_results),
        'error': None if overall_ok else 'Una o más actualizaciones no pudieron completarse. Revisa el detalle individual.',
        'installed': installed_results,
        'reboot_required': reboot_required,
        'backups': backups,
        'restore_point': restore,
        'download_root': str(session_root),
        'source': 'CorePulse Driver Catalog · descarga directa',
        'policy': POLICY,
    }
