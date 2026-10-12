"""Comparador de medidas REALES de benchmark V462; no crea puntuaciones simuladas."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys


def compare_reports(paths: list[Path]) -> dict:
    if len(paths)<2:
        raise ValueError('Se necesitan al menos dos informes de inferencia real.')
    reports=[]
    for p in paths:
        data=json.loads(p.read_text(encoding='utf-8'))
        if data.get('schema')!='corepulse-model-benchmark-v462' or data.get('mode')!='live_synthetic_inference' or not data.get('model_inference_performed'):
            raise ValueError(f'{p.name} no es una medición real V462.')
        reports.append(data)
    digests={r.get('dataset_sha256') for r in reports}
    if None in digests or len(digests)>1:
        raise ValueError('Los informes comparados deben provenir del mismo conjunto SHA256.')
    samples={r.get('sample_count') for r in reports}
    if len(samples)>1:
        raise ValueError('Los informes deben contener la misma cantidad de muestras.')
    models=[x['model_id'] for x in reports]
    if len(set(models))!=len(models):
        raise ValueError('Los modelos deben ser distintos para compararlos.')
    return {
        'schema':'corepulse-model-comparison-v462','mode':'real_synthetic_results_only',
        'dataset_sha256':next(iter(digests)),
        'case_count_per_model':reports[0]['case_count'],
        'automatic_rubric_only':True,
        'qualified_winner':None,
        'comparison':[
            {'model':r['model_id'], 'automatic_checks_pass_rate':r['automatic_checks_pass_rate'],
             'critical_violations':r['critical_violations'],
             'model_errors':r['model_errors'], 'latency_ms_p50':r['latency_ms_p50'],
             'latency_ms_p95':r['latency_ms_p95'],
             'server_gpu_vram_mib':r.get('server_gpu_vram_mib'),
             'server_power_watts':r.get('server_power_watts'),
             'manual_hardware_expert_review':r.get('manual_hardware_expert_review','PENDING')}
            for r in reports
        ],
        'note':'Comparación de checks automáticos y latencia, sin afirmar que un modelo sea el mejor ni precisión técnica certificada.'
    }


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument('reports',type=Path,nargs='+')
    parser.add_argument('--out',type=Path)
    args=parser.parse_args()
    try:
        result=compare_reports(args.reports)
        content=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
        if args.out:
            args.out.parent.mkdir(parents=True,exist_ok=True)
            args.out.write_text(content,encoding='utf-8')
            print('Comparación guardada:',args.out)
        else:
            print(content)
        return 0
    except (ValueError,KeyError,OSError) as exc:
        print(f'No se pueden comparar los informes: {exc}',file=sys.stderr)
        return 2

if __name__=='__main__':
    raise SystemExit(main())
