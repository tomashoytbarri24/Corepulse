"""Agrupa redibujos de tamaño CTk por ventana mientras se redimensiona.

V159 conserva el manejador original de CustomTkinter, incluidas sus conversiones
de DPI y posibles extensiones. Sólo aplaza sus llamadas a _draw durante el gesto;
los cambios de color/contenido fuera de ese manejador siguen dibujando normalmente.
La aplicación pasa owner=app para no congelar diálogos ni otras ventanas.
Todas las funciones se invocan desde el hilo de Tk.
"""
from __future__ import annotations

import logging
import weakref

logger = logging.getLogger('CorePulse.Resize')
_installed = False
_active = False  # Compatibilidad con consumidores de set_active(active) de V158.
_owners = weakref.WeakSet()
_dirty = weakref.WeakKeyDictionary()
_original_update_dimensions_event = None
_MISSING = object()
_frame_callbacks = weakref.WeakKeyDictionary()
FRAME_INTERVAL_MS = 16


def _schedule_frame(owner):
    """Pinta el tamaño reciente una vez por frame, incluso durante el gesto.

    Esperar al debounce final dejaba el canvas CTk con el tamaño anterior
    mientras Windows ya había maximizado/restaurado los controles nativos.
    """
    if owner is None or owner in _frame_callbacks:
        return
    reference = weakref.ref(owner)
    def paint():
        window = reference()
        if window is not None:
            _frame_callbacks.pop(window, None)
            flush(owner=window)
    try:
        _frame_callbacks[owner] = owner.after(FRAME_INTERVAL_MS, paint)
    except (AttributeError, RuntimeError):
        pass


def _cancel_frame(owner):
    callback = _frame_callbacks.pop(owner, None)
    if callback is not None:
        try:
            owner.after_cancel(callback)
        except Exception:
            pass


def _resolve_base_class():
    try:
        from customtkinter.windows.widgets.core_widget_classes.ctk_base_class import CTkBaseClass
        return CTkBaseClass
    except ImportError:
        return None


def _window(widget):
    try:
        return widget.winfo_toplevel()
    except Exception:
        return None


def _patched_update_dimensions_event(self, event):
    owner = _window(self) if _owners else None
    if not _active and owner not in _owners:
        return _original_update_dimensions_event(self, event)

    # Dejar al proveedor actualizar dimensiones y ejecutar sus propios efectos.
    # La sustitución dura únicamente esta llamada síncrona y se restaura incluso
    # si el manejador lanza una excepción. No se enlazan callbacks nuevos por píxel.
    previous = vars(self).get('_draw', _MISSING)

    def defer_draw(*args, **kwargs):
        root = owner if owner is not None else _window(self)
        old = _dirty.get(self)
        if old and old[1].get('no_color_updates') is False:
            kwargs['no_color_updates'] = False
        _dirty[self] = (args, dict(kwargs), weakref.ref(root) if root is not None else None)
        _schedule_frame(root)

    self._draw = defer_draw
    try:
        return _original_update_dimensions_event(self, event)
    finally:
        if previous is _MISSING:
            del self._draw
        else:
            self._draw = previous


def install():
    """Instala una sola envoltura antes de crear widgets, conservando el original."""
    global _installed, _original_update_dimensions_event
    if _installed:
        return True
    base_cls = _resolve_base_class()
    if base_cls is None:
        return False
    original = getattr(base_cls, '_corepulse_resize_guard_original', None)
    if original is None:
        original = getattr(base_cls, '_update_dimensions_event', None)
    if not callable(original):
        return False
    _original_update_dimensions_event = original
    base_cls._corepulse_resize_guard_original = original
    base_cls._update_dimensions_event = _patched_update_dimensions_event
    base_cls._corepulse_resize_guard_installed = True
    _installed = True
    return True


def set_active(active, *, owner=None):
    """Agrupa por toplevel; desactivar una ventana no libera ni congela otra."""
    global _active
    if owner is None:
        _active = bool(active)
    elif active:
        _owners.add(owner)
    else:
        _owners.discard(owner)
    if not active:
        for window in list(_frame_callbacks):
            if owner is None or owner is window:
                _cancel_frame(window)
        flush(owner=owner)


def flush(*, owner=None):
    """Dibuja el último tamaño de cada widget pendiente una vez, si aún existe."""
    for widget, (args, kwargs, root_ref) in list(_dirty.items()):
        if owner is not None and (root_ref is None or root_ref() is not owner):
            continue
        # Eliminar antes de dibujar: un evento anidado podrá volver a encolarlo.
        _dirty.pop(widget, None)
        try:
            if widget.winfo_exists():
                widget._draw(*args, **kwargs)
        except Exception:
            logger.debug('No se pudo redibujar un widget pendiente', exc_info=True)


def release(owner):
    """Retira la ventana al cerrarla, sin redibujar widgets en destrucción."""
    _owners.discard(owner)
    _cancel_frame(owner)
    for widget, (_, _, root_ref) in list(_dirty.items()):
        if root_ref is not None and root_ref() is owner:
            _dirty.pop(widget, None)


