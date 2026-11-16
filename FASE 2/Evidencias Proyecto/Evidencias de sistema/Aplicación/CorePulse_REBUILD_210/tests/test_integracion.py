"""Pruebas de integración: varios módulos trabajando juntos con almacenamiento real.

No modifican Windows: el Registro se simula y los archivos se crean en carpetas temporales.
"""
import sys

import pytest

from core import cuenta
from core.health.game_sessions import GameSessionStore
from core.tweaks import tweaks as tweaks_module


def _juego():
    return {'name': 'Juego de prueba', 'source': 'Steam', 'executable': r'C:\Juegos\prueba.exe', 'pid': 100}


def _agregados(fps_values):
    return {'active_seconds': len(fps_values) * 5, 'fps_sum': sum(fps_values), 'fps_count': len(fps_values),
            'fps_min': min(fps_values), 'fps_max': max(fps_values), 'frame_count': len(fps_values) * 300,
            'cpu_peak': 80.0, 'gpu_peak': 95.0}


def test_sesion_de_juego_completa_persiste_en_sqlite(tmp_path):
    """Inicio → muestras → incidencia → cierre → reapertura de la base: los datos se conservan."""
    base = tmp_path / 'game_sessions.sqlite3'
    store = GameSessionStore(base)
    sesion = store.start(_juego(), 1000.0, 'Alto rendimiento')
    fps = []
    for i, valor in enumerate([60.0, 58.0, 62.0, 30.0]):
        fps.append(valor)
        store.sample(sesion, 1000.0 + i * 5, {'fps': valor, 'cpu': 50.0, 'gpu': 70.0, 'ram': 40.0,
                                               'cpu_temp': 65.0, 'gpu_temp': None}, _agregados(fps))
    store.event(sesion, 1015.0, 'fps', 'Caída de FPS', 'Bajó de 60 a 30 FPS')
    store.finish(sesion, 1020.0, 30.0, 1200)
    store.close()

    reabierta = GameSessionStore(base)
    try:
        resumen = reabierta.summaries()[0]
        detalle = reabierta.detail(sesion)
    finally:
        reabierta.close()
    assert resumen['status'] == 'finalizada'
    assert resumen['averageFps'] == 52.5
    assert resumen['plan_name'] == 'Alto rendimiento'
    assert [m['fps'] for m in detalle['samples']] == [60.0, 58.0, 62.0, 30.0]
    assert detalle['samples'][0]['gpu_temp'] is None  # REAL_OR_NA: sin sensor se guarda vacío, no un valor inventado
    assert detalle['events'][0]['title'] == 'Caída de FPS'


def test_sesion_abierta_queda_interrumpida_al_reiniciar(tmp_path):
    """Si CorePulse se cierra con una partida en curso, al volver a abrir queda como interrumpida."""
    base = tmp_path / 'game_sessions.sqlite3'
    store = GameSessionStore(base)
    sesion = store.start(_juego(), 2000.0, 'Equilibrado')
    store.close()
    reabierta = GameSessionStore(base)
    try:
        assert reabierta.detail(sesion)['status'] == 'interrumpida'
    finally:
        reabierta.close()


class _RegistroSimulado:
    """Registro de Windows en memoria para probar el motor de tweaks sin tocar el equipo."""

    def __init__(self):
        self.valores = {}

    def leer(self, spec):
        clave = (spec['path'], spec['name'])
        if clave not in self.valores:
            return False, None, None
        return True, self.valores[clave], tweaks_module.winreg.REG_DWORD

    def escribir(self, spec, valor):
        self.valores[(spec['path'], spec['name'])] = int(valor)

    def restaurar(self, spec, original):
        clave = (spec['path'], spec['name'])
        if original['present']:
            self.valores[clave] = original['value']
        else:
            self.valores.pop(clave, None)


@pytest.fixture
def motor_tweaks(tmp_path, monkeypatch):
    if sys.platform != 'win32':
        pytest.skip('El motor de tweaks solo funciona en Windows')
    registro = _RegistroSimulado()
    monkeypatch.setattr(tweaks_module, '_is_windows_11', lambda: True)
    monkeypatch.setattr(tweaks_module, '_read_value', registro.leer)
    monkeypatch.setattr(tweaks_module, '_write_value', registro.escribir)
    monkeypatch.setattr(tweaks_module, '_restore_value', registro.restaurar)
    respaldo = tmp_path / 'tweaks_originales.json'
    manager = tweaks_module.TweaksManager(backup=respaldo)
    monkeypatch.setattr(manager, 'refresh', lambda *a, **k: None)
    spec = next(s for s in tweaks_module._OPTIONS if s['enabledByPolicy'])
    yield manager, registro, respaldo, spec
    manager.close()


def test_tweak_aplicar_y_restaurar_vuelve_al_estado_original(motor_tweaks):
    """Aplicar guarda el valor original en el respaldo; restaurar lo devuelve y limpia el respaldo."""
    manager, registro, respaldo, spec = motor_tweaks
    clave = (spec['path'], spec['name'])
    original = (int(spec['value']) + 1) % 2
    registro.valores[clave] = original

    mensaje = manager.applyTweak(spec['id'])
    assert 'verificado' in mensaje
    assert registro.valores[clave] == spec['value']
    guardado = tweaks_module._load_backup(respaldo)['originales'][spec['id']]
    assert guardado == {'present': True, 'value': original}

    mensaje = manager.restoreTweak(spec['id'])
    assert 'restaurado' in mensaje.lower()
    assert registro.valores[clave] == original
    assert spec['id'] not in tweaks_module._load_backup(respaldo)['originales']


def test_tweak_sin_valor_previo_se_restaura_eliminando_el_valor(motor_tweaks):
    """Si el valor no existía antes del tweak, restaurar lo elimina en vez de dejar uno inventado."""
    manager, registro, _respaldo, spec = motor_tweaks
    manager.applyTweak(spec['id'])
    assert (spec['path'], spec['name']) in registro.valores
    manager.restoreTweak(spec['id'])
    assert (spec['path'], spec['name']) not in registro.valores


def test_sesion_de_cuenta_se_guarda_y_se_lee_con_dpapi(tmp_path, monkeypatch):
    """Guardar la sesión cifra con DPAPI en disco y leerla devuelve el mismo token y perfil."""
    if sys.platform != 'win32':
        pytest.skip('DPAPI solo existe en Windows')
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    perfil = {'nombre': 'Prueba', 'plan': 'free'}
    assert cuenta.guardar_sesion('token-de-prueba-123', perfil)
    assert cuenta.leer_sesion() == ('token-de-prueba-123', perfil)
    cuenta.borrar_sesion()
    assert cuenta.leer_sesion() is None
