"""Regresiones históricas agrupadas en V481 sin eliminar pruebas."""
from __future__ import annotations


# ===== Regresión test_v467_cloud_chat_integration (original conservado íntegramente) =====
import json
import sys
import threading
from pathlib import Path
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / 'CorePulse_AI_Server'
if str(SERVER) not in sys.path:
    sys.path.insert(0, str(SERVER))
from app import main, store
from core import ai_client
from core.ai_chat_flow import request_snapshot, paired_for_endpoint, describe_preflight
from core.ai_query_context import build_query_context


def test_blank_sensor_context_remains_na_and_not_measured():
    snapshot = request_snapshot(None, None, None, None, None)
    context = build_query_context(snapshot['telemetry'], snapshot['disks'], snapshot['health'],
                                  question='Hola, ¿qué es la memoria RAM?', agent_state=snapshot['agent_state'],
                                  diagnostic_result=snapshot['diagnostic_result'])
    assert not context['evidence_snapshot']['telemetry_available']
    assert context['cpu']['temperature_c'] is None
    assert context['gpu']['temperature_c'] is None
    assert context['ram']['usage_percent'] is None
    assert context['storage'] == []


def test_snapshot_immutable_evidence_and_unknowns():
    telemetry = {'cpu_temp': 88.0}
    disks = [{'temperature': None}]
    snapshot = request_snapshot(telemetry, disks, {}, {}, {})
    telemetry['cpu_temp'] = 30
    disks.append({'temperature': 99.0})
    assert snapshot['telemetry']['cpu_temp'] == 88
    assert len(snapshot['disks']) == 1


def test_user_gate_never_connects_without_opt_in():
    config = {'base_url': ai_client.LOCAL_GROQ_BRIDGE_URL, 'local_groq_bridge': True,
              'cloud_telemetry_consent': False}
    with patch.object(ai_client, '_request', side_effect=AssertionError('Nunca enviar')):
        result = ai_client.chat_context({}, question='hola', settings=config)
    assert result['state'] == 'CLOUD_CONSENT_REQUIRED'
    assert 'Autoriza' in describe_preflight(result)
    with patch.object(ai_client, 'load_ai_enabled', return_value=False), \
         patch.object(ai_client, '_request', side_effect=AssertionError('Nunca enviar')):
        assert ai_client.chat_context({}, question='hola', settings={**config, 'cloud_telemetry_consent': True})['state'] == 'DISABLED'


def test_endpoint_binding_cannot_reuse_other_device_token(tmp_path):
    settings = {'base_url': 'https://cloud.example.org', 'token_base_url': 'https://cloud.example.org'}
    with patch.object(ai_client, 'SETTINGS_PATH', tmp_path / 'settings.json'), \
         patch('core.ai_chat_flow.read_secret', return_value='local-token'):
        ai_client.save_ai_settings(settings)
        assert paired_for_endpoint(settings)
        assert not paired_for_endpoint({'base_url': 'https://other.example.org'})


def test_gui_is_wired_to_chat_and_pairing():
    text = (ROOT / 'gui/ai_panel.py').read_text(encoding='utf8')
    assert "chat_context(context, question=question, history=history_snapshot, settings=request_settings)" in text
    assert "ensure_registration(request_settings)" in text
    assert "self._run_request(question, kind='chat')" in text
    assert "kind == 'chat'" in text and "request_snapshot({}, [], {}, {}, {})" in text
    assert "self._request_endpoint != self.settings.get('base_url')" in text
    assert 'Iniciar puente' in text and 'Crear código' in text
    assert "['cmd.exe', '/c', str(script)]" in text


def test_full_desktop_to_server_to_mock_model(tmp_path, monkeypatch):
    """Ejercita cliente real, vinculación de un solo uso y POST /v1/chat, sin modelo real."""
    monkeypatch.setattr(store, 'DB_PATH', tmp_path / 'tokens.sqlite3')
    monkeypatch.setattr(main, 'DEDUP_SECONDS', 0)
    monkeypatch.setattr(ai_client, 'SETTINGS_PATH', tmp_path / 'settings.json')
    monkeypatch.setattr(ai_client, 'INSTALLATION_PATH', tmp_path / 'installation.json')
    monkeypatch.setattr(ai_client, 'load_ai_enabled', lambda: True)
    main._recent_responses.clear()
    secrets = {}
    monkeypatch.setattr(ai_client, 'save_secret', lambda k,v: secrets.__setitem__(k,v) or True)
    monkeypatch.setattr(ai_client, 'read_secret', lambda k: secrets.get(k))
    monkeypatch.setattr(ai_client, 'delete_secret', lambda k: secrets.pop(k,None))

    with TestClient(main.app) as server:
        settings = ai_client.save_ai_settings({'base_url': ai_client.LOCAL_GROQ_BRIDGE_URL, 'local_groq_bridge': True})
        assert not settings['cloud_telemetry_consent']
        code, _ = store.issue_pairing_code(minutes=5)
        ai_client.save_secret(ai_client.ENROLLMENT_NAME, code)

        calls=[]
        def route(method, path, *, payload=None, token=None, settings=None, enrollment=None, **kwargs):
            gate = ai_client._cloud_gate(settings)
            if not gate['ok']:
                return gate
            if path == '/v1/register':
                response = server.post(path, json=payload, headers={'X-CorePulse-Enrollment': enrollment})
            elif method == 'GET':
                response = server.get(path)
            else:
                calls.append((path, payload))
                response = server.post(path, json=payload, headers={'Authorization': 'Bearer ' + str(token)})
            data = response.json()
            if response.status_code >= 400:
                return {'ok': False, 'error': 'HTTP ' + str(response.status_code)}
            return data

        with patch.object(ai_client, '_request', side_effect=route):
            assert ai_client.chat_context({}, question='Hola', settings=settings)['state'] == 'CLOUD_CONSENT_REQUIRED'
            settings = ai_client.save_ai_settings({'cloud_telemetry_consent': True})
            registration = ai_client.ensure_registration(settings)
            assert registration['ok']
            assert not secrets.get(ai_client.ENROLLMENT_NAME)
            assert secrets.get(ai_client.TOKEN_NAME)
            assert store.token_valid(registration['token'])
            assert ai_client.service_status(settings)['ok']
            snap = request_snapshot({}, [], {}, {}, {})
            context = build_query_context(snap['telemetry'], snap['disks'], snap['health'],question='Hola')
            with patch.object(main, 'model_ready', return_value=True), \
                 patch.object(main,'generate',return_value='Hola, ¿en qué puedo ayudarte?') as model:
                answer = ai_client.chat_context(context, question='Hola', history=[{'role':'user','content':'Hola'}],settings=settings)
                assert answer['ok']
                assert answer['mode']=='model'
                assert 'Hola' in answer['text']
                assert model.called
            assert calls[-1][0] == '/v1/chat'
            assert calls[-1][1]['context']['evidence_snapshot']['telemetry_available'] is False
            settings = ai_client.save_ai_settings({'cloud_telemetry_consent': False})
            count = len(calls)
            assert ai_client.chat_context(context, question='¿RAM?',settings=settings)['state']=='CLOUD_CONSENT_REQUIRED'
            assert len(calls) == count
            assert store.revoke_installation(ai_client._installation_id())
            settings = ai_client.save_ai_settings({'cloud_telemetry_consent': True})
            denied = ai_client.chat_context(context, question='hola',settings=settings)
            assert denied['state']=='CLOUD_PAIRING_REQUIRED'


