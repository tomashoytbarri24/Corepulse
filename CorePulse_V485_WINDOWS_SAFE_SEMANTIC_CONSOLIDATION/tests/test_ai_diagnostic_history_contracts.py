"""Regresiones históricas agrupadas en V481 sin eliminar pruebas."""
from __future__ import annotations


# ===== Regresión test_v475_intelligence_engine (original conservado íntegramente) =====
import json
from unittest.mock import patch
from fastapi.testclient import TestClient
import pytest
from CorePulse_AI_Server.app.evidence import sanitize_context
from CorePulse_AI_Server.app.intelligence_engine import (
    ENGINE_VERSION, analyze_evidence, format_diagnostic_brief, is_diagnostic_request,
)
from CorePulse_AI_Server.app.model_gateway import build_messages
from CorePulse_AI_Server.app import main


def prepared(**kwargs):
    return sanitize_context(kwargs)


def codes(report):
    return {x['code'] for x in report['findings']}


def test_no_data_never_assumes_healthy_or_breakdown():
    r = analyze_evidence(prepared())
    assert r['no_alerts_reported'] and r['finding_count'] == 0
    assert 'cpu.temperature_c' in r['missing']
    assert 'gpu.temperature_c' in r['missing']
    out = format_diagnostic_brief(r)
    assert 'N/A' in out and 'no demuestra' in out
    assert 'No se ha modificado Windows' in out


def test_numerical_temperature_does_not_create_an_alert():
    r = analyze_evidence(prepared(cpu={'temperature_c': 102, 'usage_percent': 80}))
    assert r['findings'] == []
    assert {'source':'cpu.temperature_c','value':102,'unit':'°C'} in r['observations']


def test_explicit_thermal_alert_without_temperature():
    r = analyze_evidence(prepared(decision={'thermal_alerts':['CPU']}))
    assert codes(r) == {'CPU_THERMAL_REPORTED'}
    f = r['findings'][0]
    assert f['evidence_sources'] == ['decision.thermal_alerts']
    assert 'N/A' in f['observation']
    assert not f['confirmed_hardware_failure']
    assert not f['windows_action_performed']


def test_thermal_alert_with_evidence_and_two_components():
    r = analyze_evidence(prepared(cpu={'temperature_c':96},gpu={'temperature_c':91},decision={'thermal_alerts':['CPU','GPU']}))
    assert codes(r) == {'CPU_THERMAL_REPORTED','GPU_THERMAL_REPORTED'}
    assert 'cpu.temperature_c' in r['findings'][0]['evidence_sources']


def test_high_memory_measurement_alone_cannot_diagnose_ram_fault():
    r = analyze_evidence(prepared(ram={'usage_percent':98},decision={'ram_usage_state':'NORMAL_SAMPLE'}))
    assert 'RAM_PRESSURE' not in codes(r)


def test_corepulse_ram_state_is_usage_only():
    r = analyze_evidence(prepared(ram={'usage_percent':94},decision={'ram_usage_state':'HIGH_USAGE'}))
    assert codes(r) == {'RAM_PRESSURE'}
    assert 'avería física' in r['findings'][0]['observation']
    assert 'ram.usage_percent' in r['findings'][0]['evidence_sources']


def test_storage_usage_not_smart_health():
    r = analyze_evidence(prepared(storage=[{'used_percent':96,'health_percent':None}],
                                  decision={'attention_areas':['ALMACENAMIENTO']}))
    assert codes(r) == {'STORAGE_ATTENTION'}
    assert 'storage[0].used_percent' in [x['source'] for x in r['observations']]
    assert 'storage[0].health_percent' in r['missing']
    assert 'salud SMART' in r['findings'][0]['observation']


def test_smart_value_does_not_by_itself_create_attention():
    r = analyze_evidence(prepared(storage=[{'used_percent':15,'health_percent':20}]))
    assert not r['findings']
    assert any(x['source']=='storage[0].health_percent' for x in r['observations'])


def test_nonfinite_boolean_and_implausible_telemetry_safely_na():
    r = analyze_evidence(prepared(cpu={'temperature_c':float('nan'),'usage_percent':102},
                                  gpu={'usage_percent':True},storage=[{'used_percent':-1}]))
    assert not r['observations']
    assert 'cpu.temperature_c' in r['missing']
    assert 'cpu.usage_percent' in r['missing']
    assert 'storage[0].used_percent' in r['missing']


