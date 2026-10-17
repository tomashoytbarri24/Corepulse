"""Contratos de base nueva, sin ejecutar operaciones ni necesitar PySide6."""
from __future__ import annotations
import ast
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
UI = ROOT / "ui"


def _helper(name):
    tree = ast.parse((ROOT / "core" / "monitoring" / "telemetry.py").read_text(encoding="utf-8"))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    import math
    namespace = {"math": math}
    exec(compile(ast.Module(body=[node], type_ignores=[]), "telemetry.py", "exec"), namespace)
    return namespace[name]


def test_minimal_tree_and_single_launcher():
    files = [p for p in ROOT.rglob("*") if p.is_file() and "__pycache__" not in p.parts and ".pytest_cache" not in p.parts]
    assert len(files) == 47
    assert (ROOT / "Reglas para crear Versiones nuevas.txt").is_file()
    assert (ROOT / "versiones" / "HISTORIAL.md").is_file()
    assert sorted(p.name for p in ROOT.glob("*.py")) == ["main.py"]
    assert len(list(ROOT.rglob("*.bat"))) == 1
    for forbidden in ("gui", "build", "runtime", "performance", "database"):
        assert not (ROOT / forbidden).exists()


def test_all_qml_components_exist():
    files = {p.stem for p in UI.glob("*.qml")}
    assert files == {"Main", "Overview", "HistoryChart", "MetricLine", "StatTile", "Glyph", "ComponentDetail", "TweaksPage", "CleanupPage", "ThinScroll", "HealthPage", "ThemesPage", "AIPage", "OverlayPage", "NetworkPage", "BenchmarkPage"}
    text = "\n".join(p.read_text(encoding="utf-8") for p in UI.glob("*.qml"))
    assert not re.search(r"Math\.random|synthetic|fake[_ ]?fps", text, re.I)


def test_health_not_invented():
    src = (ROOT / "core" / "monitoring" / "telemetry.py").read_text(encoding="utf-8")
    assert '"health": "N/A"' in src
    assert '"alerts": "N/A"' in src
    assert '"cpuTemp": None' in src


def test_percentage_rejects_missing_and_invalid_values():
    p = _helper("percentage")
    for value in (None, True, False, "N/A", "-", -1, 101, float("nan"), float("inf")):
        assert p(value) is None
    assert p(0) == 0.0
    assert p(37.24) == 37.2
    assert p(100) == 100.0


def test_uptime_reading_format():
    f = _helper("format_uptime")
    assert f(3661) == "01:01:01"
    assert f(0) == "00:00:00"
    assert f(-5) == "N/A"


def test_no_dangerous_automatic_windows_operations():
    text = (ROOT / "core" / "monitoring" / "telemetry.py").read_text(encoding="utf-8")
    for banned in ("reg delete", "powercfg", "taskkill", "shutdown /", "cleanmgr", "sc stop"):
        assert banned not in text.lower()


def test_new_project_not_importing_legacy():
    for p in (ROOT / "main.py", ROOT / "core" / "monitoring" / "telemetry.py"):
        source = p.read_text(encoding="utf-8")
        assert "main_legacy" not in source
        assert "gui." not in source
        assert "ui_qt" not in source


def _geometry_helper():
    # Extrae solo el cálculo puro, sin importar Qt, Windows ni el launcher.
    tree = ast.parse((ROOT / "main.py").read_text(encoding="utf-8"))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "steam_window_geometry")
    namespace = {}
    exec(compile(ast.Module(body=[node], type_ignores=[]), "main.py", "exec"), namespace)
    return namespace["steam_window_geometry"]


def test_steam_window_geometry_standard_and_scaled():
    steam_window_geometry = _geometry_helper()

    # Monitor grande: tamaño de referencia Steam, centrado en área útil.
    assert steam_window_geometry(0, 0, 1920, 1040) == (320, 160, 1280, 720)
    # Monitor portátil 1366x768 con barra de tareas (área útil 728 px).
    x, y, width, height = steam_window_geometry(0, 0, 1366, 728)
    assert width == int(1366 * .90)
    assert height == int(728 * .90)
    assert (x, y) == ((1366 - width) // 2, (728 - height) // 2)
    assert 0 <= x < x + width <= 1366
    assert 0 <= y < y + height <= 728
    # Monitor secundario con origen negativo: no recentrar en el principal.
    assert steam_window_geometry(-1920, 50, 1920, 1080) == (-1600, 230, 1280, 720)


def test_steam_window_geometry_small_monitor_does_not_exceed_work_area():
    steam_window_geometry = _geometry_helper()
    for dimensions in ((1024, 720), (850, 600), (400, 300)):
        x, y, width, height = steam_window_geometry(-150, 30, *dimensions)
        assert 0 < width <= dimensions[0]
        assert 0 < height <= dimensions[1]
        assert x >= -150 and y >= 30
        assert x + width <= -150 + dimensions[0]
        assert y + height <= 30 + dimensions[1]


def test_frameless_window_drag_is_accessible_and_controls_stay_clickable():
    qml = (UI / "Main.qml").read_text(encoding="utf-8")
    assert 'component WindowDragArea: MouseArea' in qml
    assert 'if(window.startSystemMove()) return' in qml
    assert 'onPositionChanged:function(mouse)' in qml
    assert 'anchors.right:sidebarToggle.left' in qml
    assert 'id: sidebarToggle' in qml
    assert 'anchors.right:windowActions.left' in qml
    assert 'anchors.bottom:parent.bottom' in qml
    assert 'height:16' not in qml
    assert 'startSystemResize(Qt.LeftEdge)' in qml
    assert 'startSystemResize(Qt.TopEdge)' in qml
    assert 'onClicked:window.sidebarCollapsed=!window.sidebarCollapsed' in qml
    assert 'if(modelData.action==="min")window.showMinimized()' in qml


def test_initial_window_uses_primary_screen_work_area_and_preserves_fullscreen():
    py = (ROOT / "main.py").read_text(encoding="utf-8")
    qml = (UI / "Main.qml").read_text(encoding="utf-8")
    assert 'screen.availableGeometry()' in py
    assert 'context.setContextProperty("initialWindowWidth", initial_width)' in py
    assert 'width:initialWindowWidth' in qml
    assert 'height:initialWindowHeight' in qml
    assert 'x:initialWindowX' in qml
    assert 'y:initialWindowY' in qml
    assert 'sequence:"F11"' in qml
    assert 'sequence:"Escape"' in qml


def test_sidebar_logo_removed_and_navigation_moves_up_without_losing_drag():
    qml = (UI / "Main.qml").read_text(encoding="utf-8")
    assert 'text:"Herramientas del equipo"' not in qml
    assert 'text:"COREPULSE"' not in qml
    # No modificar el encabezado general de la pantalla ni la identidad del PC.
    assert 'text:"Core"' in qml
    assert 'text:"Pulse"' in qml
    assert 'text:telemetry && telemetry.metrics ? telemetry.metrics.computer : "N/A"' in qml
    # La nueva cabecera lateral mide 52 px y su menú queda inmediatamente debajo.
    side_top = qml.split('id: sideTop', 1)[1].split('id:navScroll', 1)[0]
    assert 'height:52' in side_top
    assert 'id: sidebarToggle' in side_top
    assert 'WindowDragArea {' in side_top
    assert 'anchors.right:sidebarToggle.left' in side_top
    assert 'onClicked:window.sidebarCollapsed=!window.sidebarCollapsed' in side_top
    assert 'anchors.top:sideTop.bottom' in qml
    assert 'width:window.sidebarCollapsed ? 74 : 270' in qml


def test_sidebar_icons_are_specific_and_not_reused_in_key_entries():
    qml = (UI / "Main.qml").read_text(encoding="utf-8")
    expected = {
        'label:"Resumen",icon:"dashboard"',
        'label:"Benchmark",icon:"gauge"',
        'label:"Iniciar diagnóstico",icon:"scan"',
        'label:"Centro de salud",icon:"health_shield"',
        'label:"Limpieza de sistema",icon:"broom"',
        'label:"Tweaks Windows 11",icon:"sliders"',
        'label:"Alertas técnicas",icon:"bell_alert"',
        'label:"Tendencias",icon:"trend_up"',
        'label:"Historial de alertas",icon:"history"',
        'label:"CorePulse AI",icon:"spark_ai"',
    }
    for fragment in expected:
        assert fragment in qml
    assert 'label:"Iniciar diagnóstico",icon:"shield"' not in qml
    assert 'label:"Alertas técnicas",icon:"bell"' not in qml
    assert 'label:"Historial de alertas",icon:"bell"' not in qml

    glyph = (UI / "Glyph.qml").read_text(encoding="utf-8")
    for kind in ("dashboard", "gauge", "scan", "health_shield", "broom", "sliders", "bell_alert", "trend_up", "history", "spark_ai"):
        assert f'case "{kind}":' in glyph



def test_rebuild_008_direct_geometry_no_scaled_shape_and_sidebar_contract():
    qml = (UI / "Main.qml").read_text(encoding="utf-8")
    glyph = (UI / "Glyph.qml").read_text(encoding="utf-8")
    assert 'title:"CorePulse — Rebuild 107"' in qml
    assert 'Monitoreo real del equipo · Rebuild 107' in qml
    assert 'width:26;height:26;radius:9' in qml
    assert 'readonly property bool innerFrameVisible: !compactMode && (entry.active || entryMouse.containsMouse)' in qml
    assert 'readonly property bool innerFrameVisible: !compactMode && (extraEntry.active || extraMouse.containsMouse)' in qml
    assert 'width:22;height:22;kind:entry.modelData.icon' in qml
    assert 'width:22;height:22;kind:extraEntry.modelData.icon' in qml
    assert 'import QtQuick.Shapes' in glyph
    assert 'Shape {' in glyph and 'ShapePath {' in glyph
    assert 'PathSvg { path: glyph.fittedPath(glyph.iconPath(glyph.kind)) }' in glyph
    assert 'anchors.fill: parent' in glyph
    assert 'transform: Scale {' not in glyph
    assert 'xScale: glyph.width / 24' not in glyph
    assert 'yScale: glyph.height / 24' not in glyph
    assert 'Canvas {' not in glyph
    assert 'ShapePath.RoundCap' in glyph and 'ShapePath.RoundJoin' in glyph
    assert 'typeof Shape.CurveRenderer === "number"' in glyph
    assert 'Shape.CurveRenderer : Shape.GeometryRenderer' in glyph
    assert 'readonly property real effectiveStroke: Math.max(1.8, stroke * pixelScale)' in glyph
    assert 'window.selectedPage==="diagnostic"?diagnosticComponent' in qml
    assert 'window.selectedPage==="overlay"?overlayComponent' in qml
    assert 'text:"Iniciar diagnóstico"' in qml
    assert 'const relative = command !== type' in glyph
    assert 'type === "A"' in glyph and 'pos === 5' in glyph and 'pos === 6' in glyph


def test_rebuild_008_all_declared_icons_have_vector_paths_and_no_duplicates():
    import re
    qml = (UI / "Main.qml").read_text(encoding="utf-8")
    glyph = (UI / "Glyph.qml").read_text(encoding="utf-8")
    kinds = set(re.findall(r'icon:"([^"]+)"', qml))
    kinds.update(re.findall(r'kind:"([^"]+)"', (UI / "Overview.qml").read_text(encoding="utf-8")))
    kinds.update(re.findall(r'kind:"([^"]+)"', (UI / "StatTile.qml").read_text(encoding="utf-8")))
    kinds.update(re.findall(r'kind:"([^"]+)"', (UI / "MetricLine.qml").read_text(encoding="utf-8")))
    cases = set(re.findall(r'case "([^"]+)":', glyph))
    assert kinds <= cases, sorted(kinds - cases)

    pairs = re.findall(r'id:"([^"]+)",label:"[^"]+",icon:"([^"]+)"', qml)
    primary = pairs[:12]
    assert len(primary) == 12
    assert len({name for _, name in primary}) == 12
    extra = pairs[12:]
    assert len(extra) == 19
    assert len({name for _, name in extra}) == 19
    assert len({name for _, name in pairs}) == len(pairs)


def test_rebuild_008_user_rules_mandatory_before_creating_anything():
    rules = (ROOT / "Reglas para crear Versiones nuevas.txt").read_text(encoding="utf-8")
    history = (ROOT / "versiones" / "HISTORIAL.md").read_text(encoding="utf-8")
    assert "Si una versión quedó Obsoleta" in rules
    assert "no generar tantos archivos.py" in rules
    assert "Recuerda que las cosas que queden obsoletas" in rules
    assert "Reglas para crear Versiones nuevas.txt" in history
    assert "REBUILD 008" in history
    assert "Regla obligatoria: antes de crear cualquier versión" in rules
    assert "leer y respetar" in rules
    assert "antes de crear o modificar CUALQUIER elemento" not in history or "leer y respetar obligatoriamente" in history
    assert "**TXT obligatorio para crear cualquier cosa.**" in history


def test_rebuild_008_benchmark_gauge_curves_are_legible_and_only_icon_changed():
    import re
    glyph = (UI / "Glyph.qml").read_text(encoding="utf-8")
    gauge = glyph.split('case "gauge":', 1)[1].split('case "scan":', 1)[0]
    assert 'M 4 17 C 4 12 7.6 8 12 8 C 16.4 8 20 12 20 17' in gauge
    assert 'M 12 15.8 L 16.9 11.1' in gauge
    assert 'circle(12, 15.8, 1.4)' in gauge
    assert not re.search(r'(?<![A-Za-z])A\s+8\.3', gauge)
    main = (UI / "Main.qml").read_text(encoding="utf-8")
    assert 'label:"Benchmark",icon:"gauge"' in main
    rules = (ROOT / "Reglas para crear Versiones nuevas.txt").read_bytes()
    assert b"Regla obligatoria:" in rules


def _telemetry_helpers(*function_names):
    import math
    import statistics
    from types import SimpleNamespace
    tree = ast.parse((ROOT / "core" / "monitoring" / "telemetry.py").read_text(encoding="utf-8"))
    selected = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in function_names]
    namespace = {"math": math, "statistics": statistics, "re": re, "SimpleNamespace": SimpleNamespace}
    exec(compile(ast.Module(body=selected, type_ignores=[]), "telemetry.py", "exec"), namespace)
    return [namespace[name] for name in function_names]


def test_ram_percent_and_used_are_from_the_same_available_memory_snapshot():
    from types import SimpleNamespace
    pct, positive_number, ram_reading = _telemetry_helpers("percentage", "positive_number", "ram_reading")
    gb = 1024**3
    assert ram_reading(SimpleNamespace(total=16*gb, available=6*gb)) == (62.5, 10.0, 16.0)
    assert ram_reading(SimpleNamespace(total=16*gb, available=16*gb)) == (0.0, 0.0, 16.0)
    assert ram_reading(SimpleNamespace(total=16*gb, available=0)) == (100.0, 16.0, 16.0)
    assert ram_reading(SimpleNamespace(total=16*gb, available=17*gb)) == (None, None, 16.0)
    assert pct(float("inf")) is None
    assert positive_number(float("nan")) is None


def test_cpu_sensor_parser_never_accepts_zero_or_gpu_sensor_as_cpu_temperature():
    pct, positive_number, parse = _telemetry_helpers("percentage", "positive_number", "parse_cpu_sensors")
    items = [
        {"SensorType": "Temperature", "Name": "GPU Core", "Identifier": "/nvidiagpu/0/temperature/0", "Value": 63},
        {"SensorType": "Temperature", "Name": "CPU Package", "Identifier": "/intelcpu/0/temperature/0", "Value": 0},
        {"SensorType": "Temperature", "Name": "CPU Package", "Identifier": "/intelcpu/0/temperature/1", "Value": 75.4},
        {"SensorType": "Temperature", "Name": "CPU Core #1", "Identifier": "/intelcpu/0/temperature/3", "Value": 84},
        {"SensorType": "Clock", "Name": "CPU Core #1", "Identifier": "/intelcpu/0/clock/1", "Value": 4200},
        {"SensorType": "Clock", "Name": "CPU Core #2", "Identifier": "/intelcpu/0/clock/2", "Value": 4000},
        {"SensorType": "Clock", "Name": "Bus Speed", "Identifier": "/intelcpu/0/clock/0", "Value": 100},
    ]
    assert parse(items) == {"temp": 75.4, "ghz": 4.1}
    assert parse(items[:2]) == {"temp": None, "ghz": None}
    assert parse([{"SensorType":"Temperature", "Name":"CPU (Tctl/Tdie)",
                   "Identifier":"/amdcpu/0/temperature/0", "Value": 89}])["temp"] == 89


def test_nvidia_csv_validation_handles_na_and_single_device_consistently():
    percentage, positive_number, parse = _telemetry_helpers("percentage", "positive_number", "parse_nvidia_csv")
    assert parse("NVIDIA GeForce RTX 2070, 24 %, 52") == {"name": "NVIDIA GeForce RTX 2070", "usage": None, "temp": 52.0, "vramUsed": None, "vramTotal": None}
    assert parse("NVIDIA RTX, 21, 48")["usage"] == 21.0
    assert parse("NVIDIA RTX, 0, N/A") == {"name": "NVIDIA RTX", "usage": 0.0, "temp": None, "vramUsed": None, "vramTotal": None}
    assert parse("NVIDIA RTX, 999, 0") == {"name": "NVIDIA RTX", "usage": None, "temp": None, "vramUsed": None, "vramTotal": None}
    assert parse("") == {"name": "N/A", "usage": None, "temp": None, "vramUsed": None, "vramTotal": None}


def test_disk_physical_model_is_sanitized_and_unknown_stays_na():
    name = _telemetry_helpers("disk_display_name")[0]
    assert name("  SK hynix    PC601  ") == "SK hynix PC601"
    assert name(None) is None
    assert name("Unknown") is None


def test_cpu_clock_does_not_use_windows_base_clock_as_live_frequency():
    source = (ROOT / "core" / "monitoring" / "telemetry.py").read_text(encoding="utf-8")
    assert r'\Processor Information(_Total)\% Processor Performance' in source
    assert r'\Processor Information(_Total)\Processor Frequency' not in source
    assert "estimated_cpu_ghz" in source
    assert "read_performance_percent()" in source
    assert "speed = psutil.cpu_freq()" not in source.split('def refresh(self):', 1)[1].split('def close(self):', 1)[0]
    assert '"cpuTemp": None' in source
    assert '"diskName": "N/A"' in source
    assert "WindowsCpuFrequency()" in source
    assert "ThreadPoolExecutor(max_workers=2" in source
    assert "self._hardware_next_poll = now + 4.0" in source


def test_cpu_temp_gpu_ram_and_disk_model_are_presented_without_undefined():
    qml = (UI / "Overview.qml").read_text(encoding="utf-8")
    assert 'page.validNumber(page.m.cpuGHz)' in qml
    assert 'temperature: page.m.cpuTemp' in qml
    assert 'page.validNumber(page.m.gpuTemp)' in qml
    assert 'page.validNumber(page.m.ramUsed)&&page.validNumber(page.m.ramTotal)' in qml
    assert 'hardwareName:page.m.diskName' in qml
    assert 'Modelo N/A (' in qml
    assert 'page.m.diskLabel' in qml


def test_windows_hardware_provider_correlates_system_drive_and_cpu_sensor():
    """Prueba PowerShell simulado; no depende de Windows ni crea archivos/sistema."""
    import json
    import os
    import subprocess
    from types import SimpleNamespace

    tree = ast.parse((ROOT / "core" / "monitoring" / "telemetry.py").read_text(encoding="utf-8"))
    fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
              and node.name == "query_windows_hardware")
    percentage, positive, parse_cpu = _telemetry_helpers("percentage", "positive_number", "parse_cpu_sensors")
    disk_name = _telemetry_helpers("disk_display_name")[0]
    called = []

    def mock_run(args, **kwargs):
        called.append(args)
        data = {"sensors": [
            {"Identifier":"/intelcpu/0/temperature/0", "Name":"CPU Package", "SensorType":"Temperature", "Value":68.5},
            {"Identifier":"/intelcpu/0/clock/1", "Name":"Core #1", "SensorType":"Clock", "Value":4185},
            {"Identifier":"/nvidiagpu/0/temperature/0", "Name":"GPU Core", "SensorType":"Temperature", "Value":48},
        ], "disk":"SK hynix PC601 NVMe"}
        data["baseMHz"] = 2600
        return SimpleNamespace(returncode=0, stdout=json.dumps(data))

    namespace = {
        "os": SimpleNamespace(name="nt"),
        "shutil": SimpleNamespace(which=lambda name: "powershell.exe"),
        "subprocess": SimpleNamespace(run=mock_run, CREATE_NO_WINDOW=0, TimeoutExpired=subprocess.TimeoutExpired),
        "json": json,
        "parse_cpu_sensors": parse_cpu,
        "parse_cpu_extra_sensors": _telemetry_helpers("positive_number", "parse_cpu_extra_sensors")[1],
        "disk_display_name": disk_name,
        "positive_number": positive,
    }
    exec(compile(ast.Module(body=[fn], type_ignores=[]), "telemetry.py", "exec"), namespace)
    query = namespace["query_windows_hardware"]
    assert query("C:", True) == {"temp":68.5, "ghz":4.18, "disk":"SK hynix PC601 NVMe", "baseMHz":2600.0,
                                 "power":None, "coreTemps":[], "detailSource":"N/A"}
    command = called[0][-1]
    assert "Get-Partition -DriveLetter 'C'" in command
    assert 'root\\LibreHardwareMonitor' in command
    assert 'root\\OpenHardwareMonitor' in command
    assert "$true" in command
    assert query("C:", False)["disk"] == "SK hynix PC601 NVMe"  # lectura simulada
    assert query("C:", False)["baseMHz"] == 2600.0
    assert "$false" in called[-1][-1]
    assert query("&", True) == {"temp":None, "ghz":None, "disk":None, "baseMHz":None,
                                "power":None, "coreTemps":[], "detailSource":"N/A"}  # letra inválida
    assert len(called) == 3


def test_windows_cpu_turbo_clock_estimate_and_missing_values():
    percentage, positive_number, estimate = _telemetry_helpers(
        "percentage", "positive_number", "estimated_cpu_ghz")
    # 2600 MHz nominal + 165% de rendimiento medido = 4.29 GHz estimados.
    assert estimate(2600, 165) == 4.29
    assert estimate(2600, 100) == 2.6
    assert estimate(2600, 50) == 1.3
    assert estimate(None, 165) is None
    assert estimate(2600, None) is None
    for bad in (0, float("nan"), float("inf"), "N/A", True, 1000000):
        assert estimate(bad, 120) is None
        assert estimate(2600, bad) is None
    assert estimate(2600, 401) is None


def test_clock_reads_measured_cpu_sensor_before_windows_estimation():
    source = (ROOT / "core" / "monitoring" / "telemetry.py").read_text(encoding="utf-8")
    refresh = source.split("    def refresh(self):", 1)[1].split("    @Slot()\n    def close", 1)[0]
    assert refresh.index('clock = self._hardware["ghz"]') < refresh.index('read_performance_percent()')
    assert 'if now - self._cpu_sensor_time <= 12.0' in refresh
    assert '"cpuClockSource"] = "Clocks CPU medidos por monitor WMI"' in refresh
    assert '"cpuClockSource"] = "Estimación Windows PDH' in refresh
    assert '"gpuUtilSource"] = "NVIDIA-SMI / NVML' in refresh
    assert 'self._gpu_sample_time > 0 and now - self._gpu_sample_time <= 5.0' in refresh


def test_telemetry_sources_explain_comparability_without_changing_layout():
    overview = (UI / "Overview.qml").read_text(encoding="utf-8")
    meter = (UI / "MetricLine.qml").read_text(encoding="utf-8")
    assert 'page.m.cpuClockSource' in overview
    assert 'page.m.cpuTempSource' in overview
    assert 'page.m.gpuUtilSource' in overview
    assert 'HoverHandler { id: detailsHover }' in meter
    assert 'ToolTip.visible: detailsHover.hovered' in meter
    assert 'property string sourceHint:' in meter
    assert 'page.m.ramUsed.toFixed(1)' in overview
    assert 'hardwareName:page.m.diskName' in overview
    # Solo el origen de datos, no la geometría.
    assert 'implicitHeight: 78' in meter


def test_project_rules_unchanged_and_no_new_runtime_py_files():
    import hashlib
    rules = (ROOT / "Reglas para crear Versiones nuevas.txt").read_bytes()
    older = ROOT.parent / "CorePulse_REBUILD_009_TELEMETRIA_REAL" / "Reglas para crear Versiones nuevas.txt"
    if older.is_file():
        assert hashlib.sha256(rules).digest() == hashlib.sha256(older.read_bytes()).digest()
    assert sorted(f.name for f in ROOT.glob("*.py")) == ["main.py"]
    assert len(list(ROOT.glob("*.bat"))) == 1


def test_classic_hardwaremonitor_cpu_route_is_brought_back_without_importing_legacy_tree():
    source = (ROOT / "core" / "monitoring" / "telemetry.py").read_text(encoding="utf-8")
    req = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "from HardwareMonitor.Hardware import Computer" in source
    assert "computer.IsCpuEnabled = True" in source
    assert "computer.IsMotherboardEnabled = True" in source
    assert "computer.IsControllerEnabled = True" in source
    assert "computer.Close()" in source
    assert "query_packaged_cpu_temperature" in source
    assert "query_hardware_with_legacy" in source
    assert "self._executor.submit(query_hardware_with_legacy" in source
    assert "pythonnet>=3.1" in req
    assert "HardwareMonitor>=1.2.1" in req
    assert "CPU Package" in (ROOT / "versiones" / "HISTORIAL.md").read_text(encoding="utf-8")
    # Esta ruta es independiente del árbol grande; solo reutiliza la idea validada.
    assert "from core." not in source
    assert "import main_legacy" not in source


def test_classic_monitor_uses_separate_process_and_does_not_install_driver():
    source = (ROOT / "core" / "monitoring" / "telemetry.py").read_text(encoding="utf-8")
    assert '[sys.executable, "-B", "-c", _CPU_PACKAGE_PROBE]' in source
    assert "timeout=8" in source
    assert "CREATE_NO_WINDOW" in source
    assert "ttl = 2.0 if" in source and "else 20.0" in source
    assert "HardwareMonitor / LibreHardwareMonitorLib (directo)" in source
    # No bajar binarios ni ejecutar instaladores de controladores.
    for unsafe in ("winget install", "Install-Module", "Start-Service", "Add-WindowsDriver"):
        assert unsafe not in source


def test_classic_cpu_temperature_selection_disallows_gpu_nvm_and_zero():
    import json
    import subprocess
    import sys
    from types import SimpleNamespace
    tree = ast.parse((ROOT / "core" / "monitoring" / "telemetry.py").read_text(encoding="utf-8"))
    values = {node.targets[0].id: ast.literal_eval(node.value) for node in tree.body
              if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
              and node.targets[0].id == "_CPU_PACKAGE_PROBE"}
    embedded = values["_CPU_PACKAGE_PROBE"]
    ast.parse(embedded)
    assert '"gpu"' in embedded and '"nvme"' in embedded
    assert '5.0 <= number <= 115.0' in embedded
    assert '"cpu package"' in embedded
    assert '"motherboard"' not in embedded.lower() or "computer.IsMotherboardEnabled = True" in embedded
    assert 'computer.IsMotherboardEnabled = True' in embedded
    # La salida del monitor debe ser una muestra real con etiqueta e identidad.
    fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
              and node.name == "query_packaged_cpu_temperature")
    cache = {"at": 0.0, "data": None}
    def fake_run(args, **kwargs):
        assert args[:3] == [sys.executable, "-B", "-c"]
        return SimpleNamespace(stdout=json.dumps({"temp": 74.5, "hardware": "Intel Core i7",
                                                  "sensor": "CPU Package", "identifier": "/intelcpu/0/temperature/0"}),
                               stderr="", returncode=0)
    ns = {"os":SimpleNamespace(name="nt"), "time":SimpleNamespace(monotonic=lambda:42.0),
          "subprocess":SimpleNamespace(run=fake_run, CREATE_NO_WINDOW=0, TimeoutExpired=subprocess.TimeoutExpired),
          "sys":SimpleNamespace(executable=sys.executable),
          "_CPU_PACKAGE_PROBE":embedded, "_CPU_PACKAGE_PROBE_CACHE":cache,
          "json":json, "positive_number":_helper("positive_number"),
          "parse_cpu_extra_sensors":_telemetry_helpers("positive_number", "parse_cpu_extra_sensors")[1]}
    exec(compile(ast.Module(body=[fn],type_ignores=[]),"test.py","exec"),ns)
    result=ns["query_packaged_cpu_temperature"]()
    assert result["temp"] == 74.5
    assert "CPU Package" in result["sensor"]
    assert "directo" in result["source"]
    assert ns["query_packaged_cpu_temperature"]() == result  # caché; una sola lectura


def test_direct_cpu_sensor_is_used_when_wmi_has_no_temperature():
    tree = ast.parse((ROOT / "core" / "monitoring" / "telemetry.py").read_text(encoding="utf-8"))
    fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
              and node.name == "query_hardware_with_legacy")
    base = {"temp":None,"ghz":None,"disk":"SAMSUNG SSD","baseMHz":2600}
    ns = {"query_windows_hardware":lambda drive, disk:dict(base),
          "query_packaged_cpu_temperature":lambda:{"temp":73.0,"source":"LHM directo","sensor":"Intel / CPU Package"}}
    exec(compile(ast.Module(body=[fn],type_ignores=[]),"test.py","exec"),ns)
    value=ns["query_hardware_with_legacy"]("C:",True)
    assert value["temp"] == 73.0
    assert value["ghz"] is None
    assert value["disk"] == "SAMSUNG SSD"
    assert "Intel / CPU Package" in value["tempSource"]
    # La lectura directa más reciente tiene prioridad si WMI conserva una muestra antigua.
    ns["query_windows_hardware"] = lambda drive, disk:dict(base,temp=69.0)
    assert ns["query_hardware_with_legacy"]("C:",True)["temp"] == 73.0
    # Si no se dispone de lectura directa, la fuente WMI real sigue disponible.
    ns["query_packaged_cpu_temperature"] = lambda:{"temp":None,"reason":"no publicado"}
    assert ns["query_hardware_with_legacy"]("C:",True)["temp"] == 69.0
    # Con ningún sensor real, no inventa temperatura.
    ns["query_windows_hardware"] = lambda drive, disk:dict(base)
    ns["query_packaged_cpu_temperature"] = lambda:{"temp":None,"reason":"falta driver"}
    value = ns["query_hardware_with_legacy"]("C:",True)
    assert value["temp"] is None
    assert "falta driver" in value["tempSource"]


def test_classic_sensor_probe_executes_cpu_priority_and_oem_fallback():
    """Ejecuta el código antiguo adaptado con sensores ficticios SOLO en pruebas."""
    import contextlib
    import io
    import json
    import sys
    import types

    tree = ast.parse((ROOT / "core" / "monitoring" / "telemetry.py").read_text(encoding="utf-8"))
    probe = next(ast.literal_eval(n.value) for n in tree.body
                 if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
                 and n.targets[0].id == "_CPU_PACKAGE_PROBE")

    def run_probe(hardware):
        hardware_module = types.ModuleType("HardwareMonitor.Hardware")
        package = types.ModuleType("HardwareMonitor")
        package.__path__ = []

        class Computer:
            Hardware = hardware
            def Open(self):
                pass
            def Close(self):
                pass

        hardware_module.Computer = Computer
        original = {name: sys.modules.get(name) for name in ("HardwareMonitor", "HardwareMonitor.Hardware")}
        sys.modules["HardwareMonitor"] = package
        sys.modules["HardwareMonitor.Hardware"] = hardware_module
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out):
                exec(compile(probe, "embedded_classic.py", "exec"), {"__name__": "__main__"})
        finally:
            for name, module in original.items():
                if module is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = module
        return json.loads(out.getvalue().splitlines()[-1])

    def device(name, typ, sensors):
        def make_sensor(label, value):
            return types.SimpleNamespace(SensorType="Temperature", Value=value,
                                         Identifier=f"/{name.casefold()}/0/temperature/0", Name=label)
        return types.SimpleNamespace(Name=name, HardwareType=typ, Sensors=[make_sensor(*x) for x in sensors],
                                     SubHardware=[], Update=lambda:None)

    package = device("Intel Core i7-10750H", "Cpu", [("CPU Package", 73.5), ("Core #1", 80.4)])
    gpu = device("NVIDIA RTX 2070", "GpuNvidia", [("GPU Core", 58.0)])
    storage = device("Samsung NVMe", "Storage", [("Temperature", 46.0)])
    assert run_probe([package, gpu, storage])["temp"] == 73.5
    assert run_probe([gpu, storage])["temp"] is None
    controller = device("Embedded Controller", "SuperIO", [("CPU Temperature", 81.0), ("GPU", 65.0)])
    selection = run_probe([controller, gpu])
    assert selection["temp"] == 81.0
    assert selection["sensor"] == "CPU Temperature"


def test_available_readings_exactly_seven_real_metrics():
    import math
    fn, = _telemetry_helpers("build_available_readings")
    fully_available = {
        "cpuPercent": 13.0, "cpuGHz": 4.21, "cpuTemp": 61.5,
        "ramPercent": 49.0, "gpuPercent": 20.0, "gpuTemp": 44.0,
        "gpuVramUsed": 1.0, "gpuVramTotal": 8.0,
        "cpuClockSource": "Estimación Windows PDH (% rendimiento × nominal)",
        "cpuTempSource": "CPU Package · LHM", "gpuUtilSource": "NVIDIA-SMI / NVML",
    }
    rows, count = fn(fully_available)
    assert count == "7/7"
    assert len(rows) == 7
    assert len({row["id"] for row in rows}) == 7
    assert [row["status"] for row in rows] == ["Disponible"]*7
    assert rows[1]["value"] == "4.21 GHz (est.)"
    assert rows[1]["source"].startswith("Estimación Windows")
    measured_rows, _ = fn({**fully_available, "cpuClockSource": "Clocks CPU medidos por monitor WMI"})
    assert measured_rows[1]["value"] == "4.21 GHz"
    assert rows[6]["value"] == "1.00 / 8.00 GiB"
    none = {**fully_available, "cpuTemp": None, "gpuVramTotal": None}
    rows, count = fn(none)
    assert count == "5/7"
    assert rows[2]["status"] == "No disponible"
    assert rows[6]["status"] == "No disponible"
    rows, count = fn(none, cpu_pending=True, gpu_pending=True)
    assert count == "5/7"
    assert rows[2]["status"] == "Evaluando"
    assert rows[6]["status"] == "Evaluando"
    invalid = {k:None for k in fully_available}
    invalid["cpuPercent"] = float("nan")
    invalid["ramPercent"] = True
    invalid["gpuPercent"] = -1
    invalid["gpuVramUsed"] = 3
    invalid["gpuVramTotal"] = 2
    rows, count = fn(invalid)
    assert count == "0/7"
    assert all(row["value"] == "N/A" for row in rows)


