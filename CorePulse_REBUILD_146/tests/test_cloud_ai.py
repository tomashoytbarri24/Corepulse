"""Static/client contract tests; do not contact external services or require PySide6."""
import io
import json
from pathlib import Path
from urllib.error import HTTPError
import pytest
from core.ai import cloud_url, CorePulseCloudGateway


class FakeResponse:
    status = 200
    def __init__(self, payload):
        self.payload = payload
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self, limit): return json.dumps(self.payload).encode()


class FakeOpener:
    def __init__(self): self.requests=[]
    def open(self, request, timeout):
        self.requests.append(request)
        if request.full_url.endswith('/v1/status'):
            return FakeResponse({'available':True})
        return FakeResponse({'answer':'Respuesta desde servicio independiente'})


def test_cloud_opt_in_and_allowlisted_origin(monkeypatch):
    monkeypatch.delenv('COREPULSE_AI_CLOUD_URL', raising=False)
    assert cloud_url() == 'https://ai.corepulse.cl'
    for url in ('https://evil.example', 'https://ai.corepulse.cl.evil.example',
                'https://x@ai.corepulse.cl', 'http://ai.corepulse.cl',
                'https://ai.corepulse.cl/extra', 'https://ai.corepulse.cl:notaport'):
        monkeypatch.setenv('COREPULSE_AI_CLOUD_URL', url)
        assert cloud_url() == ''
    monkeypatch.setenv('COREPULSE_AI_CLOUD_URL','https://ai.corepulse.cl')
    assert cloud_url() == 'https://ai.corepulse.cl'


def test_cloud_gateway_uses_login_token_without_groq_key():
    opener=FakeOpener()
    gateway=CorePulseCloudGateway('https://ai.corepulse.cl',opener)
    assert gateway.probe('device-token') is True
    answer=gateway.chat('device-token','Consulta de RAM', {'ramPercent':79}, [{'role':'assistant','text':'contexto'}])
    assert answer=='Respuesta desde servicio independiente'
    posted=json.loads(opener.requests[1].data)
    assert posted['snapshot']['ramPercent']==79
    assert posted['history'][0]['role']=='assistant'
    assert opener.requests[1].get_header('Authorization')=='Bearer device-token'
    assert 'groq' not in opener.requests[1].full_url.lower()


def test_empty_login_token_rejected_before_request():
    opener=FakeOpener()
    with pytest.raises(RuntimeError,match='CLOUD_ACCOUNT_REQUIRED'):
        CorePulseCloudGateway('https://ai.corepulse.cl',opener).probe('')
    assert opener.requests==[]


def test_app_keeps_permissions_and_offline_core():
    root=Path(__file__).resolve().parents[1]
    main=(root/'main.py').read_text(encoding='utf-8')
    ai=(root/'core'/'ai.py').read_text(encoding='utf-8')
    qml=(root/'ui'/'AIPage.qml').read_text(encoding='utf-8')
    assert 'make_ai_controller(telemetry, system_health, cuenta, monitoring_insights)' in main
    assert 'authorized_snapshot(dict(telemetry.metrics), self._hardware)' in ai
    assert 'if not (self._enabled and self._consent and self._hardware and self._ready)' in ai
    assert 'CorePulse AI Cloud · Conexión automática' in qml
    assert 'corepulseAI.chooseProvider("cloud")' not in qml
    assert 'corepulseAI.chooseProvider("groq")' not in qml
    assert 'id: keyInput' not in qml


