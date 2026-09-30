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
from core.version import VERSION_LABEL as VERSION

POLICY = 'AI_INTERPRETS_REAL_EVIDENCE_ONLY'
MODEL_PRIORITY = ('COREPULSE_AI_BACKEND',)


def _text(value: Any, default: str='') -> str:
    return default if value is None else str(value).strip()


def _safe_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _sanitized_inventory(telemetry: Dict[str, Any], disks: List[Dict[str, Any]]) -> Dict[str, Any]:
    telemetry = telemetry if isinstance(telemetry, dict) else {}
    disks = disks if isinstance(disks, list) else []
    components = []
    cpu = _text(telemetry.get('cpu_name'))
    gpu = _text(telemetry.get('gpu_name'))
    if cpu:
        components.append({'id':'CPU','type':'CPU','name':cpu,'facts':{}})
    total = telemetry.get('ram_total_gb')
    components.append({'id':'RAM','type':'RAM','name':f'{float(total):.2f} GB RAM' if isinstance(total,(int,float)) else 'RAM','facts':{'total_gb': total if isinstance(total,(int,float)) else None}})
    if gpu:
        components.append({'id':'GPU:0','type':'GPU','name':gpu,'facts':{'vram_gb': telemetry.get('gpu_vram_gb')}})
    for idx, disk in enumerate(disks[:8]):
        if not isinstance(disk, dict):
            continue
        name = _text(disk.get('model') or disk.get('name'), f'Unidad {idx+1}')
        components.append({'id':f'STORAGE:{idx}','type':'STORAGE','name':name,'facts':{'capacity_gb': disk.get('size_gb') or disk.get('total_gb')}})
    return {'captured_at': time.time(), 'device': {'form_factor':'UNKNOWN','manufacturer':'N/A','model':'N/A','display_model':'N/A','support_target':'N/A','motherboard':'N/A'}, 'components': components, 'policy':'REAL_OS_IDENTITY_SANITIZED_NO_SERIALS'}


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
    del api_key, model  # V331: el cliente ya no administra proveedores ni claves.
    year = datetime.now().year
    telemetry = telemetry if isinstance(telemetry, dict) else {}
    disks = disks if isinstance(disks, list) else []
    diagnostic_result = diagnostic_result if isinstance(diagnostic_result, dict) else {}
    inventory = _sanitized_inventory(telemetry, disks)
    diagnostic = _diagnostic_digest(diagnostic_result)
    problems = _problem_cases(diagnostic_result, inventory)
    health = {
        'score': diagnostic_result.get('score'),
        'status': diagnostic_result.get('status'),
        'severity': diagnostic_result.get('severity'),
        'reasons': [x.get('reason') or x.get('title') for x in problems if isinstance(x, dict)],
    }
    context = build_runtime_context(telemetry, disks, health)
    question = 'Resume este diagnóstico para el informe técnico. Explica sólo la evidencia real y no inventes causas ni mediciones.'
    result = analyze_context(context, question=question)
    if not result.get('ok'):
        out = _fallback_result(inventory, _text(result.get('error'), 'CorePulse AI no disponible.'), year=year)
        out.update({'diagnostic':diagnostic,'detected_problems':problems,'generated_at':time.time()})
        return out
    mode = _text(result.get('mode'))
    status = 'OK' if mode == 'model' else 'PARTIAL'
    limitations = [] if status == 'OK' else ['El servidor respondió mediante CorePulse Evidence Engine porque el modelo generativo no está configurado o no respondió.']
    return {
        'version': VERSION, 'status': status, 'provider':'COREPULSE_AI',
        'model':'CorePulse AI' if status == 'OK' else 'CorePulse Evidence Engine',
        'available_models':[], 'current_year':year,
        'executive_summary':_text(result.get('text')),
        'hardware_relevance':[], 'problem_recommendations':[], 'recommendations':[],
        'limitations':limitations,
        'research':{'status':'NOT_CONFIGURED','capability':'BACKEND_ONLY','sources':[],'source_count':0,'reason':'V331 usa el backend propio de CorePulse AI; la investigación web del reporte no se ejecuta desde el cliente.'},
        'policy':{'evidence_only':True,'no_sensor_fabrication':True,'technical_pdf_survives_ai_failure':True,'backend_owned_by_corepulse':True},
        'inventory':inventory,'diagnostic':diagnostic,'detected_problems':problems,
        'model_attempts':[{'model':'COREPULSE_AI_BACKEND','mode':mode,'status':status}],
        'generated_at':time.time(),
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
