"""Certificación de FPS REALES exclusivamente desde RTSS Shared Memory.

No estima FPS con Hz de pantalla, benchmarks ni otras fuentes; sin lectura fresca y
válida de RTSS devuelve None (N/A en la interfaz), nunca un número supuesto.
"""
from __future__ import annotations

import math
import threading
import time
from pathlib import Path

from core.version import VERSION_LABEL as VERSION
from core.runtime_paths import resource_root
from core.rtss_osd import RTSSSharedMemory, start_rtss

POLICY = 'REAL_FPS_OR_NA_ONLY'
RTSS_FRESHNESS_MS = 2500


def _finite(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return parsed if math.isfinite(parsed) else None


def _fps_plausible(value):
    v = _finite(value)
    return v is not None and 0.0 < v <= 2000.0


def _frametime_plausible(value):
    v = _finite(value)
    return v is not None and 0.0 < v < 1000.0


class CertifiedFPSProvider:
    """Expone sólo FPS del proceso activo medidos y validados mediante RTSS."""

    def __init__(self, project_root=None):
        self.project_root = Path(project_root) if project_root else resource_root()
        self._lock = threading.RLock()
        self.rtss = RTSSSharedMemory()
        if not self.rtss.available:
            start_rtss()
            time.sleep(0.8)
        self.last = self._empty('UNAVAILABLE', 'NO_CAPTURE_YET')

    @staticmethod
    def _empty(quality, reason):
        return {
            'version': VERSION, 'policy': POLICY, 'fps': None,
            'fps_instant': None, 'frametime_ms': None, 'fps_1pct_low': None,
            'pid': None, 'process_name': None, 'quality': quality, 'reason': reason,
            'source': None, 'source_primary': 'RTSS Shared Memory',
            'source_crosscheck': None, 'rtss_age_ms': None,
            'sensor_timestamp': None, 'snapshot_timestamp': time.time(),
            'crosscheck': None, 'synthetic': False, 'estimated': False,
            'interpolated': False,
        }

    def _rtss_app(self):
        if not self.rtss.available:
            return None
        result = self.rtss.active_app(freshness_ms=RTSS_FRESHNESS_MS)
        return result if isinstance(result, dict) else None

    def get_snapshot(self, rtss_app=None):
        with self._lock:
            now = time.time()
            app = rtss_app if isinstance(rtss_app, dict) else self._rtss_app()
            if not app or app.get('quality') != 'VALID':
                self.last = self._empty('UNAVAILABLE', 'NO_FRESH_3D_APP_IN_RTSS')
                return dict(self.last)
            age_ms = _finite(app.get('age_ms'))
            if age_ms is not None and (age_ms < 0 or age_ms > RTSS_FRESHNESS_MS):
                self.last = self._empty('UNAVAILABLE', 'STALE_RTSS_SAMPLE')
                return dict(self.last)
            fps_1s = _finite(app.get('fps_1s'))
            fps_inst = _finite(app.get('fps'))
            fps = fps_1s if _fps_plausible(fps_1s) else fps_inst
            if not _fps_plausible(fps):
                self.last = self._empty('UNAVAILABLE', 'RTSS_FPS_NOT_VALID')
                return dict(self.last)
            frametime = _finite(app.get('frametime_ms'))
            if not _frametime_plausible(frametime):
                frametime = None
            low_1 = _finite(app.get('fps_1pct_low'))
            pid = app.get('pid')
            sensor_ts = now - age_ms / 1000.0 if age_ms is not None else None
            self.last = {
                'version': VERSION, 'policy': POLICY,
                'fps': round(fps, 3),
                'fps_instant': round(fps_inst, 3) if _fps_plausible(fps_inst) else None,
                'frametime_ms': round(frametime, 3) if frametime is not None else None,
                'fps_1pct_low': round(low_1, 3) if _fps_plausible(low_1) else None,
                'pid': int(pid) if pid else None, 'process_name': app.get('name'),
                'quality': 'VALID_RTSS', 'reason': None,
                'source': 'RTSS Shared Memory', 'source_primary': 'RTSS Shared Memory',
                'source_crosscheck': None, 'rtss_age_ms': age_ms,
                'sensor_timestamp': sensor_ts, 'snapshot_timestamp': now,
                'crosscheck': None, 'synthetic': False, 'estimated': False,
                'interpolated': False,
            }
            return dict(self.last)

    def runtime_capability(self):
        info = self.rtss.raw_diagnostic()
        return {
            'version': VERSION, 'policy': POLICY,
            'rtss': {
                'available': bool(info.get('ok')),
                'version': self.rtss.version if info.get('ok') else None,
                'diagnostic': info,
            },
            'rules': {
                'primary_source': 'RTSS Shared Memory',
                'no_refresh_rate_fallback': True,
                'no_estimated_fps': True,
                'no_interpolation': True,
                'missing_real_fps_means_na': True,
            },
        }

    def stop(self):
        try:
            self.rtss.close()
        except Exception:
            pass


_SINGLETON = None
_SINGLETON_LOCK = threading.Lock()


def get_fps_provider():
    global _SINGLETON
    with _SINGLETON_LOCK:
        if _SINGLETON is None:
            _SINGLETON = CertifiedFPSProvider()
        return _SINGLETON


def get_certified_fps(rtss_app=None):
    return get_fps_provider().get_snapshot(rtss_app=rtss_app)


def get_fps_runtime_capability():
    return get_fps_provider().runtime_capability()


def stop_fps_provider():
    global _SINGLETON
    with _SINGLETON_LOCK:
        provider, _SINGLETON = _SINGLETON, None
    if provider is not None:
        provider.stop()
