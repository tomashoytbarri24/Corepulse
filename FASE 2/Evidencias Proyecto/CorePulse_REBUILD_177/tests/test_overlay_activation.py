"""Regression checks for startup and windowed game routing."""

from types import SimpleNamespace
import codecs
import io
import time
import threading
from concurrent.futures import Future
import psutil
import pytest

from PySide6.QtCore import QCoreApplication

from core import overlay
from core.health.fps import PresentMonFPSReader, _decoded_lines
import core.health.fps as fps_module


def _authorize(controller, monkeypatch):
    """Routing tests model a game the user already authorized."""
    monkeypatch.setattr(controller, '_pid_game_key', lambda pid: 'juego-autorizado')
    controller._hook_games = {'juego-autorizado'}


@pytest.mark.parametrize('encoding,prefix', [
    ('utf-8', b''), ('utf-8', codecs.BOM_UTF8),
    ('utf-16-le', codecs.BOM_UTF16_LE), ('utf-16-be', codecs.BOM_UTF16_BE),
    ('utf-16-le', b''), ('utf-16-be', b''),
])
def test_presentmon_decodes_redirected_bytes_across_character_boundaries(encoding, prefix):
    class Chunks(io.BytesIO):
        def read1(self, size):
            return super().read(min(size, 3))
    original = 'Application,ProcessID\r\nJuego á.exe,42\r\n'
    assert list(_decoded_lines(Chunks(prefix + original.encode(encoding)))) == original.splitlines()


@pytest.mark.parametrize('metric,runtime', [
    ('MsBetweenPresents','PresentRuntime'), ('msBetweenPresents','Runtime'),
    ('FrameTime','PresentRuntime'),
])
def test_presentmon_accepts_official_csv_schemas_and_keeps_pid_isolation(metric, runtime):
    rows = f'Application,ProcessID,SwapChainAddress,{runtime},PresentMode,{metric}\n'
    rows += 'Juego,42,0xA,DXGI,Composed: Flip,16\n'
    rows += 'Otra app,7,0xA,DXGI,Composed: Flip,1\n'
    rows += 'Juego,42,0xA,DXGI,Composed: Flip,20\n'
    rows += 'Juego,42,0xA,DXGI,Composed: Flip,NaN\n'
    reader = PresentMonFPSReader()
    process = SimpleNamespace(stdout=io.BytesIO(codecs.BOM_UTF16_LE + rows.encode('utf-16-le')), poll=lambda: None)
    reader._process, reader._pid = process, 42
    reader._consume(process, 42)
    result = reader.snapshot(42)
    assert result['quality'] == 'VALID_ETW'
    assert result['fps'] == 55.6
    assert result['runtime'] == 'DXGI'
    assert reader.take_frame_intervals(42) == [16, 20]
    reader._process = None


def test_presentmon_reports_utf16_permission_errors():
    reader = PresentMonFPSReader()
    message = 'error: failed to start trace session: access denied.\n'
    process = SimpleNamespace(stderr=io.BytesIO(codecs.BOM_UTF16_LE + message.encode('utf-16-le')))
    reader._process = process
    reader._read_stderr(process)
    assert reader._permission_blocked
    reader._process = None


def test_presentmon_reports_lost_events_instead_of_waiting_forever():
    reader = PresentMonFPSReader()
    process = SimpleNamespace(stderr=io.BytesIO(b'warning: 400 ETW events were lost.\n'),poll=lambda: None)
    reader._process, reader._pid = process, 42
    reader._read_stderr(process)
    assert 'eventos ETW' in reader.snapshot(42)['reason']
    assert reader.snapshot(42)['fps'] is None
    reader._process = None


def test_capture_restart_waits_for_own_session_cleanup_without_blocking_ui(monkeypatch):
    reader = PresentMonFPSReader()
    waiting, release, launched = threading.Event(), threading.Event(), threading.Event()
    calls = []
    class Process:
        def __init__(self, old=False):
            self.old=old
            self.stdout=io.BytesIO(b'ProcessID,SwapChainAddress,MsBetweenPresents\n')
            self.stderr=io.BytesIO()
        def terminate(self): calls.append('terminate-old' if self.old else 'terminate-new')
        def wait(self, timeout=None):
            if self.old:
                waiting.set(); release.wait(2)
            return 0
        def poll(self): return None
    reader._process, reader._pid = Process(old=True), 42
    monkeypatch.setattr(reader,'_guard',lambda *args: calls.append(args[0]))
    def popen(*args,**kwargs):
        calls.append('launch'); launched.set(); return Process()
    monkeypatch.setattr(fps_module.subprocess,'Popen',popen)
    try:
        start=time.monotonic()
        reader._start(43)
        assert time.monotonic()-start < .25
        assert waiting.wait(1)
        assert not launched.is_set()
        release.set()
        assert launched.wait(2)
        assert calls.index('terminate-old') < calls.index('--stop-owner') < calls.index('launch')
    finally:
        release.set(); reader.shutdown()
        reader._worker.shutdown(wait=True)


