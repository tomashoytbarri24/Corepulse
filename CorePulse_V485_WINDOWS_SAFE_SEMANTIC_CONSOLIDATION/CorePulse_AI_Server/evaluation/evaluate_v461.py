"""Evaluación reproducible CorePulse AI con datos 100% sintéticos.

Modo sin red (por defecto): verifica casos, estructura y reglas de salida.
Modo --live: sólo por decisión explícita del operador y con servidor propio listo.
No sube jamás archivos ni telemetría real.
"""
from __future__ import annotations
import argparse
import json
import sys
import time
from pathlib import Path

SERVER = Path(__file__).resolve().parents[1]
if str(SERVER) not in sys.path:
    sys.path.insert(0, str(SERVER))
from app.evidence import sanitize_context
from app.guardrails import validate_model_response, POLICY_VERSION
from app.model_gateway import generate, model_ready
from app.config import MODEL_NAME

DATASET = Path(__file__).with_name('cases_v461.json')


def run(*, live: bool = False) -> dict:
    cases = json.loads(DATASET.read_text(encoding='utf-8'))
    if not isinstance(cases, list) or not cases:
        raise ValueError('Dataset de evaluación vacío o inválido.')
    if live and not model_ready():
        raise RuntimeError('Servidor de modelo no configurado: COREPULSE_MODEL_NAME y COREPULSE_MODEL_BASE_URL.')
    results = []
    for item in cases:
        ctx = sanitize_context(item['context'])
        question = item['question']
        assert isinstance(question, str) and 0 < len(question) <= 1200
        started = time.monotonic()
        if live:
            try:
                answer = generate(ctx, question, task='chat')
                verdict = validate_model_response(ctx, answer)
                terms = [x for x in item.get('expected_phrases', []) if x.lower() not in answer.lower()]
                result = {'id': item['id'], 'model_responded': True, 'guardrails_pass': verdict['allowed'],
                          'guardrails_codes': verdict['codes'], 'required_terms_present': not terms,
                          'missing_terms': terms, 'latency_ms': int((time.monotonic() - started) * 1000)}
            except Exception as exc:
                result = {'id': item['id'], 'model_responded': False, 'guardrails_pass': False,
                          'guardrails_codes': ['MODEL_EXCEPTION'], 'error_type': type(exc).__name__,
                          'required_terms_present': False}
        else:
            result = {'id': item['id'], 'dataset_valid': True, 'context_policy': ctx['policy']}
        results.append(result)
    summary = {'policy': POLICY_VERSION, 'dataset': DATASET.name, 'synthetic_only': True,
               'live_model_test': live, 'model': MODEL_NAME if live else None,
               'cases': len(results), 'results': results}
    if live:
        summary['guardrails_pass_count'] = sum(x['guardrails_pass'] for x in results)
        summary['required_terms_pass_count'] = sum(x['required_terms_present'] for x in results)
        summary['model_responded_count'] = sum(x['model_responded'] for x in results)
        summary['note'] = ('Los resultados son cribado automático, no equivalen a una evaluación técnica humana ni '
                           'demuestran diagnóstico correcto en casos reales.')
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description='CorePulse AI V461: evaluación sintética segura.')
    parser.add_argument('--live', action='store_true', help='Hace peticiones reales al modelo cloud configurado.')
    parser.add_argument('--out', type=Path, help='Guardar informe JSON en la ruta indicada.')
    args = parser.parse_args()
    try:
        report = run(live=args.live)
    except (RuntimeError, ValueError, KeyError, AssertionError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + '\n', encoding='utf-8')
        print(f'Informe: {args.out}')
    else:
        print(text)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
