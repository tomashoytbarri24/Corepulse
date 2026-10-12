"""V475 · 100% local y sintético. Sin red, secretos ni datos del equipo."""
from __future__ import annotations
import json
from CorePulse_AI_Server.app.evidence import sanitize_context
from CorePulse_AI_Server.app.intelligence_engine import analyze_evidence, format_diagnostic_brief

SCENARIOS = [
    ('Sensores ausentes', {}),
    ('Temperatura sin clasificación', {'cpu': {'temperature_c': 95}}),
    ('Alerta térmica declarada', {'cpu': {'temperature_c': 96}, 'decision': {'thermal_alerts': ['CPU']}}),
    ('RAM en uso elevado', {'ram': {'usage_percent': 93}, 'decision': {'ram_usage_state':'HIGH_USAGE'}}),
    ('SSD ocupado, SMART N/A', {'storage': [{'used_percent':94}], 'decision': {'attention_areas':['ALMACENAMIENTO']}}),
]

def main():
    results=[]
    for name,ctx in SCENARIOS:
        report=analyze_evidence(sanitize_context(ctx))
        results.append({'scenario': name, 'findings': [x['code'] for x in report['findings']],
                        'na_count': len(report['missing']), 'engine_version': report['engine_version']})
    assert not results[0]['findings'] and not results[1]['findings']
    assert results[2]['findings']==['CPU_THERMAL_REPORTED']
    assert results[3]['findings']==['RAM_PRESSURE']
    assert results[4]['findings']==['STORAGE_ATTENTION']
    print('COREPULSE_INTELLIGENCE_V475_PASS')
    print(json.dumps(results,ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