def test_pending_capture_launch_is_cancelled_when_target_disappears(monkeypatch):
    reader = PresentMonFPSReader()
    entered, release = threading.Event(), threading.Event()
    def guard(*args):
        entered.set(); release.wait(2)
    monkeypatch.setattr(reader,'_guard',guard)
    monkeypatch.setattr(fps_module.subprocess,'Popen',lambda *args,**kwargs: pytest.fail('Stale launch'))
    reader._start(42)
    assert entered.wait(1)
    reader.close()
    release.set()
    reader._worker.shutdown(wait=True)
    assert reader._process is None and reader._pid == 0


class _Hotkeys:
    def __init__(self, *_args):
        pass

    def start(self):
        pass

    def change(self, *_args):
        pass

    def stop(self):
        pass


class _Performance:
    def __init__(self):
        self.data = {'probableGames': [], 'plans': []}
        self.clients = set()

    def startGameWatch(self, name):
        self.clients.add(name)

    def stopGameWatch(self, name):
        self.clients.discard(name)


def test_fps_display_holds_exact_sample_without_smoothing():
    app = QCoreApplication.instance() or QCoreApplication([])
    controller = overlay.OverlayController(SimpleNamespace(metrics={}), _Performance())
    try:
        assert controller._fps_for_display(42, 165.0, 10.0) == 165.0
        assert controller._fps_for_display(42, 154.3, 10.5) == 165.0
        assert controller._fps_for_display(42, 154.3, 11.21) == 154.3
        assert controller._fps_for_display(42, None, 11.3) is None
        assert controller._fps_for_display(43, 92.0, 11.4) == 92.0
    finally:
        controller.close()
        app.processEvents()


def test_live_fps_history_is_raw_while_osd_number_is_readable(monkeypatch):
    app = QCoreApplication.instance() or QCoreApplication([])
    monkeypatch.setattr(overlay, 'GlobalHotkeys', _Hotkeys)
    monkeypatch.setattr(overlay, '_foreground_process', lambda: (43210, 'SampleGame.exe'))
    monkeypatch.setattr(overlay, '_foreground_fullscreen', lambda: False)
    performance = _Performance()
    performance.data['probableGames'] = [{'active': True, 'pid': 43210}]
    controller = overlay.OverlayController(SimpleNamespace(metrics={}), performance)
    _authorize(controller, monkeypatch)
    current = [165.0]
    monkeypatch.setattr(controller, '_ensure_host', lambda: True)
    monkeypatch.setattr(controller, '_send', lambda value: True)
    monkeypatch.setattr(controller, '_game_actions', lambda pid: (True, current[0], 0, 1))
    try:
        controller._enabled = True
        controller._publish()
        assert controller.data['fps'] == 165.0
        assert controller.data['fpsValue'] == '165.0 FPS'
        current[0] = 154.3
        controller._publish()
        state = overlay._GameState.from_buffer_copy(controller._game_state_map[:])
        assert controller.data['fps'] == 154.3
        assert controller.data['fpsValue'] == '165.0 FPS'
        assert state.fps == b'165.0'
        controller._visible_fps_at -= 1.3
        controller._publish()
        state = overlay._GameState.from_buffer_copy(controller._game_state_map[:])
        assert state.fps == b'154.3'
    finally:
        controller.close()
        app.processEvents()


