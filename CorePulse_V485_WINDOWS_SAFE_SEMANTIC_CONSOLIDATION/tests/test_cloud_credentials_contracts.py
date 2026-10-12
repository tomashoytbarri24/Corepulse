"""Regresiones históricas agrupadas en V481 sin eliminar pruebas."""
from __future__ import annotations


# ===== Regresión test_v464_groq_diagnostics (original conservado íntegramente) =====
import io
import json
import ssl
import sys
import urllib.error
from pathlib import Path
from unittest.mock import patch
import pytest

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / 'CorePulse_AI_Server'
if str(SERVER) not in sys.path:
    sys.path.insert(0,str(SERVER))
from app import groq_diagnostics, groq_probe, model_gateway


@pytest.mark.parametrize('http,expected',[(400,'GROQ_HTTP_400'),(401,'GROQ_HTTP_401'),(403,'GROQ_HTTP_403'),(404,'GROQ_HTTP_404'),(429,'GROQ_HTTP_429'),(502,'GROQ_HTTP_502')])
def test_http_error_classification(http, expected):
    e=urllib.error.HTTPError('https://api.groq.com/openai/v1',http,'gsk_FAKE_SECRET',{},None)
    try:
        raise RuntimeError('generic opaque failure') from e
    except RuntimeError as outer:
        code,message=groq_diagnostics.classify_error(outer)
    assert code==expected
    assert 'gsk_FAKE_SECRET' not in message
    assert 'https://' not in message


def test_ssl_and_network_categorization():
    assert groq_diagnostics.classify_error(ssl.SSLCertVerificationError('secret'))[0]=='GROQ_TLS_ERROR'
    assert groq_diagnostics.classify_error(urllib.error.URLError('secret'))[0]=='GROQ_NETWORK_ERROR'
    assert groq_diagnostics.classify_error(TimeoutError('secret'))[0]=='GROQ_TIMEOUT'


def test_model_readiness_has_zero_network():
    with patch.object(model_gateway,'MODEL_PROVIDER','groq'), patch.object(model_gateway,'MODEL_API_KEY',''):
        with patch.object(groq_diagnostics.urllib.request,'build_opener',side_effect=AssertionError('no network')):
            ok, code, msg=groq_diagnostics.check_connection()
    assert not ok and code=='GROQ_KEY_MISSING'


class FakeHTTPResponse:
    def __init__(self,obj):self.obj=obj
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def read(self,*args):return json.dumps(self.obj).encode('utf8')


def test_diagnostic_only_get_models_without_telemetry():
    captured=[]
    class Opener:
        def open(self,req,timeout=0):
            captured.append((req.full_url,req.get_method(),req.data,dict(req.headers),timeout))
            return FakeHTTPResponse({'data':[{'id':'openai/gpt-oss-120b'}]})
    with patch.object(model_gateway,'MODEL_PROVIDER','groq'),patch.object(model_gateway,'MODEL_BASE_URL','https://api.groq.com/openai/v1'),patch.object(model_gateway,'MODEL_NAME','openai/gpt-oss-120b'),patch.object(model_gateway,'MODEL_API_KEY','gsk_FAKE_SECRET'),patch.object(groq_diagnostics.urllib.request,'build_opener',return_value=Opener()):
        ok, code, msg=groq_diagnostics.check_connection()
    assert ok and code=='GROQ_MODEL_AVAILABLE'
    url,method,data,headers,timeout=captured[0]
    assert url=='https://api.groq.com/openai/v1/models' and method=='GET' and data is None
    assert headers['Authorization']=='Bearer gsk_FAKE_SECRET'
    assert timeout<=15


def test_model_missing_is_not_success():
    class Opener:
        def open(self,req,timeout=0):return FakeHTTPResponse({'data':[{'id':'other'}]})
    with patch.object(model_gateway,'MODEL_PROVIDER','groq'),patch.object(model_gateway,'MODEL_NAME','openai/gpt-oss-120b'),patch.object(model_gateway,'MODEL_BASE_URL','https://api.groq.com/openai/v1'),patch.object(model_gateway,'MODEL_API_KEY','gsk_FAKE_SECRET'),patch.object(groq_diagnostics.urllib.request,'build_opener',return_value=Opener()):
        ok, code, msg=groq_diagnostics.check_connection()
    assert not ok and code=='GROQ_MODEL_UNAVAILABLE'


