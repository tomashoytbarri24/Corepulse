"""Construye la presentación visual del Dashboard principal de CorePulse.

Este módulo SOLO modifica presentación. No obtiene telemetría, no altera valores,
no calcula salud y no reemplaza ninguna autoridad de diagnóstico. Los widgets
siguen consumiendo exactamente los mismos datos reales del runtime.
"""
from __future__ import annotations
from gui.widget_updates import configure_changed
from gui.professional_visuals import StatusSymbol
from gui.professional_visuals import HeaderIdentityCanvas
from gui.ai_native_status_canvas import AIStatusCanvas
from gui.workspace_background import _blend as _ws_blend, _palette as _ws_palette, native_surface_color_at
from core.theme_manager import color as theme_color, brand_symbol_path, sidebar_assets_path, theme_action_label, role_color

import time
import math
import types
import threading
from pathlib import Path
from core.runtime_paths import resource_root

import psutil
import customtkinter as ctk
import tkinter as tk
from PIL import Image

from core.version import VERSION_LABEL
from core.device_identity import collect_device_identity

VERSION = VERSION_LABEL
DESIGN_ID = 'COREPULSE_DASHBOARD_REFERENCE'

# V128 — contrato visual de temas. Las superficies estructurales del Dashboard
# consumen directamente los roles EXACTOS de la paleta activa. No se infieren
# desde azules heredados y no se aplican mezclas, darken/lighten ni filtros.
# Esta misma semántica es la que usa la vista previa de Temas.
COLORS = {
    'app': role_color('bg'),
    'sidebar': role_color('sidebar'),
    'surface': role_color('glass_surface'),
    'surface_2': role_color('glass_surface_2'),
    'surface_hover': role_color('glass_hover'),
    'border': role_color('glass_border'),
    'border_soft': role_color('glass_border'),
    'text': role_color('text'),
    'text_2': role_color('text_2'),
    'muted': role_color('muted'),
    'primary': role_color('accent'),
    'primary_dark': role_color('accent_2'),
    'green': '#16d98b',
    'amber': '#f3b54a',
    'red': '#ff5d6c',
    'purple': '#a064ff',
    'track': role_color('glass_track'),
}
FONT = 'Segoe UI'
ICON_FONT = 'Segoe UI Symbol'


def _dashboard_workspace_left(app, root_width):
    main = getattr(app, 'main_content', None)
    try:
        if main is not None and main.winfo_exists() and main.winfo_ismapped():
            return int(main.winfo_rootx() - app.winfo_rootx())
    except Exception:
        pass
    workspace = getattr(app, 'workspace_background', None)
    try:
        if workspace is not None and getattr(workspace, '_workspace_left', None) is not None:
            return int(workspace._workspace_left)
    except Exception:
        pass
    return int(max(0, int(root_width) * 0.205))


