"""Obtiene información real de salud y confiabilidad de unidades de almacenamiento."""
from __future__ import annotations

import json
import logging
from core.windows_commands import run_powershell

logger = logging.getLogger("CorePulse.Storage")


def _safe_int(value, default=None):
    if value is None:
        return default
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def _safe_float(value, default=None):
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _normalize_value(value):
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        if value == "":
            return None
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            return value
    return value


def _run_powershell(script):
    result = run_powershell(script, timeout=15, category='STORAGE')
    if not result.ok:
        logger.warning('[STORAGE WARNING] PowerShell falló: %s', result.message())
        return None
    return result.stdout.strip()


def get_windows_storage_health():
    """Lee Get-PhysicalDisk/Get-StorageReliabilityCounter sin derivar métricas."""
    script = r"""
$ErrorActionPreference = 'SilentlyContinue'
$result = @()
$physicalDisks = Get-PhysicalDisk

foreach ($disk in $physicalDisks) {
    $counter = $null
    try {
        $counter = Get-StorageReliabilityCounter -PhysicalDisk $disk
    }
    catch {
        $counter = $null
    }

    # Algunos drivers exponen MSFT_StorageReliabilityCounter pero el cmdlet no
    # resuelve correctamente la asociación PhysicalDisk. Intentamos la clase CIM
    # directa antes de declarar Wear/temperatura como ausentes.
    if (-not $counter) {
        try {
            $diskId = [string]$disk.DeviceId
            $counter = Get-CimInstance -Namespace 'root/Microsoft/Windows/Storage' -ClassName MSFT_StorageReliabilityCounter |
                Where-Object { [string]$_.DeviceId -eq $diskId } |
                Select-Object -First 1
        }
        catch {
            $counter = $null
        }
    }

    $mounts = @()
    try {
        $diskNumber = [int]$disk.DeviceId
        $mounts = Get-Partition -DiskNumber $diskNumber |
            Where-Object { $_.DriveLetter } |
            ForEach-Object { "$($_.DriveLetter):" }
    }
    catch {
        $mounts = @()
    }

    $result += [PSCustomObject]@{
        DeviceId = $disk.DeviceId
        FriendlyName = $disk.FriendlyName
        Model = $disk.Model
        SerialNumber = $disk.SerialNumber
        FirmwareVersion = $disk.FirmwareVersion
        MountPoints = ($mounts -join ', ')
        MediaType = [string]$disk.MediaType
        BusType = [string]$disk.BusType
        OperationalStatus = [string]$disk.OperationalStatus
        HealthStatus = [string]$disk.HealthStatus
        Size = $disk.Size
        Temperature = if ($counter) { $counter.Temperature } else { $null }
        TemperatureMax = if ($counter) { $counter.TemperatureMax } else { $null }
        Wear = if ($counter) { $counter.Wear } else { $null }
        PowerOnHours = if ($counter) { $counter.PowerOnHours } else { $null }
        ReadErrorsCorrected = if ($counter) { $counter.ReadErrorsCorrected } else { $null }
        ReadErrorsTotal = if ($counter) { $counter.ReadErrorsTotal } else { $null }
        ReadErrorsUncorrected = if ($counter) { $counter.ReadErrorsUncorrected } else { $null }
        WriteErrorsCorrected = if ($counter) { $counter.WriteErrorsCorrected } else { $null }
        WriteErrorsTotal = if ($counter) { $counter.WriteErrorsTotal } else { $null }
        WriteErrorsUncorrected = if ($counter) { $counter.WriteErrorsUncorrected } else { $null }
        StartStopCycleCount = if ($counter) { $counter.StartStopCycleCount } else { $null }
        LoadUnloadCycleCount = if ($counter) { $counter.LoadUnloadCycleCount } else { $null }
        FlushLatencyMax = if ($counter) { $counter.FlushLatencyMax } else { $null }
        ReadLatencyMax = if ($counter) { $counter.ReadLatencyMax } else { $null }
        WriteLatencyMax = if ($counter) { $counter.WriteLatencyMax } else { $null }
        ReliabilityCounterAvailable = [bool]$counter
        ReliabilityEvidenceFields = if ($counter) {
            @('Temperature','TemperatureMax','Wear','PowerOnHours','ReadErrorsCorrected','ReadErrorsTotal','ReadErrorsUncorrected','WriteErrorsCorrected','WriteErrorsTotal','WriteErrorsUncorrected','StartStopCycleCount','LoadUnloadCycleCount','FlushLatencyMax','ReadLatencyMax','WriteLatencyMax') |
                Where-Object { $null -ne $counter.$_ } |
                ForEach-Object { $_ }
        } else { @() }
        ReliabilityCounterLive = if ($counter) {
            $evidence = @()
            foreach ($name in @('PowerOnHours','ReadErrorsCorrected','ReadErrorsTotal','ReadErrorsUncorrected','WriteErrorsCorrected','WriteErrorsTotal','WriteErrorsUncorrected','StartStopCycleCount','LoadUnloadCycleCount','FlushLatencyMax','ReadLatencyMax','WriteLatencyMax')) {
                $value = $counter.$name
                if ($null -ne $value) {
                    try {
                        if ([double]$value -gt 0) { $evidence += $name }
                    } catch { }
                }
            }
            # Wear=0 por sí solo puede ser ambiguo en miniports incompletos.
            # Latencias reales de E/S, horas/ciclos o contadores de error no cero
            # demuestran que MSFT_StorageReliabilityCounter está activo y no es
            # un objeto placeholder. En ese caso Wear=0 sí es evidencia
            # cuantitativa válida de 0% de desgaste reportado por Windows.
            [bool]($evidence.Count -gt 0)
        } else { $false }
    }
}

$result | ConvertTo-Json -Depth 5 -Compress
"""
    output = _run_powershell(script)
    if not output:
        return []
    try:
        data = json.loads(output)
    except json.JSONDecodeError as exc:
        logger.error("[STORAGE ERROR] No se pudo interpretar PowerShell: %s", exc)
        return []

    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        return []

    return [
        {key: _normalize_value(value) for key, value in item.items()}
        for item in data
        if isinstance(item, dict)
    ]