def test_assessment_plan_is_not_claimed_as_hardware_failure():
    r = analyze_evidence(prepared(deterministic_assessment={'problem_recommendations':[
        {'component_type':'RAM','title':'Revisar procesos que consumen memoria'}]}))
    assert 'COREPULSE_PLAN' in codes(r)
    assert not r['findings'][0]['confirmed_hardware_failure']
    assert 'deterministic_assessment.problem_recommendations[0]' in r['findings'][0]['evidence_sources']


@pytest.mark.parametrize('question, expected', [
    ('Hola',False), ('Dame mantenimiento preventivo',False),
    ('Analiza mi PC',True),('Diagnóstico completo',True),
    ('¿Por qué se apaga al jugar?',True),('¿Qué problema tiene mi equipo?',True),
])
def test_routing(question,expected):
    assert is_diagnostic_request(question) is expected


def test_diagnostic_prompt_gets_engine_but_educational_does_not():
    ctx=prepared(cpu={'temperature_c':32}, decision={'thermal_alerts':['GPU']})
    s=build_messages(ctx,'Analiza mi equipo')[-1]['content']
    assert 'corepulse_intelligence_engine' in s and 'GPU_THERMAL_REPORTED' in s
    assert 'corepulse_intelligence_engine' not in build_messages(ctx,'Dame un tutorial de limpieza')[-1]['content']


def test_fallback_when_model_unavailable_is_deterministic():
    ctx=prepared(cpu={'temperature_c':39}, decision={'thermal_alerts':['CPU']})
    with patch.object(main,'model_ready',return_value=False):
        out,mode,v=main._safe_generation(ctx,'Analiza mi equipo',task='chat',history=[])
    assert mode == 'evidence_fallback' and 'alerta térmica' in out
    assert '39' in out and v['codes']==['MODEL_NOT_CONFIGURED']


def test_fallback_when_model_invents_hardware_number():
    ctx=prepared(cpu={'temperature_c':39},decision={'thermal_alerts':['CPU']})
    with patch.object(main,'model_ready',return_value=True), patch.object(main,'generate',return_value='La CPU está a 104 °C.'):
        out,mode,v=main._safe_generation(ctx,'Analiza mi equipo',task='chat',history=[])
    assert mode == 'evidence_fallback' and '104' not in out
    assert 'UNSUPPORTED_TEMP' in v['codes']


def test_engine_is_provider_independent_and_no_secrets_in_results():
    ctx=prepared(cpu={'temperature_c':43},decision={'thermal_alerts':['CPU']})
    r=analyze_evidence(ctx)
    assert not any(token in json.dumps(r).lower() for token in ('api_key','groq','bearer','password'))
    assert r['engine_version']==ENGINE_VERSION


def test_status_announces_engine_version_without_inference():
    with patch.object(main,'model_ready',return_value=False):
        response=TestClient(main.app).get('/v1/status')
    assert response.status_code == 200
    assert response.json()['intelligence_engine_version'] == ENGINE_VERSION


def test_real_http_chat_returns_structured_evidence_without_model_or_network():
    client = TestClient(main.app)
    context = {'cpu': {'temperature_c': 38}, 'decision': {'thermal_alerts': ['CPU']}}
    with (patch.object(main, '_bearer', return_value='synthetic_test_token'),
          patch.object(main, '_consume_or_raise', return_value=90),
          patch.object(main, '_cached_response', return_value=None),
          patch.object(main, '_remember_response'),
          patch.object(main, 'model_ready', return_value=False)):
        result=client.post('/v1/chat',headers={'Authorization':'Bearer synthetic_test_token'},json={
            'context':context,'question':'Analiza mi equipo','history':[]})
    assert result.status_code == 200
    body=result.json()
    assert body['mode']=='evidence_fallback'
    assert body['intelligence']['findings'][0]['code']=='CPU_THERMAL_REPORTED'
    assert '38' in body['text']
    assert body['remaining_today'] == 90


def test_real_http_analyze_when_offline_reports_no_confirmation_of_failure():
    client=TestClient(main.app)
    with (patch.object(main,'_bearer',return_value='synthetic_token2'),
          patch.object(main,'_consume_or_raise',return_value=91),
          patch.object(main,'_cached_response',return_value=None),
          patch.object(main,'_remember_response'),
          patch.object(main,'model_ready',return_value=False)):
        result=client.post('/v1/analyze',headers={'Authorization':'Bearer synthetic_token2'},json={
            'context':{'cpu':{'temperature_c':95}},'question':'Analiza mi PC'})
    assert result.status_code == 200
    body=result.json()
    assert body['mode']=='evidence_fallback'
    assert not body['intelligence']['findings']
    assert 'no demuestra' in body['text']