def test_nvidia_vram_real_reading_and_unavailable_values():
    percentage, positive_number, parse = _telemetry_helpers("percentage", "positive_number", "parse_nvidia_csv")
    result = parse("NVIDIA RTX 2070, 19, 45, 2048, 8192")
    assert result["vramUsed"] == 2.0 and result["vramTotal"] == 8.0
    assert result["usage"] == 19.0
    assert parse("NVIDIA RTX, 18, 40, N/A, 8192")["vramUsed"] is None
    assert parse("NVIDIA RTX, 18, 40, 10000, 8192")["vramTotal"] is None
    assert parse("NVIDIA RTX, 18, 40, 0, 8192")["vramUsed"] == 0.0
    source = (ROOT/"core"/"monitoring"/"telemetry.py").read_text(encoding="utf-8")
    assert "memory.used,memory.total" in source


def test_readings_tile_keeps_new_name_and_navigates_with_hover():
    main = (UI/"Main.qml").read_text(encoding="utf-8")
    overview = (UI/"Overview.qml").read_text(encoding="utf-8")
    tile = (UI/"StatTile.qml").read_text(encoding="utf-8")
    assert 'title:"Lecturas disponibles"' in overview
    assert 'title:"Trazabilidad"' not in overview
    assert 'onActivated:page.openReadings()' in overview
    assert 'onOpenReadings: window.selectedPage="readings"' in main
    assert 'window.selectedPage==="readings"?readingsComponent:' in main
    assert 'onClicked:window.selectedPage="summary"' in main
    assert 'text:"Lecturas disponibles"' in main
    assert 'model:readingsPage.readingRows' in main
    assert 'tile.interactive && tileMouse.containsMouse' in tile
    assert 'onClicked: tile.activated()' in tile
    rules = (ROOT/'Reglas para crear Versiones nuevas.txt').read_text(encoding='utf-8')
    assert 'antes de crear cualquier versión' in rules


def test_rebuild_013_cpu_clock_label_has_no_unusual_prefix_but_keeps_estimate_honest():
    overview = (UI / "Overview.qml").read_text(encoding="utf-8")
    main = (UI / "Main.qml").read_text(encoding="utf-8")
    source = (ROOT / "core" / "monitoring" / "telemetry.py").read_text(encoding="utf-8")
    assert 'page.m.cpuGHz.toFixed(2)+" GHz"' in overview
    assert '" (est.)"' in overview
    assert '"≈"' not in overview
    assert 'clock_suffix = " (est.)"' in source
    assert 'clock_marker' not in source
    assert 'GHz{clock_suffix}' in source
    assert 'sourceHint:"Frecuencia: "' in overview  # la explicación sigue disponible
    assert 'title:"CorePulse — Rebuild 107"' in main


def test_rebuild_013_readings_scrollbar_dark_thin_and_not_overlapping_values():
    main = (UI / "Main.qml").read_text(encoding="utf-8")
    block = main.split('id:readingsComponent', 1)[1].split('id:placeholderComponent', 1)[0]
    assert 'id:readingsScroll' in block
    assert 'contentHeight:readingsList.implicitHeight' in block
    assert 'width:Math.max(0,readingsScroll.width-16)' in block
    assert 'ThinScroll {' in block
    assert 'target: readingsScroll' in block
    assert 'anchors.right: parent.right' in block
    assert 'ScrollBar.vertical:' not in block
    assert 'model:readingsPage.readingRows' in block
    assert 'clip:true;boundsBehavior:Flickable.StopAtBounds' in block
    assert 'ScrollBar.vertical:ScrollBar { policy:ScrollBar.AsNeeded }' not in block


# REBUILD 014: CPU/GPU/RAM con inventario Windows verificable y vista compartida.
def test_014_clicking_only_cpu_gpu_ram_icons_opens_real_component_page():
    overview = (UI / "Overview.qml").read_text(encoding="utf-8")
    meter = (UI / "MetricLine.qml").read_text(encoding="utf-8")
    main = (UI / "Main.qml").read_text(encoding="utf-8")
    detail = (UI / "ComponentDetail.qml").read_text(encoding="utf-8")
    for kind in ("cpu", "gpu", "ram"):
        assert f'onActivated:page.openComponent("{kind}")' in overview
        assert f'"{kind}"' in main
    assert 'signal activated()' in meter
    assert 'property bool interactive: false' in meter
    assert 'enabled:meter.interactive' in meter
    assert 'onClicked:meter.activated()' in meter
    assert 'title:"SSD";kind:"storage";interactive:true' in overview
    assert 'onActivated:page.openComponent("storage")' in overview
    assert 'window.selectedPage = kind' in main
    assert 'componentKind:window.selectedPage' in main
    assert 'ComponentDetail {' in main
    assert 'onGoBack:window.selectedPage="summary"' in main
    assert 'ThinScroll {' in detail and 'target: scroller' in detail
    assert 'model:page.keyFacts' in detail
    assert 'model:page.quickFacts' in detail


def test_014_windows_inventory_parses_smbios_real_fields_and_rejects_untrusted():
    positive, parse = _telemetry_helpers("positive_number", "parse_component_inventory")
    inventory = parse({
        "cpu": [{"Manufacturer":" Intel ", "SocketDesignation":"U3E1", "NumberOfCores":6, "NumberOfLogicalProcessors":12}],
        "memory": [{"DeviceLocator":" DIMM 0 ", "Manufacturer":"Samsung", "PartNumber":"M471", "Capacity":8*1024**3,
                    "ConfiguredClockSpeed":3200, "SMBIOSMemoryType":26},
                   {"DeviceLocator":"DIMM 1", "Capacity":8*1024**3, "Speed":3200, "SMBIOSMemoryType":26}],
        "video": [{"Name":"Intel(R) UHD Graphics", "DriverVersion":"30.0.1"},
                  {"Name":"NVIDIA GeForce RTX 2070", "DriverVersion":"31.0.15.7000"}],
    })
    assert inventory["cpuPhysicalCores"] == 6
    assert inventory["cpuLogicalThreads"] == 12
    assert inventory["ramModules"][0]["type"] == "DDR4"
    assert inventory["ramModules"][0]["capacityGB"] == 8
    assert inventory["ramModules"][0]["speedMHz"] == 3200
    assert inventory["ramModules"][1]["manufacturer"] == "N/A"
    assert len(inventory["gpuAdapters"]) == 2
    missing = parse({"cpu":{"NumberOfCores":0,"NumberOfLogicalProcessors":-1},
                     "memory":[{"Capacity":None,"Speed":0,"SMBIOSMemoryType":0}],
                     "video":[{"Name":"Unknown","DriverVersion":"123"}]})
    assert missing["cpuPhysicalCores"] is None
    assert missing["cpuLogicalThreads"] is None
    assert missing["ramModules"][0]["speedMHz"] is None
    assert missing["ramModules"][0]["type"] == "N/A"
    assert missing["gpuAdapters"] == []
    assert parse(None)["ramModules"] == []


def test_014_gpu_driver_identity_is_not_guessed_for_integrated_card():
    find, = _telemetry_helpers("find_gpu_driver")
    adapters = [{"name":"Intel UHD Graphics", "driver":"1.1"},
                {"name":"NVIDIA GeForce RTX 2070", "driver":"31.0"}]
    assert find("NVIDIA GeForce RTX 2070", adapters) == "31.0"
    assert find("AMD Radeon", adapters) == "N/A"
    assert find("N/A", adapters) == "N/A"
    assert find(None, adapters) == "N/A"
    src = (ROOT / "core" / "monitoring" / "telemetry.py").read_text(encoding="utf-8")
    assert 'Get-CimInstance Win32_Processor' in src
    assert 'Get-CimInstance Win32_PhysicalMemory' in src
    assert 'Get-CimInstance Win32_VideoController' in src
    assert 'self._inventory_future = self._executor.submit(query_windows_component_inventory)' in src
    assert 'self._inventory_requested = True' in src
    assert 'metrics["ramAvailable"]' in src
    assert 'self._inventory_ready = True' in src
    assert 'if not self._inventory_requested:' in src
    assert (ROOT / "Reglas para crear Versiones nuevas.txt").is_file()


# REBUILD 015 — Presentación en lenguaje comprensible y sensores opcionales reales.
def test_015_component_pages_are_friendly_and_advanced_details_opt_in():
    view = (UI / "ComponentDetail.qml").read_text(encoding="utf-8")
    assert 'property bool advancedOpen: false' in view
    assert 'Ver detalles avanzados' in view
    assert 'CÓMO INTERPRETARLO' in view
    assert 'CONOCE TU PROCESADOR' in view
    assert 'CONOCE TU TARJETA GRÁFICA' in view
    assert 'CONOCE TU MEMORIA RAM' in view
    assert 'text:page.guidance' in view
    assert 'model:page.quickFacts' in view
    assert 'model:page.keyFacts' in view
    assert 'visible:page.advancedOpen' in view
    assert 'model:page.technicalFacts' in view
    assert 'm.cpuPackagePower' in view
    assert 'm.cpuDetailSource' in view
    assert 'page.m.cpuCoreTemps' in view
    assert 'model:page.componentKind === "ram" ? (page.m.ramModules || []) : []' in view
    assert 'model:page.componentKind === "gpu" ? (page.m.gpuAdapters || []) : []' in view
    assert 'ThinScroll {' in view and 'target: scroller' in view
    assert 'onClicked:page.goBack()' in view
    assert 'Math.random' not in view

def test_015_optional_cpu_sensor_details_reject_unrelated_devices_and_invalid_readings():
    import re
    positive, parser = _telemetry_helpers("positive_number", "parse_cpu_extra_sensors")
    parser.__globals__["positive_number"] = positive
    parser.__globals__["re"] = re
    rows = [
        {"Identifier":"/intelcpu/0/power/0", "SensorType":"Power", "Name":"CPU Package", "Value":38.54},
        {"Identifier":"/intelcpu/0/power/1", "SensorType":"Power", "Name":"CPU Cores", "Value":23.1},
        {"Identifier":"/intelcpu/0/temperature/0", "SensorType":"Temperature", "Name":"CPU Core #1", "Value":67.5},
        {"Identifier":"/intelcpu/0/temperature/1", "SensorType":"Temperature", "Name":"CPU Core #2", "Value":63.0},
        {"Identifier":"/nvidiagpu/0/power/0", "SensorType":"Power", "Name":"GPU Package", "Value":140},
        {"Identifier":"/nvme/0/temperature/0", "SensorType":"Temperature", "Name":"CPU Core #99", "Value":78},
        {"Identifier":"/intelcpu/0/temperature/3", "SensorType":"Temperature", "Name":"Distance to TjMax Core #3", "Value":42},
        {"Identifier":"/intelcpu/0/power/2", "SensorType":"Power", "Name":"CPU", "Value":0},
    ]
    assert parser(rows) == {"power":38.5, "coreTemps":[{"name":"CPU Core #1","value":67.5}, {"name":"CPU Core #2","value":63.0}]}
    assert parser([{"Identifier":"/nvidiagpu/0/power/0", "SensorType":"Power", "Name":"CPU Package", "Value":99}]) == {"power":None,"coreTemps":[]}
    assert parser(None) == {"power":None,"coreTemps":[]}

def test_015_keeps_two_python_modules_and_rules_untouched():
    assert sorted(p.name for p in ROOT.glob("*.py")) == ["main.py"]
    text = (ROOT / "core" / "monitoring" / "telemetry.py").read_text(encoding="utf-8")
    assert '"cpuPackagePower": None, "cpuCoreTemps": []' in text
    assert 'self._hardware.get("power")' in text
    assert 'self._hardware.get("coreTemps", [])' in text
    assert 'self._cpu_sensor_time <= 20.0' not in text or 'now - self._cpu_sensor_time <= 20.0' in text
    assert (ROOT / "Reglas para crear Versiones nuevas.txt").exists()


def test_015_windows_wmi_cpu_power_and_core_thermometers_are_real_and_labeled():
    import json
    import re
    import subprocess
    from types import SimpleNamespace
    tree = ast.parse((ROOT / "core" / "monitoring" / "telemetry.py").read_text(encoding="utf-8"))
    fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "query_windows_hardware")
    parse_cpu = _telemetry_helpers("positive_number", "parse_cpu_sensors")[1]
    positive, extra = _telemetry_helpers("positive_number", "parse_cpu_extra_sensors")
    parse_cpu.__globals__.update(positive_number=positive, re=re, statistics=__import__('statistics'))
    extra.__globals__.update(positive_number=positive, re=re)
    raw = {"sensors": [
        {"Identifier":"/intelcpu/0/temperature/0", "Name":"CPU Package", "SensorType":"Temperature", "Value":69},
        {"Identifier":"/intelcpu/0/temperature/1", "Name":"CPU Core #1", "SensorType":"Temperature", "Value":71},
        {"Identifier":"/intelcpu/0/power/0", "Name":"CPU Package", "SensorType":"Power", "Value":38.1},
        {"Identifier":"/nvidiagpu/0/power/0", "Name":"GPU Package", "SensorType":"Power", "Value":120},
        ],"disk":None,"baseMHz":2800}
    def fake_run(*args, **kw):
        assert "'Temperature','Clock','Power'" in args[0][-1]
        return SimpleNamespace(returncode=0,stdout=json.dumps(raw))
    ns={"os":SimpleNamespace(name="nt"),"shutil":SimpleNamespace(which=lambda _:"powershell.exe"),
        "subprocess":SimpleNamespace(run=fake_run,CREATE_NO_WINDOW=0,TimeoutExpired=subprocess.TimeoutExpired),
        "json":json,"parse_cpu_sensors":parse_cpu,"parse_cpu_extra_sensors":extra,
        "disk_display_name":_telemetry_helpers("disk_display_name")[0],"positive_number":positive}
    exec(compile(ast.Module(body=[fn],type_ignores=[]),"telemetry.py","exec"),ns)
    value=ns["query_windows_hardware"]("C:",False)
    assert value["temp"]==69
    assert value["power"]==38.1
    assert value["coreTemps"]==[{"name":"CPU Core #1","value":71.0}]
    assert "WMI" in value["detailSource"]

def test_015_cpu_additional_readings_are_expirable_and_source_is_included():
    src=(ROOT/"core"/"monitoring"/"telemetry.py").read_text(encoding="utf-8")
    assert '"cpuPackagePower": None, "cpuCoreTemps": []' in src
    assert '"cpuDetailSource": "N/A"' in src
    assert 'metrics["cpuPackagePower"] = self._hardware.get("power")' in src
    assert 'metrics["cpuCoreTemps"] = self._hardware.get("coreTemps", [])' in src
    assert 'metrics["cpuDetailSource"] = self._hardware.get("detailSource", "N/A")' in src
    assert 'if now - self._cpu_sensor_time <= 12.0' in src


# REBUILD 016 — Tweaks Windows 11: pruebas con Registro simulado, sin tocar el SO.
def _fake_tweaks(monkeypatch):
    import importlib.util
    import sys
    import types

    class FakeSignal:
        def connect(self, callback):
            self.callback = callback
        def emit(self, *args):
            if hasattr(self, "callback"):
                self.callback(*args)

    class FakeTimer:
        def __init__(self, *args):
            self.timeout = FakeSignal()
        def setInterval(self, value):
            self.interval = value
        def start(self):
            self.active = True
        def stop(self):
            self.active = False

    class FakeQObject:
        def __init__(self, *args, **kwargs):
            pass

    qt_core = types.ModuleType("PySide6.QtCore")
    qt_core.QObject = FakeQObject
    qt_core.Signal = lambda: FakeSignal()
    qt_core.Slot = lambda *args, **kwargs: lambda fn: fn
    qt_core.Property = lambda *args, **kwargs: lambda fn: property(fn)
    qt_core.QTimer = FakeTimer
    qt_root = types.ModuleType("PySide6")
    monkeypatch.setitem(sys.modules, "PySide6", qt_root)
    monkeypatch.setitem(sys.modules, "PySide6.QtCore", qt_core)

    registry = types.ModuleType("winreg")
    registry.HKEY_CURRENT_USER = 1
    registry.KEY_READ = 1
    registry.KEY_SET_VALUE = 2
    registry.REG_DWORD = 4
    registry.REG_SZ = 1
    registry.values = {}
    registry.writes = []

    class Key:
        def __init__(self, path):
            self.path = path
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return None

    registry.OpenKey = lambda root, path, reserved=0, access=0: Key(path)
    registry.CreateKeyEx = lambda root, path, reserved=0, access=0: Key(path)
    def query(key, name):
        try:
            return registry.values[key.path, name]
        except KeyError:
            raise FileNotFoundError(name)
    def set_value(key, name, reserved, value_type, value):
        registry.writes.append((key.path, name, value))
        registry.values[key.path, name] = (value, value_type)
    def delete_value(key, name):
        registry.values.pop((key.path, name))
    registry.QueryValueEx = query
    registry.SetValueEx = set_value
    registry.DeleteValue = delete_value
    monkeypatch.setitem(sys.modules, "winreg", registry)

    module_spec = importlib.util.spec_from_file_location("test_corepulse_tweaks_v016", ROOT / "core" / "tweaks" / "tweaks.py")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    monkeypatch.setattr(module, "_is_windows_11", lambda: True)
    return module, registry


def _finish_tweak_refresh(manager):
    """Solo pruebas: drena la consulta asíncrona antes de otra operación."""
    if manager._future is not None:
        manager._future.result(timeout=5)
        manager._finish_if_ready()


def test_016_tweaks_all_low_risk_hkcu_dword_and_no_presets(monkeypatch):
    module, _ = _fake_tweaks(monkeypatch)
    assert len(module._OPTIONS) == 78
    assert len({x["id"] for x in module._OPTIONS}) == 78
    assert len({x["category"] for x in module._OPTIONS}) == 12
    assert all(x["path"].lower().startswith("software\\") for x in module._OPTIONS if x["enabledByPolicy"])
    code = (ROOT / "core" / "tweaks" / "tweaks.py").read_text(encoding="utf-8")
    for forbidden in ("HKEY_LOCAL_MACHINE", "powershell.exe", "taskkill", "bcdedit", "Set-ExecutionPolicy", "shutdown /", "reg delete"):
        assert forbidden not in code
    assert '"schema": 1' in code
    assert 'os.replace(temp, path)' in code


def test_016_apply_preserves_original_and_reverts_exactly(monkeypatch, tmp_path):
    module, registry = _fake_tweaks(monkeypatch)
    spec = module._BY_ID["extensions"]
    key = (spec["path"], spec["name"])
    registry.values[key] = (1, registry.REG_DWORD)
    ctrl = module.TweaksManager(backup=tmp_path / "prefs.json")
    # Las lecturas solo se fuerzan en pruebas; el getter de QML no bloquea.
    ctrl._cached_options = ctrl._collect_options()
    before = [x for x in ctrl.options if x["id"] == "extensions"][0]
    assert before["status"] == "Sin aplicar" and not before["canRestore"]
    assert "aplicado" in ctrl.applyTweak("extensions").lower()
    assert registry.values[key] == (0, registry.REG_DWORD)
    assert module._load_backup(ctrl._backup)["originales"]["extensions"] == {"present": True, "value": 1}
    assert ctrl._collect_options()[0]["canRestore"] is True
    _finish_tweak_refresh(ctrl)
    assert "restaurado" in ctrl.restoreTweak("extensions").lower()
    assert registry.values[key] == (1, registry.REG_DWORD)
    assert not module._load_backup(ctrl._backup)["originales"]


def test_016_missing_key_restores_absence_and_does_not_overwrite_original(monkeypatch, tmp_path):
    module, registry = _fake_tweaks(monkeypatch)
    spec = module._BY_ID["compact"]
    key = (spec["path"], spec["name"])
    ctrl = module.TweaksManager(backup=tmp_path / "prefs.json")
    ctrl.applyTweak("compact")
    _finish_tweak_refresh(ctrl)
    assert module._load_backup(ctrl._backup)["originales"]["compact"] == {"present": False, "value": None}
    assert "ya está activo" in ctrl.applyTweak("compact").lower()
    _finish_tweak_refresh(ctrl)
    ctrl.restoreTweak("compact")
    assert key not in registry.values


def test_016_never_writes_when_backup_fails_or_registry_incompatible(monkeypatch, tmp_path):
    module, registry = _fake_tweaks(monkeypatch)
    spec = module._BY_ID["transparency"]
    key = (spec["path"], spec["name"])
    registry.values[key] = ("no-reg-dword", registry.REG_SZ)
    ctrl = module.TweaksManager(backup=tmp_path / "settings.json")
    assert "no se cambió" in ctrl.applyTweak("transparency").lower()
    assert registry.writes == []
    registry.values[key] = (1, registry.REG_DWORD)
    def fail_save(path, data):
        raise OSError("sin espacio")
    monkeypatch.setattr(module, "_save_backup", fail_save)
    assert "no se pudo" in ctrl.applyTweak("transparency").lower()
    _finish_tweak_refresh(ctrl)
    assert registry.writes == []
    monkeypatch.setattr(module, "_is_windows_11", lambda: False)
    assert "no disponible" in ctrl.applyTweak("transparency").lower()
    assert registry.writes == []


def test_016_corrupt_backup_blocks_operations(monkeypatch, tmp_path):
    module, registry = _fake_tweaks(monkeypatch)
    backup = tmp_path / "settings.json"
    backup.write_text('{"schema":1,"originales":{"extensions":{"present":true,"value":"evil"}}}', encoding="utf-8")
    ctrl = module.TweaksManager(backup=backup)
    assert "no se pudo" in ctrl.applyTweak("extensions").lower()
    assert registry.writes == []
    assert not next(x for x in ctrl.options if x["id"] == "extensions")["available"]


def test_016_tweaks_qml_live_states_confirmation_dark_scroll_and_main_routing():
    qml = (UI / "TweaksPage.qml").read_text(encoding="utf-8")
    main = (UI / "Main.qml").read_text(encoding="utf-8")
    py = (ROOT / "main.py").read_text(encoding="utf-8")
    assert 'window.selectedPage==="tweaks"?tweaksComponent:' in main
    assert 'id:tweaksComponent' in main and 'TweaksPage {' in main
    assert 'context.setContextProperty("tweaks", tweaks)' in py
    assert '"Explorador", "Barra de tareas", "Interfaz", "Privacidad"' in qml
    assert 'tweaks.options.filter(' in qml
    assert 'ListView {' in qml
    assert 'page.pendingAction="apply"' in qml and 'page.pendingAction="restore"' in qml
    assert 'tweaks.applyTweak(page.pendingId)' in qml and 'tweaks.restoreTweak(page.pendingId)' in qml
    assert 'ThinScroll {' in qml and 'target: scroller' in qml
    assert 'no se cambian Defender, Windows Update, servicios ni controladores' in qml
    assert (ROOT / "Reglas para crear Versiones nuevas.txt").exists()


def test_017_category_colors_counter_and_unchanged_tweak_catalog():
    qml = (UI / "TweaksPage.qml").read_text(encoding="utf-8")
    source = (ROOT / "core" / "tweaks" / "tweaks.py").read_text(encoding="utf-8")
    assert 'function groupColor(category)' in qml
    for category, color in (("Explorador", "#27BDF5"), ("Barra de tareas", "#9A8CFF"), ("Interfaz", "#F6B35B")):
        assert f'case "{category}": return "{color}"' in qml
    assert 'tweaks.options.length + " ajustes originales' in qml
    assert 'page.groupColor(optionCard.opt.category)' in qml
    assert source.count("'requiresExplorer':") == 78
    assert 'def applyTweak(self, tweak_id)' in source and 'def restoreTweak(self, tweak_id)' in source

def test_018_catalog_78_categories_and_policy(monkeypatch):
    module, registry = _fake_tweaks(monkeypatch)
    assert len(module._OPTIONS) == 78
    assert len({spec["sourceId"] for spec in module._OPTIONS}) == 78
    assert len({spec["category"] for spec in module._OPTIONS}) == 12
    assert sum(spec["enabledByPolicy"] for spec in module._OPTIONS) == 34
    assert all(spec["ops"][0][0] == "HKCU" and spec["ops"][0][4] == "dword"
               for spec in module._OPTIONS if spec["enabledByPolicy"])
    assert all(not spec["enabledByPolicy"] for spec in module._OPTIONS
               if spec["category"] in ("Seguridad avanzada", "Actualizaciones", "Apps y debloat"))
    controller = module.TweaksManager(backup=__import__("pathlib").Path("/tmp/corepulse_test_tweak_missing.json"))
    assert len(controller.options) == 78


def test_018_blocked_adjustment_never_writes(monkeypatch, tmp_path):
    module, registry = _fake_tweaks(monkeypatch)
    controller = module.TweaksManager(backup=tmp_path / "backup.json")
    # No afirmamos que todos estén bloqueados: el nuevo motor permite los
    # reversibles en Windows 11, pero fuera de Windows falla cerrado.
    for tweak_id in ("disable_defender_stack", "disable_auto_updates", "remove_edge", "disable_hibernation"):
        _finish_tweak_refresh(controller)
        response = controller.applyTweak(tweak_id)
        assert "No se aplicó" in response or "Bloqueado" in response
        _finish_tweak_refresh(controller)
        assert controller.restoreTweak(tweak_id)
    assert registry.writes == []
    assert not (tmp_path / "backup.json").exists()


def test_019_catalog_information_panel_removed_but_feedback_preserved():
    qml = (UI / "TweaksPage.qml").read_text(encoding="utf-8")
    assert "Catálogo histórico de 78 ajustes." not in qml
    assert "id:information" not in qml
    assert "visible:page.feedback!==\"\"" in qml
    assert "text:page.feedback" in qml


def test_020_apply_requires_registry_readback(monkeypatch, tmp_path):
    module, registry = _fake_tweaks(monkeypatch)
    monkeypatch.setattr(module, "_is_windows_11", lambda: True)
    monkeypatch.setattr(module, "_safe_read", lambda spec: (False, None, None))
    monkeypatch.setattr(module, "_write_value", lambda spec, value: None)
    manager = module.TweaksManager(backup=tmp_path / "backup.json")
    result = manager.applyTweak("extensions")
    assert "no confirmado" in result.lower()
    assert "extensions" in module._load_backup(manager._backup)["originales"]


def test_020_restore_keeps_backup_if_not_confirmed(monkeypatch, tmp_path):
    module, registry = _fake_tweaks(monkeypatch)
    monkeypatch.setattr(module, "_is_windows_11", lambda: True)
    backup = tmp_path / "backup.json"
    module._save_backup(backup, {"schema": 1, "originales": {"extensions": {"present": False, "value": None}}})
    monkeypatch.setattr(module, "_restore_value", lambda spec, original: None)
    monkeypatch.setattr(module, "_safe_read", lambda spec: (True, 0, module.winreg.REG_DWORD))
    manager = module.TweaksManager(backup=backup)
    assert "no confirmada" in manager.restoreTweak("extensions").lower()
    assert "extensions" in module._load_backup(backup)["originales"]


def test_v485_engine_catalog_included():
    import ast
    engine = (ROOT / "core" / "tweaks" / "tweaks_engine.py").read_text(encoding="utf8")
    assert "def apply_tweak(" in engine
    assert "def undo_tweak(" in engine
    assert "def detect_tweak(" in engine
    assert "def _save_original_if_needed(" in engine
    assert "disable_defender_stack', 'disable_smartscreen', 'disable_uac'" in engine
    ast.parse(engine)

def test_v485_bridge_not_fake():
    bridge=(ROOT / "core" / "tweaks" / "tweaks.py").read_text(encoding="utf8")
    assert "legacy_engine.preflight_tweak" in bridge
    assert "legacy_engine.detect_tweak" in bridge
    assert "legacy_engine.apply_tweak" in bridge
    assert "legacy_engine.undo_tweak" in bridge


def test_cleanup_exposes_real_operations_and_safe_qml_routing():
    source = (ROOT / "core" / "maintenance" / "cleanup.py").read_text(encoding="utf-8")
    ui = (UI / "CleanupPage.qml").read_text(encoding="utf-8")
    main = (UI / "Main.qml").read_text(encoding="utf-8")
    assert "MemoryPurgeStandbyList" in source and "fn(80," in source
    assert "MIN_AGE_SECONDS = 24 * 3600" in source
    assert "path.is_symlink()" in source and "path.unlink()" in source
    assert "confirmDialog.open()" in ui and "onConfirmed: cleanup.clean()" in ui
    assert 'window.selectedPage==="cleanup"?cleanupComponent:' in main
    assert 'context.setContextProperty("cleanup", cleanup)' in (ROOT / "main.py").read_text(encoding="utf-8")


def test_temp_selection_skips_recent_and_symlinked_files(tmp_path):
    import time, os
    source = (ROOT / "core" / "maintenance" / "cleanup.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    definitions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in ("scan_temps", "clean_temps")]
    scope = {"os": os, "Path": Path, "time": time, "MAX_FILES": 120000, "MIN_AGE_SECONDS": 86400}
    exec(compile(ast.Module(body=definitions, type_ignores=[]), "cleanup.py", "exec"), scope)
    old = tmp_path / "old.tmp"; old.write_bytes(b"old-data")
    recent = tmp_path / "recent.tmp"; recent.write_bytes(b"recent")
    historical = time.time() - 86400 * 2
    os.utime(old, (historical, historical))
    rows = scope["scan_temps"](tmp_path)
    assert [r[0] for r in rows] == [old]
    result = scope["clean_temps"](tmp_path)
    assert result["removed"] == 1 and result["bytes"] == len(b"old-data")
    assert not old.exists() and recent.exists()


def test_cleanup_qml_layout_objects_no_separator_token():
    import re
    qml = (UI / "CleanupPage.qml").read_text(encoding="utf-8")
    assert not re.search(r"\}\s*;\s*(?:Text|Rectangle|RowLayout|ColumnLayout|Item|Button)\s*\{", qml)
    assert "Text { text: info.size" in qml


def test_rebuild_024_ram_privilege_is_temporarily_enabled_and_restored():
    src = (ROOT / "core" / "maintenance" / "cleanup.py").read_text(encoding="utf-8")
    assert "SeProfileSingleProcessPrivilege" in src
    assert "ERROR_NOT_ALL_ASSIGNED = 1300" in src
    assert "with standby_privilege():" in src
    assert "ctypes.byref(previous), 0, None, None" in src
    assert "finally:" in src

def test_rebuild_024_cleanup_controls_are_themed():
    qml = (UI / "CleanupPage.qml").read_text(encoding="utf-8")
    assert "component ActionButton: AbstractButton" in qml
    assert 'text: "Limpiar standby"' in qml
    assert "component DarkDialog: Popup" in qml
    assert 'actionText: "Eliminar archivos"' in qml
    assert not re.search(r'(?<!Action)\bButton\s*\{\s*text:', qml)


def test_rebuild_026_deep_and_standby_actions():
    src = (ROOT / "core" / "maintenance" / "cleanup.py").read_text(encoding="utf8")
    qml = (UI / "CleanupPage.qml").read_text(encoding="utf8")
    assert "def optimize_ram_deep()" in src
    assert "def cleanRamDeep(self):" in src
    assert 'text: "Limpiar standby"' in qml
    assert 'text: "Limpiar RAM completa"' in qml
    assert "onConfirmed: cleanup.cleanRamDeep()" in qml
    assert "onClicked: cleanup.cleanRam()" in qml
    assert "deepConfirm.open()" in qml
    assert "def windows_privilege(name):" in src



def test_rebuild_027_module_organization():
    assert sorted(p.name for p in ROOT.glob("*.py")) == ["main.py"]
    expected = {
        "core/monitoring/telemetry.py",
        "core/tweaks/tweaks.py",
        "core/tweaks/tweaks_engine.py",
        "core/maintenance/cleanup.py",
    }
    for path in expected:
        assert (ROOT / path).is_file()
        assert not (ROOT / Path(path).name).exists()
    main = (ROOT / "main.py").read_text(encoding="utf8")
    for module in (
        "core.monitoring.telemetry",
        "core.tweaks.tweaks",
        "core.maintenance.cleanup",
    ):
        assert f"from {module} import" in main
    bridge = (ROOT / "core/tweaks/tweaks.py").read_text(encoding="utf8")
    assert 'Path(__file__).with_name("tweaks_engine.py")' in bridge
    engine = (ROOT / "core/tweaks/tweaks_engine.py").read_text(encoding="utf8")
    assert "Path(__file__).resolve().parents[2]" in engine


def test_rebuild_028_hover_dialogs_and_verified_success():
    qml = (UI / "CleanupPage.qml").read_text(encoding="utf-8")
    source = (ROOT / "core" / "maintenance" / "cleanup.py").read_text(encoding="utf-8")
    assert "component ActionButton: AbstractButton" in qml
    assert "control.hovered" in qml
    assert "Overlay.modal: Rectangle" in qml
    assert "parent: Overlay.overlay" in qml
    assert 'text: "RAM limpiada correctamente"' in qml
    assert "result.resultSuccess" in qml
    assert "resultSequence" in source and "resultSuccess" in source
    assert "partially_completed = 0 < result['completed'] < result['attempted']" in source
    assert "succeeded = True" in source



def test_rebuild_029_ram_meter_snapshot_never_invents_values():
    """Un solo snapshot alimenta los valores usados y el porcentaje."""
    from types import SimpleNamespace
    source = (ROOT / "core/maintenance/cleanup.py").read_text(encoding="utf-8")
    func = next(n for n in ast.parse(source).body
                if isinstance(n, ast.FunctionDef) and n.name == "ram_usage_snapshot")
    namespace = {"psutil": SimpleNamespace(virtual_memory=lambda: SimpleNamespace(total=16 * 2**30, available=5 * 2**30))}
    exec(compile(ast.Module(body=[func], type_ignores=[]), "cleanup.py", "exec"), namespace)
    snapshot = namespace["ram_usage_snapshot"]()
    assert snapshot == {"total": 16 * 2**30, "available": 5 * 2**30,
                        "used": 11 * 2**30, "percent": 68.8}
    for total, available in ((0, 0), (16, -1), (8, 10)):
        namespace["psutil"].virtual_memory = lambda t=total, a=available: SimpleNamespace(total=t, available=a)
        import pytest
        with pytest.raises(ValueError, match="no válida"):
            namespace["ram_usage_snapshot"]()


def test_rebuild_029_ram_meter_updates_while_future_is_running_and_stops_on_result():
    """Contrato del medidor aun sin Qt/Windows, sin ejecutar purga real."""
    from types import SimpleNamespace
    source = (ROOT / "core/maintenance/cleanup.py").read_text(encoding="utf8")
    tree = ast.parse(source)
    nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))
             and n.name in ("human_bytes", "ram_usage_snapshot", "CleanupManager")]
    class StubSignal:
        def __init__(self): self.count = 0
        def connect(self, fn): self.handler = fn
        def emit(self): self.count += 1
    class StubQObject:
        def __init__(self, parent=None): pass
    class StubTimer:
        def __init__(self, parent=None): self.timeout = StubSignal(); self.running = False
        def setInterval(self, interval): self.interval = interval
        def start(self): self.running = True
        def stop(self): self.running = False
    class StubFuture:
        def __init__(self): self.ready = False; self.output = None
        def done(self): return self.ready
        def result(self):
            if isinstance(self.output, Exception): raise self.output
            return self.output
    class StubPool:
        def __init__(self, **kw): self.future = StubFuture()
        def submit(self, fn): return self.future
        def shutdown(self, **kw): pass
    samples = iter([(16, 6), (16, 9), (16, 10), (16, 10), (16, 10)])
    def memory():
        total, available = next(samples)
        return SimpleNamespace(total=total * 2**30, available=available * 2**30)
    clock = SimpleNamespace(time=1.0)
    namespace = dict(QObject=StubQObject, QTimer=StubTimer, Signal=StubSignal,
                     Slot=lambda: lambda fn: fn,
                     Property=lambda *a, **kw: lambda fn: property(fn),
                     ThreadPoolExecutor=StubPool, time=SimpleNamespace(monotonic=lambda: clock.time),
                     psutil=SimpleNamespace(virtual_memory=memory))
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "cleanup.py", "exec"), namespace)
    manager = namespace["CleanupManager"]()
    manager.cleanRamDeep()
    assert manager.data["busy"] and manager.data["ramMeterActive"]
    assert manager.data["ramMeterPercent"] == 62.5
    assert manager.data["ramMeterStart"] == "10.00 GB"
    assert manager._timer.running
    manager._check()  # future todavía trabajando, no inventar una muestra más
    assert manager.data["ramMeterSamples"] == 1
    clock.time += 0.35
    manager._check()
    assert manager.data["ramMeterPercent"] == 43.8
    assert manager.data["ramMeterUsed"] == "7.00 GB"
    assert manager.data["ramMeterDelta"] == "+3.00 GB"
    assert manager.data["ramMeterSamples"] == 2
    manager._pool.future.ready = True
    manager._pool.future.output = ("ram_deep", dict(before=6 * 2**30, after=10 * 2**30,
        delta=4 * 2**30, completed=1, attempted=6, trimmed=2, skipped=3,
        results={"working_sets": {"ok": True}}))
    manager._check()
    assert manager.data["ramMeterPercent"] == 37.5
    assert manager.data["ramMeterSamples"] == 3
    assert not manager.data["busy"] and not manager.data["ramMeterActive"]
    assert manager.data["resultSequence"] == 1 and manager.data["resultPartial"] and not manager.data["resultSuccess"]
    assert not manager._timer.running
    # Windows puede rechazar la ejecución: mantener el tipo y no mostrar éxito.
    manager._pool.future = StubFuture()
    manager.cleanRamDeep()
    manager._pool.future.ready = True
    manager._pool.future.output = PermissionError("NTSTATUS 0xC0000061")
    manager._check()
    assert manager.data["resultSequence"] == 2
    assert manager.data["resultKind"] == "ram_deep"
    assert not manager.data["resultSuccess"]
    assert "NTSTATUS 0xC0000061" in manager.data["status"]
    assert not manager.data["ramMeterActive"]