def _status_is_healthy(data):
    raw = str(data.get("HealthStatus") or data.get("health_status") or "").strip().casefold()
    op = str(data.get("OperationalStatus") or data.get("operational_status") or "").strip().casefold()
    return raw in {"healthy", "ok", "normal"} or op in {"healthy", "ok", "normal"}


def _reliability_counter_live(data):
    value = data.get("ReliabilityCounterLive")
    if value is None:
        value = data.get("reliability_counter_live")
    if isinstance(value, str):
        return value.strip().casefold() in {"true", "1", "yes"}
    return bool(value)


def calculate_storage_health(data):
    """Deriva vida restante sólo desde desgaste cuantitativo corroborado.

    ``Wear`` de ``MSFT_StorageReliabilityCounter`` representa porcentaje de
    desgaste. Algunos controladores devuelven 0 incluso cuando no implementan
    realmente el contador; por eso un 0 sólo se acepta si el mismo proveedor
    entrega además evidencia operacional real (latencias de E/S, horas, ciclos
    o errores) y Windows reporta el disco sano. Un Wear positivo es evidencia cuantitativa
    por sí mismo y se convierte en ``100 - Wear``.
    """
    wear = _safe_float(data.get("Wear") if "Wear" in data else data.get("wear"))
    if wear is None or wear < 0:
        return None
    if wear > 0:
        return max(0.0, min(100.0, 100.0 - wear))
    if wear == 0 and _reliability_counter_live(data) and _status_is_healthy(data):
        return 100.0
    return None


