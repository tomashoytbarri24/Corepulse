"""Telemetría REAL de CorePulse REBUILD: solo lecturas comprobadas o N/A.

Fuentes: psutil (CPU/RAM/disco), PDH de Windows (% rendimiento del CPU),
LibreHardwareMonitor/OpenHardwareMonitor (sensores CPU si están activos),
NVIDIA-SMI (uso y temperatura de GPU NVIDIA) y Storage de Windows (modelo físico).
Las sondas externas se realizan en trabajadores para no bloquear Qt.
"""
from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import statistics
import subprocess
import sys
import time

import psutil
from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot


def percentage(value):
    """Porcentajes numéricos reales, rango [0, 100], nunca booleanos/NaN."""
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return round(number, 1) if math.isfinite(number) and 0 <= number <= 100 else None


def positive_number(value, minimum=0, maximum=None):
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) and number > minimum and (maximum is None or number <= maximum) else None


def ram_reading(memory):
    """Coherencia: uso, porcentaje y capacidad sobre la MISMA base disponible.

    Windows 'Available' incluye libre y caché reutilizable. No confundir
    RAM comprometida/caché con RAM físicamente en uso.
    """
    total = positive_number(getattr(memory, "total", None))
    available = getattr(memory, "available", None)
    if total is None:
        return None, None, None
    try:
        available = float(available)
    except (TypeError, ValueError, OverflowError):
        return None, None, round(total / 1024**3, 1)
    if not math.isfinite(available) or available < 0 or available > total:
        return None, None, round(total / 1024**3, 1)
    used = total - available
    return percentage(100 * used / total), round(used / 1024**3, 1), round(total / 1024**3, 1)


def estimated_cpu_ghz(base_mhz, performance_percent):
    """Estimación OS: frecuencia nominal * rendimiento respecto de frecuencia nominal.

    % Processor Performance es un contador de Windows que incluye turbo (>100%).
    NO es un sensor de reloj físico: siempre se presenta como *estimado*.
    Evita confundir el contador Processor Frequency, frecuentemente fijo en base MHz,
    con el reloj dinámico del CPU. Sin ambas magnitudes confiables: N/A.
    """
    base = positive_number(base_mhz, minimum=100, maximum=12_000)
    perf = positive_number(performance_percent, minimum=0, maximum=400)
    if base is None or perf is None:
        return None
    mhz = positive_number(base * perf / 100, minimum=100, maximum=12_000)
    return round(mhz / 1000, 2) if mhz is not None else None


def cpu_name() -> str:
    if os.name == "nt":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
                value, _ = winreg.QueryValueEx(key, "ProcessorNameString")
                if isinstance(value, str) and value.strip():
                    return " ".join(value.split())
        except (OSError, ImportError, ValueError):
            pass
    return (platform.processor() or "").strip() or "N/A"


def machine_model() -> str:
    if os.name == "nt":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                r"HARDWARE\DESCRIPTION\System\BIOS") as key:
                vendor, _ = winreg.QueryValueEx(key, "SystemManufacturer")
                model, _ = winreg.QueryValueEx(key, "SystemProductName")
                name = " ".join(str(vendor).split()) + " " + " ".join(str(model).split())
                if name.strip():
                    return name.strip()
        except (OSError, ImportError, ValueError):
            pass
    return platform.node() or "N/A"


def system_disk() -> str:
    if os.name == "nt":
        return os.environ.get("SystemDrive", "C:") + "\\"
    return str(Path.home().anchor or "/")


def format_uptime(seconds: float | None) -> str:
    if seconds is None or not math.isfinite(seconds) or seconds < 0:
        return "N/A"
    total = int(seconds)
    hours, remainder = divmod(total, 3600)
    mins, secs = divmod(remainder, 60)
    return f"{hours:02d}:{mins:02d}:{secs:02d}"


def parse_nvidia_csv(content: str) -> dict:
    """Una GPU y sus propios campos: no mezcla uso de un adaptador con otro."""
    empty = {"name": "N/A", "usage": None, "temp": None,
             "vramUsed": None, "vramTotal": None}
    if not isinstance(content, str):
        return empty
    for line in content.splitlines():
        fields = [field.strip() for field in line.split(",")]
        if len(fields) < 3 or not fields[0]:
            continue
        temperature = positive_number(fields[2], minimum=0, maximum=125)
        # NVIDIA-SMI entrega memoria.used y memory.total en MiB, si están soportados.
        # Evitar considerar memoria inexistente, negativa o superior al total como real.
        try:
            used = float(fields[3]) if len(fields) >= 5 else None
            total = float(fields[4]) if len(fields) >= 5 else None
            if (used is None or total is None or not math.isfinite(used)
                    or not math.isfinite(total) or used < 0 or total <= 0 or used > total):
                used, total = None, None
        except (TypeError, ValueError, OverflowError):
            used, total = None, None
        return {"name": fields[0], "usage": percentage(fields[1]),
                "temp": round(temperature, 1) if temperature is not None else None,
                "vramUsed": round(used / 1024, 2) if used is not None else None,
                "vramTotal": round(total / 1024, 2) if total is not None else None}
    return empty


