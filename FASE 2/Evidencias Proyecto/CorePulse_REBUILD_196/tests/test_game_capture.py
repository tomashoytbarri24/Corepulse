from types import SimpleNamespace
import ctypes
import json
import io
import time

import pytest
from PySide6.QtCore import QCoreApplication, QObject, QSettings, Signal

from core import overlay
from core.health import game_capture as capture
from core.health.fps import PresentMonFPSReader


class Source(QObject):
    sampleObserved = Signal(object)

    def setCaptureStatus(self, text):
        self.status = text


@pytest.fixture
def recorder(tmp_path):
    app = QCoreApplication.instance() or QCoreApplication([])
    source = Source()
    settings = QSettings(str(tmp_path / 'records.ini'), QSettings.IniFormat)
    control = capture.ProblemCapture(source, folder=tmp_path, settings=settings)
    yield control, source
    control.close()
    app.processEvents()


def observed(stamp, pid=42, ms=16.7):
    return dict(time=stamp, pid=pid, name='Juego de prueba', cpu=40, gpu=80, ram=65,
                cpuTemp=70, gpuTemp=61, frames=[(stamp, ms)])


def test_design_validation_bounds_duplicates_and_empty_metrics():
    value = capture.normalize_design(dict(scale=900, opacity=0, gap=-8, x=float('nan'),
                                          y=1500, metrics=['disk','fps','disk','unknown']))
    assert value == dict(scale=160, opacity=25, gap=0, x=1000, y=1000,
                         metrics=['disk','fps'], frametime=True)
    assert capture.normalize_design({'metrics':[]})['metrics'] == ['fps']
    assert capture.normalize_design({'metrics':'fps'})['metrics'] == ['fps','cpu','gpu','ram']


def test_raw_frame_summary_preserves_tirones_and_unknown():
    summary = capture.frame_summary([{'ms':16.7}]*99+[{'ms':125}])
    assert summary['median'] == 16.7
    assert summary['maximum'] == 125
    assert summary['slow'] == 1
    assert capture.frame_summary([])['maximum'] is None
    rows = [dict(time=i, ms=16.7) for i in range(1200)]
    rows[531]['ms'] = 200
    assert max(r['ms'] for r in capture.peak_series(rows)) == 200


def test_timed_frame_reader_is_independent_of_session_consumer():
    reader = PresentMonFPSReader()
    reader._pid = 42
    reader._timeline_frames.extend([(1,10,'main'),(2,50,'main'),(2,1,'other')])
    reader._frame_intervals.extend([(10,'main'),(50,'main'),(1,'other')])
    assert reader.take_timed_frame_intervals(99) == []
    assert reader.take_timed_frame_intervals(42) == [(1,10),(2,50)]
    assert reader.take_frame_intervals(42) == [10,50]
    assert reader.take_timed_frame_intervals(42) == []
    reader.close()


def test_presentmon_event_clock_keeps_original_spacing(monkeypatch):
    reader=PresentMonFPSReader()
    raw=(b'ProcessID,SwapChainAddress,MsBetweenPresents,TimeInSeconds\n'
         b'42,main,16.7,12.000\n42,main,80,12.080\n42,main,16.7,12.0967\n')
    process=SimpleNamespace(stdout=io.BytesIO(raw),poll=lambda:None)
    reader._pid,reader._process=42,process
    clock=iter([100,100.2,100.4])
    monkeypatch.setattr('core.health.fps.time.monotonic',lambda:next(clock))
    reader._consume(process,42)
    rows=reader.take_timed_frame_intervals(42)
    assert rows[1][0]-rows[0][0] == pytest.approx(.080)
    assert rows[2][0]-rows[1][0] == pytest.approx(.0167)
    assert [r[1] for r in rows]==[16.7,80,16.7]
    reader._process=None


