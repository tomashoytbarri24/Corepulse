import json
import os
import threading
import time
from types import SimpleNamespace
from concurrent.futures import Future

import psutil
import pytest
from PySide6.QtCore import QCoreApplication
from core.monitoring import telemetry as module


def hardware(kind, name, temp):
    sensor = SimpleNamespace(Name='CPU Package' if kind=='Cpu' else 'GPU Core',
        SensorType='Temperature', Identifier='/cpu/0/temperature/0' if kind=='Cpu' else '/gpu/0/temperature/0', Value=temp)
    return SimpleNamespace(Name=name, HardwareType=kind, Sensors=[sensor],
                           SubHardware=[], Update=lambda:None)


def test_cpu_selector_does_not_use_gpu_heat():
    computer=SimpleNamespace(Hardware=[hardware('GpuNvidia','NVIDIA',99),hardware('Cpu','AMD Ryzen',62)])
    assert module._read_cpu_computer(computer)['temp']==62
    computer.Hardware=[hardware('GpuNvidia','NVIDIA',99)]
    assert module._read_cpu_computer(computer)['temp'] is None


def test_failed_update_does_not_republish_a_cached_sensor_as_fresh():
    cpu=hardware('Cpu','AMD Ryzen',61)
    def failed_update(): raise OSError('Sensor perdió conexión')
    cpu.Update=failed_update
    assert module._read_cpu_computer(SimpleNamespace(Hardware=[cpu]))['temp'] is None


def test_stream_reuses_cpu_provider_and_does_not_scan_motherboard(capsys):
    created=[]
    class Provider:
        def __init__(self):
            self.Hardware=[hardware('Cpu','Intel CPU',54)]
            self.opens=self.closes=0
            created.append(self)
        def Open(self): self.opens+=1
        def Close(self): self.closes+=1
    class Stop:
        ticks=0
        def is_set(self): return False
        def wait(self,_seconds):
            self.ticks+=1
            return self.ticks>=3
    module.run_cpu_sensor_worker(stream=True,computer_factory=Provider,stop_event=Stop())
    assert len(created)==1 and created[0].opens==1 and created[0].closes==1
    assert not created[0].IsMotherboardEnabled and not created[0].IsControllerEnabled
    assert len([json.loads(s) for s in capsys.readouterr().out.splitlines()])==3


def test_client_drops_stale_samples():
    stream=module.CpuSensorStream.__new__(module.CpuSensorStream)
    stream._lock=threading.Lock()
    stream._latest=(100,{'temp':60})
    assert stream.latest(102)['temp']==60
    assert stream.latest(104) is None
    assert stream.latest(99) is None


def test_fast_wmi_accepts_cpu_only_and_releases_query_resources():
    class Rows(list):
        disposed=False
        def Dispose(self): self.disposed=True
    rows=Rows([
        {'Name':'GPU Core','Identifier':'/gpu-nvidia/0/temperature/0','Parent':'/gpu-nvidia/0','Value':99},
        {'Name':'CPU Package','Identifier':'/amdcpu/0/temperature/0','Parent':'/amdcpu/0','Value':57}])
    search=SimpleNamespace(Get=lambda:rows,Dispose=lambda:None)
    result=module._read_cpu_wmi_fast(lambda *args:search)
    assert result['temp']==57 and '(WMI)' in result['source']
    assert rows.disposed


def test_fast_wmi_unavailable_is_not_a_temperature():
    def unavailable(*args): raise TimeoutError('WMI no disponible')
    assert module._read_cpu_wmi_fast(unavailable) is None


def test_stalled_worker_is_restarted_instead_of_hanging_forever():
    class Process:
        kills=0
        def poll(self): return None
        def kill(self): self.kills+=1
    stream=module.CpuSensorStream.__new__(module.CpuSensorStream)
    stream._process=Process(); stream._heartbeat=100
    stream._kill_if_stalled(105)
    assert stream._process.kills==0
    stream._kill_if_stalled(109)
    assert stream._process.kills==1


def telemetry_without_system_probes(monkeypatch):
    app=QCoreApplication.instance() or QCoreApplication([])
    class Executor:
        def __init__(self,**kwargs): pass
        def submit(self,*args): return Future()
        def shutdown(self,**kwargs): pass
    class Stream:
        sample=None
        def latest(self,*args): return self.sample
        def close(self): pass
    monkeypatch.setattr(module,'ThreadPoolExecutor',Executor)
    monkeypatch.setattr(module,'CpuSensorStream',Stream)
    monkeypatch.setattr(module,'cpu_name',lambda:'CPU')
    monkeypatch.setattr(module,'machine_model',lambda:'PC')
    monkeypatch.setattr(module,'WindowsCpuFrequency',lambda:SimpleNamespace(read_performance_percent=lambda:None,close=lambda:None))
    return app,module.Telemetry()


def test_cpu_can_be_published_while_inventory_and_gpu_are_pending(monkeypatch):
    app,obj=telemetry_without_system_probes(monkeypatch)
    try:
        obj._cpu_stream.sample={'temp':58,'hardware':'AMD Ryzen','sensor':'CPU (Tctl/Tdie)'}
        obj._cpu_tick()
        assert obj.metrics['cpuTemp']==58
        assert obj.startupReady
        assert not obj._inventory_future.done() and not obj._gpu_future.done()
    finally: obj.close()


def test_startup_is_bounded_when_sensor_is_unavailable(monkeypatch):
    app,obj=telemetry_without_system_probes(monkeypatch)
    try:
        assert not obj.startupReady and obj.metrics['cpuTemp'] is None
        obj._started_at=time.monotonic()-3
        obj._cpu_tick()
        assert obj.startupReady and obj.metrics['cpuTemp'] is None
    finally: obj.close()


@pytest.mark.skipif(os.name!='nt',reason='Windows worker')
def test_actual_stream_first_response_and_shutdown():
    began=time.monotonic()
    stream=module.CpuSensorStream()
    try:
        while time.monotonic()-began<12 and stream.latest() is None:
            time.sleep(.05)
        assert stream.latest() is not None
        process=stream._process
        assert process is not None
        pid=process.pid
    finally: stream.close()
    deadline=time.monotonic()+3
    while time.monotonic()<deadline and psutil.pid_exists(pid): time.sleep(.05)
    assert not psutil.pid_exists(pid)
