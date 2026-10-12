"""Interpretación IA del diagnóstico mediante el backend propio de CorePulse AI.

La telemetría y la clasificación técnica siguen siendo autoridad de CorePulse.
Este módulo conserva el contrato esperado por el generador PDF sin depender de
SDKs ni claves de proveedores en el PC del usuario.
"""
from __future__ import annotations

from datetime import datetime
import time
from typing import Any, Dict, Iterable, List, Optional

from core.ai_client import build_runtime_context, analyze_context
from core.ai_action_intelligence import collect_ai_inventory, build_deterministic_assessment
from core.tutorial_research import enrich_plans_with_tutorials
from core.version import VERSION_LABEL as VERSION

POLICY = 'AI_INTERPRETS_REAL_EVIDENCE_ONLY'
MODEL_PRIORITY = ('COREPULSE_AI_BACKEND',)


def _text(value: Any, default: str='') -> str:
    return default if value is None else str(value).strip()


def _safe_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _sanitized_inventory(telemetry: Dict[str, Any], disks: List[Dict[str, Any]]) -> Dict[str, Any]:
    return collect_ai_inventory(telemetry if isinstance(telemetry, dict) else {}, disks if isinstance(disks, list) else [])


def _diagnostic_digest(diagnostic: Dict[str, Any]) -> Dict[str, Any]:
    diagnostic = diagnostic if isinstance(diagnostic, dict) else {}
    findings = []
    for item in _safe_list(diagnostic.get('findings'))[:20]:
        if isinstance(item, dict):
            findings.append({
                'severity': _text(item.get('severity') or item.get('level'))[:32],
                'title': _text(item.get('title') or item.get('name'))[:160],
                'detail': _text(item.get('detail') or item.get('reason') or item.get('message'))[:400],
            })
    return {'score': diagnostic.get('score'), 'status': diagnostic.get('status'), 'findings': findings}


def _problem_cases(diagnostic: Dict[str, Any], inventory: Dict[str, Any]) -> List[Dict[str, Any]]:
    out=[]
    for item in _safe_list(diagnostic.get('findings')):
        if not isinstance(item, dict):
            continue
        severity=_text(item.get('severity') or item.get('level')).upper()
        if severity in {'WARNING','CRITICAL','ERROR','ELEVATED'}:
            out.append({'severity':severity,'title':_text(item.get('title') or item.get('name'))[:160],'reason':_text(item.get('detail') or item.get('reason') or item.get('message'))[:400]})
    return out[:12]


def _fallback_result(inventory: Dict[str, Any], reason: str, *, year: int) -> Dict[str, Any]:
    return {
        'version': VERSION, 'status':'UNAVAILABLE', 'provider':'COREPULSE_AI', 'model':None,
        'available_models':[], 'current_year':year,
        'executive_summary':'El informe técnico se generó correctamente, pero CorePulse AI no estuvo disponible.',
        'hardware_relevance':[], 'problem_recommendations':[], 'recommendations':[],
        'limitations':[reason],
        'research':{'status':'UNAVAILABLE','capability':'UNAVAILABLE','sources':[],'source_count':0,'reason':reason},
        'policy':{'evidence_only':True,'no_sensor_fabrication':True,'technical_pdf_survives_ai_failure':True},
        'inventory':inventory,
    }


