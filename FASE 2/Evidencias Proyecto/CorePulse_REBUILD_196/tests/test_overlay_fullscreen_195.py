"""REBUILD 195: protección y selección del render sin Qt ni Windows."""
import ast
from pathlib import Path


SOURCE = (Path(__file__).resolve().parents[1] / 'core' / 'overlay.py').read_text(encoding='utf-8')


def _functions():
    tree = ast.parse(SOURCE)
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and
             node.name in {'_in_game_surface_ready', '_fullscreen_status'}]
    namespace = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), 'overlay.py', 'exec'), namespace)
    return namespace


def test_dont_hide_external_during_hook_startup():
    choose = _functions()['_in_game_surface_ready']
    assert not choose(1234, True, False)  # loader iniciado, sin fotogramas
    assert not choose(1234, False, True)  # autorización retirada
    assert not choose(0, True, True)
    assert choose(1234, True, True)


def test_status_does_not_promise_visibility_in_exclusive():
    status = _functions()['_fullscreen_status']
    assert 'sin bordes' in status(1234, True, True, False)
    assert 'render interno seleccionado' in status(1234, True, True, True)
    assert 'externo' in status(1234, True, False, False)
    assert 'Esperando un juego' in status(0, False, False, False)


def test_protected_arc_raiders_is_never_opted_in():
    assert "'pioneergame.exe'" in SOURCE
    assert 'if _game_is_protected(exe, modules):' in SOURCE
    assert 'if allowed and _game_is_protected(key):' in SOURCE
    assert 'if target_pid and not hook_ready and hook_allowed:' in SOURCE


def test_the_external_host_only_hides_when_internal_is_ready():
    assert "in_game_surface = _in_game_surface_ready(target_pid, hook_allowed, hook_ready)" in SOURCE
    assert "desktop_mode = ('HIDDEN' if in_game_surface else" in SOURCE
    assert 'draw_inside=bool(in_game_surface)' in SOURCE
    assert 'hook_starting' not in SOURCE