def normalize_storage_data(raw_disks):
    normalized = []
    for index, disk in enumerate(raw_disks, start=1):
        if not isinstance(disk, dict):
            continue
        size = _safe_int(disk.get("Size"))
        normalized.append({
            "index": index,
            "device_id": disk.get("DeviceId"),
            "model": disk.get("Model") or disk.get("FriendlyName") or "Unidad de almacenamiento",
            "friendly_name": disk.get("FriendlyName"),
            "serial": disk.get("SerialNumber"),
            "firmware_version": disk.get("FirmwareVersion"),
            "mount_points": disk.get("MountPoints"),
            "media_type": disk.get("MediaType"),
            "bus_type": disk.get("BusType"),
            "operational_status": disk.get("OperationalStatus"),
            "health_status": disk.get("HealthStatus"),
            "health": calculate_storage_health(disk),
            "health_source": (
                "Windows Storage Reliability Wear · vida restante 100 - desgaste"
                if calculate_storage_health(disk) is not None else None
            ),
            "health_derived": calculate_storage_health(disk) is not None,
            "reliability_counter_available": bool(disk.get("ReliabilityCounterAvailable")),
            "reliability_counter_live": bool(disk.get("ReliabilityCounterLive")),
            "reliability_evidence_fields": disk.get("ReliabilityEvidenceFields") or [],
            "temperature": _safe_float(disk.get("Temperature")),
            "temperature_max": _safe_float(disk.get("TemperatureMax")),
            "wear": _safe_float(disk.get("Wear")),
            "power_on_hours": _safe_int(disk.get("PowerOnHours")),
            "read_errors_corrected": _safe_int(disk.get("ReadErrorsCorrected")),
            "read_errors_total": _safe_int(disk.get("ReadErrorsTotal")),
            "read_errors_uncorrected": _safe_int(disk.get("ReadErrorsUncorrected")),
            "write_errors_corrected": _safe_int(disk.get("WriteErrorsCorrected")),
            "write_errors_total": _safe_int(disk.get("WriteErrorsTotal")),
            "write_errors_uncorrected": _safe_int(disk.get("WriteErrorsUncorrected")),
            "start_stop_cycles": _safe_int(disk.get("StartStopCycleCount")),
            "load_unload_cycles": _safe_int(disk.get("LoadUnloadCycleCount")),
            "flush_latency_max_ms": _safe_float(disk.get("FlushLatencyMax")),
            "read_latency_max_ms": _safe_float(disk.get("ReadLatencyMax")),
            "write_latency_max_ms": _safe_float(disk.get("WriteLatencyMax")),
            "used_gb": None,
            "total_gb": round(size / 1024 ** 3, 1) if size is not None else None,
            "used_percent": None,
            "source": "Windows Storage Reliability",
            "policy": "REAL_OR_NA",
        })
    return normalized


def get_storage_health():
    """Obtiene confiabilidad nativa de Windows sin rellenar campos no expuestos."""
    raw = get_windows_storage_health()
    if not raw:
        logger.warning("[STORAGE WARNING] No se obtuvieron datos de confiabilidad.")
        return []

    normalized = normalize_storage_data(raw)
    logger.info("[STORAGE INFO] Se detectaron %s unidades.", len(normalized))
    return normalized


if __name__ == "__main__":
    print("=" * 70)
    print("COREPULSE - STORAGE HEALTH TEST")
    print("=" * 70)
    print(json.dumps(get_storage_health(), indent=2, ensure_ascii=False))


# V482: fusión sin cambios de lógica desde core/storage/storage_summary_health.py
import copy
import json
import time
from typing import Any, Dict, Optional

from core.storage_details import match_reliability_record, resolve_physical_disk_index
from core.smartctl_storage import query_nvme_health_log
from core.smartctl_storage import query_smartctl_health, merge_health_sources
from core.runtime_paths import cache_path

_CACHE_FILE = cache_path('storage_summary_health.json')
_CACHE_MAX_AGE_SECONDS = 24 * 60 * 60


# V484: implementacion numerica unica, identica y reutilizada por SMART.
from core.smartctl_storage import _num


