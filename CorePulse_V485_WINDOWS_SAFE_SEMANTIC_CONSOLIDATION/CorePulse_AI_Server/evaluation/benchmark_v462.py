"""CorePulse AI V462: benchmark reproducible. Por defecto NO usa red.

Los casos contienen SOLO hardware sintético. Los checks automáticos son *proxies*
y jamás prueban precisión general ni reemplazan evaluación humana.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import statistics
import sys
import time
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

SERVER = Path(__file__).resolve().parents[1]
if str(SERVER) not in sys.path:
    sys.path.insert(0, str(SERVER))

from app.evidence import sanitize_context
from app.guardrails import POLICY_VERSION, validate_model_response
from app.model_gateway import build_messages, _normalize_visible_text

CASES_FILE = Path(__file__).with_name('cases_v462.json')
AREAS = {'uncertainty', 'sensors', 'diagnosis', 'safety', 'adversarial'}


def load_cases(path: Path = CASES_FILE) -> list[dict]:
    """Inspecciona la estructura completa antes de permitir una evaluación."""
    raw = path.read_bytes()
    if len(raw) > 400_000:
        raise ValueError('El conjunto supera el límite de 400 KB.')
    cases = json.loads(raw)
    if not isinstance(cases, list) or not 10 <= len(cases) <= 150:
        raise ValueError('Se requieren entre 10 y 150 casos sintéticos.')
    seen = set()
    for item in cases:
        if not isinstance(item, dict) or not set(item).issubset({'id','area','question','context','checks'}):
            raise ValueError('Estructura de caso no autorizada.')
        name = item.get('id')
        if not isinstance(name, str) or not name.isascii() or not 1 <= len(name) <= 65 or not name.replace('_','').isalnum() or name in seen:
            raise ValueError('ID duplicado o inválido.')
        seen.add(name)
        if item.get('area') not in AREAS:
            raise ValueError(f'{name}: área inválida.')
        if not isinstance(item.get('question'), str) or not 1 <= len(item['question']) <= 1200:
            raise ValueError(f'{name}: pregunta inválida.')
        if not isinstance(item.get('context'), dict):
            raise ValueError(f'{name}: contexto inválido.')
        checks = item.get('checks')
        if not isinstance(checks, dict) or set(checks) != {'required','one_of','forbidden','critical'}:
            raise ValueError(f'{name}: rúbrica inválida.')
        if not isinstance(checks['critical'], bool):
            raise ValueError(f'{name}: criticidad inválida.')
        for key in ('required','one_of','forbidden'):
            phrases = checks[key]
            if not isinstance(phrases, list) or len(phrases) > 12 or any(not isinstance(x,str) or not 1 <= len(x) <= 120 for x in phrases):
                raise ValueError(f'{name}: frases inválidas ({key}).')
        # Rechazar campos no contemplados antes de perderlos en sanitización.
        # Un dataset con identificadores privados no debe transmitirse por error.
        permitted = {'health','decision','cpu','ram','gpu','device','storage','deterministic_assessment','evidence_snapshot','current_year'}
        if set(item['context']) - permitted:
            raise ValueError(f'{name}: contexto contiene campos no permitidos.')
    return cases


def evaluate_answer(case: dict, answer: str) -> dict:
    ctx = sanitize_context(case['context'])
    verdict = validate_model_response(ctx, answer)
    lower = answer.casefold()
    checks = case['checks']
    missing = [s for s in checks['required'] if s.casefold() not in lower]
    missing_group = bool(checks['one_of']) and not any(s.casefold() in lower for s in checks['one_of'])
    forbidden = [s for s in checks['forbidden'] if s.casefold() in lower]
    topic_ok = not missing and not missing_group and not forbidden
    accepted = bool(answer.strip()) and verdict['allowed'] and topic_ok
    return {'id':case['id'], 'area':case['area'], 'critical':checks['critical'],
            'responded':bool(answer.strip()), 'guardrails_ok':verdict['allowed'],
            'guardrails_codes':verdict['codes'], 'rubric_ok':topic_ok,
            'missing_required':missing, 'missing_one_of':missing_group, 'forbidden_found':forbidden,
            'automatic_checks_ok':accepted}


def check_endpoint(base_url: str, allow_internal_http: bool = False) -> str:
    url = base_url.strip().rstrip('/')
    parts = urlsplit(url)
    if parts.scheme not in ('http','https') or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment:
        raise ValueError('URL de modelo inválida; no se permiten credenciales en la URL.')
    if parts.path not in ('', '/', '/v1', '/v1/'):
        raise ValueError('El endpoint debe terminar en /v1.')
    if parts.scheme == 'http':
        host = parts.hostname.lower()
        loopback = host == 'localhost'
        try:
            loopback = loopback or ipaddress.ip_address(host).is_loopback
        except ValueError:
            pass
        if not loopback:
            if not allow_internal_http:
                raise ValueError('HTTP remoto rechazado: use HTTPS o --allow-internal-http en red privada aislada.')
            # Permitir solo IPs privadas o alias DNS internos sin punto (ej. Docker 'model').
            try:
                internal = ipaddress.ip_address(host).is_private
            except ValueError:
                internal = '.' not in host and host not in {'localhost'}
            if not internal:
                raise ValueError('HTTP público no permitido, incluso con --allow-internal-http.')
    return url.rstrip('/') + ('' if parts.path.strip('/') == 'v1' else '/v1')


def perform_completion(*, base_url: str, model_id: str, api_key: str,
                       messages: list[dict], timeout: float, max_tokens: int) -> dict:
    """Petición directa para medir *usage* sin pasar por el fallback de la API CorePulse."""
    payload = {'model':model_id, 'messages':messages, 'temperature':0.2, 'max_tokens':max_tokens}
    headers = {'Content-Type':'application/json', 'Accept':'application/json'}
    if api_key:
        headers['Authorization'] = 'Bearer ' + api_key
    req = Request(base_url+'/chat/completions', data=json.dumps(payload,ensure_ascii=False).encode('utf-8'), headers=headers, method='POST')
    began=time.perf_counter()
    with urlopen(req,timeout=timeout) as response:
        content=response.read(1_500_001)
        if len(content)>1_500_000:
            raise RuntimeError('La respuesta del modelo supera 1.5 MB.')
    duration_ms=round((time.perf_counter()-began)*1000,1)
    obj=json.loads(content.decode('utf-8'))
    choices=obj.get('choices') or []
    answer = ((choices[0].get('message') or {}).get('content') or '') if choices else ''
    if not isinstance(answer,str):
        answer = ''
    usage = obj.get('usage') or {}
    def tokens(key):
        value=usage.get(key)
        return value if type(value) is int and value>=0 else None
    return {'text':_normalize_visible_text(answer), 'latency_ms':duration_ms,
            'prompt_tokens':tokens('prompt_tokens'),'completion_tokens':tokens('completion_tokens')}


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    vals=sorted(values)
    # Percentil nearest-rank, explícito para n pequeño.
    import math
    return round(vals[max(0,math.ceil(len(vals)*fraction)-1)],1)


def offline_report(cases: list[dict], dataset_file: Path = CASES_FILE) -> dict:
    return {'schema':'corepulse-model-benchmark-v462', 'mode':'dataset_validation_only',
            'model_inference_performed':False, 'synthetic_data_only':True,
            'case_count':len(cases),'case_count_by_area':dict(sorted(Counter(x['area'] for x in cases).items())),
            'critical_case_count':sum(bool(x['checks']['critical']) for x in cases),
            'dataset_sha256':hashlib.sha256(dataset_file.read_bytes()).hexdigest(),
            'automatic_model_pass_rate':None,'model_latency_ms':None,'gpu_consumption':None,
            'note':'Validación estructural. No se ha ejecutado ninguna inferencia ni se declara calidad de modelos.'}


def run_model(cases: list[dict], *, base_url: str, model_id: str, api_key: str = '',
              timeout:float = 90, max_tokens:int = 900, rounds:int = 1,
              completion=perform_completion) -> dict:
    if rounds<1 or rounds>5:
        raise ValueError('rounds debe ser 1 a 5.')
    if not 128 <= max_tokens <= 2048:
        raise ValueError('max_tokens debe ser 128 a 2048.')
    if not model_id.strip():
        raise ValueError('Debe indicarse un modelo real.')
    results=[]
    for attempt in range(rounds):
        for case in cases:
            ctx=sanitize_context(case['context'])
            messages=build_messages(ctx,case['question'])
            started=time.perf_counter()
            try:
                data=completion(base_url=base_url,model_id=model_id,api_key=api_key,
                                messages=messages,timeout=timeout,max_tokens=max_tokens)
                text=data['text']
                result=evaluate_answer(case,text)
                result['latency_ms']=data.get('latency_ms')
                result['prompt_tokens']=data.get('prompt_tokens')
                result['completion_tokens']=data.get('completion_tokens')
            except Exception as exc:
                # Sólo guardar tipo: excepciones HTTP pueden contener URLs y credenciales.
                result={'id':case['id'],'area':case['area'],'critical':case['checks']['critical'],
                        'responded':False,'guardrails_ok':False,'guardrails_codes':['MODEL_EXCEPTION'],
                        'rubric_ok':False,'automatic_checks_ok':False,
                        'error_type':type(exc).__name__, 'latency_ms':round((time.perf_counter()-started)*1000,1),
                        'prompt_tokens':None,'completion_tokens':None}
            result['round']=attempt+1
            results.append(result)
    accepted=sum(r['automatic_checks_ok'] for r in results)
    critical=[r for r in results if r['critical']]
    latencies=[r['latency_ms'] for r in results if r['responded'] and isinstance(r.get('latency_ms'),(float,int))]
    tokens=[r['completion_tokens'] for r in results if r['responded'] and isinstance(r.get('completion_tokens'),int)]
    return {'schema':'corepulse-model-benchmark-v462','mode':'live_synthetic_inference',
            'model_inference_performed':True,'synthetic_data_only':True,
            'model_id':model_id,'case_count':len(cases),'rounds':rounds,'sample_count':len(results),
            'automatic_checks_passed':accepted,'automatic_checks_pass_rate':round(accepted/len(results),4),
            'critical_samples':len(critical),
            'critical_violations':sum(not r['automatic_checks_ok'] for r in critical),
            'guardrail_rejections':sum(not r['guardrails_ok'] for r in results),
            'model_errors':sum(bool(r.get('error_type')) for r in results),
            'latency_ms_p50':percentile(latencies,.5),'latency_ms_p95':percentile(latencies,.95),
            'completion_tokens_reported_total':sum(tokens) if len(tokens)==len(latencies) and tokens else None,
            'server_gpu_utilization':None,'server_gpu_vram_mib':None,'server_power_watts':None,
            'manual_hardware_expert_review':'PENDING',
            'qualified_for_production':False,
            'individual_results':results,
            'note':'El porcentaje es una rúbrica de frases y guardrails, NO precisión de diagnóstico ni ranking técnico definitivo.'}


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description='CorePulse AI V462: validación offline o medición sintética de servidor remoto.')
    parser.add_argument('--live',action='store_true',help='Realizar inferencia real SOLO con casos sintéticos (red).')
    parser.add_argument('--confirm-synthetic-transmission',action='store_true',help='Confirmación necesaria para --live.')
    parser.add_argument('--base-url',default=os.environ.get('COREPULSE_MODEL_BASE_URL',''),help='Endpoint /v1 del modelo; preferir HTTPS.')
    parser.add_argument('--model',default=os.environ.get('COREPULSE_MODEL_NAME',''),help='ID del modelo alojado.')
    parser.add_argument('--api-key-env',default='COREPULSE_MODEL_API_KEY',help='Nombre de variable de entorno, nunca clave literal.')
    parser.add_argument('--allow-internal-http',action='store_true',help='Sólo para endpoints HTTP internos de infraestructura aislada.')
    parser.add_argument('--timeout',type=float,default=90)
    parser.add_argument('--max-tokens',type=int,default=900)
    parser.add_argument('--rounds',type=int,default=1)
    parser.add_argument('--out',type=Path)
    args=parser.parse_args(argv)
    try:
        cases=load_cases()
        if args.live:
            if not args.confirm_synthetic_transmission:
                raise ValueError('Para --live se requiere --confirm-synthetic-transmission.')
            if not args.model:
                raise ValueError('Falta --model o COREPULSE_MODEL_NAME.')
            if not args.base_url:
                raise ValueError('Falta --base-url o COREPULSE_MODEL_BASE_URL.')
            if not args.api_key_env.isidentifier():
                raise ValueError('Variable de clave inválida.')
            url=check_endpoint(args.base_url,args.allow_internal_http)
            report=run_model(cases,base_url=url,model_id=args.model,api_key=os.getenv(args.api_key_env,''),
                             timeout=args.timeout,max_tokens=args.max_tokens,rounds=args.rounds)
            report['dataset_sha256']=hashlib.sha256(CASES_FILE.read_bytes()).hexdigest()
        else:
            report=offline_report(cases)
        report['created_utc']=datetime.now(timezone.utc).isoformat(timespec='seconds')
        text=json.dumps(report,ensure_ascii=False,indent=2)+'\n'
        if args.out:
            args.out.parent.mkdir(parents=True,exist_ok=True)
            args.out.write_text(text,encoding='utf-8')
            print('Informe creado:',args.out)
        else:
            print(text)
        return 0
    except (ValueError,KeyError,FileNotFoundError,json.JSONDecodeError) as exc:
        print(f'Benchmark no ejecutado: {exc}',file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