def is_active(owner=None):
    return bool(_active or (owner in _owners if owner is not None else _owners))


def is_installed():
    return _installed


def pending_count():
    return len(_dirty)

# V481: política de refresco consolidada con guardas de redibujado.
from dataclasses import dataclass
import os
import sys


@dataclass(frozen=True)
class UIRefreshPolicy:
    display_hz: int
    target_hz: int
    frame_ms: int
    source: str


def _windows_primary_refresh_hz() -> int | None:
    """Lee la frecuencia actual del display primario sin dependencias externas."""
    if sys.platform != 'win32':
        return None
    try:
        import ctypes
        from ctypes import wintypes

        CCHDEVICENAME = 32
        CCHFORMNAME = 32
        ENUM_CURRENT_SETTINGS = -1

        class POINTL(ctypes.Structure):
            _fields_ = [('x', wintypes.LONG), ('y', wintypes.LONG)]

        class _PrinterFields(ctypes.Structure):
            _fields_ = [
                ('dmOrientation', ctypes.c_short),
                ('dmPaperSize', ctypes.c_short),
                ('dmPaperLength', ctypes.c_short),
                ('dmPaperWidth', ctypes.c_short),
                ('dmScale', ctypes.c_short),
                ('dmCopies', ctypes.c_short),
                ('dmDefaultSource', ctypes.c_short),
                ('dmPrintQuality', ctypes.c_short),
            ]

        class _DisplayFields(ctypes.Structure):
            _fields_ = [
                ('dmPosition', POINTL),
                ('dmDisplayOrientation', wintypes.DWORD),
                ('dmDisplayFixedOutput', wintypes.DWORD),
            ]

        class _ModeUnion(ctypes.Union):
            _fields_ = [('printer', _PrinterFields), ('display', _DisplayFields)]

        class DEVMODEW(ctypes.Structure):
            _anonymous_ = ('mode',)
            _fields_ = [
                ('dmDeviceName', wintypes.WCHAR * CCHDEVICENAME),
                ('dmSpecVersion', wintypes.WORD),
                ('dmDriverVersion', wintypes.WORD),
                ('dmSize', wintypes.WORD),
                ('dmDriverExtra', wintypes.WORD),
                ('dmFields', wintypes.DWORD),
                ('mode', _ModeUnion),
                ('dmColor', ctypes.c_short),
                ('dmDuplex', ctypes.c_short),
                ('dmYResolution', ctypes.c_short),
                ('dmTTOption', ctypes.c_short),
                ('dmCollate', ctypes.c_short),
                ('dmFormName', wintypes.WCHAR * CCHFORMNAME),
                ('dmLogPixels', wintypes.WORD),
                ('dmBitsPerPel', wintypes.DWORD),
                ('dmPelsWidth', wintypes.DWORD),
                ('dmPelsHeight', wintypes.DWORD),
                ('dmDisplayFlags', wintypes.DWORD),
                ('dmDisplayFrequency', wintypes.DWORD),
                ('dmICMMethod', wintypes.DWORD),
                ('dmICMIntent', wintypes.DWORD),
                ('dmMediaType', wintypes.DWORD),
                ('dmDitherType', wintypes.DWORD),
                ('dmReserved1', wintypes.DWORD),
                ('dmReserved2', wintypes.DWORD),
                ('dmPanningWidth', wintypes.DWORD),
                ('dmPanningHeight', wintypes.DWORD),
            ]

        mode = DEVMODEW()
        mode.dmSize = ctypes.sizeof(DEVMODEW)
        ok = ctypes.windll.user32.EnumDisplaySettingsW(None, ENUM_CURRENT_SETTINGS, ctypes.byref(mode))
        if not ok:
            return None
        hz = int(mode.dmDisplayFrequency or 0)
        return hz if 30 <= hz <= 1000 else None
    except Exception:
        return None


def get_ui_refresh_policy() -> UIRefreshPolicy:
    """Devuelve una política conservadora con tope de 120 Hz para Tk/CTk.

    ``COREPULSE_UI_HZ`` permite diagnóstico manual, pero siempre se limita a
    60..120 Hz para evitar que la interfaz compita con los juegos por CPU.
    """
    override = str(os.environ.get('COREPULSE_UI_HZ', '') or '').strip()
    if override:
        try:
            display_hz = max(30, min(1000, int(float(override))))
            source = 'env'
        except Exception:
            display_hz = _windows_primary_refresh_hz() or 60
            source = 'windows' if display_hz != 60 else 'fallback'
    else:
        detected = _windows_primary_refresh_hz()
        display_hz = detected or 60
        source = 'windows' if detected else 'fallback'

    # 60 Hz conserva el coste histórico; 75/90/120/144/165/240 ganan pasos
    # adicionales, con techo de 120 Hz para CustomTkinter.
    target_hz = max(60, min(120, int(display_hz)))
    frame_ms = max(8, int(1000.0 / float(target_hz)))
    return UIRefreshPolicy(display_hz=display_hz, target_hz=target_hz, frame_ms=frame_ms, source=source)


DEFAULT_NAVIGATION_DEBOUNCE_MS = 4