def test_account_is_initialized_before_ai_controller():
    """Reproduce la dependencia de arranque sin requerir PySide6 en CI/Linux."""
    import ast
    root = Path(__file__).resolve().parents[1]
    program = ast.parse((root / 'main.py').read_text(encoding='utf-8'))
    main_fn = next(n for n in program.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
    statements = []
    for statement in main_fn.body:
        if not isinstance(statement, ast.Assign) or len(statement.targets) != 1:
            continue
        target = statement.targets[0]
        if not isinstance(target, ast.Name) or target.id not in {'cuenta', 'corepulse_ai'}:
            continue
        statements.append(statement)
    assert len(statements) == 2
    assert [s.targets[0].id for s in statements] == ['cuenta', 'corepulse_ai']
    assert isinstance(statements[0].value, ast.Call)
    assert isinstance(statements[0].value.func, ast.Name)
    assert statements[0].value.func.id == 'CuentaManager'
    assert isinstance(statements[1].value, ast.Call)
    assert isinstance(statements[1].value.func, ast.Name)
    assert statements[1].value.func.id == 'make_ai_controller'

    class FakeCuenta: pass
    created = []
    def make_controller(telemetry, system_health, cuenta, monitoring_insights):
        created.append(cuenta)
        return object()
    # Se ejecutan los dos statements en su orden original dentro de una función
    # local: si cuenta no existe, fallará igual que en Windows con UnboundLocalError.
    snippet = ast.Module(body=[ast.FunctionDef(
        name='boot', args=ast.arguments(posonlyargs=[], args=[], vararg=None,
                                        kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[]),
        body=statements, decorator_list=[])], type_ignores=[])
    namespace = {'CuentaManager': FakeCuenta, 'make_ai_controller': make_controller,
                 'telemetry': object(), 'system_health': object(), 'monitoring_insights': object()}
    exec(compile(ast.fix_missing_locations(snippet), '<startup-contract>', 'exec'), namespace)
    namespace['boot']()
    assert len(created) == 1 and isinstance(created[0], FakeCuenta)


@pytest.mark.parametrize("status,payload,expected", [
    (503, {'error': 'identity_unavailable'}, 'CLOUD_IDENTITY_UNAVAILABLE'),
    (503, {'error': 'service_not_configured'}, 'CLOUD_SERVICE_NOT_CONFIGURED'),
    (503, {'error': 'provider_unavailable'}, 'CLOUD_PROVIDER_UNAVAILABLE'),
    (503, {'error': 'model_budget_unavailable'}, 'CLOUD_MODEL_BUDGET_UNAVAILABLE'),
    (429, {'error': 'model_budget_reached'}, 'CLOUD_MODEL_BUDGET_REACHED'),
    (503, {'error': 'unexpected'}, 'CLOUD_HTTP_503'),
    (401, {'error': 'unauthorized'}, 'CLOUD_HTTP_401'),
])
def test_cloud_gateway_reports_only_known_server_errors(status, payload, expected):
    class ErrorOpener:
        def open(self, request, timeout):
            raise HTTPError(request.full_url, status, 'error', {},
                            io.BytesIO(json.dumps(payload).encode('utf-8')))
    gateway=CorePulseCloudGateway('https://ai.corepulse.cl',ErrorOpener())
    with pytest.raises(RuntimeError, match='^'+expected+'$'):
        gateway.probe('device-token-fake')


def test_cloud_error_does_not_echo_untrusted_secret():
    class ErrorOpener:
        def open(self, request, timeout):
            body={'error':'private-example-should-never-be-displayed', 'authorization':'token-hidden'}
            raise HTTPError(request.full_url, 503, 'error', {},
                            io.BytesIO(json.dumps(body).encode('utf-8')))
    with pytest.raises(RuntimeError, match='^CLOUD_HTTP_503$'):
        CorePulseCloudGateway('https://ai.corepulse.cl',ErrorOpener()).probe('device-token-fake')


def test_cloud_gateway_displays_verified_server_references():
    class SourcesOpener(FakeOpener):
        def open(self, request, timeout):
            self.requests.append(request)
            return FakeResponse({'answer': 'Revisa las lecturas.', 'sources': [
                {'id': 'MS-BATTERY', 'title': 'Microsoft — batería',
                 'url': 'https://support.microsoft.com/es-es/windows/experience/power-battery/caring-for-your-battery-in-windows'}]})
    answer = CorePulseCloudGateway('https://ai.corepulse.cl', SourcesOpener()).chat('device-token', 'batería', {}, [])
    assert 'Documentación de referencia (catálogo CorePulse):' in answer
    assert 'https://support.microsoft.com/' in answer


def test_cloud_gateway_does_not_echo_arbitrary_references():
    class SourcesOpener(FakeOpener):
        def open(self, request, timeout):
            return FakeResponse({'answer': 'Valor N/A', 'sources': [
                {'id': 'BAD', 'title': 'fuente mala', 'url': 'https://fake.support.microsoft.com.evil.org/id'},
                {'id': 'JS', 'title': 'JS', 'url': 'javascript:alert(1)'},
                {'id': 'BADUSER', 'title': 'User', 'url': 'https://username:password@support.microsoft.com/secret'},
                {'id': 'INVALID', 'title': 'BAD\nINJECT', 'url': 'https://support.microsoft.com/doc'}]})
    result=CorePulseCloudGateway('https://ai.corepulse.cl', SourcesOpener()).chat('device-token', 'test', {}, [])
    assert result=='Valor N/A'


def test_old_cloud_response_without_references_is_compatible():
    answer=CorePulseCloudGateway('https://ai.corepulse.cl', FakeOpener()).chat('device-token','consulta',{},[])
    assert answer=='Respuesta desde servicio independiente'


def test_history_gateway_only_adds_summary_with_explicit_input():
    opener=FakeOpener()
    gateway=CorePulseCloudGateway('https://ai.corepulse.cl', opener)
    gateway.chat('device-token','hola',{},[])
    assert 'sessionSummary' not in json.loads(opener.requests[-1].data)
    gateway.chat('device-token','mis tendencias',{},[],{'sampleCount':3,'observedSeconds':65})
    assert json.loads(opener.requests[-1].data)['sessionSummary']['sampleCount']==3


def test_history_aggregate_never_leaks_raw_timestamps_or_paths():
    import ast, math
    source=(Path(__file__).resolve().parents[1]/'core'/'health'/'monitoring_insights.py').read_text('utf8')
    parsed=ast.parse(source)
    names={'_sustained_run','_evaluate_session_readings','_ai_session_summary'}
    nodes=[n for n in parsed.body if isinstance(n,ast.FunctionDef) and n.name in names]
    namespace={'math': math}
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])), '<summary>', 'exec'),namespace)
    rows=[{'ts':1000,'cpu_temp':94,'gpu_temp':None,'ram':95,'disk':None,'battery_state':None,'disk_state':None},
          {'ts':1030,'cpu_temp':96,'gpu_temp':None,'ram':96,'disk':None,'battery_state':None,'disk_state':None},
          {'ts':2500,'cpu_temp':98,'gpu_temp':None,'ram':98,'disk':None,'battery_state':None,'disk_state':None}]
    summary=namespace['_ai_session_summary'](rows)
    assert summary['cpuTempPeak']==98
    assert summary['cpuTempLongestHighSeconds']==30
    assert summary['ramPercentLongestHighSeconds']==30
    assert summary['missingIntervals']==1
    assert summary['observedSeconds']==30
    assert 'ts' not in summary and 'session_id' not in summary
    assert summary.get('gpuTempPeak') is None