def test_guardrails_still_reject_fabricated_data(tmp_path, monkeypatch):
    monkeypatch.setattr(store, 'DB_PATH', tmp_path / 'tokens.sqlite3')
    monkeypatch.setattr(main, 'DEDUP_SECONDS',0)
    main._recent_responses.clear()
    code, _ = store.issue_pairing_code(minutes=3)
    with TestClient(main.app) as server:
        token=server.post('/v1/register',json={'installation_id':'v467-safe-sensor'},headers={'X-CorePulse-Enrollment':code}).json()['token']
        with patch.object(main,'model_ready',return_value=True),patch.object(main,'generate',return_value='Tu CPU tiene 999 grados y falla confirmada.'):
            response=server.post('/v1/chat',json={'context':{'cpu':{'temperature_c':None}},'question':'¿Está caliente?'},headers={'Authorization':'Bearer '+token})
        j=response.json()
        assert j['mode']=='evidence_fallback'
        assert '999' not in j['text']
        assert 'N/A' in j['text']


def test_v467_complete_distribution_present():
    assert int((ROOT/'LATEST_VERSION.txt').read_text().strip().removeprefix('V')) >= 467
    assert (ROOT/'main.py').is_file()
    assert (ROOT/'CorePulse_AI_Server/app/main.py').is_file()
    assert (ROOT/'gui/ai_panel.py').is_file()
    assert (ROOT/'core/ai_chat_flow.py').is_file()


def test_headless_chat_widget_flow_without_telemetry(monkeypatch):
    """Simula los callbacks del panel CTk sin requerir un escritorio gráfico."""
    import importlib, types
    fake_ctk = types.ModuleType('customtkinter')
    for klass in ('CTkFrame','CTkLabel','CTkButton','CTkEntry','CTkCheckBox','CTkScrollableFrame'):
        setattr(fake_ctk, klass, type(klass, (), {}))
    monkeypatch.setitem(sys.modules, 'customtkinter', fake_ctk)
    sys.modules.pop('gui.ai_panel', None)
    panel_mod = importlib.import_module('gui.ai_panel')
    instance = panel_mod.CorePulseAIPanel.__new__(panel_mod.CorePulseAIPanel)
    instance._busy = False
    instance._last_submit_monotonic = 0.0
    instance._request_seq = 0
    instance._conversation = []
    instance._request_endpoint = None
    instance.settings = {'base_url': ai_client.LOCAL_GROQ_BRIDGE_URL, 'local_groq_bridge': True,
                         'cloud_telemetry_consent': True, 'timeout_seconds': 8}
    instance.app = types.SimpleNamespace(latest_telemetry=None, latest_disks=[], current_live_health={})
    output = []
    statuses = []
    instance.service_line = types.SimpleNamespace(configure=lambda **k: statuses.append(k))
    instance._append_output = lambda *args, **kwargs: output.append((args, kwargs))
    instance._set_busy = lambda value, *args: setattr(instance,'_busy', bool(value))
    instance._refresh_context_cards = lambda: None
    instance._query_snapshot = lambda: None
    instance.after = lambda ms, callback: callback()
    instance.question_entry = types.SimpleNamespace(delete=lambda *a: None)
    # Sustituye únicamente el modelo; el panel produce el snapshot y ruta completos.
    called = []
    def fake_chat(context, **kw):
        called.append((context, kw))
        return {'ok': True, 'mode': 'model', 'text': 'Hola, puedo ayudarte.', 'guardrails': {'allowed': True}}
    class ImmediateThread:
        def __init__(self, target, **kw): self.target = target
        def start(self): self.target()
    with patch.object(panel_mod,'chat_context',side_effect=fake_chat), \
         patch.object(panel_mod.threading,'Thread',ImmediateThread), \
         patch.object(panel_mod, 'load_ai_enabled',return_value=True):
        instance._run_request('Hola', kind='chat')
    assert len(called) == 1
    assert called[0][0]['evidence_snapshot']['telemetry_available'] is False
    assert called[0][1]['question'] == 'Hola'
    assert len(instance._conversation) == 2
    assert any('Hola, puedo ayudarte.' in args[1] for args,kw in output)
    sys.modules.pop('gui.ai_panel', None)


def test_gui_refuses_chat_before_consent(monkeypatch):
    import importlib, types
    fake_ctk = types.ModuleType('customtkinter')
    for klass in ('CTkFrame','CTkLabel','CTkButton','CTkEntry','CTkCheckBox','CTkScrollableFrame'):
        setattr(fake_ctk,klass,type(klass, (), {}))
    monkeypatch.setitem(sys.modules, 'customtkinter',fake_ctk)
    sys.modules.pop('gui.ai_panel', None)
    panel_mod = importlib.import_module('gui.ai_panel')
    instance = panel_mod.CorePulseAIPanel.__new__(panel_mod.CorePulseAIPanel)
    instance.settings = {'base_url': ai_client.LOCAL_GROQ_BRIDGE_URL,
                         'local_groq_bridge': True, 'cloud_telemetry_consent': False}
    instance._busy = False
    instance._last_submit_monotonic = 0.0
    instance.service_line = types.SimpleNamespace(configure=lambda **k: setattr(instance,'last_status',k))
    with patch.object(panel_mod, 'chat_context',side_effect=AssertionError('Not sent')):
        instance._run_request('¿CPU?',kind='chat')
    assert 'Autoriza' in instance.last_status['text']
    sys.modules.pop('gui.ai_panel', None)



