"""Contratos de sesiones, perfiles y reportes sin iniciar un juego real."""
import sqlite3
import time
from types import SimpleNamespace

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QGuiApplication

from core.health import game_sessions
from core.health import monitoring_insights
from core.health import performance
from core.health.performance import game_profile_key


class _Performance(QObject):
    changed = Signal()

    def __init__(self, game):
        super().__init__()
        self.data = {
            'probableGames': [game], 'activeName': 'Equilibrado',
            'plans': [{'guid': '11111111-1111-1111-1111-111111111111', 'name': 'Alto rendimiento'}],
        }
        self.profiles = {}

    def startGameWatch(self, _client):
        pass

    def stopGameWatch(self, _client):
        pass

    def setGamePlanProfiles(self, profiles):
        self.profiles = profiles

    def refresh(self):
        pass


class _Overlay:
    def __init__(self, pid):
        self.data = {'targetPid': pid, 'fps': 100.0, 'fpsQuality': 'VALID_HOOK'}
        self.history = False
        self.applied = None

    def setFrameHistoryEnabled(self, value):
        self.history = value

    def setDesignGame(self, key):
        self.design_game = key

    def takeFrameIntervals(self, _pid):
        return [10.0] * 600

    def applyGameProfile(self, corner, temperatures):
        self.applied = (corner, temperatures)

    def clearGameProfile(self):
        self.applied = None


class _Telemetry:
    metrics = {'cpuPercent': 41.0, 'gpuPercent': 71.0, 'ramPercent': 52.0,
               'cpuTemp': 66.0, 'gpuTemp': 62.0}


def test_session_persists_real_samples_low_and_pdf(tmp_path, monkeypatch):
    QGuiApplication.instance() or QGuiApplication([])
    monkeypatch.setattr(game_sessions, '_windows_session_events', lambda *_: [])
    monkeypatch.setattr(game_sessions, '_output_dir', lambda: tmp_path)
    game = {'active': True, 'source': 'Steam', 'appid': '1234', 'name': 'Juego de prueba',
            'pid': 44221, 'executable': 'juego.exe'}
    perf, overlay = _Performance(game), _Overlay(game['pid'])
    controller = game_sessions.GameSessionsController(
        _Telemetry(), perf, overlay, database_path=tmp_path / 'sessions.sqlite3')
    try:
        now = time.time()
        controller._start(game, now)
        assert overlay.history
        for second in range(1, 13):
            controller._observe(now + second, 1.0)
        controller._finish(now + 13)
        detail = controller.data['detail']
        assert detail['name'] == game['name']
        assert detail['averageFps'] == 100.0
        assert detail['low_1'] == 100.0
        assert detail['frame_count'] == 7200
        assert detail['active_seconds'] == 12
        assert detail['gpu_peak'] == 62.0
        assert not overlay.history
        controller.exportPdf(detail['id'])
        assert (tmp_path / next(p.name for p in tmp_path.glob('CorePulse_Partida_*.pdf'))).stat().st_size > 2000
    finally:
        controller.close()
    reopened = game_sessions.GameSessionStore(tmp_path / 'sessions.sqlite3')
    try:
        assert reopened.summaries()[0]['low_1'] == 100.0
    finally:
        reopened.close()


def test_profile_uses_stable_game_key_and_rejects_missing_plan(tmp_path, monkeypatch):
    QGuiApplication.instance() or QGuiApplication([])
    monkeypatch.setattr(game_sessions, '_windows_session_events', lambda *_: [])
    game = {'active': True, 'source': 'Steam', 'appid': '1234', 'name': 'Juego de prueba',
            'pid': 44221, 'executable': 'juego.exe'}
    perf, overlay = _Performance(game), _Overlay(game['pid'])
    controller = game_sessions.GameSessionsController(
        _Telemetry(), perf, overlay, database_path=tmp_path / 'sessions.sqlite3')
    try:
        controller._start(game, time.time())
        key = game_profile_key(game)
        guid = perf.data['plans'][0]['guid']
        controller.saveProfile(key, guid, 'top-right', 'off')
        assert perf.profiles[key] == guid
        assert overlay.applied == ('top-right', 'off')
        controller.saveProfile(key, '99999999-9999-9999-9999-999999999999', 'top-left', 'on')
        assert perf.profiles[key] == guid
        assert 'no guardado' in controller.data['message']
    finally:
        controller.close()