def _native_card_fill(app, widget, *, lift=0.58):
    """Color de tarjeta alineado con la superficie maestra real.

    Toma el tono exacto del workspace en el centro visible de la tarjeta y lo
    eleva sutilmente con el material glass propio de CorePulse. Así la tarjeta
    se integra con la capa maestra sin perder jerarquía visual.
    """
    fallback = COLORS['surface']
    try:
        if widget is None or not widget.winfo_exists() or not app.winfo_exists():
            return fallback
        root_width = max(1, int(app.winfo_width()))
        root_height = max(1, int(app.winfo_height()))
        x = int(widget.winfo_rootx() - app.winfo_rootx()) + max(1, int(widget.winfo_width()) // 2)
        y = int(widget.winfo_rooty() - app.winfo_rooty()) + max(1, int(widget.winfo_height()) // 2)
        base = native_surface_color_at(
            x, y, root_width, root_height,
            palette=_ws_palette(),
            workspace_left=_dashboard_workspace_left(app, root_width),
        )
        return base  # V436: coincidencia exacta, sin tinte glass opaco
    except Exception:
        return fallback


def _native_card_hover(fill, *, accent=None):
    try:
        return fill  # V436: el hover no vuelve a oscurecer la tarjeta
    except Exception:
        return COLORS['surface_hover']


def _apply_native_card_surface(card, fill, *, hover=None, border_width=0):
    if card is None:
        return False
    fill = str(fill or COLORS['surface'])
    hover = str(hover or _native_card_hover(fill))
    _safe_config(card, fg_color=fill, bg_color=fill, border_color=fill, border_width=border_width)
    card._cp_surface_normal = fill
    card._cp_surface_hover = fill
    card._cp_seamless_surface = True
    return True


def _sync_native_card_surfaces(app):
    """Replica en las tarjetas la misma lógica aprobada para gráficos."""
    if app is None or not getattr(app, 'is_running', False):
        return False
    touched = False

    def active_color(widget, default):
        try:
            c = widget.cget('fg_color')
            return str(c if isinstance(c, str) else c[0]) if c else default
        except (AttributeError, TypeError, IndexError):
            return default

    ai_card = getattr(app, '_ai_card', None)
    ai_accent = active_color(getattr(app, '_ai_accent', None), COLORS['green'])
    if ai_card is not None:
        # CorePulse AI comparte el fondo del encabezado; no recibe superficie de tarjeta.
        ai_card._cp_hover_accent = ai_accent

    status_cards = tuple(getattr(app, '_status_cards', ()) or ())
    accents = (COLORS['green'], COLORS['amber'], COLORS['primary'], COLORS['purple'])
    for index, card in enumerate(status_cards):
        fill = _native_card_fill(app, card, lift=0.57)
        accent = accents[index] if index < len(accents) else COLORS['primary']
        if index == 0:
            accent = (getattr(card, '_cp_hover_accent', accent)
                      if getattr(card, '_cp_hover_active', False)
                      else active_color(getattr(card, '_cp_health_accent', None), accent))
        touched |= _apply_native_card_surface(card, fill, hover=_native_card_hover(fill, accent=accent))
        card._cp_hover_accent = accent
        for name in ('_cp_health_shell', '_cp_health_body', '_cp_health_metrics_row', '_cp_health_status_strip'):
            widget = getattr(card, name, None)
            if widget is not None:
                _safe_config(widget, fg_color=fill, bg_color=fill)
        for widget in getattr(card, '_cp_health_background_labels', ()) or ():
            _safe_config(widget, bg_color=fill)
        _safe_config(getattr(card, '_cp_health_pill', None), bg_color=fill)
        _safe_config(getattr(card, '_cp_icon_label', None), bg_color=fill)

    for card, accent in (
        (getattr(app, 'card_cpu', None), COLORS['primary']),
        (getattr(app, 'card_ram', None), COLORS['green']),
        (getattr(app, 'card_gpu', None), COLORS['purple']),
    ):
        if card is None:
            continue
        fill = _native_card_fill(app, card, lift=0.60)
        touched |= _apply_native_card_surface(card, fill, hover=_native_card_hover(fill, accent=accent))
        card._cp_hover_accent = accent

    for widgets in (getattr(app, 'disk_widgets', {}) or {}).values():
        card = widgets.get('card') if isinstance(widgets, dict) else None
        if card is None:
            continue
        fill = _native_card_fill(app, card, lift=0.60)
        touched |= _apply_native_card_surface(card, fill, hover=_native_card_hover(fill, accent=COLORS['primary']))
        card._cp_hover_accent = COLORS['primary']

    # V439: sólo las franjas verticales aceptan hover. El resto de
    # CTkFrames, etiquetas, pills y barras jamás reciben otra capa.
    ai_strip = getattr(app, '_ai_accent', None)
    cards_and_strips = []
    for card in status_cards:
        cards_and_strips.append((card, getattr(card, '_cp_health_accent', None)
                                 or getattr(card, '_cp_status_accent', None)))
    for card in (getattr(app, 'card_cpu', None), getattr(app, 'card_ram', None),
                 getattr(app, 'card_gpu', None)):
        cards_and_strips.append((card, getattr(card, '_corepulse_resource_accent', None)))
    for widgets in (getattr(app, 'disk_widgets', {}) or {}).values():
        if isinstance(widgets, dict):
            card = widgets.get('card')
            cards_and_strips.append((card, getattr(card, '_corepulse_storage_accent', None)))
    for card, strip in cards_and_strips:
        if card is None or strip is None:
            continue
        card._cp_native_hover_strip = strip
        strip._cp_native_accent_strip = True
        if getattr(card, '_cp_hover_active', False):
            try:
                from gui.card_workspace_surface import apply_card_hover_accent
                apply_card_hover_accent(card, True)
            except Exception:
                pass

    workspace = getattr(app, 'workspace_background', None)
    if workspace is not None:
        try:
            for card in (list(status_cards) + [getattr(app, 'card_cpu', None),
                        getattr(app, 'card_ram', None), getattr(app, 'card_gpu', None)]
                         + [entry.get('card') for entry in (getattr(app, 'disk_widgets', {}) or {}).values()
                            if isinstance(entry, dict)]):
                if card is not None:
                    workspace.register_native_card(card)
        except Exception:
            pass
    return touched


def request_native_card_surface_sync(app):
    if app is None or not getattr(app, 'is_running', False):
        return False
    if getattr(app, '_native_card_surface_after_id', None) is not None:
        return True

    def _commit():
        app._native_card_surface_after_id = None
        try:
            _sync_native_card_surfaces(app)
        except Exception:
            pass

    try:
        app._native_card_surface_after_id = app.after_idle(_commit)
        return True
    except Exception:
        app._native_card_surface_after_id = None
        return _sync_native_card_surfaces(app)

# V128 — el estado activo replica la previsualización de Temas: accent_2
# exacto, hover accent y texto del rol text. Sin tonos intermedios derivados.
SIDEBAR_ACTIVE_BG = role_color('accent_2')
SIDEBAR_ACTIVE_HOVER = role_color('accent')
SIDEBAR_ACTIVE_BORDER = role_color('accent')
SIDEBAR_INACTIVE_TEXT = role_color('text_2')

# V229 — experimento visual: borde funcional por opción del sidebar.
SIDEBAR_OPTION_ACCENTS = {
    '_btn_summary': COLORS['primary'],
    'btn_benchmark': COLORS['purple'],
    'btn_diagnostic': COLORS['amber'],
    'btn_health_center': COLORS['green'],
    'btn_cleanup': COLORS['primary'],
    'btn_tweaks': COLORS['purple'],
    'btn_network': COLORS['primary'],
    'btn_smart_alerts': COLORS['red'],
    'btn_session_trends': COLORS['green'],
    'btn_alert_history': COLORS['amber'],
}

def _sidebar_option_accent(attr):
    return SIDEBAR_OPTION_ACCENTS.get(attr, COLORS['primary'])

SIDEBAR_ICON_FILES = {
    '_btn_summary': 'summary.png',
    'btn_benchmark': 'overlay.png',
    'btn_diagnostic': 'diagnostic.png',
    'btn_health_center': 'health.png',
    'btn_cleanup': 'cleanup.png',
    'btn_tweaks': 'tweaks.png',
    'btn_network': 'network.png',
    'btn_smart_alerts': 'alerts.png',
    'btn_session_trends': 'trends.png',
    'btn_alert_history': 'history.png',
    '_theme_toggle_button': 'theme.png',
    '_ai_button': 'ai.png',
}
SIDEBAR_LABELS = {
    '_btn_summary': 'Resumen',
    'btn_benchmark': 'Benchmark',
    'btn_diagnostic': 'Iniciar diagnóstico',
    'btn_health_center': 'Centro de salud',
    'btn_cleanup': 'Limpieza de sistema',
    'btn_tweaks': 'Tweaks Windows 11',
    'btn_network': 'Red avanzada',
    'btn_smart_alerts': 'Alertas técnicas',
    'btn_session_trends': 'Tendencias',
    'btn_alert_history': 'Historial de alertas',
    '_theme_toggle_button': 'Temas',
    '_ai_button': 'CorePulse AI',
}


def _safe_config(widget, **kwargs):
    try:
        configure_changed(widget, **kwargs)
    except Exception:
        pass


def _safe_pack_forget(widget):
    try:
        widget.pack_forget()
    except Exception:
        pass


def _bind_sidebar_glyph(widget, command):
    """Hace clickeable un glifo sin convertirlo en botón/cápsula."""
    if widget is None:
        return widget
    try:
        widget.configure(cursor='hand2')
    except Exception:
        pass
    try:
        widget.bind('<Button-1>', lambda _event: command() if callable(command) else None, add='+')
    except Exception:
        pass
    return widget


def _install_sidebar_hover_close(app):
    """V279: hover estable de la X sin remapear widgets del sidebar.

    La geometría del control se mantiene reservada permanentemente en la esquina
    superior derecha. Al entrar/salir sólo cambia el texto mostrado; no se usa
    ``place_forget`` ni se enlazan eventos recursivamente a cada hijo, evitando
    invalidaciones de dibujo y parpadeos al cruzar botones, iconos y separadores.
    """
    root = getattr(app, 'sidebar', None)
    action = getattr(app, '_sidebar_close_button', None)
    if root is None or action is None:
        return

    state = {'visible': False, 'after': None}

    def set_visible(value):
        value = bool(value)
        if state['visible'] == value:
            return
        state['visible'] = value
        _safe_config(action, text='✕' if value else '')
        if value:
            try:
                action.lift()
            except Exception:
                pass

    def pointer_inside_sidebar():
        try:
            px, py = root.winfo_pointerxy()
            x0 = root.winfo_rootx()
            y0 = root.winfo_rooty()
            width = max(1, root.winfo_width())
            height = max(1, root.winfo_height())
            return x0 <= px < (x0 + width) and y0 <= py < (y0 + height)
        except Exception:
            return False

    def cancel_pending():
        after_id = state.get('after')
        if after_id:
            try:
                root.after_cancel(after_id)
            except Exception:
                pass
        state['after'] = None

    def enter(_event=None):
        cancel_pending()
        set_visible(True)

    def finalize_leave():
        state['after'] = None
        if pointer_inside_sidebar():
            set_visible(True)
        else:
            set_visible(False)

    def leave(_event=None):
        cancel_pending()
        try:
            state['after'] = root.after(90, finalize_leave)
        except Exception:
            finalize_leave()

    # Un solo par de bindings en el contenedor. Los eventos NotifyInferior que
    # aparecen al pasar de un hijo a otro quedan absorbidos por el debounce y la
    # comprobación geométrica del puntero, sin tocar el árbol completo.
    try:
        # Reemplazamos sólo estos bindings del contenedor; así una reconstrucción
        # del sidebar no acumula callbacks duplicados.
        root.bind('<Enter>', enter)
        root.bind('<Leave>', leave)
    except Exception:
        pass

    # La X siempre está mapeada: sólo su contenido se oculta/expone.
    try:
        action.place(relx=1.0, x=-2, y=1, anchor='ne')
        action.lift()
    except Exception:
        pass
    _safe_config(action, text='')
    state['visible'] = False
    app._sidebar_hover_close_state = state


def _sync_sidebar_visibility_controls(app):
    """La barra compacta contiene su propio botón para expandir el menú."""
    glyph = getattr(app, '_sidebar_reopen_button', None)
    if glyph is not None:
        glyph.place_forget()
    from gui.internal_navigation import sync_compact_sidebar
    sync_compact_sidebar(app)
    return glyph


def _install_sidebar_hover_expand(app):
    """Hover integrado al lienzo maestro, sin animar geometría."""
    from gui.sidebar_native_hover import install_native_sidebar_hover
    install_native_sidebar_hover(app, SIDEBAR_LABELS)
    app._sidebar_hover_expand_state = {}


def _status_color(score):
    try:
        score = float(score)
    except Exception:
        return COLORS['muted']
    if score < 50:
        return COLORS['red']
    if score < 70:
        return COLORS['amber']
    if score < 85:
        return COLORS['primary']
    return COLORS['green']


def _status_name(score):
    try:
        score = float(score)
    except Exception:
        return 'EVALUANDO'
    if score < 50:
        return 'CRÍTICO'
    if score < 70:
        return 'ADVERTENCIA'
    if score < 85:
        return 'ESTABLE'
    return 'ÓPTIMO'


def _uptime_elapsed_seconds():
    try:
        return max(0, int(time.time() - psutil.boot_time()))
    except Exception:
        return None


def _uptime_text():
    try:
        elapsed = _uptime_elapsed_seconds()
        if elapsed is None:
            return 'N/A'
        h, rem = divmod(int(elapsed), 3600)
        m, s = divmod(rem, 60)
        if h >= 100:
            d, h = divmod(h, 24)
            return f'{d}d {h:02d}:{m:02d}'
        return f'{h:02d}:{m:02d}:{s:02d}'
    except Exception:
        return 'N/A'


def _uptime_hours_value():
    seconds = _uptime_elapsed_seconds()
    if seconds is None:
        return None
    try:
        return float(seconds) / 3600.0
    except Exception:
        return None


def _telemetry_coverage(telemetry):
    """Cuenta únicamente el metadata de certificación ya producido por CorePulse."""
    if not isinstance(telemetry, dict):
        return (None, None)
    metrics = telemetry.get('_metrics')
    if not isinstance(metrics, dict) or not metrics:
        return (None, None)
    total = 0
    valid = 0
    for meta in metrics.values():
        if not isinstance(meta, dict):
            continue
        total += 1
        if str(meta.get('quality') or '').upper() == 'VALID':
            valid += 1
    return (valid, total)


def _bind_click_tree(widget, callback):
    """Hace clickeable una tarjeta completa sin duplicar acciones de botones hijos."""
    if widget is None or not callable(callback):
        return
    # Los CTkButton conservan su propio command. Evita dobles aperturas cuando
    # una tarjeta navegable contiene un botón de acción explícito.
    if isinstance(widget, ctk.CTkButton):
        return
    try:
        widget.configure(cursor='hand2')
    except Exception:
        pass
    try:
        widget.bind('<Button-1>', lambda _event: callback(), add='+')
    except Exception:
        pass
    try:
        for child in widget.winfo_children():
            _bind_click_tree(child, callback)
    except Exception:
        pass


def _bind_card_hover(root, *, normal=None, hover=None, action_button=None, action_place=None):
    """Feedback de hover estable para tarjetas del Dashboard.

    V392 elimina la micro-expansión geométrica que reducía temporalmente el
    margen horizontal al posar el puntero. El hover conserva únicamente el
    cambio visual de superficie y las acciones contextuales (por ejemplo,
    ``Ver detalles``), sin modificar tamaño, margen ni posición de la tarjeta.
    """
    if root is None:
        return
    if not hasattr(root, '_cp_hover_active'):
        root._cp_hover_active = False
    normal = normal or getattr(root, '_cp_surface_normal', COLORS['surface'])
    hover = hover or getattr(root, '_cp_surface_hover', COLORS['surface_hover'])
    pending = {'after': None}
    action_place = dict(action_place or {})

    def show_action():
        if action_button is None:
            return
        try:
            if not action_button.winfo_manager():
                action_button.place(**action_place)
            action_button.lift()
        except Exception:
            pass

    def hide_action():
        if action_button is None:
            return
        try:
            action_button.place_forget()
        except Exception:
            pass

    def inside_root():
        try:
            x, y = root.winfo_pointerxy()
            node = root.winfo_containing(x, y)
            while node is not None:
                if node is root:
                    return True
                node = getattr(node, 'master', None)
        except Exception:
            pass
        return False

    def _set_native_hover(active):
        if not getattr(root, '_cp_seamless_surface', False):
            return
        active = bool(active)
        if bool(getattr(root, '_cp_hover_active', False)) == active:
            return
        root._cp_hover_active = active
        try:
            from gui.card_workspace_surface import repaint_card_hover
            app = root.winfo_toplevel()
            repaint_card_hover(root, getattr(app, 'workspace_background', None))
        except (AttributeError, ValueError, RuntimeError):
            pass

    def enter(_event=None):
        after_id = pending.get('after')
        if after_id:
            try:
                root.after_cancel(after_id)
            except Exception:
                pass
            pending['after'] = None
        active_hover = getattr(root, '_cp_surface_hover', hover)
        if not getattr(root, '_cp_seamless_surface', False):
            _safe_config(root, fg_color=active_hover)
        else:
            _set_native_hover(True)
        show_action()

    def finalize_leave():
        pending['after'] = None
        if not inside_root():
            active_normal = getattr(root, '_cp_surface_normal', normal)
            if not getattr(root, '_cp_seamless_surface', False):
                _safe_config(root, fg_color=active_normal)
            else:
                _set_native_hover(False)
            hide_action()

    def leave(_event=None):
        try:
            pending['after'] = root.after(12, finalize_leave)
        except Exception:
            finalize_leave()

    def bind_node(node):
        try:
            node.configure(cursor='hand2')
        except Exception:
            pass
        try:
            node.bind('<Enter>', enter, add='+')
            node.bind('<Leave>', leave, add='+')
        except Exception:
            pass
        try:
            for child in node.winfo_children():
                bind_node(child)
        except Exception:
            pass

    bind_node(root)
    hide_action()

def _bind_hover_tooltip(root, text_provider, *, delay_ms=280):
    """Tooltip visual liviano para explicar una tarjeta sin abrir ventanas modales."""
    if root is None or not callable(text_provider):
        return
    state = {'after': None, 'tip': None}

    def cancel_pending():
        after_id = state.get('after')
        if after_id:
            try:
                root.after_cancel(after_id)
            except Exception:
                pass
        state['after'] = None

    def destroy_tip():
        tip = state.get('tip')
        if tip is not None:
            try:
                tip.destroy()
            except Exception:
                pass
        state['tip'] = None

    def position_tip(event=None):
        tip = state.get('tip')
        if tip is None:
            return
        try:
            x = (event.x_root + 18) if event is not None else (root.winfo_pointerx() + 18)
            y = (event.y_root + 18) if event is not None else (root.winfo_pointery() + 18)
            tip.geometry(f'+{int(x)}+{int(y)}')
        except Exception:
            pass

    def _normalize_payload():
        payload = text_provider()
        if isinstance(payload, dict):
            title = str(payload.get('title') or '').strip()
            body = [str(item).strip() for item in (payload.get('body') or []) if str(item).strip()]
            accent = str(payload.get('accent') or COLORS['primary'])
            return title, body, accent
        message = str(payload or '').strip()
        if not message:
            return '', [], COLORS['primary']
        lines = [line.strip() for line in message.splitlines() if line.strip()]
        title = lines[0] if lines else ''
        body = lines[1:] if len(lines) > 1 else []
        return title, body, COLORS['primary']

    def show_tip(event=None):
        cancel_pending()
        destroy_tip()
        title, body_lines, accent = _normalize_payload()
        if not title and not body_lines:
            return
        try:
            tip = tk.Toplevel(root)
            tip.withdraw()
            tip.overrideredirect(True)
            try:
                tip.attributes('-topmost', True)
            except Exception:
                pass
            try:
                tip.configure(bg=COLORS['surface'])
            except Exception:
                pass

            shell = ctk.CTkFrame(
                tip,
                fg_color=COLORS['surface'],
                border_width=1,
                border_color=accent,
                corner_radius=12,
            )
            shell.pack(fill='both', expand=True)

            accent_bar = ctk.CTkFrame(shell, fg_color=accent, width=4, corner_radius=10)
            accent_bar.pack(side='left', fill='y', padx=(1, 0), pady=1)

            content = ctk.CTkFrame(shell, fg_color='transparent')
            content.pack(side='left', fill='both', expand=True, padx=(12, 12), pady=(10, 10))

            if title:
                ctk.CTkLabel(
                    content,
                    text=title,
                    font=(FONT, 11, 'bold'),
                    text_color=COLORS['text'],
                    justify='left',
                    anchor='w',
                ).pack(anchor='w')
            for idx, line in enumerate(body_lines):
                is_heading = str(line).strip().upper() in {'FACTORES DETECTADOS', 'ESTADO ACTUAL'}
                ctk.CTkLabel(
                    content,
                    text=line,
                    font=(FONT, 8, 'bold') if is_heading else (FONT, 8),
                    text_color=accent if is_heading else COLORS['text'],
                    justify='left',
                    anchor='w',
                    wraplength=320,
                ).pack(anchor='w', pady=(8 if is_heading else 4 if idx == 0 and title else 2, 0))

            state['tip'] = tip
            position_tip(event)
            tip.deiconify()
        except Exception:
            destroy_tip()

    def schedule_show(event=None):
        cancel_pending()
        try:
            state['after'] = root.after(delay_ms, lambda ev=event: show_tip(ev))
        except Exception:
            show_tip(event)

    def hide_tip(_event=None):
        cancel_pending()
        destroy_tip()

    def bind_node(node):
        try:
            node.bind('<Enter>', schedule_show, add='+')
            node.bind('<Leave>', hide_tip, add='+')
            node.bind('<Motion>', position_tip, add='+')
        except Exception:
            pass
        try:
            for child in node.winfo_children():
                bind_node(child)
        except Exception:
            pass

    bind_node(root)


def _health_hover_text(app):
    result = getattr(app, 'current_live_health', None)
    if not isinstance(result, dict):
        return {
            'title': 'Salud del sistema · evaluando',
            'body': [
                'CorePulse aún está recopilando evidencia real para calcular el porcentaje de salud.',
            ],
            'accent': COLORS['green'],
        }

    score = result.get('score')
    status = str(result.get('status') or 'NO EVALUABLE').strip()
    reasons = [str(item).strip() for item in (result.get('reasons') or []) if str(item).strip()]
    title = f'Salud del sistema · {float(score):.1f}% · {status}' if isinstance(score, (int, float)) else f'Salud del sistema · N/A · {status}'

    if reasons and not (len(reasons) == 1 and reasons[0].startswith('No se detectan señales')):
        body = ['FACTORES DETECTADOS'] + [f'• {item}' for item in reasons[:5]]
    else:
        body = [
            'ESTADO ACTUAL',
            'Sin revisión necesaria por ahora.',
            'RAM, almacenamiento y temperaturas se encuentran dentro de los rangos evaluados.',
        ]

    body.append('100% significa que no hay señales relevantes para revisar en las métricas evaluadas.')
    return {
        'title': title,
        'body': body,
        'accent': COLORS['green'] if str(result.get('severity') or '').upper() not in {'WARNING', 'CRITICAL', 'ERROR'} else COLORS['amber'] if str(result.get('severity') or '').upper() in {'ELEVATED', 'WARNING'} else COLORS['red'],
    }


def _relative_update_text(telemetry):
    if not isinstance(telemetry, dict):
        return 'esperando'
    stamp = telemetry.get('_snapshot_timestamp') or telemetry.get('timestamp')
    try:
        age = max(0.0, time.time() - float(stamp))
    except Exception:
        return 'ahora'
    if age < 1.0:
        return '< 1 s'
    if age < 60.0:
        return f'{int(age)} s'
    return f'{age / 60.0:.1f} min'


def _section_label(parent, text):
    return ctk.CTkLabel(
        parent,
        text=text,
        height=17,
        font=(FONT, 8, 'bold'),
        text_color=COLORS['text'],
        anchor='w',
    )


def _sidebar_divider(parent):
    # V272: los divisores dejan de competir con el acento principal. Usan el
    # mismo borde estructural que tarjetas y gráficos para una separación más
    # sobria, coherente y compatible con todos los temas.
    return tk.Frame(
        parent,
        bg=COLORS['border'],
        height=1,
        bd=0,
        highlightthickness=0,
    )


def _ensure_sidebar_native_border(app):
    """V421: elimina el cuadro perimetral del sidebar.

    Se mantiene este helper por compatibilidad con llamadas existentes, pero ya
    no se dibujan líneas superior/inferior/laterales alrededor del menú.
    """
    old = getattr(app, '_sidebar_native_border', None)
    if old is not None:
        for widget in old if isinstance(old, (tuple, list)) else (old,):
            try:
                widget.destroy()
            except Exception:
                pass
    app._sidebar_native_border = None

    if not getattr(app, '_sidebar_window_resize_bound', False):
        def _window_resize(_event=None):
            try:
                app.after_idle(lambda: _sync_sidebar_native_border_to_content(app))
            except Exception:
                pass
        try:
            app.bind('<Configure>', _window_resize, add='+')
            app._sidebar_window_resize_bound = True
        except Exception:
            pass

    _sync_sidebar_native_border_to_content(app)
    return None


def _sync_sidebar_native_border_to_content(app):
    """Mantiene altura/alineación del sidebar sin borde perimetral."""
    if getattr(app, '_sidebar_collapsed', False):
        return
    try:
        if not app.sidebar.winfo_exists():
            return

        content_bottom = 0
        for child in app.sidebar.winfo_children():
            try:
                if not child.winfo_manager():
                    continue
                child_bottom = int(child.winfo_y()) + max(
                    int(child.winfo_height()), int(child.winfo_reqheight())
                )
                content_bottom = max(content_bottom, child_bottom)
            except Exception:
                continue

        try:
            client_bottom = int(app.winfo_rooty()) + int(app.winfo_height())
            viewport_limit = max(300, client_bottom - int(app.sidebar.winfo_rooty()) - 14)
        except Exception:
            viewport_limit = 760

        desired_h = max(300, content_bottom + 2)
        charts = getattr(app, 'frame_charts', None)
        if charts is not None and not getattr(app, '_active_internal_page', None):
            try:
                if charts.winfo_ismapped() and charts.winfo_height() > 60:
                    charts_bottom = charts.winfo_rooty() + charts.winfo_height()
                    sidebar_top = app.sidebar.winfo_rooty()
                    aligned_h = int(charts_bottom - sidebar_top)
                    if aligned_h > 0:
                        desired_h = max(300, aligned_h - 1)
            except (AttributeError, ValueError, TypeError):
                pass

        desired_h = min(viewport_limit, desired_h)
        previous_h = int(getattr(app, '_sidebar_visible_height', 0) or 0)
        app._sidebar_visible_height = desired_h

        manager = str(app.sidebar.winfo_manager() or '')
        if manager == 'grid':
            if previous_h != desired_h:
                app.sidebar.configure(height=desired_h)
            sidebar_top_pad = 32 if getattr(app, 'is_fullscreen', False) else 14
            app.sidebar.grid_configure(sticky='new', padx=(12, 0), pady=(sidebar_top_pad, 0))
    except Exception:
        pass

def _section_header(parent, title, subtitle):
    """Cabecera compacta de sección para dar más jerarquía al Resumen."""
    box = ctk.CTkFrame(parent, fg_color='transparent', height=30)
    box.pack_propagate(False)
    left = ctk.CTkFrame(box, fg_color='transparent')
    left.pack(side='left', fill='both', expand=True)
    ctk.CTkLabel(
        left,
        text=title,
        height=16,
        font=(FONT, 11, 'bold'),
        text_color=COLORS['text_2'],
        anchor='w',
    ).pack(anchor='w')
    ctk.CTkLabel(
        left,
        text=subtitle,
        height=14,
        font=(FONT, 8),
        text_color=COLORS['muted'],
        anchor='w',
    ).pack(anchor='w', pady=(0, 1))
    return box


def _ensure_soft_card_accent(card, accent, *, placement='left', length=0.32):
    """Aplica un acento visual suave a las tarjetas del dashboard."""
    if card is None:
        return None
    bar = getattr(card, '_soft_accent_bar', None)
    if bar is None or not bool(getattr(bar, 'winfo_exists', lambda: False)()):
        bar = ctk.CTkFrame(card, fg_color=accent, corner_radius=16)
        card._soft_accent_bar = bar
    try:
        if placement == 'top':
            bar.place(relx=0.0, rely=0.0, x=12, y=8, relwidth=max(0.18, min(0.55, length)), height=3, anchor='nw')
        else:
            bar.place(relx=0.0, rely=0.0, x=1, y=10, relheight=0.72, width=3, anchor='nw')
        bar.lift()
    except Exception:
        pass
    return bar


def _set_nav_selection_indicator(btn, active=False):
    """Acento lateral fino para que la selección del sidebar se vea más premium."""
    if btn is None:
        return None
    bar = getattr(btn, '_nav_selection_indicator', None)
    if active:
        if bar is None or not bool(getattr(bar, 'winfo_exists', lambda: False)()):
            bar = ctk.CTkFrame(btn, fg_color=COLORS['primary'], corner_radius=16)
            btn._nav_selection_indicator = bar
        try:
            bar.place(x=7, rely=0.5, anchor='w', width=3, relheight=0.52)
            bar.lift()
        except Exception:
            pass
    elif bar is not None:
        try:
            bar.place_forget()
        except Exception:
            pass
    return bar


def _set_sidebar_option_line(btn, color, *, active=False):
    """V254: sólo la opción activa usa una línea vertical fina."""
    if btn is None:
        return None
    line = getattr(btn, '_sidebar_option_line', None)
    if not active:
        if line is not None:
            try:
                line.place_forget()
            except Exception:
                pass
        return line
    try:
        exists = bool(line is not None and line.winfo_exists())
    except Exception:
        exists = False
    if not exists:
        line = ctk.CTkFrame(btn, fg_color=color, corner_radius=6)
        btn._sidebar_option_line = line
    _safe_config(line, fg_color=color)
    try:
        line.place(x=5, rely=0.5, anchor='w', width=3, relheight=0.54)
        line.lift()
    except Exception:
        pass
    return line


def _resource_soft_bg(accent):
    if accent == COLORS['green']:
        return role_color('ok_bg')
    if accent == COLORS['purple']:
        return theme_color('#1c2752')
    return role_color('accent_soft')


def _resource_title_text(kind, previous_text):
    kind = str(kind or '').strip()
    previous = str(previous_text or '').strip()
    if '\n' in previous:
        return previous
    if not previous or previous.upper() == kind.upper():
        return kind
    return f'{kind}\n{previous}'


def _ensure_resource_card_decor(app, card, accent, eyebrow_text):
    """V237: tarjeta de recurso según la referencia aprobada por el usuario.

    Mantiene el borde/acento lateral actual y elimina iconos, pills y adornos.
    La jerarquía queda: componente/modelo -> porcentaje -> barra -> detalle.
    """
    if card is None:
        return
    if getattr(card, '_corepulse_reference_layout', False):
        return

    if card is app.card_cpu:
        old_title, old_value, old_bar, old_detail = app.lbl_cpu_title, app.lbl_cpu, app.bar_cpu, app.lbl_cpu_temp
    elif card is app.card_ram:
        old_title, old_value, old_bar, old_detail = app.lbl_ram_title, app.lbl_ram, app.bar_ram, app.lbl_ram_gb
    else:
        old_title, old_value, old_bar, old_detail = app.lbl_gpu_title, app.lbl_gpu, app.bar_gpu, app.lbl_gpu_temp

    try:
        title_text = _resource_title_text(eyebrow_text, old_title.cget('text'))
    except Exception:
        title_text = eyebrow_text
    try:
        value_text = str(old_value.cget('text') or 'N/A')
    except Exception:
        value_text = 'N/A'
    try:
        detail_text = str(old_detail.cget('text') or 'N/A')
    except Exception:
        detail_text = 'N/A'
    try:
        old_progress = float(old_bar.get())
    except Exception:
        old_progress = 0.0

    for child in list(card.winfo_children()):
        try:
            child.destroy()
        except Exception:
            pass

    _safe_config(
        card,
        fg_color=COLORS['surface'],
        border_color=COLORS['surface'],
        border_width=0,
        corner_radius=16,
    )
    try:
        card.pack_propagate(False)
    except Exception:
        pass

    shell = ctk.CTkFrame(card, fg_color='transparent')
    shell.pack(fill='both', expand=True)

    # IMPORTANTE: se conserva exactamente el acento/borde lateral de color.
    accent_bar = ctk.CTkFrame(shell, fg_color=accent, width=4, corner_radius=14)
    accent_bar.pack(side='left', fill='y', padx=(1, 0), pady=1)
    card._corepulse_resource_accent = accent_bar
    accent_bar._cp_native_accent_strip = True

    content = ctk.CTkFrame(shell, fg_color='transparent')
    content.pack(side='left', fill='both', expand=True, padx=(12, 12), pady=(9, 8))

    title = ctk.CTkLabel(
        content, text=title_text, font=(FONT, 9, 'bold'),
        text_color=COLORS['text_2'], anchor='w', justify='left', height=30,
    )
    title.pack(fill='x', anchor='w', pady=(0, 1))

    value = ctk.CTkLabel(
        content, text=value_text, font=(FONT, 29, 'bold'),
        text_color=COLORS['text'], anchor='w', height=34,
    )
    value.pack(fill='x', anchor='w', pady=(0, 1))

    bar = ctk.CTkProgressBar(
        content, height=6, corner_radius=3,
        progress_color=accent, fg_color=COLORS['track'],
    )
    bar.set(max(0.0, min(1.0, old_progress)))
    bar.pack(fill='x', pady=(0, 5))

    detail = ctk.CTkLabel(
        content, text=detail_text, font=(FONT, 9, 'bold'),
        text_color=accent, anchor='w', justify='left', height=18,
    )
    detail.pack(fill='x', anchor='w', pady=(0, 0))

    if card is app.card_cpu:
        app.lbl_cpu_title, app.lbl_cpu, app.bar_cpu, app.lbl_cpu_temp = title, value, bar, detail
    elif card is app.card_ram:
        app.lbl_ram_title, app.lbl_ram, app.bar_ram, app.lbl_ram_gb = title, value, bar, detail
    else:
        app.lbl_gpu_title, app.lbl_gpu, app.bar_gpu, app.lbl_gpu_temp = title, value, bar, detail

    card._corepulse_reference_layout = True
    card._corepulse_status_parity = True


def _apply_resource_card_geometry(app):
    # La geometría ya está definida por la estructura tipo status-card.
    return


def _ensure_storage_card_decor(card, widgets=None, accent=None):
    """Tarjeta compacta por unidad con salud inline y ojo de detalles a la derecha."""
    if card is None:
        return
    if getattr(card, '_corepulse_storage_v238', False):
        return

    widgets = widgets if isinstance(widgets, dict) else {}
    old_name = widgets.get('lbl_name')
    old_badge = widgets.get('lbl_badge')
    old_exact = widgets.get('lbl_exact')
    old_bar = widgets.get('bar')
    old_details = widgets.get('btn_details')

    try:
        name_text = str(old_name.cget('text') or 'Unidad de almacenamiento')
    except Exception:
        name_text = 'Unidad de almacenamiento'
    try:
        badge_text = str(old_badge.cget('text') or 'Salud N/A')
    except Exception:
        badge_text = 'Salud N/A'
    try:
        exact_text = str(old_exact.cget('text') or 'Información de capacidad: N/A')
    except Exception:
        exact_text = 'Información de capacidad: N/A'
    try:
        old_progress = float(old_bar.get())
    except Exception:
        old_progress = 0.0
    try:
        details_command = getattr(old_details, '_command', None)
    except Exception:
        details_command = None

    for child in list(card.winfo_children()):
        try:
            child.destroy()
        except Exception:
            pass

    _safe_config(card, fg_color=COLORS['surface'], border_color=COLORS['surface'], border_width=0, corner_radius=16, height=86)
    try:
        card.pack_propagate(False)
    except Exception:
        pass

    shell = ctk.CTkFrame(card, fg_color='transparent')
    shell.pack(fill='both', expand=True)
    accent_color = accent or COLORS['primary']
    accent_strip = ctk.CTkFrame(shell, fg_color=accent_color, width=4, corner_radius=14)
    accent_strip.pack(side='left', fill='y', padx=(1, 0), pady=1)
    card._corepulse_storage_accent = accent_strip
    accent_strip._cp_native_accent_strip = True

    content = ctk.CTkFrame(shell, fg_color='transparent')
    content.pack(side='left', fill='both', expand=True, padx=(12, 12), pady=(7, 7))

    top = ctk.CTkFrame(content, fg_color='transparent', height=25)
    top.pack(fill='x')
    top.pack_propagate(False)

    name = ctk.CTkLabel(top, text=name_text, font=(FONT, 10, 'bold'), text_color=COLORS['text'], anchor='w', justify='left')
    name.pack(side='left', fill='x', expand=True)

    details = ctk.CTkButton(
        top, text='👁', width=30, height=24, corner_radius=7,
        fg_color=role_color('accent_2'), hover_color=role_color('accent'),
        border_width=1, border_color=role_color('accent'), text_color=role_color('text'),
        font=(ICON_FONT, 12, 'bold'), command=details_command if callable(details_command) else None,
    )
    details.pack(side='right', padx=(8, 0))

    metrics = ctk.CTkFrame(content, fg_color='transparent', height=20)
    metrics.pack(fill='x', pady=(3, 2))
    metrics.pack_propagate(False)

    exact = ctk.CTkLabel(metrics, text=exact_text, font=(FONT, 9), text_color=accent_color, anchor='w', justify='left')
    exact.pack(side='left', anchor='w')

    badge = ctk.CTkLabel(metrics, text=badge_text, font=(FONT, 8, 'bold'), text_color=COLORS['green'], fg_color=role_color('ok_bg'), corner_radius=10, padx=9, pady=2, anchor='w')
    badge.pack(side='left', padx=(10, 0))

    bar = ctk.CTkProgressBar(content, height=6, corner_radius=3, progress_color=accent_color, fg_color=COLORS['track'])
    bar.set(max(0.0, min(1.0, old_progress)))
    bar.pack(fill='x', pady=(0, 0))

    widgets.update({
        'lbl_name': name,
        'lbl_badge': badge,
        'lbl_exact': exact,
        'bar': bar,
        'btn_details': details,
        'details_slot': top,
        'metrics_row': metrics,
    })
    card._corepulse_reference_layout = True
    card._corepulse_status_parity = True
    card._corepulse_storage_v238 = True

def _ensure_chart_accents(app):
    frame = getattr(app, 'frame_charts', None)
    if frame is None:
        return
    bars = list(getattr(app, '_chart_top_accents', []) or [])
    if len(bars) != 3:
        for item in bars:
            try:
                item.destroy()
            except Exception:
                pass
        bars = []
        for color in (COLORS['primary'], COLORS['green'], COLORS['purple']):
            bars.append(ctk.CTkFrame(frame, fg_color=color, height=3, corner_radius=8))
        app._chart_top_accents = bars
    for idx, bar in enumerate(bars):
        try:
            bar.place(relx=0.012 + idx * 0.333, y=8, relwidth=0.309, height=3, anchor='nw')
            bar.lift()
        except Exception:
            pass


def _build_sidebar_toggle(app):
    """Botón flotante pegado al divisor entre sidebar y contenido."""
    button = getattr(app, '_sidebar_toggle_button', None)
    try:
        exists = bool(button is not None and button.winfo_exists())
    except Exception:
        exists = False
    if not exists:
        button = ctk.CTkButton(
            app,
            text='›' if getattr(app, '_sidebar_collapsed', False) else '‹',
            width=18,
            height=34,
            corner_radius=9,
            fg_color=COLORS['surface_2'],
            hover_color=COLORS['surface_hover'],
            border_width=1,
            border_color=COLORS['border'],
            text_color=COLORS['text'],
            font=(FONT, 15, 'bold'),
            command=getattr(app, 'toggle_sidebar_collapse', None),
        )
        app._sidebar_toggle_button = button
    else:
        _safe_config(
            button,
            text='›' if getattr(app, '_sidebar_collapsed', False) else '‹',
            command=getattr(app, 'toggle_sidebar_collapse', None),
        )
    try:
        app._position_sidebar_toggle()
    except Exception:
        pass
    return button


def _style_nav_button(btn, *, active=False, disabled=False, accent=None):
    """V254: navegación uniforme, compacta y con selección sobria."""
    accent = accent or COLORS['primary']
    if disabled:
        _safe_config(
            btn,
            fg_color='transparent',
            hover_color=role_color('sidebar'),
            text_color=theme_color('#5f7189'),
            border_width=0,
            corner_radius=8,
            height=36,
            font=(FONT, 10, 'bold'),
            anchor='w',
            padx=15,
        )
        _set_nav_selection_indicator(btn, False)
        _set_sidebar_option_line(btn, accent, active=False)
        return
    _safe_config(
        btn,
        fg_color=COLORS['surface_2'] if active else 'transparent',
        hover_color=COLORS['surface_2'],
        text_color=COLORS['text'] if active else SIDEBAR_INACTIVE_TEXT,
        border_width=0,
        corner_radius=8,
        height=36,
        font=(FONT, 10, 'bold'),
        anchor='w',
        padx=17 if active else 15,
    )
    _set_nav_selection_indicator(btn, False)
    _set_sidebar_option_line(btn, COLORS['primary'], active=active)

def _load_white_brand_asset(app):
    """Carga el símbolo de CorePulse para la cabecera principal.

    Desde V0.9.24.10w la marca deja de consumir altura en el sidebar. La imagen
    se mantiene como una única referencia CTkImage y se monta en el header.
    """
    try:
        path = brand_symbol_path(resource_root(), dashboard=True)
        if not path.exists():
            return
        pil_img = Image.open(path)
        app._dashboard_brand_image = ctk.CTkImage(
            light_image=pil_img,
            dark_image=pil_img,
            size=(46, 46),
        )
        # Compatibilidad con la referencia creada por main.py, pero el widget
        # queda deliberadamente fuera del layout lateral.
        icon = getattr(app, 'lbl_logo_icon', None)
        if icon is not None:
            _safe_pack_forget(icon)
            _safe_config(icon, image=app._dashboard_brand_image, text='')
    except Exception:
        pass


def _load_sidebar_icons(app):
    """Carga iconos PNG reales para evitar glifos Unicode deformados en Windows."""
    images = {}
    base = sidebar_assets_path(resource_root())
    for attr, filename in SIDEBAR_ICON_FILES.items():
        try:
            path = base / filename
            if not path.exists():
                continue
            pil = Image.open(path).convert('RGBA')
            images[attr] = ctk.CTkImage(light_image=pil, dark_image=pil, size=(25, 25) if attr in ('_theme_toggle_button', '_ai_button') else (20, 20))
        except Exception:
            continue
    app._dashboard_sidebar_icons = images
    return images


def _apply_sidebar_icon(app, attr, *, active=False, collapsed=False):
    button = getattr(app, attr, None)
    if button is None:
        return
    image = getattr(app, '_dashboard_sidebar_icons', {}).get(attr)
    label = SIDEBAR_LABELS.get(attr, '')
    kwargs = dict(text='' if collapsed else label, compound='left', anchor='center' if collapsed else 'w')
    if image is not None:
        kwargs['image'] = image
    _safe_config(button, **kwargs)
    _style_nav_button(button, active=active, accent=_sidebar_option_accent(attr))
    if collapsed:
        _safe_config(button, padx=0)



def _format_device_model(identity):
    """Forma un nombre visible usando solo identidad real reportada por Windows."""
    if not isinstance(identity, dict):
        return 'N/A'

    manufacturer = str(identity.get('manufacturer') or '').strip()
    model = str(identity.get('display_model') or identity.get('model') or '').strip()
    form_factor = str(identity.get('form_factor') or '').upper().strip()

    if form_factor == 'DESKTOP' and model.lower().startswith('pc de escritorio'):
        return model

    if manufacturer and model:
        if manufacturer.casefold() in model.casefold():
            return model
        return f'{manufacturer} {model}'
    if model:
        return model
    if manufacturer:
        return manufacturer

    # Para PC de escritorio, la placa madre es una identidad real útil cuando
    # Windows no expone un modelo de sistema válido.
    if form_factor == 'DESKTOP':
        board = identity.get('motherboard') if isinstance(identity.get('motherboard'), dict) else {}
        board_manufacturer = str(board.get('manufacturer') or '').strip()
        board_model = str(board.get('model') or '').strip()
        board_name = ' '.join(x for x in (board_manufacturer, board_model) if x).strip()
        if board_name:
            return f'PC · {board_name}'

    return 'N/A'


def _poll_device_identity(app):
    """Actualiza la etiqueta desde el hilo principal cuando finaliza la consulta."""
    try:
        pending = getattr(app, '_dashboard_device_identity_pending', None)
        if isinstance(pending, dict):
            app._device_identity_cache = pending
            app._dashboard_device_identity_pending = None
            try:
                if hasattr(app, '_prime_battery_presence_cache'):
                    app._prime_battery_presence_cache(pending)
            except Exception:
                pass
            _safe_config(
                getattr(app, '_header_device_model', None),
                text=_format_device_model(pending),
                text_color=COLORS['text'],
            )
            return
        if getattr(app, '_dashboard_device_identity_done', False):
            _safe_config(
                getattr(app, '_header_device_model', None),
                text='N/A',
                text_color=COLORS['muted'],
            )
            return
        app.after(120, lambda: _poll_device_identity(app))
    except Exception:
        pass


def _start_device_identity_load(app):
    """Obtiene el modelo real sin bloquear la interfaz de CorePulse."""
    cached = getattr(app, '_device_identity_cache', None)
    if isinstance(cached, dict):
        _safe_config(
            getattr(app, '_header_device_model', None),
            text=_format_device_model(cached),
            text_color=COLORS['text'],
        )
        return

    if getattr(app, '_dashboard_device_identity_loading', False):
        return

    app._dashboard_device_identity_loading = True
    app._dashboard_device_identity_done = False
    app._dashboard_device_identity_pending = None

    def worker():
        try:
            identity = collect_device_identity()
            if isinstance(identity, dict):
                app._dashboard_device_identity_pending = identity
        except Exception:
            app._dashboard_device_identity_pending = None
        finally:
            app._dashboard_device_identity_done = True

    threading.Thread(
        target=worker,
        name='CorePulseDeviceIdentityUI',
        daemon=True,
    ).start()
    app.after(120, lambda: _poll_device_identity(app))

def _build_header(app):
    """Cabecera integrada al fondo: identidad del equipo y estado AI en línea."""
    header = ctk.CTkFrame(
        app.main_content,
        fg_color='transparent',
        border_width=0,
        corner_radius=0,
        height=96,
    )
    header.pack_propagate(False)

    hero = ctk.CTkFrame(
        header,
        fg_color='transparent',
        border_width=0,
        corner_radius=0,
        height=94,
    )
    hero.pack(fill='both', expand=True)
    hero.pack_propagate(False)
    app._header_hero = hero

    # Bloque izquierdo: no es tarjeta. Se integra al wallpaper maestro y sólo
    # expone la identidad del equipo.
    left = ctk.CTkFrame(hero, fg_color='transparent', corner_radius=0)
    left.pack(side='left', fill='both', expand=True, padx=(10, 12), pady=(4, 4))

    # V410: Lienzo de identidad sobre la MISMA superficie nativa: CTkLabel dibujaba
    # dos recuadros negros detrás del logo y del texto (no son del PNG).
    # Este lienzo conserva el texto dinámico y escala con el diseño responsive.
    identity = HeaderIdentityCanvas(left, foreground=COLORS['text'])
    identity.pack(fill='both', expand=True)
    app._header_identity = identity
    app._header_identity_canvas = identity
    app._header_brand_icon = None  # El icono se dibuja en el lienzo, sin CTkLabel.
    app._header_device_box = None
    app._header_eyebrow = None
    app._header_device_model = identity.text_control

    app._header_subtitle = None
    app._header_chip_row = None
    app._header_chip_live = None
    app._header_chip_data = None
    app._header_chip_focus = None

    # El estado de CorePulse AI queda integrado al fondo, sin tarjeta.
    right = ctk.CTkFrame(hero, fg_color='transparent', corner_radius=0, width=320)
    right.pack(side='right', fill='y', padx=(10, 4), pady=(2, 2))
    right.pack_propagate(False)
    app._header_right_stack = right

    ai_card = ctk.CTkFrame(
        right, fg_color='transparent', bg_color='transparent',
        border_width=0, border_color=COLORS['surface'], corner_radius=0, height=90,
    )
    ai_card.pack(fill='both', expand=True)
    ai_card.pack_propagate(False)
    app._header_ai_frame = ai_card

    # V447: el texto y la franja se pintan EN EL MISMO LIENZO del fondo
    # nativo. No se inserta otro CTkFrame/CTkLabel (eran el rectángulo opaco
    # que tapaba el gradiente del encabezado en V446).
    status_canvas = AIStatusCanvas(ai_card, accent=COLORS['green'])
    status_canvas.pack(fill='both', expand=True)
    app._header_ai_native_canvas = status_canvas
    status_canvas.set_power_action(lambda: getattr(app, 'toggle_local_ai', lambda: None)())
    status_canvas.set_power_enabled(getattr(app, '_ai_local_enabled', True))
    ai_card._cp_ai_native_canvas = status_canvas  # lienzo integrado al fondo

    app._ai_card = ai_card
    app._ai_accent = status_canvas.accent_control
    app._ai_status = status_canvas.text_control
    app._ai_title = None
    app._ai_badge = None
    app._ai_dot = None
    app._ai_mode = None
    app._ai_state = None
    app._ai_detail = status_canvas.detail_control
    app._header_last_update = None

    app._header_ai_dot = None
    app._header_ai_text = status_canvas.text_control
    app._header_ai_hint = None
    app._header_meta = ai_card
    app._header_meta_hint = None
    app._header_ai_divider = None

    def _bind_ai_open(widget):
        try:
            widget.bind('<Button-1>', lambda _event: getattr(app, 'open_ai_center', lambda: None)(), add='+')
            widget.configure(cursor='hand2')
        except Exception:
            pass
        try:
            for child in widget.winfo_children():
                _bind_ai_open(child)
        except Exception:
            pass
    _bind_ai_open(ai_card)

    _start_device_identity_load(app)
    return header




def _status_card_surface(accent):
    if accent == COLORS['primary']:
        return role_color('accent_soft')
    if accent == COLORS['green']:
        return role_color('ok_bg')
    if accent == COLORS['purple']:
        return theme_color('#17182f')
    if accent == COLORS['amber']:
        return role_color('warn_bg')
    if accent == COLORS['red']:
        return role_color('bad_bg')
    return COLORS['surface_2']


def _health_status_card(parent):
    card = ctk.CTkFrame(
        parent,
        fg_color=COLORS['surface'],
        border_width=0,
        border_color=COLORS['surface'],
        corner_radius=15,
        height=124,
    )
    card.pack_propagate(False)

    # V434: eliminar el panel interior distinguible bajo Salud. Todo el árbol
    # de CTkFrames y sus CTkLabels recibe el mismo material que la raíz.
    shell = ctk.CTkFrame(card, fg_color=COLORS['surface'], corner_radius=0)
    shell.pack(fill='both', expand=True)

    side_accent = ctk.CTkFrame(shell, fg_color=COLORS['green'], width=4, corner_radius=14)
    side_accent.pack(side='left', fill='y', padx=(1, 0), pady=1)

    # V428: grid child wrappers must use exactly the same glass material as
    # the health card. CTk's inherited 'transparent' backgrounds were painting
    # black rectangles behind the icon and metric labels on some Windows DPIs.
    row = ctk.CTkFrame(shell, fg_color=COLORS['surface'], corner_radius=0)
    row.pack(side='left', fill='both', expand=True, padx=(12, 12), pady=(10, 10))
    body = ctk.CTkFrame(row, fg_color=COLORS['surface'], corner_radius=0)
    body.pack(side='left', fill='both', expand=True)
    body.grid_columnconfigure(1, weight=1)
    body.grid_rowconfigure(3, weight=0)

    icon_box = StatusSymbol(
        row, kind='health',
        text='',
        width=40,
        height=40,
        corner_radius=14,
        fg_color=_status_card_surface(COLORS['green']),
        text_color=COLORS['green'],
        font=(FONT, 16, 'bold'),
    )
    icon_box.pack(side='left', before=body, padx=(0, 12))

    eyebrow_label = ctk.CTkLabel(
        body,
        text='SALUD DEL SISTEMA',
        font=(FONT, 8, 'bold'),
        text_color=COLORS['green'],
        anchor='w',
    )
    eyebrow_label.grid(row=0, column=1, sticky='w')

    title_label = ctk.CTkLabel(
        body,
        text='ÍNDICE DE SALUD',
        font=(FONT, 9, 'bold'),
        text_color=COLORS['text'],
        anchor='w',
    )
    title_label.grid(row=1, column=1, sticky='w', pady=(2, 0))

    metrics_row = ctk.CTkFrame(body, fg_color=COLORS['surface'], corner_radius=0)
    metrics_row.grid(row=2, column=1, sticky='ew', pady=(5, 0))
    metrics_row.grid_columnconfigure(0, weight=0)
    metrics_row.grid_columnconfigure(1, weight=1)

    value = ctk.CTkLabel(
        metrics_row,
        text='--%',
        font=(FONT, 27, 'bold'),
        text_color=COLORS['text'],
        anchor='w',
    )
    value.grid(row=0, column=0, sticky='w')

    pill = ctk.CTkLabel(
        metrics_row,
        text='Evaluando',
        font=(FONT, 8, 'bold'),
        text_color=COLORS['green'],
        fg_color=_status_card_surface(COLORS['green']),
        corner_radius=10,
        padx=9,
        pady=3,
        anchor='center',
    )
    pill.grid(row=0, column=1, sticky='e', padx=(8, 0), pady=(2, 0))

    status_strip = ctk.CTkFrame(body, fg_color=COLORS['surface'], corner_radius=0)
    status_strip.grid(row=3, column=1, sticky='w', pady=(4, 0))
    semaphore_normal = ctk.CTkLabel(
        status_strip, text='●', width=12, height=12,
        font=(FONT, 9, 'bold'), text_color=COLORS['green']
    )
    semaphore_normal.pack(side='left')
    semaphore_warning = ctk.CTkLabel(
        status_strip, text='●', width=12, height=12,
        font=(FONT, 9, 'bold'), text_color=theme_color('#5f4a1d')
    )
    semaphore_warning.pack(side='left', padx=(3, 0))
    semaphore_critical = ctk.CTkLabel(
        status_strip, text='●', width=12, height=12,
        font=(FONT, 9, 'bold'), text_color=theme_color('#5a2630')
    )
    semaphore_critical.pack(side='left', padx=(3, 0))
    ctk.CTkLabel(
        status_strip,
        text='Estado',
        font=(FONT, 7, 'bold'),
        text_color=COLORS['text'],
        anchor='w',
    ).pack(side='left', padx=(7, 0))

    summary = ctk.CTkLabel(
        body,
        text='Evaluando estado general…',
        font=(FONT, 8),
        text_color=COLORS['text'],
        justify='left',
        anchor='w',
        wraplength=195,
    )
    summary.grid(row=4, column=1, sticky='ew', pady=(2, 0))

    progress = ctk.CTkProgressBar(
        body,
        height=7,
        corner_radius=5,
        progress_color=COLORS['green'],
        fg_color=COLORS['track'],
        border_width=0,
    )
    progress.set(0.0)
    progress.grid(row=5, column=1, sticky='ew', pady=(7, 0))

    hint = ctk.CTkLabel(
        body,
        text='Pasa el mouse para ver detalles',
        font=(FONT, 7),
        text_color=COLORS['muted'],
        anchor='w',
    )
    hint.grid(row=6, column=1, sticky='w', pady=(3, 0))

    # A single explicit background for health CTkLabels prevents the default
    # opaque parent-color fallback from looking like extra card borders.
    for health_label in (
        icon_box, eyebrow_label, title_label, value, pill,
        semaphore_normal, semaphore_warning, semaphore_critical, summary, hint,
    ):
        health_label.configure(bg_color=COLORS['surface'])

    card._cp_title_label = title_label
    card._cp_eyebrow_label = eyebrow_label
    card._cp_value_label = value
    card._cp_detail_label = summary
    card._cp_icon_label = icon_box
    card._cp_health_shell = shell
    card._cp_health_body = body
    card._cp_health_metrics_row = metrics_row
    card._cp_health_status_strip = status_strip
    card._cp_health_background_labels = (
        eyebrow_label, title_label, value, summary, hint,
        semaphore_normal, semaphore_warning, semaphore_critical,
    )
    card._cp_health_accent = side_accent
    side_accent._cp_native_accent_strip = True
    card._cp_health_pill = pill
    card._cp_health_progress = progress
    card._cp_health_hint = hint
    card._cp_health_semaphore_normal = semaphore_normal
    card._cp_health_semaphore_warning = semaphore_warning
    card._cp_health_semaphore_critical = semaphore_critical
    return card, icon_box, value, summary


def _status_card(parent, icon, title, *, accent, eyebrow='Módulo'):
    card = ctk.CTkFrame(
        parent,
        fg_color=COLORS['surface'],
        border_width=0,
        border_color=COLORS['surface'],
        corner_radius=15,
        height=124,
    )
    card.pack_propagate(False)

    shell = ctk.CTkFrame(card, fg_color='transparent')
    shell.pack(fill='both', expand=True, padx=(0, 0), pady=(0, 0))

    side_accent = ctk.CTkFrame(shell, fg_color=accent, width=4, corner_radius=14)
    side_accent.pack(side='left', fill='y', padx=(1, 0), pady=1)

    row = ctk.CTkFrame(shell, fg_color='transparent')
    row.pack(side='left', fill='both', expand=True, padx=(12, 12), pady=(10, 11))

    icon_box = StatusSymbol(
        row, kind={'!': 'watch', '◎': 'trace', '◷': 'session'}.get(icon, 'watch'),
        text='',
        width=44,
        height=44,
        corner_radius=14,
        fg_color=_status_card_surface(accent),
        text_color=accent,
        font=(FONT, 15, 'bold'),
    )
    icon_box.pack(side='left', padx=(0, 10))

    text_box = ctk.CTkFrame(row, fg_color='transparent')
    text_box.pack(side='left', fill='both', expand=True)
    eyebrow_label = ctk.CTkLabel(
        text_box,
        text=str(eyebrow).upper(),
        font=(FONT, 8, 'bold'),
        text_color=accent,
        anchor='w',
    )
    eyebrow_label.pack(anchor='w')
    title_label = ctk.CTkLabel(
        text_box,
        text=title,
        font=(FONT, 9, 'bold'),
        text_color=COLORS['text'],
        anchor='w',
    )
    title_label.pack(anchor='w', pady=(2, 0))
    value = ctk.CTkLabel(
        text_box,
        text='--',
        font=(FONT, 18, 'bold'),
        text_color=COLORS['text'],
        anchor='w',
    )
    value.pack(anchor='w', pady=(5, 0))
    detail = ctk.CTkLabel(
        text_box,
        text='',
        font=(FONT, 9),
        text_color=COLORS['text'],
        justify='left',
        anchor='w',
        wraplength=190,
    )
    detail.pack(anchor='w', pady=(2, 0))

    action_button = ctk.CTkButton(
        card,
        text='Reiniciar',
        width=82,
        height=24,
        corner_radius=8,
        fg_color=role_color('warn_bg'),
        hover_color=COLORS['red'],
        border_width=1,
        border_color=COLORS['red'],
        text_color=COLORS['red'],
        font=(FONT, 8, 'bold'),
    )
    try:
        action_button.place_forget()
    except Exception:
        pass

    card._cp_title_label = title_label
    card._cp_eyebrow_label = eyebrow_label
    card._cp_value_label = value
    card._cp_detail_label = detail
    card._cp_icon_label = icon_box
    card._cp_status_accent = side_accent
    card._cp_action_button = action_button
    card._cp_action_visible = False
    side_accent._cp_native_accent_strip = True
    return card, icon_box, value, detail

def _build_system_band(app):
    """Jerarquía superior: estado/condición primero; datos/sesión después."""
    band = ctk.CTkFrame(app.main_content, fg_color='transparent', height=124)
    band.pack_propagate(False)
    band.grid_columnconfigure(0, weight=5, uniform='dashboard_status_primary')
    band.grid_columnconfigure(1, weight=5, uniform='dashboard_status_primary')
    band.grid_columnconfigure(2, weight=3, uniform='dashboard_status_secondary')
    band.grid_columnconfigure(3, weight=3, uniform='dashboard_status_secondary')
    band.grid_rowconfigure(0, weight=1)

    health_card, app._health_icon, app._health_status, app._health_score = _health_status_card(band)
    health_card.grid(row=0, column=0, sticky='nsew', padx=(0, 5))
    app._health_status.configure(text='--%', text_color=COLORS['green'])
    app._health_score.configure(text='Evaluando estado general…')
    app._health_accent = getattr(health_card, '_cp_health_accent', None)
    app._health_pill = getattr(health_card, '_cp_health_pill', None)
    app._health_progress = getattr(health_card, '_cp_health_progress', None)
    app._health_hint = getattr(health_card, '_cp_health_hint', None)
    app._health_semaphore_normal = getattr(health_card, '_cp_health_semaphore_normal', None)
    app._health_semaphore_warning = getattr(health_card, '_cp_health_semaphore_warning', None)
    app._health_semaphore_critical = getattr(health_card, '_cp_health_semaphore_critical', None)

    alerts, app._alert_icon, app._alert_value, app._alert_detail = _status_card(
        band,
        '!',
        'CONDICIÓN Y ALERTAS',
        accent=COLORS['amber'],
        eyebrow='Supervisión actual',
    )
    alerts.grid(row=0, column=1, sticky='nsew', padx=(0, 5))
    app._alert_value.configure(text='Sin alertas activas', text_color=COLORS['green'], justify='left', anchor='w', wraplength=185)
    app._alert_detail.configure(text='')
    app._alert_detail.pack_forget()

    coverage, app._coverage_icon, app._coverage_value, app._coverage_detail = _status_card(
        band,
        '◎',
        'DATOS VÁLIDOS',
        accent=COLORS['primary'],
        eyebrow='Trazabilidad',
    )
    coverage.grid(row=0, column=2, sticky='nsew', padx=5)
    app._coverage_value.configure(text='Esperando')
    app._coverage_detail.configure(text='')
    app._coverage_detail.pack_forget()

    uptime, app._uptime_icon, app._uptime_value, app._uptime_detail = _status_card(
        band,
        '◷',
        'TIEMPO ACTIVO',
        accent=COLORS['purple'],
        eyebrow='Sesión',
    )
    uptime.grid(row=0, column=3, sticky='nsew', padx=(5, 0))
    app._uptime_value.configure(text=_uptime_text())
    app._uptime_detail.configure(text='')
    app._uptime_detail.pack_forget()
    app._uptime_restart_button = getattr(uptime, '_cp_action_button', None)
    try:
        if app._uptime_restart_button is not None:
            app._uptime_restart_button.configure(
                text='Reiniciar PC',
                command=getattr(app, 'request_system_restart', None),
            )
            app._uptime_restart_button.place_forget()
    except Exception:
        pass

    _bind_click_tree(health_card, getattr(app, 'open_smart_alert_window', None))
    _bind_card_hover(health_card)
    _bind_hover_tooltip(health_card, lambda: _health_hover_text(app))
    _bind_click_tree(alerts, getattr(app, 'open_smart_alert_window', None))
    _bind_card_hover(alerts)
    _bind_click_tree(coverage, getattr(app, 'open_telemetry_details', None))
    _bind_card_hover(coverage)
    # La tarjeta Sesión también reacciona visualmente, sin acción al pulsarla.
    _bind_card_hover(uptime)

    app._status_cards = (health_card, alerts, coverage, uptime)
    return band

def _rebuild_sidebar(app):
    # V223: no acumular labels/bloques dinámicos entre cierre y reapertura.
    # Los controles funcionales originales se conservan; todo lo creado por el
    # dashboard profesional se destruye antes de reconstruirlo.
    persistent = {
        getattr(app, 'frame_logo', None),
        getattr(app, 'lbl_subtitle', None),
        getattr(app, 'card_health_sidebar', None),
        getattr(app, 'btn_overlay', None),
        getattr(app, 'btn_benchmark', None),
        getattr(app, 'btn_diagnostic', None),
        getattr(app, 'btn_health_center', None),
        getattr(app, 'btn_pdf', None),
        getattr(app, 'btn_cleanup', None),
        getattr(app, 'btn_tweaks', None),
        getattr(app, 'btn_network', None),
        getattr(app, 'btn_smart_alerts', None),
        getattr(app, 'btn_session_trends', None),
        getattr(app, 'btn_alert_history', None),
    }
    for child in list(app.sidebar.winfo_children()):
        try:
            if child in persistent:
                child.pack_forget()
            else:
                child.destroy()
        except Exception:
            pass

    # V332: el módulo de Actualizaciones de CorePulse sigue retirado. Limpiamos
    # cualquier referencia heredada que pudiera quedar de una rama antigua antes
    # de reconstruir Personalización. Drivers/Windows Update no se ven afectados.
    for attr in ('_btn_summary', '_theme_toggle_button', '_ai_button',
                 '_updates_button', '_update_button', 'btn_updates', 'btn_update',
                 '_personalization_block', '_personalization_label', '_personalization_hint', '_personalization_divider', '_sidebar_version',
                 '_personalization_top_divider', '_sidebar_top_controls', '_sidebar_menu_button', '_sidebar_close_button', '_sidebar_hover_close_ready', '_sidebar_hover_close_state', '_sidebar_hover_expand_state', '_sidebar_native_border'):
        try:
            setattr(app, attr, None)
        except Exception:
            pass

    collapsed = False
    try:
        sidebar_width = int(app._sidebar_target_width())
    except Exception:
        sidebar_width = 232
    _safe_config(app.sidebar, fg_color='transparent', width=sidebar_width, border_width=0, corner_radius=0)
    _ensure_sidebar_native_border(app)
    try:
        if getattr(app, 'workspace_background', None) is not None:
            app.workspace_background.register_surface(app.sidebar)
    except Exception:
        pass

    _safe_pack_forget(app.frame_logo)
    _safe_pack_forget(getattr(app, 'lbl_logo_icon', None))
    _safe_pack_forget(app.lbl_brand)
    _safe_config(app.lbl_brand, text='')
    _safe_pack_forget(app.lbl_subtitle)
    _safe_config(app.lbl_subtitle, text='')
    _safe_pack_forget(app.card_health_sidebar)

    app._sidebar_brand_title = None
    app._sidebar_brand_company = None
    app._sidebar_brand_block = None
    app._sidebar_brand_rule = None

    # V224: retirar cualquier flecha/widget flotante heredado de V212–V223.
    old_toggle = getattr(app, '_sidebar_toggle_button', None)
    if old_toggle is not None:
        try:
            old_toggle.place_forget()
            old_toggle.destroy()
        except Exception:
            pass
    app._sidebar_toggle_button = None

    # V277: cabecera superior limpia. La X no queda fija a la izquierda;
    # aparece arriba a la derecha únicamente al entrar con el mouse al sidebar.
    top_controls = ctk.CTkFrame(app.sidebar, fg_color='transparent', height=26)
    top_controls.pack(fill='x', padx=14, pady=(9, 5))
    top_controls.pack_propagate(False)
    app._sidebar_top_controls = top_controls
    app._sidebar_menu_button = None

    close_button = ctk.CTkLabel(
        top_controls,
        text='✕',
        width=24,
        height=24,
        fg_color='transparent',
        text_color=COLORS['text_2'],
        font=(FONT, 14, 'bold'),
        anchor='center',
    )
    _bind_sidebar_glyph(close_button, getattr(app, 'toggle_sidebar_collapse', None))
    app._sidebar_close_button = close_button
    app._sidebar_hover_close_ready = False

    _sidebar_divider(app.sidebar).pack(fill='x', padx=14, pady=(0, 8))

    monitor = _section_label(app.sidebar, 'MONITOREO')
    monitor.pack(fill='x', padx=17, pady=(3, 3))
    _load_sidebar_icons(app)

    app._btn_summary = ctk.CTkButton(app.sidebar, text='Resumen', command=lambda: None)
    _apply_sidebar_icon(app, '_btn_summary', active=True, collapsed=False)
    app._btn_summary.pack(fill='x', padx=10, pady=1)

    _apply_sidebar_icon(app, 'btn_benchmark', collapsed=False)
    app.btn_benchmark.pack(fill='x', padx=10, pady=(1, 4))
    _sidebar_divider(app.sidebar).pack(fill='x', padx=14, pady=(4, 5))

    diagnosis = _section_label(app.sidebar, 'DIAGNÓSTICO')
    diagnosis.pack(fill='x', padx=17, pady=(6, 3))
    _apply_sidebar_icon(app, 'btn_diagnostic', collapsed=False)
    app.btn_diagnostic.pack(fill='x', padx=10, pady=1)
    _apply_sidebar_icon(app, 'btn_health_center', collapsed=False)
    app.btn_health_center.pack(fill='x', padx=10, pady=1)
    _safe_pack_forget(app.btn_pdf)
    _sidebar_divider(app.sidebar).pack(fill='x', padx=14, pady=(4, 5))

    maintenance = _section_label(app.sidebar, 'MANTENIMIENTO')
    maintenance.pack(fill='x', padx=17, pady=(6, 3))
    _apply_sidebar_icon(app, 'btn_cleanup', collapsed=False)
    app.btn_cleanup.pack(fill='x', padx=10, pady=1)
    _apply_sidebar_icon(app, 'btn_tweaks', collapsed=False)
    app.btn_tweaks.pack(fill='x', padx=10, pady=1)
    _apply_sidebar_icon(app, 'btn_network', collapsed=False)
    app.btn_network.pack(fill='x', padx=10, pady=1)
    _sidebar_divider(app.sidebar).pack(fill='x', padx=14, pady=(4, 5))

    history = _section_label(app.sidebar, 'HISTORIAL')
    history.pack(fill='x', padx=17, pady=(6, 3))
    _apply_sidebar_icon(app, 'btn_smart_alerts', collapsed=False)
    app.btn_smart_alerts.pack(fill='x', padx=10, pady=1)
    _apply_sidebar_icon(app, 'btn_session_trends', collapsed=False)
    app.btn_session_trends.pack(fill='x', padx=10, pady=1)
    _apply_sidebar_icon(app, 'btn_alert_history', collapsed=False)
    app.btn_alert_history.pack(fill='x', padx=10, pady=1)

    # V423: Personalización deja de construirse como bloque separado.
    # Desde aquí usa exactamente el mismo flujo del resto del sidebar.
    app._personalization_block = None

    personal_top_divider = _sidebar_divider(app.sidebar)
    personal_top_divider.pack(fill='x', padx=14, pady=(4, 5))
    app._personalization_top_divider = personal_top_divider

    personalization = _section_label(app.sidebar, 'PERSONALIZACIÓN')
    app._personalization_label = personalization
    personalization.pack(fill='x', padx=17, pady=(6, 3))
    app._personalization_hint = None

    app._theme_toggle_button = ctk.CTkButton(
        app.sidebar,
        text='Temas',
        height=38,
        corner_radius=11,
        fg_color='transparent',
        bg_color='transparent',
        hover_color=role_color('sidebar'),
        hover=False,
        border_width=0,
        border_color=COLORS['purple'],
        text_color=COLORS['text_2'],
        font=(FONT, 11, 'bold'),
        anchor='w',
        command=getattr(app, 'open_themes', None),
    )
    app._theme_toggle_button.pack(fill='x', padx=10, pady=1)
    _apply_sidebar_icon(app, '_theme_toggle_button', collapsed=False)

    app._ai_button = ctk.CTkButton(
        app.sidebar,
        text='CorePulse AI',
        height=38,
        corner_radius=11,
        fg_color='transparent',
        bg_color='transparent',
        hover_color=role_color('sidebar'),
        hover=False,
        border_width=0,
        border_color=COLORS['green'],
        text_color=COLORS['text_2'],
        font=(FONT, 11, 'bold'),
        anchor='w',
        command=getattr(app, 'open_ai_center', None),
    )
    app._ai_button.pack(fill='x', padx=10, pady=1)
    _apply_sidebar_icon(app, '_ai_button', collapsed=False)

    divider = ctk.CTkFrame(app.sidebar, fg_color='transparent', height=0, corner_radius=0)
    divider.pack_forget()
    app._personalization_divider = divider

    app._sidebar_version = ctk.CTkLabel(
        app.sidebar,
        text='',
        height=14,
        font=(FONT, 7),
        text_color=COLORS['muted'],
        anchor='w',
    )
    app._sidebar_version.pack(fill='x', padx=17, pady=(0, 0))

    _install_sidebar_hover_close(app)
    _install_sidebar_hover_expand(app)
    _sync_sidebar_visibility_controls(app)
    # V425: registrar también los wrappers de la cabecera lateral para que
    # adopten el mismo Surface Studio y no generen bandas opacas.
    try:
        if getattr(app, 'workspace_background', None) is not None:
            app.workspace_background.register_page(app.sidebar, max_depth=2)
    except Exception:
        pass
    try:
        app.after_idle(lambda: _sync_sidebar_native_border_to_content(app))
    except Exception:
        _sync_sidebar_native_border_to_content(app)


def _style_existing_cards(app):
    specs = (
        (app.card_cpu, app.lbl_cpu_title, app.lbl_cpu, app.lbl_cpu_temp, app.bar_cpu, COLORS['primary']),
        (app.card_ram, app.lbl_ram_title, app.lbl_ram, app.lbl_ram_gb, app.bar_ram, COLORS['green']),
        (app.card_gpu, app.lbl_gpu_title, app.lbl_gpu, app.lbl_gpu_temp, app.bar_gpu, COLORS['purple']),
    )
    for card, title, value, detail, bar, accent in specs:
        _safe_config(
            card,
            fg_color=COLORS['surface'],
            border_color=COLORS['surface'],
            border_width=0,
            corner_radius=16,
        )
        _safe_config(title, font=(FONT, 9, 'bold'), text_color=COLORS['text_2'], justify='left', anchor='w')
        _safe_config(value, font=(FONT, 30, 'bold'), text_color=COLORS['text'])
        _safe_config(detail, font=(FONT, 9, 'bold'), text_color=accent)
        _safe_config(bar, height=6, progress_color=accent, fg_color=COLORS['track'])
        _ensure_resource_card_decor(app, card, accent, 'CPU' if card is app.card_cpu else 'MEMORIA RAM' if card is app.card_ram else 'GPU')


    # La ficha CPU es navegable y expone una acción explícita con el mismo
    # lenguaje visual del Dashboard. El botón no usa flechas ni símbolos ajenos
    # a la identidad de CorePulse.
    cpu_callback = getattr(app, 'open_cpu_details', None)
    if callable(cpu_callback):
        _bind_click_tree(app.card_cpu, cpu_callback)
        if getattr(app, '_cpu_details_button', None) is None:
            app._cpu_details_button = ctk.CTkButton(
                app.card_cpu,
                text='Ver detalles',
                width=92,
                height=24,
                corner_radius=7,
                fg_color=role_color('accent_2'),
                hover_color=role_color('accent'),
                border_width=1,
                border_color=role_color('accent'),
                text_color=role_color('text'),
                font=(FONT, 8, 'bold'),
                command=cpu_callback,
            )
        _safe_config(app.lbl_cpu_title, wraplength=285)
        _bind_card_hover(
            app.card_cpu,
            action_button=app._cpu_details_button,
            action_place={'relx': 1.0, 'rely': 0.0, 'x': -10, 'y': 8, 'anchor': 'ne'},
        )

    # RAM completa la simetría de las tres tarjetas principales. La ficha completa
    # se alimenta del snapshot certificado y carga el inventario Windows/SMBIOS
    # fuera del hilo gráfico para conservar una navegación fluida.
    ram_callback = getattr(app, 'open_ram_details', None)
    if callable(ram_callback):
        _bind_click_tree(app.card_ram, ram_callback)
        if getattr(app, '_ram_details_button', None) is None:
            app._ram_details_button = ctk.CTkButton(
                app.card_ram,
                text='Ver detalles',
                width=92,
                height=24,
                corner_radius=7,
                fg_color=role_color('accent_2'),
                hover_color=role_color('accent'),
                border_width=1,
                border_color=role_color('accent'),
                text_color=role_color('text'),
                font=(FONT, 8, 'bold'),
                command=ram_callback,
            )
        _safe_config(app.lbl_ram_title, wraplength=285)
        _bind_card_hover(
            app.card_ram,
            action_button=app._ram_details_button,
            action_place={'relx': 1.0, 'rely': 0.0, 'x': -10, 'y': 8, 'anchor': 'ne'},
        )

    # La ficha GPU usa exactamente el mismo patrón visual y de navegación que CPU.
    # No prioriza marcas: la vista selecciona inicialmente la GPU representativa por
    # actividad real y permite cambiar entre todos los adaptadores detectados.
    gpu_callback = getattr(app, 'open_gpu_details', None)
    if callable(gpu_callback):
        _bind_click_tree(app.card_gpu, gpu_callback)
        if getattr(app, '_gpu_details_button', None) is None:
            app._gpu_details_button = ctk.CTkButton(
                app.card_gpu,
                text='Ver detalles',
                width=92,
                height=24,
                corner_radius=7,
                fg_color=role_color('accent_2'),
                hover_color=role_color('accent'),
                border_width=1,
                border_color=role_color('accent'),
                text_color=role_color('text'),
                font=(FONT, 8, 'bold'),
                command=gpu_callback,
            )
        _safe_config(app.lbl_gpu_title, wraplength=285)
        _bind_card_hover(
            app.card_gpu,
            action_button=app._gpu_details_button,
            action_place={'relx': 1.0, 'rely': 0.0, 'x': -10, 'y': 8, 'anchor': 'ne'},
        )

    _apply_resource_card_geometry(app)
    request_native_card_surface_sync(app)


def _series_stats(values):
    clean = []
    for value in values or []:
        try:
            number = float(value)
        except Exception:
            continue
        if math.isfinite(number):
            clean.append(number)
    if not clean:
        return None
    return {
        'average': sum(clean) / len(clean),
        'peak': max(clean),
    }


def _update_trend_titles(app):
    """Mantiene títulos limpios; promedio/pico quedan fuera del Resumen.

    El detalle estadístico completo pertenece a Tendencias. El Resumen sólo
    necesita mostrar la forma de la serie para evitar duplicación de datos.
    """
    titles = (
        (app.ax_cpu, 'CPU (%)', COLORS['primary']),
        (app.ax_ram, 'RAM (%)', COLORS['green']),
        (app.ax_gpu, 'GPU (%)', COLORS['purple']),
    )
    for ax, text, color in titles:
        try:
            ax.set_title(text, color=color, fontsize=9, fontweight='bold', pad=8)
        except Exception:
            pass


def _apply_chart_geometry_alignment(app):
    """Delega la geometría a la autoridad responsiva del dashboard.

    `dashboard_layout` calcula el alto útil de la tarjeta, descuenta la cabecera
    real y redimensiona el FigureCanvas para que los gráficos se mantengan
    legibles tanto en ventanas compactas como amplias.
    """
    try:
        from gui.dashboard_layout import request_chart_reflow
        request_chart_reflow(app, redraw=False)
    except Exception:
        pass


def _style_charts(app):
    # V432: este era el tercer escritor que RESTAURABA el marco exterior.
    # El contenedor, la figura y el canvas usan un único material, sin bordes.
    _safe_config(
        app.frame_charts,
        fg_color='transparent',
        border_width=0,
        corner_radius=0,
    )
    try:
        # No generar decoraciones superpuestas en el marco externo.
        for bar in getattr(app, '_chart_top_accents', ()) or ():
            try:
                bar.destroy()
            except (tk.TclError, AttributeError):
                pass
        app._chart_top_accents = []
        app.fig.set_frameon(True)
        app.fig.set_facecolor(COLORS['surface'])
        app.fig.patch.set_facecolor(COLORS['surface'])
        app.fig.patch.set_edgecolor('none')
        app.fig.patch.set_linewidth(0.0)
        if getattr(app, 'canvas', None) is not None:
            try:
                app.canvas.get_tk_widget().configure(
                    bg=COLORS['surface'], highlightthickness=0, bd=0, relief='flat',
                )
            except (tk.TclError, AttributeError):
                pass
        axes = (app.ax_cpu, app.ax_ram, app.ax_gpu)
        for ax in axes:
            ax.set_facecolor('none')  # V444: mismo fondo nativo debajo de los ejes
            ax.tick_params(axis='x', colors=COLORS['muted'], labelsize=8, length=0, pad=6)
            ax.tick_params(axis='y', colors=COLORS['muted'], labelsize=8, length=0, pad=6, labelleft=True)
            ax.grid(False)
            ax.yaxis.grid(True, color=COLORS['border_soft'], linestyle='-', linewidth=0.55, alpha=0.72)
            ax.set_axisbelow(True)
            ax.set_yticks([25, 50, 75, 100])
            ax.set_xticks([0, 6, 12, 18, 24])
            ax.set_xticklabels(['-60s', '-45s', '-30s', '-15s', 'Ahora'])
            ax.margins(x=0.02, y=0.10)
            for spine in ax.spines.values():
                spine.set_visible(False)  # V444: no recrear el marco al aplicar el tema
        _update_trend_titles(app)
        _apply_chart_geometry_alignment(app)
        try:
            from gui.chart_workspace_surface import sync_chart_workspace_surface
            sync_chart_workspace_surface(app)
        except Exception:
            pass
        app.background = None
        app.canvas.draw_idle()
    except Exception:
        pass

def _rebuild_main_layout(app):
    children = list(app.main_content.winfo_children())
    storage_label = None
    for child in children:
        try:
            if isinstance(child, ctk.CTkLabel) and 'UNIDADES DE ALMACENAMIENTO' in str(child.cget('text')):
                storage_label = child
        except Exception:
            pass

    for child in children:
        _safe_pack_forget(child)

    app._header = _build_header(app)
    app._header.pack(fill='x', pady=(0, 2))
    if getattr(app, 'workspace_background', None) is not None:
        # V408: el encabezado del Resumen ya no debe percibirse como una banda.
        # Registramos wrappers estructurales para que muestren el mismo
        # diseño nativo alineado que el resto del workspace.
        app.workspace_background.register_page(app._header, max_depth=4)
        app.workspace_background.register_canvas(getattr(app, '_header_identity_canvas', None))
        app.workspace_background.register_canvas(getattr(app, '_header_ai_native_canvas', None))
        app.workspace_background.register_surface(app.frame_meters)

    app._status_band = _build_system_band(app)
    app._status_band.pack(fill='x', pady=(0, 8))
    if getattr(app, 'workspace_background', None) is not None:
        app.workspace_background.register_surface(app._status_band)

    if getattr(app, '_resources_section', None) is not None:
        _safe_pack_forget(app._resources_section)
    app.frame_meters.pack(fill='x', pady=(0, 10))
    _safe_pack_forget(app.alert_summary_bar)

    if getattr(app, '_storage_section_header', None) is not None:
        _safe_pack_forget(app._storage_section_header)
    if storage_label is not None:
        try:
            storage_label.pack_forget()
        except Exception:
            pass

    _safe_config(app.scroll_disks, fg_color='transparent')
    try:
        # V0.10.2.28w: impedir que el Canvas interno del viewport de discos
        # vuelva a imponer su altura solicitada durante reconstrucciones visuales.
        app.scroll_disks.grid_propagate(False)
    except Exception:
        pass
    app.scroll_disks.pack(fill='x', expand=False, pady=(0, 3))

    if getattr(app, '_trends_section_header', None) is not None:
        _safe_pack_forget(app._trends_section_header)
    app.frame_charts.pack(fill='x', expand=False, pady=(6, 0))
    if getattr(app, 'workspace_background', None) is not None:
        app.workspace_background.register_surface(app.frame_charts)

    request_native_card_surface_sync(app)

    # Al cambiar tamaño de ventana, gráficos o menú, el cierre inferior del
    # sidebar sigue la línea inferior REAL de los gráficos. add='+' conserva
    # los bindings del gráfico existentes.
    if not getattr(app, '_sidebar_charts_align_bound', False):
        def _sync_sidebar_to_charts(_event=None):
            if getattr(app, '_sidebar_charts_sync_job', None) is not None:
                return
            def _commit():
                app._sidebar_charts_sync_job = None
                try:
                    if not app.winfo_exists():
                        return
                    _sync_sidebar_native_border_to_content(app)
                except Exception:
                    pass
            try:
                app._sidebar_charts_sync_job = app.after_idle(_commit)
            except Exception:
                app._sidebar_charts_sync_job = None
        app.frame_charts.bind('<Configure>', _sync_sidebar_to_charts, add='+')
        app._sidebar_charts_align_bound = True
    try:
        app.after_idle(lambda: _sync_sidebar_native_border_to_content(app))
    except Exception:
        pass

    _style_existing_cards(app)
    _style_charts(app)
    # V416: reflejo óptico sólo dentro de tarjetas del Resumen.
    from gui.glass_cards import install_glass_cards
    install_glass_cards(app)


def _apply_uptime_semantics(app):
    hours = _uptime_hours_value()
    text = _uptime_text()
    value_color = COLORS['text']
    detail_text = ''
    detail_color = COLORS['muted']
    state = 'unknown'
    icon_color = COLORS['muted']
    show_restart = False

    if isinstance(hours, (int, float)):
        if hours >= 10.0:
            state = 'critical'
            icon_color = COLORS['red']
            value_color = COLORS['red']
            detail_color = COLORS['red']
            detail_text = 'Más de 10 horas activas · se recomienda reiniciar el PC.'
            show_restart = True
        elif hours >= 8.0:
            state = 'warning'
            icon_color = COLORS['amber']
            value_color = COLORS['amber']
            detail_color = COLORS['amber']
            detail_text = 'Sesión prolongada · conviene planificar un reinicio pronto.'
        else:
            state = 'active' if getattr(app, 'is_running', False) else 'unknown'
            icon_color = COLORS['purple'] if getattr(app, 'is_running', False) else COLORS['muted']

    try:
        app._uptime_icon.set_condition(state, icon_color)
    except Exception:
        pass
    _safe_config(getattr(app, '_uptime_value', None), text=text, text_color=value_color)
    try:
        detail = getattr(app, '_uptime_detail', None)
        if detail is not None:
            if detail_text:
                detail.configure(text=detail_text, text_color=detail_color)
                if not detail.winfo_manager():
                    detail.pack(anchor='w', pady=(2, 0))
            else:
                detail.configure(text='')
                if detail.winfo_manager():
                    detail.pack_forget()
    except Exception:
        pass

    btn = getattr(app, '_uptime_restart_button', None)
    card = None
    try:
        cards = tuple(getattr(app, '_status_cards', ()) or ())
        card = cards[3] if len(cards) >= 4 else None
    except Exception:
        card = None
    try:
        if btn is not None and card is not None:
            if show_restart:
                btn.configure(state='normal')
                if not getattr(card, '_cp_action_visible', False):
                    btn.place(relx=1.0, rely=1.0, x=-12, y=-10, anchor='se')
                    card._cp_action_visible = True
            else:
                btn.place_forget()
                card._cp_action_visible = False
    except Exception:
        pass


def _wrap_telemetry_update(app):
    if getattr(app, '_dashboard_telemetry_wrapped', False):
        return
    original = app.apply_telemetry_to_ui

    def wrapped(self, telemetry, disks):
        original(telemetry, disks)

        # Reorganiza únicamente las etiquetas visuales; no modifica los datos.
        if isinstance(telemetry, dict):
            cpu_name = telemetry.get('cpu_name') or 'N/A'
            gpu_name = telemetry.get('gpu_name') or 'N/A'
            _safe_config(self.lbl_cpu_title, text=f'Procesador\n{cpu_name}')
            _safe_config(self.lbl_ram_title, text='Memoria RAM\nUso físico del sistema')
            _safe_config(self.lbl_gpu_title, text=f'Tarjeta Gráfica\n{gpu_name}')

        _apply_resource_card_geometry(self)

        # La salud/alertas finales son autoridad de `live_health_binding`, que
        # corre después de este wrapper. Aquí sólo dejamos un fallback de carga
        # inicial y evitamos volver a declarar 'ÓPTIMO' a partir de un score viejo
        # cuando el agente ya observa una condición instantánea más severa.
        if not isinstance(getattr(self, 'current_live_health', None), dict):
            score = getattr(self, 'latest_score', None)
            color = _status_color(score)
            name = _status_name(score)
            _safe_config(self._health_status, text=f'{float(score):.1f}%' if isinstance(score, (int, float)) else 'N/A', text_color=color)
            _safe_config(self._health_score, text=f'{name} · índice técnico' if isinstance(score, (int, float)) else 'Índice técnico N/A')
            _safe_config(self._health_icon, text='✓' if name in {'ÓPTIMO', 'ESTABLE'} else '!' if name != 'NO EVALUABLE' else '—', text_color=color)

        _update_trend_titles(self)

        valid, total = _telemetry_coverage(telemetry)
        if total:
            _safe_config(
                self._coverage_value,
                text=f'{valid} / {total} VÁLIDAS',
                text_color=COLORS['green'] if valid == total else COLORS['primary'],
            )
            _safe_config(self._coverage_detail, text='Métricas certificadas')
        else:
            _safe_config(self._coverage_value, text='N/A', text_color=COLORS['muted'])
            _safe_config(self._coverage_detail, text='Sin metadata de certificación')

        coverage_state = ('unknown' if not total or not valid else
                          'normal' if valid == total else 'warning')
        coverage_color = (COLORS['green'] if coverage_state == 'normal' else
                          COLORS['amber'] if coverage_state == 'warning' else COLORS['muted'])
        self._coverage_icon.set_condition(coverage_state, coverage_color)
        _apply_uptime_semantics(self)

    app.apply_telemetry_to_ui = types.MethodType(wrapped, app)
    app._dashboard_telemetry_wrapped = True


def _wrap_disk_update(app):
    if getattr(app, '_dashboard_disks_wrapped', False):
        return
    original = app.update_disks_ui

    def wrapped(self, disks_data):
        original(disks_data)
        by_index = {}
        for d in disks_data or []:
            try:
                by_index[d.get('index')] = d
            except Exception:
                pass

        for idx, widgets in getattr(self, 'disk_widgets', {}).items():
            d = by_index.get(idx, {})
            _safe_config(
                widgets.get('card'),
                fg_color=COLORS['surface'],
                border_color=COLORS['surface'],
                border_width=0,
                corner_radius=16,
            )
            _ensure_storage_card_decor(widgets.get('card'), widgets)
            _safe_config(widgets.get('bar'), progress_color=COLORS['primary'], fg_color=COLORS['track'], height=6)
            _safe_config(
                widgets.get('btn_details'),
                text='👁',
                width=30,
                height=24,
                font=(ICON_FONT, 12, 'bold'),
                fg_color=role_color('accent_2'),
                hover_color=role_color('accent'),
                border_width=1,
                border_color=role_color('accent'),
                text_color=role_color('text'),
                command=lambda disk_index=idx: self.open_storage_details(disk_index),
            )

            model = d.get('model') or 'Unidad de almacenamiento'
            mounts = str(d.get('mount_points') or '').strip()
            _safe_config(
                widgets.get('lbl_name'),
                text=(f'{model}   ·   {mounts}' if mounts and mounts.upper() not in {'N/A','NA','NONE','UNKNOWN'} else str(model)),
                text_color=COLORS['text'],
                font=(FONT, 10, 'bold'),
            )


            try:
                # V320: _build_fast_disk_snapshot publica 'health'. Mantener
                # health_percent sólo como compatibilidad con snapshots antiguos.
                smart = d.get('health')
                if smart is None:
                    smart = d.get('health_percent')
            except Exception:
                smart = None
            badge_text = 'Salud N/A'
            badge_color = COLORS['surface_2']
            badge_text_color = COLORS['muted']
            if isinstance(smart, (int, float)):
                smart_val = float(smart)
                badge_text = f'Salud {smart_val:.0f}%'
                if smart_val >= 90:
                    badge_color = role_color('ok_bg')
                    badge_text_color = COLORS['green']
                elif smart_val >= 70:
                    badge_color = role_color('warn_bg')
                    badge_text_color = COLORS['amber']
                else:
                    badge_color = role_color('bad_bg')
                    badge_text_color = COLORS['red']
            _safe_config(
                widgets.get('lbl_badge'),
                text=badge_text,
                fg_color=badge_color,
                text_color=badge_text_color,
                corner_radius=10,
                padx=10,
                pady=2,
                font=(FONT, 8, 'bold'),
            )

            try:
                used_raw = d.get('used_gb')
                total_raw = d.get('total_gb')
                pct_raw = d.get('used_percent')
                temp = d.get('temperature_c')

                if isinstance(used_raw, (int, float)) and isinstance(total_raw, (int, float)) and total_raw > 0:
                    used = float(used_raw)
                    total = float(total_raw)
                    available = max(0.0, total - used)
                    pct = float(pct_raw) if isinstance(pct_raw, (int, float)) else (used / total * 100.0)
                    capacity = f'Usado {used:.0f} GB  ·  Disponible {available:.0f} GB  ·  {pct:.1f}%'
                else:
                    capacity = 'Información de capacidad no disponible'

                if isinstance(temp, (int, float)):
                    capacity += f'  ·  {float(temp):.0f} °C'
                # Si Windows no expone temperatura, no añadimos un N/A visual.

                _safe_config(
                    widgets.get('lbl_exact'),
                    text=capacity,
                    text_color=COLORS['primary'],
                    font=(FONT, 9),
                )
            except Exception:
                pass

        request_native_card_surface_sync(self)
        try:
            from gui.dashboard_layout import _finalize_storage_viewport
            _finalize_storage_viewport(self, getattr(self, '_layout_mode', 'compact'))
        except Exception:
            pass

    app.update_disks_ui = types.MethodType(wrapped, app)
    app._dashboard_disks_wrapped = True


def _apply_window_contract(app):
    # No cambia geometría ni tamaño. Solo conserva el título y la paleta.
    app.title('CorePulse — Hardware Monitoring & Diagnostics')
    _safe_config(app, fg_color=COLORS['app'])
    _safe_config(app.main_content, fg_color='transparent')


def apply_professional_dashboard(app):
    """Aplica el rediseño visual sin alterar el pipeline funcional de CorePulse."""
    if getattr(app, '_professional_ui_active', False):
        return
    _apply_window_contract(app)
    _rebuild_sidebar(app)
    _rebuild_main_layout(app)
    _wrap_telemetry_update(app)
    _wrap_disk_update(app)
    app._professional_ui_active = True
    app._corepulse_design_id = DESIGN_ID


def refresh_professional_charts(app):
    """Aplica el estilo 60w a gráficos creados de forma diferida en 61w."""
    _style_charts(app)

