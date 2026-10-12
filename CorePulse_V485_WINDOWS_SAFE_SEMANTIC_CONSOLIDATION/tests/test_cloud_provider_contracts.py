"""Regresiones históricas agrupadas en V481 sin eliminar pruebas."""
from __future__ import annotations


# ===== Regresión test_v459_cloud_first (original conservado íntegramente) =====
import unittest
from unittest.mock import patch

from core import ai_client

class CloudFirstTests(unittest.TestCase):
    def test_no_url_no_http(self):
        s={'base_url':'', 'cloud_telemetry_consent': True, 'timeout_seconds':5}
        with patch('core.ai_client.urllib.request.build_opener', side_effect=AssertionError('network')):
            r=ai_client.service_status(s)
        self.assertEqual(r['state'], 'CLOUD_NOT_CONFIGURED')

    def test_no_consent_no_http(self):
        s={'base_url':'https://corepulse.invalid', 'cloud_telemetry_consent': False, 'timeout_seconds':5}
        with patch('core.ai_client.urllib.request.build_opener', side_effect=AssertionError('network')):
            self.assertEqual(ai_client.chat_context({'cpu':{}},question='hola',settings=s)['state'], 'CLOUD_CONSENT_REQUIRED')

    def test_shutdown_blocks_http(self):
        s={'base_url':'https://corepulse.invalid','cloud_telemetry_consent':True,'timeout_seconds':5}
        with patch('core.ai_client.load_ai_enabled',return_value=False),patch('core.ai_client.urllib.request.build_opener',side_effect=AssertionError('network')):
            self.assertEqual(ai_client.service_status(s)['state'], 'DISABLED')

    def test_never_local_or_http_endpoints(self):
        for url in ('http://example.com','http://localhost:8765','https://localhost:8765','javascript:alert(1)','https://user:pass@server.com'):
            self.assertEqual(ai_client._allowed_base_url(url),'')
        self.assertEqual(ai_client._allowed_base_url('https://ai.example.com'),'https://ai.example.com')

    def test_no_local_runtime_auto_start(self):
        from pathlib import Path
        src=(Path(__file__).resolve().parents[1]/'main.py').read_text(encoding='utf8')
        block=src.split('    def _start_ai_runtime_background(self):',1)[1].split('    def toggle_local_ai(self):',1)[0]
        self.assertNotIn('start_async(',block)
        self.assertNotIn('LocalAIRuntimeManager',block)

if __name__=='__main__': unittest.main()



# ===== Regresión test_v461_ai_guardrails (original conservado íntegramente) =====

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / 'CorePulse_AI_Server'
if str(SERVER) not in sys.path:
    sys.path.insert(0, str(SERVER))
from app import main, store
from app.evidence import sanitize_context
from app.guardrails import validate_model_response, evidence_fields, POLICY_VERSION


def context(**extra):
    ctx = {
        'cpu': {'name': 'AMD Ryzen', 'temperature_c': None, 'usage_percent': 34.2, 'frequency_ghz': 3.25},
        'gpu': {'name': 'NVIDIA', 'temperature_c': 43.3, 'usage_percent': 25.0, 'vram_gb': 8},
        'ram': {'total_gb': 16, 'used_gb': 6, 'usage_percent': 37.5},
        'storage': [{'model': 'SSD', 'used_percent': 60, 'health_percent': None, 'temperature_c': 39, 'total_space_gb': 512}],
        'health': {'score': 84, 'status': 'NORMAL'},
        'decision': {'attention_areas': [], 'thermal_alerts': [], 'ram_usage_state': 'NORMAL_SAMPLE'},
    }
    ctx.update(extra)
    return sanitize_context(ctx)