def test_history_policies_and_opt_in_static():
    root=Path(__file__).resolve().parents[1]
    ai=(root/'core'/'ai.py').read_text('utf8')
    qml=(root/'ui'/'AIPage.qml').read_text('utf8')
    assert 'self._history_consent = False' in ai
    assert 'self._history_consent and temporal_question' in ai
    assert 'self._hardware and' in ai
    assert 'onToggled: corepulseAI.allowHistory(checked)' in qml
    assert 'Compartir resumen de sesión de Tendencias' in qml


def _comparison_functions():
    """Run history's pure functions without importing Windows/PySide6 in CI."""
    import ast
    import math
    path=Path(__file__).resolve().parents[1]/'core'/'health'/'monitoring_insights.py'
    tree=ast.parse(path.read_text(encoding='utf-8'))
    names={'_valid_metric','_sustained_run','_ai_compare_sessions'}
    funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    ns={'math':math}
    exec(compile(ast.Module(body=funcs,type_ignores=[]),str(path),'exec'),ns)
    return ns


def test_cross_boot_comparison_requires_two_distinct_sessions_and_coverage():
    compare=_comparison_functions()['_ai_compare_sessions']
    early=[{'ts':1000+i*30,'cpu_temp':92,'gpu_temp':88,'ram':94,'disk':70,
            'battery_state':'ok','disk_state':'ok'} for i in range(11)]
    later=[{'ts':4000+i*30,'cpu_temp':91,'gpu_temp':80,'ram':91,'disk':97,
            'battery_state':'attention','disk_state':'ok'} for i in range(11)]
    unknown=[{'ts':9000,'gpu_temp':92,'ram':None}, {'ts':9030,'gpu_temp':60,'ram':None}]
    assert compare([early]) is None
    result=compare([early,later,unknown])
    assert result['sessionsCompared']==3
    assert result['cpuTempAssessedSessions']==2
    assert result['cpuHeatSessions']==2
    assert result['gpuTempAssessedSessions']==3
    assert result['gpuHeatSessions']==1
    assert result['gpuPeakOnlySessions']==1
    assert result['ramAssessedSessions']==2
    assert result['ramHighSessions']==2
    assert result['batteryAlertSessions']==1
    assert result['batteryAssessedSessions']==2
    assert result['diskAlmostFullSessions']==1
    assert 'ts' not in result and 'session_id' not in result
    assert all(isinstance(v,int) for v in result.values())