def test_overlay_starts_with_existing_game_and_routes_windowed_frames(monkeypatch):
    app = QCoreApplication.instance() or QCoreApplication([])
    monkeypatch.setattr(overlay, 'GlobalHotkeys', _Hotkeys)
    monkeypatch.setattr(overlay, '_foreground_process', lambda: (43210, 'SampleGame.exe'))
    monkeypatch.setattr(overlay, '_foreground_fullscreen', lambda: False)
    performance = _Performance()
    controller = overlay.OverlayController(SimpleNamespace(metrics={}), performance)
    _authorize(controller, monkeypatch)
    sent = []
    attempted = []
    raised = []
    monkeypatch.setattr(controller, '_ensure_host', lambda: True)
    monkeypatch.setattr(controller, '_send', lambda value: sent.append(value) or True)
    monkeypatch.setattr(controller, '_scan_launches', lambda: None)
    monkeypatch.setattr(controller, '_schedule_game_hook',
                        lambda pid, **_kwargs: attempted.append(pid))
    monkeypatch.setattr(controller, '_game_actions', lambda pid: (False, None, 0, 0))
    monkeypatch.setattr(controller._fps_reader, 'snapshot', lambda pid: {'quality': 'UNAVAILABLE'})
    monkeypatch.setattr(overlay, '_keep_host_above_windowed_game', lambda: raised.append(True))
    try:
        controller.startAutoWatch()
        assert controller.data['active']
        assert 'overlay' in performance.clients
        assert sent[-1] == 'MODE\tHIDDEN'

        performance.data['probableGames'] = [{'active': True, 'pid': 43210}]
        controller._publish()
        assert attempted[-1] == 43210
        state = overlay._GameState.from_buffer_copy(controller._game_state_map[:])
        assert state.targetPid == 43210
        assert not state.flags & 16  # host fallback owns the visible surface
        assert sent[-1] == 'MODE\tOSD'  # host fallback before first hooked frame
        assert controller.data['renderMode'] == 'ventana'
        controller._set(quickPanelVisible=True)
        controller._publish()
        state = overlay._GameState.from_buffer_copy(controller._game_state_map[:])
        assert state.flags & 2
        assert not state.flags & 16
        assert sent[-1] == 'MODE\tPANEL'
        monkeypatch.setattr(controller, '_game_actions', lambda pid: (True, 60.0, 0, 1))
        controller._publish()
        state = overlay._GameState.from_buffer_copy(controller._game_state_map[:])
        assert state.flags & 16  # the hooked renderer is now the only surface
        assert sent[-1] == 'MODE\tHIDDEN'
        assert raised
        assert controller.data['renderMode'] == 'juego'
    finally:
        controller.close()
        app.processEvents()


def test_multiple_loaded_graphics_apis_are_available_for_fallback():
    modules = {'d3d12.dll', 'd3d11.dll', 'd3d9.dll', 'opengl32.dll'}
    assert overlay._renderer_candidates(modules) == [
        'D3D12', 'D3D11', 'D3D9', 'OpenGL'
    ]


def test_failed_loader_uses_host_for_fullscreen_osd_and_mouse_panel(monkeypatch):
    app = QCoreApplication.instance() or QCoreApplication([])
    monkeypatch.setattr(overlay, 'GlobalHotkeys', _Hotkeys)
    monkeypatch.setattr(overlay, '_foreground_process', lambda: (43210, 'SampleGame.exe'))
    monkeypatch.setattr(overlay, '_foreground_fullscreen', lambda: True)
    controller = overlay.OverlayController(SimpleNamespace(metrics={}), _Performance())
    _authorize(controller, monkeypatch)
    sent = []
    monkeypatch.setattr(controller, '_ensure_host', lambda: True)
    monkeypatch.setattr(controller, '_send', lambda value: sent.append(value) or True)
    monkeypatch.setattr(controller, '_game_actions', lambda pid: (False, None, 0, 0))
    monkeypatch.setattr(controller._fps_reader, 'snapshot',
                        lambda pid: {'quality': 'UNAVAILABLE'})
    monkeypatch.setattr(controller, '_schedule_game_hook', lambda pid, **kwargs: None)
    monkeypatch.setattr(overlay, '_keep_host_above_windowed_game', lambda: None)
    try:
        controller._enabled = True
        controller._inject_result = 'LOADER_9_WINERR_5'
        controller._publish()
        assert sent[-1] == 'MODE\tOSD'
        assert controller.data['renderMode'] == 'respaldo externo'
        assert 'Error de Windows 5' in controller.data['hookDetail']
        controller._set(quickPanelVisible=True)
        controller._publish()
        assert sent[-1] == 'MODE\tPANEL'
    finally:
        controller.close()
        app.processEvents()