@pytest.mark.parametrize('answer,code', [
    ('CPU: 78 °C.', 'UNSUPPORTED_TEMP'),
    ('CPU a 43.3 °C; GPU a 43.3 °C.', 'UNSUPPORTED_TEMP'),  # no intercambiar GPU/CPU
    ('GPU: 56 °C.', 'UNSUPPORTED_TEMP'),
    ('RAM: 73% uso.', 'UNSUPPORTED_PERCENT'),
    ('Salud SMART del SSD: 60%.', 'UNSUPPORTED_PERCENT'),
    ('RAM usada: 16 GB.', 'UNSUPPORTED_GB'),
    ('RAM total: 6 GB.', 'UNSUPPORTED_GB'),
    ('CPU: 42% uso.', 'UNSUPPORTED_PERCENT'),
    ('La frecuencia CPU es 4.8 GHz.', 'UNSUPPORTED_GHZ'),
    ('El sistema tiene 64 GB de RAM.', 'UNSUPPORTED_GB'),
    ('La GPU tiene 12 GB de VRAM.', 'UNSUPPORTED_GB'),
    ('Rinde a 120 FPS.', 'FPS_WITHOUT_REAL_MEASUREMENT'),
    ('El SSD escribe 400 MB/s.', 'UNVERIFIED_THROUGHPUT'),
    ('La temperatura CPU: 70.', 'UNVERIFIABLE_TEMPERATURE'),
    ('CPU con temperatura alta.', 'UNVERIFIED_THERMAL_CLASSIFICATION'),
    ('Se observa sobrecalentamiento.', 'UNVERIFIED_THERMAL_CLASSIFICATION'),
    ('La GPU está dañada.', 'UNVERIFIED_HARDWARE_FAULT'),
    ('He actualizado Windows.', 'UNAUTHORIZED_ACTION_CLAIM'),
    ('Ya ejecutado un cambio.', 'UNAUTHORIZED_ACTION_CLAIM'),
    ('Verifica el tutorial https://example.com/video/123', 'UNVERIFIED_LINK'),
])
def test_blocks_unsupported_claims(answer, code):
    verdict = validate_model_response(context(), answer)
    assert not verdict['allowed'], answer
    assert code in verdict['codes'], (answer, verdict)


@pytest.mark.parametrize('answer', [
    'La temperatura de la CPU es N/A. No hay lectura válida.',
    'CPU: 34.2% de uso, 3.25 GHz. GPU: 43.3 °C.',
    'La GPU funciona al 25% de uso.',
    'La RAM usa 6 de 16 GB y tiene 10 GB restantes (cálculo).',
    'RAM total: 16 GB, RAM usada: 6 GB, RAM libre: 10 GB (cálculo).',
    'El SSD reporta 60% de ocupación, SMART N/A.',
    'Salud del sistema: 84%.',
    'Hola, ¿qué aspecto del equipo quieres revisar?',
    'Los FPS son N/A; CorePulse no tiene una lectura real.',
])
def test_accepts_grounded_answer(answer):
    result = validate_model_response(context(), answer)
    assert result['allowed'], (answer, result)


def test_urls_only_from_approved_tutorial_and_search_not_disguised():
    url = 'https://youtube.com/watch?v=example'
    search = 'https://www.youtube.com/results?search_query=cpu'
    approved = context(deterministic_assessment={'problem_recommendations': [
        {'tutorial': {'status': 'VERIFIED_EXACT', 'url': url}},
        {'tutorial': {'status': 'SEARCH_ONLY', 'url': 'https://youtube.com/watch?v=not_verified', 'search_url': search}},
    ]})
    assert validate_model_response(approved, f'Tutorial verificado: {url}')['allowed']
    assert validate_model_response(approved, f'Búsqueda: {search}')['allowed']
    assert 'SEARCH_PRESENTED_AS_EXACT' in validate_model_response(approved, f'Tutorial exacto: {search}')['codes']
    assert 'UNVERIFIED_LINK' in validate_model_response(approved, 'https://youtube.com/watch?v=not_verified')['codes']


def test_real_temperature_alert_does_not_allow_guessing_another_value():
    alert = context(cpu={'temperature_c': 96}, decision={'thermal_alerts': ['CPU']})
    assert validate_model_response(alert, 'CPU: 96 °C, temperatura alta.')['allowed']
    assert not validate_model_response(alert, 'CPU: 88 °C, temperatura alta.')['allowed']