def test_probe_prints_safe_status_no_credentials(capsys):
    error=urllib.error.HTTPError('https://api.groq.com/openai/v1/chat/completions',429,'gsk_FAKE_SECRET',{},None)
    with patch.object(groq_probe,'model_ready',return_value=True),patch.object(groq_probe,'generate',side_effect=RuntimeError('HTTP 429') ) as fake:
        fake.side_effect.__cause__=error
        assert groq_probe.main()==3
    output=capsys.readouterr().out
    assert 'GROQ_HTTP_429' in output
    assert 'gsk_FAKE_SECRET' not in output
    assert 'https://' not in output
    assert 'RuntimeError' not in output


def test_no_redirect_handler_to_protect_authorization():
    obj=groq_diagnostics._NoRedirect()
    assert obj.redirect_request(object(),None,302,'Found',{},'https://other.example') is None


def test_bat_validation_file_uses_valid_separator():
    contents=(ROOT/'herramientas'/'ia'/'13_VALIDAR_GROQ_V463.bat').read_text(encoding='utf8')
    assert 'tests/test_v463_groq_cloud.py' in contents
    assert '\t' not in contents


def test_model_reply_is_still_checked_by_v463_guardrails():
    from app.guardrails import validate_model_response
    status=validate_model_response({'cpu':{'temperature_c':None}},'CPU a 500 °C')
    assert not status['allowed']



# ===== Regresión test_v465_groq_permission_rootcause (original conservado íntegramente) =====
import io
import sys
import json
import urllib.error
from pathlib import Path
from unittest.mock import patch
import pytest

ROOT=Path(__file__).resolve().parents[1]
SERVER=ROOT / 'CorePulse_AI_Server'
if str(SERVER) not in sys.path:
    sys.path.insert(0,str(SERVER))

from app.groq_credentials import choose_key
from app import groq_diagnostics, groq_probe, groq_key_status


@pytest.mark.parametrize('env,stored,expected,conflict',[
    ('', '', 'NONE', False),
    ('gsk_env','', 'GROQ_API_KEY_ENV', False),
    ('','gsk_stored', 'WINDOWS_CREDENTIAL_MANAGER', False),
    ('gsk_same','gsk_same', 'WINDOWS_CREDENTIAL_MANAGER', False),
    ('gsk_wrong','gsk_stored', 'WINDOWS_CREDENTIAL_MANAGER', True),
    ('   gsk_env   ','  gsk_stored  ', 'WINDOWS_CREDENTIAL_MANAGER', True),
])
def test_key_selection(env,stored,expected,conflict):
    actual, source, has_conflict, has_env, has_stored = choose_key(env,stored)
    assert source==expected
    assert has_conflict==conflict
    assert actual==(stored.strip() or env.strip())
    assert has_env==bool(env.strip())
    assert has_stored==bool(stored.strip())


def http_error(status, body=None):
    return urllib.error.HTTPError(
        'https://api.groq.com/openai/v1/chat/completions',status,'gsk_SENSITIVE_DO_NOT_PRINT',
        {'Content-Type':'application/json'}, io.BytesIO(body) if body is not None else None)

@pytest.mark.parametrize('groq_code,expected',[
    ('model_permission_blocked_org','GROQ_BLOCKED_ORGANIZATION'),
    ('model_permission_blocked_project','GROQ_BLOCKED_PROJECT'),
])
def test_known_model_permission_from_403(groq_code,expected):
    blob=json.dumps({'error': {'code':groq_code,'message':'gsk_PRIVATE_ONLY'}}).encode()
    err=http_error(403,blob)
    try:
        raise RuntimeError('Opaque') from err
    except RuntimeError as exception:
        code, guidance=groq_diagnostics.classify_error(exception)
    assert code==expected
    assert 'gsk_PRIVATE_ONLY' not in guidance
    assert 'https://' not in guidance