def test_overlay_disk_uses_model_mapped_to_system_volume():
    storage = SimpleNamespace(data={'volumes': [
        {'mount': 'C:\\', 'physicalName': 'SKHynix_HFS512GDE9X084N'},
        {'mount': 'D:\\', 'physicalName': 'MSI M450 1TB'},
    ]})
    assert overlay._overlay_disk_name({'diskLabel': 'C:\\', 'diskName': 'N/A'}, storage) == \
        'SKHynix_HFS512GDE9X084N'
    assert overlay._overlay_disk_name({'diskLabel': 'E:\\', 'diskName': 'N/A'}, storage) == \
        'Unidad E:\\'


def test_capture_tool_is_not_targeted_as_game_with_panel_open(monkeypatch):
    app = QCoreApplication.instance() or QCoreApplication([])
    monkeypatch.setattr(overlay, 'GlobalHotkeys', _Hotkeys)
    monkeypatch.setattr(overlay, '_foreground_process', lambda: (54321, 'SnippingTool.exe'))
    monkeypatch.setattr(overlay, '_foreground_fullscreen', lambda: True)
    controller = overlay.OverlayController(SimpleNamespace(metrics={}), _Performance())
    attempted = []
    monkeypatch.setattr(controller, '_ensure_host', lambda: True)
    monkeypatch.setattr(controller, '_send', lambda value: True)
    monkeypatch.setattr(controller, '_schedule_game_hook',
                        lambda pid, **kwargs: attempted.append(pid))
    try:
        controller._enabled = True
        controller._set(quickPanelVisible=True)
        controller._publish()
        assert attempted == []
        assert controller.data['targetPid'] == 0
    finally:
        controller.close()
        app.processEvents()


def test_presentmon_warning_is_not_permission_failure_but_denial_is():
    reader = PresentMonFPSReader()
    process = SimpleNamespace(stderr=['warning: requires Performance Log Users\n'])
    reader._process = process
    reader._read_stderr(process)
    assert not reader._permission_blocked

    process = SimpleNamespace(stderr=['error: failed to start trace session: access denied.\n'])
    reader._process = process
    reader._read_stderr(process)
    assert reader._permission_blocked
    assert 'Windows denegó' in reader._error
    reader._process = None
    assert reader.snapshot(0)['permissionRequired'] is True


def test_stalled_graphics_api_schedules_the_next_one(monkeypatch):
    app = QCoreApplication.instance() or QCoreApplication([])
    monkeypatch.setattr(overlay, 'GlobalHotkeys', _Hotkeys)
    controller = overlay.OverlayController(SimpleNamespace(metrics={}), _Performance())
    _authorize(controller, monkeypatch)
    calls = []
    finished = Future()
    finished.set_result('LOADED_D3D11')
    monkeypatch.setattr(controller._executor, 'submit',
                        lambda fn, pid, tried, allowed: calls.append((pid, tried)) or finished)
    try:
        controller._hook_attempted_pid = 43210
        controller._inject_result = 'LOADED_D3D12'
        controller._hook_attempted_at = time.monotonic() - 7
        controller._schedule_game_hook(43210)
        assert calls == [(43210, ('D3D12',))]
    finally:
        controller.close()
        app.processEvents()


class _FakeSettings:
    def __init__(self):
        self.values = {}

    def setValue(self, key, value):
        self.values[key] = value

    def sync(self):
        pass


def _foreground_game(monkeypatch, controller, pid=43210, fullscreen=True):
    sent = []
    monkeypatch.setattr(overlay, '_foreground_process', lambda: (pid, 'juego.exe'))
    monkeypatch.setattr(overlay, '_foreground_fullscreen', lambda: fullscreen)
    monkeypatch.setattr(overlay, '_keep_host_above_windowed_game', lambda: None)
    monkeypatch.setattr(controller, '_ensure_host', lambda: True)
    monkeypatch.setattr(controller, '_send', lambda value: sent.append(value) or True)
    monkeypatch.setattr(controller, '_game_actions', lambda target: (False, None, 0, 0))
    monkeypatch.setattr(controller, '_pid_game_key', lambda target: 'c:\\juegos\\juego.exe')
    monkeypatch.setattr(controller._fps_reader, 'snapshot', lambda target: {'quality': 'UNAVAILABLE'})
    monkeypatch.setattr(controller, '_settings', _FakeSettings())
    return sent


