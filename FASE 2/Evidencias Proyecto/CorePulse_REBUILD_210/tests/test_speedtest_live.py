"""JSONL real de Ookla y publicación de lecturas en vivo, sin depender de Qt."""
from __future__ import annotations

import ast
from collections import deque
from pathlib import Path
from queue import Empty, Queue
from threading import Thread
import json
import math
import os
import subprocess
import sys
import time

SOURCE = (Path(__file__).resolve().parents[1] / 'core/maintenance/speed_test.py').read_text('utf-8')
TREE = ast.parse(SOURCE)
NAMES = ('_num', '_safe_progress', '_subprocess_kwargs', '_ookla_bandwidth_mbps',
         '_ookla_stream_event', '_read_ookla_jsonl')


def _functions():
    nodes = [node for node in TREE.body if isinstance(node, ast.FunctionDef) and node.name in NAMES]
    env = {'json': json, 'math': math, 'os': os, 'subprocess': subprocess,
           'time': time, 'Thread': Thread, 'Queue': Queue, 'Empty': Empty, 'deque': deque}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), 'speed_test.py', 'exec'), env)
    return env


def test_official_jsonl_progress_maps_bytes_per_second_to_real_mbps():
    f = _functions()
    seen = []
    send = lambda item: seen.append(item)
    f['_ookla_stream_event']({'type': 'ping', 'ping': {'latency': 11.33, 'jitter': 1.25}}, send)
    f['_ookla_stream_event']({'type': 'download', 'progress': 0.48,
                              'download': {'bandwidth': 12_500_000}}, send)
    f['_ookla_stream_event']({'type': 'upload', 'upload': {'bandwidth': 3_125_000}}, send)
    assert [item['phase'] for item in seen] == ['ping', 'download', 'upload']
    assert seen[0]['live_ping_ms'] == 11.33 and seen[0]['live_jitter_ms'] == 1.25
    assert seen[1]['live_download_mbps'] == 100.0 and seen[1]['percent'] == 48
    assert seen[2]['live_upload_mbps'] == 25.0


def test_missing_or_invalid_partial_samples_are_not_invented():
    f = _functions()
    seen = []
    for data in [
        {'type': 'download', 'download': {}},
        {'type': 'upload', 'upload': {'bandwidth': -1}},
        {'type': 'download', 'download': {'bandwidth': 'nan'}},
        {'type': 'download', 'download': {'bandwidth': 'inf'}},
        {'type': 'result', 'download': {'bandwidth': 11}},
    ]:
        f['_ookla_stream_event'](data, seen.append)
    assert len(seen) == 4  # Los resultados finales no son muestras parciales.
    assert all('live_rate_mbps' not in item for item in seen)
    assert all('live_download_mbps' not in item for item in seen)
    assert all('live_upload_mbps' not in item for item in seen)


def test_jsonl_reader_streams_before_final_and_retains_authoritative_result():
    f = _functions()
    script = '''import json, sys, time
for event in (
 {'type':'ping','ping':{'latency':12.5,'jitter':1}},
 {'type':'download','download':{'bandwidth':5000000}},
 {'type':'upload','upload':{'bandwidth':1500000}},
 {'type':'result','download':{'bandwidth':4500000},'upload':{'bandwidth':1200000}}):
 print(json.dumps(event), flush=True)
 time.sleep(0.05)
'''
    updates = []
    code, result, errors = f['_read_ookla_jsonl']([sys.executable, '-u', '-c', script], 5, updates.append)
    assert code == 0 and not errors
    assert result['type'] == 'result' and result['download']['bandwidth'] == 4_500_000
    assert [u['phase'] for u in updates] == ['ping', 'download', 'upload']
    assert [u['live_rate_mbps'] for u in updates if 'live_rate_mbps' in u] == [40.0, 12.0]


def test_jsonl_reader_times_out_even_if_stdout_never_produces_a_line():
    f = _functions()
    import pytest
    with pytest.raises(subprocess.TimeoutExpired):
        f['_read_ookla_jsonl']([sys.executable, '-c', 'import time;time.sleep(30)'], 0.2, None)


def test_start_event_reports_ookla_server_only_when_present():
    f = _functions()
    seen = []
    f['_ookla_stream_event']({'type': 'testStart', 'server': {'name': 'Servidor verificado'}}, seen.append)
    f['_ookla_stream_event']({'type': 'testStart', 'server': {}}, seen.append)
    assert len(seen) == 1
    assert seen[0]['live_server_name'] == 'Servidor verificado'
    assert 'ip' not in ''.join(seen[0].keys()).lower()


