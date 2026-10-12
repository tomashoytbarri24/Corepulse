"""Centraliza el cierre idempotente de agentes, hilos, RTSS y proveedores de sensores."""
from __future__ import annotations
# Código refactorizado: nombres estables y documentación en español.
import atexit
import gc
import threading
import time
_shutdown_lock = threading.RLock()
_shutdown_done = False

def _call_first(obj, method_names):
    if obj is None:
        return (False, None)
    for name in method_names:
        method = getattr(obj, name, None)
        if callable(method):
            try:
                method()
                return (True, None)
            except Exception as exc:
                return (False, f'{type(exc).__name__}: {exc}')
    return (False, None)

def _stop_telemetry_worker(report):
    try:
        from core import telemetry_background as telemetry
        stop = getattr(telemetry, 'stop_background_worker', None)
        if callable(stop):
            stop()
            report.append('telemetry worker: stopped')
        else:
            report.append('telemetry worker: no stop function')
    except Exception as exc:
        report.append(f'telemetry worker: {type(exc).__name__}: {exc}')

def _close_rtss_instances(report):
    try:
        from core import realtime_agent
        report.append('RTSS: owned instances handled by services')
    except Exception as exc:
        report.append(f'RTSS: {type(exc).__name__}: {exc}')

def _dispose_lhm_objects(report):
    """Gestiona la operación `dispose_lhm_objects` dentro de CorePulse sin alterar la evidencia real ni las reglas del módulo."""
    try:
        from core import telemetry_full as telemetry
        candidates = []
        for name, value in vars(telemetry).items():
            lowered = name.lower()
            if any((token in lowered for token in ('provider', 'computer', 'monitor', 'hardware', 'lhm'))):
                candidates.append((name, value))
        seen = set()
        for name, obj in candidates:
            if obj is None:
                continue
            ident = id(obj)
            if ident in seen:
                continue
            seen.add(ident)
            called, error = _call_first(obj, ('Close', 'Dispose', 'close', 'dispose', 'shutdown', 'stop'))
            if called:
                report.append(f'LHM object closed: {name}')
            elif error:
                report.append(f'LHM object {name}: {error}')
    except Exception as exc:
        report.append(f'LHM cleanup: {type(exc).__name__}: {exc}')

def shutdown_corepulse_services(agent=None, tray=None, overlay=None, performance=None, *, verbose=False):
    """Detiene la operación `shutdown_corepulse_services` dentro de CorePulse sin alterar la evidencia real ni las reglas del módulo."""
    global _shutdown_done
    with _shutdown_lock:
        if _shutdown_done:
            return {'already_shutdown': True, 'steps': []}
        _shutdown_done = True
    report = []
    if performance is not None:
        called, error = _call_first(performance, ('shutdown', 'close', 'stop'))
        if called:
            report.append('performance profiles: stopped; persistent Windows plan preserved; checked after Game Boost teardown')
        elif error:
            report.append(f'performance profiles: {error}')
    if agent is not None:
        called, error = _call_first(agent, ('stop', 'close', 'shutdown'))
        if called:
            report.append('realtime agent: stopped')
        elif error:
            report.append(f'realtime agent: {error}')
    if overlay is not None:
        called, error = _call_first(overlay, ('stop', 'close', 'shutdown'))
        if called:
            report.append('overlay service: stopped')
        elif error:
            report.append(f'overlay service: {error}')
    if tray is not None:
        called, error = _call_first(tray, ('stop', 'close', 'shutdown'))
        if called:
            report.append('tray: stopped')
        elif error:
            report.append(f'tray: {error}')
    _stop_telemetry_worker(report)
    _close_rtss_instances(report)
    _dispose_lhm_objects(report)

    # El plan persistente debe ser la ÚLTIMA escritura de energía de CorePulse.
    # Se verifica de nuevo después de cerrar agente, overlay, bandeja y sensores,
    # de modo que ningún rollback temporal pueda quedar por encima de la elección
    # explícita del usuario.
    if performance is not None:
        finalize = getattr(performance, 'finalize_persistent_plan', None)
        if callable(finalize):
            try:
                persisted = finalize() or {}
                if persisted.get('success'):
                    report.append('performance plan: final Windows GUID verified')
                else:
                    report.append('performance plan: final verification failed: ' + str(persisted.get('message') or 'unknown'))
            except Exception as exc:
                report.append(f'performance plan finalization: {type(exc).__name__}: {exc}')

    time.sleep(0.1)
    try:
        gc.collect()
        report.append('gc: collected')
    except Exception as exc:
        report.append(f'gc: {type(exc).__name__}: {exc}')
    if verbose:
        print('[CorePulse Safe Shutdown]')
        for item in report:
            print(' -', item)
    return {'already_shutdown': False, 'steps': report}

def _atexit_shutdown():
    try:
        shutdown_corepulse_services(verbose=False)
    except Exception:
        pass
atexit.register(_atexit_shutdown)