@pytest.mark.parametrize('body',[
    b'{broken json',
    b'<html>gsk_SENSITIVE_DO_NOT_PRINT</html>',
    json.dumps({'error': {'code': 'unrecognized_user_specific_code', 'message': 'gsk_SENSITIVE_DO_NOT_PRINT'}}).encode(),
    b'Z' * 9000,
])
def test_unknown_provider_response_does_not_echo_body(body):
    code, guidance=groq_diagnostics.classify_error(http_error(403,body))
    assert code in ('GROQ_HTTP_403','GROQ_HTTP_403_UNKNOWN')
    assert 'gsk_' not in code+guidance and 'https://' not in code+guidance


def test_known_permission_other_http_does_not_false_attribute():
    body=json.dumps({'error':{'code':'model_permission_blocked_org'}}).encode()
    assert groq_diagnostics.classify_error(http_error(429,body))[0]=='GROQ_HTTP_429'


def test_print_credential_source_without_key(capsys):
    with patch.object(groq_diagnostics, 'credential_source_info',return_value=('WINDOWS_CREDENTIAL_MANAGER',True)):
        groq_diagnostics.print_credential_source()
    out=capsys.readouterr().out
    assert 'WINDOWS_CREDENTIAL_MANAGER' in out
    assert 'GROQ_API_KEY' in out
    assert 'gsk_' not in out


def test_status_offline_no_external_request(capsys):
    with patch.object(groq_key_status,'GROQ_KEY_SOURCE','WINDOWS_CREDENTIAL_MANAGER'), \
         patch.object(groq_key_status,'GROQ_KEY_CONFLICT',True), \
         patch.object(groq_key_status,'GROQ_KEY_PRESENT_ENV',True), \
         patch.object(groq_key_status,'GROQ_KEY_PRESENT_MANAGER',True), \
         patch('urllib.request.urlopen', side_effect=AssertionError('NO INTERNET')):
        assert groq_key_status.main()==0
    out=capsys.readouterr().out
    assert 'SIN conexión a Internet' in out
    assert 'gsk_' not in out


def test_probe_reports_groq_code_with_no_body(capsys):
    private_body=json.dumps({'error': {'code':'model_permission_blocked_project','message':'gsk_NEVER_EXPOSE'}}).encode()
    err=http_error(403,private_body)
    try:
        raise RuntimeError('opaque') from err
    except RuntimeError as e:
        with patch.object(groq_probe,'model_ready',return_value=True), patch.object(groq_probe,'generate',side_effect=e):
            assert groq_probe.main()==3
    out=capsys.readouterr().out
    assert 'GROQ_BLOCKED_PROJECT' in out
    assert 'gsk_NEVER_EXPOSE' not in out


def test_files_stay_in_base_and_groq_localhost():
    assert (ROOT/'main.py').is_file()
    assert (ROOT/'gui/ai_panel.py').is_file()
    assert (ROOT/'herramientas'/'ia'/'16_REVISAR_CREDENCIAL_GROQ_V465.bat').is_file()
    bat=(ROOT/'herramientas'/'ia'/'11_INICIAR_PUENTE_GROQ_V463.bat').read_text(encoding='utf8')
    assert '--host 127.0.0.1' in bat



# ===== Regresión test_v466_groq_edge_useragent (original conservado íntegramente) =====
import io
import json
import sys
import urllib.error
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
SERVER=ROOT/'CorePulse_AI_Server'
if str(SERVER) not in sys.path:
    sys.path.insert(0,str(SERVER))
from app import model_gateway, groq_diagnostics, groq_client_check


def http403(body: bytes):
    return urllib.error.HTTPError('https://api.groq.com/openai/v1/models',403,
                'PRIVATE_USER_INFO',{'Content-Type':'text/plain'},io.BytesIO(body))


def test_explicit_useragent_only_for_groq():
    with patch.object(model_gateway,'MODEL_PROVIDER','groq'), patch.object(model_gateway,'MODEL_API_KEY','gsk_PRIVATE'):
        headers=model_gateway._headers()
        assert headers['User-Agent']=='CorePulse-AI/466'
        assert headers['Authorization']=='Bearer gsk_PRIVATE'
        assert 'Python-urllib' not in headers['User-Agent']
    with patch.object(model_gateway,'MODEL_PROVIDER','custom'), patch.object(model_gateway,'MODEL_API_KEY',''):
        assert 'User-Agent' not in model_gateway._headers()


