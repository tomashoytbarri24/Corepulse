"""V475 · CorePulse Intelligence Engine: razonamiento determinista sobre evidencia.

Sin red, inferencia LLM, escritura en Windows ni umbrales térmicos nuevos.
Las clasificaciones de diagnóstico sólo provienen de CorePulse; las hipótesis
son posibilidades no confirmadas y jamás órdenes de actuación.
"""
from __future__ import annotations

import math
import re
import unicodedata
from typing import Any
from .investigation_engine import investigate_timeline, timeline_brief

ENGINE_VERSION = '476.0'


def _n(value: Any, minimum: float = 0, maximum: float = float('inf')) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (ValueError, TypeError, OverflowError):
        return None
    return number if math.isfinite(number) and minimum <= number <= maximum else None


def _norm(value: Any) -> str:
    text = unicodedata.normalize('NFKD', str(value or '').lower())
    return ''.join(c for c in text if unicodedata.category(c) != 'Mn')


def is_diagnostic_request(question: str, task: str = 'chat') -> bool:
    if task == 'analysis':
        return True
    q = _norm(question)
    return bool(re.search(
        r'\b(?:diagnostic\w*|analiz\w*|analisis|investig\w*|averigu\w*|que falla|que problema|'
        r'por que se apaga|por que se cierra|causa del problema|que debo mejorar|'
        r'que necesita atencion|que esta fallando|como ha cambiado|compar\w*|evolucion|tendencia\w*)\b', q))