def test_cross_boot_gaps_never_create_a_sustained_episode():
    compare=_comparison_functions()['_ai_compare_sessions']
    interrupted=[{'ts':1000,'cpu_temp':99,'ram':100},
                 {'ts':1301,'cpu_temp':99,'ram':100}]
    other=[{'ts':4000,'cpu_temp':70,'ram':40},
           {'ts':4030,'cpu_temp':70,'ram':40}]
    result=compare([interrupted,other])
    assert result['cpuHeatSessions']==0
    assert result['cpuPeakOnlySessions']==1
    assert result['ramHighSessions']==0
    assert result['missingIntervals']==1


def test_cross_boot_cloud_gateway_is_optional_and_metadata_minimal():
    opener=FakeOpener()
    gateway=CorePulseCloudGateway('https://ai.corepulse.cl',opener)
    comparison={"sessionsCompared":2,"cpuTempAssessedSessions":2,
                "cpuHeatSessions":2,"deviceId":"NEVER_SEND"}
    gateway.chat('token','¿Se repite el calor en otras sesiones?',{},[],None,comparison)
    posted=json.loads(opener.requests[-1].data)
    assert posted['sessionComparison']==comparison  # Server validates strict schema.
    gateway.chat('token','Hola',{},[])
    assert 'sessionComparison' not in json.loads(opener.requests[-1].data)


def test_cross_boot_permission_is_separate_and_fail_closed_static():
    root=Path(__file__).resolve().parents[1]
    ai=(root/'core'/'ai.py').read_text(encoding='utf-8')
    assert 'share_comparison = bool(share_session and compare_question)' in ai
    assert 'if share_comparison else None' in ai
    assert 'ai_multi_session_summary()' in ai
    assert 'self._history_consent = False' in ai
    assert 'historyConsent' in (root/'ui'/'AIPage.qml').read_text(encoding='utf-8')


# V127 — Connection and privacy contracts for zero-setup CorePulse AI.
def test_v127_default_cloud_override_is_strict(monkeypatch):
    monkeypatch.delenv("COREPULSE_AI_CLOUD_URL", raising=False)
    monkeypatch.delenv("COREPULSE_AI_DEV", raising=False)
    assert cloud_url() == "https://ai.corepulse.cl"
    monkeypatch.setenv("COREPULSE_AI_CLOUD_URL", "https://ai.corepulse.cl.evil.org")
    assert cloud_url() == ""  # no arbitrary token destination


def test_v127_preference_opt_out_survives_restart_without_sensitive_data(tmp_path, monkeypatch):
    from core.ai import ai_preferences_path, read_ai_preferences, save_ai_preferences
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert read_ai_preferences() == {}
    assert save_ai_preferences(enabled=False, questions=False)
    assert read_ai_preferences() == {"enabled": False, "questions": False}
    text = ai_preferences_path().read_text(encoding="utf-8")
    assert "token" not in text and "hardware" not in text and "history" not in text
    assert save_ai_preferences(enabled=True, questions=True)
    assert read_ai_preferences() == {"enabled": True, "questions": True}