def test_comparison_requires_same_game(tmp_path, monkeypatch):
    QGuiApplication.instance() or QGuiApplication([])
    monkeypatch.setattr(game_sessions, '_windows_session_events', lambda *_: [])
    game = {'active': True, 'source': 'Steam', 'appid': '1234', 'name': 'Juego de prueba',
            'pid': 44221, 'executable': 'juego.exe'}
    controller = game_sessions.GameSessionsController(
        _Telemetry(), _Performance(game), _Overlay(game['pid']),
        database_path=tmp_path / 'sessions.sqlite3')
    try:
        now = time.time()
        controller._start(game, now)
        first = controller.data['selectedId']
        controller._observe(now + 6, 1)
        controller._finish(now + 7)
        controller._start(game, now + 20)
        second = controller.data['selectedId']
        controller._observe(now + 26, 1)
        controller._finish(now + 27)
        controller.selectComparison(first)
        assert controller.data['comparison']['id'] == first
        other = {**game, 'appid': '5678', 'name': 'Otro juego'}
        controller._start(other, now + 30)
        assert controller.data['selectedId'] != second
        assert controller.data['comparison'] == {}
    finally:
        controller.close()


def test_one_percent_low_requires_real_frame_sample():
    assert game_sessions._one_percent_low([16.7] * 299) is None
    assert game_sessions._one_percent_low([16.7] * 297 + [50.0] * 3) == 20.0


def test_game_plan_switch_keeps_original_and_respects_manual_change(monkeypatch):
    original = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
    first = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'
    second = 'cccccccc-cccc-cccc-cccc-cccccccccccc'
    plans = [{'guid': guid, 'name': name} for guid, name in
             [(original, 'Equilibrado'), (first, 'Juego 1'), (second, 'Juego 2')]]
    current = [original]
    backup = [None]
    monkeypatch.setattr(performance, '_power_state_only', lambda: (plans, current[0]))
    monkeypatch.setattr(performance, '_read_auto_power_backup', lambda: backup[0])
    monkeypatch.setattr(performance, '_save_auto_power_backup',
                        lambda original_guid, boost_guid: backup.__setitem__(
                            0, {'originalGuid': original_guid, 'boostGuid': boost_guid}))
    monkeypatch.setattr(performance, '_clear_auto_power_backup', lambda: backup.__setitem__(0, None))

    def set_active(args):
        current[0] = args[1]
        return True, '', ''

    monkeypatch.setattr(performance, '_cmd', set_active)
    assert performance._auto_power_transition(True, first)[0] == 'ACTIVO'
    assert (current[0], backup[0]['originalGuid']) == (first, original)
    assert performance._auto_power_transition(True, second)[0] == 'ACTIVO'
    assert (current[0], backup[0]['originalGuid']) == (second, original)
    assert performance._auto_power_transition(False)[0] == 'RESTAURADO'
    assert (current[0], backup[0]) == (original, None)

    assert performance._auto_power_transition(True, first)[0] == 'ACTIVO'
    current[0] = second  # cambio manual fuera de CorePulse
    assert performance._auto_power_transition(False)[0] == 'MANUAL'
    assert current[0] == second


def test_damaged_history_is_set_aside_and_new_sessions_persist(tmp_path):
    QGuiApplication.instance() or QGuiApplication([])
    database = tmp_path / 'game_sessions.sqlite3'
    database.write_bytes(b'no es una base sqlite' * 500)
    performance = _Performance({'pid': 1, 'name': 'Juego', 'active': False})
    controller = game_sessions.GameSessionsController(SimpleNamespace(metrics={}), performance,
                                                      _Overlay(1), database_path=str(database))
    try:
        assert list(tmp_path.glob('*.danada-*'))[0].read_bytes().startswith(b'no es una base')
        assert database.is_file() and 'dañado' in controller._error
        assert controller._store.profiles() == {}
    finally:
        controller.close()


def test_monitoring_history_damage_cannot_block_startup(tmp_path, monkeypatch):
    QGuiApplication.instance() or QGuiApplication([])
    database = tmp_path / 'monitoring_history.sqlite3'
    database.write_bytes(b'no es una base sqlite' * 500)
    monkeypatch.setattr(monitoring_insights, '_database_path', lambda: database)
    monkeypatch.setattr(monitoring_insights.sys, 'platform', 'test')

    class Telemetry(QObject):
        metricsChanged = Signal()
        metrics = {}

    class Health(QObject):
        changed = Signal()
        data = {}

    telemetry, health = Telemetry(), Health()
    insights = monitoring_insights.MonitoringInsights(telemetry, health)
    try:
        assert list(tmp_path.glob('*.danada-*'))
        assert sqlite3.connect(database).execute('SELECT count(*) FROM alert_events').fetchone() == (0,)
    finally:
        insights._timer.stop()
        insights._closed = True