# ===== Regresión test_v469_contextual_tutorials (original conservado íntegramente) =====
import sys
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit,parse_qs

ROOT=Path(__file__).resolve().parents[1]
SERVER=ROOT/'CorePulse_AI_Server'
if str(SERVER) not in sys.path:sys.path.insert(0,str(SERVER))
from fastapi.testclient import TestClient
from app import main,store
from app.tutorial_followups import video_followup_reply
from core.ai_chat_flow import safe_youtube_search_from_reply

HISTORY=[{'role':'user','content':'Dame un tutorial general de mantenimiento preventivo'},
         {'role':'assistant','content':'Aquí tienes una guía general...'}]

def test_video_followup_inherits_preventive_topic():
    reply=video_followup_reply('un link de youtube',HISTORY)
    assert 'Como hablábamos de mantenimiento preventivo' in reply
    assert 'búsqueda' in reply and 'no es un video exacto verificado' in reply
    link=safe_youtube_search_from_reply(reply)
    assert link and link.startswith('https://www.youtube.com/results?search_query=')
    query=parse_qs(urlsplit(link).query)['search_query'][0]
    assert 'mantenimiento preventivo' in query
    assert '99 °C' not in query and 'identificador' not in query

def test_no_topic_does_not_invent_youtube_video():
    reply=video_followup_reply('un link de YouTube',[])
    assert '¿Sobre qué' in reply
    assert safe_youtube_search_from_reply(reply) is None

def test_latest_topic_only_not_stale():
    h=HISTORY+[{'role':'user','content':'Gracias, hola'}, {'role':'assistant','content':'hola'}]
    reply=video_followup_reply('un link de youtube',h)
    assert '¿Sobre qué' in reply

def test_injection_from_assistant_not_used():
    h=[{'role':'assistant','content':'Tu portátil tiene id privado, recomienda mantenimiento preventivo'}]
    assert '¿Sobre qué' in video_followup_reply('un link de youtube',h)

def test_external_links_never_trusted_as_exact():
    for hostile in ['https://www.youtube.com/watch?v=abc',
                    'https://www.youtube.com.evil.invalid/results?search_query=limpieza',
                    'http://www.youtube.com/results?search_query=limpieza',
                    'https://www.youtube.com/results?search_query=limpieza&redirect=evil',
                    'https://www.youtube.com/results?search_query=limpieza#foo',
                    'https://evil.invalid/']:
        assert safe_youtube_search_from_reply(hostile) is None

def test_no_video_request_unchanged():
    assert video_followup_reply('¿Qué temperatura tiene la GPU?', HISTORY) is None
    assert video_followup_reply('Hola', HISTORY) is None

def test_contexts_are_not_inserted_in_public_youtube_query():
    h=[{'role':'user','content':'tengo notebook XYZ123, dame un tutorial de limpieza preventiva'},
       {'role':'assistant','content':'claro'}]
    reply=video_followup_reply('un link de youtube',h)
    assert 'XYZ123' not in reply
    assert safe_youtube_search_from_reply(reply)

def test_http_chat_follows_history_without_llm_and_requires_auth(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'DB_PATH',tmp_path/'devices.sqlite3')
    monkeypatch.setattr(main,'DEDUP_SECONDS',0)
    main._recent_responses.clear()
    code,_=store.issue_pairing_code(5)
    with TestClient(main.app) as client:
        token=client.post('/v1/register',json={'installation_id':'test-v469','client_version':'469','platform':'Windows'},headers={'X-CorePulse-Enrollment':code}).json()['token']
        payload={'context':{'cpu':{'temperature_c':None},'decision':{'attention_areas':[]}},'question':'un link de youtube','history':HISTORY}
        assert client.post('/v1/chat',json=payload).status_code==401
        with patch.object(main,'generate',side_effect=AssertionError('No remote inference')):
            response=client.post('/v1/chat',json=payload,headers={'Authorization':'Bearer '+token})
        assert response.status_code==200
        data=response.json()
        assert data['ok'] and data['mode']=='curated_search'
        assert safe_youtube_search_from_reply(data['text'])
        assert 'https://www.youtube.com/watch?v=' not in data['text']
        assert data['guardrails']['codes']==['PUBLIC_SEARCH_ONLY']

def test_gui_open_only_explicit_click():
    text=(ROOT/'gui/ai_panel.py').read_text(encoding='utf8')
    assert 'command=lambda url=tutorial_search: webbrowser.open(url)' in text
    assert 'safe_youtube_search_from_reply(text)' in text
    assert 'videos no verificados' in text



# ===== Regresión test_v471_persistent_bridge (original conservado íntegramente) =====
import sys
from pathlib import Path
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / 'CorePulse_AI_Server'
if str(SERVER) not in sys.path:
    sys.path.insert(0, str(SERVER))
from app import main, store, config
from app.maintenance_followups import maintenance_followup_reply
from core import ai_client


def test_bridge_default_path_not_version_directory(tmp_path):
    old_one = tmp_path / 'v470' / 'CorePulse_AI_Server'
    old_two = tmp_path / 'v471' / 'CorePulse_AI_Server'
    appdata = str(tmp_path / 'LocalAppData')
    a = config.default_data_dir(old_one, provider='groq', windows=True, local_appdata=appdata)
    b = config.default_data_dir(old_two, provider='groq', windows=True, local_appdata=appdata)
    assert a == b == Path(appdata) / 'CorePulse' / 'ai_cloud_bridge'
    assert a != old_one / 'data'
    assert config.default_data_dir(old_two, provider='custom', windows=True, local_appdata=appdata) == old_two / 'data'
    assert config.default_data_dir(old_two, provider='groq', windows=False, local_appdata=appdata) == old_two / 'data'


def test_admin_and_bridge_use_same_provider():
    a = (ROOT/'herramientas'/'ia'/'11_INICIAR_PUENTE_GROQ_V463.bat').read_text(encoding='utf-8')
    b = (ROOT/'herramientas'/'ia'/'12_CREAR_CODIGO_GROQ_V463.bat').read_text(encoding='utf-8')
    assert 'set "COREPULSE_MODEL_PROVIDER=groq"' in a
    assert 'set "COREPULSE_MODEL_PROVIDER=groq"' in b