def test_rebuild_029_progress_modal_is_real_and_success_is_result_gated():
    qml = (UI / "CleanupPage.qml").read_text(encoding="utf8")
    python = (ROOT / "core/maintenance/cleanup.py").read_text(encoding="utf8")
    assert 'id: ramProgress' in qml and 'id: gaugeCanvas' in qml
    assert 'result.busy && result.ramMeterActive' in qml
    assert 'if (!result.busy && ramProgress.opened)' in qml
    assert 'Qt.callLater(function() { ramSuccess.open() })' in qml
    assert 'if (result.resultSuccess)' in qml
    assert 'id: ramFailure' in qml
    assert 'property int seenResultSequence: info.resultSequence || 0' in qml
    assert 'text: "RAM limpiada correctamente"' in qml
    assert 'ramProgress.animatedPercent' in qml
    assert 'Number(info.ramMeterPercent).toFixed(1)' in qml
    assert 'Math.random' not in qml
    assert 'now - self._meter_last_read < 0.28' in python
    assert 'self._sample_ram_meter(force=True)' in python
    assert 'kind="ram_deep"' in python and 'kind="ram"' in python
    assert 'closePolicy: Popup.NoAutoClose' in qml


def test_rebuild_030_cleanup_compact_by_default_and_results_accessible():
    qml = (UI / "CleanupPage.qml").read_text(encoding="utf-8")
    backend = (ROOT / "core/maintenance/cleanup.py").read_text(encoding="utf-8")
    # No dejar la franja de estado permanente ni los seis textos en la tarjeta RAM.
    assert '"ESTADO DE LIMPIEZA"' not in qml
    assert 'visible: info.busy || tempError' in qml
    assert 'text: "Standby o limpieza completa"' in qml
    assert 'property bool ramDetailsOpen: false' in qml
    assert 'visible: page.ramDetailsOpen && page.hasRamResult' in qml
    assert '"lastRamKind": ""' in backend
    assert 'self._data["lastRamKind"] = "ram"' in backend
    assert 'self._data["lastRamKind"] = "ram_deep"' in backend
    # Conservar controles y monitor de limpieza en tiempo real sin telemetría inventada.
    assert 'onClicked: cleanup.cleanRam()' in qml
    assert 'onConfirmed: cleanup.cleanRamDeep()' in qml
    assert 'id: ramProgress' in qml and 'Number(info.ramMeterPercent).toFixed(1)' in qml
    assert 'text: "RAM limpiada correctamente"' in qml
    assert 'id: ramFailure' in qml
    assert '"No se pudo completar:"' in qml


# REBUILD 031: caché de Windows, Papelera y DNS, con pruebas reales de
# borrado sobre datos temporales simulados (sin tocar Windows del usuario).
def _cleanup_functions(*names):
    import os
    import time
    from pathlib import Path
    src = (ROOT / "core/maintenance/cleanup.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    ns = {"Path": Path, "os": os, "time": time, "MAX_FILES": 120000}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), 'cleanup.py', 'exec'), ns)
    return ns


def test_rebuild_031_cache_is_real_and_does_not_delete_outside_roots(tmp_path):
    ns = _cleanup_functions('scan_user_cache', 'clean_user_cache')
    cache = tmp_path / 'D3DSCache'; cache.mkdir()
    outside = tmp_path / 'Documents'; outside.mkdir()
    wanted = cache / 'shader.bin'; wanted.write_bytes(b'legitimately disposable cache')
    personal = outside / 'important.txt'; personal.write_bytes(b'private')
    symlink = cache / 'dangerous.bin'
    try:
        symlink.symlink_to(personal)
    except (OSError, NotImplementedError):
        pass
    entries = ns['scan_user_cache']([(cache, None)])
    assert [r[0] for r in entries] == [wanted]
    result = ns['clean_user_cache']([(cache, None)])
    assert result['removed'] == 1 and result['bytes'] == len(b'legitimately disposable cache')
    assert result['remaining'] == 0 and result['remaining_bytes'] == 0
    assert not wanted.exists() and personal.read_bytes() == b'private'


def test_rebuild_031_cache_prefix_and_modified_file_not_removed(tmp_path):
    ns = _cleanup_functions('scan_user_cache', 'clean_user_cache')
    root = tmp_path / 'Explorer'; root.mkdir()
    wanted = root / 'thumbcache_1920.db'; wanted.write_bytes(b'a')
    protected = root / 'icons.db'; protected.write_bytes(b'b')
    assert len(ns['scan_user_cache']([(root, 'thumbcache_')])) == 1
    original_scan = ns['scan_user_cache']
    def changed_during_scan(locations):
        result = original_scan(locations)
        wanted.write_bytes(b'changed during deletion')
        return result
    ns['scan_user_cache'] = changed_during_scan
    result = ns['clean_user_cache']([(root, 'thumbcache_')])
    assert result['removed'] == 0 and result['skipped'] == 1
    assert wanted.read_bytes() == b'changed during deletion' and protected.exists()


def test_rebuild_031_dns_flush_reports_windows_confirmation_or_error():
    import types
    ns = _cleanup_functions('flush_dns_cache')
    ns['os'] = types.SimpleNamespace(name='nt')
    commands = []
    def run_ok(cmd, **kw):
        commands.append((cmd, kw))
        return types.SimpleNamespace(returncode=0, stdout='success', stderr='')
    ns['subprocess'] = types.SimpleNamespace(run=run_ok, CREATE_NO_WINDOW=134217728)
    assert ns['flush_dns_cache']() == {'accepted': True}
    assert commands[0][0] == ['ipconfig', '/flushdns']
    assert commands[0][1]['timeout'] == 20
    ns['subprocess'].run = lambda *a, **kw: types.SimpleNamespace(returncode=1, stdout='', stderr='Access denied')
    import pytest
    with pytest.raises(RuntimeError, match='Access denied'):
        ns['flush_dns_cache']()
    ns['os'].name = 'posix'
    with pytest.raises(OSError, match='Windows'):
        ns['flush_dns_cache']()


def test_rebuild_031_recycle_requires_real_shell_success():
    import types, ctypes
    ns = _cleanup_functions('empty_recycle_bin')
    before = {'count': 7, 'bytes': 3000}
    after = {'count': 1, 'bytes': 200}
    readings = iter((before, after))
    ns['recycle_bin_info'] = lambda: next(readings)
    flags_seen = []
    def shell_empty(_window, _drive, flags):
        flags_seen.append(flags)
        return 0
    ns['ctypes'] = types.SimpleNamespace(WinDLL=lambda *args, **kw: types.SimpleNamespace(SHEmptyRecycleBinW=shell_empty),
                                         c_uint32=ctypes.c_uint32, c_long=ctypes.c_long)
    result = ns['empty_recycle_bin']()
    assert result['emptied'] == 6 and result['after']['count'] == 1
    assert flags_seen == [7]
    ns['recycle_bin_info'] = lambda: {'count': 0, 'bytes': 0}
    result = ns['empty_recycle_bin']()
    assert result['emptied'] == 0 and len(flags_seen) == 1


def test_rebuild_031_cleaning_cards_and_confirmations_are_connected():
    source = (ROOT / 'core/maintenance/cleanup.py').read_text(encoding='utf-8')
    view = (UI / 'CleanupPage.qml').read_text(encoding='utf-8')
    for slot in ('analyzeCache', 'cleanCache', 'analyzeRecycleBin', 'emptyRecycleBin', 'flushDns'):
        assert f'def {slot}(self)' in source
        assert f'cleanup.{slot}()' in view
    for name in ('cacheConfirm', 'recycleConfirm'):
        assert f'id: {name}' in view and f'{name}.open()' in view
    assert 'Layout.columnSpan: page.width < 850 ? 1 : 2' in view
    assert 'text: "Limpiar caché"' in view and 'text: "Caché DNS"' in view
    assert 'text: "Papelera de reciclaje"' in view
    assert 'user_cache_locations' in source and 'thumbcache_' in source
    assert 'SHQueryRecycleBinW' in source and 'SHEmptyRecycleBinW' in source
    assert '"ipconfig", "/flushdns"' in source
    assert 'windows_tweaks_state.json' not in source


# REBUILD 032: corregir las causas de los avisos QML, no esconder el log.
def test_rebuild_032_grid_widths_cannot_depend_on_own_grid():
    source=(UI/'Overview.qml').read_text(encoding='utf-8')
    assert 'primary.width*' not in source
    assert '(page.width - 14) * .70' in source
    assert '(page.width - 14) * .30' in source
    assert 'readonly property bool horizontal: width >= 810' in source
    assert 'Layout.preferredHeight: page.horizontal ? page.panelsHeight : 385' in source
    assert 'Layout.preferredHeight:page.horizontal ? page.panelsHeight : 300' in source


def test_rebuild_032_null_guards_protect_telemetry_and_cleanup():
    overview=(UI/'Overview.qml').read_text(encoding='utf-8')
    detail=(UI/'ComponentDetail.qml').read_text(encoding='utf-8')
    main=(UI/'Main.qml').read_text(encoding='utf-8')
    cleaning=(UI/'CleanupPage.qml').read_text(encoding='utf-8')
    assert 'telemetry && telemetry.metrics ? telemetry.metrics : ({' in overview and 'health: "N/A"' in overview
    assert 'telemetry && telemetry.metrics ? telemetry.metrics : ({})' in detail
    assert 'text:telemetry && telemetry.metrics ? telemetry.metrics.computer : "N/A"' in main
    assert 'telemetry && telemetry.metrics ? (telemetry.metrics.readings || []) : []' in main
    assert 'telemetry && telemetry.metrics ? (telemetry.metrics.coverage || "N/A") : "N/A"' in main
    assert 'cleanup && cleanup.data ? cleanup.data' in cleaning
    assert 'if (!cleanup || !cleanup.data) return' in cleaning
    assert 'property int seenResultSequence: info.resultSequence || 0' in cleaning
    assert 'readonly property var info: cleanup.data' not in cleaning
    assert 'property int seenResultSequence: cleanup.data.resultSequence' not in cleaning


def test_rebuild_032_scrollbars_are_custom_but_scrollable_and_reusable():
    bar=(UI/'ThinScroll.qml').read_text(encoding='utf-8')
    assert 'required property Flickable target' in bar
    assert 'rail.target.contentY =' in bar
    assert 'target.contentHeight > target.height + 1' in bar
    assert 'hoverEnabled: true' in bar
    assert 'background:' not in bar and 'ScrollBar' not in bar.replace('ScrollBar nativo','')
    for name in ('Main.qml','TweaksPage.qml','ComponentDetail.qml','CleanupPage.qml'):
        code=(UI/name).read_text(encoding='utf-8')
        assert 'ThinScroll {' in code
        assert 'ScrollBar.vertical:' not in code
        assert 'ScrollView {' not in code
    cleaning=(UI/'CleanupPage.qml').read_text(encoding='utf-8')
    assert 'contentHeight: cleanupContents.implicitHeight + 12' in cleaning
    assert 'id: cleanupScroll' in cleaning


def test_rebuild_032_unmodified_windows_engines_and_coverage():
    assert 'CorePulse — Rebuild 107' in (UI/'Main.qml').read_text(encoding='utf-8')
    assert (ROOT/'Reglas para crear Versiones nuevas.txt').is_file()
    assert 'REBUILD 032' in (ROOT/'versiones/HISTORIAL.md').read_text(encoding='utf-8')


# REBUILD 033: mantener el medidor real y alinear únicamente su tema al de CorePulse.
def test_rebuild_033_ram_monitor_uses_corepulse_palette_not_sky_blue():
    view = (UI / "CleanupPage.qml").read_text(encoding="utf-8")
    modal = view.split("    Popup {\n        id: ramProgress", 1)[1].split("    Popup {\n        id: ramFailure", 1)[0]
    assert 'readonly property color surface: themeManager.palette.panel' in view
    assert 'readonly property color ramModalAccent: "#4EDDC8"' in view
    assert 'background: ModalSurface {}' in modal
    assert 'color: page.surface' in view.split('component ModalSurface: Rectangle {', 1)[1].split('}', 1)[0]
    assert 'border.color: page.edge' in view.split('component ModalSurface: Rectangle {', 1)[1].split('}', 1)[0]
    assert 'ctx.strokeStyle = String(page.ramModalAccent)' in modal
    assert 'color: page.ramModalAccent' in modal
    assert 'ink: page.ramModalAccent' in modal
    assert not any(hue in modal for hue in ("#68C9F5", "#76D8ED", "#77C6FF"))

def test_rebuild_033_no_changes_to_ram_data_or_interaction():
    view = (UI / "CleanupPage.qml").read_text(encoding="utf-8")
    main = (UI / "Main.qml").read_text(encoding="utf-8")
    assert 'title:"CorePulse — Rebuild 107"' in main
    assert 'REBUILD 033' in (ROOT / "versiones" / "HISTORIAL.md").read_text(encoding="utf-8")
    for part in (
        'ramProgress.animatedPercent',
        'info.ramMeterPercent',
        'info.ramMeterStart',
        'info.ramMeterUsed',
        'info.ramMeterDelta',
        'ramProgress.open()',
        'ramSuccess.open()',
        'ramFailure.open()',
    ):
        assert part in view


# REBUILD 034: a Flickable reparents visual children to its contentItem.
# The thumb is an overlay sibling of the Flickable, NOT its content child.
def test_rebuild_034_scroll_overlay_never_anchors_across_flickable_content_item():
    for file, flick_id in (
        ("TweaksPage.qml", "scroller"),
        ("ComponentDetail.qml", "scroller"),
        ("Main.qml", "readingsScroll"),
    ):
        source = (UI / file).read_text(encoding="utf-8")
        id_match = re.search(r"\b(?:Flickable|ListView)\s*\{\s*id\s*:\s*" + flick_id + r"\b", source)
        assert id_match, f"Flickable missing: {file}"
        # Walk QML curly braces from Flickable's opening brace, accounting for
        # string literals, to find its matching closing brace.
        opening = source.index("{", id_match.start())
        depth, quoted, escaping = 0, None, False
        closing = None
        for position in range(opening, len(source)):
            ch = source[position]
            if quoted is not None:
                if escaping:
                    escaping = False
                elif ch == "\\":
                    escaping = True
                elif ch == quoted:
                    quoted = None
                continue
            if ch in (chr(34), chr(39)):
                quoted = ch
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    closing = position
                    break
        assert closing is not None
        # The scrollbar must start AFTER the Flickable block closes, inside
        # their shared wrapper. The old code put it inside the Flickable.
        thumb_start = source.index("ThinScroll {", id_match.end())
        assert opening < closing < thumb_start, f"Invalid scroll-parent hierarchy: {file}"
        between = source[closing + 1: thumb_start]
        assert between.strip() == "", f"Unexpected component between scroll and overlay: {file}"
        thumb = source[thumb_start: source.index("}", thumb_start)]
        assert f"target: {flick_id}" in thumb
        for side in ("top", "bottom", "right"):
            assert f"anchors.{side}: parent.{side}" in thumb
        assert f"parent: {flick_id}" not in thumb
        assert "anchors.fill: parent" in source[opening:closing]

def test_rebuild_034_cleanup_scrollbar_has_valid_sibling_anchors():
    source = (UI / "CleanupPage.qml").read_text(encoding="utf-8")
    thumb = source.split("ThinScroll {", 1)[1].split("}", 1)[0]
    assert "target: cleanupScroll" in thumb
    # Unlike the old three pages, CleanupPage's Flickable and ThinScroll
    # were already declared as siblings under the page root.
    for side in ("top", "bottom", "right"):
        assert f"anchors.{side}: cleanupScroll.{side}" in thumb
    assert "parent: cleanupScroll" not in thumb


# REBUILD 034: All modal rectangles, not merely the progress gauge, must share
# the card styling. Accent tones belong to progress/check/labels, not frames.
def test_rebuild_034_all_cleanup_dialogs_use_same_corepulse_card_skin():
    view = (UI / 'CleanupPage.qml').read_text(encoding='utf-8')
    skin = view.split('component ModalSurface: Rectangle {', 1)[1].split('}', 1)[0]
    assert 'color: page.surface' in skin
    assert 'border.color: page.edge' in skin
    assert 'radius: 19' in skin
    for component in ('component DarkDialog: Popup {',
                      'id: ramProgress', 'id: ramFailure', 'id: ramSuccess'):
        block = view.split(component, 1)[1]
        assert 'Overlay.modal: Rectangle { color: page.modalShade }' in block
        assert 'background: ModalSurface {}' in block
    # The green check is intentionally preserved as an independent success signal.
    assert 'text: "RAM limpiada correctamente"' in view
    assert 'border.color: "#43D68B"' in view
    assert 'color: "#19242A"' not in view
    assert 'color: "#1A222F"' not in view
    assert 'color: "#181F2D"' not in view


def test_rebuild_034_modal_hover_states_are_not_native_or_white():
    view = (UI / 'CleanupPage.qml').read_text(encoding='utf-8')
    button = view.split('component ActionButton: AbstractButton {', 1)[1].split('Flickable {', 1)[0]
    assert 'hoverEnabled: true' in button
    assert 'control.hovered' in button
    # REBUILD 082: la rama de acción va primero; el estilo secundario oscuro se conserva.
    assert '(!control.enabled ? "#242631"' in button and 'themeManager.palette.actionMuted' in button
    assert 'background: Rectangle {' in button
    assert '#FFFFFF' not in button and '"white"' not in button


# REBUILD 035: arranque automático de dependencias sin usar pip del usuario.
def _load_launcher_for_tests():
    import importlib.util
    import sys
    spec = importlib.util.spec_from_file_location("corepulse_launcher_rebuild035_test", ROOT / "main.py")
    launcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launcher)
    return launcher


def test_rebuild_035_bootstrap_isolated_outside_project_and_cwd_independent(tmp_path, monkeypatch):
    launcher = _load_launcher_for_tests()
    req = tmp_path / "project" / "requirements.txt"
    req.parent.mkdir()
    req.write_text("PySide6>=6.6,<7\npsutil>=5.9,<8\n", encoding="utf-8")
    monkeypatch.setattr(launcher, "REQUIREMENTS", req)
    monkeypatch.setattr(launcher, "PROJECT_DIR", req.parent)
    monkeypatch.setattr(launcher, "RUNTIME_HOME", tmp_path / "external_runtime")
    monkeypatch.chdir(tmp_path)
    first = launcher._runtime_path()
    monkeypatch.chdir(req.parent)
    assert launcher._runtime_path() == first
    assert first.is_relative_to(tmp_path / "external_runtime")
    assert not first.is_relative_to(req.parent)
    req.write_text("PySide6>=6.8,<7\n", encoding="utf-8")
    assert launcher._runtime_path() != first  # nuevo manifiesto -> entorno nuevo


def test_rebuild_035_first_launch_installs_and_next_launch_reuses_runtime(tmp_path, monkeypatch):
    launcher = _load_launcher_for_tests()
    source = tmp_path / "project"
    source.mkdir()
    req = source / "requirements.txt"
    req.write_text("PySide6>=6.6,<7\n", encoding="utf-8")
    monkeypatch.setattr(launcher, "REQUIREMENTS", req)
    monkeypatch.setattr(launcher, "PROJECT_DIR", source)
    runtime = tmp_path / "private_runtime"
    calls = []
    state = {"installed": False}

    class MockBuilder:
        def __init__(self, with_pip):
            assert with_pip is True

        def create(self, location):
            python_path = launcher._runtime_python(Path(location))
            python_path.parent.mkdir(parents=True, exist_ok=True)
            python_path.write_text("stub", encoding="utf-8")

    def fake_run(argv, **kwargs):
        calls.append((list(argv), kwargs))
        if "-m" in argv:
            assert argv[argv.index("-m") + 1] == "pip"
            assert argv[argv.index("-r") + 1] == str(req)
            assert kwargs["cwd"] == str(source)
            assert kwargs["env"]["PYTHONNOUSERSITE"] == "1"
            state["installed"] = True
        return __import__("types").SimpleNamespace(returncode=0 if state["installed"] else 1)

    monkeypatch.setattr(launcher.venv, "EnvBuilder", MockBuilder)
    monkeypatch.setattr(launcher.subprocess, "run", fake_run)
    assert launcher._prepare_runtime(runtime)
    assert (runtime / ".instalacion_correcta").exists()
    assert not (tmp_path / "private_runtime.instalando").exists()
    installs = [c for c in calls if "-m" in c[0]]
    assert len(installs) == 1
    calls.clear()
    assert launcher._prepare_runtime(runtime)
    assert not any("-m" in c[0] for c in calls)


def test_rebuild_035_failed_install_not_marked_ready_and_can_retry(tmp_path, monkeypatch):
    launcher = _load_launcher_for_tests()
    source = tmp_path / "project"
    source.mkdir()
    req = source / "requirements.txt"
    req.write_text("PySide6>=6.6,<7\n", encoding="utf-8")
    monkeypatch.setattr(launcher, "REQUIREMENTS", req)
    monkeypatch.setattr(launcher, "PROJECT_DIR", source)
    runtime = tmp_path / "private_runtime"
    state = {"allow_install": False, "installed": False}

    class MockBuilder:
        def __init__(self, with_pip):
            pass

        def create(self, location):
            python_path = launcher._runtime_python(Path(location))
            python_path.parent.mkdir(parents=True, exist_ok=True)
            python_path.write_text("stub", encoding="utf-8")

    def fake_run(argv, **kwargs):
        if "-m" in argv:
            if state["allow_install"]:
                state["installed"] = True
                return __import__("types").SimpleNamespace(returncode=0)
            return __import__("types").SimpleNamespace(returncode=1)
        return __import__("types").SimpleNamespace(returncode=0 if state["installed"] else 1)

    monkeypatch.setattr(launcher.venv, "EnvBuilder", MockBuilder)
    monkeypatch.setattr(launcher.subprocess, "run", fake_run)
    assert not launcher._prepare_runtime(runtime)
    assert not (runtime / ".instalacion_correcta").exists()
    state["allow_install"] = True
    assert launcher._prepare_runtime(runtime)
    assert (runtime / ".instalacion_correcta").exists()


def test_rebuild_035_launcher_executes_from_its_own_absolute_paths():
    main = (ROOT / "main.py").read_text(encoding="utf-8")
    bat = (ROOT / "Iniciar_CorePulse.bat").read_text(encoding="utf-8")
    assert 'PROJECT_DIR = Path(__file__).resolve().parent' in main
    assert '"-r", str(REQUIREMENTS)' in main
    assert 'from PySide6.QtCore import QUrl' in main
    assert 'venv.EnvBuilder(with_pip=True)' in main
    assert 'if not _prepare_runtime(runtime):' in main
    assert '"-B", str(PROJECT_DIR / "main.py")' in main
    assert 'cd /d "%~dp0"' in bat
    assert 'python -B "%~dp0main.py"' in bat
    assert sorted(p.name for p in ROOT.glob("*.py")) == ["main.py"]


# REBUILD 037: centro de salud / batería solo lectura, sin valores inventados.
def _battery_functions():
    import math
    tree = ast.parse((ROOT / "core" / "health" / "battery.py").read_text(encoding="utf-8"))
    needed = {"_number", "_rows", "_key", "parse_battery_specs", "format_duration"}
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in needed]
    context = {"math": math}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "battery.py", "exec"), context)
    return context


def test_battery_genuine_capacity_and_wear():
    parse = _battery_functions()["parse_battery_specs"]
    result = parse({
        "design": [{"InstanceName": "BATTERY0", "DesignedCapacity": 60000}],
        "full": [{"InstanceName": "battery0", "FullChargedCapacity": 48000}],
        "cycles": [{"InstanceName": "BATTERY0", "CycleCount": 214}],
        "win32": [{"Name": "Laptop Battery", "Manufacturer": "OEM"}],
    })
    assert result["batteryFound"] is True
    assert result["healthPct"] == 80.0 and result["wearPct"] == 20.0
    assert result["designWh"] == 60.0 and result["fullWh"] == 48.0
    assert result["cycles"] == 214


def test_battery_unknowns_do_not_become_100_percent():
    parse = _battery_functions()["parse_battery_specs"]
    for values in ({}, {"win32": [{"Name": "Battery"}]},
                   {"design": [{"InstanceName": "a", "DesignedCapacity": 50000}],
                    "full": [{"InstanceName": "b", "FullChargedCapacity": 40000}]},
                   {"design": [{"InstanceName": "a", "DesignedCapacity": 0}],
                    "full": [{"InstanceName": "a", "FullChargedCapacity": 40000}]}):
        r = parse(values)
        assert r["healthPct"] is None and r["wearPct"] is None
        assert r["designWh"] is None and r["fullWh"] is None


def test_battery_multiple_cells_requires_complete_matches():
    parse = _battery_functions()["parse_battery_specs"]
    rows = {
        "design": [{"InstanceName": "a", "DesignedCapacity": 30000},
                   {"InstanceName": "b", "DesignedCapacity": 30000}],
        "full": [{"InstanceName": "a", "FullChargedCapacity": 20000},
                 {"InstanceName": "b", "FullChargedCapacity": 28000}],
    }
    r = parse(rows)
    assert r["healthPct"] == 80 and r["cycles"] is None
    rows["full"].pop()
    assert parse(rows)["healthPct"] is None


def test_battery_duration_and_invalid_values():
    ns = _battery_functions()
    assert ns["format_duration"](7200) == "2 h 00 min"
    assert ns["format_duration"](-2) == "N/A"
    assert ns["format_duration"](None) == "N/A"
    assert ns["_number"](float("nan")) is None
    assert ns["_number"](True) is None


def test_health_page_connected_without_fake_metrics_or_windows_writes():
    main = (UI / "Main.qml").read_text(encoding="utf-8")
    health = (UI / "HealthPage.qml").read_text(encoding="utf-8")
    battery = (ROOT / "core" / "health" / "battery.py").read_text(encoding="utf-8")
    launcher = (ROOT / "main.py").read_text(encoding="utf-8")
    assert 'window.selectedPage==="health" || window.selectedPage==="battery"' in main
    assert 'HealthPage {' in main and 'onGoBack: window.selectedPage' in main
    assert 'context.setContextProperty("batteryHealth", battery_health)' in launcher
    assert 'app.aboutToQuit.connect(battery_health.close)' in launcher
    assert "class BatteryHealth(QObject):" in battery
    assert "Get-CimInstance" in battery and "sensors_battery" in battery
    assert "parse_battery_specs" in battery
    assert "ThinScroll" in health and "batteryHealth.refresh()" in health
    assert "return 'N/A'" in battery
    for forbidden in ("Set-CimInstance", "Set-WmiInstance", "powercfg /set", "reg add", "Win32_Battery -Property"):
        assert forbidden.lower() not in battery.lower()


def test_battery_win32_single_battery_fallback():
    parse = _battery_functions()["parse_battery_specs"]
    r = parse({"win32": [{"Name": "Battery", "DesignCapacity": 50000, "FullChargeCapacity": 45000}]})
    assert r["healthPct"] == 90 and r["wearPct"] == 10
    assert r["cycles"] is None
    assert parse({"win32": [{"DesignCapacity": 50000, "FullChargeCapacity": 45000},
                            {"DesignCapacity": 50000, "FullChargeCapacity": 45000}]})["healthPct"] is None


def test_battery_power_source_unknown_does_not_invent_a_charge():
    import types
    ns = {"psutil": types.SimpleNamespace(sensors_battery=lambda: None),
          "_number": _battery_functions()["_number"]}
    tree = ast.parse((ROOT / "core" / "health" / "battery.py").read_text(encoding="utf-8"))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "read_charge_state")
    exec(compile(ast.Module(body=[node], type_ignores=[]), "battery.py", "exec"), ns)
    assert ns["read_charge_state"]() is None
    ns["psutil"].sensors_battery = lambda: types.SimpleNamespace(percent=65.2, secsleft=-2, power_plugged=True)
    assert ns["read_charge_state"]() == {"percent": 65.2, "plugged": True, "seconds": None}
    ns["psutil"].sensors_battery = lambda: types.SimpleNamespace(percent=float("nan"), secsleft=2000, power_plugged=False)
    assert ns["read_charge_state"]() == {"percent": None, "plugged": False, "seconds": 2000}


# REBUILD 037: recupera fuentes de V485 sin cruzar capacidades entre baterías.
def _battery_report_functions():
    import math
    import xml.etree.ElementTree as ET
    tree = ast.parse((ROOT / 'core' / 'health' / 'battery.py').read_text(encoding='utf-8'))
    names = {'_number', '_xml_local', '_xml_field', 'parse_battery_report_xml',
             'merge_battery_sources'}
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    ns = {'math':math, 'ET':ET}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), 'battery.py', 'exec'), ns)
    return ns


def test_battery_report_xml_one_real_battery():
    parse = _battery_report_functions()['parse_battery_report_xml']
    xml = b"""<BatteryReport xmlns="urn:windows:battery"><Batteries>
    <Battery><Name>OEM pack</Name><Manufacturer>OEM</Manufacturer>
    <DesignCapacity>60000</DesignCapacity><FullChargeCapacity>45120</FullChargeCapacity>
    <CycleCount>124</CycleCount></Battery></Batteries>
    <History><FullChargeCapacity>90000</FullChargeCapacity></History></BatteryReport>"""
    r = parse(xml)
    assert r['batteryFound'] and r['count'] == 1
    assert r['designWh'] == 60 and r['fullWh'] == 45.1
    assert r['healthPct'] == 75.2 and r['wearPct'] == 24.8
    assert r['cycles'] == 124 and r['model'] == 'OEM pack'


def test_battery_report_xml_multibattery_no_partial_or_forged_cycles():
    parse = _battery_report_functions()['parse_battery_report_xml']
    good = '<BatteryReport><Batteries><Battery><DesignCapacity>30000</DesignCapacity><FullChargeCapacity>24000</FullChargeCapacity><CycleCount>12</CycleCount></Battery><Battery><DesignCapacity>30000</DesignCapacity><FullChargeCapacity>27000</FullChargeCapacity><CycleCount>15</CycleCount></Battery></Batteries></BatteryReport>'
    r = parse(good)
    assert (r['designWh'], r['fullWh'], r['healthPct']) == (60.0, 51.0, 85.0)
    assert r['cycles'] is None
    bad = good.replace('<FullChargeCapacity>27000</FullChargeCapacity>', '')
    r = parse(bad)
    assert r['designWh'] is None and r['fullWh'] is None and r['healthPct'] is None
    assert r['count'] == 2


def test_battery_report_rejects_invalid_xml_and_invalid_capacity():
    parse = _battery_report_functions()['parse_battery_report_xml']
    assert parse('<bad>')['healthPct'] is None
    invalid = b'<BatteryReport><Batteries><Battery><DesignCapacity>0</DesignCapacity><FullChargeCapacity>40000</FullChargeCapacity><CycleCount>0</CycleCount></Battery></Batteries></BatteryReport>'
    r = parse(invalid)
    assert r['healthPct'] is None and r['cycles'] == 0


