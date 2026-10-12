# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller ONEDIR de CorePulse V404.

El build incluye todas las dependencias que pertenecen al producto. Sólo quedan
externos los componentes que por diseño son instalaciones/servicios del sistema
(RTSS, PawnIO, Ookla CLI y credenciales de IA).
"""
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules, copy_metadata

SPEC_DIR = Path(SPECPATH).resolve()
ROOT = SPEC_DIR.parent

datas = [
    (str(ROOT / "assets"), "assets"),
    # Solo helpers necesarios para ejecutar CorePulse congelado.
    # Las sondas manuales de diagnóstico viven en herramientas/diagnostico,
    # están en el ZIP de código fuente, pero NO en el ejecutable final.
    (str(ROOT / "tools" / "cpu_temp_package_probe.py"), "tools"),
    (str(ROOT / "tools" / "validate_python_runtime.py"), "tools"),
    (str(ROOT / ".env.example"), "."),
    (str(ROOT / "Instalar_Speedtest_Ookla.bat"), "."),
    # Recursos del host local de IA. En un PC limpio el manager puede preparar
    # llama.cpp desde estos scripts o usar su bootstrap portable en AppData.
    (str(ROOT / "CorePulse_AI_Model_Host"), "CorePulse_AI_Model_Host"),
    (str(ROOT / "CorePulse_AI_Server" / ".env.example"), "CorePulse_AI_Server"),
]
binaries = []
hiddenimports = [
    "HardwareMonitor",
    "clr", "pythonnet", "clr_loader",
    "wmi", "win32api", "win32com", "pythoncom", "pywintypes",
    "send2trash", "send2trash.win", "send2trash.win.modern", "send2trash.win.legacy",
    "dotenv", "pystray", "pystray._win32",
    "core.directx_scene", "core.directx_benchmark",
    "fastapi", "uvicorn", "pydantic",
    "CorePulse_AI_Server",
    "CorePulse_AI_Server.app",
    "CorePulse_AI_Server.app.main",
    "CorePulse_AI_Server.app.config",
    "CorePulse_AI_Server.app.evidence",
    "CorePulse_AI_Server.app.model_gateway",
    "CorePulse_AI_Server.app.store",
]

# Paquetes con imports dinámicos habituales.
for package in ("wmi", "win32com", "pystray", "dotenv", "send2trash", "fastapi", "uvicorn", "pydantic", "starlette"):
    try:
        hiddenimports += collect_submodules(package)
    except Exception:
        pass

# V478: módulos repartidos físicamente; mantener imports core.foo/gui.foo
# incluidas rutas consultadas dinámicamente en runtime.
for package, sample in (('core', 'core.telemetry_lhm'),
                        ('gui', 'gui.ai_status_card')):
    # No generar un EXE incompleto si PyInstaller no ve los módulos movidos.
    discovered = collect_submodules(package)
    if sample not in discovered:
        raise RuntimeError(f'El empaquetador no detecta {sample}; abortando EXE para evitar fallos de importación.')
    hiddenimports += discovered

# HardwareMonitor instala LibreHardwareMonitorLib.dll y sus dependencias como
# package-data bajo HardwareMonitor/lib. Esto es CRÍTICO para temperaturas/GPU.
for package in ("HardwareMonitor", "pythonnet", "clr_loader", "customtkinter"):
    try:
        pkg_datas, pkg_binaries, pkg_hidden = collect_all(package)
        datas += pkg_datas
        binaries += pkg_binaries
        hiddenimports += pkg_hidden
    except Exception as exc:
        print(f"[CorePulse.spec] ERROR recolectando {package}: {exc}")

# Algunos SDK consultan su metadata en tiempo de ejecución.
for package in ("pythonnet", "HardwareMonitor"):
    try:
        datas += copy_metadata(package)
    except Exception:
        pass

hiddenimports = sorted(set(hiddenimports))

a = Analysis(
    [str(ROOT / "corepulse_launcher.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(ROOT / "build" / "runtime_hooks" / "corepulse_frozen_runtime.py")],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CorePulse",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(ROOT / "assets" / "CorePulseTaskbar.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="CorePulse",
)