def test_unknown_year_relevance_must_not_be_guessed():
    unavailable = context(deterministic_assessment={
        'hardware_relevance': [{'component_type': 'CPU', 'classification': 'NO_EVALUABLE'}]})
    assert 'UNVERIFIED_YEAR_CLASSIFICATION' in validate_model_response(unavailable, 'La CPU está obsoleta.')['codes']


def test_sanitization_discards_unrecognized_private_fields_and_na():
    c = context(secret_path='C:/Users/Sensitive/', cpu={'temperature_c': 'N/A'},
                extra_environment={'api_key': 'please-do-not-leak'})
    assert 'secret_path' not in c and 'extra_environment' not in c
    assert c['cpu']['temperature_c'] is None
    assert evidence_fields(c) == [x for x in evidence_fields(c) if 'temperature_c' not in x or 'cpu' not in x]


@pytest.fixture
def service(tmp_path, monkeypatch):
    monkeypatch.setattr(store, 'DB_PATH', tmp_path / 'devices.sqlite3')
    monkeypatch.setattr(store, 'DAILY_LIMIT', 50)
    monkeypatch.setattr(main, 'DEDUP_SECONDS', 0)
    main._recent_responses.clear()
    with TestClient(main.app) as client:
        code, _ = store.issue_pairing_code(minutes=5)
        pairing = client.post('/v1/register', json={'installation_id': 'v461-device'},
                              headers={'X-CorePulse-Enrollment': code})
        assert pairing.status_code == 200, pairing.text
        yield client, {'Authorization': 'Bearer ' + pairing.json()['token']}


