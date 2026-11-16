"""Pruebas de seguridad y privacidad.

No modifican Windows: el Registro se simula y los archivos se crean en carpetas temporales.
"""
import hashlib
import json
import sys
import urllib.parse
import urllib.request

import pytest

from core import cuenta
from core.ai import NoRedirect
from core.maintenance import network
from core.tweaks import tweaks as tweaks_module


def test_archivo_de_sesion_no_guarda_el_token_en_texto_plano(tmp_path, monkeypatch):
    """cuenta.dat va cifrado: ni el token ni los datos del perfil aparecen legibles."""
    if sys.platform != 'win32':
        pytest.skip('DPAPI solo existe en Windows')
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    assert cuenta.guardar_sesion('token-secreto-abc123', {'email': 'usuario@ejemplo.cl'})
    contenido = (tmp_path / 'CorePulse' / 'cuenta.dat').read_bytes()
    assert b'token-secreto-abc123' not in contenido
    assert b'usuario@ejemplo.cl' not in contenido
    assert b'password' not in contenido.lower() and b'contrase' not in contenido.lower()


def test_archivo_de_sesion_manipulado_no_se_acepta(tmp_path, monkeypatch):
    """Un cuenta.dat alterado o ajeno no entrega un token: la sesión se considera cerrada."""
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    destino = tmp_path / 'CorePulse' / 'cuenta.dat'
    destino.parent.mkdir(parents=True)
    destino.write_bytes(json.dumps({'token': 'robado'}).encode('utf-8'))
    assert cuenta.leer_sesion() is None


def test_pkce_reto_es_sha256_del_verificador_y_el_verificador_no_viaja():
    """El navegador solo recibe el reto; el verificador queda en la app hasta canjear el código."""
    verificador, reto = cuenta.nuevo_par_pkce()
    assert len(verificador) >= 43
    assert reto == hashlib.sha256(verificador.encode('ascii')).hexdigest()
    url = cuenta.url_conectar('https://corepulse.cl', 51234, 'estado-1', reto)
    parametros = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    assert parametros['reto'] == [reto]
    assert verificador not in url


def test_pkce_genera_pares_distintos_cada_vez():
    pares = {cuenta.nuevo_par_pkce()[0] for _ in range(50)}
    assert len(pares) == 50


def test_cliente_de_ia_no_sigue_redirecciones():
    """Una redirección del servidor no puede desviar el token de la cuenta a otro dominio."""
    handler = NoRedirect()
    peticion = urllib.request.Request('https://ai.corepulse.cl/v1/chat')
    assert handler.redirect_request(peticion, None, 302, 'Found', {}, 'https://otro-sitio.example/robar') is None


def test_red_avanzada_oculta_ip_y_ssid_por_defecto():
    """Los datos de red sensibles se muestran enmascarados hasta que el usuario los revela."""
    datos = {'ipv4': '192.168.1.85', 'ipv6': 'fe80::1', 'ssid': 'MiRedCasa',
             'adapters': [{'ipv4': '10.0.0.7', 'ipv6': '2800:150::1', 'ssid': 'Oficina'}]}
    vista = network._present_network(datos, revealed=())
    texto = json.dumps(vista, ensure_ascii=False)
    for sensible in ('192.168.1.85', 'MiRedCasa', '10.0.0.7', 'Oficina', '2800:150::1'):
        assert sensible not in texto
    revelada = network._present_network(datos, revealed=('ipv4',))
    assert revelada['ipv4'] == '192.168.1.85'
    assert revelada['ssid'] != 'MiRedCasa'


class _RegistroSimulado:
    def __init__(self):
        self.valores = {}
        self.escrituras = 0

    def leer(self, spec):
        clave = (spec['path'], spec['name'])
        if clave not in self.valores:
            return False, None, None
        return True, self.valores[clave], tweaks_module.winreg.REG_DWORD

    def escribir(self, spec, valor):
        self.escrituras += 1
        self.valores[(spec['path'], spec['name'])] = int(valor)


@pytest.fixture
def motor(tmp_path, monkeypatch):
    if sys.platform != 'win32':
        pytest.skip('El motor de tweaks solo funciona en Windows')
    registro = _RegistroSimulado()
    monkeypatch.setattr(tweaks_module, '_is_windows_11', lambda: True)
    monkeypatch.setattr(tweaks_module, '_read_value', registro.leer)
    monkeypatch.setattr(tweaks_module, '_write_value', registro.escribir)
    respaldo = tmp_path / 'tweaks_originales.json'
    manager = tweaks_module.TweaksManager(backup=respaldo)
    monkeypatch.setattr(manager, 'refresh', lambda *a, **k: None)
    spec = next(s for s in tweaks_module._OPTIONS if s['enabledByPolicy'])
    yield manager, registro, respaldo, spec
    manager.close()


def test_tweak_desconocido_no_modifica_windows(motor):
    manager, registro, _respaldo, _spec = motor
    mensaje = manager.applyTweak('HKCU\\Software\\cualquier-cosa')
    assert mensaje.startswith('No disponible')
    assert registro.escrituras == 0


def test_si_no_se_puede_guardar_el_respaldo_no_se_toca_windows(motor, monkeypatch):
    """Falla cerrada: sin respaldo del valor original, el tweak no se aplica."""
    manager, registro, _respaldo, spec = motor

    def falla(*_args):
        raise OSError('disco lleno')

    monkeypatch.setattr(tweaks_module, '_save_backup', falla)
    mensaje = manager.applyTweak(spec['id'])
    assert 'No se pudo aplicar' in mensaje
    assert registro.escrituras == 0


def test_respaldo_alterado_se_rechaza(motor):
    """Un respaldo con claves o valores ajenos al catálogo no se usa para escribir el Registro."""
    manager, registro, respaldo, spec = motor
    respaldo.write_text(json.dumps({'schema': 1, 'originales': {
        'HKLM\\Software\\Malicioso': {'present': True, 'value': 1}}}), encoding='utf-8')
    with pytest.raises(ValueError):
        tweaks_module._load_backup(respaldo)
    mensaje = manager.applyTweak(spec['id'])
    assert 'No se pudo aplicar' in mensaje
    assert registro.escrituras == 0


def test_respaldo_con_valor_fuera_de_rango_se_rechaza(tmp_path):
    spec = next(s for s in tweaks_module._OPTIONS if s['enabledByPolicy'])
    respaldo = tmp_path / 'tweaks_originales.json'
    respaldo.write_text(json.dumps({'schema': 1, 'originales': {
        spec['id']: {'present': True, 'value': 2 ** 40}}}), encoding='utf-8')
    with pytest.raises(ValueError):
        tweaks_module._load_backup(respaldo)
