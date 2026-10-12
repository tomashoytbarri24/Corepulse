"""Preparación controlada del stack de sensores de CorePulse.

- Descarga la release oficial y fijada de LibreHardwareMonitor a AppData.
- Si PawnIO no está instalado, solicita confirmación explícita antes de instalarlo.

La instalación de PawnIO modifica Windows y por eso nunca se ejecuta sin un Sí
expreso del usuario.
"""
from __future__ import annotations

import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from core.lhm_official import ensure_official_lhm
# V482: símbolo disponible localmente

_MB_YESNO = 0x00000004
_MB_ICONQUESTION = 0x00000020
_MB_ICONINFORMATION = 0x00000040
_IDYES = 6


def _state_dir() -> Path:
    base = os.environ.get('LOCALAPPDATA')
    root = Path(base) / 'CorePulse' / 'state' if base else Path.home() / '.corepulse' / 'state'
    root.mkdir(parents=True, exist_ok=True)
    return root


def _write_status(payload: dict) -> None:
    try:
        (_state_dir() / 'sensor_stack_v380.json').write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8'
        )
    except Exception:
        pass


def _message(text: str, *, yes_no: bool = False, title: str = 'CorePulse — sensores') -> int:
    if not sys.platform.startswith('win'):
        return 0
    flags = (_MB_YESNO | _MB_ICONQUESTION) if yes_no else _MB_ICONINFORMATION
    try:
        return int(ctypes.windll.user32.MessageBoxW(None, str(text), str(title), flags))
    except Exception:
        return 0


def _install_pawnio_with_consent() -> dict:
    """Instala PawnIO por WinGet después de confirmación explícita."""
    before = pawnio_status()
    if before.get('installed'):
        return {'ok': True, 'changed': False, 'before': before, 'after': before, 'error': None}

    answer = _message(
        'CorePulse detectó que falta PawnIO.\n\n'
        'En este equipo AMD, LibreHardwareMonitor lo necesita para acceder a la '
        'temperatura real del procesador. Sin PawnIO CorePulse mantendrá N/A.\n\n'
        '¿Quieres instalar PawnIO 2.2 mediante WinGet ahora?\n\n'
        'Windows mostrará una confirmación UAC. No se instalará nada si eliges No.',
        yes_no=True,
    )
    if answer != _IDYES:
        return {'ok': False, 'changed': False, 'before': before, 'after': before, 'error': 'user_declined'}

    # PowerShell se mantiene oculto; UAC sí debe ser visible para que el usuario
    # confirme el cambio de driver. -Wait evita abrir CorePulse antes de terminar.
    ps = (
        "$argsList=@('install','--id','namazso.PawnIO','-e','--source','winget',"
        "'--accept-package-agreements','--accept-source-agreements','--silent','--disable-interactivity');"
        "$p=Start-Process -FilePath 'winget.exe' -ArgumentList $argsList -Verb RunAs -Wait -PassThru;"
        "exit $p.ExitCode"
    )
    try:
        flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
        proc = subprocess.run(
            ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', ps],
            timeout=180,
            check=False,
            creationflags=flags,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(1.0)
        after = pawnio_status()
        ok = bool(after.get('installed'))
        if ok:
            _message(
                'PawnIO fue detectado correctamente. CorePulse continuará y volverá '
                'a enumerar los sensores de CPU con LibreHardwareMonitor oficial.'
            )
        else:
            _message(
                'La instalación terminó, pero PawnIO aún no aparece como disponible. '
                'Si Windows solicitó reiniciar, reinicia el equipo y vuelve a abrir CorePulse.'
            )
        return {
            'ok': ok,
            'changed': True,
            'before': before,
            'after': after,
            'returncode': int(proc.returncode),
            'error': None if ok else f'winget_returncode={proc.returncode}',
        }
    except Exception as exc:
        after = pawnio_status()
        _message(
            'CorePulse no pudo completar la instalación automática de PawnIO.\n\n'
            'Puedes instalarlo manualmente con:\nwinget install --id namazso.PawnIO -e'
        )
        return {
            'ok': bool(after.get('installed')),
            'changed': True,
            'before': before,
            'after': after,
            'error': f'{type(exc).__name__}: {exc}',
        }


def prepare_sensor_stack_interactive() -> dict:
    if not sys.platform.startswith('win'):
        return {'ok': False, 'error': 'Windows requerido'}

    official = ensure_official_lhm(allow_download=True)
    pawnio = _install_pawnio_with_consent()
    result = {
        'ok': bool(official.get('ok')),
        'official_lhm': official,
        'pawnio': pawnio,
        'timestamp': time.time(),
    }
    _write_status(result)
    return result


# V482: fusión sin cambios de lógica desde core/sensors/pawnio_support.py
import os
import subprocess
import sys
from typing import Any


def _registry_detect() -> tuple[bool, str | None]:
    if not sys.platform.startswith('win'):
        return False, None
    try:
        import winreg
    except Exception:
        return False, None

    keys = (
        r"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\PawnIO",
        r"SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\PawnIO",
    )
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        for key_name in keys:
            try:
                with winreg.OpenKey(hive, key_name) as key:
                    try:
                        version = str(winreg.QueryValueEx(key, 'DisplayVersion')[0] or '').strip() or None
                    except Exception:
                        version = None
                    return True, version
            except OSError:
                continue
            except Exception:
                continue
    return False, None


def _service_detect() -> bool:
    if not sys.platform.startswith('win'):
        return False
    try:
        flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
        proc = subprocess.run(
            ['sc.exe', 'query', 'PawnIO'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=3,
            creationflags=flags,
            check=False,
        )
        text = f"{proc.stdout}\n{proc.stderr}".casefold()
        return proc.returncode == 0 and 'pawnio' in text
    except Exception:
        return False


def pawnio_status() -> dict[str, Any]:
    installed_registry, version = _registry_detect()
    service = _service_detect()
    program_files = os.environ.get('ProgramFiles', r'C:\\Program Files')
    install_dir = os.path.join(program_files, 'PawnIO')
    path_exists = os.path.isdir(install_dir) if sys.platform.startswith('win') else False
    installed = bool(installed_registry or service or path_exists)
    return {
        'installed': installed,
        'registry': installed_registry,
        'service': service,
        'install_dir_exists': path_exists,
        'version': version,
        'install_dir': install_dir if path_exists else None,
    }


def missing_cpu_sensor_message() -> str:
    status = pawnio_status()
    if not status.get('installed'):
        return (
            'No se encontró una temperatura CPU real. PawnIO no está instalado; '
            'en este equipo LibreHardwareMonitor puede requerir ese driver para '
            'leer sensores térmicos de bajo nivel. Ejecuta '
            'herramientas\\ia\\06_INSTALAR_PAWNIO_CPU_TEMP.bat y reinicia CorePulse.'
        )
    return (
        'No se encontró una temperatura CPU real aun con PawnIO detectado. '
        'Ejecuta herramientas\\ia\\07_DIAGNOSTICAR_SENSOR_CPU.bat para enumerar los sensores reales '
        'sin estimar ni sustituir la temperatura.'
    )