# V482: fusión sin cambios de lógica desde core/runtime/pythonnet_shutdown.py
from core.version import VERSION_LABEL as VERSION
# Código refactorizado: nombres estables y documentación en español.
import gc
import importlib
import sys
import threading
import time
from typing import Any, Dict, List
def _safe_call(obj: Any, method: str, *args, **kwargs) -> bool:
    fn = getattr(obj, method, None)
    if not callable(fn):
        return False
    try:
        fn(*args, **kwargs)
        return True
    except Exception:
        return False

def _join_thread(thread: Any, timeout: float) -> bool:
    if not isinstance(thread, threading.Thread):
        return False
    if thread is threading.current_thread():
        return False
    try:
        if thread.is_alive():
            thread.join(timeout=max(0.0, float(timeout)))
        return not thread.is_alive()
    except Exception:
        return False

def _looks_like_sensor_provider(name: str, obj: Any) -> bool:
    n = str(name or '').lower()
    t = type(obj).__name__.lower()
    markers = ('computer', 'hardware', 'monitor', 'sensor', 'librehardware', 'lhm', 'provider')
    return any((x in n or x in t for x in markers))

def _close_provider_object(obj: Any) -> List[str]:
    actions: List[str] = []
    for method in ('stop', 'Stop', 'shutdown', 'Shutdown'):
        if _safe_call(obj, method):
            actions.append(method)
    for method in ('close', 'Close'):
        if _safe_call(obj, method):
            actions.append(method)
    for method in ('dispose', 'Dispose'):
        if _safe_call(obj, method):
            actions.append(method)
    return actions

def shutdown_telemetry_provider(*, join_timeout: float=3.0, verbose: bool=False) -> Dict[str, Any]:
    """Detiene la operación `shutdown_telemetry_provider` dentro de CorePulse sin alterar la evidencia real ni las reglas del módulo."""
    result: Dict[str, Any] = {'version': VERSION, 'module_loaded': False, 'hooks_called': [], 'objects_closed': [], 'threads_joined': [], 'threads_still_alive': [], 'forced_runtime_shutdown': False, 'ok': True}
    try:
        mod = sys.modules.get('core.telemetry_background')
        if mod is None:
            try:
                mod = importlib.import_module('core.telemetry_background')
            except Exception as exc:
                result['ok'] = False
                result['error'] = f'{type(exc).__name__}: {exc}'
                return result
        result['module_loaded'] = True
        for hook_name in ('stop_background_worker', 'shutdown_telemetry', 'shutdown', 'close', 'stop', 'cleanup', 'dispose'):
            hook = getattr(mod, hook_name, None)
            if callable(hook):
                try:
                    hook()
                    result['hooks_called'].append(hook_name)
                except Exception as exc:
                    result.setdefault('hook_errors', []).append(f'{hook_name}: {type(exc).__name__}: {exc}')
        try:
            lhm_mod = sys.modules.get('core.lhm_provider')
            if lhm_mod is None:
                lhm_mod = importlib.import_module('core.lhm_provider')
            provider = getattr(lhm_mod, '_PROVIDER', None)
            if provider is not None:
                actions = _close_provider_object(provider)
                if actions:
                    result['objects_closed'].append({'name': 'core.lhm_provider._PROVIDER', 'type': type(provider).__name__, 'actions': actions})
                try:
                    setattr(lhm_mod, '_PROVIDER', None)
                except Exception:
                    pass
                provider = None
        except Exception as exc:
            result.setdefault('hook_errors', []).append(f'lhm_provider: {type(exc).__name__}: {exc}')
        module_dict = dict(vars(mod))
        for name, obj in module_dict.items():
            if name.startswith('__'):
                continue
            if isinstance(obj, threading.Thread):
                continue
            if not _looks_like_sensor_provider(name, obj):
                continue
            actions = _close_provider_object(obj)
            if actions:
                result['objects_closed'].append({'name': name, 'type': type(obj).__name__, 'actions': actions})
        deadline = time.monotonic() + max(0.2, float(join_timeout))
        candidates = []
        for thread in threading.enumerate():
            lname = thread.name.lower()
            if any((x in lname for x in ('telemetry', 'hardware', 'sensor', 'libre', 'lhm'))):
                if thread is not threading.current_thread():
                    candidates.append(thread)
        for thread in candidates:
            remaining = max(0.0, deadline - time.monotonic())
            if _join_thread(thread, remaining):
                result['threads_joined'].append(thread.name)
            elif thread.is_alive():
                result['threads_still_alive'].append(thread.name)
        module_dict.clear()
        gc.collect()
        time.sleep(0.05)
        gc.collect()
        if verbose:
            print('[CorePulse] telemetry teardown:', result)
        return result
    except Exception as exc:
        result['ok'] = False
        result['error'] = f'{type(exc).__name__}: {exc}'
        return result

def wait_for_named_threads(names=('CorePulse-Telemetry',), timeout: float=3.0) -> Dict[str, Any]:
    wanted = {str(x) for x in names}
    deadline = time.monotonic() + max(0.0, float(timeout))
    joined = []
    alive = []
    for thread in list(threading.enumerate()):
        if thread.name not in wanted:
            continue
        remaining = max(0.0, deadline - time.monotonic())
        if _join_thread(thread, remaining):
            joined.append(thread.name)
        elif thread.is_alive():
            alive.append(thread.name)
    return {'joined': joined, 'still_alive': alive, 'ok': not alive}
