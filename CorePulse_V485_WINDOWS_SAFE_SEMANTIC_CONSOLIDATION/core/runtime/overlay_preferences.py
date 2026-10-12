"""Carga y guarda las preferencias persistentes del overlay de CorePulse."""
from __future__ import annotations

import json
from threading import RLock

from core.runtime_paths import data_path, data_dir
from core.global_hotkeys import DEFAULT_TOGGLE_HOTKEY, normalize_hotkey_config

DATA_DIR = data_dir()
PREFERENCES_FILE = data_path('overlay_preferences.json')
DEFAULTS = {
    'layout': 'FULL',
    'x': 20,
    'y': 20,
    'pixel': 1,
    'show_fps': True,
    'show_frametime': True,
    'show_1pct_low': True,
    'show_cpu': True,
    'show_ram': True,
    'show_gpu': True,
    'show_storage': True,
    'toggle_hotkey': DEFAULT_TOGGLE_HOTKEY.as_dict(),
}
_lock = RLock()
_cache = None
_cache_mtime_ns = None


def normalize_preferences(data=None):
    src = data if isinstance(data, dict) else {}
    out = dict(DEFAULTS)
    layout = str(src.get('layout', out['layout']) or '').upper().strip()
    out['layout'] = layout if layout in {'FULL', 'COMPACT'} else 'FULL'
    for key, lo, hi in (('x', 0, 5000), ('y', 0, 5000), ('pixel', 1, 4)):
        try:
            out[key] = max(lo, min(hi, int(src.get(key, out[key]))))
        except Exception:
            out[key] = DEFAULTS[key]
    for key in ('show_fps', 'show_frametime', 'show_1pct_low', 'show_cpu', 'show_ram', 'show_gpu', 'show_storage'):
        value = src.get(key, DEFAULTS[key])
        out[key] = value if isinstance(value, bool) else DEFAULTS[key]
    out['toggle_hotkey'] = normalize_hotkey_config(src.get('toggle_hotkey'), DEFAULT_TOGGLE_HOTKEY)
    return out


def _mtime():
    try:
        return PREFERENCES_FILE.stat().st_mtime_ns
    except Exception:
        return None


def load_overlay_preferences(force=False):
    global _cache, _cache_mtime_ns
    with _lock:
        mtime = _mtime()
        if not force and _cache is not None and mtime == _cache_mtime_ns:
            return dict(_cache)
        try:
            raw = json.loads(PREFERENCES_FILE.read_text(encoding='utf-8')) if PREFERENCES_FILE.exists() else {}
        except Exception:
            raw = {}
        _cache = normalize_preferences(raw)
        _cache_mtime_ns = mtime
        return dict(_cache)


def save_overlay_preferences(data):
    global _cache, _cache_mtime_ns
    value = normalize_preferences(data)
    with _lock:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        tmp = PREFERENCES_FILE.with_suffix('.json.tmp')
        tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
        tmp.replace(PREFERENCES_FILE)
        _cache = value
        _cache_mtime_ns = _mtime()
    return dict(value)


def reset_overlay_preferences():
    return save_overlay_preferences(DEFAULTS)


# V482: fusión sin cambios de lógica desde core/runtime/overlay_theme.py
# Código refactorizado: nombres estables y documentación en español.
from core.version import VERSION_LABEL
WHITE = 'F8FAFC'
LABEL = 'D7E1EE'
DIM = '7C8EA6'
DIM_LIGHT = 'A8B6C8'
FPS = '2DD4FF'
CPU = '38BDF8'
RAM = '34D399'
GPU = 'D946EF'
SSD = 'F59E0B'
PANEL_BG = 594205
PANEL_FG = 16317180
OSD_X = 20
OSD_Y = 20
OSD_PIXEL = 1
DIVIDER_COLOR = '355A7A'
DIVIDER = '============================================'

def _fmt(value, digits=0, suffix=''):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return 'N/A'
    return f'{value:.{digits}f}{suffix}'

def _tags():
    return f'<C0={FPS}><C1={CPU}><C2={RAM}><C3={GPU}><C4={SSD}><C5={WHITE}><C6={LABEL}><C7={DIM}><C8={DIM_LIGHT}><C10={DIVIDER_COLOR}>\r'