@pytest.mark.parametrize('endpoint,body', [
    ('/v1/chat', {'context': {'cpu': {'temperature_c': None}}, 'question': 'Temperatura CPU'}),
    ('/v1/analyze', {'context': {'cpu': {'temperature_c': None}}}),
])
def test_api_refuses_fabricated_temperature(service, endpoint, body):
    client, headers = service
    with patch.object(main, 'model_ready', return_value=True), \
         patch.object(main, 'generate', return_value='CPU: 97 °C. Se está sobrecalentando.'):
        response = client.post(endpoint, json=body, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data['mode'] == 'evidence_fallback'
    assert data['guardrails']['allowed'] is False
    assert 'UNSUPPORTED_TEMP' in data['guardrails']['codes']
    assert '97 °C' not in data['text']
    assert 'N/A' in data['text'] or 'no tiene una puntuación' in data['text']


def test_api_accepts_supported_model_output_and_tracks_origin(service):
    client, headers = service
    with patch.object(main, 'model_ready', return_value=True), \
         patch.object(main, 'generate', return_value='GPU: 43.3 °C. CPU: N/A.'):
        result = client.post('/v1/chat', json={'context': context(), 'question': 'temperaturas'}, headers=headers)
    assert result.status_code == 200
    data = result.json()
    assert data['mode'] == 'model' and data['guardrails']['allowed']
    assert 'gpu.temperature_c' in data['evidence_fields']
    assert 'cpu.temperature_c' not in data['evidence_fields']
    assert data['guardrails']['policy_version'] == POLICY_VERSION


def test_fallback_when_host_unavailable_not_misrepresented(service):
    client, headers = service
    with patch.object(main, 'model_ready', return_value=True), \
         patch.object(main, 'generate', side_effect=TimeoutError('GPU not connected')):
        result = client.post('/v1/chat', json={'context': context(), 'question': 'cpu'}, headers=headers)
    assert result.status_code == 200
    assert result.json()['guardrails']['codes'] == ['MODEL_ERROR']
    assert result.json()['mode'] == 'evidence_fallback'


def test_status_reports_policy_revision(service):
    client, _ = service
    with patch.object(main, 'model_ready', return_value=False):
        status = client.get('/v1/status')
    assert status.status_code == 200
    assert status.json()['service_version'] == '1.8.0'
    assert status.json()['safety_policy_version'] == POLICY_VERSION


def test_evaluation_dataset_is_synthetic_and_offline():
    sys.path.insert(0, str(SERVER / 'evaluation'))
    from evaluate_v461 import run
    with patch('app.model_gateway.urllib.request.urlopen', side_effect=AssertionError('No network in offline eval')):
        report = run(live=False)
    assert report['synthetic_only'] and not report['live_model_test']
    assert report['cases'] >= 10
    assert all(item['dataset_valid'] for item in report['results'])


def test_no_runtime_or_windows_execution_in_server():
    from app import guardrails
    import inspect
    assert 'subprocess' not in inspect.getsource(guardrails)
    assert 'os.system' not in inspect.getsource(guardrails)
    assert 'winreg' not in inspect.getsource(guardrails)


def test_tutorial_research_no_third_party_network_by_default():
    from core.tutorial_research import enrich_plans_with_tutorials
    request = [{'title': 'Actualizar SSD', 'tutorial_request': {'intent': 'ssd_upgrade', 'component': 'SSD'}}]
    inventory = {'device': {'model': 'MSI GE66 Raider'}}
    with patch('core.tutorial_research.urllib.request.urlopen', side_effect=AssertionError('Third party traffic forbidden')):
        plans = enrich_plans_with_tutorials(request, inventory)
    assert plans[0]['tutorial']['status'] == 'SEARCH_ONLY'
    assert plans[0]['tutorial']['url'] is None
    assert plans[0]['tutorial']['search_url'].startswith('https://www.youtube.com/results?search_query=')



# ===== Regresión test_v462_cloud_model_evaluation (original conservado íntegramente) =====
import json
from pathlib import Path
import sys
from unittest.mock import patch
import pytest

ROOT=Path(__file__).resolve().parents[1]
SERVER=ROOT/'CorePulse_AI_Server'
if str(SERVER) not in sys.path:
    sys.path.insert(0,str(SERVER))
from evaluation import benchmark_v462 as b
from evaluation.compare_v462 import compare_reports
from app.evidence import sanitize_context
from app.model_gateway import build_messages


def test_dataset_valid_and_synthetic_coverage():
    cases=b.load_cases()
    assert len(cases)==30
    assert {x['area'] for x in cases}==b.AREAS
    assert sum(x['checks']['critical'] for x in cases)>=12
    assert all('secret' not in json.dumps(item).lower() for item in cases)


def test_offline_does_not_run_network_or_model(tmp_path):
    report=tmp_path/'offline.json'
    with patch.object(b,'perform_completion',side_effect=AssertionError('inference forbidden')),\
         patch.object(b,'urlopen',side_effect=AssertionError('network forbidden')):
        assert b.main(['--out',str(report)])==0
    data=json.loads(report.read_text(encoding='utf-8'))
    assert data['mode']=='dataset_validation_only'
    assert data['model_inference_performed'] is False
    assert data['automatic_model_pass_rate'] is None
    assert data['gpu_consumption'] is None
    assert data['case_count']==30


def test_lint_rejects_private_context(tmp_path):
    cases=b.load_cases()
    cases[0]['context']['serial_number']='SECRET-SERIAL'
    target=tmp_path/'cases.json'
    target.write_text(json.dumps(cases),encoding='utf-8')
    with pytest.raises(ValueError,match='no permitidos'):
        b.load_cases(target)


def test_lint_rejects_duplicate_case(tmp_path):
    cases=b.load_cases()
    cases[-1]['id']=cases[0]['id']
    target=tmp_path/'cases.json'
    target.write_text(json.dumps(cases),encoding='utf-8')
    with pytest.raises(ValueError,match='duplicado'):
        b.load_cases(target)


@pytest.mark.parametrize('url,allow,expected',[
    ('https://cloud.corepulse.example/v1',False,'https://cloud.corepulse.example/v1'),
    ('https://cloud.corepulse.example',False,'https://cloud.corepulse.example/v1'),
    ('http://localhost:8000/v1',False,'http://localhost:8000/v1'),
    ('http://127.0.0.1:8000/v1',False,'http://127.0.0.1:8000/v1'),
    ('http://model:8000/v1',True,'http://model:8000/v1'),
    ('http://192.168.1.10:8000/v1',True,'http://192.168.1.10:8000/v1'),
])
def test_endpoint_allowed(url,allow,expected):
    assert b.check_endpoint(url,allow)==expected


@pytest.mark.parametrize('url,allow',[
    ('http://public.example/v1',False),
    ('http://public.example/v1',True),
    ('http://8.8.8.8:8000/v1',True),
    ('https://user:pass@cloud.example/v1',False),
    ('ftp://cloud.example/v1',False),
    ('https://cloud.example/v1?token=BAD',False),
    ('https://cloud.example/special/v1',False),
])
def test_endpoint_blocked(url,allow):
    with pytest.raises(ValueError):
        b.check_endpoint(url,allow)


def test_live_requires_explicit_confirmation():
    assert b.main(['--live','--model','fake','--base-url','http://127.0.0.1:5555/v1'])==2


def test_no_network_even_with_confirmation_if_url_is_insecure():
    with patch.object(b,'urlopen',side_effect=AssertionError('network forbidden')):
        assert b.main(['--live','--confirm-synthetic-transmission', '--model','fake','--base-url','http://public.example/v1'])==2


def test_guardrail_rejects_hallucinated_cpu():
    case=next(c for c in b.load_cases() if c['id']=='cpu_na')
    verdict=b.evaluate_answer(case,'CPU: 97 °C.')
    assert not verdict['automatic_checks_ok']
    assert not verdict['guardrails_ok']
    assert 'UNSUPPORTED_TEMP' in verdict['guardrails_codes']


def test_topic_must_be_present_even_if_guardrail_accepts():
    case=next(c for c in b.load_cases() if c['id']=='cpu_na')
    verdict=b.evaluate_answer(case,'Hola, ¿en qué puedo ayudarte?')
    assert verdict['guardrails_ok']
    assert not verdict['rubric_ok']


def test_grounded_cpu_na_accepts():
    case=next(c for c in b.load_cases() if c['id']=='cpu_na')
    verdict=b.evaluate_answer(case,'La temperatura de la CPU es N/A porque no existe lectura válida.')
    assert verdict['automatic_checks_ok']


def test_comparison_cannot_use_offline_only(tmp_path):
    report=b.offline_report(b.load_cases())
    paths=[]
    for i in range(2):
        p=tmp_path/f'{i}.json'; p.write_text(json.dumps(report),encoding='utf-8'); paths.append(p)
    with pytest.raises(ValueError,match='no es una medición real'):
        compare_reports(paths)


def test_synthetic_mock_completion_no_network(monkeypatch):
    count=0
    def fake_completion(**kwargs):
        nonlocal count
        count+=1
        assert kwargs['model_id']=='FAKE-TEST-NOT-A-MODEL'
        assert kwargs['messages'][0]['role']=='system'
        assert 'REAL_OR_NA' in kwargs['messages'][-1]['content']
        return {'text':'No tengo datos suficientes, temperatura CPU: N/A.',
                'latency_ms':10.0,'prompt_tokens':150,'completion_tokens':13}
    report=b.run_model(b.load_cases(),base_url='http://127.0.0.1:8000/v1',
                       model_id='FAKE-TEST-NOT-A-MODEL',completion=fake_completion)
    assert count==30
    assert report['sample_count']==30 and report['model_inference_performed']
    assert report['model_errors']==0 and report['latency_ms_p95']==10
    assert report['server_gpu_vram_mib'] is None
    assert not report['qualified_for_production']
    assert report['automatic_checks_pass_rate']<1


def test_comparison_only_equivalent_measurements(tmp_path):
    cases=b.load_cases()
    def make(model):
        data=b.run_model(cases,base_url='http://localhost/v1',model_id=model,
            completion=lambda **kwargs: {'text':'No hay lectura: N/A.','latency_ms':17.,'prompt_tokens':9,'completion_tokens':7})
        data['dataset_sha256']='TEST-DIGEST'
        p=tmp_path/f'{model}.json';p.write_text(json.dumps(data),encoding='utf-8');return p
    a,bfile=make('model-A'),make('model-B')
    comparison=compare_reports([a,bfile])
    assert comparison['qualified_winner'] is None
    assert len(comparison['comparison'])==2
    altered=json.loads(bfile.read_text(encoding='utf-8'))
    altered['dataset_sha256']='MISMATCH'
    bfile.write_text(json.dumps(altered),encoding='utf-8')
    with pytest.raises(ValueError,match='SHA256'):
        compare_reports([a,bfile])


def test_message_builder_respects_evidence_and_no_private_keys():
    ctx=sanitize_context({'cpu':{'temperature_c':None}, 'private_path':'C:/Users/alguien',
                          'sensitive_key':'VERY-PRIVATE'})
    messages=build_messages(ctx,'¿Cuál es la CPU?', task='chat')
    body=json.dumps(messages,ensure_ascii=False)
    assert 'N/A' in body or 'null' in body
    assert 'VERY-PRIVATE' not in body and 'C:/Users/alguien' not in body


def test_catalog_not_misrepresented_as_benchmark():
    catalog=json.loads((SERVER/'evaluation/model_candidates_v462.json').read_text(encoding='utf8'))
    assert len(catalog['candidates'])==3
    assert all(x['quality_measured'] is False for x in catalog['candidates'])
    assert all(x['reference'].startswith('https://huggingface.co/') for x in catalog['candidates'])


def test_http_actual_loopback_openai_compatible():
    """Transport HTTP real contra stub local: NO es prueba de calidad de LLM."""
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from threading import Thread
    observed=[]
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            assert self.path == '/v1/chat/completions'
            length=int(self.headers.get('Content-Length','0'))
            payload=json.loads(self.rfile.read(length).decode('utf-8'))
            observed.append({'payload':payload,'authorization':self.headers.get('Authorization')})
            response={'choices':[{'message':{'content':'La temperatura CPU es N/A.'}}],
                      'usage':{'prompt_tokens':125,'completion_tokens':10}}
            blob=json.dumps(response).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(blob)))
            self.end_headers()
            self.wfile.write(blob)
        def log_message(self,*args):
            pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=Thread(target=server.serve_forever,daemon=True)
    thread.start()
    try:
        endpoint=b.check_endpoint(f'http://127.0.0.1:{server.server_port}/v1')
        result=b.perform_completion(base_url=endpoint,model_id='mock-HTTP',api_key='test-only-key',
                                    messages=build_messages(sanitize_context({'cpu':{'temperature_c':None}}),
                                                            '¿Qué temperatura CPU?'),timeout=5,max_tokens=200)
        assert result['text']=='La temperatura CPU es N/A.'
        assert result['prompt_tokens']==125 and result['completion_tokens']==10
        assert result['latency_ms']>=0
        assert observed[0]['authorization']=='Bearer test-only-key'
        assert observed[0]['payload']['model']=='mock-HTTP'
    finally:
        server.shutdown();server.server_close();thread.join(timeout=2)