def test_sensor_only_stream_does_not_create_automatic_record(recorder,monkeypatch):
    control,source=recorder
    monkeypatch.setattr(capture.time,'monotonic',lambda:100)
    source.sampleObserved.emit({**observed(100),'game':True,'frames':[]})
    assert not control.data['recording']
    assert not list(control._folder.glob('*.json'))


def test_foreground_change_finishes_partial_and_never_mixes_pids(stream):
    control, source, feed, clock = stream
    feed(106.5,frames=[(106.48,120)])
    feed(107,pid=43)
    assert control.data['selected']['partial']
    assert all(row['pid']==42 for row in control.data['selected']['samples'])
    assert control._pid==43


def test_close_saves_partial_once_and_skips_corrupt_file(stream):
    control, source, feed, clock = stream
    (control._folder/'CorePulse_Problema_bad.json').write_text('{',encoding='utf-8')
    feed(106.5,frames=[(106.48,120)])
    control.close()
    control.close()
    assert len(control.data['captures'])==1
    assert control.data['selected']['partial']
    assert 'cerró' in control.data['selected']['note']


@pytest.fixture
def stream(recorder, monkeypatch):
    control, source = recorder
    clock = [100.0]
    monkeypatch.setattr(capture.time, 'monotonic', lambda: clock[0])

    def feed(stamp, ms=16.7, pid=42, game=True, frames=None):
        clock[0] = stamp
        if frames is None:
            count = max(1, int(500 / ms))
            frames = [(stamp - (count - 1 - i) * ms / 1000, ms) for i in range(count)]
        source.sampleObserved.emit({**observed(stamp, pid=pid), 'game':game, 'frames':frames})
    for i in range(13):
        feed(100 + i * .5)
    return control, source, feed, clock


def test_automatic_spike_saves_real_event_and_following_frames(stream):
    control, source, feed, clock = stream
    for i in range(1,61):
        feed(106 + i * .5)
    feed(136.5, frames=[(136.48, 120)])
    assert control.data['automatic'] and control.data['recording']
    assert control._pending['mark'] == 136.48
    for i in range(1,31):
        feed(136.5 + i * .5)
    control._tick()
    row = control.data['selected']
    assert row['trigger']['kind'] == 'automatic'
    assert row['trigger']['frameMs'] == 120
    assert row['trigger']['baselineMs'] == pytest.approx(16.7)
    assert row['summary']['maximum'] == 120
    assert any(r['time']==0 and r['ms']==120 for r in row['frames'])
    assert row['preSeconds'] >= 29 and row['postSeconds'] >= 14
    assert not row['partial']
    assert 'Automático' in control.data['captures'][0]['label']
    assert len(list(control._folder.glob('*.json'))) == 1
    raw = json.loads(next(control._folder.glob('*.json')).read_text(encoding='utf-8'))
    assert len(raw['frames']) == raw['summary']['count']


def test_automatic_merges_nearby_spikes_and_waits_before_new_record(stream):
    control, source, feed, clock = stream
    feed(106.5, frames=[(106.48, 120)])
    feed(107, frames=[(106.98, 250)])
    for i in range(1,31):
        feed(107 + i * .5)
    control._tick()
    assert len(control.data['captures']) == 1
    assert control.data['selected']['summary']['maximum'] == 250
    # Keep observing actual frames through the cooldown; repeated peaks do not
    # produce overlapping records that evict all useful history.
    for i in range(1,90):
        stamp = 122 + i * .5
        feed(stamp, frames=[(stamp, 100)] if i % 10 == 0 else None)
        assert not control.data['recording']
    feed(167, frames=[(166.98, 120)])
    assert control.data['recording']


def test_automatic_does_not_treat_low_fps_or_a_sensor_value_as_stutter(stream):
    control, source, feed, clock = stream
    for i in range(1,41):
        feed(106+i*.5, ms=33.33)
    assert not control.data['recording']
    feed(127, frames=[])
    assert not control.data['recording']
    assert not list(control._folder.glob('*.json'))