# ===== Regresión test_v476_investigation (original conservado íntegramente) =====
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
import json
from fastapi.testclient import TestClient
from core.ai_investigation_history import query_sample, append_sample
from CorePulse_AI_Server.app.evidence import sanitize_context
from CorePulse_AI_Server.app.intelligence_engine import analyze_evidence, format_diagnostic_brief, is_diagnostic_request
from CorePulse_AI_Server.app.investigation_engine import sanitize_session_history
from CorePulse_AI_Server.app.model_gateway import build_messages
from CorePulse_AI_Server.app import main


def now(seconds=0):
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat(timespec='seconds')


def ctx(value=40, stamp=None, prev=None, extra=None):
    payload = {'cpu': {'temperature_c': value, 'usage_percent':50},
               'evidence_snapshot':{'captured_at_utc':stamp or now()},
               'observation_history':prev or []}
    if extra:
        payload.update(extra)
    return sanitize_context(payload)


def sample(value=40, stamp=None):
    return {'source':'COREPULSE_QUERY_SNAPSHOT', 'captured_at_utc':stamp or now(-60),
            'metrics': {'cpu': {'temperature_c': value, 'usage_percent':25}}}


def test_single_reading_no_historical_claim():
    result=analyze_evidence(ctx())
    assert result['timeline']['status']=='INSUFFICIENT'
    assert 'no hay dos lecturas' in format_diagnostic_brief(result)


def test_two_distinct_readings_comparable_not_fault():
    c=ctx(61,prev=[sample(40)])
    result=analyze_evidence(c)
    info=result['timeline']
    assert info['status']=='TWO_SNAPSHOTS_COMPARABLE'
    assert info['server_verified_sampling'] is False
    temp=next(x for x in info['comparisons'] if x['metric']=='cpu.temperature_c')
    assert temp['delta']==21 and temp['direction']=='SUBE'
    assert result['no_alerts_reported'] is True
    assert result['findings']==[]
    assert 'no prueban la causa' in format_diagnostic_brief(result)


def test_no_smart_from_used_or_ram_fault():
    c=ctx(46, prev=[sample(40)], extra={'storage':[{'used_percent':98}], 'ram':{'usage_percent':99}})
    r=analyze_evidence(c)
    assert r['findings']==[]
    assert 'storage[0].health_percent' in r['missing']
    assert 'ram.usage_percent' not in [x['metric'] for x in r['timeline']['comparisons']]


def test_short_spacing_ignored():
    c=ctx(prev=[sample(stamp=now(-3))])
    assert analyze_evidence(c)['timeline']['status']=='INSUFFICIENT'


def test_missing_current_sensor_cannot_compare():
    c=ctx(None,prev=[sample(45)])
    measurements=analyze_evidence(c)['timeline']['comparisons']
    assert 'cpu.temperature_c' not in [x['metric'] for x in measurements]


def test_invalid_nan_infinite_boolean_and_range():
    s=sample(999)
    s['metrics']['gpu']={'temperature_c':'nan','usage_percent':True}
    s['metrics']['ram']={'usage_percent':float('inf')}
    assert sanitize_session_history([s])==[{'captured_at_utc':s['captured_at_utc'],'metrics':{'cpu':{'usage_percent':25.0}},'source':'CLIENT_REPORTED_SESSION_SAMPLE','reported_thermal_alerts':[]}]


def test_old_and_future_samples_discarded():
    assert sanitize_session_history([sample(stamp=now(-90000)),sample(stamp=now(130))])==[]


def test_duplicate_same_second_one_and_bounded():
    arr=[sample(value=x,stamp=now(-80+x)) for x in range(12)]
    arr[-1]['captured_at_utc']=arr[-2]['captured_at_utc']
    out=sanitize_session_history(arr)
    assert len(out)<=5
    assert len({s['captured_at_utc'] for s in out})==len(out)


