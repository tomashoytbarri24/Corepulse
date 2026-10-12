"""Autodiagnóstico de capacidades de CorePulse.

V134 combina dos fuentes que CorePulse ya conoce:
- el preflight/runtime real del equipo actual;
- el último snapshot certificado de telemetría/sensores.

No genera puntuaciones de salud ni supone que una capacidad opcional ausente sea
un fallo. Los estados son descriptivos: AVAILABLE, PARTIAL, N/A, INFO o ERROR.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
from typing import Any, Dict, Iterable, List

from core.runtime_paths import diagnostics_dir
# V482: símbolo disponible localmente
from core.startup_readiness import collect_readiness
from core.version import VERSION_LABEL

POLICY = "REAL_OR_NA_ONLY"
SCHEMA = 1


def _state_from_readiness(status: str, required: bool) -> str:
    raw = str(status or "N/A").upper()
    if raw == "OK":
        return "AVAILABLE"
    if raw == "INFO":
        return "INFO"
    if required:
        return "ERROR"
    return "N/A"


def _powershell_path() -> str | None:
    for name in ("powershell.exe", "powershell", "pwsh.exe", "pwsh"):
        found = shutil.which(name)
        if found:
            return str(found)
    if os.name == "nt":
        root = Path(os.environ.get("SystemRoot", r"C:\Windows"))
        candidate = root / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
        if candidate.is_file():
            return str(candidate)
    return None


def _sensor_state(group: Dict[str, Any]) -> str:
    raw = str(group.get("state") or "UNAVAILABLE").upper()
    return {
        "AVAILABLE": "AVAILABLE",
        "PARTIAL": "PARTIAL",
        "UNAVAILABLE": "N/A",
    }.get(raw, "N/A")


def _sensor_detail(group: Dict[str, Any]) -> str:
    available = int(group.get("available") or 0)
    total = int(group.get("total") or 0)
    base = str(group.get("detail") or "").strip()
    sources = [str(x) for x in (group.get("sources") or []) if str(x).strip()]
    parts = [f"{available} de {total} lecturas certificadas"]
    if base:
        parts.append(base)
    if sources:
        parts.append("Fuentes: " + ", ".join(sources[:3]))
    return " · ".join(parts)


def _count_states(items: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    counts = {"AVAILABLE": 0, "PARTIAL": 0, "N/A": 0, "INFO": 0, "ERROR": 0}
    for item in items:
        state = str(item.get("state") or "N/A").upper()
        if state not in counts:
            state = "N/A"
        counts[state] += 1
    return counts


def collect_corepulse_diagnostics(
    telemetry: Any = None,
    *,
    runtime_context: Dict[str, Any] | None = None,
    persist: bool = True,
) -> Dict[str, Any]:
    """Construye un informe de capacidades sin convertir N/A en fallo.

    ``runtime_context`` puede incluir hechos ya conocidos por la UI (por ejemplo,
    si el agente está ejecutándose). No se infieren valores ausentes.
    """
    context = runtime_context if isinstance(runtime_context, dict) else {}
    readiness = collect_readiness(version=VERSION_LABEL)
    sensor_report = build_sensor_diagnostics(telemetry if isinstance(telemetry, dict) else {})

    runtime_items: List[Dict[str, Any]] = []
    optional_items: List[Dict[str, Any]] = []
    for item in readiness.items:
        row = {
            "id": str(item.id),
            "label": str(item.label),
            "state": _state_from_readiness(item.status, bool(item.required)),
            "required": bool(item.required),
            "detail": str(item.detail or ""),
            "source": "startup_readiness",
        }
        (runtime_items if item.required else optional_items).append(row)

    # PowerShell es necesario para DISM/SFC, pero no para el monitoreo normal.
    powershell = _powershell_path()
    optional_items.append({
        "id": "powershell",
        "label": "Windows PowerShell",
        "state": "AVAILABLE" if powershell else "N/A",
        "required": False,
        "detail": powershell or "No se detectó PowerShell; reparación DISM/SFC queda no disponible.",
        "source": "filesystem/path",
    })

    # Hechos del runtime que la propia App ya conoce; no se ejecutan probes nuevos.
    if "agent_running" in context:
        running = bool(context.get("agent_running"))
        optional_items.append({
            "id": "realtime_agent",
            "label": "Agente de monitoreo",
            "state": "AVAILABLE" if running else "INFO",
            "required": False,
            "detail": "Agente en ejecución" if running else "El agente todavía no reporta ejecución activa.",
            "source": "runtime_context",
        })
    if "telemetry_snapshot" in context:
        has_snapshot = bool(context.get("telemetry_snapshot"))
        optional_items.append({
            "id": "telemetry_snapshot",
            "label": "Snapshot de telemetría",
            "state": "AVAILABLE" if has_snapshot else "INFO",
            "required": False,
            "detail": "Existe un snapshot real disponible" if has_snapshot else "Aún no se recibió un snapshot de telemetría.",
            "source": "runtime_context",
        })

    sensor_items: List[Dict[str, Any]] = []
    for group in sensor_report.get("groups") or []:
        if not isinstance(group, dict):
            continue
        sensor_items.append({
            "id": "sensor_" + str(group.get("key") or "unknown"),
            "label": str(group.get("label") or "Sensores"),
            "state": _sensor_state(group),
            "required": False,
            "detail": _sensor_detail(group),
            "source": "CURRENT_TELEMETRY_SNAPSHOT",
            "metrics": list(group.get("metrics") or []),
            "unavailable": list(group.get("unavailable") or []),
        })

    all_items = runtime_items + optional_items + sensor_items
    counts = _count_states(all_items)
    critical_errors = [x for x in runtime_items if x.get("state") == "ERROR"]
    if critical_errors:
        overall = "ERROR"
        title = "El núcleo de CorePulse requiere atención"
    else:
        overall = "AVAILABLE"
        title = "Núcleo de CorePulse listo"

    report: Dict[str, Any] = {
        "schema": SCHEMA,
        "version": VERSION_LABEL,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "policy": POLICY,
        "overall_state": overall,
        "title": title,
        "ready": not critical_errors,
        "counts": counts,
        "runtime": runtime_items,
        "optional": optional_items,
        "sensors": sensor_items,
        "sensor_metrics_available": int(sensor_report.get("available") or 0),
        "sensor_metrics_total": int(sensor_report.get("total") or 0),
        "note": "N/A significa que la capacidad no está instalada, presente o expuesta; no se interpreta como fallo del equipo.",
    }

    if persist:
        try:
            path = diagnostics_dir() / "corepulse_capabilities.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            report["report_path"] = str(path)
        except Exception as exc:
            report["persist_error"] = f"{type(exc).__name__}: {exc}"
    return report


# V482: fusión sin cambios de lógica desde core/sensors/sensor_diagnostics.py
from typing import Any, Dict, Iterable, List


_REASON_LABELS = {
    'SENSOR_NOT_EXPOSED': 'sensor no expuesto',
    'SENSOR_SAMPLE_OLD': 'lectura antigua',
    'NOT_PRESENT_OR_NOT_EXPOSED': 'no presente/no expuesto',
    'UNAVAILABLE': 'no disponible',
}


def _metric_meta(meta: Any) -> Dict[str, Any]:
    return meta if isinstance(meta, dict) else {}


def _source(meta: Any) -> str | None:
    item = _metric_meta(meta)
    value = item.get('source')
    if value:
        return str(value)
    sensor = item.get('sensor')
    if sensor:
        return str(sensor)
    return None


def _quality(meta: Any) -> str:
    return str(_metric_meta(meta).get('quality') or 'UNAVAILABLE').upper()


def _is_available(meta: Any) -> bool:
    item = _metric_meta(meta)
    return bool(item.get('available')) or _quality(item) == 'VALID'


def _reason(meta: Any) -> str | None:
    item = _metric_meta(meta)
    value = item.get('reason')
    if not value:
        return None
    return _REASON_LABELS.get(str(value).upper(), str(value).replace('_', ' ').lower())


def _dedupe(values: Iterable[str | None]) -> List[str]:
    out: List[str] = []
    seen = set()
    for value in values:
        text = str(value or '').strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out


def _group(key: str, label: str, metrics: List[tuple[str, Dict[str, Any]]], *, detail: str = '') -> Dict[str, Any]:
    total = len(metrics)
    available = sum(1 for _, meta in metrics if _is_available(meta))
    if total <= 0:
        state = 'UNAVAILABLE'
    elif available == total:
        state = 'AVAILABLE'
    elif available > 0:
        state = 'PARTIAL'
    else:
        state = 'UNAVAILABLE'
    sources = _dedupe(_source(meta) for _, meta in metrics if _is_available(meta))
    unavailable = [
        {'label': label_text, 'reason': _reason(meta) or 'sin lectura certificada'}
        for label_text, meta in metrics
        if not _is_available(meta)
    ]
    return {
        'key': key,
        'label': label,
        'state': state,
        'available': available,
        'total': total,
        'coverage_percent': (available / total * 100.0) if total else 0.0,
        'sources': sources,
        'unavailable': unavailable,
        'detail': detail,
        'metrics': [
            {
                'label': label_text,
                'available': _is_available(meta),
                'quality': _quality(meta),
                'source': _source(meta),
                'reason': _reason(meta),
            }
            for label_text, meta in metrics
        ],
    }


def build_sensor_diagnostics(snapshot: Any) -> Dict[str, Any]:
    """Devuelve una lectura compacta de sensores sin volver a consultar hardware."""
    snap = snapshot if isinstance(snapshot, dict) else {}
    matrix = snap.get('_hardware_capability_matrix')
    matrix = matrix if isinstance(matrix, dict) else {}
    top = snap.get('_metrics')
    top = top if isinstance(top, dict) else {}

    groups: List[Dict[str, Any]] = []

    cpu = matrix.get('cpu') if isinstance(matrix.get('cpu'), dict) else {}
    cpu_metrics = cpu.get('metrics') if isinstance(cpu.get('metrics'), dict) else {}
    cpu_items = [
        ('Uso', _metric_meta(top.get('cpu_usage'))),
        ('Temperatura', _metric_meta(cpu_metrics.get('package_temp_c') or top.get('cpu_temp'))),
        ('Frecuencia', _metric_meta(cpu_metrics.get('clock_avg_ghz') or top.get('cpu_ghz'))),
        ('Potencia', _metric_meta(cpu_metrics.get('package_power_w'))),
    ]
    groups.append(_group('cpu', 'CPU', cpu_items, detail=str(cpu.get('name') or snap.get('cpu_name') or 'Procesador')))

    ram_items = [('Uso de memoria', _metric_meta(top.get('ram_usage')))]
    groups.append(_group('ram', 'RAM', ram_items, detail='Memoria del sistema'))

    gpu_list = matrix.get('gpus') if isinstance(matrix.get('gpus'), list) else []
    primary_gpu = None
    wanted_name = str(snap.get('gpu_name') or '').strip().lower()
    for gpu in gpu_list:
        if not isinstance(gpu, dict):
            continue
        if wanted_name and str(gpu.get('name') or '').strip().lower() == wanted_name:
            primary_gpu = gpu
            break
        if primary_gpu is None and gpu.get('telemetry_available'):
            primary_gpu = gpu
    if primary_gpu is None and gpu_list:
        primary_gpu = next((g for g in gpu_list if isinstance(g, dict)), None)
    if isinstance(primary_gpu, dict):
        gm = primary_gpu.get('metrics') if isinstance(primary_gpu.get('metrics'), dict) else {}
        gpu_items = [
            ('Uso', _metric_meta(gm.get('usage_percent') or top.get('gpu_usage'))),
            ('Temperatura', _metric_meta(gm.get('temperature_c') or top.get('gpu_temp'))),
            ('Hotspot', _metric_meta(gm.get('hotspot_c'))),
            ('Frecuencia', _metric_meta(gm.get('core_clock_mhz'))),
            ('Potencia', _metric_meta(gm.get('power_w'))),
        ]
        groups.append(_group('gpu', 'GPU', gpu_items, detail=str(primary_gpu.get('name') or snap.get('gpu_name') or 'GPU')))

    storage_list = matrix.get('storage') if isinstance(matrix.get('storage'), list) else []
    if storage_list:
        storage_items: List[tuple[str, Dict[str, Any]]] = []
        for idx, disk in enumerate(storage_list, 1):
            if not isinstance(disk, dict):
                continue
            dm = disk.get('metrics') if isinstance(disk.get('metrics'), dict) else {}
            disk_name = str(disk.get('name') or f'Unidad {idx}')
            storage_items.extend([
                (f'{disk_name} · temperatura', _metric_meta(dm.get('temperature_c'))),
                (f'{disk_name} · vida', _metric_meta(dm.get('life_percent'))),
            ])
        groups.append(_group('storage', 'Almacenamiento', storage_items, detail=f'{len(storage_list)} unidad(es) detectada(s)'))

    battery = matrix.get('battery') if isinstance(matrix.get('battery'), dict) else {}
    if battery.get('inventory_available'):
        bm = battery.get('metrics') if isinstance(battery.get('metrics'), dict) else {}
        battery_items = [
            ('Carga', _metric_meta(bm.get('charge_percent'))),
            ('Desgaste', _metric_meta(bm.get('degradation_percent'))),
            ('Capacidad completa', _metric_meta(bm.get('full_charge_capacity_mwh'))),
            ('Voltaje', _metric_meta(bm.get('voltage_v'))),
        ]
        groups.append(_group('battery', 'Batería', battery_items, detail='Batería detectada por el sistema'))

    total = sum(int(g.get('total') or 0) for g in groups)
    available = sum(int(g.get('available') or 0) for g in groups)
    state = 'AVAILABLE' if total and available == total else 'PARTIAL' if available else 'UNAVAILABLE'
    return {
        'policy': 'REAL_OR_NA_ONLY',
        'source': 'CURRENT_TELEMETRY_SNAPSHOT',
        'groups': groups,
        'available': available,
        'total': total,
        'coverage_percent': (available / total * 100.0) if total else 0.0,
        'state': state,
        'note': 'Esta vista reutiliza el último snapshot certificado; no vuelve a consultar hardware.',
    }