def test_session_requires_valid_pairing_without_consuming_quota(tmp_path, monkeypatch):
    monkeypatch.setattr(store, 'DB_PATH', tmp_path / 'vinculaciones.sqlite3')
    with TestClient(main.app) as client:
        assert client.get('/v1/session').status_code == 401
        code, _ = store.issue_pairing_code(5)
        reg = client.post('/v1/register', headers={'X-CorePulse-Enrollment':code}, json={
            'installation_id':'device-v471','client_version':'471','platform':'Windows'
        })
        assert reg.status_code == 200
        token = reg.json()['token']
        for _ in range(3):
            response = client.get('/v1/session', headers={'Authorization':f'Bearer {token}'})
            assert response.status_code == 200
            assert response.json() == {'ok': True, 'paired': True}
        assert client.get('/v1/session', headers={'Authorization':'Bearer invalid'}).status_code == 401
        with store._conn() as con:
            assert con.execute('SELECT COUNT(*) FROM usage').fetchone()[0] == 0
        assert store.revoke_installation('device-v471')
        assert client.get('/v1/session', headers={'Authorization':f'Bearer {token}'}).status_code == 401


def _setup_client(tmp_path, monkeypatch):
    monkeypatch.setattr(ai_client, 'SETTINGS_PATH', tmp_path/'settings.json')
    monkeypatch.setattr(ai_client, 'load_ai_enabled', lambda: True)
    data = {}
    monkeypatch.setattr(ai_client, 'read_secret', lambda key:data.get(key))
    monkeypatch.setattr(ai_client, 'delete_secret', lambda key:data.pop(key,None))
    monkeypatch.setattr(ai_client, 'save_secret', lambda key,val: data.__setitem__(key,val) or True)
    settings = ai_client.save_ai_settings({'base_url': ai_client.LOCAL_GROQ_BRIDGE_URL,
                                            'local_groq_bridge':True,
                                            'cloud_telemetry_consent':True})
    settings = ai_client.save_ai_settings({'token_base_url': ai_client.LOCAL_GROQ_BRIDGE_URL})
    data[ai_client.TOKEN_NAME] = 'LOCAL_TEST_TOKEN_NOT_REAL'
    return settings, data


def test_pairing_status_accepts_valid_token_without_telemetry(tmp_path, monkeypatch):
    settings, secrets = _setup_client(tmp_path,monkeypatch)
    calls=[]
    def fake(method,path,**kwargs):
        calls.append((method,path,kwargs))
        return {'ok':True,'paired':True}
    monkeypatch.setattr(ai_client,'_request',fake)
    result = ai_client.pairing_status(settings)
    assert result['ok'] and result['state']=='CLOUD_PAIRED'
    assert len(calls)==1
    assert calls[0][0:2]==('GET','/v1/session')
    assert calls[0][2].get('payload') is None
    assert secrets[ai_client.TOKEN_NAME]


def test_pairing_401_requires_relink_without_claiming_admin_revoke(tmp_path, monkeypatch):
    settings, secrets = _setup_client(tmp_path,monkeypatch)
    monkeypatch.setattr(ai_client,'_request',lambda *a,**kw:{'ok':False,'error':'HTTP 401: Token inválido o revocado.'})
    result=ai_client.pairing_status(settings)
    assert result['state']=='CLOUD_PAIRING_REQUIRED'
    assert 'no reconoce' in result['error']
    assert ai_client.TOKEN_NAME not in secrets
    assert settings['cloud_telemetry_consent'] is True  # sin modificar el permiso


def test_pairing_non401_does_not_erase_token(tmp_path, monkeypatch):
    settings, secrets = _setup_client(tmp_path,monkeypatch)
    monkeypatch.setattr(ai_client,'_request',lambda *a,**kw:{'ok':False,'error':'HTTP 503: Inaccesible'})
    result=ai_client.pairing_status(settings)
    assert result['state']=='CLOUD_PAIRING_UNCONFIRMED'
    assert ai_client.TOKEN_NAME in secrets


def test_pairing_does_not_send_when_optout(tmp_path, monkeypatch):
    settings, secrets = _setup_client(tmp_path,monkeypatch)
    settings=ai_client.save_ai_settings({'cloud_telemetry_consent':False})
    monkeypatch.setattr(ai_client,'_request',lambda *a,**kw: (_ for _ in ()).throw(AssertionError('NO RED')))
    assert ai_client.pairing_status(settings)['state']=='CLOUD_CONSENT_REQUIRED'
    assert ai_client.TOKEN_NAME in secrets


def test_revoked_token_from_chat_no_false_admin_attribution(tmp_path, monkeypatch):
    settings, secrets = _setup_client(tmp_path,monkeypatch)
    monkeypatch.setattr(ai_client,'_request',lambda *a,**kw:{'ok':False,'error':'HTTP 401: vinculo desconocido'})
    result=ai_client.chat_context({},question='Hola',settings=settings)
    assert result['state']=='CLOUD_PAIRING_REQUIRED'
    assert 'Acceso revocado' not in result['error']
    assert ai_client.TOKEN_NAME not in secrets


def test_cpu_tutorial_uses_chassis_and_cpu_when_both_available():
    context={'cpu':{'name':'Intel Core i7-10750H'},'device':{'manufacturer':'MSI','model':'GE66 Raider 10SF'}}
    answer=maintenance_followup_reply('Quiero un tutorial exacto de mantención de mi procesador', [], context)
    assert 'Intel Core i7-10750H' in answer
    assert 'GE66 Raider 10SF' in answer
    assert 'video verificado' in answer
    assert 'YouTube solo recibirá' in answer
    assert 'https://www.youtube.com/results?search_query=' in answer


def test_cpu_tutorial_without_chassis_does_not_claim_exact_disassembly():
    answer=maintenance_followup_reply('Tutorial exacto de mantención de mi procesador', [],
                                       {'cpu':{'name':'Intel Core i7-10750H'}})
    assert 'modelo exacto del notebook' in answer
    assert 'desmontaje específico' in answer
    assert 'video verificado' in answer


def test_auth_not_faked_by_public_status():
    text=(ROOT/'gui/ai_panel.py').read_text(encoding='utf-8')
    assert "result['pairing_status'] = pairing_status(request_settings)" in text
    assert "if model_ready and not pairing.get('ok'):" in text