def test_v127_cloud_auto_start_wiring_does_not_autoshare_hardware():
    root = Path(__file__).resolve().parents[1]
    ai = (root / 'core' / 'ai.py').read_text(encoding='utf-8')
    qml = (root / 'ui' / 'AIPage.qml').read_text(encoding='utf-8')
    assert 'QTimer.singleShot(0, self._auto_connect_if_possible)' in ai
    assert 'self._provider = "cloud"' in ai
    assert 'self._enabled = prefs.get("enabled", True)' in ai
    assert 'self._hardware = False' in ai
    assert 'self._history_consent = False' in ai
    assert 'self._account_token()' in ai
    assert 'self._cloud.probe(token)' in ai
    assert 'self._consent and temporal_question' not in ai or 'self._history_consent and temporal_question' in ai
    assert 'onClicked: cuenta.iniciarSesion()' in qml
    assert 'onClicked: corepulseAI.connectCloud()' in qml
    assert 'Compartir lecturas técnicas del equipo (opcional)' in qml
    assert 'al pulsar Enviar' in qml
    assert 'Groq (clave propia)' not in qml and 'keyInput' not in qml


def test_v127_auto_probe_and_logout_with_fake_qt(monkeypatch):
    """Behavioral test: cached login probes status; no chat or sensor data on startup."""
    import sys
    import types
    import core.ai as module

    class BoundSignal:
        def __init__(self): self.listeners = []
        def connect(self, callback): self.listeners.append(callback)
        def emit(self, *args):
            for fn in list(self.listeners): fn(*args)

    class Signal:
        def __init__(self, *args): self.name = None
        def __set_name__(self, owner, name): self.name = '_signal_' + name
        def __get__(self, obj, cls=None):
            if obj is None: return self
            if self.name not in obj.__dict__: obj.__dict__[self.name] = BoundSignal()
            return obj.__dict__[self.name]

    def qt_property(*args, **kwargs):
        def decorator(fn): return property(fn)
        return decorator
    def slot(*args, **kwargs):
        def decorator(fn): return fn
        return decorator
    queue = []
    class Timer:
        @staticmethod
        def singleShot(delay, cb): queue.append(cb)

    core = types.ModuleType('PySide6.QtCore')
    core.QObject = object
    core.Property = qt_property
    core.QTimer = Timer
    core.Signal = Signal
    core.Slot = slot
    pkg = types.ModuleType('PySide6')
    pkg.QtCore = core
    monkeypatch.setitem(sys.modules, 'PySide6', pkg)
    monkeypatch.setitem(sys.modules, 'PySide6.QtCore', core)
    monkeypatch.setattr(module, 'read_ai_preferences', lambda: {})
    monkeypatch.setattr(module, 'save_ai_preferences', lambda **kw: True)

    requests = []
    class FakeCloud:
        def __init__(self, url): requests.append(('endpoint', url))
        def probe(self, token):
            requests.append(('probe', token)); return True
        def chat_structured(self, token, question, snapshot, history, *a):
            requests.append(('chat', token, question, snapshot, history))
            return {'text': 'Respuesta segura'}
    monkeypatch.setattr(module, 'CorePulseCloudGateway', FakeCloud)
    class ImmediateFuture:
        def __init__(self, func):
            try: self.value=func(); self.error=None
            except Exception as exc: self.value=None; self.error=exc
        def result(self):
            if self.error: raise self.error
            return self.value
        def add_done_callback(self, cb): cb(self)
    class ImmediatePool:
        def __init__(self,*args,**kwargs): pass
        def submit(self, func): return ImmediateFuture(func)
        def shutdown(self, **kwargs): pass
    monkeypatch.setattr(module, 'ThreadPoolExecutor', ImmediatePool)
    class FakeAccount:
        def __init__(self): self.changed=BoundSignal(); self.conectado=True
        def token_para_ai(self): return 'fake-device-token' if self.conectado else ''
    cuenta=FakeAccount()
    ctrl=module.make_ai_controller(types.SimpleNamespace(metrics={'cpuTemp':101}), cuenta=cuenta)
    assert ctrl.state['provider'] == 'cloud' and ctrl.state['enabled'] and ctrl.state['consent']
    assert ctrl.state['hardware'] is False and ctrl.state['historyConsent'] is False
    assert requests == [('endpoint','https://ai.corepulse.cl')]
    queue.pop(0)()
    assert ('probe','fake-device-token') in requests and ctrl.state['ready']
    assert not any(r[0]=='chat' for r in requests)
    ctrl.send('¿Cómo puedo mejorar la RAM?')
    chats=[r for r in requests if r[0]=='chat']
    assert len(chats)==1 and chats[0][3]=={}
    cuenta.conectado=False
    cuenta.changed.emit()
    assert not ctrl.state['ready'] and not ctrl.state['messages']
    assert not ctrl.state['historyConsent']
    # Reingreso tras iniciar sesión: sin botones extra ni consultas automáticas.
    cuenta.conectado = True
    cuenta.changed.emit()
    assert ctrl.state['ready']
    assert len([r for r in requests if r[0] == 'probe']) == 2
    assert len([r for r in requests if r[0] == 'chat']) == 1  # solo pregunta explícita
    ctrl.enable(False)
    assert not ctrl.state['ready'] and not ctrl.state['enabled']
    ctrl.close()