def test_battery_merging_does_not_mix_pack_inventories():
    merge = _battery_report_functions()['merge_battery_sources']
    cim = {'batteryFound': True, 'count': 2, 'healthPct': None, 'cycles': None}
    report = {'batteryFound': True, 'count': 1, 'healthPct': 90.0, 'wearPct': 10.0, 'designWh': 50.0, 'fullWh': 45.0, 'cycles': 200}
    r = merge(cim, report)
    assert r['healthPct'] is None and r['cycles'] is None
    assert r['count'] == 2
    r = merge({'count':1, 'healthPct':None}, report)
    assert r['healthPct'] == 90.0 and r['cycles'] == 200
    r = merge({'count':1, 'healthPct':84.0, 'designWh':50.0, 'fullWh':42.0, 'cycles':5}, report)
    assert (r['healthPct'], r['cycles']) == (84.0, 5)


def test_battery_report_runs_read_only_and_removes_transient_xml():
    battery = (ROOT / 'core/health/battery.py').read_text(encoding='utf-8')
    assert "'/batteryreport', '/xml', '/output'" in battery
    assert 'output.unlink(missing_ok=True)' in battery
    assert 'ThreadPoolExecutor' in battery and 'timeout=25' in battery
    for dangerous in ('powercfg /set', 'Set-CimInstance', 'Set-WmiInstance', 'reg add'):
        assert dangerous.lower() not in battery.lower()


def test_battery_connected_does_not_mislabel_time_as_failure():
    battery = (ROOT / 'core/health/battery.py').read_text(encoding='utf-8')
    assert "'Conectado a corriente' if plugged is True" in battery
    assert 'Conectado a corriente' in battery


# REBUILD 038: autonomía real y Centro de Salud multiplataforma.
def _selected_pure_battery(*names):
    import math
    path = ROOT / 'core/health/battery.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    needed = {'_number', 'estimate_runtime_from_rate', 'estimate_runtime_from_samples'}
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in needed]
    env = {'math': math}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), env)
    return [env[n] for n in names]


def test_runtime_from_single_wmi_battery_consumption():
    f, = _selected_pure_battery('estimate_runtime_from_rate')
    assert f([{'InstanceName':'BAT0','Discharging':True,
               'RemainingCapacity':30000,'DischargeRate':12000}]) == 9000
    assert f([{'InstanceName':'BAT0','Discharging':False,
               'RemainingCapacity':30000,'DischargeRate':12000}]) is None


def test_runtime_multibattery_requires_all_valid_unique_real_rates():
    f, = _selected_pure_battery('estimate_runtime_from_rate')
    good = [{'InstanceName':'BAT0','Discharging':True, 'RemainingCapacity':20000,'DischargeRate':10000},
            {'InstanceName':'BAT1','Discharging':True, 'RemainingCapacity':30000,'DischargeRate':10000}]
    assert f(good) == 9000
    assert f(good + [good[0]]) is None
    assert f(good[:1] + [dict(good[1], DischargeRate=0)]) is None
    assert f([{'InstanceName':'BAT0','Discharging':True,
               'RemainingCapacity':20000,'DischargeRate':-1}]) is None


def test_observed_discharge_requires_enough_time_and_percent_drop():
    f, = _selected_pure_battery('estimate_runtime_from_samples')
    assert f([(10,55.0),(310,54.0)]) == 16200
    assert f([(10,55.0),(150,54.0)]) is None
    assert f([(10,55.0),(310,55.0)]) is None
    assert f([(10,55.0),(310,56.0)]) is None


def _selected_pure_storage():
    import math
    path = ROOT / 'core/health/storage.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    wanted = {'_capacity', 'format_gib', 'parse_physical_disks'}
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in wanted]
    env = {'math':math}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), env)
    return env


def test_storage_health_distinguishes_unknown_and_healthy():
    f = _selected_pure_storage()['parse_physical_disks']
    a = f([{'FriendlyName':'Disk A', 'HealthStatus':0, 'MediaType':4, 'Size':512*1024**3},
           {'FriendlyName':'Disk B', 'HealthStatus':5, 'MediaType':3, 'Size':1000*1024**3}])
    assert len(a) == 2
    assert (a[0]['health'],a[0]['media'],a[0]['healthKnown']) == ('Correcto','SSD',True)
    assert a[1]['health'] == 'N/A' and a[1]['healthKnown'] is False
    assert f([{'FriendlyName':'', 'HealthStatus':0}]) == []


def test_storage_data_does_not_claim_wear_percent_or_guess_smart():
    file = (ROOT/'core/health/storage.py').read_text(encoding='utf-8')
    assert 'MSFT_PhysicalDisk' in file and 'disk_usage' in file
    assert 'GetDriveTypeW' in file and 'Get-CimInstance' in file
    assert 'chkdsk /f' not in file and 'Set-Disk' not in file
    assert 'healthKnown' in file and 'usedPct' in file


def test_health_modules_respect_desktop_absence_and_allow_storage():
    main = (UI/'Main.qml').read_text(encoding='utf-8')
    page = (UI/'HealthPage.qml').read_text(encoding='utf-8')
    assert 'item.id !== "battery" ||' in main
    assert 'info.hasBattery' in page
    assert 'page.currentModule === "storage"' in page
    assert 'page.currentModule === "battery" && info.hasBattery' in page
    assert 'storageHealth.refresh()' in page
    assert 'remainingSource' in page
    assert 'requestedModule: window.selectedPage === "storage"' in main
    assert 'storage_health = StorageHealth()' in (ROOT/'main.py').read_text(encoding='utf-8')


def test_battery_runtime_safety_and_source_traceability():
    code = (ROOT/'core/health/battery.py').read_text(encoding='utf-8')
    assert 'read_discharge_runtime' in code and 'BatteryStatus' in code
    assert 'estimate_runtime_from_samples' in code
    assert "'Estimación según descarga actual (Windows WMI)'" in code
    assert "'Estimación según descarga observada'" in code
    assert 'self._runtime_executor.shutdown' in code
    assert 'self._samples.clear()' in code


def test_storage_zero_bytes_available_is_real_zero_not_na():
    fmt = _selected_pure_storage()['format_gib']
    assert fmt(0) == '0.0 GB'
    assert fmt(None) == 'N/A'
    assert fmt(-1) == 'N/A'
    assert fmt(2**30) == '1.0 GB'


def test_discharge_sessions_invalidate_old_results():
    battery = (ROOT/'core/health/battery.py').read_text(encoding='utf-8')
    assert 'self._pending_runtime_session == self._runtime_session' in battery
    assert 'self._runtime_session += 1' in battery
    assert 'self._samples.clear()' in battery


# REBUILD 039: contrato de análisis de Windows recuperado (solo diagnóstico).
def _pure_windows_parser():
    import ast
    path = ROOT/'core/health/windows.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    names = {'_int_count', '_short', '_items', '_empty_section', 'parse_windows_report'}
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    ns = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), ns)
    return ns['parse_windows_report']


def test_windows_health_missing_data_is_not_healthy_or_zero():
    parse = _pure_windows_parser()
    for raw in (None, {}, [], {'startup': None, 'drivers': {'available': False, 'problems': 0}}):
        a = parse(raw)
        assert all(not x['available'] and x['metric'] == 'N/A' for x in a.values())


def test_windows_health_real_counts_and_capped_events():
    parse = _pure_windows_parser()
    a = parse({
        'startup': {'available': True, 'count': 4, 'items': [{'Name': 'Programa', 'Location': 'HKCU'}]},
        'services': {'available': True, 'total': 140, 'running': 85,
                     'autoStopped': 7, 'items': [{'Name': 'Svc', 'DisplayName': 'Servicio', 'State': 'Stopped'}]},
        'events': {'available': True, 'count': 80, 'capped': True, 'items': [{'Source':'Kernel','Id':41,'When':'2026-10-11 14:00'}]},
        'drivers': {'available': True, 'total': 120, 'problems': 1, 'items': [{'Name': 'Adaptador','ConfigManagerErrorCode': 28}]},
    })
    assert a['startup']['metric'] == '4' and a['startup']['items'][0]['primary'] == 'Programa'
    assert a['services']['metric'] == '7' and 'no siempre es error' in a['services']['caption']
    assert a['events']['metric'] == '80+' and 'ID 41' in a['events']['items'][0]['primary']
    assert a['drivers']['metric'] == '1' and '28' in a['drivers']['items'][0]['secondary']


def test_windows_health_zero_is_real_only_when_source_available():
    parse = _pure_windows_parser()
    a = parse({'events': {'available': True, 'count': 0, 'capped': False, 'items': []},
               'drivers': {'available': True, 'total': 120, 'problems': 0, 'items': []}})
    assert a['events']['metric'] == '0'
    assert a['drivers']['metric'] == '0'
    assert a['startup']['metric'] == 'N/A'


def test_windows_health_rejects_inconsistent_counts_and_control_chars():
    parse = _pure_windows_parser()
    a = parse({'startup': {'available': True, 'count': True, 'items': []},
               'services': {'available': True, 'total': 5, 'running': 9, 'autoStopped': 0},
               'drivers': {'available': True, 'total': 10, 'problems': 12},
               'events': {'available': True, 'count': 1, 'items': [{'Source':'Test\nTest','Id':33}]}})
    assert not a['startup']['available'] and not a['services']['available']
    assert not a['drivers']['available']
    assert '\n' not in a['events']['items'][0]['primary']


def test_windows_health_sources_are_read_only_and_bounded():
    code = (ROOT/'core/health/windows.py').read_text(encoding='utf-8')
    for source in ('Win32_StartupCommand', 'Win32_Service', 'Get-WinEvent', 'Win32_PnPEntity'):
        assert source in code
    for mutation in ('Set-Service', 'Stop-Service', 'Disable-PnpDevice', 'Remove-Item', 'Set-ItemProperty', 'New-ItemProperty', 'reg delete', 'sc stop'):
        assert mutation.lower() not in code.lower()
    assert '-MaxEvents 80' in code and 'timeout=45' in code
    assert 'ThreadPoolExecutor' in code and 'creationflags' in code
    assert 'CommandLine' not in code and 'Message' not in code  # datos privados innecesarios


def test_windows_health_qml_navigation_and_lifecycle():
    main = (UI/'Main.qml').read_text(encoding='utf-8')
    page = (UI/'HealthPage.qml').read_text(encoding='utf-8')
    launcher = (ROOT/'main.py').read_text(encoding='utf-8')
    assert 'id:"windows_health",label:"Análisis de Windows"' in main
    assert 'requestedModule: window.selectedPage === "storage" ? "storage"' in main
    assert 'window.selectedPage === "windows_health" ? "windows"' in main
    assert 'visible: page.currentModule === "windows"' in page
    assert 'windowsHealth.refresh()' in page
    assert 'page.windowsInfo' in page and 'Ver detalles' in page
    for contract in ('windows_health = WindowsHealth()', 'windows_health.close', 'setContextProperty("windowsHealth", windows_health)'):
        assert contract in launcher


def test_windows_health_is_lazy_until_user_opens_module():
    py = (ROOT/'core/health/windows.py').read_text(encoding='utf-8')
    qml = (UI/'HealthPage.qml').read_text(encoding='utf-8')
    # La consulta WMI potencialmente costosa no debe ejecutarse durante el arranque principal.
    init = py.split('def __init__(self, parent=None):', 1)[1].split('    @Property', 1)[0]
    assert 'self.refresh()' not in init
    assert 'onCurrentModuleChanged:' in qml and 'Component.onCompleted:' in qml


# REBUILD 040 — Reparación de Windows y tarjetas compactas.
def _repair_pure_classifier():
    tree = ast.parse((ROOT / "core/health/repair.py").read_text(encoding="utf-8"))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "classify_integrity")
    ns = {}
    exec(compile(ast.Module(body=[node], type_ignores=[]), "repair.py", "exec"), ns)
    return ns["classify_integrity"]

def test_repair_distinguishes_success_from_health_and_failure():
    classify = _repair_pure_classifier()
    assert classify("dism_checkhealth", 0, "No component store corruption detected")[0] == "SIN_DANOS"
    assert classify("dism_scanhealth", 0, "The component store is repairable")[0] == "ATENCION"
    assert classify("sfc_verifyonly", 0, "Windows Resource Protection did not find any integrity violations")[0] == "SIN_DANOS"
    assert classify("sfc_scannow", 0, "Windows Resource Protection found corrupt files and successfully repaired them")[0] == "REPARADO"
    assert classify("dism_restorehealth", 0, "unrecognized output")[0] == "SIN_CLASIFICAR"
    assert classify("dism_checkhealth", 5, "ok")[0] == "ERROR"
    assert classify("sfc_scannow", None, "unknown")[0] == "ERROR"

def test_repair_only_explicit_and_privileged_no_shell_or_auto_run():
    src = (ROOT / 'core/health/repair.py').read_text(encoding='utf-8')
    page = (UI / 'HealthPage.qml').read_text(encoding='utf-8')
    launcher = (ROOT/'main.py').read_text(encoding='utf-8')
    for op in ('/CheckHealth','/ScanHealth','/verifyonly','/RestoreHealth','/scannow'):
        assert op in src
    assert 'if not has_admin_rights():' in src
    assert 'shell=True' not in src and 'subprocess.run(' in src
    assert 'def start(self, kind):' in src
    assert 'self._pool.submit(run_integrity, kind' in src
    assert 'self.start(' not in src.split('def __init__(self, parent=None):')[1].split('@Property')[0]
    assert 'onClicked: page.confirmRepair = "repair"' in page
    assert 'if (selected === "diagnostic" || selected === "repair") repairHealth.start(selected)' in page
    assert 'context.setContextProperty("repairHealth", repair_health)' in launcher
    assert 'app.aboutToQuit.connect(repair_health.close)' in launcher

def test_windows_cards_details_raised_and_repair_ui_present():
    page = (UI/'HealthPage.qml').read_text(encoding='utf-8')
    main = (UI/'Main.qml').read_text(encoding='utf-8')
    assert 'Layout.fillWidth: true; Layout.preferredHeight: 152' in page
    assert 'text: section.caption; Layout.fillWidth: true' in page
    assert 'Layout.preferredHeight: 33' in page
    assert 'visible: page.currentModule === "repair"' in page
    assert 'id: repairConfirmOverlay' in page
    assert 'window.selectedPage==="repair"' in main
    assert 'Rebuild 107' in main


def test_rebuild_042_recovery_module_present():
    main = (UI/'Main.qml').read_text(encoding='utf-8')
    page = (UI/'HealthPage.qml').read_text(encoding='utf-8')
    recovery = (ROOT/'core'/'health'/'recovery.py').read_text(encoding='utf-8')
    app = (ROOT/'main.py').read_text(encoding='utf-8')
    assert '{id:"restore",label:"Recuperación",icon:"restore"}' in main
    assert 'window.selectedPage === "restore" ? "recovery" :'  in main
    assert 'text: "Recuperación del sistema"' in page
    assert 'visible: page.currentModule === "recovery"' in page
    assert 'Abrir Restaurar sistema' in page
    assert 'class RecoveryHealth(QObject):' in recovery
    assert 'def createPoint(self):' in recovery
    assert 'context.setContextProperty("recoveryHealth", recovery_health)' in app

# Recuperación V043: pruebas ejecutables sin dependencias Qt ni Windows.
def _recovery_contract_functions():
    import base64
    import datetime
    import json
    import types
    import subprocess
    import shutil
    path = ROOT / 'core' / 'health' / 'recovery.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    names = {'_short', '_type_name', '_parse_restore_points', '_parse_winre',
             '_run_ps_json', 'read_recovery_report', 'create_restore_point',
             '_failure_message', '_creation_failure'}
    defs = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    constants = [n for n in tree.body if isinstance(n, ast.Assign) and any(
        isinstance(t, ast.Name) and t.id in ('RESTORE_POINTS_QUERY', 'CREATE_POINT_SCRIPT') for t in n.targets)]
    ns = {'base64': base64, 'json': json, 'datetime': datetime.datetime,
          're': re, 'subprocess': subprocess, 'shutil': shutil,
          'os': types.SimpleNamespace(name='nt', environ={'SystemDrive': 'C:'})}
    exec(compile(ast.Module(body=constants + defs, type_ignores=[]), str(path), 'exec'), ns)
    return ns


def test_recovery_043_parses_real_points_and_correct_wmi_dates():
    fn = _recovery_contract_functions()
    script = fn['RESTORE_POINTS_QUERY']
    assert 'Select-Object -First 12' in script
    assert 'ManagementDateTimeConverter' in script
    assert "@{\n        N='Description'" not in script
    records = {'available': True, 'pointCount': 2, 'points': [
        {'Description': 'Instalación segura', 'SequenceNumber': 20, 'RestorePointType': 16,
         'CreationTime': '2026-10-11 23:15'},
        {'Description': 'Windows Update', 'SequenceNumber': 19, 'RestorePointType': 18,
         'CreationTime': '2026-10-09 10:01'}]}
    points, count, latest, when, known = fn['_parse_restore_points'](records)
    assert known and count == '2' and latest == 'Instalación segura'
    assert when == '2026-10-11 23:15' and len(points) == 2
    assert 'Windows Update' in points[1]['primary']


def test_recovery_043_unknown_not_false_zero_and_zero_is_real():
    fn = _recovery_contract_functions()
    for payload in (None, {'available': False, 'pointCount': 0, 'points': []}):
        rows, count, latest, when, known = fn['_parse_restore_points'](payload)
        assert not known and count == 'N/A' and rows == []
    rows, count, latest, when, known = fn['_parse_restore_points']({
        'available': True, 'pointCount': 0, 'points': []})
    assert known and count == '0' and latest == 'Sin puntos'


def test_recovery_043_winre_language_sensitive_and_no_false_positive():
    fn = _recovery_contract_functions()['_parse_winre']
    assert fn('Windows RE status: Enabled') == 'Activa'
    assert fn('Estado de Windows RE: Habilitado') == 'Activa'
    assert fn('Estado de Windows RE: Deshabilitado') == 'Desactivada'
    assert fn('Windows RE status: Disabled') == 'Desactivada'
    assert fn('Windows RE location: Enabled folder') == 'N/A'


def test_recovery_043_encoded_command_and_strict_json_result():
    import base64
    import types
    fn = _recovery_contract_functions()
    captured = {}

    def fake_run(args, **kwargs):
        captured['command'] = args
        return types.SimpleNamespace(returncode=0, stdout=b'{"available":true,"pointCount":0}', stderr=b'')

    fn['shutil'] = types.SimpleNamespace(which=lambda _: 'powershell.exe')
    fn['subprocess'] = types.SimpleNamespace(
        run=fake_run, CREATE_NO_WINDOW=0, TimeoutExpired=__import__('subprocess').TimeoutExpired)
    data, err = fn['_run_ps_json']('Write-Output "é"')
    assert err == 'none' and data['pointCount'] == 0
    assert '-EncodedCommand' in captured['command']
    command_string = base64.b64decode(captured['command'][-1]).decode('utf-16le')
    assert command_string == 'Write-Output "é"'


def test_recovery_043_results_never_mark_failed_query_healthy():
    fn = _recovery_contract_functions()
    fn['_run_ps_json'] = lambda *_: (None, 'invalid_response')
    fn['_run_reagentc'] = lambda: 'Windows RE status: Enabled'
    fn['has_admin_rights'] = lambda: True
    output = fn['read_recovery_report']()
    assert output['status'] == 'PARCIAL'
    assert output['pointCount'] == 'N/A'
    assert output['protectionText'] == 'No confirmada'
    assert output['recoveryEnv'] == 'Activa'
    assert 'línea' not in output['summary']
    fn['_run_ps_json'] = lambda *_: ({'available': True, 'pointCount': 0,
        'points': [], 'protectionState': 'unknown', 'errorKind': 'none'}, 'none')
    output = fn['read_recovery_report']()
    assert output['status'] == 'OK' and output['pointCount'] == '0'
    assert output['latestDescription'] == 'Sin puntos'


def test_recovery_043_creation_requires_explicit_verification():
    fn = _recovery_contract_functions()
    fn['has_admin_rights'] = lambda: True
    fn['_run_ps_json'] = lambda *_ , **__: ({'ok': True, 'verified': False}, 'none')
    assert fn['create_restore_point']()[0] is False
    fn['_run_ps_json'] = lambda *_ , **__: ({'ok': True, 'verified': True}, 'none')
    assert fn['create_restore_point']()[0] is True
    assert '$beforeOk -and $fresh.Count -gt 0' in fn['CREATE_POINT_SCRIPT']

# REBUILD 044: pruebas reales del parser de historial, sin Windows ni Qt.
def _history_contract_functions():
    import datetime
    import json
    import os
    from collections import deque
    path = ROOT / 'core' / 'health' / 'history.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    names = {'_short', '_dt', '_event', '_result', 'read_tweaks', 'read_repairs',
             'parse_updates', 'parse_restore', 'read_history'}
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    constants = [n for n in tree.body if isinstance(n, ast.Assign) and any(
        isinstance(a, ast.Name) and a.id in {'SOURCE_LABELS', 'SOURCE_HINTS'}
        for a in n.targets)]
    env = {'datetime': datetime.datetime, 'Path': Path, 'json': json, 'deque': deque, 'os': os}
    exec(compile(ast.Module(body=constants + nodes, type_ignores=[]), str(path), 'exec'), env)
    return env


def test_history_044_qml_routes_without_duplicate_modules():
    main = (UI/'Main.qml').read_text(encoding='utf-8')
    health = (UI/'HealthPage.qml').read_text(encoding='utf-8')
    app = (ROOT/'main.py').read_text(encoding='utf-8')
    assert 'title:"CorePulse — Rebuild 107"' in main
    assert 'window.selectedPage === "change_history" ? "history"' in main
    assert main.count('id:"change_history",label:"Historial de cambios"') == 1
    assert 'visible: page.currentModule === "history"' in health
    assert 'page.historyInfo.sections || []' in health
    assert 'page.historyFiltered' in health
    assert 'changeHistory.refresh()' in health
    assert 'from core.health.history import ChangeHistory' in app
    assert 'context.setContextProperty("changeHistory", change_history)' in app
    assert 'app.aboutToQuit.connect(change_history.close)' in app


def test_history_044_tweak_audit_persisted_and_malformed_ignored(tmp_path):
    fn = _history_contract_functions()
    assert fn['read_tweaks'](tmp_path)['available'] is True
    assert fn['read_tweaks'](tmp_path)['entries'] == []
    import json
    data = [
        {'timestamp': 1791733200, 'tweak_id': 'show_file_extensions', 'action': 'apply', 'success': True},
        {'timestamp': 1791733300, 'tweak_id': 'show_file_extensions', 'action': 'undo', 'success': False},
    ]
    (tmp_path/'windows_tweaks_history.jsonl').write_text(
        json.dumps(data[0]) + '\n{corrupto\n' + json.dumps(data[1]) + '\n', encoding='utf-8')
    out = fn['read_tweaks'](tmp_path)
    assert out['available'] and len(out['entries']) == 2
    assert {x['state'] for x in out['entries']} == {'Aplicado', 'Falló'}
    assert 'show file extensions' in out['entries'][0]['title']


def test_history_044_repair_logs_usable_and_corrupt_report_not_success(tmp_path):
    fn = _history_contract_functions()
    log = tmp_path/'integridad_20261011_210000_000.json'
    log.write_text('{nojson', encoding='utf-8')
    assert fn['read_repairs'](tmp_path)['available'] is False
    import json
    log.write_text(json.dumps({'kind': 'diagnostic', 'finished':'2026-10-11T21:00:00',
                               'state':'SIN_DANOS', 'results':[{'title':'SFC'}]}), encoding='utf-8')
    out = fn['read_repairs'](tmp_path)
    assert out['available'] and len(out['entries']) == 1
    assert 'Comprobación de integridad' in out['entries'][0]['title']
    assert out['entries'][0]['state'] == 'SIN_DANOS'


def test_history_044_restore_and_updates_reject_unverified_data():
    fn = _history_contract_functions()
    assert fn['parse_restore'](None)['available'] is False
    assert fn['parse_restore']({'available': False, 'pointCount': 0, 'points': []})['available'] is False
    zero = fn['parse_restore']({'available': True, 'pointCount': 0, 'points': []})
    assert zero['available'] and not zero['entries']
    restore = fn['parse_restore']({'available': True, 'pointCount': 1, 'points': [
        {'Description':'Instalación DirectX', 'CreationTime':'2026-10-11 02:01', 'SequenceNumber':10}]})
    assert restore['available'] and len(restore['entries']) == 1
    assert fn['parse_updates']({'available': False, 'entries': []})['available'] is False
    result = fn['parse_updates']({'available': True, 'entries': [
        {'Title':'Actualización acumulativa', 'Date':'2026-10-10T15:03:00+00:00',
         'Operation': 1, 'ResultCode': 2}]})
    assert result['available'] and result['entries'][0]['state'] == 'Correcto'
    assert fn['parse_updates']({'available': True, 'entries': [
        {'Title':'Evento sin fecha', 'Operation':1, 'ResultCode':2}]})['available'] is False


def test_history_044_partial_sources_and_timeline_sorted():
    fn = _history_contract_functions()
    first = fn['_event']('tweaks', 'Acción A', 'Registro', 'Aplicado', '2026-10-09T13:00:00')
    second = fn['_event']('repair', 'Acción B', 'Registro', 'SIN_DANOS', '2026-10-11T15:00:00')
    stages = []
    readers = {
        'tweaks': lambda: fn['_result']([first], True),
        'repair': lambda: fn['_result']([second], True),
        'updates': lambda: fn['_result']([], False),
        'restore': lambda: fn['_result']([], True),
    }
    result = fn['read_history'](lambda pct, msg: stages.append(pct), readers=readers)
    assert result['sourceCount'] == '3/4' and result['status'] == 'PARCIAL'
    assert result['events'][0]['title'] == 'Acción B'
    assert '_sort' not in result['events'][0]
    assert result['sections'][2]['metric'] == 'N/A'
    assert result['sections'][3]['metric'] == '0'
    assert stages[-1] == 100 and stages == sorted(stages)


def _health_045_functions():
    """Ejecuta solamente funciones puras sin Qt ni Windows instalado."""
    import math
    path = ROOT / "core" / "health" / "system_health.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = {"valid_number", "build_health_summary"}
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    namespace = {"math": math}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
    return namespace


def test_045_real_data_coverage_does_not_invent_health_score():
    fn = _health_045_functions()["build_health_summary"]
    result = fn({}, {}, {}, {}, {})
    assert result["verified"] == 0 and result["state"] == "partial"
    assert result["coverage"] == "0/7"  # no battery on a desktop
    assert not any(x["key"] == "battery" for x in result["checks"])
    assert "score" not in result and "healthPct" not in result
    assert all(x["state"] == "na" for x in result["checks"])
    assert all(x["value"] == "N/A" for x in result["checks"])


def test_045_independent_critical_sensor_and_battery_are_evidence_based():
    fn = _health_045_functions()["build_health_summary"]
    result = fn({"cpuTemp": 97, "gpuTemp": 42, "ramPercent": 71, "cpuTempSource": "Sensor AMD"},
                {"hasBattery": True, "healthPct": 48, "source": "powercfg"},
                {"physical": [{"healthKnown": True, "health": "Correcto"}], "volumes": [{"usedPct": 20}]},
                {"drivers": {"available": True, "metric": "0"}}, {"recoveryEnv": "Activo"})
    assert result["total"] == 8 and result["verified"] == 8
    assert result["critical"] == 2 and result["state"] == "critical"
    assert result["headline"] == "Atención prioritaria"
    assert next(x for x in result["checks"] if x["key"] == "cpu")["source"] == "Sensor AMD"


def test_045_mixed_coverage_not_falsely_healthy():
    fn = _health_045_functions()["build_health_summary"]
    result = fn({"cpuTemp": float("nan"), "gpuTemp": None, "ramPercent": 30},
                {"hasBattery": True, "healthPct": None},
                {"physical": [{"healthKnown": True, "health": "Correcto"},
                              {"healthKnown": False, "health": "N/A"}], "volumes": []},
                {"drivers": {"available": False, "metric": "0"}}, {"recoveryEnv": "N/A"})
    assert result["verified"] == 1 and result["unknown"] == 7
    assert result["state"] == "partial"
    assert next(x for x in result["checks"] if x["key"] == "disks")["state"] == "na"
    assert next(x for x in result["checks"] if x["key"] == "drivers")["state"] == "na"


def test_045_pnp_and_disk_alerts_do_not_claim_driver_updates():
    fn = _health_045_functions()["build_health_summary"]
    result = fn({"ramPercent": 25}, {},
                {"physical": [{"healthKnown": True, "health": "Advertencia"}], "volumes": [{"usedPct": 96}]},
                {"drivers": {"available": True, "metric": "3"}}, {"recoveryEnv": "Inactivo"})
    assert result["attention"] == 4
    assert result["state"] == "attention"
    assert next(x for x in result["checks"] if x["key"] == "drivers")["route"] == "windows_health"
    assert "actualizaciones" in next(x for x in result["checks"] if x["key"] == "drivers")["detail"]


def test_045_wiring_navigation_unique_and_inherited_engines_unchanged():
    qml = (UI / "HealthPage.qml").read_text(encoding="utf-8")
    main = (UI / "Main.qml").read_text(encoding="utf-8")
    app = (ROOT / "main.py").read_text(encoding="utf-8")
    assert 'visible: page.currentModule === "hub"' in qml
    assert 'onNavigateTo: function(target)' in main
    assert 'systemHealth.refresh()' in qml
    assert 'window.selectedPage === "battery" ? "battery"' in main
    assert 'signal navigateTo(string route)' in qml
    assert 'Evidencia: ' in qml
    assert 'Las lecturas ausentes no se consideran saludables.' in qml
    for item in ('recoveryHealth', 'changeHistory', 'systemHealth'):
        assert app.count(f'context.setContextProperty("{item}"') == 1
    assert app.count('recovery_health = RecoveryHealth()') == 1
    assert app.count('change_history = ChangeHistory()') == 1
    assert (ROOT / 'core' / 'health' / 'system_health.py').is_file()


def test_046_temperature_sources_refresh_more_often_and_expire():
    source = (ROOT/'core'/'monitoring'/'telemetry.py').read_text(encoding='utf-8')
    assert 'ttl = 2.0 if cache["data"]' in source
    assert 'else 20.0' in source
    assert 'self._hardware_next_poll = now + 4.0' in source
    assert 'if now - self._cpu_sensor_time <= 12.0' in source
    assert 'direct = query_packaged_cpu_temperature()' in source
    assert source.index('if direct.get("temp") is not None:', source.index('def query_hardware_with_legacy')) < source.index('elif data["temp"] is not None:', source.index('def query_hardware_with_legacy'))


def test_046_critical_limits_are_exclusive_to_verified_readings():
    overview = (UI/'Overview.qml').read_text(encoding='utf-8')
    meter = (UI/'MetricLine.qml').read_text(encoding='utf-8')
    assert 'page.m.uptimeSeconds >= 10 * 3600' in overview
    assert 'page.m.ramPercent >= 90' in overview
    assert 'hotThreshold: 90' in overview  # CPU
    assert 'hotThreshold: 85' in overview  # GPU
    assert 'temperature: page.m.cpuTemp' in overview
    assert 'temperature: page.m.gpuTemp' in overview
    assert 'property bool critical: false' in meter
    assert 'hasTemperature && temperature >= hotThreshold' in meter
    assert 'typeof temperature === "number" && isFinite(temperature)' in meter
    assert 'color:meter.tooHot ? "#F36B75"' in meter


def test_046_uptime_is_observed_and_restarter_requires_confirmation():
    telemetry = (ROOT/'core'/'monitoring'/'telemetry.py').read_text(encoding='utf-8')
    overview = (UI/'Overview.qml').read_text(encoding='utf-8')
    tile = (UI/'StatTile.qml').read_text(encoding='utf-8')
    main = (UI/'Main.qml').read_text(encoding='utf-8')
    assert '"uptimeSeconds": None' in telemetry
    assert 'metrics["uptimeSeconds"] = int(uptime_seconds)' in telemetry
    assert 'restartVisible:page.longSession' in overview
    assert 'onRestartRequested:page.restartRequested()' in overview
    assert 'signal restartRequested()' in tile
    assert 'onClicked:tile.restartRequested()' in tile
    assert 'if (systemActions.pending) window.restartResultOpen = true' in main
    assert 'else window.restartConfirmOpen = true' in main
    assert 'systemActions.scheduleRestart()' in main
    assert 'systemActions.cancelRestart()' in main
    assert 'visible: window.restartConfirmOpen || window.restartResultOpen' in main