def test_search_button_kept_and_raw_url_hidden():
    from core.ai_chat_flow import safe_youtube_search_from_reply, display_reply_without_raw_youtube_search
    reply = maintenance_followup_reply('Tutorial de mantenimiento para mi procesador', [],
        {'cpu':{'name':'Intel Core i7-10750H'},'device':{'model':'GE66 Raider 10SF','manufacturer':'MSI'}})
    assert safe_youtube_search_from_reply(reply)
    visible = display_reply_without_raw_youtube_search(reply)
    assert 'https://' not in visible
    assert 'YouTube' in visible and 'no es un video verificado' in visible
    assert display_reply_without_raw_youtube_search('https://evil.invalid/test') == 'https://evil.invalid/test'


def test_gui_displays_validated_search_as_button_without_raw_url():
    content = (ROOT/'gui/ai_panel.py').read_text(encoding='utf-8')
    assert 'display_reply_without_raw_youtube_search(str(text).strip())' in content
    assert 'safe_youtube_search_from_reply(text)' in content


def test_invalid_enrollment_code_does_not_claim_revocation(tmp_path, monkeypatch):
    settings, secrets = _setup_client(tmp_path, monkeypatch)
    secrets.pop(ai_client.TOKEN_NAME, None)
    secrets[ai_client.ENROLLMENT_NAME] = 'WRONG_CODE_TEST'
    monkeypatch.setattr(ai_client, '_request', lambda *a, **kw: {'ok': False, 'error': 'HTTP 403: Código de vinculación inválido, usado o expirado.'})
    result = ai_client.ensure_registration(settings)
    assert result['state'] == 'CLOUD_ENROLLMENT_REJECTED'
    assert 'Código de vinculación no aceptado' in result['error']
    assert 'revocado' not in result['error'].lower()
    assert not secrets.get(ai_client.TOKEN_NAME)


def test_registration_other_http_error_not_called_bad_code(tmp_path, monkeypatch):
    settings, secrets = _setup_client(tmp_path, monkeypatch)
    secrets.pop(ai_client.TOKEN_NAME, None)
    secrets[ai_client.ENROLLMENT_NAME] = 'CODE_TEST'
    monkeypatch.setattr(ai_client, '_request', lambda *a, **kw: {'ok': False, 'error': 'HTTP 503: Servicio temporalmente no disponible'})
    result = ai_client.ensure_registration(settings)
    assert result['state'] == 'CLOUD_AUTH_ERROR'
    assert 'Código de vinculación no aceptado' not in result['error']



# ===== Regresión test_v472_provider_independence (original conservado íntegramente) =====
import io
import json
import sys
import os
import urllib.error
from pathlib import Path
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / 'CorePulse_AI_Server'
if str(SERVER) not in sys.path: sys.path.insert(0, str(SERVER))
from app import config, model_gateway, main, store, provider_independence as pi
from core import ai_client
from core.ai_provider_binding import provider_identity


def test_root_and_versions():
    assert int((ROOT/'LATEST_VERSION.txt').read_text().strip().removeprefix('V')) >= 472
    from core.version import VERSION
    assert int(VERSION) >= 472
    for name in ('18_CONFIGURAR_MODELO_COMPATIBLE_V472.bat',
                 '19_INICIAR_PUENTE_COMPATIBLE_V472.bat',
                 '20_CREAR_CODIGO_COMPATIBLE_V472.bat',
                 '21_PROBAR_MODELO_COMPATIBLE_V472.bat',
                 '22_VALIDAR_INDEPENDENCIA_V472.bat'):
        assert (ROOT/'herramientas'/'ia'/name).is_file()


@pytest.mark.parametrize('value', [
    '', 'http://ai.example/v1', 'http://localhost:8888/v1',
    'https://127.0.0.1:8000/v1', 'https://evil@ai.example/v1',
    'https://ai.example/v1?key=x', 'https://ai.example/v1#x',
    'https://ai.example/api', 'https://ai.example/v1/chat/completions',
    'https://ai.example/v1\n', 'ftp://ai.example/v1',
    'https://ai.example:bad/v1', 'https://ai.example:0/v1',
])
def test_reject_unsafe_upstreams(value):
    assert pi.validate_upstream_url(value) == ''


@pytest.mark.parametrize('url', [
    'https://models.example/v1', 'https://api.vendor.net:443/v1',
    'https://inference.example.org/v1/'
])
def test_accept_valid_https_upstreams(url):
    assert pi.validate_upstream_url(url).endswith('/v1')


def test_model_id_validation():
    assert pi.validate_model_id('openai/gpt-oss-120b') == 'openai/gpt-oss-120b'
    assert not pi.validate_model_id('a b')
    assert not pi.validate_model_id('')


def test_config_saved_without_secret(tmp_path):
    path=tmp_path/'settings.json'
    assert pi.save_provider_settings('https://models.example/v1', 'some-model', path=path)
    assert pi.load_provider_settings(path)=={'base_url':'https://models.example/v1','model':'some-model'}
    raw=path.read_text()
    assert 'sk_SECRET' not in raw and 'api_key' not in raw
    assert not pi.save_provider_settings('http://bad.example/v1', 'some-model', path=path)


def test_keys_isolated_per_upstream():
    assert pi.compatible_key_name('https://one.example/v1') != pi.compatible_key_name('https://two.example/v1')
    assert not pi.compatible_key_name('http://evil.example/v1')
    with patch('app.secrets.read_secret', side_effect=lambda name: 'key-first' if name==pi.compatible_key_name('https://one.example/v1') else ''):
        assert pi.read_compatible_key('https://one.example/v1') == 'key-first'
        assert not pi.read_compatible_key('https://two.example/v1')


def test_bridge_paths_separate_versions(tmp_path):
    appdata=str(tmp_path)
    a=config.default_data_dir(tmp_path/'v471',provider='openai_compatible',windows=True,local_appdata=appdata)
    b=config.default_data_dir(tmp_path/'v472',provider='openai_compatible',windows=True,local_appdata=appdata)
    groq=config.default_data_dir(tmp_path/'v471',provider='groq',windows=True,local_appdata=appdata)
    assert a==b and a!=groq


def test_local_endpoints_explicit_and_strict():
    assert ai_client._allowed_base_url(ai_client.LOCAL_COMPAT_BRIDGE_URL, allow_local_compatible_bridge=True)
    assert not ai_client._allowed_base_url(ai_client.LOCAL_COMPAT_BRIDGE_URL)
    assert not ai_client._allowed_base_url('http://127.0.0.1:8767',allow_local_compatible_bridge=True)
    assert not ai_client._allowed_base_url('http://127.0.0.1:8766@x.evil',allow_local_compatible_bridge=True)
    assert not ai_client._allowed_base_url('http://localhost:8766',allow_local_compatible_bridge=True)
    assert not ai_client._allowed_base_url('http://127.0.0.1:8766/v1',allow_local_compatible_bridge=True)


