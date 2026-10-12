"""Inteligencia determinista que alimenta CorePulse AI después de un diagnóstico.

La IA generativa no decide si existe una falla, ni inventa compatibilidad o vigencia.
Este módulo transforma evidencia certificada de CorePulse en estados, planes de acción
y consultas de soporte. La capa generativa sólo los explica.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List

from core.device_identity import collect_hardware_inventory, collect_ram_identity

POLICY = 'DETERMINISTIC_ACTION_INTELLIGENCE_REAL_EVIDENCE_ONLY'


def _num(value: Any):
    if value is None or isinstance(value, bool):
        return None
    try:
        value = float(value)
    except Exception:
        return None
    return value if value == value and value not in (float('inf'), float('-inf')) else None


def _text(value: Any, limit: int = 180) -> str:
    return str(value or '').strip()[:limit]




def _first_not_none(*values):
    for value in values:
        if value is not None:
            return value
    return None

def _safe_modules(rows: Any) -> list[dict]:
    out = []
    for row in list(rows or [])[:8]:
        if not isinstance(row, dict):
            continue
        out.append({
            'slot': _text(row.get('slot'), 80) or None,
            'bank': _text(row.get('bank'), 80) or None,
            'manufacturer': _text(row.get('manufacturer'), 80) or None,
            'part_number': _text(row.get('part_number'), 100) or None,
            'capacity_gb': _num(row.get('capacity_gb')),
            'configured_speed_mhz': _num(row.get('configured_speed_mhz')),
            'speed_mhz': _num(row.get('speed_mhz')),
            'memory_type': _text(row.get('memory_type'), 32) or None,
            'form_factor': _text(row.get('form_factor'), 32) or None,
        })
    return out


def _safe_storage(rows: Any) -> list[dict]:
    out = []
    for row in list(rows or [])[:8]:
        if not isinstance(row, dict):
            continue
        out.append({
            'name': _text(row.get('name') or row.get('model'), 140) or None,
            'model': _text(row.get('model') or row.get('name'), 140) or None,
            'manufacturer': _text(row.get('manufacturer'), 80) or None,
            'total_space_gb': _num(_first_not_none(row.get('total_space_gb'), row.get('size_gb'), row.get('total_gb'))),
            'interface': _text(row.get('interface'), 40) or None,
            'temperature_c': _num(_first_not_none(row.get('temperature_c'), row.get('temperature'))),
            'health_percent': _num(_first_not_none(row.get('health_percent'), row.get('life_percent'), row.get('health'))),
        })
    return out


def collect_ai_inventory(telemetry: dict | None, disks: list | None) -> dict:
    """Inventario real sanitizado, sin seriales, UUID ni PNP IDs."""
    telemetry = telemetry if isinstance(telemetry, dict) else {}
    disks = disks if isinstance(disks, list) else []
    try:
        raw = collect_hardware_inventory(telemetry=telemetry, disks=disks)
    except Exception:
        raw = {}
    identity = raw.get('identity') if isinstance(raw.get('identity'), dict) else {}
    board = identity.get('motherboard') if isinstance(identity.get('motherboard'), dict) else {}
    cpu = raw.get('cpu') if isinstance(raw.get('cpu'), dict) else {}
    ram = raw.get('ram') if isinstance(raw.get('ram'), dict) else {}
    try:
        ram_identity = collect_ram_identity()
    except Exception:
        ram_identity = {}
    modules = _safe_modules((ram_identity or {}).get('modules') or ram.get('modules'))
    gpus = []
    for row in list(raw.get('gpus') or [])[:6]:
        if not isinstance(row, dict):
            continue
        name = _text(row.get('name'), 140)
        if not name:
            continue
        gpus.append({
            'name': name,
            'vendor': _text(row.get('vendor'), 80) or None,
            'vram_gb': _num(row.get('vram_gb') or row.get('vram_gb_wmi')),
            'driver_version': _text(row.get('driver_version'), 64) or None,
        })
    if not gpus:
        telemetry_gpu = _text(telemetry.get('gpu_name'), 140)
        if telemetry_gpu:
            gpus.append({
                'name': telemetry_gpu,
                'vendor': None,
                'vram_gb': _num(telemetry.get('gpu_vram_gb')),
                'driver_version': None,
            })
    storage = _safe_storage(raw.get('storage') or disks)
    return {
        'captured_at': raw.get('captured_at'),
        'device': {
            'form_factor': _text(identity.get('form_factor') or raw.get('form_factor'), 40) or 'UNKNOWN',
            'manufacturer': _text(identity.get('manufacturer'), 80) or None,
            'model': _text(identity.get('model'), 120) or None,
            'display_model': _text(identity.get('display_model'), 160) or None,
            'support_target': _text(identity.get('support_target'), 160) or None,
            'motherboard': ' '.join(x for x in (_text(board.get('manufacturer'), 80), _text(board.get('model'), 120)) if x) or None,
        },
        'cpu': {
            'name': _text(cpu.get('name') or telemetry.get('cpu_name'), 160) or None,
            'current_ghz': _num(cpu.get('current_ghz') or telemetry.get('cpu_ghz')),
        },
        'ram': {
            'total_gb': _num((ram_identity or {}).get('installed_capacity_gb') or ram.get('total_gb') or telemetry.get('ram_total_gb')),
            'module_count': int((ram_identity or {}).get('module_count') or ram.get('module_count') or len(modules)),
            'slots_total': (ram_identity or {}).get('slots_total'),
            'slots_available': (ram_identity or {}).get('slots_available'),
            'memory_types': list((ram_identity or {}).get('memory_types') or [])[:4],
            'modules': modules,
        },
        'gpus': gpus,
        'storage': storage,
        'policy': 'REAL_OS_IDENTITY_SANITIZED_NO_SERIALS',
    }


def _baseline(year: int) -> dict:
    """Política de vigencia de CorePulse, no una ley universal del mercado.

    Los escalones se versionan deliberadamente. Años futuros usan el tramo vigente
    hasta que una versión posterior de CorePulse actualice la política.
    """
    year = int(year)
    if year <= 2028:
        return {'ram_standard_gb': 16, 'ram_optimal_gb': 32, 'storage_standard_gb': 512, 'storage_optimal_gb': 1000, 'policy_window': '2026-2028'}
    if year <= 2031:
        return {'ram_standard_gb': 24, 'ram_optimal_gb': 32, 'storage_standard_gb': 1000, 'storage_optimal_gb': 2000, 'policy_window': '2029-2031'}
    return {'ram_standard_gb': 32, 'ram_optimal_gb': 64, 'storage_standard_gb': 1000, 'storage_optimal_gb': 2000, 'policy_window': '2032+'}


def evaluate_hardware_relevance(inventory: dict, *, year: int | None = None) -> list[dict]:
    year = int(year or datetime.now().year)
    policy = _baseline(year)
    out: list[dict] = []

    cpu_name = _text((inventory.get('cpu') or {}).get('name'), 160)
    out.append({
        'component_id': 'CPU', 'component_type': 'CPU', 'detected_hardware': cpu_name or 'N/A',
        'classification': 'NO_EVALUABLE', 'confidence': 'BAJA',
        'reason': f'CorePulse no clasifica la vigencia {year} de una CPU sólo por su nombre; requiere evidencia comparativa verificable del año actual.',
        'evidence_axes': {'runtime_year': year, 'policy_window': policy['policy_window'], 'external_reference_required': True},
    })

    gpu_name = _text(((inventory.get('gpus') or [{}])[0] or {}).get('name'), 160) if inventory.get('gpus') else ''
    out.append({
        'component_id': 'GPU', 'component_type': 'GPU', 'detected_hardware': gpu_name or 'N/A',
        'classification': 'NO_EVALUABLE', 'confidence': 'BAJA',
        'reason': f'CorePulse no clasifica la vigencia {year} de una GPU sin benchmark o evidencia comparativa verificable del año actual.',
        'evidence_axes': {'runtime_year': year, 'policy_window': policy['policy_window'], 'external_reference_required': True},
    })

    ram = inventory.get('ram') if isinstance(inventory.get('ram'), dict) else {}
    total = _num(ram.get('total_gb'))
    if total is None:
        ram_class, ram_conf, ram_reason = 'NO_EVALUABLE', 'BAJA', 'Capacidad RAM no disponible.'
    elif total >= policy['ram_optimal_gb']:
        ram_class, ram_conf, ram_reason = 'OPTIMO', 'ALTA', f'{total:.0f} GB alcanza el objetivo alto de la política CorePulse {policy["policy_window"]}.'
    elif total >= policy['ram_standard_gb']:
        ram_class, ram_conf, ram_reason = 'ESTANDAR', 'ALTA', f'{total:.0f} GB cumple el estándar CorePulse para {year}.'
    elif total >= max(8, policy['ram_standard_gb'] / 2):
        ram_class, ram_conf, ram_reason = 'JUSTO', 'ALTA', f'{total:.0f} GB queda por debajo del estándar CorePulse de {policy["ram_standard_gb"]} GB para {year}.'
    else:
        ram_class, ram_conf, ram_reason = 'POR_DEBAJO_DEL_ESTANDAR', 'ALTA', f'{total:.0f} GB está claramente por debajo del estándar CorePulse de {policy["ram_standard_gb"]} GB para {year}.'
    out.append({
        'component_id': 'RAM', 'component_type': 'RAM', 'detected_hardware': f'{total:.0f} GB' if total is not None else 'N/A',
        'classification': ram_class, 'confidence': ram_conf, 'reason': ram_reason,
        'evidence_axes': {'runtime_year': year, **policy, 'measured_total_gb': total, 'policy_type': 'COREPULSE_CAPACITY_BASELINE'},
    })

    storage = inventory.get('storage') if isinstance(inventory.get('storage'), list) else []
    primary = storage[0] if storage and isinstance(storage[0], dict) else {}
    cap = _num(primary.get('total_space_gb'))
    disk_name = _text(primary.get('model') or primary.get('name'), 140) or 'Almacenamiento'
    if cap is None:
        disk_class, disk_conf, disk_reason = 'NO_EVALUABLE', 'BAJA', 'Capacidad física de almacenamiento no disponible.'
    elif cap >= policy['storage_optimal_gb']:
        disk_class, disk_conf, disk_reason = 'OPTIMO', 'ALTA', f'{cap:.0f} GB alcanza el objetivo alto de capacidad CorePulse para {year}.'
    elif cap >= policy['storage_standard_gb']:
        disk_class, disk_conf, disk_reason = 'ESTANDAR', 'ALTA', f'{cap:.0f} GB cumple el estándar de capacidad CorePulse para {year}.'
    elif cap >= max(256, policy['storage_standard_gb'] / 2):
        disk_class, disk_conf, disk_reason = 'JUSTO', 'ALTA', f'{cap:.0f} GB queda por debajo del estándar CorePulse de {policy["storage_standard_gb"]} GB para {year}.'
    else:
        disk_class, disk_conf, disk_reason = 'POR_DEBAJO_DEL_ESTANDAR', 'ALTA', f'{cap:.0f} GB está claramente por debajo del estándar CorePulse de {policy["storage_standard_gb"]} GB para {year}.'
    out.append({
        'component_id': 'STORAGE:0', 'component_type': 'ALMACENAMIENTO', 'detected_hardware': f'{disk_name} · {cap:.0f} GB' if cap is not None else disk_name,
        'classification': disk_class, 'confidence': disk_conf, 'reason': disk_reason,
        'evidence_axes': {'runtime_year': year, **policy, 'measured_capacity_gb': cap, 'policy_type': 'COREPULSE_CAPACITY_BASELINE'},
    })
    return out


def _findings(diagnostic: dict) -> list[dict]:
    return [x for x in list((diagnostic or {}).get('findings') or []) if isinstance(x, dict)]


def _finding_text(item: dict) -> str:
    return ' '.join(_text(item.get(k), 400) for k in ('component', 'title', 'detail', 'reason', 'message')).lower()


def _has_problem(findings: Iterable[dict], *tokens: str) -> bool:
    for item in findings:
        sev = _text(item.get('severity') or item.get('level'), 32).upper()
        if sev not in {'ATTENTION', 'ELEVATED', 'WARNING', 'WARN', 'CRITICAL', 'ERROR'}:
            continue
        text = _finding_text(item)
        if any(token.lower() in text for token in tokens):
            return True
    return False


def _device_label(inventory: dict) -> str:
    device = inventory.get('device') if isinstance(inventory.get('device'), dict) else {}
    return _text(device.get('display_model') or device.get('support_target') or device.get('model'), 180) or 'equipo detectado'


def build_action_plans(diagnostic: dict, telemetry: dict, disks: list, inventory: dict, *, year: int | None = None) -> list[dict]:
    year = int(year or datetime.now().year)
    policy = _baseline(year)
    findings = _findings(diagnostic)
    plans: list[dict] = []
    device_label = _device_label(inventory)

    def add(plan: dict):
        if not any((x.get('component_type'), x.get('title')) == (plan.get('component_type'), plan.get('title')) for x in plans):
            plans.append(plan)

    # Temperatura/throttling: sólo si CorePulse ya lo marcó como problema.
    if _has_problem(findings, 'cpu', 'procesador') and _has_problem(findings, 'temperatura', 'térmic', 'termic', 'throttl'):
        add({
            'severity': 'WARNING', 'component_type': 'CPU', 'title': 'Revisión térmica de CPU',
            'priority_level': 'RECOMENDADO',
            'summary': 'CorePulse detectó evidencia térmica de CPU que merece revisión; la IA no creó esta alerta.',
            'actions': ['Repetir una medición bajo carga para confirmar persistencia.', 'Revisar y limpiar entradas/salidas de aire y ventiladores.', 'Si la condición persiste, realizar mantenimiento térmico siguiendo un tutorial específico del equipo.', 'Volver a ejecutar el diagnóstico después del mantenimiento.'],
            'supplies': ['Juego de destornilladores de precisión', 'Aire comprimido o brocha antiestática', 'Alcohol isopropílico 90%+ y paño sin pelusa', 'Pasta térmica compatible'],
            'precautions': ['Apagar y desconectar el equipo antes de abrirlo.', 'Desconectar batería interna si el procedimiento del modelo lo indica.', 'No sustituir thermal pads sin espesor confirmado para ese modelo.'],
            'tutorial_request': {'intent': 'thermal_service_cpu', 'target': device_label, 'component': _text((inventory.get('cpu') or {}).get('name'), 160)},
        })

    if _has_problem(findings, 'gpu', 'gráfica', 'grafica') and _has_problem(findings, 'temperatura', 'térmic', 'termic', 'throttl'):
        add({
            'severity': 'WARNING', 'component_type': 'GPU', 'title': 'Revisión térmica de GPU',
            'priority_level': 'RECOMENDADO',
            'summary': 'CorePulse detectó evidencia térmica de GPU que merece revisión; la recomendación se basa en el diagnóstico real.',
            'actions': ['Confirmar la lectura bajo carga real.', 'Limpiar rejillas, ventiladores y disipación accesible.', 'Si persiste, seguir un procedimiento específico del modelo para mantenimiento térmico.', 'Repetir benchmark/estrés y comparar temperaturas.'],
            'supplies': ['Juego de destornilladores de precisión', 'Aire comprimido o brocha antiestática', 'Alcohol isopropílico 90%+ y paño sin pelusa', 'Pasta térmica; thermal pads sólo con medida verificada'],
            'precautions': ['Apagar y desconectar el equipo.', 'No usar un tutorial de otro chasis aunque comparta GPU.', 'No cambiar espesores de pads por estimación.'],
            'tutorial_request': {'intent': 'thermal_service_gpu', 'target': device_label, 'component': _text(((inventory.get('gpus') or [{}])[0] or {}).get('name'), 160)},
        })

    ram = inventory.get('ram') if isinstance(inventory.get('ram'), dict) else {}
    ram_total = _num(ram.get('total_gb') or telemetry.get('ram_total_gb'))
    ram_usage = _num(telemetry.get('ram_usage'))
    if ram_usage is not None and ram_usage >= 85:
        add({
            'severity': 'ATTENTION', 'component_type': 'RAM', 'title': 'Uso alto de memoria',
            'priority_level': 'OBSERVAR',
            'summary': f'La muestra actual usa {ram_usage:.0f}% de RAM. Esto no demuestra una falla física, pero reduce el margen disponible.',
            'actions': ['Cerrar tareas que ya no se estén utilizando.', 'Si el uso alto persiste sin una carga esperada, ejecutar CorePulse > Limpieza de sistema > Liberar RAM Segura.', 'Volver a medir antes de concluir que falta capacidad física.'],
            'supplies': [],
            'precautions': ['Liberar RAM no reemplaza una ampliación cuando la capacidad instalada es insuficiente.', 'No finalizar procesos críticos de Windows manualmente.'],
            'corepulse_action': {'id': 'cleanup_ram', 'label': 'Liberar RAM Segura'},
        })

    if ram_total is not None and ram_total < policy['ram_standard_gb']:
        memory_type = ', '.join(str(x) for x in list(ram.get('memory_types') or [])[:2]) or 'tipo N/A'
        form = _text(((ram.get('modules') or [{}])[0] or {}).get('form_factor'), 40) if ram.get('modules') else ''
        compatibility = ' '.join(x for x in (memory_type, form) if x).strip()
        slots = ram.get('slots_available')
        slot_note = f' CorePulse detecta {slots} ranura(s) disponible(s).' if isinstance(slots, int) else ''
        add({
            'severity': 'ATTENTION', 'component_type': 'RAM', 'title': f'Ampliación de RAM para {year}',
            'priority_level': 'MEJORA RECOMENDADA',
            'summary': f'El equipo tiene {ram_total:.0f} GB y la política CorePulse {policy["policy_window"]} usa {policy["ram_standard_gb"]} GB como estándar general/gaming.{slot_note}',
            'actions': [f'Verificar capacidad máxima admitida por {device_label}.', f'Comprar memoria compatible con el tipo detectado ({compatibility or "N/A"}); no asumir compatibilidad si el dato falta.', f'Objetivo recomendado: al menos {policy["ram_standard_gb"]} GB totales; {policy["ram_optimal_gb"]} GB para mayor margen.', 'Instalar siguiendo un tutorial específico del modelo y comprobar que Windows reconoce toda la capacidad.'],
            'supplies': ['Módulo(s) RAM compatibles con el equipo', 'Destornillador de precisión si el chasis lo requiere', 'Superficie limpia y medidas antiestáticas'],
            'precautions': ['No comprar RAM sólo por frecuencia: tipo, formato y compatibilidad del equipo deben coincidir.', 'Desconectar alimentación/batería según el procedimiento exacto del modelo.'],
            'tutorial_request': {'intent': 'ram_upgrade', 'target': device_label, 'component': compatibility},
        })

    storage = inventory.get('storage') if isinstance(inventory.get('storage'), list) else []
    disk = storage[0] if storage and isinstance(storage[0], dict) else {}
    disk_capacity = _num(disk.get('total_space_gb'))
    disk_health = _num(disk.get('health_percent'))
    used_percent = None
    if disks and isinstance(disks[0], dict):
        used_percent = _num(disks[0].get('used_percent'))
        if disk_health is None:
            disk_health = _num(_first_not_none(disks[0].get('health'), disks[0].get('health_percent')))
    if disk_health is not None and disk_health < 80:
        add({
            'severity': 'WARNING', 'component_type': 'ALMACENAMIENTO', 'title': 'SSD con salud reducida',
            'priority_level': 'PRIORITARIO',
            'summary': f'La salud SMART reportada es {disk_health:.0f}%. CorePulse recomienda proteger los datos y preparar un reemplazo compatible.',
            'actions': ['Realizar copia de seguridad de datos importantes.', 'Verificar interfaz y formato físico compatibles con el equipo.', 'Seleccionar un SSD de reemplazo compatible y decidir entre instalación limpia o clonación.', 'Instalar siguiendo un tutorial específico del modelo y volver a comprobar SMART.'],
            'supplies': ['SSD compatible verificado para el equipo', 'Destornillador de precisión', 'Adaptador/carcasa de clonación sólo si se migrarán datos', 'Copia de seguridad externa'],
            'precautions': ['No clonar desde una unidad inestable sin copia previa de datos críticos.', 'No asumir M.2/SATA/NVMe si CorePulse no pudo verificar la interfaz.'],
            'tutorial_request': {'intent': 'ssd_replace', 'target': device_label, 'component': _text(disk.get('model'), 140)},
        })
    elif disk_capacity is not None and disk_capacity < policy['storage_standard_gb']:
        add({
            'severity': 'ATTENTION', 'component_type': 'ALMACENAMIENTO', 'title': f'Ampliación de almacenamiento para {year}',
            'priority_level': 'MEJORA RECOMENDADA',
            'summary': f'La capacidad detectada ({disk_capacity:.0f} GB) queda por debajo del estándar CorePulse de {policy["storage_standard_gb"]} GB para {year}.',
            'actions': ['Verificar qué interfaz y formato de SSD admite el equipo.', f'Considerar al menos {policy["storage_standard_gb"]} GB; {policy["storage_optimal_gb"]} GB ofrece mayor margen para juegos y aplicaciones.', 'Si se reemplaza la unidad actual, preparar copia de seguridad o clonación.', 'Instalar con un tutorial específico del modelo.'],
            'supplies': ['SSD compatible verificado para el equipo', 'Destornillador de precisión', 'Adaptador/carcasa sólo si se requiere clonación'],
            'precautions': ['No comprar una unidad sólo por capacidad; confirmar interfaz, formato y ranura.', 'Respaldar datos antes de intervenir el almacenamiento.'],
            'tutorial_request': {'intent': 'ssd_upgrade', 'target': device_label, 'component': _text(disk.get('model'), 140)},
        })
    elif used_percent is not None and used_percent >= 90:
        add({
            'severity': 'ATTENTION', 'component_type': 'ALMACENAMIENTO', 'title': 'Espacio libre reducido',
            'priority_level': 'OBSERVAR',
            'summary': f'La unidad está aproximadamente {used_percent:.0f}% ocupada. Conviene liberar espacio antes de decidir una ampliación.',
            'actions': ['Ejecutar Limpieza de sistema de CorePulse.', 'Revisar archivos grandes y aplicaciones que ya no se utilicen.', 'Volver a medir el espacio libre; ampliar sólo si la capacidad sigue siendo insuficiente para el uso real.'],
            'supplies': [], 'precautions': ['No borrar archivos personales automáticamente.'],
            'corepulse_action': {'id': 'cleanup_storage', 'label': 'Limpieza de sistema'},
        })

    return plans[:12]


def build_deterministic_assessment(diagnostic: dict, telemetry: dict, disks: list, inventory: dict, *, year: int | None = None) -> dict:
    year = int(year or datetime.now().year)
    relevance = evaluate_hardware_relevance(inventory, year=year)
    actions = build_action_plans(diagnostic, telemetry, disks, inventory, year=year)
    attention = []
    for action in actions:
        comp = _text(action.get('component_type'), 40)
        if comp and comp not in attention:
            attention.append(comp)
    return {
        'current_year': year,
        'baseline': _baseline(year),
        'hardware_relevance': relevance,
        'problem_recommendations': actions,
        'attention_areas': attention,
        'policy': POLICY,
    }


__all__ = [
    'POLICY', 'collect_ai_inventory', 'evaluate_hardware_relevance',
    'build_action_plans', 'build_deterministic_assessment',
]
