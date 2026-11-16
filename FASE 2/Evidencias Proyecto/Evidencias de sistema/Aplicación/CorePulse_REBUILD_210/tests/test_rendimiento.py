"""Pruebas de rendimiento con límites de tiempo medibles.

Los límites tienen holgura para no fallar en equipos lentos, pero detectan regresiones
graves (por ejemplo, una consulta sin índice o una escritura por cada fila sin transacción).
"""
import json
import time

from core import runtime
from core.health.game_sessions import GameSessionStore
from core.maintenance import network
from core.tweaks import tweaks as tweaks_module


def _cronometrar(funcion):
    inicio = time.perf_counter()
    resultado = funcion()
    return time.perf_counter() - inicio, resultado


def test_una_hora_de_partida_se_guarda_en_menos_de_5_segundos(tmp_path):
    """720 muestras (una hora con una muestra cada 5 segundos) se registran en menos de 5 s."""
    store = GameSessionStore(tmp_path / 'game_sessions.sqlite3')
    try:
        sesion = store.start({'name': 'Juego', 'source': 'Steam', 'executable': 'juego.exe'}, 0.0, 'Equilibrado')
        agregados = {'active_seconds': 0, 'fps_sum': 0.0, 'fps_count': 0, 'fps_min': 60.0, 'fps_max': 60.0,
                     'frame_count': 0, 'cpu_peak': 50.0, 'gpu_peak': 60.0}

        def guardar():
            for i in range(720):
                store.sample(sesion, i * 5.0, {'fps': 60.0, 'cpu': 50.0, 'gpu': 60.0, 'ram': 40.0,
                                               'cpu_temp': 65.0, 'gpu_temp': 70.0}, agregados)

        segundos, _ = _cronometrar(guardar)
        assert segundos < 5.0, f'Guardar 720 muestras tomó {segundos:.2f} s'

        segundos, detalle = _cronometrar(lambda: store.detail(sesion))
        assert len(detalle['samples']) == 720
        assert segundos < 0.5, f'Leer el detalle de la partida tomó {segundos:.2f} s'
    finally:
        store.close()


def test_historial_de_100_partidas_se_lista_rapido(tmp_path):
    """La lista de sesiones de juego responde en menos de 0,2 s con el máximo de 100 partidas."""
    store = GameSessionStore(tmp_path / 'game_sessions.sqlite3')
    try:
        for i in range(100):
            sesion = store.start({'name': f'Juego {i}', 'source': 'Steam', 'executable': 'juego.exe'},
                                 i * 3600.0, 'Equilibrado')
            store.finish(sesion, i * 3600.0 + 1800, 55.0, 1000)
        segundos, resumenes = _cronometrar(store.summaries)
        assert len(resumenes) == 30
        assert segundos < 0.2, f'Listar sesiones tomó {segundos:.2f} s'
    finally:
        store.close()


def test_enmascarar_la_red_no_retrasa_la_interfaz():
    """Preparar la vista de Red avanzada con 50 adaptadores toma menos de 0,1 s."""
    datos = {'ipv4': '192.168.1.10', 'ssid': 'Red', 'adapters': [
        {'ipv4': f'10.0.{i}.1', 'ipv6': 'fe80::1', 'ssid': f'Red {i}'} for i in range(50)]}
    segundos, vista = _cronometrar(lambda: network._present_network(datos, revealed=()))
    assert len(vista['adapters']) == 50
    assert segundos < 0.1, f'Enmascarar 50 adaptadores tomó {segundos:.3f} s'


def test_respaldo_de_78_tweaks_se_guarda_y_lee_rapido(tmp_path):
    """Guardar y leer el respaldo completo de los tweaks toma menos de 0,5 s."""
    respaldo = tmp_path / 'tweaks_originales.json'
    datos = {'schema': 1, 'originales': {spec['id']: {'present': True, 'value': 1}
                                         for spec in tweaks_module._OPTIONS}}

    def ida_y_vuelta():
        tweaks_module._save_backup(respaldo, datos)
        return tweaks_module._load_backup(respaldo)

    segundos, leido = _cronometrar(ida_y_vuelta)
    assert leido == json.loads(json.dumps(datos))
    assert segundos < 0.5, f'Respaldo de tweaks tomó {segundos:.2f} s'


def test_codificacion_de_consola_se_calcula_una_sola_vez():
    """console_encoding() se consulta en cada comando de Windows; después de la primera vez es inmediata."""
    runtime.console_encoding()
    segundos, _ = _cronometrar(lambda: [runtime.console_encoding() for _ in range(10000)])
    assert segundos < 0.1, f'10.000 consultas tomaron {segundos:.3f} s'