def _controller():
    QCoreApplication.instance() or QCoreApplication([])
    performance = SimpleNamespace(data={'probableGames': []}, startGameWatch=lambda client: None,
                                  stopGameWatch=lambda client: None)
    controller = overlay.OverlayController(SimpleNamespace(metrics={}), performance)
    controller._hook_games = set()
    return controller


def test_fullscreen_game_is_never_touched_without_user_permission(monkeypatch):
    controller = _controller()
    sent = _foreground_game(monkeypatch, controller)
    monkeypatch.setattr(overlay, '_inject_game_hook', lambda *args: pytest.fail('Injected'))
    monkeypatch.setattr(controller, '_schedule_game_hook', lambda *args, **kwargs: pytest.fail('Scheduled'))
    try:
        controller._enabled = True
        controller._publish()
        assert controller.data['inGameHook'] == 'DESACTIVADO'
        assert sent[-1] == 'MODE\tOSD'  # external host is the visible surface
        assert not overlay._GameState.from_buffer_copy(controller._game_state_map[:]).flags & 16
    finally:
        controller._enabled = False
        controller.close()


def test_permission_is_explicit_per_game_and_can_be_revoked(monkeypatch):
    controller = _controller()
    _foreground_game(monkeypatch, controller)
    attempted = []
    monkeypatch.setattr(controller, '_schedule_game_hook', lambda pid, **kwargs: attempted.append(pid))
    monkeypatch.setattr(overlay, '_game_is_protected', lambda *args: False)
    try:
        controller._enabled = True
        controller._publish()
        assert not attempted and controller.data['lastGameKey'].endswith('juego.exe')
        controller.setHookAllowed(True)
        assert 'overlay/hookGames' in controller._settings.values
        controller._publish()
        assert attempted == [43210] and controller.data['lastGameAllowed']
        controller.setHookAllowed(False)
        attempted.clear()
        controller._publish()
        assert not attempted and not controller.data['lastGameAllowed']
    finally:
        controller._enabled = False
        controller.close()


def test_protected_game_cannot_be_authorized(monkeypatch):
    controller = _controller()
    _foreground_game(monkeypatch, controller)
    monkeypatch.setattr(overlay, '_game_is_protected', lambda *args: True)
    try:
        controller._set(lastGameKey='c:\\juegos\\juego.exe')
        controller.setHookAllowed(True)
        assert not controller._hook_games
        assert 'antitrampas' in controller.data['message']
    finally:
        controller.close()


def test_loader_refuses_unauthorized_and_protected_processes(monkeypatch):
    process = psutil.Process()
    key = overlay._game_key(process.exe())
    monkeypatch.setattr(overlay.subprocess, 'run', lambda *args, **kwargs: pytest.fail('Loader started'))
    assert overlay._inject_game_hook(process.pid) == 'DESACTIVADO'
    assert overlay._inject_game_hook(process.pid, allowed=frozenset({'otro.exe'})) == 'DESACTIVADO'
    monkeypatch.setattr(overlay, '_game_is_protected', lambda *args: True)
    assert overlay._inject_game_hook(process.pid, allowed=frozenset({key})) == 'PROTECTED'


@pytest.mark.parametrize('layout', [
    ('Juego', 'EasyAntiCheat', 'Launcher.exe'),
    ('Juego', 'BattlEye', 'BEClient_x64.dll'),
])
def test_anticheat_is_found_in_the_game_folder_before_it_loads(tmp_path, layout):
    root = tmp_path.joinpath(*layout[:-1])
    root.mkdir(parents=True)
    (root / layout[-1]).write_bytes(b'')
    binary = tmp_path / 'Juego' / 'Binaries' / 'Win64'
    binary.mkdir(parents=True)
    assert overlay._folder_has_anticheat(binary / 'juego.exe')


def test_folder_scan_stops_at_the_shared_library_root(tmp_path):
    common = tmp_path / 'steamapps' / 'common'
    (common / 'OtroJuego' / 'EasyAntiCheat').mkdir(parents=True)
    (common / 'EasyAntiCheat_compartido').mkdir()
    game = common / 'Juego'
    game.mkdir()
    assert not overlay._folder_has_anticheat(game / 'juego.exe')


def test_known_protected_title_is_refused_by_name_without_scanning(monkeypatch):
    monkeypatch.setattr(overlay, '_folder_has_anticheat', lambda exe: pytest.fail('Scanned'))
    assert overlay._game_is_protected('C:/Juegos/Counter-Strike/CS2.EXE')