def test_046_restart_command_is_not_run_until_explicit_action(monkeypatch):
    import importlib.util
    import sys
    from types import SimpleNamespace
    from unittest.mock import Mock
    path = ROOT/'main.py'
    spec = importlib.util.spec_from_file_location('corepulse046main_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    class SignalFake:
        def emit(self): pass
    class QObjectFake:
        pass
    def signal(*a, **kw): return SignalFake()
    def slot(*a, **kw): return lambda fn: fn
    def qtprop(tp, notify=None): return lambda fn: property(fn)
    qtcore = SimpleNamespace(QObject=QObjectFake, Property=qtprop, Signal=signal, Slot=slot)
    monkeypatch.setitem(sys.modules, 'PySide6', SimpleNamespace(QtCore=qtcore))
    monkeypatch.setitem(sys.modules, 'PySide6.QtCore', qtcore)
    monkeypatch.setattr(module, 'os', SimpleNamespace(name='nt'))
    monkeypatch.setattr(module.shutil, 'which', lambda exe: r'C:\Windows\System32\shutdown.exe')
    fake_run = Mock(return_value=SimpleNamespace(returncode=0))
    monkeypatch.setattr(module.subprocess, 'run', fake_run)
    actions = module.make_system_actions()
    assert fake_run.call_count == 0  # iniciar no puede reiniciar
    assert actions.scheduleRestart() is True
    assert actions.pending is True
    assert fake_run.call_args.args[0][1:] == ['/r','/t','60','/c','Reinicio solicitado por el usuario desde CorePulse']
    assert actions.cancelRestart() is True
    assert fake_run.call_args.args[0][1:] == ['/a']
    assert actions.pending is False


def test_048_audio_stereo_channels_and_pcm_header(tmp_path, monkeypatch):
    import importlib.util
    import wave
    import struct
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    spec = importlib.util.spec_from_file_location("corepulse48_launcher", ROOT / "main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    tones = module.ensure_audio_test_tones()
    assert set(tones) == {"left", "both", "right"}
    assert len(set(tones.values())) == 3
    files = {name: tmp_path / "CorePulse" / "audio_test" / f"stereo_660hz_{name}_v1.wav" for name in tones}
    for name, path in files.items():
        assert path.is_file()
        assert tones[name] == path.resolve().as_uri()
        with wave.open(str(path), "rb") as wav:
            assert (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) == (2, 2, 44100)
            assert wav.getnframes() == int(.7 * 44100)
            sound = wav.readframes(wav.getnframes())
        samples = struct.iter_unpack('<hh', sound)
        left, right = zip(*samples)
        assert max(abs(v) for v in left) > 500 if name != "right" else all(v == 0 for v in left)
        assert max(abs(v) for v in right) > 500 if name != "left" else all(v == 0 for v in right)
    before = {n: p.stat().st_mtime_ns for n, p in files.items()}
    assert module.ensure_audio_test_tones() == tones
    assert {n: p.stat().st_mtime_ns for n, p in files.items()} == before


def test_048_health_hub_only_cards_and_inner_back_navigation():
    health = (UI / "HealthPage.qml").read_text(encoding="utf-8")
    main = (UI / "Main.qml").read_text(encoding="utf-8")
    assert 'requestedModule === "audio" ? "audio" :' in health
    assert '"battery" : "hub"' in health
    assert 'visible: page.currentModule === "hub"' in health
    assert 'page.currentModule = "hub"' in health
    assert 'visible: currentModule !== "hub"; text: "Volver"' in health
    assert 'text: "Estado general"' not in health  # obsolete upper tabs removed
    assert 'text: "Áreas de mantenimiento y diagnóstico"' in health
    for name in ('Batería', 'Windows', 'Reparación', 'Historial y cambios', 'Recuperación', 'Test de Audio'):
        assert f'title:"{name}"' in health
    assert 'target:"audio"' in health
    assert 'onClicked: page.currentModule = hubCard.modelData.target' in health
    assert 'window.selectedPage==="change_history" || window.selectedPage==="audio"' in main
    assert 'window.selectedPage === "audio" ? "audio"' in main


def test_048_audio_guided_wasapi_preserves_windows_actions():
    ui = (UI / "HealthPage.qml").read_text(encoding="utf-8")
    main = (UI / "Main.qml").read_text(encoding="utf-8")
    launcher = (ROOT / 'main.py').read_text(encoding='utf-8')
    audio_engine = (ROOT / 'core' / 'maintenance' / 'audio_test.py').read_text(encoding='utf-8')
    assert 'from core.maintenance.audio_test import AudioTestController' in launcher
    assert 'class AudioTestController(QObject)' in audio_engine
    assert 'def record(self, on_level)' in audio_engine
    assert 'limit = int(5 * info[\'rate\'])' in audio_engine
    assert 'def evidence_rows(result):' in audio_engine
    assert 'import QtMultimedia' not in ui
    assert ui.index('text: "Izquierdo"') < ui.index('text: "Ambos"') < ui.index('text: "Derecho"')
    assert 'onClicked: audioTest.play("left")' in ui
    assert 'onClicked: audioTest.play("both")' in ui
    assert 'onClicked: audioTest.play("right")' in ui
    assert 'audioTest.record()' in ui and 'audioTest.replay()' in ui
    assert 'audioTest.confirm("No estoy seguro")' in ui
    assert 'context.setContextProperty("audioTest", audio_test)' in launcher
    assert 'audioToneLeft' not in launcher and 'audioToneRight' not in launcher
    assert 'systemActions.scheduleRestart()' in main
    assert 'systemActions.cancelRestart()' in main
    assert 'if (systemActions.pending) window.restartResultOpen = true' in main
    assert 'window.restartConfirmOpen || window.restartResultOpen' in main
    assert (ROOT/'core'/'monitoring'/'telemetry.py').read_text(encoding='utf-8').count('self._hardware_next_poll = now + 4.0') == 1


def test_048_winre_parity_handles_spanish_active_value_without_inventing_data():
    fn = _health_045_functions()['build_health_summary']
    for label in ('Activo', 'Activa', 'habilitado', 'Enabled'):
        summary = fn({}, {}, {}, {}, {'recoveryEnv': label})
        recovery = next(row for row in summary['checks'] if row['key'] == 'recovery')
        assert recovery['state'] == 'ok' and recovery['value'] == 'Activo'
    for label in ('Inactivo', 'Desactivada', 'disabled'):
        summary = fn({}, {}, {}, {}, {'recoveryEnv': label})
        recovery = next(row for row in summary['checks'] if row['key'] == 'recovery')
        assert recovery['state'] == 'attention' and recovery['value'] == 'Inactivo'
    summary = fn({}, {}, {}, {}, {'recoveryEnv': None})
    recovery = next(row for row in summary['checks'] if row['key'] == 'recovery')
    assert recovery['state'] == 'na' and recovery['value'] == 'N/A'

# REBUILD 049: rendimiento real y reversibilidad; pruebas independientes de Windows/Qt.
def _performance_module_for_tests():
    import importlib.util
    import sys
    import types
    qt = types.ModuleType('PySide6')
    core = types.ModuleType('PySide6.QtCore')
    class StubSignal:
        def emit(self, *a, **kw):
            pass
    core.QObject = type('QObject', (), {})
    core.Signal = lambda *args, **kwargs: StubSignal()
    core.Slot = lambda *args, **kwargs: (lambda fn: fn)
    core.Property = lambda *args, **kwargs: (lambda fn: property(fn))
    core.QTimer = type('QTimer', (), {})
    qt.QtCore = core
    old_qt = sys.modules.get('PySide6')
    old_core = sys.modules.get('PySide6.QtCore')
    sys.modules['PySide6'] = qt
    sys.modules['PySide6.QtCore'] = core
    try:
        spec = importlib.util.spec_from_file_location('corepulse_performance_test', ROOT/'core'/'health'/'performance.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        if old_qt is None:
            sys.modules.pop('PySide6', None)
        else:
            sys.modules['PySide6'] = old_qt
        if old_core is None:
            sys.modules.pop('PySide6.QtCore', None)
        else:
            sys.modules['PySide6.QtCore'] = old_core


def test_049_powercfg_parser_localized_and_oem_schemes():
    m = _performance_module_for_tests()
    text = ('Esquemas de energía existentes (* activo)\n'
            'GUID de plan: 381b4222-f694-41f0-9685-ff5bb260df2e  (Equilibrado) *\n'
            'Power Scheme GUID: 88888888-9999-aaaa-bbbb-cccccccccccc  (OEM Lenovo rendimiento)\n')
    plans = m.parse_power_schemes(text)
    assert len(plans) == 2
    assert plans[0]['name'] == 'Equilibrado' and plans[0]['active'] is True
    assert plans[1]['name'] == 'OEM Lenovo rendimiento' and not plans[1]['active']
    assert m.parse_active_scheme('Aktiver Plan: 88888888-9999-aaaa-bbbb-cccccccccccc') == plans[1]['guid']


def test_049_powercfg_parser_rejects_empty_or_unsupported():
    m = _performance_module_for_tests()
    assert m.parse_power_schemes('No se encontraron planes') == []
    assert m.parse_active_scheme('sin resultado') is None
    assert m._guid('381b4222-unsafe; cmd /c del') is None


def test_049_power_change_only_existing_verified_and_can_restore(tmp_path):
    from unittest.mock import patch
    m = _performance_module_for_tests()
    first = '381b4222-f694-41f0-9685-ff5bb260df2e'
    second = '8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c'
    state = {'current': first}
    calls = []
    plans = [{'guid': first, 'name': 'Equilibrado', 'active': True},
             {'guid': second, 'name': 'Alto rendimiento', 'active': False}]
    def read():
        return {'available': True, 'activeGuid': state['current'], 'plans': plans}
    def command(args):
        calls.append(list(args))
        state['current'] = args[1]
        return True, '', ''
    with patch.object(m, '_backup_path', lambda: tmp_path/'backup.json'), \
         patch.object(m, 'read_performance', read), patch.object(m, '_cmd', command):
        assert m.apply_power_scheme('not-a-guid')[0] is False
        assert m.apply_power_scheme('99999999-9999-9999-9999-999999999999')[0] is False
        assert not calls
        ok, _ = m.apply_power_scheme(second)
        assert ok and calls == [['/setactive', second]]
        assert m._read_backup()['originalGuid'] == first
        ok, _ = m.restore_power_scheme()
        assert ok and calls[-1] == ['/setactive', first]
        assert m._read_backup() is None


def test_049_failed_powercfg_change_keeps_rollback(tmp_path):
    from unittest.mock import patch
    m = _performance_module_for_tests()
    first = '381b4222-f694-41f0-9685-ff5bb260df2e'
    second = '8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c'
    plans = [{'guid': first, 'name': 'Equilibrado'}, {'guid': second, 'name': 'Alto rendimiento'}]
    with patch.object(m, '_backup_path', lambda: tmp_path/'backup.json'), \
         patch.object(m, 'read_performance', lambda: {'available': True, 'activeGuid': first, 'plans': plans}), \
         patch.object(m, '_cmd', lambda args: (False, '', 'Permiso denegado')):
        ok, message = m.apply_power_scheme(second)
        assert not ok and 'no confirmó' in message
        assert m._read_backup()['originalGuid'] == first


def test_049_windows_powercfg_changes_require_confirmation():
    page = (UI/'HealthPage.qml').read_text(encoding='utf-8')
    src = (ROOT/'core'/'health'/'performance.py').read_text(encoding='utf-8')
    assert 'id: powerConfirmOverlay' in page
    assert 'pendingPowerGuid' in page and 'confirmPowerRestore' in page
    assert 'performanceHealth.applyPlan(selected)' in page
    assert 'performanceHealth.restorePrevious()' in page
    assert "['/setactive', chosen['guid']]" in src
    assert "['/setactive', original]" in src
    assert 'os.replace(tmp, target)' in src
    assert 'powercfg /duplicatescheme' not in src.lower()


def test_049_performance_migration_uses_real_or_na_and_hub_navigation():
    page = (UI/'HealthPage.qml').read_text(encoding='utf-8')
    main = (UI/'Main.qml').read_text(encoding='utf-8')
    app = (ROOT/'main.py').read_text(encoding='utf-8')
    assert '{key:"performance", title:"Rendimiento"' in page
    assert 'target:"performance"' in page
    assert 'visible: page.currentModule === "performance"' in page
    assert 'performanceHealth.refresh()' in page
    assert 'onClicked: page.currentModule = "hub"' in page
    assert 'text: "N/A — No hay sensor de limitación térmica confirmado"' in page
    assert 'FPS: N/A' in page
    assert 'window.selectedPage === "health_performance" ? "performance"' in main
    assert 'context.setContextProperty("performanceHealth", performance_health)' in app
    assert 'app.aboutToQuit.connect(performance_health.close)' in app


def test_049_probable_game_processes_do_not_claim_full_detection():
    m = _performance_module_for_tests()
    from unittest.mock import patch
    class Fake:
        def __init__(self, name, path, pid):
            self.info = {'name': name, 'exe': path, 'pid': pid}
    fake = [Fake('Game-Win64-Shipping.exe', r'C:\Steam\steamapps\common\Game\Binaries\Game-Win64-Shipping.exe', 201),
            Fake('easyanticheat.exe', r'C:\Steam\steamapps\common\Game\easyanticheat.exe', 202),
            Fake('notepad.exe', r'C:\Windows\System32\notepad.exe', 203)]
    with patch.object(m.psutil, 'process_iter', lambda attrs: iter(fake)):
        observed = m._detect_probable_games()
    assert len(observed) == 1 and observed[0]['source'] == 'Steam' and observed[0]['pid'] == 201


# REBUILD 051: tarjeta viva estilo Steam, datos del proceso y arte verificable.
def test_050_extracts_steam_title_appid_only_from_matching_manifest(tmp_path):
    m = _performance_module_for_tests()
    from unittest.mock import patch
    library = tmp_path / 'SteamLibrary' / 'steamapps'
    folder = library / 'common' / 'Juego_Real'
    folder.mkdir(parents=True)
    manifest = library / 'appmanifest_12345.acf'
    manifest.write_text('"AppState"\n{\n  "appid" "12345"\n  "name" "Mi juego real"\n  "installdir" "Juego_Real"\n}\n', encoding='utf-8')
    exe = folder/'Binaries'/'Win64'/'realgame.exe'
    assert m._steamapps_directory(str(exe)) == library
    assert m._installed_folder(str(exe), 'Steam') == 'Juego_Real'
    data = m._steam_manifest_details(str(library), 'Juego_Real')
    assert data == {'appid': '12345', 'name': 'Mi juego real'}
    assert m._steam_manifest_details(str(library), 'OtroJuego')['appid'] == ''
    assert m._steam_artwork(library, '12345') == ''
    assert m._steam_cover_urls('12345')[0].endswith('/12345/library_hero.jpg')
    cache = library.parent/'appcache'/'librarycache'
    cache.mkdir(parents=True)
    (cache/'12345_library_hero.jpg').write_bytes(b'JPEG' * 100)
    assert m._steam_artwork(library, '12345').startswith('file:')


def test_050_running_game_detection_uses_real_process_and_session(tmp_path):
    m = _performance_module_for_tests()
    from unittest.mock import patch
    import time
    library = tmp_path/'SteamLibrary'/'steamapps'
    folder = library/'common'/'Racing Game'
    folder.mkdir(parents=True)
    (library/'appmanifest_9988.acf').write_text('"appid" "9988"\n"name" "Gran Carrera"\n"installdir" "Racing Game"\n', encoding='utf-8')
    class Fake:
        def __init__(self, name, path, pid):
            self.info = {'name': name, 'exe': str(path), 'pid': pid, 'create_time': time.time()-127}
    items = [Fake('Game-Win64-Shipping.exe',folder/'Game-Win64-Shipping.exe', 451),
             Fake('easyanticheat.exe',folder/'easyanticheat.exe',452),
             Fake('steam.exe',folder/'steam.exe',453)]
    with patch.object(m.psutil, 'process_iter', lambda attrs: iter(items)):
        results = m._detect_probable_games()
    assert len(results) == 1
    assert results[0]['name'] == 'Gran Carrera'
    assert results[0]['appid'] == '9988'
    assert results[0]['source'] == 'Steam'
    assert results[0]['pid'] == 451
    assert results[0]['session'].startswith('00:02:')
    assert m._active_game(results)['active'] is True
    assert m._active_game([])['active'] is False


def test_050_game_card_no_invented_data_and_update_while_visible():
    health = (UI/'HealthPage.qml').read_text(encoding='utf-8')
    performance = (ROOT/'core'/'health'/'performance.py').read_text(encoding='utf-8')
    assert 'id: currentGameCard' in health and 'id: gameArtwork' in health
    assert 'Aún no hay juego activo' in health
    assert 'JUEGO EN EJECUCIÓN' in health
    assert 'performanceHealth.startGameWatch()' in health
    assert 'performanceHealth.stopGameWatch()' in health
    assert 'def _detect_probable_games():' in performance
    assert 'self._game_watch.setInterval(2500)' in performance
    assert 'startGameWatch(self, client="health")' in performance
    assert 'stopGameWatch(self, client="health")' in performance
    assert 'FPS: N/A' in health
    assert 'Game Boost: pendiente de migración' in health


def test_050_artwork_now_fetches_automatically_in_worker():
    code = (ROOT/'core'/'health'/'performance.py').read_text(encoding='utf-8')
    qml = (UI/'HealthPage.qml').read_text(encoding='utf-8')
    assert 'def _automatic_artwork(self, game):' in code
    assert 'self._art_future = self._executor.submit(_resolve_game_cover' in code
    assert 'self._automatic_artwork(_active_game(games))' in code
    assert 'def _detect_probable_games():' in code
    assert 'performanceHealth.loadOnlineArtwork()' not in qml
    assert 'Elegir portada' not in qml and 'FileDialog {' not in qml
    assert 'Se conserva el ícono' not in qml


def test_themes_module_exists_and_shell_palette_is_switchable():
    main_qml = (UI / "Main.qml").read_text(encoding="utf-8")
    themes_qml = (UI / "ThemesPage.qml").read_text(encoding="utf-8")
    app = (ROOT / "main.py").read_text(encoding="utf-8")
    assert 'id:"themes",label:"Temas",icon:"palette"' in main_qml
    assert 'window.selectedPage==="themes"?themesComponent' in main_qml
    assert 'readonly property string selectedThemeId: themeManager.themeId' in main_qml
    assert 'readonly property var themeCatalog: themeManager.themes' in main_qml
    assert 'themeManager.applyTheme(themeId)' in main_qml
    assert "self._store.setValue('theme/id', theme_id)" in app
    assert 'signal applyTheme(string themeId)' in themes_qml
    assert 'text: "Temas"' in themes_qml
    assert 'text: themeCard.active ? "Aplicado" : "Aplicar"' in themes_qml


def test_health_hub_icons_use_distinct_colors():
    qml = (UI / "HealthPage.qml").read_text(encoding="utf-8")
    for fragment in (
        'iconColor:"#4EDDC8"',
        'iconColor:"#58C8FF"',
        'iconColor:"#7EE08A"',
        'iconColor:"#F2B661"',
        'iconColor:"#5EE1D5"',
        'iconColor:"#B879FF"',
        'iconColor:"#FF82CF"',
    ):
        assert fragment in qml
    assert 'function moduleAccent(moduleKey)' in qml
    assert 'hubCard.modelData.iconColor' in qml


# REBUILD 053 — UI inmediata sin sondeo síncrono de 78 tweaks.
def test_053_tweaks_getter_does_not_query_registry_or_legacy(monkeypatch, tmp_path):
    module, _ = _fake_tweaks(monkeypatch)
    def forbidden(*args, **kwargs):
        raise AssertionError("No debe consultarse Windows durante construcción de la vista")
    monkeypatch.setattr(module, "_safe_read", forbidden)
    monkeypatch.setattr(module.legacy_engine, "detect_tweak", forbidden)
    manager = module.TweaksManager(backup=tmp_path / "backup.json")
    assert len(manager.options) == 78
    assert not any(item["available"] or item["canRestore"] for item in manager.options)
    assert all(item["status"] == "Comprobando…" for item in manager.options)
    assert manager.busy is False
    manager.close()


def test_053_refresh_runs_in_worker_and_commits_only_after_result(monkeypatch, tmp_path):
    import threading
    import time
    module, _ = _fake_tweaks(monkeypatch)
    manager = module.TweaksManager(backup=tmp_path / "backup.json")
    started, release = threading.Event(), threading.Event()
    result = [dict(item) for item in manager.options]
    result[0].update(status="Ajuste activo", available=True, active=True)
    def slow_probe():
        started.set()
        assert release.wait(timeout=5)
        return result
    monkeypatch.setattr(manager, "_collect_options", slow_probe)
    t0 = time.monotonic()
    manager.refresh()
    assert time.monotonic() - t0 < 0.5
    assert started.wait(timeout=1)
    assert manager.busy and manager.options[0]["status"] == "Comprobando…"
    release.set()
    assert manager._future.result(timeout=5) is result
    manager._finish_if_ready()
    assert not manager.busy
    assert manager.options[0]["active"] is True
    manager.close()


def test_053_virtualized_cards_are_offscreen_safe():
    qml = (UI / "TweaksPage.qml").read_text(encoding="utf-8")
    manager = (ROOT / "core" / "tweaks" / "tweaks.py").read_text(encoding="utf-8")
    assert "ListView {" in qml and "model: page.displayRows" in qml
    assert "cacheBuffer: 280" in qml
    assert 'enabled:!tweaks.busy && optionCard.opt.available' in qml
    assert "ThreadPoolExecutor(max_workers=1" in manager
    assert "self._executor.submit(self._collect_options)" in manager
    assert "self._cached_options" in manager
    assert "app.aboutToQuit.connect(tweaks.close)" in (ROOT / "main.py").read_text(encoding="utf-8")


def test_053_reopen_skips_recently_verified_refresh(monkeypatch, tmp_path):
    import time
    module, _ = _fake_tweaks(monkeypatch)
    manager = module.TweaksManager(backup=tmp_path / "prefs.json")
    manager._last_scan = time.monotonic()
    monkeypatch.setattr(manager, "refresh", lambda: (_ for _ in ()).throw(AssertionError("No recalcular")))
    manager.ensureFresh()
    manager.close()


# REBUILD 054 — Juegos Riot: identificación conservadora desde procesos reales.
def test_054_riot_signatures_require_real_game_paths():
    mod = _performance_module_for_tests()
    specs = (
        ('VALORANT-Win64-Shipping.exe', r'E:\Riot Games\VALORANT\live\ShooterGame\Binaries\Win64\VALORANT-Win64-Shipping.exe', 'VALORANT', 'En ejecución'),
        ('League of Legends.exe', r'D:\Games\League of Legends\Game\League of Legends.exe', 'League of Legends', 'En partida'),
        ('LeagueClient.exe', r'C:\Riot Games\League of Legends\LeagueClient.exe', 'League of Legends', 'Cliente abierto'),
        ('LoR.exe', r'C:\Riot Games\LoR\live\Game\LoR.exe', 'Legends of Runeterra', 'En ejecución'),
    )
    for name, path, expected, state in specs:
        detected = mod._riot_process_game(name, path)
        assert detected and detected[:2] == (expected, state)
    assert mod._riot_process_game('RiotClientServices.exe', r'C:\Riot Games\Riot Client\RiotClientServices.exe') is None
    assert mod._riot_process_game('VALORANT-Win64-Shipping.exe', r'C:\Temp\VALORANT-Win64-Shipping.exe') is None
    assert mod._riot_process_game('VALORANT-Win64-Shipping.exe', r'C:\Riot Games\VALORANT\live\ShooterGame\Binaries\Win64\fake.exe') is None


def test_054_riot_vanguard_and_riot_client_do_not_create_fake_games():
    mod = _performance_module_for_tests()
    from unittest.mock import patch
    import time
    class Fake:
        def __init__(self, name, path, pid):
            self.info = {'name': name, 'exe': path, 'pid': pid, 'create_time': time.time() - 40}
    fake = [
        Fake('RiotClientServices.exe', r'C:\Riot Games\Riot Client\RiotClientServices.exe', 150),
        Fake('RiotClientUx.exe', r'C:\Riot Games\Riot Client\UX\RiotClientUx.exe', 151),
        Fake('LeagueClientUx.exe', r'D:\Riot Games\League of Legends\LeagueClientUx.exe', 152),
        Fake('VALORANT.exe', r'D:\Riot Games\VALORANT\live\VALORANT.exe', 153),
        Fake('vgc.exe', r'C:\Program Files\Riot Vanguard\vgc.exe', 154),
        Fake('League of Legends.exe', r'C:\Users\Test\Downloads\League of Legends.exe', 155),
    ]
    with patch.object(mod.psutil, 'process_iter', lambda attrs: iter(fake)):
        assert mod._detect_probable_games() == []


def test_054_valorant_game_card_detects_real_process_and_session():
    mod = _performance_module_for_tests()
    from unittest.mock import patch
    import time
    class Fake:
        def __init__(self, name, path, pid):
            self.info = {'name': name, 'exe': path, 'pid': pid, 'create_time': time.time() - 143}
    fake = [
        Fake('RiotClientServices.exe', r'C:\Riot Games\Riot Client\RiotClientServices.exe', 1),
        Fake('VALORANT-Win64-Shipping.exe', r'D:\Riot Games\VALORANT\live\ShooterGame\Binaries\Win64\VALORANT-Win64-Shipping.exe', 2),
    ]
    with patch.object(mod.psutil, 'process_iter', lambda attrs: iter(fake)):
        found = mod._detect_probable_games()
    assert len(found) == 1
    game = found[0]
    assert game['name'] == 'VALORANT' and game['source'] == 'Riot Games'
    assert game['pid'] == 2 and game['state'] == 'En ejecución'
    assert game['session'].startswith('00:02:')
    assert game['artUrl'] == '' and game['appid'] == ''
    assert '_priority' not in game


def test_054_league_client_vs_real_match_priority_and_no_duplicate():
    mod = _performance_module_for_tests()
    from unittest.mock import patch
    import time
    now = time.time()
    class Fake:
        def __init__(self, name, path, pid, age):
            self.info = {'name': name, 'exe': path, 'pid': pid, 'create_time': now - age}
    client = Fake('LeagueClient.exe', r'C:\Riot Games\League of Legends\LeagueClient.exe', 19, 1800)
    match = Fake('League of Legends.exe', r'C:\Riot Games\League of Legends\Game\League of Legends.exe', 20, 200)
    with patch.object(mod.psutil, 'process_iter', lambda attrs: iter([client, match])):
        results = mod._detect_probable_games()
    assert len(results) == 1
    assert results[0]['pid'] == 20 and results[0]['state'] == 'En partida'
    assert results[0]['session'].startswith('00:03:')
    with patch.object(mod.psutil, 'process_iter', lambda attrs: iter([client])):
        results = mod._detect_probable_games()
    assert len(results) == 1 and results[0]['state'] == 'Cliente abierto'


def test_054_fallbacks_and_previous_stores_unchanged():
    mod = _performance_module_for_tests()
    from unittest.mock import patch
    import time
    class Fake:
        def __init__(self, name, path, pid):
            self.info = {'name': name, 'exe': path, 'pid': pid, 'create_time': time.time() - 40}
    games = [
        Fake('steamgame.exe', r'E:\SteamLibrary\steamapps\common\TestGame\steamgame.exe', 10),
        Fake('epicgame.exe', r'D:\Epic Games\Another Game\epicgame.exe', 11),
        Fake('VALORANT-Win64-Shipping.exe', r'F:\Riot Games\VALORANT\live\ShooterGame\Binaries\Win64\VALORANT-Win64-Shipping.exe', 12),
    ]
    with patch.object(mod.psutil, 'process_iter', lambda attrs: iter(games)):
        detected = mod._detect_probable_games()
    assert {x['source'] for x in detected} == {'Steam', 'Epic Games', 'Riot Games'}
    assert 'Riot Games' in mod._game_caption([])
    view = (UI/'HealthPage.qml').read_text(encoding='utf-8')
    assert 'Steam, Epic, Riot, EA app o Microsoft Store/Xbox' in view
    assert 'page.activeGame.state || "En ejecución"' in view
    assert 'page.activeGame.state === "Cliente abierto"' in view
    assert 'FPS: N/A' in view


# REBUILD 055 — diez temas persistentes y bandeja de sistema con RAM manual.
def test_055_theme_catalog_has_ten_distinct_complete_palettes():
    import ast
    src = (ROOT / 'main.py').read_text(encoding='utf-8')
    tree = ast.parse(src)
    assignments = [n for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'THEMES' for t in n.targets)]
    assert len(assignments) == 1
    themes = ast.literal_eval(assignments[0].value)
    assert len(themes) == 10
    assert len({x[0] for x in themes}) == 10
    assert len({x[3:7] for x in themes}) == 10
    assert len({x[7] for x in themes}) == 10
    for theme in themes:
        assert len(theme) == 13
        assert all(h.startswith('#') and len(h) == 7 for h in theme[3:])


def test_055_tray_close_restoration_and_confirmed_ram_shortcut():
    app = (ROOT / 'main.py').read_text(encoding='utf-8')
    main_qml = (UI / 'Main.qml').read_text(encoding='utf-8')
    cleanup_qml = (UI / 'CleanupPage.qml').read_text(encoding='utf-8')
    assert 'from PySide6.QtWidgets import QApplication' in app
    assert 'QSystemTrayIcon.isSystemTrayAvailable()' in app
    assert 'app.setQuitOnLastWindowClosed(False)' in app
    assert 'self._tray.setContextMenu(menu)' in app
    assert 'self._quitting = True' in app
    assert 'Limpieza completa de RAM…' in app
    # La acción de bandeja se ejecuta en segundo plano por conexión Python,
    # sin reabrir la ventana ni invocar la confirmación visual.
    assert 'ramCleanupRequested = Signal()' in app
    assert 'self.ramCleanupRequested.emit()' in app
    assert 'tray_controller.ramCleanupRequested.connect(start_tray_ram_cleanup)' in app
    assert 'cleanup.cleanRamDeepFromTray()' in app
    assert 'if (trayController.available && !trayController.quitRequested)' in main_qml
    assert 'close.accepted = false' in main_qml
    assert 'window.hide()' in main_qml
    assert 'onOpenRamCleanupRequested' not in main_qml
    assert 'function showRamDeepConfirmation()' in cleanup_qml
    assert 'onConfirmed: cleanup.cleanRamDeep()' in cleanup_qml


def test_055_ram_deep_partial_cannot_be_reported_as_full_success():
    source = (ROOT / 'core/maintenance/cleanup.py').read_text(encoding='utf-8')
    view = (UI / 'CleanupPage.qml').read_text(encoding='utf-8')
    assert "succeeded = result['attempted'] > 0 and result['completed'] == result['attempted']" in source
    assert "partially_completed = 0 < result['completed'] < result['attempted']" in source
    assert "self._data['resultPartial'] = partially_completed" in source
    assert 'id: ramPartial' in view and 'Limpieza parcialmente completada' in view
    assert 'if (result.resultPartial)' in view

# REBUILD 056 — ampliación de tiendas y arte local verificable.
def test_056_store_signatures_avoid_launchers_and_support_ea_xbox():
    mod = _performance_module_for_tests()
    assert mod._game_source(r'D:\EA Games\The Sims 4\Game\Bin\TS4_x64.exe', 'ts4_x64.exe') == 'EA app'
    assert mod._game_source(r'G:\Origin Games\Battlefield 4\bf4.exe', 'bf4.exe') == 'EA app'
    assert mod._game_source(r'E:\XboxGames\Starfield\Content\Starfield.exe', 'starfield.exe') == 'Microsoft Store / Xbox'
    assert mod._game_source(r'C:\Windows\System32\notepad.exe', 'notepad.exe') is None
    assert 'eadesktop.exe' in mod._EXCLUDED_NAMES
    assert 'gamelaunchhelper.exe' in mod._EXCLUDED_NAMES


def test_056_detect_new_stores_and_uses_real_executable_icon_on_missing_cover(monkeypatch):
    mod = _performance_module_for_tests()
    import time
    class Fake:
        def __init__(self, name, path, pid):
            self.info = {'name': name, 'exe': path, 'pid': pid, 'create_time': time.time()-100}
    processes = [
        Fake('eadesktop.exe', r'C:\Program Files\Electronic Arts\EA Desktop\EADesktop.exe', 1),
        Fake('TS4_x64.exe', r'D:\EA Games\The Sims 4\Game\Bin\TS4_x64.exe', 2),
        Fake('Starfield.exe', r'E:\XboxGames\Starfield\Content\Starfield.exe', 3),
        Fake('VALORANT-Win64-Shipping.exe', r'D:\Riot Games\VALORANT\live\ShooterGame\Binaries\Win64\VALORANT-Win64-Shipping.exe', 4),
        Fake('GamingServices.exe', r'C:\Program Files\WindowsApps\GamingServices.exe', 5),
    ]
    monkeypatch.setattr(mod.psutil, 'process_iter', lambda attrs: iter(processes))
    monkeypatch.setattr(mod, '_executable_artwork', lambda exe: 'file:///verified-exe-icon.png')
    got = mod._detect_probable_games()
    assert {i['source'] for i in got} == {'EA app', 'Microsoft Store / Xbox', 'Riot Games'}
    assert {i['name'] for i in got} == {'The Sims 4', 'Starfield', 'VALORANT'}
    assert all(i['artUrl'] == 'file:///verified-exe-icon.png' and i['artKind'] == 'icon' for i in got)


def test_056_xbox_package_manifest_name_and_image_are_local(tmp_path):
    mod = _performance_module_for_tests()
    pkg = tmp_path / 'WindowsApps' / 'Microsoft.ForzaHorizon5_1.2.3.0_x64__123'
    (pkg / 'Assets').mkdir(parents=True)
    logo = pkg / 'Assets' / 'GameLogo.png'
    logo.write_bytes(b'PNG' * 140)
    (pkg / 'AppxManifest.xml').write_text('''<?xml version="1.0"?>
<Package xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10"
  xmlns:uap="http://schemas.microsoft.com/appx/manifest/uap/windows10">
<Properties><DisplayName>Forza Horizon 5</DisplayName></Properties>
<Applications><Application Id="App" Executable="Game.exe">
<uap:VisualElements DisplayName="Forza Horizon 5" Square150x150Logo="Assets/GameLogo.png" />
</Application></Applications></Package>''', encoding='utf-8')
    exe = pkg / 'Game.exe'
    meta = mod._store_visual_manifest(str(exe))
    assert meta['isGame'] and meta['name'] == 'Forza Horizon 5'
    assert meta['cover'] == logo.resolve().as_uri()
    assert mod._game_source(str(exe), 'game.exe') == 'Microsoft Store / Xbox'
    assert mod._store_game_details(str(exe), 'Microsoft Store / Xbox')[:2] == ('Forza Horizon 5', logo.resolve().as_uri())


def test_056_sidebar_collapsed_hover_is_animated_and_shows_tooltips():
    main = (UI / 'Main.qml').read_text(encoding='utf-8')
    health = (UI / 'HealthPage.qml').read_text(encoding='utf-8')
    for symbol in ('entryMouse', 'extraMouse', 'moreMouse'):
        assert f'window.sidebarCollapsed && {symbol}.containsMouse ? 1.20 : 1.0' in main
    assert main.count('Behavior on scale { NumberAnimation { duration:145; easing.type:Easing.OutCubic } }') >= 3
    assert 'ToolTip.text:entry.modelData.label' in main
    assert 'ToolTip.text:extraEntry.modelData.label' in main
    assert 'page.activeGame.artKind === "icon" ? Image.PreserveAspectFit : Image.PreserveAspectCrop' in health
    assert 'Ícono local del juego' in health



# REBUILD 057 — Portadas panorámicas verificadas y privacidad por clic.
def test_057_riot_pages_are_exact_titles_and_https():
    m = _performance_module_for_tests()
    assert m._OFFICIAL_RIOT_PAGES['valorant'].startswith('https://playvalorant.com/')
    assert len(m._OFFICIAL_RIOT_PAGES) == 3
    assert m._safe_remote_url('https://playvalorant.com/en-us/', m._OFFICIAL_PAGE_HOSTS)
    assert not m._safe_remote_url('http://playvalorant.com/en-us/', m._OFFICIAL_PAGE_HOSTS)
    assert not m._safe_remote_url('https://playvalorant.com.evil.example/', m._OFFICIAL_PAGE_HOSTS)
    assert not m._safe_remote_url('file:///C:/Games/art.jpg', m._OFFICIAL_IMAGE_HOSTS)
    assert not m._safe_remote_url('https://attacker.invalid/image.jpg', m._OFFICIAL_IMAGE_HOSTS)

def test_057_riot_metadata_is_verified_and_only_fetched_by_explicit_call(monkeypatch, tmp_path):
    m = _performance_module_for_tests()
    call_urls = []
    def fake_get(url, hosts, limit=m._MAX_ART_BYTES):
        call_urls.append(url)
        if url.startswith('https://playvalorant.com/'):
            return b'<html><head><meta property="og:title" content="VALORANT - Riot Games"><meta property="og:image" content="https://images.contentstack.io/valorant/banner.jpg"></head></html>'
        if url.startswith('https://images.contentstack.io/'):
            return b'correct-banner'
        return None
    monkeypatch.setattr(m, '_get_limited_bytes', fake_get)
    monkeypatch.setattr(m, '_cached_cover', lambda *x: '')
    monkeypatch.setattr(m, '_cache_verified_image', lambda source, title, data: 'file:///cached-cover.png' if data == b'correct-banner' else '')
    assert call_urls == []  # ningún sondeo automático llama al proveedor remoto
    assert m._fetch_riot_cover('Riot Games', 'VALORANT') == 'file:///cached-cover.png'
    assert len(call_urls) == 2
    assert m._fetch_riot_cover('EA app', 'VALORANT') == ''
    assert m._fetch_riot_cover('Riot Games', 'Nombre inventado') == ''
    assert len(call_urls) == 2

def test_057_rejects_wrong_game_title_and_untrusted_image_domain(monkeypatch):
    m = _performance_module_for_tests()
    monkeypatch.setattr(m, '_cached_cover', lambda *x: '')
    responses = {
        'https://playvalorant.com/en-us/': b'<meta property="og:title" content="Other Game"><meta property="og:image" content="https://images.contentstack.io/b.jpg">',
        'https://www.leagueoflegends.com/en-us/': b'<meta property="og:title" content="League of Legends"><meta property="og:image" content="https://attacker.invalid/fake.jpg">',
    }
    monkeypatch.setattr(m, '_get_limited_bytes', lambda url, hosts, limit=m._MAX_ART_BYTES: responses.get(url))
    assert m._fetch_riot_cover('Riot Games', 'VALORANT') == ''
    assert m._fetch_riot_cover('Riot Games', 'League of Legends') == ''

def test_058_qml_no_manual_cover_controls_and_keeps_game_details():
    qml = (UI / 'HealthPage.qml').read_text(encoding='utf-8')
    src = (ROOT/'core'/'health'/'performance.py').read_text(encoding='utf-8')
    assert 'import QtQuick.Dialogs' not in qml
    assert 'FileDialog {' not in qml
    assert 'performanceHealth.setCustomArtwork' not in qml
    assert 'Buscar portada oficial' not in qml and 'Elegir portada' not in qml
    assert 'TIEMPO ACTIVO' in qml and 'ORIGEN' in qml
    assert 'page.activeGame.artKind === "icon"' in qml
    assert '_cached_cover(origin, title)' in src
    assert 'self._art_future = self._executor.submit(_resolve_game_cover' in src
    assert 'QImageReader' in src and 'size.width() >= 600 and size.height() >= 300' in src


def test_058_exact_store_name_matching_protects_other_games(monkeypatch):
    import json
    m = _performance_module_for_tests()
    seen = []
    def fetched(url, hosts, limit=m._MAX_ART_BYTES):
        seen.append(url)
        assert hosts == m._STEAM_SEARCH_HOSTS
        return json.dumps({'items':[
            {'name':'The Last of Us Part II', 'id':987},
            {'name':'The Last of Us Part I', 'id':555},
        ]}).encode()
    monkeypatch.setattr(m, '_get_limited_bytes', fetched)
    assert m._matching_store_appid('The Last of Us Part I') == '555'
    assert m._matching_store_appid('The Last of Us') == ''
    assert seen and 'storesearch/' in seen[0]
    assert m._matching_store_appid('') == ''


def test_058_auto_cover_resolver_uses_verified_sources_only(monkeypatch):
    m = _performance_module_for_tests()
    monkeypatch.setattr(m, '_cached_cover', lambda *a: '')
    monkeypatch.setattr(m, '_fetch_riot_cover', lambda s,n: 'file:///riot.png' if n == 'VALORANT' else '')
    monkeypatch.setattr(m, '_matching_store_appid', lambda n: '555' if n == 'The Last of Us Part I' else '')
    monkeypatch.setattr(m, '_fetch_steam_cover', lambda s,n,appid: f'file:///{s}-{appid}.png')
    assert m._resolve_game_cover('Riot Games','VALORANT','') == 'file:///riot.png'
    assert m._resolve_game_cover('EA app','The Last of Us Part I','') == 'file:///EA app-555.png'
    assert m._resolve_game_cover('Epic Games','Unlisted Game','') == ''
    assert m._resolve_game_cover('Steam','Some Game','123') == 'file:///Steam-123.png'
    assert m._resolve_game_cover('Unknown','Other','') == ''


def test_058_auto_lookup_never_repeats_for_each_scan(monkeypatch):
    from concurrent.futures import Future
    m = _performance_module_for_tests()
    class Executor:
        def __init__(self): self.calls = []
        def submit(self, fn, *args):
            self.calls.append(args)
            result = Future()
            result.set_result('file:///verified.png')
            return result
    class Timer:
        def __init__(self): self.started = 0; self.stopped = 0
        def start(self): self.started += 1
        def stop(self): self.stopped += 1
    obj = object.__new__(m.PerformanceHealth)
    obj._closed = False
    obj._art_future = None
    obj._art_attempts = {}
    obj._executor = Executor()
    obj._art_poll = Timer()
    obj._data = {'activeGame':{'active':True,'source':'Riot Games','name':'VALORANT','pid':99,'appid':'','artKind':'icon'},'probableGames':[]}
    game = obj._data['activeGame']
    obj._automatic_artwork(game)
    assert obj._executor.calls == [('Riot Games','VALORANT','')]
    assert obj._art_poll.started == 1
    obj._finish_artwork()
    assert obj._data['activeGame']['artKind'] == 'cover'
    assert obj._data['activeGame']['artUrl'] == 'file:///verified.png'
    obj._data['activeGame']['artKind'] = 'icon'
    obj._art_future = None
    obj._automatic_artwork(obj._data['activeGame'])
    assert len(obj._executor.calls) == 1


def test_058_rejects_untrusted_redirect_and_ambiguous_titles(monkeypatch):
    import json
    m = _performance_module_for_tests()
    monkeypatch.setattr(m, '_get_limited_bytes', lambda *a, **k: json.dumps({'items': [
        {'name':'Exact Name','id':123},{'name':'Exact Name','id':456}
    ]}).encode())
    assert m._matching_store_appid('Exact Name') == ''
    assert not m._safe_remote_url('https://store.steampowered.com.evil.org/api/storesearch/', m._STEAM_SEARCH_HOSTS)
    assert not m._safe_remote_url('http://store.steampowered.com/api/storesearch/', m._STEAM_SEARCH_HOSTS)


def test_059_account_menu_opens_below_button():
    main = (UI / "Main.qml").read_text(encoding="utf-8")
    glyph = (UI / "Glyph.qml").read_text(encoding="utf-8")
    assert "id:accountButton" in main and "id:accountMenu" in main
    assert "y:accountButton.height+8" in main  # lista debajo del botón
    assert "Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent" in main
    assert 'kind:"user";ink:"#F5F8FD"' in main
    assert 'text:"Usuario"' not in main and 'text:"U";' not in main
    for kind in ("user", "login", "user_plus", "logout"):
        assert f'case "{kind}":' in glyph



# REBUILD 060: inicio de sesión de la app a través de la web (código de un solo uso + 127.0.0.1).
def _cuenta_module_for_tests():
    import importlib.util
    import sys
    import types
    qt = types.ModuleType("PySide6")
    core = types.ModuleType("PySide6.QtCore")
    gui = types.ModuleType("PySide6.QtGui")
    class StubSignal:
        def __init__(self, *a, **kw):
            self.emitted = 0
        def emit(self, *a, **kw):
            self.emitted += 1
        def connect(self, *a, **kw):
            pass
    core.QObject = type("QObject", (), {"__init__": lambda self, *a, **kw: None})
    core.Signal = lambda *args, **kwargs: StubSignal()
    core.Slot = lambda *args, **kwargs: (lambda fn: fn)
    core.Property = lambda *args, **kwargs: (lambda fn: property(fn))
    core.QTimer = type("QTimer", (), {"__init__": lambda self, *a: None, "setInterval": lambda self, v: None, "start": lambda self: None, "stop": lambda self: None, "timeout": StubSignal()})
    core.QUrl = lambda u: u
    abiertas = []
    gui.QDesktopServices = type("QDesktopServices", (), {"openUrl": staticmethod(lambda u: abiertas.append(u))})
    qt.QtCore, qt.QtGui = core, gui
    saved = {k: sys.modules.get(k) for k in ("PySide6", "PySide6.QtCore", "PySide6.QtGui")}
    sys.modules.update({"PySide6": qt, "PySide6.QtCore": core, "PySide6.QtGui": gui})
    try:
        spec = importlib.util.spec_from_file_location("cuenta_test", ROOT / "core" / "cuenta.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
    module._abiertas = abiertas
    return module


def test_060_web_base_only_https_or_localhost(monkeypatch):
    m = _cuenta_module_for_tests()
    monkeypatch.delenv("COREPULSE_WEB", raising=False)
    assert m.web_base() == "https://corepulse.cl"
    for malo in ("http://evil.example", "https://user@evil.example", "ftp://x", "https://corepulse.example/ruta", "javascript:alert(1)"):
        monkeypatch.setenv("COREPULSE_WEB", malo)
        assert m.web_base() == m.WEB_PREDETERMINADA
    monkeypatch.setenv("COREPULSE_WEB", "http://localhost:3000/")
    assert m.web_base() == "http://localhost:3000"


def test_060_pkce_pair_and_connect_url():
    import hashlib
    import re
    from urllib.parse import parse_qs, urlparse
    m = _cuenta_module_for_tests()
    verificador, reto = m.nuevo_par_pkce()
    assert re.fullmatch(r"[A-Za-z0-9_-]{43,128}", verificador)
    assert reto == hashlib.sha256(verificador.encode()).hexdigest()
    url = urlparse(m.url_conectar("https://web.example", 54321, "estado-1234567890ab", reto))
    q = parse_qs(url.query)
    assert url.path == "/app/conectar" and q["puerto"] == ["54321"] and q["reto"] == [reto]
    assert verificador not in m.url_conectar("https://web.example", 54321, "estado-1234567890ab", reto)


def _llamar_vuelta(servidor, ruta):
    import threading
    import urllib.request
    hilo = threading.Thread(target=servidor.servidor.handle_request)
    hilo.start()
    with urllib.request.urlopen(f"http://127.0.0.1:{servidor.puerto}{ruta}", timeout=5) as r:
        cuerpo = r.read().decode()
    hilo.join(5)
    return cuerpo


def test_060_loopback_server_checks_state_and_code():
    m = _cuenta_module_for_tests()
    codigo = "a" * 64
    s = m.ServidorVuelta("estado-correcto-123456")
    try:
        assert s.servidor.server_address[0] == "127.0.0.1"
        assert "no válido" in _llamar_vuelta(s, f"/callback?codigo={codigo}&estado=otro-estado-1234567")
        assert s.resultado is None
        assert "Sesión iniciada" in _llamar_vuelta(s, f"/callback?codigo={codigo}&estado=estado-correcto-123456")
        assert s.resultado == {"codigo": codigo}
    finally:
        s.servidor.server_close()
    s2 = m.ServidorVuelta("estado-correcto-123456")
    try:
        _llamar_vuelta(s2, "/callback?error=cancelado&estado=estado-correcto-123456")
        assert s2.resultado == {"error": "cancelado"}
    finally:
        s2.servidor.server_close()


def test_060_login_flow_exchanges_code_with_verifier(monkeypatch):
    import threading
    m = _cuenta_module_for_tests()
    llamadas = []
    def peticion(metodo, ruta, **kw):
        llamadas.append((metodo, ruta, kw.get("cuerpo")))
        return 200, {"token": "b" * 64, "perfil": {"email": "a@b.c", "nombre": "Agus", "plan": "free"}}
    monkeypatch.setattr(m, "_peticion", peticion)
    class Servidor:
        def esperar(self, cancelado):
            return {"codigo": "c" * 64}
    r = m._flujo_login(Servidor(), "verificador-secreto", threading.Event())
    assert r["token"] == "b" * 64 and r["perfil"]["nombre"] == "Agus"
    assert llamadas == [("POST", "/api/app/token", {"codigo": "c" * 64, "verificador": "verificador-secreto"})]
    monkeypatch.setattr(m, "_peticion", lambda *a, **k: (401, {"error": "codigo_invalido"}))
    assert m._flujo_login(Servidor(), "v", threading.Event()) == {"error": "codigo"}
    class Cancelado:
        def esperar(self, cancelado):
            return {"error": "cancelado"}
    assert m._flujo_login(Cancelado(), "v", threading.Event()) == {"error": "cancelado"}


def test_060_session_storage_never_plaintext_outside_windows(monkeypatch, tmp_path):
    m = _cuenta_module_for_tests()
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr(m.os, "name", "posix")
    assert m.guardar_sesion("d" * 64, {"plan": "free"}) is False
    assert not (tmp_path / "CorePulse" / "cuenta.dat").exists()
    assert m.leer_sesion() is None
    src = (ROOT / "core" / "cuenta.py").read_text(encoding="utf-8")
    assert "CryptProtectData" in src and "CRYPTPROTECT_UI_FORBIDDEN" in src


def test_060_wiring_and_menu_actions():
    main_py = (ROOT / "main.py").read_text(encoding="utf-8")
    qml = (UI / "Main.qml").read_text(encoding="utf-8")
    assert "from core.cuenta import CuentaManager" in main_py
    assert 'context.setContextProperty("cuenta", cuenta)' in main_py
    assert "app.aboutToQuit.connect(cuenta.close)" in main_py
    assert "cuenta.sesionIniciada.connect(tray_controller.restore)" in main_py
    for accion in ("cuenta.iniciarSesion()", "cuenta.cancelar()", "cuenta.cerrarSesion()", "cuenta.abrirWeb(option.path)"):
        assert accion in qml
    assert "accountWebBase" not in qml and "próximamente" not in qml
    assert 'type:"password"' not in qml.lower() and "echoMode" not in qml  # la contraseña nunca se escribe en la app


# REBUILD 061: la app usa el dominio propio.
def test_061_app_uses_own_domain():
    src = (ROOT / "core" / "cuenta.py").read_text(encoding="utf-8")
    assert 'WEB_PREDETERMINADA = "https://corepulse.cl"' in src
    assert "onrender.com" not in src


# REBUILD 062: gráfico de rendimiento con movimiento continuo y curva monótona.
def test_062_history_chart_smooth_and_honest():
    qml = (UI / "HistoryChart.qml").read_text(encoding="utf-8")
    # Deslizamiento continuo entre muestras, sincronizado con el muestreo de 1 s.
    assert "NumberAnimation" in qml and 'property: "advance"' in qml
    assert "duration: history.sampleMs" in qml and "Easing.Linear" in qml
    assert "onAdvanceChanged: chart.requestPaint()" in qml
    telemetry = (ROOT / "core" / "monitoring" / "telemetry.py").read_text(encoding="utf-8")
    assert "self._timer.setInterval(1000)" in telemetry and "[-60:]" in telemetry
    # Curva monótona (Fritsch–Carlson): sin picos inventados ni valores fuera de 0–100 %.
    assert "bezierCurveTo" in qml and "s > 9" in qml and "d[k-1]*d[k] <= 0 ? 0" in qml
    assert "v >= 0 && v <= 100" in qml
    # Las lecturas N/A siguen cortando la línea (no se inventa continuidad).
    assert "strokeRun(run); run = []" in qml
    assert "c.clip()" in qml
    assert "Math.random" not in qml


# REBUILD 065 — Pruebas de IA importadas de la rama de chat ampliado.

def test_059_ai_native_page_integrated_without_other_page_changes():
    from core import ai
    main = (UI / "Main.qml").read_text(encoding="utf-8")
    page = (UI / "AIPage.qml").read_text(encoding="utf-8")
    app = (ROOT / "main.py").read_text(encoding="utf-8")
    assert 'window.selectedPage==="ai"?aiComponent:' in main
    assert 'AIPage { onGoBack:window.selectedPage="summary" }' in main
    assert 'context.setContextProperty("corepulseAI", corepulse_ai)' in app
    assert 'app.aboutToQuit.connect(corepulse_ai.close)' in app
    assert 'id: keyInput' in page and 'echoMode: TextInput.Password' in page
    assert 'corepulseAI.enable(!page.info.enabled)' in page
    assert 'corepulseAI.allowQuestions(checked)' in page
    assert 'corepulseAI.allowHardware(checked)' in page
    assert 'corepulseAI.connectCloud()' in page
    assert 'textFormat: Text.PlainText' in page
    assert ai.GROQ_MODEL == 'openai/gpt-oss-120b'


def test_059_ai_hardware_snapshot_requires_explicit_opt_in_and_minimizes_data():
    from core.ai import authorized_snapshot
    metrics = {"computer": "PRIVATE-HOST", "cpuName": "Ryzen 7 5800H", "gpuName": "RTX 3060",
               "cpuTemp": 83.5, "cpuTempSource": "LibreHardwareMonitor", "gpuTemp": None,
               "cpuPercent": 36.0, "ramPercent": 79.3, "diskPercent": 92,
               "diskHealth": "Healthy", "serial": "SECRET", "fps": 999, "drive": "C:\\secret"}
    assert authorized_snapshot(metrics, False) == {}
    result = authorized_snapshot(metrics, True)
    assert result["cpuTemp"] == 83.5
    assert result["gpuTemp"] == "N/A"
    assert result["fps"] == "N/A" and result["diskHealth"] == "N/A"
    assert "computer" not in result and "serial" not in result and "drive" not in result
    assert "PRIVATE-HOST" not in str(result) and "SECRET" not in str(result)


def test_059_ai_missing_sensor_zero_nan_and_unverified_source_becomes_na():
    from core.ai import authorized_snapshot
    result = authorized_snapshot({"cpuTemp": 0, "gpuTemp": float("nan"),
                                  "cpuPercent": 120, "ramPercent": float("inf"),
                                  "diskPercent": -3}, True)
    assert all(result[k] == "N/A" for k in ("cpuTemp", "gpuTemp", "cpuPercent", "ramPercent", "diskPercent"))
    result = authorized_snapshot({"cpuTemp": 91, "cpuTempSource": "N/A"}, True)
    assert result["cpuTemp"] == "N/A"


def test_059_prompt_without_telemetry_does_not_claim_system_measurements():
    from core.ai import make_messages
    messages = make_messages("Quiero un tutorial preventivo", {})
    assert len(messages) == 3
    assert messages[2]["content"] == "Quiero un tutorial preventivo"
    assert "NO autorizó" in messages[1]["content"]
    assert "No inventes mediciones" in messages[0]["content"]
    assert "modificado Windows" in messages[0]["content"]
    assert "REAL_OR_NA" not in str(messages[2])  # pregunta sin instrucciones inyectadas


def test_059_guard_rejects_unbacked_numeric_metrics_and_keeps_valid_measures():
    from core.ai import reject_unbacked_measures
    assert reject_unbacked_measures("CPU: 97 °C", {})
    assert reject_unbacked_measures("GPU: 89 °C", {"gpuTemp": "N/A"})
    assert reject_unbacked_measures("RAM 97%", {"ramPercent": 71})
    assert reject_unbacked_measures("FPS: 60 fps", {})
    assert not reject_unbacked_measures("CPU: 72 °C", {"cpuTemp": 72.0})
    assert not reject_unbacked_measures("Consejo general: limpia el polvo sin líquidos.", {})


def test_059_provider_client_uses_https_fixed_model_and_blocks_redirects():
    from core.ai import ModelGateway, NoRedirect, GROQ_TARGET, USER_AGENT
    from urllib.request import Request
    import pytest
    assert GROQ_TARGET == "CorePulse/AI/BackendGroqKey"
    assert "Python-urllib" not in USER_AGENT
    for bad in ("http://api.groq.com", "https://user:password@example.org", "https://api.groq.com/v1?key=abc"):
        with pytest.raises(ValueError): ModelGateway(bad)
    assert NoRedirect().redirect_request(Request("https://a.example/"), None, 302, "Redirect", {}, "https://x.example/") is None


def test_059_groq_probe_and_chat_use_same_authorized_client_without_local_model():
    from core.ai import ModelGateway, make_messages, GROQ_MODEL, USER_AGENT
    import json
    class FakeResponse:
        status = 200
        def __init__(self, data): self.data = data
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, amount): return json.dumps(self.data).encode('utf8')
    class FakeOpener:
        calls = []
        def open(self, request, timeout):
            self.calls.append(request)
            if request.full_url.endswith('/models'):
                return FakeResponse({"data": [{"id": GROQ_MODEL}]})
            return FakeResponse({"choices": [{"message": {"content": "CPU N/A; FPS N/A"}}]})
    opener = FakeOpener()
    gateway = ModelGateway(opener=opener)
    assert gateway.probe("test-key")
    assert gateway.chat("test-key", make_messages("Hola", {})) == "CPU N/A; FPS N/A"
    assert len(opener.calls) == 2
    for req in opener.calls:
        assert req.get_header("Authorization") == "Bearer test-key"
        assert req.get_header("User-agent") == USER_AGENT
        assert req.full_url.startswith("https://api.groq.com/openai/v1/")
    body = json.loads(opener.calls[1].data)
    assert body['model'] == GROQ_MODEL and 'Lecturas autorizadas' not in str(body)


def test_059_missing_windows_store_does_not_save_in_plaintext(monkeypatch):
    from core import ai
    monkeypatch.setattr(ai, "_advapi32", lambda: None)
    assert ai.read_key() == ""
    assert ai.save_key("gsk_do_not_save") is False
    assert 'QSettings' not in (ROOT / "core" / "ai.py").read_text(encoding="utf-8")


def test_059_followup_context_uses_only_short_lived_authorized_history():
    from core.ai import make_messages
    history = [{"role": "user", "text": "Dame un tutorial de mantenimiento preventivo"},
               {"role": "assistant", "text": "Empieza revisando ventilaciones sin desmontar el equipo."}]
    messages = make_messages("¿Y para mi notebook?", {}, history)
    assert [m['role'] for m in messages] == ['system', 'system', 'user', 'assistant', 'user']
    assert messages[-1]['content'] == '¿Y para mi notebook?'
    assert messages[-2]['content'].startswith('Empieza revisando')
    assert "NO autorizó" in messages[1]['content']


def test_059_guard_blocks_claimed_cpu_gpu_readings_in_natural_language():
    from core.ai import reject_unbacked_measures
    assert reject_unbacked_measures("Tu GPU está a 86 °C", {})
    assert reject_unbacked_measures("Tu CPU tiene 94 °C", {"cpuTemp": "N/A"})


def test_059_ssd_occupancy_cannot_be_presented_as_smart_health():
    from core.ai import reject_unbacked_measures
    assert reject_unbacked_measures("SSD: salud 85%", {"diskPercent": 85})
    assert reject_unbacked_measures("Salud del disco: 90%", {"diskPercent": 90})


def test_060_markdown_table_with_html_breaks_becomes_readable_steps():
    from core.ai import readable_answer
    original = ("| Acción | Por qué ayuda | Cómo hacerlo (paso a paso) |\n"
                "| --- | --- | --- |\n"
                "| **Limpiar ventiladores** | Reduce polvo | 1. Apaga el PC.<br>2. Usa aire suave |\n"
                "| **Ventilación** | Evita bloqueos | 1. Colócalo sobre base rígida |")
    response = readable_answer(original)
    assert "Limpiar ventiladores" in response and "Reduce polvo" in response
    assert "Por qué ayuda: Reduce polvo" in response
    assert "1. Apaga el PC.\n2. Usa aire suave" in response
    assert "Ventilación" in response and "base rígida" in response
    assert "**" not in response and "<br>" not in response and "|" not in response


def test_060_simple_spanish_steps_preserve_real_numbers_and_na():
    from core.ai import readable_answer
    answer = "### Qué sé\n**CPU:** 35 °C<br>**GPU:** N/A\n- **Limpieza:** paso 1\n- **Aviso:** sin medición de FPS"
    response = readable_answer(answer)
    assert "CPU: 35 °C" in response and "GPU: N/A" in response
    assert "• Limpieza: paso 1" in response
    assert "###" not in response and "**" not in response


def test_060_safe_links_and_code_are_text_not_executable_html():
    from core.ai import readable_answer
    answer = 'Abre [la guía](https://example.org/manual), usa `msinfo32` y <b>lee</b>.<script>alert(1)</script>'
    result = readable_answer(answer)
    assert 'https://example.org/manual' in result and 'msinfo32' in result
    assert '<script>' not in result and '<b>' not in result
    assert 'alert(1)' in result  # solo texto; nunca se ejecuta en PlainText


def test_060_guard_runs_on_original_before_presentation():
    from core.ai import readable_answer, reject_unbacked_measures
    raw = '**CPU:** 97 °C<br>**GPU:** N/A'
    cleaned = readable_answer(raw)
    assert '97 °C' in cleaned
    assert reject_unbacked_measures(cleaned, {})
    source = (ROOT / 'core' / 'ai.py').read_text(encoding='utf-8')
    assert 'reject_unbacked_measures(text, evidence) or reject_unbacked_measures(normalized, evidence)' in source
    assert source.index('reject_unbacked_measures(normalized, evidence)') < source.index('"text": normalized')


def test_060_qml_messages_have_stable_hover_and_plain_text_layout():
    qml = (UI / 'AIPage.qml').read_text(encoding='utf-8')
    assert 'implicitWidth: compact ? 38 : Math.max(94, buttonLabel.implicitWidth + 28)' in qml
    assert 'Behavior on color' in qml
    assert 'scale:' not in qml and 'border.width: btn.hovered' not in qml
    assert 'textFormat: Text.PlainText' in qml
    assert 'id: speaker' in qml and 'id: messageText' in qml
    assert 'ScrollBar.vertical:' in qml
    assert 'corepulseAI.allowQuestions(checked)' in qml
    assert 'corepulseAI.allowHardware(checked)' in qml
    assert 'corepulseAI.connectCloud()' in qml
    assert 'echoMode: TextInput.Password' in qml


def test_060_two_column_metric_tables_cannot_bypass_na_guard():
    from core.ai import readable_answer, reject_unbacked_measures
    answer = '| Componente | Lectura |\n| --- | --- |\n| CPU | 97 °C |'
    normalized = readable_answer(answer)
    assert 'CPU: 97 °C' in normalized
    assert reject_unbacked_measures(normalized, {})
    assert not reject_unbacked_measures(normalized, {'cpuTemp': 97.0})


def test_061_ai_page_no_unsupported_select_by_mouse_on_text():
    source = (UI / "AIPage.qml").read_text(encoding="utf-8")
    assert "selectByMouse:" not in source
    assert "textFormat: Text.PlainText" in source
    assert "wrapMode: Text.WrapAtWordBoundaryOrAnywhere" in source
    assert "text: bubble.modelData.text" in source
    assert "component ActionButton: Button" in source


def test_061_main_qml_still_loads_ai_page_and_labels_new_release():
    qml = (UI / "Main.qml").read_text(encoding="utf-8")
    assert 'AIPage { onGoBack:window.selectedPage="summary" }' in qml
    assert 'title:"CorePulse — Rebuild 107"' in qml


def test_062_both_controllers_wired_and_closed():
    launcher = (ROOT / "main.py").read_text(encoding="utf-8")
    qml = (UI / "Main.qml").read_text(encoding="utf-8")
    assert 'from core.cuenta import CuentaManager' in launcher
    assert 'from core.ai import make_ai_controller' in launcher
    assert 'context.setContextProperty("cuenta", cuenta)' in launcher
    assert 'context.setContextProperty("corepulseAI", corepulse_ai)' in launcher
    assert 'app.aboutToQuit.connect(cuenta.close)' in launcher
    assert 'app.aboutToQuit.connect(corepulse_ai.close)' in launcher
    assert 'cuenta.sesionIniciada.connect(tray_controller.restore)' in launcher
    assert 'window.selectedPage==="ai"?aiComponent:' in qml
    assert 'AIPage { onGoBack:window.selectedPage="summary" }' in qml
    assert 'id:accountMenu' in qml and 'cuenta.iniciarSesion()' in qml


def test_062_credentials_and_approval_remain_independent():
    ai = (ROOT / "core" / "ai.py").read_text(encoding="utf-8")
    cuenta = (ROOT / "core" / "cuenta.py").read_text(encoding="utf-8")
    page = (UI / "AIPage.qml").read_text(encoding="utf-8")
    assert 'CorePulse/AI/BackendGroqKey' in ai
    assert 'cuenta.dat' in cuenta
    assert 'corepulseAI.allowQuestions(checked)' in page
    assert 'corepulseAI.allowHardware(checked)' in page
    assert 'cuenta.conectado' not in page
    assert 'GROQ_API_KEY' not in cuenta


def test_062_account_icons_are_preserved():
    glyph = (UI / "Glyph.qml").read_text(encoding="utf-8")
    for kind in ('login','logout','user','user_plus'):
        assert f'case "{kind}":' in glyph


def test_062_rules_and_new_version_are_present():
    root = ROOT
    assert (root / "Reglas para crear Versiones nuevas.txt").is_file()
    assert (root / "versiones" / "HISTORIAL.md").is_file()
    assert 'Rebuild 107' in (UI / "Main.qml").read_text(encoding="utf-8")


def test_063_ai_controls_use_customizable_basic_style_without_global_override():
    page = (UI / "AIPage.qml").read_text(encoding="utf-8")
    launcher = (ROOT / "main.py").read_text(encoding="utf-8")
    main = (UI / "Main.qml").read_text(encoding="utf-8")
    assert "import QtQuick.Controls.Basic\n" in page
    assert "import QtQuick.Controls\n" not in page
    assert "import QtQuick.Controls\n" in main  # Estilo normal de otras pestañas.
    for declaration in ("component ActionButton: Button", "component ConsentCheck: CheckBox",
                        "background: Rectangle", "contentItem: Text", "indicator: Rectangle"):
        assert declaration in page
    assert "QQuickStyle.setStyle(" not in launcher
    assert "QT_QUICK_CONTROLS_STYLE" not in launcher
    assert "selectByMouse:" not in page


def test_063_ai_style_does_not_change_login_controller_or_telemetry():
    main = (UI / "Main.qml").read_text(encoding="utf-8")
    bootstrap = (ROOT / "main.py").read_text(encoding="utf-8")
    assert 'id:accountMenu' in main
    assert 'window.selectedPage==="ai"?aiComponent:' in main
    assert 'context.setContextProperty("cuenta", cuenta)' in bootstrap
    assert 'context.setContextProperty("corepulseAI", corepulse_ai)' in bootstrap
    assert 'app.aboutToQuit.connect(cuenta.close)' in bootstrap
    assert 'app.aboutToQuit.connect(corepulse_ai.close)' in bootstrap


def test_064_chat_uses_available_height_and_readable_text():
    qml = (UI / "AIPage.qml").read_text(encoding="utf-8")
    assert 'Layout.fillWidth: true; Layout.fillHeight: true' in qml
    assert 'Layout.minimumHeight: page.height >= 620 ? 220 : (page.height >= 510 ? 170 : 115)' in qml
    assert 'property int chatFontSize: 16' in qml
    assert 'font.pixelSize: page.chatFontSize' in qml
    assert 'lineHeight: 1.33' in qml
    assert 'text: "A−"' in qml and 'text: "A+"' in qml
    assert 'page.chatFontSize = Math.max(14' in qml
    assert 'page.chatFontSize = Math.min(19' in qml
    assert 'ScrollBar.vertical: ScrollBar' in qml
    assert 'textFormat: Text.PlainText' in qml


def test_064_settings_collapse_when_connected_but_user_can_reopen():
    qml = (UI / "AIPage.qml").read_text(encoding="utf-8")
    assert 'property bool settingsExpanded: false' in qml
    assert '(page.settingsExpanded || !page.info.ready || page.editKey)' in qml
    assert 'visible: page.showSettings' in qml
    assert 'page.settingsExpanded = !page.settingsExpanded' in qml
    assert 'visible: page.info.enabled && page.info.ready' in qml
    assert 'corepulseAI.allowQuestions(checked)' in qml
    assert 'corepulseAI.allowHardware(checked)' in qml
    assert 'corepulseAI.enable(!page.info.enabled)' in qml
    assert 'corepulseAI.connectCloud()' in qml
    assert 'import QtQuick.Controls.Basic' in qml
    main = (UI / "Main.qml").read_text(encoding="utf-8")
    assert 'title:"CorePulse — Rebuild 107"' in main
    assert 'id:accountMenu' in main


# REBUILD 065: fusion real de Gráfico Fluido (Agustín) y Chat Ampliado (IA).
def test_065_agustin_chart_and_cloud_ai_coexist():
    graph = (UI / "HistoryChart.qml").read_text(encoding="utf-8")
    page = (UI / "AIPage.qml").read_text(encoding="utf-8")
    main = (UI / "Main.qml").read_text(encoding="utf-8")
    app = (ROOT / "main.py").read_text(encoding="utf-8")
    assert "NumberAnimation" in graph and "bezierCurveTo" in graph
    assert "strokeRun(run); run = []" in graph and "c.clip()" in graph
    assert "text: \"A−\"" in page and "text: \"A+\"" in page
    assert 'import QtQuick.Controls.Basic' in page
    assert 'window.selectedPage==="ai"?aiComponent:' in main
    assert 'context.setContextProperty("corepulseAI", corepulse_ai)' in app

def test_065_login_uses_agustin_domain_and_separate_groq_credentials():
    cuenta = (ROOT / "core/cuenta.py").read_text(encoding="utf-8")
    ai = (ROOT / "core/ai.py").read_text(encoding="utf-8")
    assert 'WEB_PREDETERMINADA = "https://corepulse.cl"' in cuenta
    assert 'CorePulse/AI/BackendGroqKey' in ai
    assert 'corepulse-web.onrender.com' not in cuenta
    assert 'GROQ_API_KEY' not in cuenta

def test_065_version_is_consolidated_without_parallel_backends():
    m = (ROOT / "main.py").read_text(encoding="utf-8")
    assert m.count('from core.cuenta import CuentaManager') == 1
    assert m.count('from core.ai import make_ai_controller') == 1
    assert m.count('app.aboutToQuit.connect(corepulse_ai.close)') == 1
    assert m.count('app.aboutToQuit.connect(cuenta.close)') == 1
    assert (ROOT / 'ui/AIPage.qml').is_file()


def test_overlay_page_exists_and_uses_real_metrics():
    qml = (UI / "OverlayPage.qml").read_text(encoding="utf-8")
    assert "overlayController.start()" in qml
    assert "telemetry && telemetry.metrics" in qml
    assert 'name:"FPS"' in qml
    assert 'value: "N/A"' in qml
    assert 'Sin fuente RTSS' in qml


# REBUILD 068: pruebas funcionales puras del contrato RTSS, sin requerir Windows/PySide6.
def _overlay_pure_functions():
    import re as std_re
    p = ROOT / 'core' / 'overlay.py'
    tree = ast.parse(p.read_text(encoding='utf-8'))
    names = {'parse_shortcut', '_format_metric', 'make_overlay_text'}
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    scope = {'re': std_re, 'MOD_ALT': 1, 'MOD_CONTROL': 2, 'MOD_SHIFT': 4, 'MOD_NOREPEAT': 0x4000,
             'VALID_KEY': std_re.compile(r'^(?:[A-Z0-9]|F(?:[1-9]|1[0-2]))$')}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(p), 'exec'), scope)
    return scope