def analyze_report_with_ai(diagnostic_result: Dict[str, Any], telemetry: Dict[str, Any], disks: List[Dict[str, Any]], *, api_key: Optional[str]=None, model: Optional[str]=None) -> Dict[str, Any]:
    del api_key, model  # El cliente no administra proveedores ni claves.
    year = datetime.now().year
    telemetry = telemetry if isinstance(telemetry, dict) else {}
    disks = disks if isinstance(disks, list) else []
    diagnostic_result = diagnostic_result if isinstance(diagnostic_result, dict) else {}

    inventory = _sanitized_inventory(telemetry, disks)
    diagnostic = _diagnostic_digest(diagnostic_result)
    problems = _problem_cases(diagnostic_result, inventory)

    assessment = build_deterministic_assessment(
        diagnostic_result, telemetry, disks, inventory, year=year,
    )
    raw_plans = list(assessment.get('problem_recommendations') or [])
    try:
        plans = enrich_plans_with_tutorials(raw_plans, inventory, max_lookups=4, allow_network=False)
    except Exception:
        plans = raw_plans
    assessment['problem_recommendations'] = plans

    health = {
        'score': diagnostic_result.get('score'),
        'status': diagnostic_result.get('status') or diagnostic_result.get('overall_status'),
        'severity': diagnostic_result.get('severity'),
        'reasons': [x.get('reason') or x.get('title') for x in problems if isinstance(x, dict)],
    }
    context = build_runtime_context(telemetry, disks, health)
    context['current_year'] = year
    context['device'] = dict(inventory.get('device') or {})
    context['deterministic_assessment'] = assessment

    question = (
        'Resume este diagnóstico para el informe técnico. '
        'Usa la evaluación determinista de CorePulse como autoridad. '
        'Distingue salud técnica de vigencia anual. '
        'Explica las acciones recomendadas sin inventar compatibilidad, fallas ni mediciones.'
    )
    result = analyze_context(context, question=question)

    verified_tutorials = []
    search_fallbacks = []
    for plan in plans:
        tutorial = plan.get('tutorial') if isinstance(plan, dict) and isinstance(plan.get('tutorial'), dict) else {}
        if tutorial.get('status') == 'VERIFIED_EXACT' and str(tutorial.get('url') or '').startswith('https://'):
            verified_tutorials.append({
                'title': tutorial.get('title'), 'url': tutorial.get('url'),
                'query': tutorial.get('query'), 'status': 'VERIFIED_EXACT',
            })
        elif tutorial.get('status') == 'SEARCH_ONLY' and tutorial.get('search_url'):
            search_fallbacks.append({
                'title': None, 'url': tutorial.get('search_url'),
                'query': tutorial.get('query'), 'status': 'SEARCH_ONLY',
            })

    research_status = 'OK' if verified_tutorials and not search_fallbacks else 'PARTIAL' if (verified_tutorials or search_fallbacks) else 'NOT_REQUIRED'
    research = {
        'status': research_status,
        'capability': 'MODEL_SPECIFIC_TUTORIAL_LOOKUP',
        'sources': verified_tutorials,
        'source_count': len(verified_tutorials),
        'search_fallbacks': search_fallbacks,
        'relevance_status': 'PARTIAL',
        'reason': (
            'Los tutoriales directos sólo se publican cuando el modelo del equipo y la intención del procedimiento coinciden con un resultado verificable. '
            'CPU/GPU permanecen NO EVALUABLE para vigencia anual mientras no exista evidencia comparativa externa verificable.'
        ),
    }

    hardware_relevance = list(assessment.get('hardware_relevance') or [])
    recommendations = [
        {
            'component': p.get('component_type'),
            'title': p.get('title'),
            'summary': p.get('summary'),
        }
        for p in plans if isinstance(p, dict)
    ]

    if not result.get('ok'):
        out = _fallback_result(inventory, _text(result.get('error'), 'CorePulse AI no disponible.'), year=year)
        out.update({
            'diagnostic': diagnostic,
            'detected_problems': problems,
            'hardware_relevance': hardware_relevance,
            'problem_recommendations': plans,
            'recommendations': recommendations,
            'research': research,
            'deterministic_assessment': assessment,
            'generated_at': time.time(),
        })
        return out

    mode = _text(result.get('mode'))
    status = 'OK' if mode == 'model' else 'PARTIAL'
    limitations = [] if status == 'OK' else ['El servidor respondió mediante CorePulse Evidence Engine porque el modelo generativo no está configurado o no respondió.']
    if any(x.get('classification') == 'NO_EVALUABLE' for x in hardware_relevance if isinstance(x, dict)):
        limitations.append('La vigencia de CPU/GPU no se completa sin evidencia comparativa verificable; CorePulse prefiere NO EVALUABLE antes que estimar.')

    return {
        'version': VERSION,
        'status': status,
        'provider': 'COREPULSE_AI',
        'model': 'CorePulse AI' if status == 'OK' else 'CorePulse Evidence Engine',
        'available_models': [],
        'current_year': year,
        'executive_summary': _text(result.get('text')),
        'hardware_relevance': hardware_relevance,
        'problem_recommendations': plans,
        'recommendations': recommendations,
        'limitations': limitations,
        'research': research,
        'policy': {
            'evidence_only': True,
            'no_sensor_fabrication': True,
            'technical_pdf_survives_ai_failure': True,
            'backend_owned_by_corepulse': True,
            'deterministic_fault_authority': True,
            'runtime_year': year,
            'viability_independent_from_health': True,
            'exact_tutorial_requires_verified_match': True,
        },
        'inventory': inventory,
        'diagnostic': diagnostic,
        'detected_problems': problems,
        'deterministic_assessment': assessment,
        'model_attempts': [{'model': 'COREPULSE_AI_BACKEND', 'mode': mode, 'status': status}],
        'generated_at': time.time(),
    }


def _select_model(*args, **kwargs):
    return 'COREPULSE_AI_BACKEND'


def _candidate_models(*args, **kwargs):
    return ['COREPULSE_AI_BACKEND']


def _normalize(payload, *args, **kwargs):
    return payload if isinstance(payload, dict) else {}


def _decorate_problem_priority(value, *args, **kwargs):
    return value


__all__ = ['analyze_report_with_ai','_select_model','_candidate_models','_problem_cases','_normalize','_decorate_problem_priority','VERSION','POLICY','MODEL_PRIORITY']