def test_cloudflare_1010_safe_code():
    error=http403(b'error code: 1010\ngsk_PRIVATE_TOKEN_MUST_NOT_PRINT')
    code,message=groq_diagnostics.classify_error(error)
    assert code=='GROQ_EDGE_BLOCKED_1010'
    assert 'gsk_' not in message and 'PRIVATE_' not in message


def test_retain_unknown_403_and_verified_permission_codes():
    assert groq_diagnostics.classify_error(http403(b'<html>Unknown gsk_LEAK</html>'))[0]=='GROQ_HTTP_403'
    import json
    error=http403(json.dumps({'error':{'code':'model_permission_blocked_org'}}).encode())
    assert groq_diagnostics.classify_error(error)[0]=='GROQ_BLOCKED_ORGANIZATION'


def test_get_models_uses_header_without_network():
    requests=[]
    class DummyResp:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def read(self, max_size): return json.dumps({'data':[{'id':'openai/gpt-oss-120b'}]}).encode()
    class DummyOpener:
        def open(self,request, timeout):
            requests.append(request)
            return DummyResp()
    with patch.object(model_gateway,'MODEL_PROVIDER','groq'), patch.object(model_gateway,'MODEL_NAME','openai/gpt-oss-120b'), patch.object(model_gateway,'MODEL_API_KEY','gsk_TEST'), patch.object(model_gateway,'MODEL_BASE_URL','https://api.groq.com/openai/v1'), patch('urllib.request.build_opener', return_value=DummyOpener()):
        assert groq_diagnostics.check_connection()[1]=='GROQ_MODEL_AVAILABLE'
    assert requests[0].get_header('User-agent')=='CorePulse-AI/466'
    assert requests[0].get_header('Authorization')=='Bearer gsk_TEST'
    assert requests[0].full_url=='https://api.groq.com/openai/v1/models'


def test_post_chat_uses_header_and_synthetic_data_without_network():
    requests=[]
    class DummyResp:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def read(self): return json.dumps({'choices':[{'message':{'content':'N/A'}}]}).encode()
    def fake_urlopen(request, timeout):
        requests.append(request)
        return DummyResp()
    with patch.object(model_gateway,'MODEL_PROVIDER','groq'), patch.object(model_gateway,'MODEL_NAME','openai/gpt-oss-120b'), patch.object(model_gateway,'MODEL_API_KEY','gsk_TEST'), patch.object(model_gateway,'MODEL_BASE_URL','https://api.groq.com/openai/v1'), patch('urllib.request.urlopen', side_effect=fake_urlopen):
        assert model_gateway.generate({'cpu':{'temperature_c':None}},'¿Temperatura?')=='N/A'
    req=requests[0]
    assert req.get_header('User-agent')=='CorePulse-AI/466'
    assert req.get_header('Authorization')=='Bearer gsk_TEST'
    assert req.full_url=='https://api.groq.com/openai/v1/chat/completions'
    assert json.loads(req.data)['model']=='openai/gpt-oss-120b'


def test_local_preflight_no_network_and_no_secret_output(capsys):
    with patch.object(model_gateway,'MODEL_PROVIDER','groq'), patch.object(model_gateway,'MODEL_API_KEY','gsk_SECRET'), patch('urllib.request.urlopen', side_effect=AssertionError('NO INTERNET')):
        assert groq_client_check.main()==0
    out=capsys.readouterr().out
    assert 'GROQ_CLIENT_HEADER_READY' in out
    assert 'gsk_' not in out and 'Authorization' not in out


def test_zip_full_root_present():
    assert (ROOT/'main.py').is_file()
    assert (ROOT/'gui/ai_panel.py').is_file()
    assert (ROOT/'herramientas'/'ia'/'11_INICIAR_PUENTE_GROQ_V463.bat').is_file()
    assert (ROOT/'herramientas'/'ia'/'17_VERIFICAR_CLIENTE_GROQ_V466.bat').is_file()
    assert int((ROOT/'LATEST_VERSION.txt').read_text().strip().removeprefix('V')) >= 466