def _clamp_pct(value: Any) -> Optional[float]:
    number = _num(value)
    if number is None:
        return None
    return max(0.0, min(100.0, number))


def _remaining_from_wear(value: Any) -> Optional[float]:
    wear = _num(value)
    if wear is None or wear < 0:
        return None
    return max(0.0, min(100.0, 100.0 - wear))


def _valid_temperature(value: Any) -> Optional[float]:
    """Acepta sólo una temperatura física utilizable.

    Varios drivers/OEM rellenan sensores no soportados con 0. CorePulse no debe
    convertir ese sentinel en una lectura real de 0 °C.
    """
    temp = _num(value)
    if temp is None or temp <= 0.0 or temp > 200.0:
        return None
    return temp


def _status_label(value: Any) -> str:
    raw = str(value or '').strip()
    low = raw.casefold()
    if not raw:
        return ''
    if low in {'healthy', 'ok', 'normal'}:
        return 'Saludable'
    if 'warning' in low or 'warn' in low:
        return 'Advertencia'
    if 'unhealthy' in low or 'critical' in low or 'failed' in low:
        return 'Crítico'
    return raw


def _device_at(telemetry: Dict[str, Any], index: int) -> Dict[str, Any]:
    devices = telemetry.get('_storage_devices') if isinstance(telemetry, dict) else None
    if not isinstance(devices, list) or index < 0 or index >= len(devices):
        return {}
    item = devices[index]
    return dict(item) if isinstance(item, dict) else {}


