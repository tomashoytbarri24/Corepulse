# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_data_files, collect_dynamic_libs, copy_metadata

root = Path(SPECPATH).parent
datas = [(str(root / 'ui'), 'ui'), (str(root / 'bin'), 'bin'),
         (str(root / 'core' / 'tweaks' / 'tweaks_engine.py'), 'core/tweaks'),
         (str(root / 'requirements.txt'), '.'),
         (str(root / 'Reglas para crear Versiones nuevas.txt'), '.'),
         (str(root / 'installer' / 'THIRD_PARTY_NOTICES.txt'), '.')]
hidden = collect_submodules('core') + ['clr', 'pythonnet', 'clr_loader',
    'HardwareMonitor', 'HardwareMonitor.Hardware', 'core.benchmark_gpu', 'PySide6.QtQuick',
    'PySide6.QtQuickControls2', 'PySide6.QtNetwork', 'PySide6.QtMultimedia']
binaries = []
for package in ('HardwareMonitor', 'pythonnet', 'clr_loader'):
    datas += collect_data_files(package)
    binaries += collect_dynamic_libs(package)
for package in ('pythonnet', 'HardwareMonitor', 'psutil', 'PySide6', 'PySide6_Essentials',
                'PySide6_Addons', 'shiboken6', 'cffi', 'clr_loader', 'pycparser'):
    datas += copy_metadata(package)
a = Analysis([str(root / 'main.py')], pathex=[str(root)], binaries=binaries,
    datas=datas, hiddenimports=hidden, hookspath=[], runtime_hooks=[],
    excludes=['tkinter', 'PyQt5', 'PyQt6', 'PySide2', 'pytest'], noarchive=False)
# A Poppler/Conda ICU on a developer's PATH has the same filename as Windows
# ICU but version-suffixed exports. Qt must use the OS library it was built for.
a.binaries = [row for row in a.binaries if 'poppler' not in {p.lower() for p in Path(row[1]).parts}]
pyz = PYZ(a.pure)
common = dict(exclude_binaries=True, debug=False, bootloader_ignore_signals=False,
              strip=False, upx=False, icon=str(root / 'installer' / 'CorePulse.ico'),
              version=str(root / 'installer' / 'version_info.txt'))
app = EXE(pyz, a.scripts, [], name='CorePulse', console=False, uac_admin=False, **common)
worker = EXE(pyz, a.scripts, [], name='CorePulseWorker', console=True, uac_admin=False, **common)
coll = COLLECT(app, worker, a.binaries, a.datas, strip=False, upx=False, name='CorePulse')