def test_068_shortcut_parser_canonical_and_windows_masks():
    shortcut = _overlay_pure_functions()['parse_shortcut']
    assert shortcut('ctrl+shift+o') == ('Ctrl+Shift+O', 0x4000 | 0x0002 | 0x0004, 79)
    assert shortcut('Alt+Shift+F10') == ('Alt+Shift+F10', 0x4000 | 0x0001 | 0x0004, 0x79)
    assert shortcut('ctrl+Alt+SHIFT+1')[0] == 'Ctrl+Alt+Shift+1'


def test_068_invalid_shortcuts_rejected():
    import pytest
    shortcut = _overlay_pure_functions()['parse_shortcut']
    for broken in ('F9', 'Ctrl+R', 'Windows+Shift+O', 'Ctrl+Ctrl+O', 'Ctrl+Shift+F13', 'Alt+Shift+Tab', 'Ctrl+Shift+O+X'):
        with pytest.raises(ValueError): shortcut(broken)


def test_068_overlay_text_only_verified_readings_and_never_fake_fps():
    func = _overlay_pure_functions()['make_overlay_text']
    text = func({'cpuPercent': 25.5, 'gpuPercent': 50, 'ramPercent': 68.5, 'cpuTemp': None},
                {'active': True, 'name': 'VALORANT', 'source': 'Riot Games'})
    assert 'VALORANT' in text and 'CPU 26%' in text
    assert 'GPU 50%' in text and 'RAM 68%' in text
    assert 'FPS N/A' in text and 'N/A' in text
    assert 'FPS 0' not in text