def test_qml_gauge_uses_live_rates_and_does_not_fake_a_pulsing_speed():
    network = (Path(__file__).resolve().parents[1] / 'ui/NetworkPage.qml').read_text('utf-8')
    engine = SOURCE
    assert "--format=jsonl" in engine
    assert "subprocess.Popen(args, bufsize=1" in engine
    assert 'speedInfo.live_download_mbps' in network
    assert 'speedInfo.live_upload_mbps' in network
    assert 'speedInfo.live_ping_ms' in network
    assert 'speedInfo.live_jitter_ms' in network
    assert 'id: speedGauge' in network and 'property real visualRate' in network
    assert 'pulsePhase' not in network
    assert 'cloudflare' not in network.lower()
    assert 'speed.cloudflare.com' not in engine


def test_speedtest_layout_is_centered_and_matches_reference_states():
    network = (Path(__file__).resolve().parents[1] / 'ui/NetworkPage.qml').read_text('utf-8')
    start = network.index('// REBUILD 188: arco ligado')
    end = network.index('Text { text: "Datos de red ocultos', start)
    speed_section = network[start:end]
    assert 'id: speedStage' in speed_section
    assert 'id: startRing' in speed_section
    assert 'id: repeatRing' in speed_section
    assert 'id: finishedView' in speed_section
    assert 'id: resultSummary' in speed_section
    assert 'id: liveDial' in speed_section
    assert 'id: speedGauge' in speed_section
    assert 'Layout.fillWidth: true' in speed_section
    assert 'width: Math.min(parent.width - 24, 825)' in speed_section
    assert 'GridLayout {' in speed_section  # solo métricas finales, nunca el dial
    assert 'anchors.centerIn: parent' in speed_section
    assert 'speedInfo.busy ? 466 : speedInfo.result.ok ? 305 : 352' in speed_section
    assert 'const gradient = ctx.createLinearGradient' in speed_section
    assert 'onClicked: page.beginSpeedtest()' in speed_section
    assert 'Qt.openUrlExternally(link)' in speed_section  # terms link only; never automatic navigation
    assert 'Cloudflare' not in speed_section
    assert 'Behavior on visualRate' in speed_section
    assert 'ColorAnimation { duration: 570 }' in speed_section
    assert 'NumberAnimation on connectionSweep' in speed_section
    assert 'Behavior on animatedHeight' in speed_section
    assert 'speedGauge.currentRate >= 0 ? speedGauge.visualRate.toFixed(2) : "—"' in speed_section


def test_speedtest_arc_matches_needle_and_does_not_fake_a_full_ring():
    qml = (Path(__file__).resolve().parents[1] / 'ui/NetworkPage.qml').read_text('utf-8')
    start = qml.index('id: speedGauge')
    end = qml.index('Column {\n                                        anchors.horizontalCenter', start)
    gauge = qml[start:end]
    assert 'readonly property real arcFraction: phaseMeasuring && currentRate >= 0' in gauge
    assert 'gaugeFraction(visualRate, maxRate) : 0' in gauge
    assert 'const finish = begin + span * arcFraction' in gauge
    assert 'const angle = begin + span * arcFraction' in gauge
    assert 'onArcFractionChanged: requestPaint()' in gauge
    assert 'property real revealFraction' not in gauge
    assert 'speedInfo.live_download_mbps' in qml
    assert 'speedInfo.live_upload_mbps' in qml
    assert 'const finish = begin + span * revealFraction' not in gauge


def test_speedtest_no_dark_overlay_or_large_halo_circle():
    qml = (Path(__file__).resolve().parents[1] / 'ui/NetworkPage.qml').read_text('utf-8')
    start = qml.index('// REBUILD 188: arco ligado')
    end = qml.index('Text { text: "Datos de red ocultos', start)
    section = qml[start:end]
    assert 'color: "transparent"' in section
    assert 'width: Math.min(parent.width * 0.72, 520)' not in section
    assert 'width: Math.min(parent.width * 0.49, 350)' not in section
    assert 'Qt.alpha(page.cyan, speedInfo.busy ? 0.029 : 0.018)' not in section
    assert 'color: Qt.darker(' not in section
    assert 'GlassPanel {' in section


def test_speedtest_progress_and_results_remain_separate_from_live_indication():
    qml = (Path(__file__).resolve().parents[1] / 'ui/NetworkPage.qml').read_text('utf-8')
    # REBUILD 189+: progress is governed by measured Mbps, not synthetic phase percent.
    assert 'width: parent.width * (page.phaseHasLiveRate ? Math.max(0, Math.min(1, speedGauge.arcFraction)) : 0)' in qml
    assert 'speedInfo.result.download_mbps' in qml
    assert 'speedInfo.result.upload_mbps' in qml
    assert 'speedInfo.result.packet_loss_percent' in qml
    assert 'networkSpeedTest.startWithConsent("ookla",accepted)' in qml
    assert 'speedInfo.result.ok' in qml