def collect_storage_summary_health(telemetry: Dict[str, Any], *, include_slow_fallbacks: bool = True) -> Dict[int, Dict[str, Any]]:
    """Devuelve salud por disco físico usando primero APIs nativas de Windows.

    Autoridad cuantitativa:
    1) NVMe Health Log vía IOCTL de Windows (Percentage Used);
    2) Storage Reliability Counter (Wear);
    3) Life/Health real publicado por LibreHardwareMonitor;
    4) smartctl sólo como último fallback opcional.

    Nunca convierte ``Healthy``/``SMART PASSED`` en 100%.
    """
    tele = copy.deepcopy(telemetry) if isinstance(telemetry, dict) else {}
    devices = tele.get('_storage_inventory') if isinstance(tele.get('_storage_inventory'), list) else None
    if not isinstance(devices, list):
        devices = tele.get('_storage_devices') if isinstance(tele.get('_storage_devices'), list) else []
    # La lectura NVMe nativa es rápida. Storage Reliability/PowerShell se reserva
    # para el enriquecimiento posterior, para que el Resumen no espere decenas de segundos.
    records = (get_storage_health() or []) if include_slow_fallbacks else []
    out: Dict[int, Dict[str, Any]] = {}

    for index, device in enumerate(devices):
        if not isinstance(device, dict):
            continue
        os_inv = device.get('os_inventory') if isinstance(device.get('os_inventory'), dict) else {}
        record = match_reliability_record(device, records) or {}
        physical_index = resolve_physical_disk_index(index, tele)
        # V258 merge: si LHM no publicó el Win32_DiskDrive.Index, reutiliza el
        # DeviceId/DiskNumber del registro Windows ya emparejado por serial/modelo.
        # Esto permite consultar el NVMe Health Log nativo sin depender de que el
        # proveedor de sensores entregue también la identidad física del disco.
        if physical_index is None and record:
            try:
                candidate = record.get('device_id')
                physical_index = int(candidate) if candidate is not None else None
            except (TypeError, ValueError):
                physical_index = None

        try:
            nvme_native = query_nvme_health_log(physical_index) if physical_index is not None else {}
        except Exception:
            nvme_native = {}

        status = _status_label(
            record.get('health_status') or record.get('operational_status')
            or os_inv.get('health_status_os') or os_inv.get('operational_status_os')
        )
        native_used = _num(nvme_native.get('percentage_used'))
        native_remaining = _remaining_from_wear(native_used)
        windows_wear = _num(record.get('wear'))
        windows_health = _clamp_pct(record.get('health'))
        direct_health = _clamp_pct(device.get('life_percent'))
        windows_health_source = str(record.get('health_source') or '').strip()

        smartctl = {}
        smart_used = None
        smart_remaining = None
        # smartctl se reserva para el final. Sólo se ejecuta si las fuentes
        # nativas/embebidas no entregaron un porcentaje cuantitativo.
        if include_slow_fallbacks and native_remaining is None and windows_health is None and not (windows_wear is not None and windows_wear > 0) and not (direct_health is not None and direct_health > 0):
            try:
                smartctl = query_smartctl_health(physical_index) if physical_index is not None else {}
            except Exception:
                smartctl = {}
            smart_used = _num(smartctl.get('percentage_used'))
            smart_remaining = _remaining_from_wear(smart_used)

        if native_remaining is not None:
            health = native_remaining
            health_label = f'Salud  {health:.0f}%'
            health_source = 'Windows NVMe Health Log · 100 - Percentage Used'
            derived = True
            wear = native_used
            wear_source = 'Windows NVMe Health Log / Percentage Used'
        elif windows_health is not None:
            health = windows_health
            health_label = f'Salud  {health:.0f}%'
            health_source = windows_health_source or 'Windows Storage Reliability · 100 - Wear'
            derived = True
            wear = windows_wear
            wear_source = record.get('reliability_counter_path') or 'Windows Storage Reliability / Wear'
        elif windows_wear is not None and windows_wear > 0.0:
            health = _remaining_from_wear(windows_wear)
            health_label = f'Salud  {health:.0f}%'
            health_source = record.get('reliability_counter_path') or 'Windows Storage Reliability · 100 - Wear'
            derived = True
            wear = windows_wear
            wear_source = record.get('reliability_counter_path') or 'Windows Storage Reliability / Wear'
        elif direct_health is not None and direct_health > 0.0:
            health = direct_health
            health_label = f'Salud  {health:.0f}%'
            health_source = 'LibreHardwareMonitor Life/Health'
            derived = False
            wear = None
            wear_source = None
        elif smart_remaining is not None:
            health = smart_remaining
            health_label = f'Salud  {health:.0f}%'
            health_source = 'smartctl NVMe Percentage Used · fallback'
            derived = True
            wear = smart_used
            wear_source = 'smartctl / Percentage Used'
        elif direct_health == 0.0 and status in {'Crítico', 'Advertencia'}:
            health = 0.0
            health_label = 'Salud  0%'
            health_source = 'LibreHardwareMonitor Life/Health · corroborado por Windows'
            derived = False
            wear = None
            wear_source = None
        else:
            health = None
            health_label = f'Estado  {status}' if status else 'Salud  N/A'
            health_source = 'Windows Storage HealthStatus' if status else 'N/A'
            derived = False
            wear = windows_wear if windows_wear is not None else smart_used
            wear_source = None

        temp = _valid_temperature(nvme_native.get('temperature_c'))
        temp_source = 'Windows NVMe Health Log' if temp is not None else None
        if temp is None:
            temp = _valid_temperature(record.get('temperature'))
            if temp is not None:
                temp_source = 'Windows Storage Reliability'
        if temp is None:
            temp = _valid_temperature(device.get('temperature_c'))
            if temp is not None:
                temp_source = 'LibreHardwareMonitor'
        if temp is None and smartctl:
            temp = _valid_temperature(smartctl.get('temperature_c'))
            if temp is not None:
                temp_source = 'smartctl fallback'

        size_bytes = _num(os_inv.get('size_bytes_os'))
        total_gb = _num(record.get('total_gb'))
        if total_gb is None and size_bytes is not None and size_bytes > 0:
            total_gb = size_bytes / (1024 ** 3)
        if total_gb is None:
            total_gb = _num(device.get('total_space_gb'))

        mounts = (
            str(os_inv.get('mount_points') or '').strip()
            or str(record.get('mount_points') or '').strip()
            or str(device.get('mount_points') or '').strip()
            or None
        )
        volume_total = _num(os_inv.get('volume_total_gb'))
        if volume_total is None:
            volume_total = _num(record.get('volume_total_gb'))
        used_gb = _num(os_inv.get('used_space_gb'))
        if used_gb is None:
            used_gb = _num(record.get('used_gb'))
        free_gb = _num(os_inv.get('free_space_gb'))
        if free_gb is None:
            free_gb = _num(record.get('free_gb'))
        used_percent = _num(os_inv.get('used_space_percent'))
        if used_percent is None:
            used_percent = _num(record.get('used_percent'))
        if used_percent is None and volume_total and used_gb is not None:
            used_percent = (used_gb / volume_total) * 100.0

        out[index] = {
            'index': index,
            'physical_disk_index': physical_index,
            'model': device.get('model') or device.get('name') or os_inv.get('model'),
            'health': health,
            'health_label': health_label,
            'health_source': health_source,
            'health_derived': derived,
            'windows_health_status': status or None,
            'wear_percent': wear,
            'wear_source': wear_source,
            'wear_quantitative_reliable': bool(health is not None and (native_remaining is not None or windows_health is not None or (windows_wear is not None and windows_wear > 0) or direct_health not in (None, 0.0) or smart_remaining is not None)),
            'temperature_c': temp,
            'temperature_source': temp_source,
            'total_gb': total_gb,
            'volume_total_gb': volume_total,
            'used_gb': used_gb,
            'free_gb': free_gb,
            'used_percent': used_percent,
            'volume_count': int(_num(os_inv.get('volume_count')) or _num(record.get('volume_count')) or 0),
            'mount_points': mounts,
            'system_disk': bool(os_inv.get('system_disk')),
            'nvme_smart_available': bool(nvme_native),
            'smartctl_available': bool(smartctl),
            'smartctl_source': smartctl.get('source') if isinstance(smartctl, dict) else None,
            'nvme_query_scope': nvme_native.get('query_scope') if isinstance(nvme_native, dict) else None,
            'nvme_percentage_used': native_used,
            'reliability_available': bool(record),
            'reliability_counter_path': record.get('reliability_counter_path'),
        }
    return out