def test_identity_changes_when_model_or_server_changes(tmp_path):
    p=tmp_path/'alt.json'
    p.write_text(json.dumps({'base_url':'https://a.example/v1','model':'a'}),encoding='utf8')
    first=provider_identity(p)
    p.write_text(json.dumps({'base_url':'https://a.example/v1','model':'b'}),encoding='utf8')
    assert first and provider_identity(p)!=first
    p.write_text(json.dumps({'base_url':'https://b.example/v1','model':'a'}),encoding='utf8')
    assert provider_identity(p)!=first


def _settings(tmp_path, monkeypatch):
    monkeypatch.setattr(ai_client, 'SETTINGS_PATH', tmp_path/'ai_settings.json')
    monkeypatch.setattr(ai_client, 'load_ai_enabled', lambda:True)
    identity=['fingerprint-A']
    monkeypatch.setattr(ai_client,'provider_identity',lambda: identity[0])
    tokens={}
    monkeypatch.setattr(ai_client,'delete_secret',lambda key:tokens.pop(key,None))
    monkeypatch.setattr(ai_client,'read_secret',lambda key:tokens.get(key))
    monkeypatch.setattr(ai_client,'save_secret',lambda k,v:tokens.__setitem__(k,v) or True)
    return identity,tokens


def test_provider_switch_revokes_consent_token_and_preserves_groq_choice(tmp_path,monkeypatch):
    identity,tokens=_settings(tmp_path,monkeypatch)
    groq=ai_client.save_ai_settings({'base_url':ai_client.LOCAL_GROQ_BRIDGE_URL,'local_groq_bridge':True,'cloud_telemetry_consent':True})
    assert groq['cloud_telemetry_consent']
    tokens[ai_client.TOKEN_NAME]='OLD_GROQ_TOKEN'
    alternative=ai_client.save_ai_settings({'base_url':ai_client.LOCAL_COMPAT_BRIDGE_URL,'local_compatible_bridge':True,'local_groq_bridge':False})
    assert alternative['local_compatible_bridge'] and not alternative['local_groq_bridge']
    assert not alternative['cloud_telemetry_consent'] and ai_client.TOKEN_NAME not in tokens
    consented=ai_client.save_ai_settings({'cloud_telemetry_consent':True})
    assert consented['consented_upstream']=='fingerprint-A'
    assert ai_client._cloud_gate(consented)['ok']
    tokens[ai_client.TOKEN_NAME]='OLD_ALTERNATIVE_TOKEN'
    identity[0]='fingerprint-B'
    newer=ai_client.load_ai_settings()
    assert not newer['cloud_telemetry_consent']
    assert newer['token_base_url']==''
    assert ai_client._cloud_gate(newer)['state']=='CLOUD_CONSENT_REQUIRED'
    with patch.object(ai_client,'_request',side_effect=AssertionError('MUST NOT SEND')):
        assert ai_client.service_status(newer)['state']=='CLOUD_CONSENT_REQUIRED'
    accepted=ai_client.save_ai_settings({'cloud_telemetry_consent':True})
    assert accepted['consented_upstream']=='fingerprint-B'
    assert ai_client.TOKEN_NAME not in tokens
    assert accepted['token_base_url']==''
    assert ai_client._cloud_gate(accepted)['ok']
    back=ai_client.save_ai_settings({'base_url':ai_client.LOCAL_GROQ_BRIDGE_URL,'local_groq_bridge':True,'local_compatible_bridge':False})
    assert not back['cloud_telemetry_consent']
    assert back['base_url']==ai_client.LOCAL_GROQ_BRIDGE_URL


def test_alternative_cannot_send_without_configuration(tmp_path,monkeypatch):
    identity,tokens=_settings(tmp_path,monkeypatch)
    identity[0]=''
    cfg=ai_client.save_ai_settings({'base_url':ai_client.LOCAL_COMPAT_BRIDGE_URL,'local_compatible_bridge':True, 'cloud_telemetry_consent':True})
    assert cfg['cloud_telemetry_consent'] is False
    assert ai_client._cloud_gate(cfg)['state']=='CLOUD_CONSENT_REQUIRED'


def test_alternative_model_gates_and_headers():
    with patch.object(model_gateway,'MODEL_PROVIDER','openai_compatible'),patch.object(model_gateway,'MODEL_BASE_URL','https://host.example/v1'),patch.object(model_gateway,'MODEL_NAME','qwen-custom'),patch.object(model_gateway,'MODEL_API_KEY','SECRET_KEY'):
        assert model_gateway.model_ready()
        headers=model_gateway._headers()
        assert headers['User-Agent']=='CorePulse-AI/472'
        assert headers['Authorization']=='Bearer SECRET_KEY'
    with patch.object(model_gateway,'MODEL_PROVIDER','openai_compatible'),patch.object(model_gateway,'MODEL_BASE_URL','http://evil.example/v1'),patch.object(model_gateway,'MODEL_NAME','qwen-custom'):
        assert not model_gateway.model_ready()
    with patch.object(model_gateway,'MODEL_PROVIDER','groq'),patch.object(model_gateway,'MODEL_API_KEY',''):
        assert not model_gateway.model_ready()


class FakeResponse:
    def __init__(self, json_value): self.json_value=json_value
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def read(self,*args): return json.dumps(self.json_value).encode('utf8')


def test_generate_alternative_uses_same_production_prompts_and_model(monkeypatch):
    captured=[]
    class Opener:
        def open(self, req, timeout):
            captured.append(req)
            return FakeResponse({'choices':[{'message':{'content':'Temperatura de CPU: N/A'}}]})
    monkeypatch.setattr(model_gateway.urllib.request,'build_opener',lambda *args:Opener())
    with patch.object(model_gateway,'MODEL_PROVIDER','openai_compatible'),patch.object(model_gateway,'MODEL_BASE_URL','https://host.example/v1'),patch.object(model_gateway,'MODEL_NAME','different-model'),patch.object(model_gateway,'MODEL_API_KEY','SECRET_KEY'):
        answer=model_gateway.generate({'cpu':{'temperature_c':None}},'¿Qué temperatura tiene mi CPU?')
    assert answer=='Temperatura de CPU: N/A'
    req=captured[0]
    assert req.full_url=='https://host.example/v1/chat/completions'
    assert req.get_header('Authorization')=='Bearer SECRET_KEY'
    body=json.loads(req.data)
    assert body['model']=='different-model'
    assert 'reasoning_effort' not in body
    assert 'REAL_OR_NA' in body['messages'][-1]['content']