def test_068_overlay_bindings_and_shared_memory_own_slot():
    app = (ROOT/'main.py').read_text(encoding='utf-8')
    qml = (UI/'OverlayPage.qml').read_text(encoding='utf-8')
    backend = (ROOT/'core/overlay.py').read_text(encoding='utf-8')
    manager = (ROOT/'core/health/performance.py').read_text(encoding='utf-8')
    assert 'OverlayController(telemetry, performance_health)' in app
    assert 'context.setContextProperty("overlayController", overlay_controller)' in app
    assert 'app.aboutToQuit.connect(overlay_controller.close)' in app
    assert 'overlayController.start()' in qml
    assert 'overlayController.hide()' in qml
    assert 'overlayController.setShortcut(' in qml
    assert 'RTSSSharedMemoryV2' in backend and 'OSD_OWNER = b"CorePulse"' in backend
    assert 'range(1, count)' in backend and 'owner == OSD_OWNER' in backend
    assert 'self._game_clients.add(' in manager and 'self._game_clients.discard(' in manager
    assert 'overlayController.setRtssPath(selectedFile.toString())' in qml


def test_068_new_overlay_not_preview_only_or_inert_shortcuts():
    qml = (UI/'OverlayPage.qml').read_text(encoding='utf-8')
    assert 'Keys.onPressed:' in qml
    assert 'shortcutCapture.forceActiveFocus()' in qml
    assert 'Overlay · ' not in qml  # label not duplicated
    assert 'Vista previa' in qml and 'RivaTuner Statistics Server' in qml


def test_069_rtss_sdk_header_offsets_and_publication_memory_reproduction():
    """Regression for V068: its +40 busy/+36 frame fields prevented OSD updates."""
    import ctypes
    import struct
    from types import SimpleNamespace

    source = (ROOT / "core" / "overlay.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "publish_osd")
    block = compile(ast.Module(body=[fn], type_ignores=[]), "overlay.py", "exec")

    memory = ctypes.create_string_buffer(10000)
    address = ctypes.addressof(memory)
    osd_offset = 64
    size = 4608
    signature = 0x52545353
    struct.pack_into('<9I', memory, 0, signature, 0x0002000E, 0, 0, 0, size, osd_offset, 2, 7)

    class Kernel:
        def OpenFileMappingW(self, *args): return 1
        def MapViewOfFile(self, *args): return address
        def UnmapViewOfFile(self, *args): return True
        def CloseHandle(self, *args): return True
        def InterlockedCompareExchange(self, ptr, target, expected):
            before = ptr.contents.value
            if before == expected: ptr.contents.value = target
            return before
        def InterlockedExchange(self, ptr, target):
            before = ptr.contents.value
            ptr.contents.value = target
            return before

    names = {
        'os': SimpleNamespace(name='nt'), 'ctypes': ctypes, 'struct': struct,
        '_api': lambda: Kernel(), '_mapped_region_size': lambda kernel, ptr: len(memory),
        'FILE_MAP_ALL_ACCESS': 0x000F001F, 'RTSS_MEMORY_NAME': 'RTSSSharedMemoryV2',
        'RTSS_SIGNATURE': signature, 'RTSS_BUSY_OFFSET': 36, 'RTSS_OSD_FRAME_OFFSET': 32,
        'OSD_OWNER': b'CorePulse',
    }
    exec(block, names)
    publish = names['publish_osd']
    assert publish('CPU 34%\nRAM 69%') is True
    assert struct.unpack_from('<I', memory, 32)[0] == 8
    assert struct.unpack_from('<I', memory, 36)[0] == 0
    assert struct.unpack_from('<I', memory, 40)[0] == 0
    slot_offset = osd_offset + size
    assert b'CorePulse' in memory.raw[slot_offset+256:slot_offset+300]
    assert b'CPU 34%' in memory.raw[slot_offset+512:slot_offset+600]
    # Renderer-busy guard must not overwrite or advance the OSD frame.
    struct.pack_into('<I', memory, 36, 1)
    assert publish('SHOULD NOT WRITE') is None
    assert struct.unpack_from('<I', memory, 32)[0] == 8
    struct.pack_into('<I', memory, 36, 0)
    assert publish('', clear=True) is True
    assert struct.unpack_from('<I', memory, 32)[0] == 9
    assert memory.raw[slot_offset+256:slot_offset+264] == b'\0' * 8


def test_069_network_module_comes_from_v485_and_preserves_na():
    source = (ROOT / "core" / "maintenance" / "network.py").read_text(encoding="utf-8")
    qml = (UI / "NetworkPage.qml").read_text(encoding="utf-8")
    main = (UI / "Main.qml").read_text(encoding="utf-8")
    app = (ROOT / "main.py").read_text(encoding="utf-8")
    assert 'def collect_network_identity():' in source
    assert 'def diagnose_network(identity=None, count=4):' not in source
    assert 'class NetworkTrafficSampler:' in source
    assert 'class NetworkHealth(QObject)' in source
    assert 'self._executor.submit(collect_network_identity)' in source
    assert 'self._executor.submit(diagnose_network, self._inventory, 2)' not in source
    assert 'window.selectedPage==="advanced_network"' in main
    assert 'NetworkPage { onGoBack:' in main
    assert 'context.setContextProperty("networkHealth", network_health)' in app
    assert 'networkHealth.startWatch()' in qml
    assert 'networkHealth.diagnose()' not in qml
    assert 'N/A' in source


def test_069_network_primary_missing_is_explicitly_na():
    source = (ROOT / "core" / "maintenance" / "network.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    fns = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in ('_display_value','_flatten_network')]
    env = {}
    exec(compile(ast.Module(body=fns, type_ignores=[]), 'network.py', 'exec'), env)
    empty = env['_flatten_network']({'adapters': [], 'primary_index': None, 'source': 'psutil'})
    assert empty['primary'] == 'N/A'
    assert empty['ipv4'] == 'N/A'
    assert empty['total'] == 0
    sample = env['_flatten_network']({'adapters': [{'name':'Wi-Fi','ipv4':['192.168.1.3'],
        'gateways':['192.168.1.1'], 'dns_servers':['1.1.1.1'],'is_up':True,
        'link_speed_mbps': 866.7}], 'primary_index':0,'source':'psutil'})
    assert sample['primary'] == 'Wi-Fi'
    assert sample['ipv4'] == '192.168.1.3'
    assert sample['linkSpeed'] == '867 Mbps'


def test_070_benchmark_is_real_and_has_no_gpu_illusion():
    engine = (ROOT / "core/benchmark.py").read_text(encoding="utf-8")
    qml = (UI / "BenchmarkPage.qml").read_text(encoding="utf-8")
    main = (UI / "Main.qml").read_text(encoding="utf-8")
    assert 'benchmarkController.start()' in qml
    assert 'benchmarkController.cancel()' in qml
    assert 'window.selectedPage==="benchmark"?benchmarkComponent' in main
    assert 'hashlib.sha256()' in engine
    assert 'os.fsync(f.fileno())' in engine
    assert 'GPU · Escena DirectX 11' in qml
    assert "'gpu': None" in engine and "'score': None" in engine
    assert 'NamedTemporaryFile' in engine and 'filename.unlink(missing_ok=True)' in engine


def test_070_rtss_launches_on_new_game_or_store_not_opening_overlay():
    overlay_py = (ROOT / "core/overlay.py").read_text(encoding="utf-8")
    overlay_qml = (UI / "OverlayPage.qml").read_text(encoding="utf-8")
    launch = (ROOT / "main.py").read_text(encoding="utf-8")
    assert 'QTimer.singleShot(0, overlay_controller.startAutoWatch)' in launch
    assert 'self._launch_baseline = observed' in overlay_py
    assert 'if previous is None:' in overlay_py
    assert 'if observed.difference(previous)' in overlay_py
    for executable in ['steam.exe','epicgameslauncher.exe','riotclientservices.exe','eadesktop.exe','xboxpcapp.exe']:
        assert executable in overlay_py
    assert 'overlayController.start()' not in overlay_qml.split('FileDialog {',1)[0]
    assert 'overlayController.start()' in overlay_qml


def test_070_disk_benchmark_records_actual_bytes_and_cleans_file(tmp_path):
    import ast, hashlib, os, threading, time, tempfile
    src = (ROOT / 'core/benchmark.py').read_text(encoding='utf-8')
    tree = ast.parse(src)
    needed = {'_speed','_ssd_workload'}
    items = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in needed]
    ns = {'Path': Path, 'hashlib': hashlib, 'os': os, 'time': time, 'tempfile': tempfile}
    exec(compile(ast.Module(body=items, type_ignores=[]), 'benchmark.py','exec'), ns)
    measured = ns['_ssd_workload'](threading.Event(), folder=str(tmp_path), size=64*1024)
    assert measured['bytesWritten'] == 65536
    assert measured['integrity'] == 'PASS'
    assert measured['writeMiBPerSecond'] > 0
    assert not list(tmp_path.glob('corepulse_bench_*'))


def test_070_cpu_and_ram_benchmarks_measure_work_done():
    import ast, threading, time
    src = (ROOT/'core/benchmark.py').read_text(encoding='utf-8')
    tree = ast.parse(src)
    names = {'_speed','_cpu_workload','_ram_workload'}
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    ns = {'time': time}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'benchmark.py','exec'),ns)
    cpu=ns['_cpu_workload'](0.01, threading.Event())
    ram=ns['_ram_workload'](0.01, threading.Event())
    assert cpu['operations'] >= 60000
    assert cpu['operationsPerSecond'] > 0
    assert ram['bytesCopied'] >= 8*1024*1024
    assert ram['mibPerSecond'] > 0
    cancelled=threading.Event();cancelled.set()
    assert ns['_cpu_workload'](0.01, cancelled) is None


def test_070_launcher_detection_uses_strict_names_not_windows_services():
    import ast
    source = (ROOT/'core/overlay.py').read_text(encoding='utf-8')
    tree=ast.parse(source)
    scanner=next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name=='_interesting_process')
    names=next(n for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id=='_LAUNCHER_EXES' for t in n.targets))
    ns={}
    exec(compile(ast.Module(body=[names,scanner], type_ignores=[]),'overlay.py','exec'),ns)
    detect=ns['_interesting_process']
    for name in ('Steam.exe','EpicGamesLauncher.exe','RiotClientServices.exe','EADesktop.exe','XboxPcApp.exe'):
        assert detect({'name':name, 'exe':''})
    for name in ('GamingServices.exe','WindowsExplorer.exe','SteamService.exe'):
        assert not detect({'name':name,'exe':''})


def test_071_gpu_directx_source_is_historical_and_subprocess_isolated():
    backend = (ROOT / 'core/benchmark_gpu.py').read_text(encoding='utf-8')
    scene = (ROOT / 'core/directx_scene.py').read_text(encoding='utf-8')
    runner = (ROOT / 'core/benchmark.py').read_text(encoding='utf-8')
    assert 'D3D11Renderer' in backend and 'run_directx_benchmark(' in backend
    assert 'render_frame(' in backend and 'present_ns=time.perf_counter_ns()' in backend
    assert 'wall_clock_deterministic' in backend
    for label in ("'avenue'", "'district'", "'skyline'", "'megacity'"):
        assert label in scene
    assert 'class SceneLevel' in scene and 'def level_workload(' in scene
    assert 'run_gpu_isolated(' in runner
    assert "'-m', 'core.benchmark_gpu'" in runner
    assert 'process.terminate()' in runner and 'process.kill()' in runner
    assert 'subprocess.Popen' in runner


def test_071_gpu_benchmark_ui_profiles_and_verified_scene_results():
    view = (UI / 'BenchmarkPage.qml').read_text(encoding='utf-8')
    assert 'benchmarkController.startGpu(page.gpuProfile)' in view
    assert 'benchmarkController.start()' in view
    assert 'benchmarkController.cancel()' in view
    for profile in ('quick', 'standard', 'extended'):
        assert profile in view
    assert 'sceneTile.reading.frames_per_s' in view
    assert 'sceneTile.reading.one_percent_low_fps' in view
    assert 'gpu.value' in view
    assert 'COREPULSE_REBUILD' not in view


def test_071_gpu_runner_reports_na_on_unsupported_platform(tmp_path):
    import subprocess, json, sys, platform
    if platform.system() == 'Windows':
        return
    output = tmp_path / 'gpu.json'
    completed = subprocess.run([sys.executable, '-B', '-m', 'core.benchmark_gpu',
                                '--profile', 'quick', '--output', str(output)],
                               cwd=str(ROOT), capture_output=True, text=True, timeout=15)
    assert completed.returncode == 0, completed.stderr
    data = json.loads(output.read_text(encoding='utf-8'))
    assert data['status'] == 'UNAVAILABLE' and data['value'] is None
    assert data['benchmark_method'].endswith('_DETERMINISTIC')


def _071_gpu_isolation_callable():
    """Extract only the subprocess worker to exercise IPC without Qt or D3D."""
    import ast, json, math, os, subprocess, sys, tempfile, threading, time
    from types import SimpleNamespace
    source = (ROOT / 'core/benchmark.py').read_text(encoding='utf-8')
    tree = ast.parse(source)
    method = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in ('run_gpu_isolated', '_run_gpu_child')]
    namespace = {'os': SimpleNamespace(name='nt', environ=dict(os.environ)),
                 'subprocess': subprocess, 'sys':sys, 'time':time,
                 'threading':threading, 'json':json, 'math':math,
                 'Path':Path, 'GPU_PROFILES':('quick','standard','extended'),
                 'GPU_METHOD':'COREPULSE_GPU_DIRECTX11_SCENES_V25_WALLCLOCK_DETERMINISTIC',
                 '_read_last_json': lambda filename: json.loads(Path(filename).read_text(encoding='utf-8'))}
    exec(compile(ast.Module(body=method, type_ignores=[]), 'benchmark.py', 'exec'),namespace)
    return namespace['run_gpu_isolated']


def test_071_gpu_subprocess_ipc_validates_real_scene_fields(tmp_path):
    import sys, threading
    root = tmp_path / 'mini'
    module_dir = root / 'core'
    module_dir.mkdir(parents=True)
    (module_dir / '__init__.py').write_text('',encoding='utf-8')
    child = module_dir / 'benchmark_gpu.py'
    child.write_text('''import argparse,json
p=argparse.ArgumentParser()
p.add_argument('--profile');p.add_argument('--output')
a=p.parse_args()
print(json.dumps({'event':'progress','progress':25,'stage':'Valle','detail':'Frames reales de prueba'}),flush=True)
keys=['valley','forest','lake'] if a.profile=='quick' else ['valley','forest','lake','extreme']
json.dump({'kind':'GPU','status':'OK','benchmark_method':'COREPULSE_GPU_DIRECTX11_SCENES_V25_WALLCLOCK_DETERMINISTIC',
'primary_scene':keys[-1],'value':60.0,'scenes':[{'key':k,'status':'OK','frames':120,'frames_per_s':60.0} for k in keys]},open(a.output,'w'))
''', encoding='utf-8')
    updates=[]
    result = _071_gpu_isolation_callable()('quick',threading.Event(),
                                             lambda done,total,label:updates.append((done,total,label)),
                                             python_path=sys.executable,script_path=child)
    assert result['status']=='OK' and result['primary_scene']=='lake'
    assert len(result['scenes']) == 3
    assert updates and updates[0][0]==25


def test_071_gpu_subprocess_rejects_incomplete_scenes(tmp_path):
    import sys, threading
    root=tmp_path/'mini'
    module_dir=root/'core';module_dir.mkdir(parents=True)
    (module_dir/'__init__.py').write_text('',encoding='utf-8')
    child=module_dir/'benchmark_gpu.py'
    child.write_text('''import argparse,json
p=argparse.ArgumentParser();p.add_argument('--profile');p.add_argument('--output');a=p.parse_args()
json.dump({'kind':'GPU','status':'OK','benchmark_method':'COREPULSE_GPU_DIRECTX11_SCENES_V25_WALLCLOCK_DETERMINISTIC',
'value':9999,'scenes':[{'key':'valley','status':'OK','frames':0,'frames_per_s':9999}]},open(a.output,'w'))
''',encoding='utf-8')
    result=_071_gpu_isolation_callable()('quick',threading.Event(),
                                           python_path=sys.executable,script_path=child)
    assert result['status']=='ERROR' and result['value'] is None


# --- Benchmark GPU V27-V29: medición, sensores, nombre del equipo y ciudad ---

def _072_module_constant(path, name):
    import ast
    tree = ast.parse((ROOT / path).read_text(encoding='utf-8'))
    node = next(n for n in tree.body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == name for t in n.targets))
    return ast.literal_eval(node.value)


def _072_functions(path, names, namespace):
    import ast
    tree = ast.parse((ROOT / path).read_text(encoding='utf-8'))
    nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.Assign)) and (
        getattr(n, 'name', None) in names or any(isinstance(t, ast.Name) and t.id in names for t in getattr(n, 'targets', [])))]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), path, 'exec'), namespace)
    return namespace


def _073_scene():
    import importlib.util, sys
    spec = importlib.util.spec_from_file_location('directx_scene_073', ROOT / 'core/directx_scene.py')
    scene = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = scene  # dataclasses necesita el módulo registrado
    spec.loader.exec_module(scene)
    return scene


def test_072_gpu_method_matches_between_runner_and_worker():
    # V26 entregaba un método que el runner (V25) rechazaba: ningún resultado se aceptaba.
    worker = _072_module_constant('core/benchmark_gpu.py', 'GPU_BENCHMARK_METHOD')
    runner = _072_module_constant('core/benchmark.py', 'GPU_METHOD')
    assert worker == runner and 'V29' in worker and 'NEON_CITY' in worker


def test_072_fps_uses_present_intervals_and_wall_clock():
    import math, statistics
    backend = (ROOT / 'core/benchmark_gpu.py').read_text(encoding='utf-8')
    assert 'frame_ms=(present_ns-last_present_ns)/1_000_000.0' in backend
    assert "'fps_method':'PRESENTED_FRAMES_DIV_WALLCLOCK'" in backend
    ns = _072_functions('core/benchmark_gpu.py', {'_fps_stats', '_percentile', '_bottleneck'},
                        {'math': math, 'statistics': statistics})
    assert abs(ns['_fps_stats']([4.0] * 100)['fps'] - 250.0) < 1e-9
    assert ns['_bottleneck'](10.0, 9.8, 1.0)['bottleneck'] == 'GPU'
    assert ns['_bottleneck'](10.0, 4.0, 1.0)['bottleneck'] == 'CPU_O_SISTEMA'
    assert ns['_bottleneck'](10.0, 9.8, 0.2)['bottleneck'] == 'N/A'


def test_072_render_resolution_fixed_and_high_performance_adapter():
    backend = (ROOT / 'core/benchmark_gpu.py').read_text(encoding='utf-8')
    assert 'self.width=min(self.width,sw)' not in backend
    assert 'SetProcessDpiAwarenessContext' in backend
    assert 'DXGI_GPU_PREFERENCE_HIGH_PERFORMANCE' in backend and 'FACTORY1_ENUM_ADAPTERS1' in backend
    assert 'D3D_DRIVER_TYPE_UNKNOWN if adapter else D3D_DRIVER_TYPE_HARDWARE' in backend
    assert _072_module_constant('core/benchmark_gpu.py', 'RENDER_WIDTH') == 1920
    assert _072_module_constant('core/benchmark_gpu.py', 'RENDER_HEIGHT') == 1080


def test_072_nvidia_session_parser_and_power_cap_is_not_throttling():
    import math, os, re
    ns = _072_functions('core/benchmark.py', {'_nv_number', 'parse_nvidia_session_line', '_pick_gpu_samples',
                                              'summarize_gpu_session', '_NVIDIA_THERMAL_BITS', '_NVIDIA_HW_BITS',
                                              '_NVIDIA_POWER_CAP'}, {'math': math, 'os': os, 're': re})
    parse = ns['parse_nvidia_session_line']
    row = parse('0, NVIDIA GeForce RTX 2080 SUPER, 71, 99, 1890, 2115, 248.10, 250.00, P0, 0x0000000000000004')
    assert row['temp_c'] == 71 and row['clock_mhz'] == 1890 and row['reasons'] == 0x4
    assert parse('0, NVIDIA GeForce RTX 3060 Laptop GPU, 80, 98, 1500, 2100, [N/A], [N/A], P0, 0x20')['power_w'] is None
    assert parse('Field "clocks_event_reasons.active" is not a valid field to query.') is None
    result = {'renderer': 'NVIDIA GeForce RTX 2080 SUPER', 'scenes': []}
    capped = [parse('0, NVIDIA GeForce RTX 2080 SUPER, 70, 99, 1900, 2115, 249, 250, P0, 0x4') for _ in range(20)]
    desk = ns['summarize_gpu_session'](result, capped, {'has_battery': False, 'power_plan': 'Equilibrado'}, {'has_battery': False})
    assert desk['stability'] == 'ESTABLE' and desk['device_class'] == 'ESCRITORIO' and desk['warnings'] == []
    hot = [parse('0, NVIDIA GeForce RTX 2080 SUPER, 88, 99, 1300, 2115, 200, 250, P0, 0x20') for _ in range(20)]
    assert ns['summarize_gpu_session'](result, hot, {}, {})['stability'] == 'THROTTLING'
    slow = [parse('0, NVIDIA GeForce RTX 2080 SUPER, 50, 100, 1200, 2115, 110, 250, P0, 0x1') for _ in range(20)]
    assert ns['summarize_gpu_session'](result, slow, {}, {})['stability'] == 'RELOJ_BAJO'
    mobile = [parse('0, NVIDIA GeForce RTX 3060 Laptop GPU, 75, 100, 1300, 2100, 80, 80, P0, 0x4') for _ in range(20)]
    assert ns['summarize_gpu_session']({'renderer': 'NVIDIA GeForce RTX 3060 Laptop GPU'}, mobile, {}, {})['stability'] == 'ESTABLE'


def test_072_notebook_battery_and_non_nvidia_are_reported_not_invented():
    import math, os, re
    ns = _072_functions('core/benchmark.py', {'_nv_number', 'parse_nvidia_session_line', '_pick_gpu_samples',
                                              'summarize_gpu_session', '_NVIDIA_THERMAL_BITS', '_NVIDIA_HW_BITS',
                                              '_NVIDIA_POWER_CAP'}, {'math': math, 'os': os, 're': re})
    laptop = {'has_battery': True, 'on_battery': True, 'battery_percent': 64.0, 'power_plan': 'Economizador de batería'}
    summary = ns['summarize_gpu_session']({'renderer': 'AMD Radeon RX 6600M', 'scenes': []}, [], laptop, laptop)
    assert summary['device_class'] == 'NOTEBOOK' and summary['on_battery'] and summary['stability'] == 'SIN_DATOS'
    assert summary['gpu_temp_max_c'] is None and summary['sensor_status'].startswith('N/A')
    assert 'batería' in ' '.join(summary['warnings']) and 'Economizador' in ' '.join(summary['warnings'])
    nvidia = ns['parse_nvidia_session_line']('0, NVIDIA GeForce RTX 3060 Laptop GPU, 60, 1, 300, 2100, 10, 80, P8, 0x1')
    intel = ns['summarize_gpu_session']({'renderer': 'Intel(R) Iris(R) Xe Graphics', 'scenes': []}, [nvidia], {}, {})
    assert intel['samples'] == 0 and intel['stability'] == 'SIN_DATOS'


def test_072_machine_name_ignores_smbios_placeholders():
    import platform, re
    ns = _072_functions('core/monitoring/telemetry.py', {'_SMBIOS_PLACEHOLDERS', '_VENDOR_SHORT', '_smbios_text',
                                                         '_short_vendor', 'describe_machine'}, {'re': re, 'platform': platform})
    describe = ns['describe_machine']
    built = {'SystemManufacturer': 'System manufacturer', 'SystemProductName': 'System Product Name',
             'BaseBoardManufacturer': 'ASUSTeK COMPUTER INC.', 'BaseBoardProduct': 'TUF Z390-PRO GAMING'}
    assert describe(built, 'AGT') == 'AGT · ASUS TUF Z390-PRO GAMING'
    assert describe({'SystemManufacturer': 'LENOVO', 'SystemProductName': '82JW'}, 'X') == 'Lenovo 82JW'
    assert describe({'SystemManufacturer': 'Default string', 'SystemProductName': 'Default string'}, '') == 'N/A'


def test_073_city_keeps_the_ring_boulevard_free_for_camera_and_traffic():
    import math
    scene = _073_scene()
    layout = scene.city_layout()
    inner, outer = scene.RING_INNER, scene.RING_OUTER
    half_lot_room = scene.CITY['lot'] * 1.5  # mitad de manzana: 3 lotes de 20
    for x, z, w, h, d, *_ in layout['buildings']:
        near, far = scene._rect_radial_range(x, z, w / 2.0, d / 2.0)
        assert not (near < outer and far > inner), (x, z)
        # Ningún edificio invade la calle: queda dentro de su manzana.
        for c, half in ((x, w / 2.0), (z, d / 2.0)):
            block = round(c / scene.PITCH) * scene.PITCH
            assert abs(c - block) + half <= half_lot_room + 1e-6, (x, z)
    tube = scene.CAMERA_TUBE
    for level in range(4):
        for k in range(0, 1200, 3):
            eye, _target = scene.camera_pose(k * 0.1, level)
            r = math.hypot(eye[0], eye[2])
            assert tube['r_min'] <= r <= tube['r_max'] and tube['y_min'] <= eye[1] <= tube['y_max']
    for kind, a, height, _speed, *_ in layout['vehicles']:
        if kind < 0.5:   # carriles del bulevar: lejos del tubo o muy por encima
            assert not (tube['r_min'] - 4 <= a <= tube['r_max'] + 4 and height <= tube['y_max'] + 12)
            assert inner < a < outer
        else:            # avenidas que cruzan el bulevar: por debajo o muy por encima de la cámara
            assert height <= tube['y_min'] - 10 or height >= tube['y_max'] + 12
    for x, z, *_ in layout['steam']:
        assert not (inner - 4 < math.hypot(x, z) < outer + 4)


def test_073_city_levels_are_deterministic_and_grow_in_load():
    scene = _073_scene()
    a, b = scene.city_layout(), scene.city_layout.__wrapped__()
    assert a['buildings'][:50] == b['buildings'][:50]
    loads = [scene.level_workload(s) for s in scene.SCENE_LEVELS]
    for key in ('building_instances', 'streetlight_instances', 'vehicle_instances', 'volumetric_steps'):
        values = [w[key] for w in loads]
        assert values == sorted(values) and values[0] < values[-1], key
    for s in scene.SCENE_LEVELS:
        assert s.building_instances <= len(a['buildings']) and s.streetlight_instances <= len(a['streetlights'])
    assert scene.SCENE_LEVELS[-1].reflection_divisor == 1
    assert [s.key for s in scene.profile_levels('quick')] == ['avenue', 'district', 'skyline']


def test_073_shader_constants_match_city_layout():
    scene = _073_scene()
    hlsl = (ROOT / 'core/benchmark_gpu.py').read_text(encoding='utf-8').split("HLSL = r" + "'" * 3, 1)[1].split("'" * 3, 1)[0]
    def const(name):
        line = next(l for l in hlsl.splitlines() if f'static const float {name} =' in l)
        return eval(line.split('=', 1)[1].strip().rstrip(';'))
    assert const('PITCH') == scene.PITCH and const('ROAD') == scene.CITY['road']
    assert const('CITY_EXTENT') == scene.CITY_EXTENT and const('RING_R') == scene.CITY['ring_radius']
    assert const('RING_HW') == scene.CITY['ring_half_width'] and abs(const('LAMP_EDGE') - scene.LAMP_EDGE) < 1e-9
    assert const('LAMP_SPACING') == scene.CITY['lamp_spacing'] and const('LAMP_H') == scene.CITY['lamp_height']
    assert const('SHADOW_TEXEL') == 1.0 / _072_module_constant('core/benchmark_gpu.py', 'SHADOW_MAP_SIZE')


def test_073_render_passes_order_resources_and_no_island_leftovers():
    backend = (ROOT / 'core/benchmark_gpu.py').read_text(encoding='utf-8')
    scene = (ROOT / 'core/directx_scene.py').read_text(encoding='utf-8')
    frame = backend.split('def render_frame', 1)[1].split('def _post', 1)[0]
    assert frame.index('self.shadow_dsv') < frame.index('self.refl_rtv') < frame.index('self.hdr_rtv') < frame.index("'PSComposite'")
    assert 'mirror=_mat_mul(_reflect_y(),vp_mat)' in frame and 'render_pass=2' in frame
    assert "b'INSTA'" in backend and 'D3D11_INPUT_PER_INSTANCE_DATA' in backend
    assert 'moonShafts' in backend and 'level.volumetric_steps' in backend
    close = backend.split('    def close(self):', 2)[2]
    for name in ('refl_tex', 'refl_depth', 'shadow_tex', 'hdr_tex', 'post_cb'):
        assert f"'{name}'" in close
    assert 'self.instances={}' in close
    for gone in ('build_tree', 'build_boat', 'build_water', 'terrain_height', 'BOAT_ROUTE', 'storm'):
        assert gone not in backend and gone not in scene, gone
    # El hash de ventanas usa la cara redondeada (la normal interpolada variaba
    # por píxel y producía «estática» en las fachadas).
    assert 'float2 face=round(float2(N.x,N.z));' in backend


def test_073_benchmark_page_shows_city_scenes_and_v29():
    view = (UI / 'BenchmarkPage.qml').read_text(encoding='utf-8')
    for key in ('"avenue"', '"district"', '"skyline"', '"megacity"'):
        assert key in view
    assert 'GPU · DirectX 11 V29' in view and 'CONDICIONES DE LA PRUEBA GPU' in view
    assert 'Pradera' not in view and 'valley' not in view
    runner = (ROOT / 'core/benchmark.py').read_text(encoding='utf-8')
    assert 'benchmark_gpu_v29_ultimo_resultado.json' in runner and 'monitor_factory=GpuSessionMonitor' in runner


# --- REBUILD 081: privacidad en Red avanzada ---

def _081_network_functions():
    import ast
    source = (ROOT / 'core' / 'maintenance' / 'network.py').read_text(encoding='utf-8')
    tree = ast.parse(source)
    names = {'_display_value', '_flatten_network', '_mask_ip', '_mask_value', '_present_network',
             'HIDDEN_MARK', 'SENSITIVE_FIELDS', 'FULLY_HIDDEN', 'REVEAL_SECONDS'}
    nodes = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name in names) or
             (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in names for t in n.targets))]
    env = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), 'network.py', 'exec'), env)
    return env


def test_081_network_identity_is_masked_until_revealed():
    env = _081_network_functions()
    flat = env['_flatten_network']({'adapters': [{
        'name': 'Wi-Fi', 'ipv4': ['192.168.1.37'], 'ipv6': ['2800:810:4f2:1a::5'], 'gateways': ['192.168.1.1'],
        'dns_servers': ['200.42.4.1', '1.1.1.1'], 'ssid': 'Casa Perez 5G', 'wifi_signal_percent': 80,
        'link_speed_mbps': 866, 'is_up': True}], 'primary_index': 0, 'source': 'psutil'})
    hidden = env['_present_network'](flat, set())
    dump = repr(hidden)
    for secret in ('192.168.1.37', '2800:810', 'Casa Perez', '200.42.4.1', '192.168.1.1'):
        assert secret not in dump, secret
    assert hidden['ipv4'] == '192.168.1.•••' and hidden['gateway'] == '192.168.1.•••'
    assert hidden['dns'] == '200.42.•••.•••, 1.1.•••.•••'      # IP pública: dos tramos ocultos
    assert hidden['ssid'] == env['HIDDEN_MARK'] and hidden['ipv6'] == env['HIDDEN_MARK']
    assert hidden['signal'] == '80%' and hidden['linkSpeed'] == '866 Mbps'   # lo inofensivo no se oculta
    assert hidden['hasSensitive']['ssid'] and not hidden['revealed']['ssid']
    only_ssid = env['_present_network'](flat, {'ssid'})
    assert only_ssid['ssid'] == 'Casa Perez 5G' and '2800:810' not in repr(only_ssid['ipv6'])
    assert 'Casa Perez' not in repr(only_ssid['adapters'])           # revelar un campo no revela el adaptador
    adapter = env['_present_network'](flat, {'adapter:0'})
    assert adapter['adapters'][0]['ipv4'] == '192.168.1.37' and adapter['adapters'][0]['revealed']
    assert adapter['ipv4'] == '192.168.1.•••'
    assert env['_mask_ip']('fe80::1%12') == 'fe80:••••' and env['_mask_value']('dns', 'N/A') == 'N/A'
    assert env['REVEAL_SECONDS'] == 30


