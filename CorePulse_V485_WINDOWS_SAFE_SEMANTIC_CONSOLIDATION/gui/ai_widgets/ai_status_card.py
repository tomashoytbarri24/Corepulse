"""Tarjeta de estado de CorePulse AI para el Resumen principal."""
from __future__ import annotations

import threading
import time
from datetime import datetime

from core.ai_client import service_status
from core.theme_manager import color as theme_color
from gui.widget_updates import configure_changed

GREEN = '#22d995'
CYAN = '#14b8ff'
AMBER = '#f5b83d'
RED = '#ff5d6c'
TEXT = theme_color('#f4f7fb')
TEXT_2 = theme_color('#b8c4d4')
MUTED = theme_color('#7f91a8')
BORDER = theme_color('#1b3048')
SURFACE2 = theme_color('#102238')
FONT = 'Segoe UI'


def _cfg(widget, **kwargs):
    if widget is None:
        return
    try:
        configure_changed(widget, **kwargs)
    except Exception:
        try:
            widget.configure(**kwargs)
        except Exception:
            pass


def render_ai_card(app, status=None):
    """Actualiza únicamente la tarjeta de CorePulse AI del encabezado."""
    status = status if isinstance(status, dict) else None
    state = str((status or {}).get('state') or '').upper()
    if not getattr(app, '_ai_local_enabled', True):
        tone, main = MUTED, 'COREPULSE AI APAGADA'
    elif status is not None and status.get('ok') and bool(status.get('model_ready')):
        tone, main = GREEN, 'IA NUBE CONECTADA'
    elif state == 'CLOUD_NOT_CONFIGURED':
        tone, main = AMBER, 'CONFIGURAR IA NUBE'
    elif state == 'CLOUD_CONSENT_REQUIRED':
        tone, main = AMBER, 'IA NUBE SIN PERMISO'
    elif status is None:
        tone, main = AMBER, 'COMPROBANDO IA NUBE'
    elif status is not None and status.get('ok'):
        tone, main = AMBER, 'IA NUBE SIN MODELO'
    else:
        tone, main = RED, 'IA NUBE NO DISPONIBLE'

    _cfg(getattr(app, '_ai_accent', None), fg_color=tone)
    _cfg(getattr(app, '_ai_status', None), text=main, text_color=TEXT)
    _cfg(getattr(app, '_ai_card', None), border_color=BORDER)
    # El brillo sigue el estado real de la IA, no un verde fijo.
    ai_card = getattr(app, '_ai_card', None)
    if ai_card is not None:
        before = getattr(ai_card, '_cp_hover_accent', None)
        ai_card._cp_hover_accent = tone
        if before != tone and getattr(ai_card, '_cp_hover_active', False):
            try:
                from gui.card_workspace_surface import repaint_card_hover
                repaint_card_hover(ai_card, getattr(app, 'workspace_background', None))
            except Exception:
                pass
    model_info = str((status or {}).get('model_name') or '').rsplit('/', 1)[-1][:34]
    if not getattr(app, '_ai_local_enabled', True):
        detail = 'IA apagada · Sin conexión ni modelo local activo'
    elif status is None:
        detail = 'Servicio cloud pendiente de comprobación'
    elif state == 'CLOUD_NOT_CONFIGURED':
        detail = 'Define el servidor HTTPS desde la pestaña CorePulse AI'
    elif state == 'CLOUD_CONSENT_REQUIRED':
        detail = 'Se requiere autorización explícita para enviar datos'
    elif status.get('ok') and status.get('model_ready'):
        detail = f'Modelo remoto listo · {model_info}' if model_info else 'Modelo remoto listo'
    elif status.get('ok'):
        detail = 'Servidor cloud accesible · Modelo generativo no disponible'
    else:
        detail = 'CorePulse AI Cloud no disponible; el diagnóstico local sigue activo'
    _cfg(getattr(app, '_ai_detail', None), text=detail, text_color=TEXT_2)
    app._ai_runtime_status = ({'ok': False, 'state': 'DISABLED'}
                              if not getattr(app, '_ai_local_enabled', True)
                              else status or {'ok': None, 'state': 'CHECKING'})
    canvas = getattr(app, '_header_ai_native_canvas', None)
    if canvas is not None:
        try:
            canvas.set_power_enabled(getattr(app, '_ai_local_enabled', True))
        except Exception:
            pass


def refresh_ai_status_async(app, *, force=False):
    """Consulta /v1/status fuera del hilo Tk y refleja el resultado en la tarjeta."""
    if not getattr(app, 'is_running', False):
        return False
    if not getattr(app, '_ai_local_enabled', True):
        return False
    now = time.monotonic()
    last = float(getattr(app, '_ai_status_last_started', 0.0) or 0.0)
    if not force and now - last < 6.0:
        return False
    if getattr(app, '_ai_status_refreshing', False):
        return False
    app._ai_status_refreshing = True
    app._ai_status_last_started = now

    def worker():
        try:
            result = service_status()
        except Exception as exc:
            result = {'ok': False, 'state': 'OFFLINE', 'error': f'{type(exc).__name__}: {exc}'}

        def commit():
            app._ai_status_refreshing = False
            if not getattr(app, 'is_running', False):
                return
            render_ai_card(app, result)
            app._ai_status_checked_at = datetime.now().isoformat(timespec='seconds')

        try:
            app.after(0, commit)
        except Exception:
            app._ai_status_refreshing = False

    threading.Thread(target=worker, daemon=True, name='CorePulse-AI-Status').start()
    return True