# ===== Regresión test_v463_groq_cloud (original conservado íntegramente) =====
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch
import pytest

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / 'CorePulse_AI_Server'
if str(SERVER) not in sys.path:
    sys.path.insert(0, str(SERVER))

from app import config, model_gateway, main, store
from core import ai_client
from fastapi.testclient import TestClient


def trial_settings(consent=True):
    return {'base_url': ai_client.LOCAL_GROQ_BRIDGE_URL, 'local_groq_bridge': True,
            'cloud_telemetry_consent': consent, 'timeout_seconds': 7, 'token_base_url': ''}


def test_default_rejects_all_local_http_and_external_http():
    for url in ('http://127.0.0.1:8765', 'http://localhost:8765',
                'http://192.168.0.2:8765','http://example.org','https://localhost:8765'):
        assert not ai_client._allowed_base_url(url)


@pytest.mark.parametrize('endpoint', [
    'http://localhost:8765', 'http://127.0.0.1:8766',
    'http://127.0.0.1:8765/v1', 'http://127.0.0.1:8765@evil.example',
    'http://127.0.0.1:8765?token=abc', 'http://0.0.0.0:8765',
    'https://127.0.0.1:8765', 'http://127.0.0.1:8765.evil.example',
])
def test_local_bridge_exact_address_only(endpoint):
    assert not ai_client._allowed_base_url(endpoint, allow_local_groq_bridge=True)