def test_081_mac_bssid_and_speedtest_identity_are_not_collected():
    network = (ROOT / 'core' / 'maintenance' / 'network.py').read_text(encoding='utf-8')
    speed = (ROOT / 'core' / 'maintenance' / 'speed_test.py').read_text(encoding='utf-8')
    for gone in ('MacAddress', "'bssid'", "'mac'", 'AF_LINK'):
        assert gone not in network, gone
    for gone in ("'external_ip':", "'internal_ip':", "'client_ip':", "'isp':", "'city':", "'result_url':", "'bind_ip':"):
        assert gone not in speed, gone
    assert "return {'colo': data.get('colo')}" in speed


def test_081_network_page_uses_reusable_privacy_eye():
    page = (UI / 'NetworkPage.qml').read_text(encoding='utf-8')
    eye = (UI / 'PrivacyEye.qml').read_text(encoding='utf-8')
    glyph = (UI / 'Glyph.qml').read_text(encoding='utf-8')
    assert 'signal toggled()' in eye and 'property bool revealed' in eye
    assert 'case "eye":' in glyph and 'case "eye_off":' in glyph
    assert page.count('PrivacyEye {') == 3
    assert 'privacyKey: "ipv4"' in page and 'networkHealth.toggleReveal("adapter:" + index)' in page
    for key in ('k:"gateway"', 'k:"dns"', 'k:"ipv6"', 'k:"ssid"'):
        assert key in page
    controller = (ROOT / 'core' / 'maintenance' / 'network.py').read_text(encoding='utf-8')
    assert 'def toggleReveal' in controller and 'def hideSensitive' in controller
    assert 'self.hideSensitive()' in controller.split('def stopWatch', 1)[1].split('def ', 1)[0]


# --- REBUILD 082: botones de acción destacados ---

def test_082_action_buttons_colored_text_and_solid_only_for_apply_update():
    main = (ROOT / 'main.py').read_text(encoding='utf-8')
    for key in ("'action': '#17B9F7'", "'actionText'", "'actionMuted'", "'actionMutedText'"):
        assert key in main, key
    expected = {'CleanupPage.qml': 14, 'HealthPage.qml': 19, 'NetworkPage.qml': 5, 'ThemesPage.qml': 1}
    for name, minimum in expected.items():
        qml = (UI / name).read_text(encoding='utf-8')
        assert 'property bool actionStyle: false' in qml and 'property bool solidStyle: false' in qml, name
        assert qml.count('actionStyle: true') + qml.count('actionStyle: !') >= minimum, name
        # «action» es una propiedad FINAL de AbstractButton: no debe reusarse.
        assert 'property bool action:' not in qml, name
    # Relleno completo sólo en Aplicar / Actualizar.
    health = (UI / 'HealthPage.qml').read_text(encoding='utf-8')
    assert health.count('solidStyle: true') == 3
    assert 'solidStyle: true; label: d.busy ? "Consultando…" : "Actualizar"' in (UI / 'NetworkPage.qml').read_text(encoding='utf-8')
    assert 'solidStyle: !themeCard.active' in (UI / 'ThemesPage.qml').read_text(encoding='utf-8')
    assert 'solidStyle: true' not in (UI / 'CleanupPage.qml').read_text(encoding='utf-8')
    for name in ('StartupPage.qml', 'InsightsPage.qml', 'TweaksPage.qml'):
        line = next(l for l in (UI / name).read_text(encoding='utf-8').splitlines() if '"Actualizar"' in l and 'Text' in l)
        assert 'actionText' in line, name
    # El resto de las acciones: texto de color, sin relleno.
    for name, label in (('DriversPage.qml', 'Buscar actualizaciones'), ('ReportsPage.qml', 'Generar informe PDF'),
                        ('OverlayPage.qml', 'Localizar RTSS.exe'), ('Main.qml', 'Crear PDF')):
        line = next(l for l in (UI / name).read_text(encoding='utf-8').splitlines() if label in l and 'Text' in l)
        assert 'themeManager.palette.action' in line and 'actionText' not in line, (name, label)


def test_rebuild_087_health_hub_icons_larger():
    qml = (UI / "HealthPage.qml").read_text(encoding="utf-8")
    assert 'kind: hubCard.modelData.icon' in qml
    assert 'Layout.preferredWidth: 30; Layout.preferredHeight: 30' in qml
    for area in ("battery", "windows", "repair", "history", "recovery", "performance", "audio"):
        assert f'key:"{area}"' in qml

def test_rebuild_087_cleanup_grid_uniform_heights():
    qml = (UI / "CleanupPage.qml").read_text(encoding="utf-8")
    assert 'readonly property int cleanupCardHeight: 270' in qml
    assert qml.count('Layout.preferredHeight: page.cleanupCardHeight') == 5
    assert 'page.ramDetailsOpen && page.hasRamResult ? page.cleanupExpandedRamHeight : page.cleanupCardHeight' in qml
    assert 'actionStyle: true' in qml  # botones y acciones de la base Maxi se conservan


def test_rebuild_088_health_hub_uses_icon_refresh_button():
    qml = (UI / "HealthPage.qml").read_text(encoding="utf-8")
    assert 'component HeaderIconButton: AbstractButton' in qml
    assert 'visible: currentModule === "hub"' in qml
    assert 'kind: "refresh"' in qml


def test_rebuild_088_health_hub_removes_fixed_evidence_copy():
    qml = (UI / "HealthPage.qml").read_text(encoding="utf-8")
    assert 'Evaluación explicable con los indicadores disponibles.' not in qml
    assert 'text: "Evidencia: " +' not in qml
    py = (ROOT / 'core' / 'health' / 'system_health.py').read_text(encoding='utf-8')
    assert 'headlineDisplay' in py
    assert 'headlineDetail' in py



def test_rebuild_089_gpu_brand_logo_follows_monitored_adapter():
    detail = (UI / "ComponentDetail.qml").read_text(encoding="utf-8")
    glyph = (UI / "Glyph.qml").read_text(encoding="utf-8")
    assert 'String(m.gpuName || "").toLowerCase()' in detail
    for name in ('nvidia', 'amd', 'intel'):
        assert f'return "{name}"' in detail
    assert 'return "unknown"' in detail
    assert 'page.componentKind === "gpu" && page.gpuVendor === "nvidia"' in detail
    assert 'page.componentKind === "gpu" && page.gpuVendor === "amd"' in detail
    assert 'page.componentKind === "gpu" && page.gpuVendor === "intel"' in detail
    assert 'kind: "gpu_nvidia"' in detail
    assert 'text: "AMD"' in detail
    assert 'text: "intel"' in detail
    assert 'case "gpu_nvidia":' in glyph and 'case "gpu_amd":' in glyph


def test_rebuild_090_gpu_header_brand_badges():
    detail = (UI / 'ComponentDetail.qml').read_text(encoding='utf-8')
    glyph = (UI / 'Glyph.qml').read_text(encoding='utf-8')
    assert 'text: "AMD"' in detail
    assert 'text: "intel"' in detail
    assert 'page.gpuVendor === "nvidia"' in detail
    assert 'case "gpu_nvidia":' in glyph and 'case "gpu_amd":' in glyph


def test_rebuild_091_cpu_branding_in_detail_and_summary():
    detail = (UI / 'ComponentDetail.qml').read_text(encoding='utf-8')
    overview = (UI / 'Overview.qml').read_text(encoding='utf-8')
    metric = (UI / 'MetricLine.qml').read_text(encoding='utf-8')
    assert 'readonly property string cpuVendor:' in detail
    assert 'page.componentKind === "cpu" && page.cpuVendor === "intel"' in detail
    assert 'page.componentKind === "cpu" && page.cpuVendor === "amd"' in detail
    assert 'function cpuVendor(name, manufacturer)' in overview
    assert 'brandVendor: page.cpuVendor(page.m.cpuName, page.m.cpuManufacturer)' in overview
    assert 'property string brandVendor: "unknown"' in metric
    assert 'readonly property bool brandedCpu:' in metric
    assert 'meter.hasBrandMark && meter.brandVendor === "intel"' in metric
    assert 'meter.hasBrandMark && meter.brandVendor === "amd"' in metric


def test_rebuild_092_gpu_vendor_branding_in_system_status():
    overview = (UI / "Overview.qml").read_text(encoding="utf-8")
    metric = (UI / "MetricLine.qml").read_text(encoding="utf-8")
    assert 'function gpuVendor(name)' in overview
    assert 'brandVendor: page.gpuVendor(page.m.gpuName)' in overview
    assert 'readonly property bool brandedGpu:' in metric
    assert 'meter.brandedGpu && meter.brandVendor === "nvidia"' in metric
    assert 'meter.hasBrandMark && meter.brandVendor === "amd"' in metric
    assert 'meter.hasBrandMark && meter.brandVendor === "intel"' in metric
    assert 'visible: !meter.hasBrandMark' in metric
    # No altera el click que abre la ficha GPU.
    assert 'onClicked:meter.activated()' in metric


def test_rebuild_092_chart_legend_displays_vendor_icons_without_changing_data():
    overview = (UI / "Overview.qml").read_text(encoding="utf-8")
    assert 'component ChartBrandIcon: Item' in overview
    assert 'vendor: page.cpuVendor(page.m.cpuName, page.m.cpuManufacturer)' in overview
    assert 'vendor: page.gpuVendor(page.m.gpuName)' in overview
    assert 'cpuValues:telemetry ? telemetry.cpuHistory : []' in overview
    assert 'gpuValues:telemetry ? telemetry.gpuHistory : []' in overview
    assert 'cpuColor:page.cpuBrandColor' in overview
    assert 'gpuColor:page.gpuBrandColor' in overview
    assert 'Rectangle {Layout.preferredWidth:8;Layout.preferredHeight:8;radius:4;color:page.gpuBrandColor}' not in overview


def test_rebuild_093_chart_legend_returns_to_simple_points():
    overview = (UI / 'Overview.qml').read_text(encoding='utf-8')
    assert 'Layout.preferredWidth: 10' in overview
    assert 'radius: 5' in overview
    assert 'color: page.cpuBrandColor' in overview
    assert 'color: page.gpuBrandColor' in overview
    legend_head = overview.split('HistoryChart {', 1)[0]
    assert 'ChartBrandIcon {' not in legend_head


def test_rebuild_094_metricline_uses_detail_style_brand_badges():
    metric = (UI / 'MetricLine.qml').read_text(encoding='utf-8')
    assert 'readonly property color brandFill:' in metric
    assert 'brandVendor === "nvidia" ? "#76B900"' in metric
    assert 'brandVendor === "amd" ? "#B11F25"' in metric
    assert 'brandVendor === "intel" ? "#1AA0F2"' in metric
    assert 'meter.brandFill' in metric
    assert 'ink: meter.brandInk' in metric


def test_rebuild_095_tray_cleanup_has_no_stale_qml_signal():
    main_qml = (UI / "Main.qml").read_text(encoding="utf-8")
    app = (ROOT / "main.py").read_text(encoding="utf-8")
    cleanup_qml = (UI / "CleanupPage.qml").read_text(encoding="utf-8")
    assert 'onOpenRamCleanupRequested' not in main_qml
    assert 'target: trayController' not in main_qml
    assert 'ramCleanupRequested = Signal()' in app
    assert 'tray_controller.ramCleanupRequested.connect(start_tray_ram_cleanup)' in app
    assert 'cleanup.cleanRamDeepFromTray()' in app
    assert 'ram_ui_feedback=False, tray_operation=True' in (ROOT / "core" / "maintenance" / "cleanup.py").read_text(encoding="utf-8")
    assert 'onConfirmed: cleanup.cleanRamDeep()' in cleanup_qml


def test_rebuild_096_removes_only_full_page_card_shells():
    from pathlib import Path
    bare_pages = ("InsightsPage.qml", "StartupPage.qml", "DriversPage.qml", "ReportsPage.qml",
                  "BenchmarkPage.qml", "NetworkPage.qml", "OverlayPage.qml", "ComponentDetail.qml")
    for filename in bare_pages:
        source = (UI / filename).read_text(encoding="utf-8")
        assert not any(item in source for item in (
            'anchors.fill: parent; radius: 22; color: page.theme.panel; border.width: 1',
            'anchors.fill:parent; radius:22; color:page.theme.panel; border.width:1',
            'anchors.fill:parent; color:page.panel; radius:22; border.width:1',
            'anchors.fill: parent; color: page.panel; radius: 22; border.width: 1',
        )), filename
    main = (UI / "Main.qml").read_text(encoding="utf-8")
    assert 'id: readingsPage' in main
    assert 'Item {\n                    id: readingsPage' in main
    assert 'contentHeight: Math.max(diagnosticContent.implicitHeight, diagnosticContent.height) + 16' in main
    assert 'id: diagnosticPage' in main


def test_rebuild_096_retains_inner_cards_confirmations_and_background():
    insight = (UI / "InsightsPage.qml").read_text(encoding="utf-8")
    assert 'id: trendCanvas' in insight
    # La tarjeta interior conserva la superficie de Limpieza/Resumen;
    # el botón Volver inferior (que usaba panelRaised) fue retirado en V100.
    assert 'color: page.theme.panel; border.width: 1; border.color: page.theme.panelBorder' in insight
    assert 'visible: page.confirmClear' in insight
    assert 'monitoringInsights.refresh()' in insight
    benchmark = (UI / "BenchmarkPage.qml").read_text(encoding="utf-8")
    assert 'benchmarkController.startGpu(page.gpuProfile)' in benchmark
    assert 'benchmarkController.start()' in benchmark
    network = (UI / "NetworkPage.qml").read_text(encoding="utf-8")
    assert 'id: scroller' in network
    detail = (UI / "ComponentDetail.qml").read_text(encoding="utf-8")
    assert 'page.gpuVendor === "nvidia"' in detail
    assert 'page.cpuVendor === "intel"' in detail
    main = (UI / "Main.qml").read_text(encoding="utf-8")
    assert 'readonly property color shellBgStart' in main
    assert 'readonly property color shellBgEnd' in main


def test_rebuild_097_card_surfaces_match_cleanup_and_overview():
    read = lambda file: (UI / file).read_text(encoding="utf-8")
    cleanup = read("CleanupPage.qml")
    overview = read("Overview.qml")
    assert 'readonly property color surface: themeManager.palette.panel' in cleanup
    assert 'color:themeManager.palette.panel;border.width:1' in overview or 'color:themeManager.palette.panel;border.width:1' in overview.replace(' ', '')
    for name in ("InsightsPage.qml", "BenchmarkPage.qml", "NetworkPage.qml", "OverlayPage.qml", "StartupPage.qml", "DriversPage.qml", "ReportsPage.qml", "ComponentDetail.qml"):
        source = read(name)
        assert 'themeManager.palette.panel' in source or 'page.theme.panel' in source or 'page.panel' in source
    assert 'color: page.theme.panel; border.width: 1' in read("InsightsPage.qml")
    assert 'radius:16; color:page.panel; border.width:1' in read("BenchmarkPage.qml")
    assert 'radius: 18; color: page.panel; border.width: 1' in read("OverlayPage.qml")
    assert 'radius: 14; color:themeManager.palette.panel; border.width:1' in read("ComponentDetail.qml")
    assert 'radius:13;color:window.activeTheme.panel;border.width:1;border.color:window.activeTheme.panelBorder' in read("Main.qml")


def test_rebuild_097_no_reintroduced_outer_page_cards_or_backend_edits():
    for name in ("InsightsPage.qml", "StartupPage.qml", "DriversPage.qml", "ReportsPage.qml", "NetworkPage.qml", "ComponentDetail.qml"):
        s=(UI / name).read_text(encoding="utf-8")
        assert 'anchors.fill: parent' in s
    s=(UI / "Overview.qml").read_text(encoding="utf-8")
    assert 'themeManager.palette.panel' in s
    assert 'cpuValues:telemetry ? telemetry.cpuHistory : []' in s


# REBUILD 098: navegador tras prueba oficial, sin exponer URL ni datos sensibles.
def test_rebuild_098_validates_official_speedtest_result_urls():
    import re
    src = (ROOT / 'core' / 'maintenance' / 'speed_test.py').read_text(encoding='utf-8')
    node = next(node for node in ast.parse(src).body
                if isinstance(node, ast.FunctionDef) and node.name == '_official_ookla_web_link')
    context = {'re': re}
    exec(compile(ast.Module(body=[node], type_ignores=[]), 'speed_test.py', 'exec'), context)
    validate = context['_official_ookla_web_link']
    good = 'https://www.speedtest.net/result/c/4ef15b76-abcb-49c6-b803-c801a872b6f1'
    assert validate({'result': {'url': good}}) == good
    assert validate({'result': {'url': 'https://speedtest.net/result/1234567890'}}) == 'https://speedtest.net/result/1234567890'
    for url in (
        'http://www.speedtest.net/result/c/4ef15b76-abcb-49c6-b803-c801a872b6f1',
        'https://speedtest.net.evil.com/result/123456789',
        'https://www.speedtest.net@evil.com/result/123456789',
        'https://www.speedtest.net/result/123456789?x=1',
        'https://www.speedtest.net/result/123456789#extra',
        'https://www.speedtest.net:8443/result/123456789',
        'https://www.speedtest.net/about/terms',
        'javascript:alert(1)',
    ):
        assert validate({'result': {'url': url}}) is None
    assert validate({}) is None
    assert validate({'result': {}}) is None
    assert validate({'result': {'url': 333}}) is None


def test_rebuild_098_only_signals_successful_ookla_and_keeps_link_private():
    import queue
    from types import SimpleNamespace
    source = (ROOT / 'core' / 'maintenance' / 'speed_test.py').read_text(encoding='utf-8')
    class_node = next(node for node in ast.parse(source).body
                      if isinstance(node, ast.ClassDef) and node.name == 'NetworkSpeedTest')
    method = next(node for node in class_node.body
                  if isinstance(node, ast.FunctionDef) and node.name == '_finish')
    env = {'Empty': queue.Empty, 'OOKLA_PROVIDER': 'ookla'}
    exec(compile(ast.Module(body=[method], type_ignores=[]), 'speed_test.py', 'exec'), env)
    finish = env['_finish']

    class SignalSpy:
        def __init__(self): self.calls = []
        def emit(self, *args): self.calls.append(args)

    class ReadyFuture:
        def __init__(self, result): self.payload = result
        def done(self): return True
        def result(self): return self.payload

    link = 'https://www.speedtest.net/result/c/4ef15b76-abcb-49c6-b803-c801a872b6f1'
    for successful, provider, has_link, closed in (
        (True, 'ookla', True, False),
        (False, 'ookla', True, False),
        (True, 'cloudflare', True, False),
        (True, 'ookla', False, False),
        (True, 'ookla', True, True),
    ):
        result = {'ok': successful, 'provider_key': provider}
        if has_link: result['_official_web_link'] = link
        changed, browser = SignalSpy(), SignalSpy()
        instance = SimpleNamespace(
            _provision_future=None, _progress_queue=queue.Queue(),
            _future=ReadyFuture(result), _mode='speed_test',
            _poll=SimpleNamespace(stop=lambda: None),
            _data={'busy': True}, _closed=closed,
            changed=changed, officialResultReady=browser,
        )
        finish(instance)
        assert instance._future is None
        assert '_official_web_link' not in instance._data['result']
        assert browser.calls == ([(link,)] if successful and provider == 'ookla' and has_link and not closed else [])


def test_rebuild_098_automatic_browser_connection_and_cloudflare_explanation():
    engine = (ROOT / 'core' / 'maintenance' / 'speed_test.py').read_text(encoding='utf-8')
    main = (UI / 'Main.qml').read_text(encoding='utf-8')
    network = (UI / 'NetworkPage.qml').read_text(encoding='utf-8')
    assert "result['_official_web_link'] = web_link" in engine
    assert 'officialResultReady = Signal(str)' in engine
    assert 'self.officialResultReady.emit(web_link)' in engine
    assert 'target: networkSpeedTest' in main
    assert 'function onOfficialResultReady(url) { Qt.openUrlExternally(url) }' in main
    assert 'Cloudflare solo muestra sus mediciones locales' in network


def test_rebuild_100_trends_graph_uses_only_persisted_samples_and_30s_refresh():
    qml = (UI / "InsightsPage.qml").read_text(encoding="utf-8")
    backend = (ROOT / "core" / "health" / "monitoring_insights.py").read_text(encoding="utf-8")
    assert 'height: page.section === "trends" ? implicitHeight : pageScroll.height' in qml
    assert 'contentHeight: content.implicitHeight + 12' in qml
    assert 'target: monitoringInsights' in qml
    assert 'trendCanvas.sampleSignature() !== trendCanvas.lastPlottedSignature' in qml
    assert 'const v = rows[i][seriesItem.key]' in qml
    assert 'ctx.stroke()' in qml
    assert 'target: telemetry' not in qml
    assert 'onMetricsChanged()' not in qml
    assert 'liveMetrics' not in qml
    assert 'livePercent' not in qml
    assert 'ctx.arc(w - 2.5, liveY' not in qml
    assert 'self._timer.setInterval(30_000)' in backend
    assert 'self.telemetry.metricsChanged.connect(self._record_if_due)' in backend


def test_rebuild_100_trends_navigation_cleaned_without_breaking_refresh():
    qml = (UI / "InsightsPage.qml").read_text(encoding="utf-8")
    assert qml.index('id: backMouse') < qml.index('id: refreshMouse')
    assert qml.count('text: "Volver"') == 1
    assert 'onClicked: page.goBack()' in qml
    assert 'monitoringInsights.refresh()' in qml
    assert 'Component.onCompleted: monitoringInsights.refresh()' not in qml
    assert 'N/A indica que la fuente no proporcionó un valor comprobable.' not in qml
    assert 'return typeof value === "number" && isFinite(value) && value >= 0 && value <= 100' in qml
    assert 'return typeof value' in qml and ': "N/A"' in qml
    assert 'Última muestra guardada:' in qml


def test_rebuild_101_sessions_migrated_without_falsely_associating_legacy_samples():
    source = (ROOT / 'core' / 'health' / 'monitoring_insights.py').read_text(encoding='utf-8')
    assert 'ALTER TABLE samples ADD COLUMN session_id TEXT' in source
    assert 'CREATE TABLE IF NOT EXISTS windows_sessions' in source
    assert 'psutil.boot_time()' in source
    assert 'self._session_id, self._boot_ts = _windows_boot_session()' in source
    assert 'RETENTION_DAYS = 90' in source
    assert 'self._timer.setInterval(30_000)' in source
    assert 'MAX(s.ts) AS lastSample' in source
    assert 'AVG(s.cpu) AS cpuAvg' in source


def test_rebuild_101_history_and_comparison_ui_are_below_graph():
    qml = (UI / 'InsightsPage.qml').read_text(encoding='utf-8')
    assert qml.index('id: trendCanvas') < qml.index('HISTORIAL DE SESIONES DE WINDOWS')
    for name in ('selectSession(modelData.id)', 'compareSession(modelData.id)', 'clearComparison()',
                 'page.comparisonSamples', 'page.selectedSession.cpuAvg'):
        assert name in qml or (name == 'page.selectedSession.cpuAvg' and 'page.selectedSession[keyName]' in qml)
    assert 'FastFlickable {\n        id: pageScroll' in qml
    assert 'sin asignar a una sesión' in qml
    assert 'puede contener pausas' in qml
    assert 'value:page.selectedSession.count' in qml


def test_rebuild_101_session_boot_identity_and_real_sample_thinning():
    import math
    import time
    from types import SimpleNamespace
    tree = ast.parse((ROOT / 'core' / 'health' / 'monitoring_insights.py').read_text(encoding='utf-8'))
    funcs = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in
             ('_windows_boot_session', '_thin_real_samples', '_valid_metric')]
    ns = {'math': math, 'time': time, 'CHART_POINT_LIMIT': 480,
          'psutil': SimpleNamespace(boot_time=lambda: 1700000000.4)}
    exec(compile(ast.Module(body=funcs, type_ignores=[]), 'monitoring_insights.py', 'exec'), ns)
    ident1, boot1 = ns['_windows_boot_session'](now=1700001000)
    ident2, boot2 = ns['_windows_boot_session'](now=1700001900)
    assert ident1 == ident2 == 'winboot:1700000000'
    assert boot1 == boot2 == 1700000000.0
    assert ns['_windows_boot_session'](now=1700001900, boot=0) == (None, None)
    assert ns['_valid_metric'](0) == 0 and ns['_valid_metric'](100) == 100
    for invalid in (-1, 101, True, float('nan'), None):
        assert ns['_valid_metric'](invalid) is None
    real = [{'ts': i, 'cpu': float(i % 100)} for i in range(10000)]
    thin = ns['_thin_real_samples'](real)
    assert len(thin) <= 480 and thin[0] == real[0] and thin[-1] == real[-1]
    assert all(point in real for point in thin)


def test_rebuild_101_sqlite_schema_upgrade_preserves_legacy_and_session_averages(tmp_path):
    import sqlite3
    from types import SimpleNamespace
    db_path = tmp_path / 'legacy.sqlite3'
    with sqlite3.connect(db_path) as db:
        db.execute('CREATE TABLE samples (ts REAL PRIMARY KEY, cpu REAL, gpu REAL, ram REAL, disk REAL)')
        db.execute('INSERT INTO samples VALUES (1000,30,NULL,50,20)')
    tree = ast.parse((ROOT / 'core' / 'health' / 'monitoring_insights.py').read_text(encoding='utf-8'))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'MonitoringInsights')
    names = ('_ensure_schema', '_session_rows')
    methods = [node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name in names]
    ns = {'sqlite3': sqlite3}
    exec(compile(ast.Module(body=methods, type_ignores=[]), 'monitoring_insights.py', 'exec'), ns)
    def connection():
        c = sqlite3.connect(db_path)
        c.row_factory = sqlite3.Row
        return c
    obj = SimpleNamespace(_connect=connection, _session_id='winboot:950')
    ns['_ensure_schema'](obj)
    with connection() as db:
        assert 'session_id' in {row[1] for row in db.execute('PRAGMA table_info(samples)')}
        assert db.execute('SELECT session_id FROM samples WHERE ts=1000').fetchone()[0] is None
        db.execute('INSERT INTO windows_sessions VALUES (?,?,?,?)', ('winboot:950',950,1002,1032))
        db.execute('INSERT INTO samples VALUES (?,?,?,?,?,?)', (1002,70,None,40,20,'winboot:950'))
        db.execute('INSERT INTO samples VALUES (?,?,?,?,?,?)', (1032,30,None,60,25,'winboot:950'))
        result = ns['_session_rows'](obj, db)
        assert len(result) == 1 and result[0]['count'] == 2
        assert result[0]['cpuAvg'] == 50 and result[0]['gpuAvg'] is None
        assert result[0]['recordedSpanSeconds'] == 30
        assert result[0]['current'] is True


def test_rebuild_102_network_page_removes_connectivity_diagnostic():
    qml = (UI / 'NetworkPage.qml').read_text(encoding='utf-8')
    assert 'Diagnóstico de conectividad' not in qml
    assert 'Ejecutar pruebas' not in qml


def test_rebuild_102_network_backend_removes_diagnose_logic():
    source = (ROOT / 'core' / 'maintenance' / 'network.py').read_text(encoding='utf-8')
    assert 'def diagnose_network(identity=None, count=4):' not in source
    assert 'def diagnose(self):' not in source
    assert "'diagnosis': {}" not in source
    assert "'diagnosing': False" not in source


def test_rebuild_103_diagnostic_layout_centered_and_larger():
    qml = (UI / 'Main.qml').read_text(encoding='utf-8')
    assert 'Layout.preferredHeight: 430' in qml
    assert 'width: 320' in qml
    assert 'height: 320' in qml
    assert 'anchors.centerIn: parent' in qml


def test_rebuild_104_diagnostic_center_uses_available_viewport_height():
    qml = (UI / 'Main.qml').read_text(encoding='utf-8')
    assert 'id: diagnosticScroller' in qml
    assert 'height: Math.max(implicitHeight, diagnosticScroller.height - 16)' in qml
    assert 'contentHeight: Math.max(diagnosticContent.implicitHeight, diagnosticContent.height) + 16' in qml
    assert 'Layout.fillHeight: diagnostic.status !== "complete" && diagnostic.status !== "partial"' in qml
    block = qml.split('id: diagnosticCircle', 1)[1].split('Behavior on scale', 1)[0]
    assert 'anchors.centerIn: parent' in block
    assert 'anchors.verticalCenterOffset' not in block
    assert 'width: 320' in block and 'height: 320' in block
    assert 'onClicked: systemHealth.runDiagnostic()' in qml


def test_rebuild_105_diagnostic_circle_idle_full_and_running_starts_zero():
    qml = (UI / 'Main.qml').read_text(encoding='utf-8')
    canvas = qml.split('id: diagnosticRing', 1)[1].split('Connections {', 1)[0]
    assert 'state === "idle" || state === "complete"' in canvas
    assert 'return 1' in canvas
    assert 'Math.max(0, Math.min(1, value / 100))' in canvas
    assert 'if (drawnProgress <= 0) return' in canvas
    assert 'ctx.clearRect(0, 0, width, height)' in canvas
    assert 'Number(diagnosticPage.diagnostic.progress) > 0' in canvas
    assert 'Math.max(0.04' not in canvas
    assert '0.31' not in canvas


def test_rebuild_105_diagnostic_publishes_zero_before_first_poll():
    backend = (ROOT / 'core' / 'health' / 'system_health.py').read_text(encoding='utf-8')
    block = backend.split('    def runDiagnostic(self):', 1)[1].split('    def _poll_diagnostic(self):', 1)[0]
    assert "'status': 'running', 'progress': 0" in block
    assert 'self._diagnostic_timer.start()' in block
    assert 'self._poll_diagnostic()' not in block
    assert 'self._diagnostic_timer.setInterval(250)' in backend


def test_rebuild_105_diagnostic_actual_progress_from_completed_sources():
    """Ejecuta los métodos reales con fuentes simuladas sin necesitar PySide6."""
    import ast
    import datetime
    import time
    from types import SimpleNamespace

    source = (ROOT / 'core' / 'health' / 'system_health.py').read_text(encoding='utf-8')
    klass = next(n for n in ast.parse(source).body
                 if isinstance(n, ast.ClassDef) and n.name == 'SystemHealth')
    functions = []
    for method in klass.body:
        if isinstance(method, ast.FunctionDef) and method.name in ('runDiagnostic', '_poll_diagnostic'):
            method.decorator_list = []
            functions.append(method)
    namespace = {'time': time, 'datetime': datetime.datetime}
    exec(compile(ast.fix_missing_locations(ast.Module(body=functions, type_ignores=[])),
                 '<corepulse-sistema-diagnostico>', 'exec'), namespace)

    class FakeSource:
        def __init__(self):
            self.data = {'busy': False}
        def refresh(self):
            self.data['busy'] = True

    class FakeTimer:
        def __init__(self):
            self.started = False
        def start(self):
            self.started = True
        def stop(self):
            self.started = False

    class FakeSignal:
        def emit(self):
            pass

    sources = [FakeSource() for _ in range(4)]
    dummy = SimpleNamespace(
        telemetry=SimpleNamespace(refresh=lambda: None),
        battery=sources[0], storage=sources[1], windows=sources[2], recovery=sources[3],
        _diagnostic={'status': 'idle', 'progress': 0, 'runId': 0},
        _diagnostic_timer=FakeTimer(), diagnosticChanged=FakeSignal(),
        _rebuild=lambda: None, _data={'coverage': 'N/A'},
    )
    dummy.refresh = lambda: [source.refresh() for source in sources]
    namespace['runDiagnostic'](dummy)
    assert dummy._diagnostic['status'] == 'running'
    assert dummy._diagnostic['progress'] == 0
    assert dummy._diagnostic_timer.started
    namespace['_poll_diagnostic'](dummy)
    assert dummy._diagnostic['progress'] == 0  # Aún hay 4 fuentes ocupadas.
    sources[0].data['busy'] = False
    namespace['_poll_diagnostic'](dummy)
    assert dummy._diagnostic['progress'] == 22
    sources[1].data['busy'] = False
    namespace['_poll_diagnostic'](dummy)
    assert dummy._diagnostic['progress'] == 45
    sources[2].data['busy'] = False
    namespace['_poll_diagnostic'](dummy)
    assert dummy._diagnostic['progress'] == 68
    sources[3].data['busy'] = False
    namespace['_poll_diagnostic'](dummy)
    assert dummy._diagnostic['status'] == 'complete'
    assert dummy._diagnostic['progress'] == 100


def test_rebuild_107_nvidia_brand_uses_approved_v109_geometry_on_v106_base():
    glyph = (UI / "Glyph.qml").read_text(encoding="utf-8")
    metric = (UI / "MetricLine.qml").read_text(encoding="utf-8")
    assert 'M 9.5 0 L 9.5 2.89' in glyph
    assert 'kind === "gpu_nvidia" ? pixelScale * (383 / 597) : pixelScale' in glyph
    assert 'readonly property real offsetY: (height - 24 * iconYScale) / 2' in glyph
    assert 'number = number * iconYScale + (relative ? 0 : offsetY)' in glyph
    assert 'number = number * (xCoordinate ? pixelScale : iconYScale)' in glyph
    assert 'fillColor: (glyph.kind === "gpu_amd" || glyph.kind === "gpu_nvidia") ? glyph.ink : "transparent"' in glyph
    assert 'strokeWidth: (glyph.kind === "gpu_amd" || glyph.kind === "gpu_nvidia") ? 0 : glyph.effectiveStroke' in glyph
    assert 'width: 29; height: 29' in metric
    assert 'ShapePath.OddEvenFill' not in glyph