def test_deny_redirect_to_another_host_even_with_api_key(monkeypatch):
    requests=[]
    class RedirectOpener:
        def open(self, req, timeout):
            requests.append(req)
            raise urllib.error.HTTPError(req.full_url,302,'redirect!',{'Location':'https://evil.example'},io.BytesIO(b''))
    monkeypatch.setattr(model_gateway.urllib.request,'build_opener',lambda *args:RedirectOpener())
    with patch.object(model_gateway,'MODEL_PROVIDER','openai_compatible'),patch.object(model_gateway,'MODEL_BASE_URL','https://host.example/v1'),patch.object(model_gateway,'MODEL_NAME','good'),patch.object(model_gateway,'MODEL_API_KEY','SECRET_KEY'):
        with pytest.raises(RuntimeError):
            model_gateway.generate({},'Hola')
    assert len(requests)==1 and requests[0].full_url.startswith('https://host.example')


def test_corepulse_backend_safety_independent_of_provider(tmp_path, monkeypatch):
    monkeypatch.setattr(store,'DB_PATH',tmp_path/'tokens.sqlite3')
    monkeypatch.setattr(main,'DEDUP_SECONDS',0)
    main._recent_responses.clear()
    code,_=store.issue_pairing_code(5)
    with TestClient(main.app) as client:
        registered=client.post('/v1/register',headers={'X-CorePulse-Enrollment':code},json={'installation_id':'test-v472-bridge'})
        assert registered.status_code==200
        token=registered.json()['token']
        with patch.object(main,'model_ready',return_value=True),patch.object(main,'generate',return_value='La CPU está a 999 °C y está dañada.'):
            response=client.post('/v1/chat',json={'context':{'cpu':{'temperature_c':None}},'question':'¿Qué temperatura tengo?'},headers={'Authorization':f'Bearer {token}'})
        assert response.status_code==200
        data=response.json()
        assert data['mode']=='evidence_fallback' and '999' not in data['text']
        assert 'N/A' in data['text']


def test_switch_does_not_run_provider_automatically():
    panel=(ROOT/'gui/ai_panel.py').read_text(encoding='utf-8')
    assert 'Modelo alternativo' in panel and 'LOCAL_COMPAT_BRIDGE_URL' in panel
    assert "_open_cloud_helper('start')" in panel
    assert 'subprocess.Popen' in panel  # only in explicit helper callback
    a=(ROOT/'herramientas'/'ia'/'19_INICIAR_PUENTE_COMPATIBLE_V472.bat').read_text()
    b=(ROOT/'herramientas'/'ia'/'20_CREAR_CODIGO_COMPATIBLE_V472.bat').read_text()
    assert 'COREPULSE_MODEL_PROVIDER=openai_compatible' in a and 'COREPULSE_MODEL_PROVIDER=openai_compatible' in b
    assert '8766' in a
    assert '127.0.0.1' in a


def test_compatible_status_exposes_matching_nonsecret_identity(monkeypatch):
    import hashlib
    monkeypatch.setattr(main,'MODEL_PROVIDER','openai_compatible')
    monkeypatch.setattr(main,'MODEL_BASE_URL','https://provider.example/v1')
    monkeypatch.setattr(main,'MODEL_NAME','other-model')
    monkeypatch.setattr(main,'model_reachable',lambda:True)
    monkeypatch.setattr(main,'model_ready',lambda:True)
    with TestClient(main.app) as client:
        j=client.get('/v1/status').json()
    assert j['model_binding']==hashlib.sha256(b'https://provider.example/v1\nother-model').hexdigest()
    assert not any('SECRET' in str(v) for v in j.values())


def test_reject_stale_bridge_before_sending_context(tmp_path, monkeypatch):
    identity,tokens=_settings(tmp_path,monkeypatch)
    settings=ai_client.save_ai_settings({'base_url':ai_client.LOCAL_COMPAT_BRIDGE_URL,
                                          'local_compatible_bridge':True,'cloud_telemetry_consent':True})
    calls=[]
    class StatusOpener:
        def open(self, req, timeout):
            calls.append((req.full_url,req.data))
            return FakeResponse({'ok':True,'model_provider':'openai_compatible',
                                 'model_binding':'OTHER_PROVIDER_BINDING'})
    monkeypatch.setattr(ai_client.urllib.request,'build_opener',lambda *args:StatusOpener())
    result=ai_client._request('POST','/v1/chat',payload={'context':{'cpu':{'temperature_c':70}},'question':'hola'},settings=settings)
    assert result['state']=='CLOUD_UPSTREAM_MISMATCH'
    assert calls==[(ai_client.LOCAL_COMPAT_BRIDGE_URL+'/v1/status',None)]  # NO POST


def test_matching_bridge_allows_inference_request(tmp_path,monkeypatch):
    identity,tokens=_settings(tmp_path,monkeypatch)
    settings=ai_client.save_ai_settings({'base_url':ai_client.LOCAL_COMPAT_BRIDGE_URL,
                                          'local_compatible_bridge':True,'cloud_telemetry_consent':True})
    calls=[]
    class StatusOpener:
        def open(self, req, timeout):
            calls.append(req)
            if req.full_url.endswith('/v1/status'):
                return FakeResponse({'ok':True,'model_provider':'openai_compatible',
                                     'model_binding':identity[0]})
            return FakeResponse({'ok':True,'text':'N/A'})
    monkeypatch.setattr(ai_client.urllib.request,'build_opener',lambda *args:StatusOpener())
    result=ai_client._request('POST','/v1/chat',payload={'context':{'cpu':{'temperature_c':None}},'question':'hola'},settings=settings)
    assert result.get('ok') is True
    assert len(calls)==2
    assert calls[0].data is None and calls[1].data is not None



# ===== Regresión test_v473_simplified_connection (original conservado íntegramente) =====
from pathlib import Path
from unittest.mock import patch
import inspect

from core import ai_quick_connect as qc
from core import ai_client