def _compact(data, prefs):
    lines = [_tags(), f"<C5>COREPULSE<C>  <C8>{data.get('exe') or 'Aplicacion 3D'}<C>"]
    frame = []
    if prefs.get('show_fps', True):
        frame.append(f"<C6>FPS<C> <C0>{_fmt(data.get('fps'), 0)}<C>")
    if prefs.get('show_frametime', True):
        frame.append(f"<C6>FT<C> <C0>{_fmt(data.get('frametime'), 2, ' ms')}<C>")
    if prefs.get('show_1pct_low', True):
        frame.append(f"<C6>1% LOW<C> <C0>{_fmt(data.get('low_1'), 0)}<C>")
    if frame:
        lines.append('   '.join(frame))
    comp = []
    if prefs.get('show_cpu', True):
        comp.append(f"<C6>CPU<C> <C1>{_fmt(data.get('cpu_usage'), 0, '%')} {_fmt(data.get('cpu_temp'), 0, 'C')}<C>")
    if prefs.get('show_ram', True):
        comp.append(f"<C6>RAM<C> <C2>{_fmt(data.get('ram_usage'), 0, '%')}<C>")
    if prefs.get('show_gpu', True):
        comp.append(f"<C6>GPU<C> <C3>{_fmt(data.get('gpu_usage'), 0, '%')} {_fmt(data.get('gpu_temp'), 0, 'C')}<C>")
    if prefs.get('show_storage', True):
        comp.append(f"<C6>SSD<C> <C4>{_fmt(data.get('ssd_temp'), 0, 'C')} {_fmt(data.get('ssd_life'), 0, '%')}<C>")
    if comp:
        lines.append('   '.join(comp))
    if len(lines) <= 2:
        lines.append('<C7>Sin métricas seleccionadas<C>')
    lines.append('<C7>REAL_OR_NA · RTSS<C>')
    return '\n'.join(lines)

def build_original_overlay(data, prefs=None):
    prefs = prefs if isinstance(prefs, dict) else {}
    if str(prefs.get('layout', 'FULL')).upper() == 'COMPACT':
        return _compact(data, prefs)
    lines = [_tags(), '<C5>COREPULSE<C>                              <C8>RTSS<C>', f"<C6>{data.get('exe') or 'Aplicacion 3D'}<C>"]
    if prefs.get('show_fps', True) or prefs.get('show_frametime', True) or prefs.get('show_1pct_low', True):
        lines += [f'<C10>{DIVIDER}<C>', '<C8>FRAME PRESENTATION<C>']
        row = []
        if prefs.get('show_fps', True):
            row.append(f"<C6>FPS<C> <C0>{_fmt(data.get('fps'), 0)}<C>")
        if prefs.get('show_frametime', True):
            row.append(f"<C6>FT<C> <C0>{_fmt(data.get('frametime'), 2, ' ms')}<C>")
        if row:
            lines.append('                 '.join(row))
        if prefs.get('show_1pct_low', True):
            lines.append(f"<C6>1% LOW<C> <C0>{_fmt(data.get('low_1'), 0)}<C>")
    comp = []
    secondary = []
    if prefs.get('show_cpu', True):
        comp.append(f"<C6>CPU<C> <C1>{_fmt(data.get('cpu_usage'), 0, '%')} {_fmt(data.get('cpu_temp'), 0, 'C')}<C>")
        secondary.append(f"<C6>CPU GHz<C> <C1>{_fmt(data.get('cpu_ghz'), 2)}<C>")
    if prefs.get('show_ram', True):
        comp.append(f"<C6>RAM<C> <C2>{_fmt(data.get('ram_usage'), 0, '%')}<C>")
    if prefs.get('show_gpu', True):
        comp.append(f"<C6>GPU<C> <C3>{_fmt(data.get('gpu_usage'), 0, '%')} {_fmt(data.get('gpu_temp'), 0, 'C')}<C>")
        secondary.append(f"<C6>GPU HOT<C> <C3>{_fmt(data.get('gpu_hotspot'), 0, 'C')}<C>")
    if prefs.get('show_storage', True):
        comp.append(f"<C6>SSD<C> <C4>{_fmt(data.get('ssd_temp'), 0, 'C')}<C>")
        secondary.append(f"<C6>SSD LIFE<C> <C4>{_fmt(data.get('ssd_life'), 0, '%')}<C>")
    if comp:
        lines += [f'<C10>{DIVIDER}<C>', '<C8>HARDWARE<C>', '    '.join(comp)]
        if secondary:
            lines.append('   <C8>•<C>   '.join(secondary))
    if len(lines) <= 3:
        lines.append('<C7>Sin métricas seleccionadas<C>')
    lines += [f'<C10>{DIVIDER}<C>', '<C6>Estado<C>  <C0>RTSS conectado<C>', f'<C7>CorePulse {VERSION_LABEL} · REAL_OR_NA<C>']
    return '\n'.join(lines)