def test_bridge_requires_explicit_consent_and_enabled_ai():
    with patch.object(ai_client.urllib.request, 'build_opener', side_effect=AssertionError('No debe haber tráfico')):
        assert ai_client.service_status(trial_settings(False))['state'] == 'CLOUD_CONSENT_REQUIRED'
        with patch.object(ai_client, 'load_ai_enabled', return_value=False):
            assert ai_client.service_status(trial_settings(True))['state'] == 'DISABLED'
    assert ai_client._allowed_base_url(ai_client.LOCAL_GROQ_BRIDGE_URL, allow_local_groq_bridge=True)


def test_no_other_ip_even_with_consent():
    s = trial_settings()
    s['base_url'] = 'http://8.8.8.8:8765'
    with patch.object(ai_client.urllib.request, 'build_opener', side_effect=AssertionError('No debe haber tráfico')):
        assert ai_client.service_status(s)['state'] == 'CLOUD_INVALID_ENDPOINT'


def test_switching_endpoint_removes_consent_and_client_token(tmp_path):
    with patch.object(ai_client,'SETTINGS_PATH',tmp_path / 'ai.json'),patch.object(ai_client,'delete_secret') as delete:
        initial = ai_client.save_ai_settings({'base_url':'https://cloud.example.org','cloud_telemetry_consent':True})
        assert initial['cloud_telemetry_consent']
        trial = ai_client.save_ai_settings({'base_url':ai_client.LOCAL_GROQ_BRIDGE_URL,'local_groq_bridge':True})
        assert trial['base_url']==ai_client.LOCAL_GROQ_BRIDGE_URL
        assert trial['local_groq_bridge'] is True
        assert trial['cloud_telemetry_consent'] is False
        assert ai_client.load_ai_settings()['base_url']==ai_client.LOCAL_GROQ_BRIDGE_URL
        production=ai_client.save_ai_settings({'base_url':'https://cloud2.example.org','local_groq_bridge':False})
        assert not production['cloud_telemetry_consent']
        assert not production['local_groq_bridge']
        assert delete.call_count >= 2