def analyze_evidence(ctx: dict) -> dict:
    """Produce conclusiones explicables; acepta SOLO el contexto ya saneado.

    No aprende de la salida del LLM ni usa un porcentaje para generar alertas
    térmicas/SMART por su cuenta. La falta de historial deja las causas abiertas.
    """
    ctx = ctx if isinstance(ctx, dict) else {}
    cpu = ctx.get('cpu') if isinstance(ctx.get('cpu'), dict) else {}
    gpu = ctx.get('gpu') if isinstance(ctx.get('gpu'), dict) else {}
    ram = ctx.get('ram') if isinstance(ctx.get('ram'), dict) else {}
    decision = ctx.get('decision') if isinstance(ctx.get('decision'), dict) else {}
    assessment = ctx.get('deterministic_assessment') if isinstance(ctx.get('deterministic_assessment'), dict) else {}
    storage = ctx.get('storage') if isinstance(ctx.get('storage'), list) else []
    observations: list[dict] = []
    missing: list[str] = []
    findings: list[dict] = []
    def measure(field: str, raw: Any, unit: str, minimum: float = 0, maximum: float = float('inf')):
        num = _n(raw, minimum, maximum)
        if num is None:
            missing.append(field)
        else:
            observations.append({'source': field, 'value': num, 'unit': unit})
        return num

    measure('cpu.temperature_c', cpu.get('temperature_c'), '°C', 0, 130)
    measure('cpu.usage_percent', cpu.get('usage_percent'), '%', 0, 100)
    measure('gpu.temperature_c', gpu.get('temperature_c'), '°C', 0, 130)
    measure('gpu.usage_percent', gpu.get('usage_percent'), '%', 0, 100)
    measure('ram.usage_percent', ram.get('usage_percent'), '%', 0, 100)
    used = measure('ram.used_gb', ram.get('used_gb'), 'GB', 0, 16384)
    total = measure('ram.total_gb', ram.get('total_gb'), 'GB', 0, 16384)
    if used is not None and total is not None and used > total:
        observations[:] = [x for x in observations if x['source'] != 'ram.used_gb']
        missing.append('ram.used_gb')
    for idx, disk in enumerate(storage[:8]):
        if not isinstance(disk, dict):
            continue
        for key, unit, upper in [('used_percent','%',100), ('health_percent','%',100),
                                  ('temperature_c','°C',130)]:
            measure(f'storage[{idx}].{key}', disk.get(key), unit, 0, upper)

    observed = {x['source'] for x in observations}
    thermal = {_norm(x).strip() for x in (decision.get('thermal_alerts') or []) if isinstance(x, str)}
    areas = {_norm(x).strip() for x in (decision.get('attention_areas') or []) if isinstance(x, str)}
    plans = assessment.get('problem_recommendations') or []
    if not isinstance(plans, list):
        plans = []

    def add(code: str, component: str, observation: str, sources: list[str],
            hypothesis: str, verification: str):
        findings.append({'code': code, 'component': component, 'classification': 'ATTENTION_FROM_COREPULSE',
                         'observation': observation, 'evidence_sources': sources,
                         'hypothesis_unconfirmed': hypothesis, 'safe_next_check': verification,
                         'confirmed_hardware_failure': False, 'windows_action_performed': False})

    for component in ('cpu', 'gpu'):
        if component in thermal:
            src = f'{component}.temperature_c'
            evidence = ['decision.thermal_alerts'] + ([src] if src in observed else [])
            add(f'{component.upper()}_THERMAL_REPORTED', component.upper(),
                f'CorePulse ha marcado una alerta térmica de {component.upper()}.' +
                (' Lectura térmica actual presente.' if src in observed else ' Temperatura actual N/A.'),
                evidence, 'La refrigeración o la carga podrían estar relacionadas; no hay causa física confirmada.',
                'Comparar varias muestras reales de temperatura, carga y ventilación; revisar alertas y registros antes de intervenir.')

    ram_state = _norm(decision.get('ram_usage_state'))
    if ram_state in {'high_usage', 'elevated_usage'}:
        sources = ['decision.ram_usage_state']
        if 'ram.usage_percent' in observed:
            sources.append('ram.usage_percent')
        add('RAM_PRESSURE', 'RAM', 'CorePulse reporta presión de uso de memoria, no una avería física.',
            sources, 'Podrían intervenir procesos o aplicaciones demandantes; no está comprobado cuál.',
            'Revisar procesos de mayor consumo y repetir la lectura durante la carga afectada, sin cerrar procesos automáticamente.')

    covered = {'cpu', 'gpu', 'ram'}
    for area in sorted(areas):
        component = ('ALMACENAMIENTO' if any(k in area for k in ('almacen', 'ssd', 'disco','smart'))
                     else 'CPU' if 'cpu' in area or 'procesador' in area
                     else 'GPU' if 'gpu' in area or 'grafica' in area
                     else 'RAM' if 'ram' in area or 'memoria' in area else None)
        if not component or (component.lower() in covered and any(x['component'] == component for x in findings)):
            continue
        if component.lower() == 'almacenamiento':
            evidence = ['decision.attention_areas'] + [x['source'] for x in observations if x['source'].startswith('storage[')][:3]
            add('STORAGE_ATTENTION', component, 'CorePulse señala almacenamiento como área de atención; ocupación y salud SMART son mediciones diferentes.',
                evidence, 'Puede tratarse de capacidad, rendimiento o salud, pero no hay causa confirmada.',
                'Revisar capacidad libre y estado SMART real por separado; respaldar archivos antes de intervenir.')
        else:
            add(f'{component}_ATTENTION', component,
                f'CorePulse señala {component} como área de atención, sin confirmar la causa.',
                ['decision.attention_areas'], 'Se necesitan más mediciones para formular una causa probable.',
                'Repetir mediciones reales durante el problema y consultar el diagnóstico completo de CorePulse.')

    # Anclar los planes previamente evaluados, sin recrear su clasificación ni convertir
    # su contenido en cambios ejecutables. Solo fuentes, códigos y límites; no URLs.
    for idx, plan in enumerate(plans[:10]):
        if isinstance(plan, dict) and plan.get('title'):
            findings.append({'code': 'COREPULSE_PLAN', 'component': str(plan.get('component_type') or 'N/A')[:48],
                             'classification': 'COREPULSE_RECOMMENDATION',
                             'observation': str(plan['title'])[:140],
                             'evidence_sources': [f'deterministic_assessment.problem_recommendations[{idx}]'],
                             'hypothesis_unconfirmed': 'Un plan de acción no prueba por sí solo la causa física.',
                             'safe_next_check': 'Consultar las precauciones y la evidencia del plan original antes de actuar.',
                             'confirmed_hardware_failure': False, 'windows_action_performed': False})

    snapshot = ctx.get('evidence_snapshot') if isinstance(ctx.get('evidence_snapshot'), dict) else {}
    return {'engine_version': ENGINE_VERSION, 'policy': 'REAL_OR_NA',
            'source': 'COREPULSE_SANITIZED_SNAPSHOT', 'captured_at_utc': snapshot.get('captured_at_utc'),
            'freshness_verified_by_engine': False,
            'observations': observations[:40], 'missing': sorted(set(missing))[:40],
            'timeline': investigate_timeline(ctx),
            'findings': findings[:18], 'finding_count': len(findings),
            'no_alerts_reported': not findings,
            'limitations': [
                'Las alertas dependen de la clasificación determinista de CorePulse; no se inventan umbrales.',
                'Una muestra aislada no confirma causas ni daños físicos.',
                'La frescura del sensor debe validarse en el origen; este motor no la certifica.',
                'No mide FPS ni realiza acciones sobre Windows.'
            ]}


def format_diagnostic_brief(report: dict) -> str:
    lines = ['Diagnóstico técnico CorePulse (evidencia disponible):']
    findings = report.get('findings') or []
    if findings:
        for finding in findings[:5]:
            lines.append('• ' + finding['observation'])
            lines.append('  Siguiente comprobación: ' + finding['safe_next_check'])
    else:
        lines.append('No hay alertas declaradas por CorePulse en esta muestra. Esto no demuestra que el equipo esté libre de fallas.')
    metrics = report.get('observations') or []
    if metrics:
        shown = []
        for row in metrics[:8]:
            val = row['value']
            shown.append(f"{row['source']}: {val:g} {row['unit']}")
        lines.append('Lecturas observadas: ' + ' | '.join(shown) + '.')
    lines.append(timeline_brief(report.get('timeline') or {}))
    missing = report.get('missing') or []
    if missing:
        lines.append('Sin lectura válida (N/A): ' + ', '.join(missing[:8]) + '.')
    lines.append('Las causas no están confirmadas; para investigarlas hay que repetir mediciones y comprobar los registros pertinentes. No se ha modificado Windows.')
    return '\n'.join(lines)