def query_nvidia() -> dict:
    """NVML vía nvidia-smi: uso del núcleo NVIDIA, no agregado GPU Engine de Task Manager."""
    executable = shutil.which("nvidia-smi")
    if not executable and os.name == "nt":
        installed = Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "NVIDIA Corporation" / "NVSMI" / "nvidia-smi.exe"
        executable = str(installed) if installed.is_file() else None
    if not executable:
        return parse_nvidia_csv("")
    try:
        result = subprocess.run(
            [executable, "--query-gpu=name,utilization.gpu,temperature.gpu,memory.used,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=2.5, check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return parse_nvidia_csv(result.stdout) if result.returncode == 0 else parse_nvidia_csv("")
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return parse_nvidia_csv("")


def parse_cpu_sensors(items):
    """Sensores CPU confirmados; descarta 0 °C, valores inválidos y sensores de GPU.

    Prioriza CPU Package / Tctl-Tdie; usa núcleos reales como respaldo.
    Si hay varios núcleos válidos, utiliza el mayor para no ocultar puntos calientes.
    """
    if isinstance(items, dict):
        items = [items]
    if not isinstance(items, list):
        return {"temp": None, "ghz": None}
    temps = []
    clocks = []
    for item in items:
        if not isinstance(item, dict):
            continue
        ident = str(item.get("Identifier") or "").lower()
        name = str(item.get("Name") or "").lower()
        sensor_type = str(item.get("SensorType") or "").lower()
        # Identificadores propios de los proveedores de CPU (no GPU ni placa base).
        if not re.search(r"/(intelcpu|amdcpu|cpu)/", ident):
            continue
        if sensor_type == "temperature":
            # Distancia a TjMax NO es temperatura del procesador.
            if "distance" in name or "tjmax" in name:
                continue
            value = positive_number(item.get("Value"), minimum=0, maximum=115)
            if value is None:
                continue
            if "package" in name or "tctl" in name or "tdie" in name:
                priority = 0
            elif "core" in name or "ccd" in name:
                priority = 1
            elif "cpu" in name:
                priority = 2
            else:
                priority = 3
            temps.append((priority, value))
        elif sensor_type == "clock":
            if any(word in name for word in ("bus", "base", "ring", "uncore", "cache")):
                continue
            value = positive_number(item.get("Value"), minimum=100, maximum=12_000)
            if value is not None:
                clocks.append(value)
    temperature = None
    if temps:
        best = min(priority for priority, _ in temps)
        temperature = round(max(value for priority, value in temps if priority == best), 1)
    return {"temp": temperature,
            "ghz": round(statistics.median(clocks) / 1000, 2) if clocks else None}


def parse_cpu_extra_sensors(items):
    """Datos opcionales medidos, sin confundir CPU con GPU/SSD o sensores de placa.

    Las temperaturas por núcleo y la potencia son siempre lecturas observadas;
    nunca se calculan ni se crean filas ficticias.
    """
    if isinstance(items, dict):
        items = [items]
    if not isinstance(items, list):
        return {"power": None, "coreTemps": []}
    power_samples = []
    core_rows = []
    names_seen = set()
    for sensor in items:
        if not isinstance(sensor, dict):
            continue
        ident = str(sensor.get("Identifier") or "").lower()
        if not re.search(r"/(intelcpu|amdcpu|cpu)/", ident):
            continue
        name = " ".join(str(sensor.get("Name") or "").split())[:75]
        lower = name.casefold()
        typ = str(sensor.get("SensorType") or "").casefold()
        if any(bad in lower for bad in ("gpu", "ssd", "nvme", "vrm", "distance", "tjmax")):
            continue
        if typ == "power" and ("package" in lower or "cpu" in lower):
            power = positive_number(sensor.get("Value"), minimum=0, maximum=1200)
            if power is not None:
                rank = 0 if "package" in lower else 1
                power_samples.append((rank, power))
        if typ == "temperature" and ("core" in lower or "ccd" in lower):
            temp = positive_number(sensor.get("Value"), minimum=4.99, maximum=115)
            if temp is not None and lower not in names_seen and len(core_rows) < 32:
                names_seen.add(lower)
                core_rows.append({"name": name, "value": round(temp, 1)})
    cpu_power = None
    if power_samples:
        best_rank = min(rank for rank, _ in power_samples)
        cpu_power = round(max(value for rank, value in power_samples if rank == best_rank), 1)
    return {"power": cpu_power, "coreTemps": core_rows}


def disk_display_name(raw):
    """Limpia un nombre publicado por Get-Disk, sin suponer la marca ni el medio."""
    if not isinstance(raw, str):
        return None
    value = " ".join(raw.split())
    if not value or value.lower() in ("n/a", "unknown", "null", "none"):
        return None
    return value[:110]


def query_windows_hardware(drive: str, include_disk: bool) -> dict:
    """Consulta opcional y SOLO LECTURA mediante PowerShell fuera del hilo Qt.

    No instala drivers ni arranca servicios. Solo funciona si LHM/OHM expone
    los sensores CPU en WMI. Un equipo sin monitor de sensores devuelve N/A.
    """
    empty = {"temp": None, "ghz": None, "disk": None, "baseMHz": None,
             "power": None, "coreTemps": [], "detailSource": "N/A"}
    if os.name != "nt":
        return empty
    exe = shutil.which("powershell.exe") or shutil.which("powershell")
    if not exe:
        return empty
    letter = drive[:1].upper()
    if not (len(letter) == 1 and "A" <= letter <= "Z"):
        return empty
    script = r'''
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$sensors = @()
foreach ($ns in @('root\LibreHardwareMonitor','root\OpenHardwareMonitor')) {
  try {
    $sensors = @(Get-CimInstance -Namespace $ns -ClassName Sensor -ErrorAction Stop |
      Where-Object { $_.SensorType -in @('Temperature','Clock','Power') -and $_.Identifier -match '(?i)/(intelcpu|amdcpu|cpu)/' } |
      Select-Object Name, Identifier, SensorType, Value)
    if ($sensors.Count -gt 0) { break }
  } catch { }
}
# Nominal (MaxClockSpeed), NO velocidad instantánea ni Turbo Boost.
$baseMHz = $null
try {
  $baseMHz = Get-CimInstance Win32_Processor -ErrorAction Stop |
    Select-Object -First 1 -ExpandProperty MaxClockSpeed
} catch { }
$diskName = $null
if (WANT_DISK) {
  try {
    $diskName = Get-Partition -DriveLetter 'DRIVE_LETTER' -ErrorAction Stop |
      Get-Disk -ErrorAction Stop | Select-Object -First 1 -ExpandProperty FriendlyName
  } catch { }
}
@{ sensors = @($sensors); disk = $diskName; baseMHz = $baseMHz } | ConvertTo-Json -Depth 4 -Compress
'''.replace("WANT_DISK", "$true" if include_disk else "$false").replace("DRIVE_LETTER", letter)
    try:
        result = subprocess.run(
            [exe, "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=6.0, check=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode != 0 or not result.stdout.strip():
            return empty
        raw = json.loads(result.stdout.lstrip("\ufeff"))
        if not isinstance(raw, dict):
            return empty
        cpu = parse_cpu_sensors(raw.get("sensors"))
        extra = parse_cpu_extra_sensors(raw.get("sensors"))
        return {"temp": cpu["temp"], "ghz": cpu["ghz"],
                "disk": disk_display_name(raw.get("disk")),
                "baseMHz": positive_number(raw.get("baseMHz"), minimum=100, maximum=12_000),
                "power": extra["power"], "coreTemps": extra["coreTemps"],
                "detailSource": "LibreHardwareMonitor/OpenHardwareMonitor (WMI)"
                  if extra["power"] is not None or extra["coreTemps"] else "N/A"}
    except (OSError, ValueError, subprocess.TimeoutExpired, UnicodeError):
        return empty


def parse_component_inventory(payload):
    """Inventario Windows/SMBIOS de SOLO LECTURA; sin campos presumidos.

    Un adaptador gráfico integrado no se etiqueta como la GPU NVIDIA medida.
    Los módulos de RAM se mantienen individuales, sin sumar capacidades
    desalineadas a la memoria utilizable que informa psutil.
    """
    empty = {"cpuManufacturer": "N/A", "cpuSocket": "N/A",
             "cpuPhysicalCores": None, "cpuLogicalThreads": None,
             "ramModules": [], "gpuAdapters": []}
    if not isinstance(payload, dict):
        return empty

    def clean(v, size=110):
        if not isinstance(v, str):
            return "N/A"
        t = " ".join(v.strip().split())[:size]
        return t if t and t.casefold() not in ("unknown", "null", "none", "n/a", "to be filled by o.e.m.") else "N/A"

    def count(v, limit=512):
        n = positive_number(v, minimum=0, maximum=limit)
        return int(n) if n is not None and float(n).is_integer() else None

    cpu = payload.get("cpu") or {}
    if isinstance(cpu, list):
        cpu = cpu[0] if cpu else {}
    if isinstance(cpu, dict):
        empty["cpuManufacturer"] = clean(cpu.get("Manufacturer"))
        empty["cpuSocket"] = clean(cpu.get("SocketDesignation"))
        empty["cpuPhysicalCores"] = count(cpu.get("NumberOfCores"))
        empty["cpuLogicalThreads"] = count(cpu.get("NumberOfLogicalProcessors"))

    modules = payload.get("memory") or []
    if isinstance(modules, dict):
        modules = [modules]
    if isinstance(modules, list):
        for slot in modules[:32]:
            if not isinstance(slot, dict):
                continue
            cap = positive_number(slot.get("Capacity"), maximum=2**50)
            speed = count(slot.get("ConfiguredClockSpeed") or slot.get("Speed"), limit=100_000)
            typ = count(slot.get("SMBIOSMemoryType"), limit=255)
            typ = {20:"DDR", 21:"DDR2", 24:"DDR3", 26:"DDR4", 34:"DDR5"}.get(typ, "N/A")
            empty["ramModules"].append({
                "slot": clean(slot.get("DeviceLocator"), 60),
                "manufacturer": clean(slot.get("Manufacturer"), 65),
                "partNumber": clean(slot.get("PartNumber"), 85),
                "capacityGB": round(cap / 1024**3, 1) if cap is not None else None,
                "speedMHz": speed, "type": typ,
            })

    adapters = payload.get("video") or []
    if isinstance(adapters, dict):
        adapters = [adapters]
    if isinstance(adapters, list):
        for card in adapters[:16]:
            if not isinstance(card, dict):
                continue
            name = clean(card.get("Name"))
            if name == "N/A":
                continue
            empty["gpuAdapters"].append({
                "name": name,
                "driver": clean(card.get("DriverVersion"), 60),
            })
    return empty


def query_windows_component_inventory():
    """CIM una sola vez en segundo plano: CPU, DIMM y adaptadores gráficos.

    No lee ni guarda datos personales, no necesita privilegios ni cambia Windows.
    """
    defaults = parse_component_inventory({})
    if os.name != "nt":
        return defaults
    exe = shutil.which("powershell.exe") or shutil.which("powershell")
    if not exe:
        return defaults
    script = r"""
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$cpu = @(); $memory = @(); $video = @()
try { $cpu = @(Get-CimInstance Win32_Processor -ErrorAction Stop | Select-Object -First 1 Manufacturer, SocketDesignation, NumberOfCores, NumberOfLogicalProcessors) } catch { }
try { $memory = @(Get-CimInstance Win32_PhysicalMemory -ErrorAction Stop | Select-Object Capacity, ConfiguredClockSpeed, Speed, SMBIOSMemoryType, DeviceLocator, Manufacturer, PartNumber) } catch { }
try { $video = @(Get-CimInstance Win32_VideoController -ErrorAction Stop | Select-Object Name, DriverVersion) } catch { }
@{ cpu = @($cpu); memory = @($memory); video = @($video) } | ConvertTo-Json -Depth 4 -Compress
"""
    try:
        result = subprocess.run(
            [exe, "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=9.0, check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode != 0 or not result.stdout.strip():
            return defaults
        return parse_component_inventory(json.loads(result.stdout.lstrip("\ufeff")))
    except (OSError, ValueError, subprocess.TimeoutExpired, UnicodeError):
        return defaults


def find_gpu_driver(gpu_name, adapters):
    """Asocia driver solo por identidad explícita; evita confundir dGPU/iGPU."""
    if not isinstance(gpu_name, str) or not isinstance(adapters, list):
        return "N/A"
    requested = " ".join(gpu_name.casefold().split())
    if requested in ("n/a", ""):
        return "N/A"
    for adapter in adapters:
        if not isinstance(adapter, dict):
            continue
        observed = " ".join(str(adapter.get("name") or "").casefold().split())
        if observed == requested:
            return adapter.get("driver") or "N/A"
    return "N/A"


# Sensor CPU de la versión clásica de CorePulse (HardwareMonitor). Se consulta
# en un subproceso para aislar el runtime .NET del hilo gráfico Qt.
# No instala software, inicia drivers adicionales ni escribe en Windows.
_CPU_PACKAGE_PROBE = r'''
import json
import time

def enum_name(value):
    return str(value or "").split(".")[-1].strip()

def valid(value):
    try:
        number = float(value)
        return round(number, 1) if 5.0 <= number <= 115.0 else None
    except (TypeError, ValueError, OverflowError):
        return None

def valid_power(value):
    try:
        number = float(value)
        return round(number, 1) if 0.0 < number <= 1200.0 else None
    except (TypeError, ValueError, OverflowError):
        return None

def score(sensor):
    name = str(sensor.get("sensor") or "").casefold()
    hw = str(sensor.get("hardware") or "").casefold()
    hw_type = str(sensor.get("hardware_type") or "").casefold()
    ident = str(sensor.get("identifier") or "").casefold()
    text = f"{name} {hw} {hw_type} {ident}"
    if any(part in text for part in ("gpu", "nvidia", "radeon gpu", "nvme", "ssd", "hdd", "storage", "battery", "ambient", "pch", "vrm", "mos", "distance to tjmax", "tjmax")):
        return -1000
    priority = 100 if hw_type == "cpu" else 0
    if "/cpu/" in ident or "/intelcpu/" in ident or "/amdcpu/" in ident:
        priority += 90
    if any(token in hw for token in ("intel", "ryzen", "processor", "cpu")):
        priority += 40
    for token, points in (("cpu package", 170), ("cpu (tctl/tdie)", 165),
                          ("tctl/tdie", 160), ("cpu core", 150),
                          ("core max", 145), ("core average", 135),
                          ("tdie", 125), ("tctl", 120),
                          ("cpu temperature", 115), ("cpu temp", 115),
                          ("package", 90), ("cpu", 85)):
        if token in name:
            priority += points
            break
    return priority

computer = None
try:
    import HardwareMonitor  # paquete que utilizaba CorePulse clásico
    from HardwareMonitor.Hardware import Computer
    computer = Computer()
    computer.IsCpuEnabled = True
    computer.IsMotherboardEnabled = True
    computer.IsControllerEnabled = True
    computer.Open()
    rows = []
    power_rows = []
    core_rows = []
    core_names = set()

    def walk(hw):
        try:
            hw.Update()
        except Exception:
            pass
        hw_name = str(getattr(hw, "Name", "") or "")
        hw_type = enum_name(getattr(hw, "HardwareType", ""))
        for item in list(getattr(hw, "Sensors", ())):
            kind = enum_name(getattr(item, "SensorType", "")).casefold()
            if kind not in ("temperature", "power"):
                continue
            name = str(getattr(item, "Name", "") or "")[:75]
            ident = str(getattr(item, "Identifier", "") or "")
            # Algunas versiones .NET identifican la CPU por HardwareType,
            # aunque Identifier no contenga /cpu/. Conservar esa ruta histórica.
            from_cpu = (hw_type.casefold() == "cpu" or any(token in ident.casefold()
                        for token in ("/intelcpu/", "/amdcpu/", "/cpu/")))
            from_ec = (hw_type.casefold() in ("superio", "embeddedcontroller", "ec")
                       and any(label in name.casefold() for label in
                               ("cpu package", "cpu temp", "cpu temperature", "cpu core")))
            if not (from_cpu or from_ec):
                continue
            record = {"sensor": name, "hardware": hw_name,
                      "hardware_type": hw_type, "identifier": ident}
            if kind == "power":
                watts = valid_power(getattr(item, "Value", None))
                if watts is not None and ("package" in name.casefold() or "cpu" in name.casefold()):
                    power_rows.append((0 if "package" in name.casefold() else 1, watts))
                continue
            value = valid(getattr(item, "Value", None))
            if value is None:
                continue
            record["temp"] = value
            rank = score(record)
            if rank >= 90:
                rows.append((rank, record))
                lower = name.casefold()
                if ("core" in lower or "ccd" in lower) and lower not in core_names and len(core_rows) < 32:
                    core_names.add(lower)
                    core_rows.append({"name": name, "value": value})
        for child in list(getattr(hw, "SubHardware", ())):
            walk(child)

    for hardware in list(computer.Hardware):
        walk(hardware)
    power = None
    if power_rows:
        best = min(rank for rank, _ in power_rows)
        power = max(value for rank, value in power_rows if rank == best)
    if rows:
        selected = max(rows, key=lambda item: (item[0], item[1]["temp"]))[1]
        selected["source"] = "HardwareMonitor / LibreHardwareMonitorLib (lectura directa)"
        selected["power"] = power
        selected["coreTemps"] = core_rows
        print(json.dumps(selected, ensure_ascii=False))
    else:
        print(json.dumps({"temp": None, "power": power, "coreTemps": core_rows,
                          "reason": "El motor abrió, pero no publicó temperatura CPU válida"}, ensure_ascii=False))
except Exception as exc:
    print(json.dumps({"temp": None, "reason": f"{type(exc).__name__}: {str(exc)[:160]}"}, ensure_ascii=False))
finally:
    if computer is not None:
        try:
            computer.Close()
        except Exception:
            pass
'''
_CPU_PACKAGE_PROBE_CACHE = {"at": 0.0, "data": None}


def query_packaged_cpu_temperature():
    """Lee CPU mediante el motor antiguo: Intel/AMD y EC/SuperIO de OEM.

    Fail closed: nunca usa temperatura GPU/SSD ni valores ausentes como CPU.
    La caché permite lecturas más frecuentes sin lanzar procesos .NET a cada segundo
    (2 s con lectura válida y 20 s con fallo).
    """
    if os.name != "nt":
        return {"temp": None, "reason": "Windows requerido"}
    cache = _CPU_PACKAGE_PROBE_CACHE
    now = time.monotonic()
    ttl = 2.0 if cache["data"] and cache["data"].get("temp") is not None else 20.0
    if cache["at"] > 0 and now - cache["at"] < ttl:
        return dict(cache["data"])
    try:
        proc = subprocess.run(
            [sys.executable, "-B", "-c", _CPU_PACKAGE_PROBE],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=8, check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        lines = [line.strip() for line in (proc.stdout or "").splitlines() if line.strip()]
        data = json.loads(lines[-1]) if lines else {"temp": None, "reason": (proc.stderr or "Sin salida del monitor")[:160]}
        temp = positive_number(data.get("temp"), minimum=4.99, maximum=115)
        if temp is None or not data.get("sensor") or not data.get("hardware"):
            result = {"temp": None, "reason": str(data.get("reason") or "Sensor CPU no disponible")[:180]}
        else:
            # La sonda aislada filtra otros tipos de hardware por identificador.
            extra = parse_cpu_extra_sensors(
                [{"Identifier": "/cpu/0/power/0", "SensorType": "Power", "Name": "CPU Package",
                  "Value": data.get("power")}] +
                [{"Identifier": "/cpu/0/temperature/" + str(i), "SensorType": "Temperature",
                  "Name": item.get("name"), "Value": item.get("value")}
                 for i, item in enumerate((data.get("coreTemps") or [])[:32]) if isinstance(item, dict)]
            )
            result = {"temp": round(temp, 1),
                      "source": "HardwareMonitor / LibreHardwareMonitorLib (directo)",
                      "sensor": str(data["hardware"]) + " / " + str(data["sensor"]),
                      "identifier": str(data.get("identifier") or ""),
                      "power": extra["power"], "coreTemps": extra["coreTemps"]}
    except (OSError, ValueError, subprocess.TimeoutExpired, UnicodeError) as exc:
        result = {"temp": None, "reason": type(exc).__name__ + ": " + str(exc)[:150]}
    cache.update(at=time.monotonic(), data=result)
    return dict(result)


def query_hardware_with_legacy(drive, include_disk):
    """Lee fuentes reales: sonda directa preferida y WMI como alternativa.

    Algunas instancias externas WMI no publican nuevas muestras con frecuencia.
    La sonda .NET aislada obtiene una muestra de CPU cuando está disponible;
    si falla, mantenemos WMI sin inferir temperaturas desde GPU/SSD.
    """
    data = query_windows_hardware(drive, include_disk)
    direct = query_packaged_cpu_temperature()
    if direct.get("temp") is not None:
        data["temp"] = direct["temp"]
        data["tempSource"] = direct["source"] + " · " + direct["sensor"]
    elif data["temp"] is not None:
        data["tempSource"] = "LibreHardwareMonitor/OpenHardwareMonitor (WMI)"
    else:
        data["tempSource"] = "N/A · " + str(direct.get("reason") or "Sensor CPU no disponible")[:180]
    if direct.get("power") is not None:
        data["power"] = direct["power"]
        data["detailSource"] = "HardwareMonitor / LibreHardwareMonitorLib (directo)"
    if direct.get("coreTemps"):
        data["coreTemps"] = direct["coreTemps"]
        data["detailSource"] = "HardwareMonitor / LibreHardwareMonitorLib (directo)"
    return data


class WindowsCpuFrequency:
    """Lee exclusivamente % Processor Performance vía PDH (sin bloqueo).

    La velocidad derivada usa la frecuencia NOMINAL de Windows (WMI) y esta
    medida del rendimiento. No confundir con un sensor de MHz por núcleo.
    """
    def __init__(self):
        self._pdh = self._query = self._counter = None
        if os.name != "nt":
            return
        try:
            import ctypes
            from ctypes import wintypes
            pdh = ctypes.WinDLL("pdh.dll")
            pdh.PdhOpenQueryW.argtypes = [wintypes.LPCWSTR, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
            pdh.PdhAddEnglishCounterW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
            pdh.PdhCollectQueryData.argtypes = [ctypes.c_void_p]
            pdh.PdhCloseQuery.argtypes = [ctypes.c_void_p]
            for fn in (pdh.PdhOpenQueryW, pdh.PdhAddEnglishCounterW, pdh.PdhCollectQueryData,
                       pdh.PdhCloseQuery):
                fn.restype = ctypes.c_long
            query = ctypes.c_void_p()
            counter = ctypes.c_void_p()
            if pdh.PdhOpenQueryW(None, None, ctypes.byref(query)) != 0:
                return
            if pdh.PdhAddEnglishCounterW(query,
                                        r"\Processor Information(_Total)\% Processor Performance",
                                        None, ctypes.byref(counter)) != 0:
                pdh.PdhCloseQuery(query)
                return
            self._pdh, self._query, self._counter = pdh, query, counter
            pdh.PdhCollectQueryData(query)  # Primera muestra sin usar datos incompletos.
        except (OSError, AttributeError, ValueError):
            self.close()

    def read_performance_percent(self):
        if self._pdh is None or self._query is None:
            return None
        try:
            import ctypes
            from ctypes import wintypes
            class FormattedValue(ctypes.Structure):
                _fields_ = [("CStatus", wintypes.DWORD), ("doubleValue", ctypes.c_double)]
            self._pdh.PdhGetFormattedCounterValue.argtypes = [
                ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(FormattedValue)]
            self._pdh.PdhGetFormattedCounterValue.restype = ctypes.c_long
            if self._pdh.PdhCollectQueryData(self._query) != 0:
                return None
            value = FormattedValue()
            # PDH_FMT_DOUBLE=0x200. No coerción de contadores inválidos.
            if self._pdh.PdhGetFormattedCounterValue(self._counter, 0x00000200, None,
                                                      ctypes.byref(value)) != 0:
                return None
            if value.CStatus not in (0, 1):
                return None
            return positive_number(value.doubleValue, minimum=0, maximum=400)
        except (OSError, AttributeError, ValueError, TypeError):
            return None

    def close(self):
        if self._pdh is not None and self._query is not None:
            try:
                self._pdh.PdhCloseQuery(self._query)
            except (OSError, AttributeError):
                pass
        self._pdh = self._query = self._counter = None


def build_available_readings(metrics: dict, *, cpu_pending: bool = False,
                             gpu_pending: bool = False) -> tuple[list[dict], str]:
    """Las 7 comprobaciones del monitor histórico, sin fabricar sensores.

    Lectura ausente => No disponible. Solo se marca Evaluando durante la
    primera consulta asíncrona. Las estimaciones de frecuencia son visibles
    y están etiquetadas como tales, nunca se hacen pasar por reloj físico.
    """
    def valid(value, low, high):
        return (isinstance(value, (int, float)) and not isinstance(value, bool)
                and math.isfinite(value) and low <= value <= high)

    def item(key, name, value, source, available, pending=False):
        return {"id": key, "name": name, "value": value if available else "N/A",
                "source": source or "N/A",
                "status": "Disponible" if available else ("Evaluando" if pending else "No disponible")}

    cpu_use = valid(metrics.get("cpuPercent"), 0, 100)
    cpu_ghz = valid(metrics.get("cpuGHz"), 0.1, 12)
    cpu_temp = valid(metrics.get("cpuTemp"), 1, 115)
    ram_use = valid(metrics.get("ramPercent"), 0, 100)
    gpu_use = valid(metrics.get("gpuPercent"), 0, 100)
    gpu_temp = valid(metrics.get("gpuTemp"), 1, 125)
    vram_used = metrics.get("gpuVramUsed")
    vram_total = metrics.get("gpuVramTotal")
    vram_ok = (valid(vram_total, 0.001, 2048) and valid(vram_used, 0, 2048)
               and vram_used <= vram_total)
    clock_source = metrics.get("cpuClockSource") or "N/A"
    clock_suffix = " (est.)" if clock_source.startswith("Estimación") else ""
    gpu_source = "NVIDIA-SMI / NVML" if gpu_use or gpu_temp or vram_ok else "N/A"

    rows = [
        item("cpuPercent", "Uso de CPU", f'{metrics["cpuPercent"]:.1f}%' if cpu_use else "N/A", "Windows / psutil", cpu_use),
        item("cpuGHz", "Frecuencia de CPU", f'{metrics["cpuGHz"]:.2f} GHz{clock_suffix}' if cpu_ghz else "N/A",
             clock_source, cpu_ghz, cpu_pending),
        item("cpuTemp", "Temperatura de CPU", f'{metrics["cpuTemp"]:.1f} °C' if cpu_temp else "N/A",
             metrics.get("cpuTempSource"), cpu_temp, cpu_pending),
        item("ramPercent", "Uso de RAM", f'{metrics["ramPercent"]:.1f}%' if ram_use else "N/A",
             "Windows / psutil (total - disponible)", ram_use),
        item("gpuPercent", "Uso de GPU", f'{metrics["gpuPercent"]:.1f}%' if gpu_use else "N/A",
             metrics.get("gpuUtilSource") or gpu_source, gpu_use, gpu_pending),
        item("gpuTemp", "Temperatura de GPU", f'{metrics["gpuTemp"]:.1f} °C' if gpu_temp else "N/A",
             gpu_source, gpu_temp, gpu_pending),
        item("gpuVram", "Memoria de video (VRAM)",
             f'{vram_used:.2f} / {vram_total:.2f} GiB' if vram_ok else "N/A",
             gpu_source, vram_ok, gpu_pending),
    ]
    count = sum(row["status"] == "Disponible" for row in rows)
    return rows, f"{count}/7"


class Telemetry(QObject):
    metricsChanged = Signal()
    historyChanged = Signal()

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="corepulse-sensors")
        self._gpu_future: Future | None = None
        self._hardware_future: Future | None = None
        self._inventory_future: Future | None = None
        self._inventory = parse_component_inventory({})
        self._inventory_requested = False
        self._inventory_ready = False
        self._gpu_next_poll = 0.0
        self._hardware_next_poll = 0.0
        self._disk_next_attempt = 0.0
        self._gpu = parse_nvidia_csv("")
        self._hardware = {"temp": None, "ghz": None, "disk": None, "baseMHz": None,
                          "tempSource": "N/A", "power": None, "coreTemps": [],
                          "detailSource": "N/A"}
        self._gpu_sample_time = 0.0
        self._cpu_sensor_time = 0.0
        self._cpu_freq = WindowsCpuFrequency()
        self._history_cpu: list[float | None] = []
        self._history_gpu: list[float | None] = []
        self._name = cpu_name()
        self._computer = machine_model()
        self._system_disk = system_disk()
        self._cpu_physical = psutil.cpu_count(logical=False)
        self._cpu_logical = psutil.cpu_count(logical=True)
        self._metrics = self._empty_metrics()
        psutil.cpu_percent(interval=None)  # línea base, no se muestra como muestra real
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self.refresh)
        self._timer.start()
        self.refresh()  # datos iniciales (lecturas externas llegan asincrónicamente)

    def _empty_metrics(self) -> dict:
        return {
            "computer": self._computer, "cpuName": self._name,
            "cpuPercent": None, "cpuGHz": None, "cpuTemp": None,
            "cpuArchitecture": platform.machine() or "N/A",
            "cpuManufacturer": "N/A", "cpuSocket": "N/A",
            "cpuPhysicalCores": self._cpu_physical, "cpuLogicalThreads": self._cpu_logical,
            "cpuBaseGHz": None, "cpuPackagePower": None, "cpuCoreTemps": [],
            "cpuDetailSource": "N/A",
            "gpuName": "N/A", "gpuPercent": None, "gpuTemp": None,
            "gpuDriver": "N/A", "gpuAdapters": [], "inventoryReady": self._inventory_ready,
            "gpuVramUsed": None, "gpuVramTotal": None,
            "ramPercent": None, "ramUsed": None, "ramTotal": None,
            "ramAvailable": None, "ramModules": [],
            "diskPercent": None, "diskUsed": None, "diskTotal": None,
            "diskName": "N/A", "diskLabel": self._system_disk,
            "cpuClockSource": "N/A", "cpuTempSource": "N/A",
            "gpuUtilSource": "N/A", "diskNameSource": "N/A",
            "uptime": "N/A", "uptimeSeconds": None, "coverage": "0/7", "readings": [],
            "coverageDetail": "Ver las 7 lecturas", "health": "N/A", "alerts": "N/A",
        }

    @Property("QVariantMap", notify=metricsChanged)
    def metrics(self):
        return self._metrics

    @Property("QVariantList", notify=historyChanged)
    def cpuHistory(self):
        return self._history_cpu

    @Property("QVariantList", notify=historyChanged)
    def gpuHistory(self):
        return self._history_gpu

    @Slot()
    def refresh(self):
        # NVIDIA, WMI e inventario solo en trabajadores; nunca bloquear Qt.
        now = time.monotonic()
        if self._inventory_future is not None and self._inventory_future.done():
            try:
                self._inventory = self._inventory_future.result()
            except Exception:
                self._inventory = parse_component_inventory({})
            self._inventory_future = None
            self._inventory_ready = True
        # El inventario es de consulta única: no volver a lanzar PowerShell cada segundo.
        if not self._inventory_requested:
            self._inventory_requested = True
            self._inventory_future = self._executor.submit(query_windows_component_inventory)
        if self._gpu_future is not None and self._gpu_future.done():
            try:
                self._gpu = self._gpu_future.result()
                self._gpu_sample_time = now
            except Exception:
                self._gpu = parse_nvidia_csv("")
                self._gpu_sample_time = 0
            self._gpu_future = None
        if self._gpu_future is None and now >= self._gpu_next_poll:
            self._gpu_future = self._executor.submit(query_nvidia)
            self._gpu_next_poll = now + 1.5  # antes cada 4 s: ahora GPU NVIDIA más actual
        if self._hardware_future is not None and self._hardware_future.done():
            try:
                updated = self._hardware_future.result()
                self._hardware.update({k: v for k, v in updated.items()
                                       if k in ("temp", "ghz", "tempSource", "power", "coreTemps", "detailSource")})
                self._cpu_sensor_time = now
                if updated.get("disk"):
                    self._hardware["disk"] = updated["disk"]
                if updated.get("baseMHz") is not None:
                    self._hardware["baseMHz"] = updated["baseMHz"]
            except Exception:
                self._hardware["temp"] = self._hardware["ghz"] = None
                self._hardware["power"], self._hardware["coreTemps"] = None, []
                self._hardware["detailSource"] = "N/A"
                self._cpu_sensor_time = 0.0
            self._hardware_future = None
        if self._hardware_future is None and now >= self._hardware_next_poll:
            include_disk = self._hardware["disk"] is None and now >= self._disk_next_attempt
            self._hardware_future = self._executor.submit(query_hardware_with_legacy, self._system_disk, include_disk)
            self._hardware_next_poll = now + 4.0
            if include_disk:
                self._disk_next_attempt = now + 60.0

        metrics = self._empty_metrics()
        metrics.update(self._inventory)
        # Psutil conoce al menos el número de procesadores del sistema si CIM falla.
        if metrics.get("cpuPhysicalCores") is None:
            metrics["cpuPhysicalCores"] = self._cpu_physical
        if metrics.get("cpuLogicalThreads") is None:
            metrics["cpuLogicalThreads"] = self._cpu_logical
        metrics["gpuDriver"] = find_gpu_driver(self._gpu.get("name"), self._inventory["gpuAdapters"])
        base_mhz = self._hardware.get("baseMHz")
        metrics["cpuBaseGHz"] = round(base_mhz / 1000, 2) if positive_number(base_mhz, 100, 12000) else None
        if self._gpu_sample_time > 0 and now - self._gpu_sample_time <= 5.0:
            metrics.update(gpuName=self._gpu["name"], gpuPercent=self._gpu["usage"],
                           gpuTemp=self._gpu["temp"], gpuVramUsed=self._gpu["vramUsed"],
                           gpuVramTotal=self._gpu["vramTotal"])
            if self._gpu["usage"] is not None:
                metrics["gpuUtilSource"] = "NVIDIA-SMI / NVML (uso núcleo GPU, no Task Manager)"
        else:
            # Si deja de responder, no mantenemos un porcentaje viejo como si fuera actual.
            metrics["gpuName"] = self._gpu["name"]
        if now - self._cpu_sensor_time <= 12.0:
            metrics["cpuTemp"] = self._hardware["temp"]
            metrics["cpuTempSource"] = self._hardware.get("tempSource", "N/A")
            metrics["cpuPackagePower"] = self._hardware.get("power")
            metrics["cpuCoreTemps"] = self._hardware.get("coreTemps", [])
            metrics["cpuDetailSource"] = self._hardware.get("detailSource", "N/A")
        metrics["diskName"] = self._hardware["disk"] or "N/A"
        if self._hardware["disk"]:
            metrics["diskNameSource"] = "Windows Get-Disk"
        try:
            metrics["cpuPercent"] = percentage(psutil.cpu_percent(interval=None))
        except (OSError, ValueError):
            pass
        # 1) Reloj de núcleos medido por sensor CPU (si está vigente).
        clock = self._hardware["ghz"] if now - self._cpu_sensor_time <= 12.0 else None
        if clock is not None:
            metrics["cpuClockSource"] = "Clocks CPU medidos por monitor WMI"
        else:
            # 2) Estimación a partir de DOS datos reales de Windows: frecuencia
            # nominal WMI + % Processor Performance PDH (incluye Turbo Boost).
            perf = self._cpu_freq.read_performance_percent()
            clock = estimated_cpu_ghz(self._hardware["baseMHz"], perf)
            if clock is not None:
                metrics["cpuClockSource"] = "Estimación Windows PDH (% rendimiento × nominal)"
        # No mostrar CPU nominal como si fuera frecuencia instantánea.
        metrics["cpuGHz"] = clock
        try:
            memory = psutil.virtual_memory()
            metrics["ramPercent"], metrics["ramUsed"], metrics["ramTotal"] = ram_reading(memory)
            available = positive_number(memory.available, minimum=-1)
            if metrics["ramTotal"] is not None and available is not None and available <= memory.total:
                metrics["ramAvailable"] = round(available / (1024**3), 1)
        except (OSError, ValueError, AttributeError):
            pass
        try:
            disk = psutil.disk_usage(self._system_disk)
            metrics.update(diskPercent=percentage(disk.percent),
                           diskUsed=round(disk.used / (1024**3), 1),
                           diskTotal=round(disk.total / (1024**3), 1))
        except (OSError, ValueError):
            pass
        try:
            uptime_seconds = max(0, time.time() - psutil.boot_time())
            metrics["uptime"] = format_uptime(uptime_seconds)
            metrics["uptimeSeconds"] = int(uptime_seconds)
        except (OSError, ValueError):
            pass

        readings, metrics["coverage"] = build_available_readings(
            metrics,
            cpu_pending=self._cpu_sensor_time <= 0 and self._hardware_future is not None,
            gpu_pending=self._gpu_sample_time <= 0 and self._gpu_future is not None,
        )
        metrics["readings"] = readings
        missing = 7 - int(metrics["coverage"].split("/", 1)[0])
        metrics["coverageDetail"] = ("7 métricas verificadas" if missing == 0
                                      else f"{missing} pendientes o no disponibles")
        self._metrics = metrics
        self._history_cpu = (self._history_cpu + [metrics["cpuPercent"]])[-60:]
        self._history_gpu = (self._history_gpu + [metrics["gpuPercent"]])[-60:]
        self.metricsChanged.emit()
        self.historyChanged.emit()

    @Slot()
    def close(self):
        self._timer.stop()
        self._cpu_freq.close()
        self._executor.shutdown(wait=False, cancel_futures=True)