def test_session_sample_whitelist_no_private_data():
    raw={'cpu':{'temperature_c':47,'usage_percent':30,'serial':'SECRET'},
         'gpu':{'temperature_c':None}, 'evidence_snapshot':{'captured_at_utc':now()},
         'device':{'model':'My private notebook'},'GROQ_API_KEY':'NOT_A_REAL_KEY'}
    s=query_sample(raw)
    assert s is not None
    serialized=json.dumps(s)
    assert 'SECRET' not in serialized and 'notebook' not in serialized and 'GROQ' not in serialized


def test_empty_sample_nothing_saved():
    assert query_sample({'evidence_snapshot':{'captured_at_utc':now()}}) is None
    assert append_sample([],None)==[]


def test_local_samples_bounded_deduplicated():
    items=[]
    for i in range(8):
        items=append_sample(items,query_sample({'cpu':{'temperature_c':40+i},'evidence_snapshot':{'captured_at_utc':now(-500+i)}}))
    assert len(items)==5
    d=items[-1]
    assert len(append_sample(items,d))==5


def test_diagnostic_routing_and_generation_prompt():
    c=ctx(50,prev=[sample(41)])
    assert is_diagnostic_request('Compara mis lecturas actuales con las anteriores')
    assert is_diagnostic_request('¿Hay tendencia en mis temperaturas?')
    assert not is_diagnostic_request('Dame mantenimiento preventivo')
    prompt=build_messages(c,'Compara mis lecturas actuales con las anteriores')[-1]['content']
    assert 'TWO_SNAPSHOTS_COMPARABLE' in prompt and 'corepulse_intelligence_engine' in prompt
    assert 'corepulse_intelligence_engine' not in build_messages(c,'Hola')[-1]['content']


def test_fallback_offline_uses_variations():
    c=ctx(55,prev=[sample(40)])
    with patch.object(main,'model_ready',return_value=False):
        text,mode,verdict=main._safe_generation(c,'Compara mis temperaturas',task='chat',history=[])
    assert mode=='evidence_fallback'
    assert '40 a 55' in text
    assert 'no constituyen' not in text or 'no prueban' in text


def test_authenticated_http_chat_timeline_no_cloud_model():
    client=TestClient(main.app)
    data={'cpu':{'temperature_c':52},'observation_history':[sample(39)],
          'evidence_snapshot':{'captured_at_utc':now()}}
    with (patch.object(main,'_bearer',return_value='test'),
          patch.object(main,'_consume_or_raise',return_value=99),
          patch.object(main,'_cached_response',return_value=None),
          patch.object(main,'_remember_response'),
          patch.object(main,'model_ready',return_value=False)):
        out=client.post('/v1/chat',json={'context':data,'question':'Compara las lecturas actuales','history':[]},headers={'Authorization':'Bearer test'})
    assert out.status_code==200
    body=out.json()
    assert body['intelligence']['timeline']['status']=='TWO_SNAPSHOTS_COMPARABLE'
    assert '39 a 52' in body['text']


def test_history_is_not_classification_authority():
    c=ctx(110,prev=[sample(18)])
    assert analyze_evidence(c)['findings']==[]
    assert 'CPU_THERMAL_REPORTED' not in format_diagnostic_brief(analyze_evidence(c))


def test_only_corepulse_explicit_alert_classified():
    c=ctx(55,prev=[sample(49)],extra={'decision':{'thermal_alerts':['CPU']}})
    findings=analyze_evidence(c)['findings']
    assert [f['code'] for f in findings]==['CPU_THERMAL_REPORTED']


def test_reported_alerts_correlate_without_new_detection():
    prev=sample(47)
    prev['reported_thermal_alerts']=['CPU']
    c=ctx(55,prev=[prev], extra={'decision':{'thermal_alerts':['CPU']}})
    report=analyze_evidence(c)
    corr=report['timeline']['alert_correlations']
    assert next(x for x in corr if x['component']=='CPU')['previous_declared']
    assert next(x for x in corr if x['component']=='CPU')['current_declared']
    assert 'de CPU en ambas capturas' in format_diagnostic_brief(report)
    assert [x['code'] for x in report['findings']]==['CPU_THERMAL_REPORTED']

def test_historical_alert_without_current_alert_not_a_new_fault():
    old=sample(90)
    old['reported_thermal_alerts']=['GPU']
    report=analyze_evidence(ctx(52,prev=[old]))
    corr=next(x for x in report['timeline']['alert_correlations'] if x['component']=='GPU')
    assert corr['previous_declared'] and not corr['current_declared']
    assert report['findings']==[]