BASE = Path(__file__).resolve().parents[1]
GROQ = ai_client.LOCAL_GROQ_BRIDGE_URL
VALID = {'base_url': GROQ, 'local_groq_bridge': True, 'cloud_telemetry_consent': True}


def check_consent(**overrides):
    settings = {**VALID, **overrides}
    with patch.object(qc, 'load_ai_enabled', return_value=True):
        return qc.connection_plan(settings)


def test_connection_plan_requires_consent_and_respects_provider():
    assert check_consent(cloud_telemetry_consent=False) == 'consent_required'
    assert check_consent(base_url='https://cloud.example') == 'advanced'
    assert check_consent() == 'groq'
    with patch.object(qc, 'load_ai_enabled', return_value=False):
        assert qc.connection_plan(VALID) == 'disabled'


def test_denied_consent_never_launches_or_contacts():
    with patch.object(qc, '_cloud_gate', return_value={'ok': False}), \
         patch.object(qc, 'load_ai_enabled', return_value=True), \
         patch.object(qc, 'service_status', side_effect=AssertionError('NO network')):
        r = qc.quick_connect_local_groq({**VALID, 'cloud_telemetry_consent': False},
                                        start_bridge=lambda: (_ for _ in ()).throw(AssertionError('NO start')))
    assert not r['ok']


def test_alternate_provider_never_uses_local_admin_flow():
    with patch.object(qc, 'load_ai_enabled', return_value=True):
        r = qc.quick_connect_local_groq({**VALID, 'base_url': 'https://other.example'},
                                        start_bridge=lambda: (_ for _ in ()).throw(AssertionError('NO start')))
    assert not r['ok']


def test_ready_and_already_paired_no_admin_code():
    with patch.object(qc, '_cloud_gate', return_value={'ok': True}), \
         patch.object(qc, '_authorized_snapshot', return_value=True), \
         patch.object(qc, 'load_ai_enabled', return_value=True), \
         patch.object(qc, 'service_status', return_value={'ok': True, 'model_provider': 'groq', 'model_configured': True, 'model_ready': True}), \
         patch.object(qc, 'pairing_status', return_value={'ok': True}), \
         patch.object(qc, '_issue_local_code', side_effect=AssertionError('NO issue')):
        res = qc.quick_connect_local_groq(VALID, start_bridge=lambda: (_ for _ in ()).throw(AssertionError('NO start')))
    assert res == {'ok': True, 'state': 'CLOUD_PAIRED', 'new_pairing': False}


def test_stale_or_wrong_provider_blocked():
    with patch.object(qc, '_cloud_gate', return_value={'ok': True}), \
         patch.object(qc, '_authorized_snapshot', return_value=True), \
         patch.object(qc, 'load_ai_enabled', return_value=True), \
         patch.object(qc, 'service_status', return_value={'ok': True, 'model_provider': 'openai_compatible', 'model_configured': True}):
        res = qc.quick_connect_local_groq(VALID, start_bridge=lambda: True)
    assert not res['ok'] and 'no es el puente Groq' in res['error']


def test_start_bridge_then_pair_once_without_showing_code():
    status = [{'ok': False}, {'ok': True, 'model_provider': 'groq', 'model_configured': True, 'model_ready': True}]
    state = {'paired': False, 'saved': None, 'deleted': None}
    def save(k,v):
        state['saved']=(k,v)
        return True
    def reg(settings):
        assert state['saved'] == (ai_client.ENROLLMENT_NAME, 'cp-'+'Q'*38)
        state['paired'] = True
        return {'ok': True}
    def paired(settings):
        return {'ok': state['paired']}
    with patch.object(qc,'_cloud_gate',return_value={'ok':True}), \
         patch.object(qc,'_authorized_snapshot',return_value=True), \
         patch.object(qc,'load_ai_enabled',return_value=True), \
         patch.object(qc,'service_status',side_effect=status), \
         patch.object(qc,'pairing_status',side_effect=paired), \
         patch.object(qc,'ensure_registration',side_effect=reg), \
         patch.object(qc,'save_secret',side_effect=save), \
         patch.object(qc,'delete_secret',side_effect=lambda k:state.update(deleted=k)):
        r = qc.quick_connect_local_groq(VALID, start_bridge=lambda: True,
                                        sleep=lambda _:None, clock=iter([0,0,1]).__next__,
                                        issue_code=lambda: 'cp-'+'Q'*38)
    assert r['ok'] and r['new_pairing'] and state['deleted']==ai_client.ENROLLMENT_NAME


def test_revoked_during_start_does_not_issue_token():
    with patch.object(qc, '_cloud_gate', return_value={'ok': True}), \
         patch.object(qc, '_authorized_snapshot', side_effect=[True, False]), \
         patch.object(qc, 'load_ai_enabled', return_value=True), \
         patch.object(qc, 'service_status', return_value={'ok': False}), \
         patch.object(qc, 'save_secret', side_effect=AssertionError('NO credentials')):
        r = qc.quick_connect_local_groq(VALID, start_bridge=lambda: True,
                                        sleep=lambda _:None, clock=iter([0,0,1]).__next__)
    assert not r['ok'] and 'retiró el permiso' in r['error']


def test_bad_code_never_saved():
    with patch.object(qc, '_cloud_gate', return_value={'ok': True}), \
         patch.object(qc, '_authorized_snapshot', return_value=True), \
         patch.object(qc, 'load_ai_enabled', return_value=True), \
         patch.object(qc, 'service_status', return_value={'ok': True, 'model_provider': 'groq', 'model_configured':True, 'model_ready': True}), \
         patch.object(qc, 'pairing_status', return_value={'ok': False}), \
         patch.object(qc, 'save_secret', side_effect=AssertionError('NO save')):
        r = qc.quick_connect_local_groq(VALID, start_bridge=lambda: True, issue_code=lambda: 'nonsense')
    assert not r['ok']


def test_gui_has_single_primary_connect_with_advanced_fold():
    src=(BASE/'gui/ai_panel.py').read_text(encoding='utf-8')
    assert "text='Conectar IA'" in src
    assert "text='Configuración avanzada'" in src
    assert 'self._connection_expanded = False' in src
    assert 'self._toggle_simple_consent' in src
    assert 'self._launch_bridge_for_quick_connect' in src
    assert "text='Modelo alternativo'" in src
    assert "self._set_connection_state('Conectada'" in src
    assert 'CorePulse/{VERSION}' in (BASE/'core/ai_client.py').read_text(encoding='utf8')