def save_storage_summary_health_cache(result: Dict[int, Dict[str, Any]]) -> bool:
    """Persiste sólo evidencia ya obtenida para sobrevivir reinicios de tema/UI."""
    if not isinstance(result, dict) or not result:
        return False
    usable = {}
    for key, value in result.items():
        if not isinstance(value, dict):
            continue
        if value.get('health') is None and value.get('used_gb') is None and value.get('mount_points') in (None, '', 'N/A'):
            continue
        usable[str(key)] = dict(value)
    if not usable:
        return False
    payload = {'saved_at': time.time(), 'disks': usable}
    try:
        _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        temp = _CACHE_FILE.with_suffix('.tmp')
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        temp.replace(_CACHE_FILE)
        return True
    except Exception:
        return False


def load_storage_summary_health_cache(max_age_seconds: float = _CACHE_MAX_AGE_SECONDS) -> Dict[int, Dict[str, Any]]:
    """Restaura evidencia reciente; nunca genera ni recalcula porcentajes."""
    try:
        raw = json.loads(_CACHE_FILE.read_text(encoding='utf-8'))
        saved_at = float(raw.get('saved_at') or 0.0)
        if saved_at <= 0 or time.time() - saved_at > float(max_age_seconds):
            return {}
        disks = raw.get('disks')
        if not isinstance(disks, dict):
            return {}
        result = {}
        for key, value in disks.items():
            if not isinstance(value, dict):
                continue
            try:
                idx = int(key)
            except (TypeError, ValueError):
                continue
            item = dict(value)
            item['cache_restored'] = True
            item['cache_saved_at'] = saved_at
            result[idx] = item
        return result
    except Exception:
        return {}


__all__ = ['collect_storage_summary_health', 'save_storage_summary_health_cache', 'load_storage_summary_health_cache']