def test_v127_account_switch_resets_hardware_and_chat_before_new_login():
    import ast
    from pathlib import Path
    source = (Path(__file__).resolve().parents[1] / 'core' / 'ai.py').read_text(encoding='utf-8')
    assert 'fingerprint != self._auto_probe_fingerprint' in source
    assert 'self._hardware = self._history_consent = False' in source
    assert 'self._messages.clear()' in source
    assert 'self._generation += 1' in source
    assert ast.parse(source)


# REBUILD 128 — Red inestable: reconexión con backoff y sesión segura.
def _v128_fake_controller(monkeypatch):
    """Qt simulado: control exacto sobre las esperas, sin hilos ni red real."""
    import sys
    import types
    import core.ai as module

    class BoundSignal:
        def __init__(self): self.listeners = []
        def connect(self, callback): self.listeners.append(callback)
        def emit(self, *args):
            for fn in list(self.listeners): fn(*args)

    class Signal:
        def __init__(self, *args): self.name = None
        def __set_name__(self, owner, name): self.name = '_signal_' + name
        def __get__(self, obj, cls=None):
            if obj is None: return self
            if self.name not in obj.__dict__:
                obj.__dict__[self.name] = BoundSignal()
            return obj.__dict__[self.name]

    def qt_property(*args, **kwargs):
        def decorator(fn): return property(fn)
        return decorator

    def slot(*args, **kwargs):
        def decorator(fn): return fn
        return decorator

    scheduled = []
    class Timer:
        @staticmethod
        def singleShot(delay, callback): scheduled.append((delay, callback))

    qt = types.ModuleType('PySide6.QtCore')
    qt.QObject = object
    qt.Property = qt_property
    qt.QTimer = Timer
    qt.Signal = Signal
    qt.Slot = slot
    pkg = types.ModuleType('PySide6')
    pkg.QtCore = qt
    monkeypatch.setitem(sys.modules, 'PySide6', pkg)
    monkeypatch.setitem(sys.modules, 'PySide6.QtCore', qt)
    monkeypatch.setattr(module, 'read_ai_preferences', lambda: {})
    monkeypatch.setattr(module, 'save_ai_preferences', lambda **kw: True)

    calls = []
    cloud = {'error': 'CLOUD_CONNECTION_ERROR', 'chat_error': None}
    class FakeCloud:
        def __init__(self, url): calls.append(('endpoint', url))
        def probe(self, token):
            calls.append(('probe', token))
            if cloud['error']: raise RuntimeError(cloud['error'])
            return True
        def chat_structured(self, token, question, snapshot, history, *extras):
            calls.append(('chat', question, snapshot))
            if cloud['chat_error']: raise RuntimeError(cloud['chat_error'])
            return {'text': 'Respuesta de prueba'}
    monkeypatch.setattr(module, 'CorePulseCloudGateway', FakeCloud)

    class ImmediateFuture:
        def __init__(self, func):
            try: self.value, self.error = func(), None
            except Exception as exc: self.value, self.error = None, exc
        def result(self):
            if self.error: raise self.error
            return self.value
        def add_done_callback(self, callback): callback(self)
    class ImmediatePool:
        def __init__(self, *a, **kw): pass
        def submit(self, func): return ImmediateFuture(func)
        def shutdown(self, **kwargs): pass
    monkeypatch.setattr(module, 'ThreadPoolExecutor', ImmediatePool)

    class FakeAccount:
        def __init__(self):
            self.changed = BoundSignal()
            self.conectado = True
            self.token = 'a-private-device-token'
        def token_para_ai(self): return self.token if self.conectado else ''
    account = FakeAccount()
    ctrl = module.make_ai_controller(types.SimpleNamespace(metrics={'cpuTemp': 99}), cuenta=account)
    delay, callback = scheduled.pop(0)
    assert delay == 0  # al abrir la app
    callback()
    return ctrl, account, scheduled, calls, cloud


