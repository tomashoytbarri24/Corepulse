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
    problemRequested = Signal()

    def setCaptureStatus(self, text):
        self.status = text


@pytest.fixture
def recorder(tmp_path):
    app = QCoreApplication.instance() or QCoreApplication([])
    source = Source()
    control = capture.ProblemCapture(source, folder=tmp_path)
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


def test_sensor_only_capture_is_explicitly_partial(recorder,monkeypatch):
    control,source=recorder
    monkeypatch.setattr(capture.time,'monotonic',lambda:100)
    source.sampleObserved.emit({**observed(100),'frames':[]})
    control.record()
    control._finish('')
    assert control.data['selected']['partial']
    assert control.data['selected']['summary']['count']==0
    assert 'ETW' in control.data['selected']['note']


def test_record_captures_pre_and_post_and_real_marker(recorder, monkeypatch):
    control, source = recorder
    now = [100.0]
    monkeypatch.setattr(capture.time, 'monotonic', lambda:now[0])
    for second in range(65,101):
        source.sampleObserved.emit(observed(second))
    source.problemRequested.emit()
    assert control.data['recording']
    for second in range(101,116):
        now[0] = second
        source.sampleObserved.emit(observed(second, ms=120 if second==103 else 16.7))
    control._tick()
    row = control.data['selected']
    assert not control.data['recording']
    assert row['preSeconds'] == 30 and row['postSeconds'] == 15
    assert not row['partial']
    assert row['samples'][0]['time'] == -30
    assert row['frames'][-1]['time'] == 15
    assert row['summary']['maximum'] == 120
    raw = json.loads(next(control._folder.glob('*.json')).read_text(encoding='utf-8'))
    assert len(raw['frames']) == 46


def test_foreground_change_finishes_partial_and_never_mixes_pids(recorder, monkeypatch):
    control, source = recorder
    monkeypatch.setattr(capture.time,'monotonic', lambda:100)
    source.sampleObserved.emit(observed(99))
    control.record()
    source.sampleObserved.emit(observed(100, pid=43))
    assert control.data['selected']['partial']
    assert all(row['pid']==42 for row in control.data['selected']['samples'])
    assert control._pid==43


def test_no_game_or_stale_samples_does_not_invent_recording(recorder, monkeypatch):
    control, source = recorder
    monkeypatch.setattr(capture.time,'monotonic',lambda:100)
    control.record()
    assert not control.data['recording']
    source.sampleObserved.emit(observed(90))
    control.record()
    assert not control.data['recording']
    assert not list(control._folder.glob('*.json'))


def test_close_saves_partial_once_and_skips_corrupt_file(recorder, monkeypatch):
    control, source = recorder
    monkeypatch.setattr(capture.time,'monotonic',lambda:100)
    (control._folder/'CorePulse_Problema_bad.json').write_text('{',encoding='utf-8')
    source.sampleObserved.emit(observed(100))
    control.record()
    control.record()
    assert 'Ya se' in control.data['message']
    control.close()
    control.close()
    assert len(control.data['captures'])==1
    assert control.data['selected']['partial']
    assert 'cerró' in control.data['selected']['note']


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