@pytest.mark.parametrize('scenario', ['desktop','stale','invalid','duplicate','focus-change','capture-gap','no-game'])
def test_automatic_rejects_non_game_and_unverified_spikes(stream, scenario):
    control, source, feed, clock = stream
    if scenario == 'desktop':
        feed(106.5, game=False, frames=[(106.48,120)])
    elif scenario == 'stale':
        feed(106.5, frames=[(98,120)])
    elif scenario == 'invalid':
        feed(106.5, frames=[(106.48,float('nan')),(106.49,-1),(float('inf'),120)])
    elif scenario == 'duplicate':
        feed(106.5, frames=[(105.9,120)])
    elif scenario == 'focus-change':
        feed(106.5, pid=43, frames=[(106.48,120)])
    elif scenario == 'no-game':
        feed(106.5,pid=0,frames=[(106.48,120)])
    else:
        feed(110.5, frames=[(110.48,120)])
    assert not control.data['recording']
    assert not list(control._folder.glob('*.json'))


def test_automatic_preference_survives_restart_and_reenable_rearms(stream):
    control, source, feed, clock = stream
    control.setAutomatic(False)
    feed(106.5, frames=[(106.48,120)])
    assert not control.data['recording']
    other = capture.ProblemCapture(source, folder=control._folder, settings=control._settings)
    assert not other.data['automatic']
    other.close()
    control.setAutomatic(True)
    for i in range(1,14):
        feed(106.5+i*.5)
    feed(113.5,frames=[(113.48,120)])
    assert control.data['recording']
    assert control._pending['trigger']['kind']=='automatic'


def test_automatic_does_not_start_again_after_close(stream):
    control, source, feed, clock = stream
    control.close()
    feed(106.5, frames=[(106.48,120)])
    assert not control.data['recording']


def test_native_ipc_transports_design_and_unchanged_frame_peaks(tmp_path,monkeypatch):
    app = QCoreApplication.instance() or QCoreApplication([])
    class Keys:
        def __init__(self,*a):pass
        def start(self):pass
        def stop(self):pass
        def change(self,*a):pass
    monkeypatch.setattr(overlay,'GlobalHotkeys',Keys)
    monkeypatch.setattr(overlay,'QSettings',lambda *a:QSettings(str(tmp_path/'settings.ini'),QSettings.IniFormat))
    monkeypatch.setattr(overlay,'GAME_STATE_NAME',overlay.GAME_STATE_NAME+str(time.time_ns()))
    monkeypatch.setattr(overlay,'GAME_ACTION_NAME',overlay.GAME_ACTION_NAME+str(time.time_ns()))
    performance=SimpleNamespace(stopGameWatch=lambda *a:None)
    controller=overlay.OverlayController(SimpleNamespace(metrics={}),performance)
    try:
        controller.setDesign(dict(scale=130,opacity=60,gap=12,x=200,y=400,metrics=['gpu','fps'],frametime=True))
        controller.saveDesign('steam:sample')
        controller.setDesignGame('steam:sample')
        controller._frame_line.extend([(1,16.7),(2,140)])
        controller._write_game_state(42,{},99,'E34245','76B900',[])
        state=overlay._GameState.from_buffer_copy(controller._game_state_map[:])
        assert ctypes.sizeof(state)==1820
        assert state.designScale==130 and state.designOpacity==60
        assert state.designX==200 and state.designY==400
        assert list(state.metricOrder)[:2]==[2,0]
        assert state.frameCount==2 and state.frameMs[1]==140
        assert state.cpuRgb==0xE34245 and state.gpuRgb==0x76B900
        controller.setDesignGame('')
        assert controller.data['design']['scale']==100
        controller.setDesignGame('steam:sample')
        assert controller.data['design']['scale']==130
        controller.inheritDesign('steam:sample')
        assert controller.data['design']['scale']==100
    finally:
        controller.close()
        app.processEvents()