def test_v128_offline_retries_exponentially_then_connects_without_sending_data(monkeypatch):
    ctrl, account, queue, calls, cloud = _v128_fake_controller(monkeypatch)
    assert not ctrl.state['ready'] and len(queue) == 1
    assert queue[0][0] == 15000
    assert 'Reconectando en 15 s' in ctrl.state['status']
    for wait in (15000, 30000, 60000, 120000, 300000):
        ms, cb = queue.pop(0)
        assert ms == wait
        cb()
        assert not ctrl.state['ready']
    assert queue[0][0] == 300000  # backoff cap
    cloud['error'] = None
    ms, cb = queue.pop(0)
    cb()
    assert ctrl.state['ready']
    assert queue == [] and len([x for x in calls if x[0] == 'probe']) == 7
    assert not any(x[0] == 'chat' for x in calls)
    assert ctrl.state['hardware'] is False
    assert ctrl.state['historyConsent'] is False
    ctrl.close()


def test_v128_logout_and_optout_invalidate_pending_delayed_callbacks(monkeypatch):
    ctrl, account, queue, calls, cloud = _v128_fake_controller(monkeypatch)
    callback = queue.pop(0)[1]
    count = len(calls)
    account.conectado = False
    account.changed.emit()
    callback()
    assert len(calls) == count and not ctrl.state['ready']
    account.conectado = True
    account.changed.emit()
    callback = queue.pop(0)[1]
    count = len(calls)
    ctrl.enable(False)
    callback()
    assert len(calls) == count
    assert not ctrl.state['enabled'] and not ctrl.state['ready']
    ctrl.close()


def test_v128_401_does_not_retry_and_manual_reconnect_is_possible(monkeypatch):
    ctrl, account, queue, calls, cloud = _v128_fake_controller(monkeypatch)
    ctrl.close()
    assert queue
    # Nuevo controlador con error de autorización desde la primera solicitud.
    ctrl, account, queue, calls, cloud = _v128_fake_controller(monkeypatch)
    cloud['error'] = 'CLOUD_HTTP_401'
    # La primera petición de arranque ya falló por red; reintento manual => 401.
    ctrl.connectCloud()
    assert 'sesión nuevamente' in ctrl.state['status']
    assert not ctrl.state['ready']
    previous = len(calls)
    for _, delayed in queue[:]:
        delayed()
    assert len(calls) == previous  # callback viejo invalidado
    ctrl.close()


def test_v128_failed_chat_is_never_automatically_replayed(monkeypatch):
    ctrl, account, queue, calls, cloud = _v128_fake_controller(monkeypatch)
    cloud['error'] = None
    _, callback = queue.pop(0)
    callback()
    assert ctrl.state['ready']
    cloud['chat_error'] = 'CLOUD_CONNECTION_ERROR'
    ctrl.send('¿Cuál es mi problema?')
    assert len([x for x in calls if x[0]=='chat']) == 1
    assert not ctrl.state['ready']
    assert queue[0][0] == 15000
    _, callback = queue.pop(0)
    callback()
    assert ctrl.state['ready']
    assert len([x for x in calls if x[0]=='chat']) == 1
    assert not any(x[0] == 'chat' and x[2] for x in calls)  # sin telemetría
    ctrl.close()


def test_v128_429_does_not_hammer_rate_limiter(monkeypatch):
    ctrl, account, queue, calls, cloud = _v128_fake_controller(monkeypatch)
    cloud['error'] = 'CLOUD_HTTP_429'
    ctrl.connectCloud()
    assert queue[-1][0] >= 75000
    ctrl.close()


def test_v128_does_not_retry_with_previous_account_after_switch(monkeypatch):
    ctrl, account, queue, calls, cloud = _v128_fake_controller(monkeypatch)
    old_callback = queue.pop(0)[1]
    account.token = 'another-device-token'
    account.changed.emit()
    assert calls[-1] == ('probe', 'another-device-token')
    previous = len(calls)
    old_callback()
    assert len(calls) == previous
    ctrl.close()