def test_model_requires_key_in_groq_mode():
    with patch.object(model_gateway,'MODEL_PROVIDER','groq'), patch.object(model_gateway,'MODEL_BASE_URL','https://api.groq.com/openai/v1'), patch.object(model_gateway,'MODEL_NAME','openai/gpt-oss-120b'), patch.object(model_gateway,'MODEL_API_KEY',''):
        assert not model_gateway.model_ready()
        assert not model_gateway.model_reachable()


def test_groq_configuration_pins_endpoint_and_model():
    assert config.MODEL_PROVIDER != 'groq' or (config.MODEL_BASE_URL == 'https://api.groq.com/openai/v1' and config.MODEL_NAME == 'openai/gpt-oss-120b')
    assert 'GROQ_API_KEY' not in (ROOT / 'CorePulse_AI_Server/.env.example').read_text() or 'GROQ_API_KEY=' in (ROOT / 'CorePulse_AI_Server/.env.example').read_text()


class FakeHTTPResponse:
    status = 200
    def __init__(self, obj):self.obj=obj
    def __enter__(self):return self
    def __exit__(self,*a):return False
    def read(self,*a):return json.dumps(self.obj).encode('utf8')


def test_real_groq_request_format_mocked_without_network():
    captured=[]
    def intercept(req, timeout=0):
        captured.append((req.full_url, dict(req.headers), json.loads(req.data), timeout))
        return FakeHTTPResponse({'choices':[{'message':{'content':'Temperatura CPU: N/A.'}}]})
    with patch.object(model_gateway,'MODEL_PROVIDER','groq'), patch.object(model_gateway,'MODEL_BASE_URL','https://api.groq.com/openai/v1'), patch.object(model_gateway,'MODEL_NAME','openai/gpt-oss-120b'), patch.object(model_gateway,'MODEL_API_KEY','gsk_FAKE_NOT_REAL'), patch.object(model_gateway.urllib.request,'urlopen',side_effect=intercept):
        actual=model_gateway.generate({'cpu':{'temperature_c':None}},'¿Temperatura CPU?')
    assert actual=='Temperatura CPU: N/A.'
    url,headers,data,timeout=captured[0]
    assert url=='https://api.groq.com/openai/v1/chat/completions'
    assert headers['Authorization']=='Bearer gsk_FAKE_NOT_REAL'
    assert data['model']=='openai/gpt-oss-120b'
    assert data['reasoning_effort']=='low'
    assert data['stream'] is False
    assert 'N/A' in data['messages'][-1]['content'] or 'null' in data['messages'][-1]['content']
    assert timeout>=5


def test_backend_filter_still_discards_hallucinated_groq_response(tmp_path, monkeypatch):
    monkeypatch.setattr(store,'DB_PATH',tmp_path/'tokens.sqlite3')
    monkeypatch.setattr(main,'DEDUP_SECONDS',0)
    main._recent_responses.clear()
    code,_=store.issue_pairing_code(minutes=2)
    with TestClient(main.app) as client:
        registration=client.post('/v1/register',json={'installation_id':'test-groq-v463'},headers={'X-CorePulse-Enrollment':code})
        assert registration.status_code==200
        token=registration.json()['token']
        with patch.object(main,'model_ready',return_value=True),patch.object(main,'generate',return_value='Tu CPU está a 999 °C, averiada definitivamente.'):
            response=client.post('/v1/chat',json={'context':{'cpu':{'temperature_c':None}},'question':'¿Cuál es la temperatura?'},headers={'Authorization':'Bearer '+token})
        assert response.status_code==200
        j=response.json()
        assert j['mode']=='evidence_fallback'
        assert '999' not in j['text']
        assert 'N/A' in j['text']


def test_bridge_client_uses_no_proxy_and_no_redirects():
    class DummyOpener:
        def open(self, req, timeout=0):
            assert req.full_url=='http://127.0.0.1:8765/v1/status'
            return FakeHTTPResponse({'ok':True,'model_ready':False})
    with patch.object(ai_client,'load_ai_enabled',return_value=True), patch.object(ai_client.urllib.request,'build_opener',return_value=DummyOpener()) as factory:
        response=ai_client.service_status(trial_settings())
    assert response['ok'] is True
    assert response['base_url']==ai_client.LOCAL_GROQ_BRIDGE_URL
    assert factory.called


def test_no_hardcoded_groq_secret():
    for relative in ['CorePulse_AI_Server/app/config.py','CorePulse_AI_Server/app/model_gateway.py','gui/ai_panel.py']:
        contents=(ROOT/relative).read_text(encoding='utf8')
        assert 'gsk_' not in contents


def test_groq_provider_env_pins_url_and_does_not_require_credential_file():
    """Configuración del proceso real en aislamiento, sin llamada de red."""
    import subprocess
    environment = os.environ.copy()
    environment.update({'COREPULSE_MODEL_PROVIDER': 'groq',
                        'GROQ_API_KEY': 'gsk_FAKE_TEST_ONLY',
                        'COREPULSE_MODEL_BASE_URL': 'https://evil.example/v1',
                        'COREPULSE_MODEL_NAME': 'evil'})
    code = ('from app.config import MODEL_BASE_URL,MODEL_NAME,MODEL_PROVIDER,MODEL_API_KEY;'
            'from app.model_gateway import model_ready;'
            'assert MODEL_PROVIDER=="groq";'
            'assert MODEL_BASE_URL=="https://api.groq.com/openai/v1";'
            'assert MODEL_NAME=="openai/gpt-oss-120b";'
            'assert MODEL_API_KEY=="gsk_FAKE_TEST_ONLY";'
            'assert model_ready(); print("GROQ_CONFIG_OK")')
    run = subprocess.run([sys.executable,'-c',code],cwd=SERVER,
                         env=environment, capture_output=True,text=True,timeout=10)
    assert run.returncode==0,run.stderr
    assert run.stdout.strip()=='GROQ_CONFIG_OK'


def test_synthetic_groq_probe_requires_explicit_api_credential(capsys):
    from app import groq_probe
    with patch.object(groq_probe,'model_ready',return_value=False),patch.object(groq_probe,'generate',side_effect=AssertionError('Sin tráfico')):
        assert groq_probe.main()==2
    assert 'Falta la clave' in capsys.readouterr().out

