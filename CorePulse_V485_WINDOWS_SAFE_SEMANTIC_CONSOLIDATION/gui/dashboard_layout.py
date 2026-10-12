"""Administra la distribución responsiva del dashboard, navegación y tarjeta del agente."""
from __future__ import annotations
from gui.widget_updates import configure_changed
from core.theme_manager import color as theme_color, theme_action_label, role_color
# Código refactorizado: nombres estables y documentación en español.
import threading, types, time, os, re
import ctypes
import sys
from gui.ai_status_card import render_ai_card
import customtkinter as ctk
from core.version import VERSION_LABEL
from core.agent_reaction import agent_display_state
VERSION = VERSION_LABEL
DESIGN_ID = 'COREPULSE_REFERENCE_DASHBOARD_LAYOUT'
FONT = 'Segoe UI'
ICON_FONT = 'Segoe UI Symbol'
# V128: misma autoridad de roles exactos que la vista previa de Temas.
APP = role_color('bg')
SIDEBAR = role_color('sidebar')
SURFACE = role_color('glass_surface')
SURFACE_2 = role_color('glass_surface_2')
BORDER = role_color('glass_border')
BORDER_SOFT = role_color('glass_border')
TRACK = role_color('glass_track')
TEXT = role_color('text')
TEXT_2 = role_color('text_2')
MUTED = role_color('muted')
CYAN = role_color('accent')
GREEN = '#16d98b'
AMBER = '#f3b54a'
RED = '#ff5d6c'
PURPLE = '#a064ff'
PRIMARY_DARK = role_color('accent_2')
SIDEBAR_ACTIVE_BG = role_color('accent_2')
SIDEBAR_ACTIVE_HOVER = role_color('accent')
SIDEBAR_ACTIVE_BORDER = role_color('accent')
SIDEBAR_INACTIVE_TEXT = role_color('text_2')
RESIZE_DEBOUNCE_MS = 85
FULLSCREEN_SETTLE_MS = 420
NAV = {'_btn_summary': 'Resumen', 'btn_benchmark': 'Benchmark', 'btn_diagnostic': 'Iniciar diagnóstico', 'btn_health_center': 'Centro de salud', 'btn_cleanup': 'Limpieza de sistema', 'btn_tweaks': 'Tweaks Windows 11', 'btn_network': 'Red avanzada', 'btn_smart_alerts': 'Alertas técnicas', 'btn_session_trends': 'Tendencias', 'btn_alert_history': 'Historial de alertas'}
SIDEBAR_OPTION_ACCENTS = {
    '_btn_summary': CYAN,
    'btn_benchmark': PURPLE,
    'btn_diagnostic': AMBER,
    'btn_health_center': GREEN,
    'btn_cleanup': CYAN,
    'btn_tweaks': PURPLE,
    'btn_network': CYAN,
    'btn_smart_alerts': RED,
    'btn_session_trends': GREEN,
    'btn_alert_history': AMBER,
}

def _sidebar_option_accent(attr):
    return SIDEBAR_OPTION_ACCENTS.get(attr, CYAN)


def _sidebar_line(button, color, active=False):
    if button is None:
        return None
    try:
        from gui.dashboard import _set_sidebar_option_line
        return _set_sidebar_option_line(button, color, active=active)
    except Exception:
        return None


def _set_resizing(app, active):
    """Punto único que marca is_resizing y, en el mismo gesto, activa/desactiva
    la guarda de redibujo CTk de esta ventana (V159). Al pasar a
    False, la guarda aplica de una sola vez los redibujos de widgets que
    quedaron pendientes durante el arrastre."""
    app.is_resizing = bool(active)
    try:
        from gui.resize_render_guard import set_active as _set_render_guard_active
        _set_render_guard_active(active, owner=app)
    except Exception:
        pass

def _cfg(w, **kw):
    if w is None:
        return
    try:
        configure_changed(w, **kw)
    except Exception:
        pass

def _text(w):
    try:
        return str(w.cget('text') or '').strip()
    except Exception:
        return ''

def _children(w):
    try:
        return list(w.winfo_children())
    except Exception:
        return []

def _desc(w):
    out = []
    stack = list(_children(w))
    while stack:
        n = stack.pop(0)
        out.append(n)
        stack.extend(_children(n))
    return out

def _cancel(app, attr):
    aid = getattr(app, attr, None)
    if aid:
        try:
            app.after_cancel(aid)
        except Exception:
            pass
    try:
        setattr(app, attr, None)
    except Exception:
        pass

def _style_sidebar(app):
    _cfg(app.sidebar, width=248, fg_color='transparent')
    try:
        app.sidebar.grid_propagate(False)
    except Exception:
        pass
    _cfg(getattr(app, 'lbl_brand', None), text='')
    _cfg(getattr(app, 'lbl_subtitle', None), text='')
    # V113: la esquina superior izquierda queda limpia; no se reinyecta branding.
    _cfg(getattr(app, '_sidebar_brand_title', None), text='')
    _cfg(getattr(app, '_sidebar_brand_company', None), text='')
    _cfg(getattr(app, '_sidebar_brand_rule', None), height=0)
    for attr, label in NAV.items():
        b = getattr(app, attr, None)
        if b is None:
            continue
        active = attr == '_btn_summary'
        _cfg(
            b,
            text=label,
            height=38,
            corner_radius=11,
            font=(FONT, 11, 'bold'),
            anchor='w',
            padx=16 if active else 14,
            text_color=TEXT if active else SIDEBAR_INACTIVE_TEXT,
            fg_color=role_color('accent_soft') if active else 'transparent',
            bg_color='transparent',
            hover_color=SIDEBAR_ACTIVE_HOVER if active else role_color('sidebar'),
            border_width=0,
            border_color=_sidebar_option_accent(attr),
        )
        _sidebar_line(b, _sidebar_option_accent(attr), active=active)
    _cfg(getattr(app, '_sidebar_version', None), text=f'{VERSION_LABEL} · Cereon Technologies', font=(FONT, 8), text_color=MUTED)
    # V131 — Personalización usa el mismo lenguaje contextual del resto del
    # sidebar: sin relleno hasta seleccionar Temas.
    _cfg(getattr(app, '_personalization_block', None), fg_color='transparent', border_width=0, corner_radius=0)
    _cfg(getattr(app, '_personalization_label', None), text_color=MUTED)
    _cfg(getattr(app, '_personalization_hint', None), text_color=MUTED)
    _cfg(getattr(app, '_personalization_divider', None), fg_color='transparent', height=0)
    for attr, label, accent in (
        ('_theme_toggle_button', 'Temas', PURPLE),
        ('_ai_button', 'CorePulse AI', GREEN),
    ):
        button = getattr(app, attr, None)
        _cfg(
            button, text=label, height=38, corner_radius=11,
            fg_color='transparent', bg_color='transparent', hover_color=role_color('sidebar'),
            border_width=0, border_color=accent,
            text_color=SIDEBAR_INACTIVE_TEXT, font=(FONT, 11, 'bold'),
            anchor='w', padx=14,
        )
        _sidebar_line(button, accent, active=False)


def _is_agent_container(w):
    titles = {'AGENTE COREPULSE', 'ESTADO DEL AGENTE'}
    return any((_text(n).upper() in titles for n in [w] + _desc(w)))

def _destroy_existing_agent_cards(app):
    for child in list(_children(getattr(app, 'sidebar', None))):
        if _is_agent_container(child):
            try:
                child.destroy()
            except Exception:
                pass

def _worker_alive(agent):
    if agent is None:
        return False
    for v in vars(agent).values():
        if isinstance(v, threading.Thread):
            try:
                if v.is_alive():
                    return True
            except Exception:
                pass
    for a in ('running', 'is_running', 'active'):
        try:
            v = getattr(agent, a)
            if isinstance(v, bool):
                return v
        except Exception:
            pass
    return False

def _agent_level(state):
    raw = str((state or {}).get('overall') or 'UNKNOWN').upper()
    return {'OK': 'NORMAL', 'OPTIMAL': 'NORMAL', 'OPTIMO': 'NORMAL', 'ÓPTIMO': 'NORMAL', 'WARN': 'WARNING', 'ADVERTENCIA': 'WARNING', 'CRITICO': 'CRITICAL', 'CRÍTICO': 'CRITICAL'}.get(raw, raw)

def _active_alerts(state):
    try:
        a = (state.get('alerts') or {}).get('active') or []
        return a if isinstance(a, list) else []
    except Exception:
        return []

def _primary_alert(state):
    a = _active_alerts(state)
    if not a:
        return None
    rank = {'CRITICAL': 3, 'WARNING': 2, 'INFO': 1}
    best = max(a, key=lambda x: rank.get(str((x or {}).get('level') or '').upper(), 0) if isinstance(x, dict) else -1)
    return str(best.get('title') or best.get('message') or '').strip() or None if isinstance(best, dict) else None

def _build_agent_card(app):
    """V227: el Estado del agente vive en el header, nunca en el sidebar."""
    _destroy_existing_agent_cards(app)
    header_card = getattr(app, '_header_agent_frame', None)
    try:
        valid = header_card is not None and header_card.winfo_exists()
    except Exception:
        valid = header_card is not None
    if valid:
        app._agent_card = header_card
        return header_card
    return None




def render_agent_card(app, state=None):
    """Renderiza solo el estado operativo del agente.

    V314: las alertas/condiciones pertenecen a Supervisión actual. Esta tarjeta
    informa únicamente si el agente está disponible, el modo y la frescura.
    """
    card = getattr(app, '_agent_card', None)
    try:
        invalid = card is None or not card.winfo_exists()
    except Exception:
        invalid = True
    if invalid:
        try:
            card = _build_agent_card(app)
        except Exception:
            return
        if card is None:
            return
    if state is None:
        try:
            state = app.realtime_agent.get_state()
        except Exception:
            state = {}
    if not isinstance(state, dict):
        state = {}

    alive = _worker_alive(getattr(app, 'realtime_agent', None))
    mode = str(state.get('mode') or state.get('context') or 'DESKTOP').upper()
    mode = {'DESKTOP': 'ESCRITORIO', 'GAME': 'JUEGO', 'GAME_ACTIVE': 'JUEGO'}.get(mode, mode)
    overall = str(state.get('overall') or 'UNKNOWN').upper()

    if alive and overall == 'UNKNOWN':
        status_text = 'Inicializando'
        state_text = 'Preparando monitoreo'
        detail_text = 'Validando fuentes y sensores'
        tone_color = AMBER
    elif alive:
        status_text = 'Monitoreo activo'
        state_text = 'Agente en ejecución'
        detail_text = 'Lecturas reales y trazables'
        tone_color = GREEN
    else:
        status_text = 'Monitoreo detenido'
        state_text = 'Agente no disponible'
        detail_text = 'Sin actualización en tiempo real'
        tone_color = RED

    _cfg(getattr(app, '_agent_title', None), text='ESTADO DEL AGENTE', text_color=TEXT_2)
    _cfg(getattr(app, '_agent_dot', None), text_color=tone_color)
    _cfg(getattr(app, '_agent_accent', None), fg_color=tone_color)
    _cfg(getattr(app, '_agent_status', None), text=status_text, text_color=tone_color)
    _cfg(getattr(app, '_agent_mode', None), text=mode.title(), text_color=MUTED)
    _cfg(getattr(app, '_agent_state', None), text=state_text, text_color=TEXT_2)
    _cfg(getattr(app, '_agent_detail', None), text=detail_text, text_color=MUTED)
    _cfg(getattr(app, '_agent_card', None), border_color=BORDER)




def _install_agent_route(app):
    app.agent_status_panel = None

    def ensure(self):
        if getattr(self, '_agent_card', None) is None:
            _build_agent_card(self)

    def refresh(self, state=None):
        if getattr(self, 'is_running', False):
            render_agent_card(self, state)
    app._ensure_agent_status_panel = types.MethodType(ensure, app)
    app._refresh_agent_status_panel = types.MethodType(refresh, app)



def _hide_storage_scrollbar_if_possible(app, disk_count):
    bar = getattr(getattr(app, 'scroll_disks', None), '_scrollbar', None)
    if bar is None:
        return
    try:
        if disk_count <= 1:
            bar.grid_remove()
        else:
            bar.grid()
    except Exception:
        pass

def _storage_height_for(app, mode):
    """Una fila de SSD visible; los demás se consultan desplazándose.

    No aumenta con el número de unidades. Así los gráficos mantienen el
    espacio que les corresponde en ventanas compactas o maximizadas.
    """
    count = len(getattr(app, 'disk_widgets', {}) or {})
    return 86 if count else (58 if mode == 'compact' else 64)


def _system_disk_sort_key(index, disk):
    """Mostrar primero el disco con la unidad de arranque de Windows."""
    mounts = str((disk or {}).get('mount_points') or '')
    system_drive = os.environ.get('SystemDrive', 'C:').strip().upper().rstrip('\\/')
    if not system_drive:
        system_drive = 'C:'
    # La letra puede aparecer como "C:", "C:", "C:; D:" o "C:".
    is_system = bool(re.search(r'(?<![A-Z0-9])' + re.escape(system_drive)
                               + r'(?=[\\/\s,;]|$)', mounts.upper()))
    try:
        order = int(index)
    except (ValueError, TypeError):
        order = 10**6
    return (0 if is_system else 1, order, str(index))


def _storage_card_bottom_padding(position, count):
    """Separación interna entre SSDs; nunca padding tras el último visible."""
    return 4 if position < count - 1 else 0


def _finalize_storage_viewport(app, mode=None):
    """Fija orden, scrollregion y posición tras cambios de topología.

    No modifica ningún dato de disco: sólo geometría/presentación.
    """
    if mode is None:
        mode = getattr(app, '_layout_mode', 'standard')
    host = getattr(app, 'scroll_disks', None)
    widgets_map = getattr(app, 'disk_widgets', {}) or {}
    if host is None:
        return

    # La partición de sistema siempre primero, incluso si Windows publica
    # su disco después de un USB. Reordenar sólo cuando cambia el inventario;
    # nunca repackear toda la lista en cada refresco de telemetría.
    latest = {d.get('index'): d for d in (getattr(app, 'latest_disks', None) or [])
              if isinstance(d, dict)}
    ordered = sorted(widgets_map, key=lambda idx: _system_disk_sort_key(idx, latest.get(idx)))
    signature = tuple(ordered)
    changed = signature != getattr(app, '_cp_storage_view_signature', None)
    if changed:
        for idx in ordered:
            card = (widgets_map.get(idx) or {}).get('card')
            if card is not None:
                try:
                    card.pack_forget()
                except Exception:
                    pass
        app._cp_storage_view_signature = signature
    for position, idx in enumerate(ordered):
        card = (widgets_map.get(idx) or {}).get('card')
        if card is None:
            continue
        try:
            card.pack_propagate(False)
            card.pack(fill='x', expand=False, padx=0,
                      pady=(0, _storage_card_bottom_padding(position, len(ordered))))
        except Exception:
            pass

    target_h = _storage_height_for(app, mode)
    _cfg(host, height=target_h)
    try:
        host.grid_propagate(False)
        host.pack_configure(fill='x', expand=False, pady=(0, 2 if mode == 'compact' else 3))
    except Exception:
        pass

    try:
        host.content.update_idletasks()
        host.update_idletasks()
    except Exception:
        pass

    count = len(widgets_map)
    _hide_storage_scrollbar_if_possible(app, count)
    # No devolver el scroll al inicio en cada lectura SMART: el usuario debe
    # poder permanecer mirando el segundo SSD mientras sigue la telemetría.
    if changed:
        try:
            host.yview_moveto(0.0)
        except Exception:
            pass

    # StableScrollHost ya expone esta autoridad. Repetimos una vez en idle y
    # una vez diferida porque Windows puede publicar la geometría del widget USB
    # uno o dos frames después de crearlo.
    schedule = getattr(host, '_schedule_geometry', None) or getattr(host, '_schedule_scrollregion', None)
    if callable(schedule):
        try:
            schedule(0)
            app.after_idle(lambda: schedule(0))
            app.after(70, lambda: schedule(0))
        except Exception:
            pass


def _sync_storage_height(app, mode=None):
    if mode is None:
        mode = getattr(app, '_layout_mode', 'standard')
    _finalize_storage_viewport(app, mode)


def _style_storage_widgets(app):
    _cfg(getattr(app, 'scroll_disks', None), fg_color='transparent')
    ordered_disks = sorted((getattr(app, 'disk_widgets', {}) or {}).items())
    for position, (_idx, widgets) in enumerate(ordered_disks):
        card = widgets.get('card')
        name = widgets.get('lbl_name')
        badge = widgets.get('lbl_badge')
        exact = widgets.get('lbl_exact')
        bar = widgets.get('bar')
        try:
            card.pack_propagate(False)
        except Exception:
            pass
        _cfg(card, border_color=SURFACE, border_width=0, corner_radius=16, height=86)
        try:
            from gui.dashboard import _ensure_storage_card_decor
            _ensure_storage_card_decor(card, widgets)
        except Exception:
            pass
        try:
            card.pack_configure(
                fill='x', expand=False, padx=0,
                pady=(0, _storage_card_bottom_padding(position, len(ordered_disks))),
            )
        except Exception:
            pass
        if name is not None:
            cur = _text(name)
            for prefix in ('💾 ', '▰  ', '▰ '):
                while cur.startswith(prefix):
                    cur = cur[len(prefix):].strip()
            _cfg(name, text=cur, font=(FONT, 10, 'bold'), text_color=TEXT, anchor='w')
        _cfg(badge, font=(FONT, 9, 'bold'))
        _cfg(exact, font=(FONT, 9), text_color=CYAN, anchor='w', justify='left')
        _cfg(bar, height=6, fg_color=TRACK, progress_color=CYAN)
    _sync_storage_height(app)

def _install_storage_route(app):
    if getattr(app, '_storage_layout_wrapped', False):
        return
    original = app.update_disks_ui

    def update(self, disks_data):
        original(disks_data)
        _style_storage_widgets(self)
        _sync_storage_height(self)
        # Los SSD aparecen dinámicamente: aplicar el mismo acabado al crearse.
        try:
            from gui.glass_cards import install_glass_cards
            install_glass_cards(self)
        except (ImportError, AttributeError):
            pass
    app.update_disks_ui = types.MethodType(update, app)
    app._storage_layout_wrapped = True
    app._sync_storage_height_callback = types.MethodType(lambda self: _sync_storage_height(self), app)
    _style_storage_widgets(app)

def _style_hardware(app):
    specs = (
        (app.card_cpu, app.lbl_cpu_title, app.lbl_cpu, app.lbl_cpu_temp, app.bar_cpu, CYAN),
        (app.card_ram, app.lbl_ram_title, app.lbl_ram, app.lbl_ram_gb, app.bar_ram, GREEN),
        (app.card_gpu, app.lbl_gpu_title, app.lbl_gpu, app.lbl_gpu_temp, app.bar_gpu, PURPLE),
    )
    for card, title, value, detail, bar, accent in specs:
        _cfg(card, border_color=SURFACE, border_width=0, corner_radius=16, height=134)
        try:
            card.pack_propagate(False)
        except Exception:
            pass
        _cfg(title, font=(FONT, 9, 'bold'), text_color=TEXT, anchor='w', justify='left')
        _cfg(value, font=(FONT, 28, 'bold'), text_color=TEXT, anchor='w')
        _cfg(detail, font=(FONT, 9, 'bold'), text_color=accent, anchor='w', justify='left')
        _cfg(bar, height=6, progress_color=accent, fg_color=TRACK)
        try:
            from gui.dashboard import _ensure_soft_card_accent
            _ensure_soft_card_accent(card, accent, placement='left')
        except Exception:
            pass
    try:
        app.card_cpu.pack_configure(side='left', expand=True, fill='both', padx=(0, 6))
        app.card_ram.pack_configure(side='left', expand=True, fill='both', padx=6)
        app.card_gpu.pack_configure(side='left', expand=True, fill='both', padx=(6, 0))
    except Exception:
        pass


def _layout_mode(w, h):
    if w < 1360 or h < 820:
        return 'compact'
    if w < 1600 or h < 930:
        return 'standard'
    return 'large'


def _is_expanded_window(app, width=None, height=None):
    """Detecta fullscreen real o una ventana maximizada que debe aprovechar más espacio."""
    if getattr(app, 'is_fullscreen', False):
        return True
    try:
        if str(app.state()).lower() == 'zoomed':
            return True
    except Exception:
        pass
    try:
        width = int(width if width is not None else app.winfo_width())
        height = int(height if height is not None else app.winfo_height())
        screen_w = int(app.winfo_screenwidth())
        screen_h = int(app.winfo_screenheight())
        return width >= max(1200, screen_w - 48) and height >= max(720, screen_h - 92)
    except Exception:
        return False

def _sidebar_section_labels(app):
    wanted = {'MONITOREO', 'DIAGNÓSTICO', 'MANTENIMIENTO', 'HISTORIAL'}
    out = []
    for child in _children(getattr(app, 'sidebar', None)):
        if _text(child).upper() in wanted:
            out.append(child)
    return out

def _style_sidebar_mode(app, mode):
    compact = mode == 'compact'
    standard = mode == 'standard'
    try:
        viewport_h = int(app.winfo_height())
    except Exception:
        viewport_h = 900
    # V300: el ancho de la ventana no debe convertir Personalización en un
    # footer flotante. En otros PCs (p. ej. 1280 px de ancho / escalado DPI)
    # `mode == 'compact'` se activaba aunque hubiera altura suficiente y dejaba
    # un hueco enorme bajo Historial. El modo ajustado depende SOLO de la altura
    # real disponible; además el bloque siempre conserva el flujo del menú.
    personalization_tight = viewport_h < 690
    # V131: el lateral conserva una anchura mínima legible incluso en modo compacto.
    collapsed = False
    width = 242 if compact else 248 if standard else 254
    _cfg(app.sidebar, width=width, fg_color='transparent', border_width=0, corner_radius=0)
    try:
        # V383: en fullscreen real el lateral baja unos píxeles para conservar
        # el mismo aire visual que el contenido principal. En ventana normal
        # mantiene exactamente la posición aprobada de V382.
        sidebar_top_pad = 32 if getattr(app, 'is_fullscreen', False) else 14
        if not getattr(app, '_sidebar_collapsed', False):
            app.sidebar.grid_configure(sticky='new', padx=(12, 0), pady=(sidebar_top_pad, 0))
    except Exception:
        pass
    try:
        border = getattr(app, '_sidebar_native_border', None)
        border_lines = border if isinstance(border, (tuple, list)) else ((border,) if border is not None else ())
        for line in border_lines:
            if line is not None and line.winfo_exists():
                line.configure(bg=BORDER)
                line.lift()
    except Exception:
        pass

    # El logotipo gráfico grande no vuelve al lateral; sólo queda la identidad
    # tipográfica compacta creada por dashboard.py.
    try:
        app.frame_logo.pack_forget()
    except Exception:
        pass
    _cfg(getattr(app, 'lbl_brand', None), text='')
    _cfg(getattr(app, 'lbl_subtitle', None), text='')

    brand = getattr(app, '_sidebar_brand_block', None)
    if brand is not None:
        _cfg(brand, height=43 if compact else 48)
        try:
            brand.pack_configure(fill='x', padx=13 if compact else 16, pady=(7 if compact else 10, 3 if compact else 4))
        except Exception:
            pass
    _cfg(getattr(app, '_sidebar_brand_title', None), font=(FONT, 13 if compact else 15, 'bold'), height=20 if compact else 23)
    _cfg(getattr(app, '_sidebar_brand_company', None), font=(FONT, 6 if compact else 7, 'bold'), height=13 if compact else 15)
    rule = getattr(app, '_sidebar_brand_rule', None)
    try:
        if rule is not None:
            rule.pack_configure(fill='x', padx=13 if compact else 16, pady=(0, 5 if compact else 7))
    except Exception:
        pass

    has_brand_block = getattr(app, '_sidebar_brand_block', None) is not None
    for label in _sidebar_section_labels(app):
        try:
            name = _text(label).upper()
            if name == 'MONITOREO':
                # Al retirar el branding superior, conservamos el aire visual que
                # antes aportaba ese bloque. No cambia el ancho ni la navegación.
                top_gap = 4 if compact else 6 if standard else 8
                if has_brand_block:
                    top_gap = 0
            else:
                top_gap = 3 if compact else 5
            label.pack_configure(padx=17, pady=(top_gap, 2 if compact else 3))
        except Exception:
            pass
        _cfg(label, height=15 if compact else 17, font=(FONT, 8 if compact else 9, 'bold'))

    context_button = {
        'dashboard': '_btn_summary',
        'gaming': 'btn_health_center',
        'overlay': 'btn_health_center',
        'diagnostic': 'btn_diagnostic',
        'health_center': 'btn_health_center',
        'cleanup': 'btn_cleanup',
        'tweaks': 'btn_tweaks',
        'network': 'btn_network',
        'alerts': 'btn_smart_alerts',
        'trends': 'btn_session_trends',
        'history': 'btn_alert_history',
        'themes': '_theme_toggle_button',
        'ai': '_ai_button',
    }
    active_attr = context_button.get(str(getattr(app, '_navigation_context', 'dashboard')).lower(), '_btn_summary')
    for attr in NAV:
        b = getattr(app, attr, None)
        if b is None:
            continue
        active = attr == active_attr
        _cfg(
            b,
            height=40 if collapsed else 34 if compact else 36 if standard else 38,
            width=44 if collapsed else 0,
            font=(FONT, 10, 'bold'),
            corner_radius=11 if collapsed else 10,
            padx=(14 if compact else 17) if active else (12 if compact else 15),
            text_color=TEXT if active else SIDEBAR_INACTIVE_TEXT,
            fg_color=role_color('accent_soft') if active else 'transparent',
            bg_color='transparent',
            hover_color=SIDEBAR_ACTIVE_HOVER if active else role_color('sidebar'),
            border_width=0,
            border_color=_sidebar_option_accent(attr),
            anchor='w',
        )
        try:
            from gui.dashboard import _set_nav_selection_indicator
            _set_nav_selection_indicator(b, False)
        except Exception:
            pass
        _sidebar_line(b, _sidebar_option_accent(attr), active=active)
        try:
            b.pack_configure(fill='none' if collapsed else 'x', padx=10 if collapsed else 11 if compact else 12, pady=1, anchor='center' if collapsed else 'w')
        except Exception:
            pass

    # V227: no existe tarjeta de agente en el sidebar. El bloque real vive en el header.
    legacy_agent = getattr(app, '_agent_card', None)
    if legacy_agent is not None and legacy_agent is not getattr(app, '_header_agent_frame', None):
        try:
            legacy_agent.pack_forget()
        except Exception:
            pass

    # Personalización conserva Temas y recorta metadatos secundarios cuando el alto es limitado.
    personal = getattr(app, '_personalization_block', None)
    _cfg(personal, fg_color='transparent', border_width=0, corner_radius=0)
    try:
        pdiv = getattr(app, '_personalization_top_divider', None)
        if pdiv is not None and pdiv.winfo_exists():
            pdiv.configure(bg=BORDER, height=1)
    except Exception:
        pass
    _cfg(getattr(app, '_personalization_label', None), height=16, font=(FONT, 8 if compact else 9, 'bold'), text_color=MUTED)
    _cfg(getattr(app, '_personalization_hint', None), height=13, font=(FONT, 8), text_color=MUTED)
    _cfg(getattr(app, '_personalization_divider', None), fg_color='transparent', height=0)

    context = str(getattr(app, '_navigation_context', '') or '').lower()
    for attr, label, key, accent in (
        ('_theme_toggle_button', 'Temas', 'themes', PURPLE),
        ('_ai_button', 'CorePulse AI', 'ai', GREEN),
    ):
        button = getattr(app, attr, None)
        active = context == key
        _cfg(
            button,
            text=label,
            height=36 if personalization_tight else 38,
            corner_radius=11,
            fg_color=role_color('accent_soft') if active else 'transparent',
            bg_color='transparent',
            hover_color=SIDEBAR_ACTIVE_HOVER if active else role_color('sidebar'),
            border_width=0,
            border_color=accent,
            text_color=TEXT if active else SIDEBAR_INACTIVE_TEXT,
            font=(FONT, 10 if compact else 11, 'bold'),
            anchor='w',
            padx=13 if compact else 14,
        )
        _sidebar_line(button, accent, active=active)

    hint = getattr(app, '_personalization_hint', None)
    divider = getattr(app, '_personalization_divider', None)
    ver = getattr(app, '_sidebar_version', None)
    _cfg(ver, text=f'{VERSION_LABEL} · Cereon Technologies', font=(FONT, 8), text_color=MUTED)
    try:
        if personalization_tight:
            # Prioridad: Temas + CorePulse AI siempre visibles. El subtítulo y
            # divisor permanecen retirados; la versión se conserva si cabe en el
            # footer compacto.
            if hint is not None:
                hint.pack_forget()
            if divider is not None:
                divider.pack_forget()
            if ver is not None and not ver.winfo_manager():
                ver.pack(fill='x', padx=17, pady=(0, 0))
        else:
            theme_button = getattr(app, '_theme_toggle_button', None)
            # V256: subtítulo de Personalización eliminado por diseño.
            # No volver a insertarlo durante cambios de tamaño/layout.
            if hint is not None and hint.winfo_manager():
                hint.pack_forget()
            if divider is not None and divider.winfo_manager():
                divider.pack_forget()
            if ver is not None and not ver.winfo_manager():
                ver.pack(fill='x', padx=17, pady=(0, 0))
        if personal is not None:
            # V300: Personalización forma parte del flujo del sidebar en TODAS
            # las resoluciones. Nunca se ancla al borde inferior: eso hacía que
            # un cambio de ancho/DPI generara el hueco visual visto en otros PCs.
            # En alturas muy bajas solo compactamos paddings/controles.
            personal.pack_configure(
                side='top',
                fill='x',
                padx=0,
                pady=((1, 0) if personalization_tight else (3, 0)),
                after=getattr(app, 'btn_alert_history', None),
            )
    except Exception:
        pass
    try:
        # V360: tras cualquier cambio responsive/fullscreen, el borde se vuelve
        # a fijar al perímetro real del sidebar (incluido el cierre inferior).
        from gui.dashboard import _sync_sidebar_native_border_to_content
        app.after_idle(lambda: _sync_sidebar_native_border_to_content(app))
    except Exception:
        pass
    # Después de los cambios responsivos, sincronizar la pintura nativa de
    # los controles; los botones conservan su fg/selección y los comandos.
    try:
        controller = getattr(app, 'workspace_background', None)
        if controller is not None:
            controller.schedule_refresh()
    except Exception:
        pass


def _style_header_mode(app, mode):
    compact = mode == 'compact'
    header = getattr(app, '_header', None)
    try:
        # V428: eliminar el falso 'sobreborde' que era espacio adicional
        # bajo el encabezado; conservar suficiente alto para el estado AI.
        header.pack_configure(fill='x', pady=(0, 2))
        _cfg(header, height=96)
    except Exception:
        pass
    # La identidad del equipo tiene una autoridad visual explícita.
    # Antes este bloque tomaba el primer Label del header por posición y lo
    # trataba como el antiguo título, sobrescribiendo el modelo a 23/26/28 px.
    # Eso hacía inútiles los tamaños definidos en dashboard.py.
    identity = getattr(app, '_header_identity', None)
    try:
        if identity is not None:
            left_pad = 10 if compact else 16 if mode == 'standard' else 18
            identity.pack_configure(padx=(left_pad, 18))
    except Exception:
        pass
    brand = getattr(app, '_header_brand_icon', None)
    try:
        if brand is not None:
            brand.pack_configure(padx=(4, 14), pady=(6 if compact else 7, 4))
    except Exception:
        pass

    _cfg(
        getattr(app, '_header_device_model', None),
        font=(FONT, 14 if compact else 15 if mode == 'standard' else 17, 'bold'),
        text_color=TEXT,
        anchor='w',
        justify='left',
        wraplength=390 if compact else 520 if mode == 'standard' else 650,
    )
    _cfg(
        getattr(app, '_header_brand_icon', None),
        width=46,
        height=46,
    )
    _cfg(getattr(app, '_header_eyebrow', None), font=(FONT, 7 if compact else 8, 'bold'), text_color=CYAN)
    _cfg(getattr(app, '_header_subtitle', None), font=(FONT, 8 if compact else 9), wraplength=420 if compact else 540 if mode == 'standard' else 660)
    _cfg(getattr(app, '_header_meta_hint', None), font=(FONT, 7 if compact else 8), wraplength=220 if compact else 260)
    for attr in ('_header_chip_live', '_header_chip_data', '_header_chip_focus'):
        _cfg(getattr(app, attr, None), font=(FONT, 7 if compact else 8, 'bold'))
    _cfg(getattr(app, '_header_ai_text', None), font=(FONT, 12 if compact else 14, 'bold'), wraplength=240 if compact else 300)
    _cfg(getattr(app, '_header_ai_hint', None), font=(FONT, 7 if compact else 8))
    _cfg(getattr(app, '_header_last_update', None), font=(FONT, 6 if compact else 7), wraplength=78 if compact else 84)
    _cfg(getattr(app, '_ai_title', None), font=(FONT, 7 if compact else 8, 'bold'))
    _cfg(getattr(app, '_ai_badge', None), font=(FONT, 6 if compact else 7, 'bold'))
    # La etiqueta de IA comparte el mismo control que _header_ai_text;
    # evitar que el estilo antiguo de 9/10 pt anule su tamaño centrado.
    _cfg(getattr(app, '_ai_mode', None), font=(FONT, 6 if compact else 7, 'bold'))
    _cfg(getattr(app, '_ai_state', None), font=(FONT, 7 if compact else 8, 'bold'))
    _cfg(getattr(app, '_ai_detail', None), font=(FONT, 6 if compact else 7), wraplength=270)
    # La referencia no muestra el botón de tamaño en el encabezado.
    size_button = getattr(app, '_size_button', None)
    try:
        if size_button:
            size_button.pack_forget()
    except Exception:
        pass


def _style_status_band(app):
    """V427: misma autoridad visual que las tarjetas construidas en dashboard.

    V426 había quitado el borde al CREAR estas tarjetas, pero esta función
    lo volvía a poner al aplicar la arquitectura; por eso persistía el
    sobrecontorno. Mantener el borde a cero en todos los reestilizados.
    """
    band = getattr(app, '_status_band', None)
    if band is None:
        return
    _cfg(band, fg_color='transparent', border_width=0, corner_radius=0)
    for card in getattr(app, '_status_cards', ()):
        _cfg(card, border_color=SURFACE, border_width=0, corner_radius=16)
        # V434: conservar un solo tono incluso después de cambiar de tema.
        # La tarjeta Salud tiene widgets Tk/CTk internos que de otra manera
        # pueden conservar fondos anteriores y parecer un marco interior.
        for name in ('_cp_health_shell', '_cp_health_body',
                     '_cp_health_metrics_row', '_cp_health_status_strip'):
            _cfg(getattr(card, name, None), fg_color=SURFACE, corner_radius=0)
        for widget in getattr(card, '_cp_health_background_labels', ()):
            _cfg(widget, bg_color=SURFACE)


def _style_status_mode(app, mode):
    band = getattr(app, '_status_band', None)
    if band is None:
        return
    compact = mode == 'compact'
    standard = mode == 'standard'
    height = 104 if compact else 118 if standard else 124
    _cfg(band, height=height)
    try:
        band.pack_configure(fill='x', pady=(0, 5 if compact else 8))
    except Exception:
        pass

    for card in getattr(app, '_status_cards', ()):
        # El reflow responsivo tampoco puede resucitar bordes eliminados.
        _cfg(card, height=height, corner_radius=11 if compact else 12,
             border_width=0, border_color=SURFACE)

    icon_size = 34 if compact else 38 if standard else 42
    icon_font = 14 if compact else 16 if standard else 18
    for attr in ('_health_icon', '_alert_icon', '_coverage_icon', '_uptime_icon'):
        _cfg(getattr(app, attr, None), width=icon_size, height=icon_size, corner_radius=icon_size // 2, font=(ICON_FONT, icon_font, 'bold'))

    _cfg(
        getattr(app, '_health_status', None),
        font=(FONT, 12 if compact else 14 if standard else 15, 'bold'),
        wraplength=150 if compact else 175 if standard else 195,
        justify='left',
        anchor='w',
    )
    _cfg(getattr(app, '_health_score', None), font=(FONT, 7 if compact else 8))
    _cfg(
        getattr(app, '_alert_value', None),
        font=(FONT, 11 if compact else 12 if standard else 14, 'bold'),
        wraplength=142 if compact else 168 if standard else 190,
        justify='left',
        anchor='w',
    )
    for attr in ('_coverage_value', '_uptime_value'):
        _cfg(getattr(app, attr, None), font=(FONT, 12 if compact else 14 if standard else 16, 'bold'))
    for attr in ('_alert_detail', '_coverage_detail', '_uptime_detail'):
        _cfg(getattr(app, attr, None), font=(FONT, 7 if compact else 8), wraplength=145 if compact else 172 if standard else 195, justify='left', anchor='w')


def _chart_tick_positions(total_points):
    total = max(2, int(total_points or 0))
    last = total - 1
    positions = [1, round(last * 0.28), round(last * 0.56), round(last * 0.80), last]
    deduped = []
    for value in positions:
        value = max(0, min(last, int(value)))
        if value not in deduped:
            deduped.append(value)
    while len(deduped) < 5:
        deduped.append(last)
    return deduped[:5]


def _chart_target_height_for(app, mode):
    """Reserva una porción visible del Dashboard a las tendencias.

    V382 aprovecha mejor fullscreen/maximizado: en ventana expandida la tarjeta
    de tendencias absorbe más alto útil para que el Dashboard no quede pequeño
    dentro de monitores grandes o al pulsar F11.
    """
    try:
        width = int(app.winfo_width())
        height = int(app.winfo_height())
    except Exception:
        width, height = (1280, 800)
    expanded = _is_expanded_window(app, width, height)
    ratio = 0.31 if mode == 'compact' else 0.39 if mode == 'standard' else 0.41
    minimum = 236 if mode == 'compact' else 338 if mode == 'standard' else 360
    maximum = 310 if mode == 'compact' else 420 if mode == 'standard' else 468
    if expanded:
        ratio += 0.03 if mode == 'compact' else 0.05 if mode == 'standard' else 0.06
        minimum += 18 if mode == 'compact' else 26 if mode == 'standard' else 34
        maximum += 42 if mode == 'compact' else 58 if mode == 'standard' else 72
    target = int(height * ratio)
    if width >= 1700:
        target += 12
    if expanded and width >= 1900:
        target += 10
    return max(minimum, min(target, maximum))



def _style_charts(app):
    _cfg(app.frame_charts, fg_color='transparent', border_width=0, corner_radius=0)
    try:
        max_points = max(2, int(getattr(app, 'max_points', 25) or 25))
        ticks = _chart_tick_positions(max_points)
        labels = ['-60s', '-45s', '-30s', '-15s', 'Ahora']
        app.fig.set_frameon(True)
        app.fig.set_facecolor(SURFACE)
        axes = (app.ax_cpu, app.ax_ram, app.ax_gpu)
        for ax in axes:
            ax.set_facecolor('none')  # V444: la imagen de la capa maestra se ve bajo el eje
            ax.tick_params(axis='x', colors=MUTED, labelsize=8, length=0, pad=6)
            ax.tick_params(axis='y', colors=MUTED, labelsize=8, length=0, pad=6, labelleft=True)
            ax.grid(False)
            ax.yaxis.grid(True, color=BORDER_SOFT, linestyle='-', linewidth=0.55, alpha=0.74)
            ax.set_axisbelow(True)
            ax.set_yticks([25, 50, 75, 100])
            ax.set_xticks(ticks)
            ax.set_xticklabels(labels)
            ax.set_ylim(0, 100)
            ax.set_xlim(0, max_points - 1)
            ax.margins(x=0.02, y=0.10)
            ax.title.set_color(TEXT_2)
            ax.title.set_fontsize(9)
            ax.title.set_fontweight('bold')
            for spine in ax.spines.values():
                spine.set_visible(False)  # V444: sin contornos incluso tras redimensionar
        try:
            app.fig.patch.set_facecolor(SURFACE)
            app.fig.patch.set_edgecolor('none')
            app.fig.patch.set_linewidth(0.0)
        except Exception:
            pass
        try:
            canvas_widget = app.canvas.get_tk_widget()
            canvas_widget.configure(bg=SURFACE, highlightthickness=0, bd=0, relief='flat')
        except Exception:
            pass
        app.fig.subplots_adjust(left=0.052, right=0.985, top=0.84, bottom=0.20, wspace=0.18)
        try:
            from gui.chart_workspace_surface import sync_chart_workspace_surface
            sync_chart_workspace_surface(app)
        except Exception:
            pass
        app.background = None
    except Exception:
        pass



def _aligned_plot_rectangles(metric_rects, canvas_left, canvas_width, *, tick_gutter=58,
                             shift_left_px=20):
    """Alinea los tres gráficos con las columnas de recursos.

    V445: mueve el área de trazado completa 20 píxeles a la izquierda,
    incluyendo ejes, etiquetas y títulos, sin cambiar su ancho ni las curvas.
    Se calcula en píxeles de pantalla para que el ajuste sea igual en las tres
    columnas y se conserve al maximizar o cambiar el tamaño de la ventana.
    """
    if len(metric_rects) != 3 or canvas_width < 300:
        return ()
    rectangles = []
    for card_left, card_width in metric_rects:
        if card_width < 170:
            return ()
        left = (card_left - canvas_left + tick_gutter - shift_left_px) / canvas_width
        right = (card_left + card_width - canvas_left - 9 - shift_left_px) / canvas_width
        if left < .01 or right > .997 or right - left < .07:
            return ()
        rectangles.append((left, right - left))
    if any(rectangles[i][0] + rectangles[i][1] >= rectangles[i+1][0]
           for i in range(2)):
        return ()
    return tuple(rectangles)


def _align_charts_to_metric_cards(app):
    """Usa geometría real, no tercios independientes de Matplotlib."""
    try:
        canvas_widget = app.canvas.get_tk_widget()
        cards = (app.card_cpu, app.card_ram, app.card_gpu)
        axes = (app.ax_cpu, app.ax_ram, app.ax_gpu)
        if not canvas_widget.winfo_ismapped() or not all(card.winfo_ismapped() for card in cards):
            return False
        widget_width = max(1.0, float(canvas_widget.winfo_width()))
        left_px = int(canvas_widget.winfo_rootx())
        metrics = [(card.winfo_rootx(), card.winfo_width()) for card in cards]
        positions = _aligned_plot_rectangles(metrics, left_px, widget_width)
        if not positions:
            return False
        for ax, (x, w) in zip(axes, positions):
            ax.set_position((x, 0.20, w, 0.64))
        return True
    except (AttributeError, TypeError, ValueError, RuntimeError):
        return False


def _sync_chart_figure_geometry(app, mode):
    """Sincroniza Matplotlib con la tarjeta usando el alto realmente útil."""
    frame = getattr(app, 'frame_charts', None)
    fig = getattr(app, 'fig', None)
    canvas = getattr(app, 'canvas', None)
    if frame is None or fig is None or canvas is None:
        return
    try:
        app.update_idletasks()
        width = max(760, int(frame.winfo_width()) - 16)
        min_plot_h = 226 if mode == 'compact' else 258 if mode == 'standard' else 286
        inner_h = int(frame.winfo_height()) - 20
        height = max(min_plot_h, inner_h)
        dpi = float(fig.get_dpi() or 96.0)
        fig.set_size_inches(width / dpi, height / dpi, forward=True)
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.pack_configure(
            side='top',
            fill='both',
            expand=True,
            padx=12 if mode == 'compact' else 14,
            pady=(8, 10),
        )
        try:
            canvas_widget.configure(height=height, bg=SURFACE, highlightthickness=0, bd=0, relief='flat')
        except Exception:
            pass
        try:
            fig.patch.set_facecolor(SURFACE)
            fig.patch.set_edgecolor('none')
            fig.patch.set_linewidth(0.0)
        except Exception:
            pass
        fig.subplots_adjust(left=0.052, right=0.985, top=0.84, bottom=0.20, wspace=0.18)
        _align_charts_to_metric_cards(app)
        try:
            from gui.chart_workspace_surface import sync_chart_workspace_surface
            sync_chart_workspace_surface(app)
        except Exception:
            pass
        app.background = None
    except Exception:
        pass


def _style_charts_mode(app, mode, mode_changed=False):
    # V104/V382: la tarjeta adopta una altura mínima más generosa y, cuando la
    # ventana está maximizada o en fullscreen, usa el espacio libre restante en
    # vez de quedarse con una huella de ventana normal.
    target_h = _chart_target_height_for(app, mode)
    _cfg(app.frame_charts, height=target_h)
    expanded = _is_expanded_window(app)
    try:
        app.frame_charts.pack_propagate(False)
        app.frame_charts.pack_configure(
            fill='both' if expanded else 'x',
            expand=bool(expanded),
            pady=(5 if mode == 'compact' else 6, 0),
        )
        _sync_chart_figure_geometry(app, mode)
        if mode_changed:
            app.background = None
            app.canvas.draw_idle()
    except Exception:
        pass


def _apply_layout(app, *, force=False):
    """Aplica layout sin reconfigurar todo el árbol en cada cambio de tamaño.

    El estilo completo sólo se recalcula cuando cambia el breakpoint responsive
    (compact/standard/large) o cuando se pide explícitamente. Si el usuario sólo
    estira la ventana dentro del mismo breakpoint, V111 conserva fuentes, cards,
    sidebar y posiciones; únicamente sincroniza alturas dependientes del viewport
    y la figura de tendencias. Esto elimina el reflow visual destructivo.
    """
    if not getattr(app, 'is_running', False):
        return
    try:
        w, h = (int(app.winfo_width()), int(app.winfo_height()))
    except Exception:
        return
    if w < 500 or h < 400:
        return

    mode = _layout_mode(w, h)
    if _is_expanded_window(app, w, h) and mode == 'standard':
        # V382: en fullscreen o maximizado, 1600x900 y resoluciones similares
        # deben lucir como layout grande aunque la altura física sea < 930 px.
        mode = 'large'
    previous = getattr(app, '_layout_mode', None)
    mode_changed = mode != previous
    app._layout_mode = mode

    if (not force) and (not mode_changed):
        # Fast path: no fuentes, grids, packs ni tarjetas se reconstruyen.
        if not getattr(app, '_active_internal_page', None):
            _sync_storage_height(app, mode)
            _style_charts_mode(app, mode, mode_changed=False)
        try:
            from gui.dashboard import request_native_card_surface_sync
            request_native_card_surface_sync(app)
        except Exception:
            pass
        app.background = None
        return

    _style_sidebar_mode(app, mode)
    _style_header_mode(app, mode)
    try:
        # V414: cerrar el hueco visible a la derecha del sidebar sin tocar su
        # ancho ni la alineación inferior con la fila de gráficos.
        app.main_content.grid_configure(
            padx=(7 if mode == 'compact' else 9 if mode == 'standard' else 10,
                  12 if mode == 'compact' else 16 if mode == 'standard' else 18),
            pady=9 if mode == 'compact' else 12 if mode == 'standard' else 14,
        )
    except Exception:
        pass

    _style_status_mode(app, mode)

    meter_h = 108 if mode == 'compact' else 122 if mode == 'standard' else 130
    for card in (app.card_cpu, app.card_ram, app.card_gpu):
        _cfg(card, height=meter_h)
    try:
        app.frame_meters.pack_configure(fill='x', pady=(0, 5 if mode == 'compact' else 8))
    except Exception:
        pass

    font_value = 23 if mode == 'compact' else 26 if mode == 'standard' else 28
    font_detail = 8 if mode == 'compact' else 9
    for value in (app.lbl_cpu, app.lbl_ram, app.lbl_gpu):
        _cfg(value, font=(FONT, font_value, 'bold'))
    for detail in (app.lbl_cpu_temp, app.lbl_ram_gb, app.lbl_gpu_temp):
        _cfg(detail, font=(FONT, font_detail, 'bold'))
    for title in (app.lbl_cpu_title, app.lbl_ram_title, app.lbl_gpu_title):
        _cfg(title, font=(FONT, 8 if mode == 'compact' else 9, 'bold'))

    _style_storage_widgets(app)
    _sync_storage_height(app, mode)
    _style_charts_mode(app, mode, mode_changed=mode_changed)
    try:
        from gui.dashboard import request_native_card_surface_sync
        request_native_card_surface_sync(app)
    except Exception:
        pass
    app.background = None


def request_stable_layout_sync(app, force=False):
    """Sincroniza la geometría visible una sola vez fuera del gesto de resize."""
    if getattr(app, '_layout_transition', False) or getattr(app, 'is_resizing', False):
        return
    try:
        _apply_layout(app, force=bool(force))
    except Exception:
        pass


def _finish(app):
    app._layout_transition = False
    _set_resizing(app, False)
    _apply_layout(app, force=True)

def _native_toplevel_hwnd(app):
    """Devuelve el HWND decorado real de la ventana Tk cuando se ejecuta en Windows."""
    if not sys.platform.startswith('win'):
        return None
    try:
        client = int(app.winfo_id())
        parent = int(ctypes.windll.user32.GetParent(client) or 0)
        return parent or client
    except Exception:
        return None


def _current_monitor_bounds(app):
    """Devuelve el rectángulo del monitor que contiene la ventana actual.

    V391: Tk puede aceptar ``-fullscreen`` pero limitarse a mover la ventana a
    (0, 0) sin expandirla en algunas combinaciones de Windows 11 + CTk.
    Esta función obtiene límites reales del monitor para reafirmar el tamaño.
    """
    if sys.platform.startswith('win'):
        hwnd = _native_toplevel_hwnd(app)
        if hwnd:
            try:
                class RECT(ctypes.Structure):
                    _fields_ = [
                        ('left', ctypes.c_long), ('top', ctypes.c_long),
                        ('right', ctypes.c_long), ('bottom', ctypes.c_long),
                    ]

                class MONITORINFO(ctypes.Structure):
                    _fields_ = [
                        ('cbSize', ctypes.c_ulong),
                        ('rcMonitor', RECT),
                        ('rcWork', RECT),
                        ('dwFlags', ctypes.c_ulong),
                    ]

                monitor = ctypes.windll.user32.MonitorFromWindow(hwnd, 2)  # MONITOR_DEFAULTTONEAREST
                if monitor:
                    info = MONITORINFO()
                    info.cbSize = ctypes.sizeof(MONITORINFO)
                    if ctypes.windll.user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
                        rect = info.rcMonitor
                        width = int(rect.right - rect.left)
                        height = int(rect.bottom - rect.top)
                        if width > 0 and height > 0:
                            return int(rect.left), int(rect.top), width, height
            except Exception:
                pass
    try:
        return 0, 0, int(app.winfo_screenwidth()), int(app.winfo_screenheight())
    except Exception:
        return 0, 0, 0, 0


def _force_fullscreen_bounds(app, bounds=None):
    """Reafirma el rectángulo fullscreen sin tocar el snapshot de restauración."""
    try:
        left, top, width, height = bounds or _current_monitor_bounds(app)
        if width <= 0 or height <= 0:
            return False
        app.geometry(f'{width}x{height}+{left}+{top}')
        app.update_idletasks()
        return True
    except Exception:
        return False


def _capture_native_window_placement(app):
    """Captura WINDOWPLACEMENT antes de F11 para que Windows restaure su rectángulo real."""
    hwnd = _native_toplevel_hwnd(app)
    if not hwnd:
        return None
    try:
        class POINT(ctypes.Structure):
            _fields_ = [('x', ctypes.c_long), ('y', ctypes.c_long)]

        class RECT(ctypes.Structure):
            _fields_ = [
                ('left', ctypes.c_long), ('top', ctypes.c_long),
                ('right', ctypes.c_long), ('bottom', ctypes.c_long),
            ]

        class WINDOWPLACEMENT(ctypes.Structure):
            _fields_ = [
                ('length', ctypes.c_uint),
                ('flags', ctypes.c_uint),
                ('showCmd', ctypes.c_uint),
                ('ptMinPosition', POINT),
                ('ptMaxPosition', POINT),
                ('rcNormalPosition', RECT),
            ]

        placement = WINDOWPLACEMENT()
        placement.length = ctypes.sizeof(WINDOWPLACEMENT)
        if not ctypes.windll.user32.GetWindowPlacement(hwnd, ctypes.byref(placement)):
            return None

        rect = placement.rcNormalPosition
        return {
            'flags': int(placement.flags),
            'show_cmd': int(placement.showCmd),
            'min_position': (int(placement.ptMinPosition.x), int(placement.ptMinPosition.y)),
            'max_position': (int(placement.ptMaxPosition.x), int(placement.ptMaxPosition.y)),
            'normal_rect': (int(rect.left), int(rect.top), int(rect.right), int(rect.bottom)),
        }
    except Exception:
        return None


def _apply_native_window_placement(app, saved):
    """Reaplica el WINDOWPLACEMENT capturado. Es más fiable que geometry() tras fullscreen."""
    if not saved or not sys.platform.startswith('win'):
        return False
    hwnd = _native_toplevel_hwnd(app)
    if not hwnd:
        return False
    try:
        class POINT(ctypes.Structure):
            _fields_ = [('x', ctypes.c_long), ('y', ctypes.c_long)]

        class RECT(ctypes.Structure):
            _fields_ = [
                ('left', ctypes.c_long), ('top', ctypes.c_long),
                ('right', ctypes.c_long), ('bottom', ctypes.c_long),
            ]

        class WINDOWPLACEMENT(ctypes.Structure):
            _fields_ = [
                ('length', ctypes.c_uint),
                ('flags', ctypes.c_uint),
                ('showCmd', ctypes.c_uint),
                ('ptMinPosition', POINT),
                ('ptMaxPosition', POINT),
                ('rcNormalPosition', RECT),
            ]

        left, top, right, bottom = [int(v) for v in saved['normal_rect']]
        min_x, min_y = [int(v) for v in saved.get('min_position', (0, 0))]
        max_x, max_y = [int(v) for v in saved.get('max_position', (0, 0))]
        show_cmd = int(saved.get('show_cmd', 1) or 1)

        # Sólo se conservan los dos estados de uso real de CorePulse antes de F11.
        # SW_SHOWNORMAL=1 / SW_SHOWMAXIMIZED=3.
        if show_cmd not in (1, 3):
            show_cmd = 1

        placement = WINDOWPLACEMENT()
        placement.length = ctypes.sizeof(WINDOWPLACEMENT)
        placement.flags = int(saved.get('flags', 0) or 0)
        placement.showCmd = show_cmd
        placement.ptMinPosition = POINT(min_x, min_y)
        placement.ptMaxPosition = POINT(max_x, max_y)
        placement.rcNormalPosition = RECT(left, top, right, bottom)

        ok = bool(ctypes.windll.user32.SetWindowPlacement(hwnd, ctypes.byref(placement)))
        if ok:
            try:
                ctypes.windll.user32.ShowWindow(hwnd, show_cmd)
            except Exception:
                pass
        return ok
    except Exception:
        return False


def _capture_window_restore_state(app):
    """Guarda estado + geometría Tk + WINDOWPLACEMENT nativo antes de entrar a F11."""
    try:
        app.update_idletasks()
    except Exception:
        pass

    state = 'normal'
    try:
        state = str(app.state() or 'normal')
    except Exception:
        pass

    try:
        geometry = str(app.winfo_geometry())
    except Exception:
        geometry = None

    try:
        bounds = (
            int(app.winfo_width()), int(app.winfo_height()),
            int(app.winfo_x()), int(app.winfo_y()),
        )
    except Exception:
        bounds = None

    app._previous_geometry = geometry
    app._previous_window_state = state
    app._previous_window_bounds = bounds
    app._previous_native_placement = _capture_native_window_placement(app)


def _enter(app):
    if getattr(app, '_layout_transition', False) or getattr(app, 'is_fullscreen', False):
        return

    _capture_window_restore_state(app)
    app._layout_transition = True
    _set_resizing(app, True)
    app.is_fullscreen = True
    _cancel(app, '_resize_after_id')

    # Fullscreen directo: nunca se pasa por zoomed, porque eso altera el
    # rectángulo normal que Windows debe recordar al volver con Escape.
    # V391: además de activar el atributo de Tk, se reafirma explícitamente el
    # rectángulo del monitor. En algunos Windows 11 + CustomTkinter, Tk mueve
    # la ventana a la esquina superior izquierda pero conserva el tamaño de
    # ventana; este segundo paso evita esa regresión sin perder el snapshot.
    fullscreen_bounds = _current_monitor_bounds(app)

    def commit_fullscreen():
        try:
            app.attributes('-fullscreen', True)
            app.update_idletasks()
        except Exception:
            pass
        _force_fullscreen_bounds(app, fullscreen_bounds)

        def reinforce_fullscreen():
            if getattr(app, 'is_fullscreen', False):
                _force_fullscreen_bounds(app, fullscreen_bounds)

        def settle_fullscreen():
            if getattr(app, 'is_fullscreen', False):
                _force_fullscreen_bounds(app, fullscreen_bounds)
            # Fuerza el layout después de que Tk/Windows ya publicaron el tamaño
            # fullscreen. Así también se aplica el margen superior del sidebar.
            _finish(app)

        try:
            app.after(90, reinforce_fullscreen)
            app.after(FULLSCREEN_SETTLE_MS, settle_fullscreen)
        except Exception:
            settle_fullscreen()

    try:
        app.after_idle(commit_fullscreen)
    except Exception:
        commit_fullscreen()


def _restore_tk_geometry_fallback(app):
    """Fallback portable cuando WINDOWPLACEMENT nativo no está disponible."""
    previous_state = str(getattr(app, '_previous_window_state', None) or 'normal').lower()
    previous_geometry = getattr(app, '_previous_geometry', None)
    previous_bounds = getattr(app, '_previous_window_bounds', None)

    try:
        if previous_state == 'zoomed':
            app.state('zoomed')
            app.update_idletasks()
            return True
        app.state('normal')
        app.update_idletasks()
    except Exception:
        pass

    restored = False
    if previous_bounds and len(previous_bounds) == 4:
        try:
            width, height, x, y = [int(v) for v in previous_bounds]
            if width > 300 and height > 250:
                app.geometry(f'{width}x{height}+{x}+{y}')
                restored = True
        except Exception:
            pass

    if (not restored) and previous_geometry:
        try:
            app.geometry(str(previous_geometry))
            restored = True
        except Exception:
            pass

    try:
        app.update_idletasks()
    except Exception:
        pass
    return restored


def _restore_window_snapshot(app):
    """Restaura primero con Windows nativo y degrada a Tk si fuera necesario."""
    try:
        app.attributes('-fullscreen', False)
        app.update_idletasks()
    except Exception:
        pass

    previous_state = str(getattr(app, '_previous_window_state', None) or 'normal').lower()
    try:
        # Sacar explícitamente a Tk del estado fullscreen antes de SetWindowPlacement.
        app.state('normal')
        app.update_idletasks()
    except Exception:
        pass

    native_saved = getattr(app, '_previous_native_placement', None)
    if _apply_native_window_placement(app, native_saved):
        return True

    # Si no existe API nativa (o falló), vuelve a la geometría capturada por Tk.
    if previous_state == 'zoomed':
        try:
            app.state('zoomed')
            app.update_idletasks()
            return True
        except Exception:
            pass
    return _restore_tk_geometry_fallback(app)


def _exit(app):
    if getattr(app, '_layout_transition', False) or not getattr(app, 'is_fullscreen', False):
        return

    app._layout_transition = True
    _set_resizing(app, True)
    app.is_fullscreen = False
    _cancel(app, '_resize_after_id')

    # Windows puede tardar varios frames en retirar WS_EX_TOPMOST/fullscreen.
    # Mientras tanto mantenemos bloqueado <Configure> y reafirmamos el snapshot
    # exacto en tres momentos. El último settle libera la autoridad responsive.
    _restore_window_snapshot(app)

    def restore_pass():
        _restore_window_snapshot(app)

    def final_restore():
        _restore_window_snapshot(app)
        try:
            app._layout_last_client_size = (int(app.winfo_width()), int(app.winfo_height()))
        except Exception:
            pass
        _finish(app)

    try:
        app.after(80, restore_pass)
        app.after(180, restore_pass)
        app.after(360, final_restore)
    except Exception:
        final_restore()


def _toggle(app, event=None):
    _exit(app) if getattr(app, 'is_fullscreen', False) else _enter(app)
    return 'break'

def _escape(app, event=None):
    if getattr(app, 'is_fullscreen', False):
        _exit(app)
        return 'break'

def _install_layout_authority(app):
    _cancel(app, 'resize_timer')
    for seq in ('<Configure>', '<F11>', '<Escape>'):
        try:
            app.unbind(seq)
        except Exception:
            pass
    app._resize_after_id = None
    app._layout_transition = False
    app._previous_geometry = None
    app._previous_window_state = None
    app._previous_window_bounds = None
    app._previous_native_placement = None
    try:
        app.update_idletasks()
        app._layout_last_client_size = (int(app.winfo_width()), int(app.winfo_height()))
    except Exception:
        app._layout_last_client_size = None

    def configure(event):
        try:
            if event.widget is not app or app._layout_transition:
                return
        except Exception:
            return

        # Windows/Tk emite <Configure> tanto al REDIMENSIONAR como al MOVER.
        # Si ancho y alto no cambiaron, es un movimiento puro: no se toca el
        # responsive, no se invalida matplotlib y no se marca is_resizing.
        try:
            width = int(getattr(event, 'width', 0) or app.winfo_width())
            height = int(getattr(event, 'height', 0) or app.winfo_height())
        except Exception:
            return
        size = (width, height)
        previous_size = getattr(app, '_layout_last_client_size', None)
        if previous_size == size:
            return
        app._layout_last_client_size = size

        _set_resizing(app, True)
        # V148: no cancelar/crear un callback Tcl por cada pixel. Se mantiene un
        # único detector trailing que observa la última marca temporal.
        app._layout_last_resize_event = time.monotonic()

        def settle():
            try:
                elapsed_ms = (time.monotonic() - float(getattr(app, '_layout_last_resize_event', 0.0))) * 1000.0
            except Exception:
                elapsed_ms = RESIZE_DEBOUNCE_MS
            if elapsed_ms < RESIZE_DEBOUNCE_MS:
                delay = max(12, int(RESIZE_DEBOUNCE_MS - elapsed_ms))
                try:
                    app._resize_after_id = app.after(delay, settle)
                    return
                except Exception:
                    pass
            app._resize_after_id = None
            _set_resizing(app, False)
            # Mientras una página interna está visible, el Dashboard permanece
            # cacheado debajo y no necesita reestilizarse. Su layout se sincroniza
            # al volver, evitando trabajo y repaints ocultos durante el resize.
            if getattr(app, '_active_internal_page', None):
                app._dashboard_layout_sync_pending = True
                try:
                    from gui.internal_navigation import notify_active_page_geometry
                    app.after_idle(lambda: notify_active_page_geometry(app))
                except Exception:
                    pass
                return
            app._dashboard_layout_sync_pending = False
            _apply_layout(app, force=False)
        if getattr(app, '_resize_after_id', None) is None:
            try:
                app._resize_after_id = app.after(RESIZE_DEBOUNCE_MS, settle)
            except Exception:
                settle()
    app.bind('<Configure>', configure, add=False)
    app.bind('<F11>', lambda e: _toggle(app, e), add=False)
    app.bind('<Escape>', lambda e: _escape(app, e), add=False)
    app.toggle_fullscreen = types.MethodType(lambda self, event=None: _toggle(self, event), app)
    app.exit_fullscreen = types.MethodType(lambda self, event=None: _escape(self, event), app)

def request_chart_reflow(app, redraw=True):
    """Reflujo liviano; nunca pelea con un resize que todavía está en curso."""
    if getattr(app, 'is_resizing', False) or getattr(app, '_layout_transition', False):
        app._chart_reflow_pending = True
        return
    app._chart_reflow_pending = False
    try:
        mode = getattr(app, '_layout_mode', None) or _layout_mode(int(app.winfo_width()), int(app.winfo_height()))
    except Exception:
        mode = 'standard'
    _sync_chart_figure_geometry(app, mode)
    if redraw:
        try:
            app.canvas.draw_idle()
        except Exception:
            pass


def _install_chart_geometry_authority(app):
    if getattr(app, '_chart_geometry_authority_active', False):
        return

    def on_frame_configure(event=None):
        frame = getattr(app, 'frame_charts', None)
        try:
            if frame is None or (event is not None and event.widget is not frame):
                return
        except Exception:
            return
        _cancel(app, '_chart_reflow_after_id')

        def settle():
            app._chart_reflow_after_id = None
            if getattr(app, 'is_resizing', False) or getattr(app, '_layout_transition', False):
                app._chart_reflow_pending = True
                return
            request_chart_reflow(app, redraw=False)
        try:
            app._chart_reflow_after_id = app.after(70, settle)
        except Exception:
            settle()

    try:
        app.frame_charts.bind('<Configure>', on_frame_configure, add='+')
    except Exception:
        pass
    app._chart_geometry_authority_active = True


def apply_dashboard_architecture(app):
    if getattr(app, '_dashboard_layout_active', False):
        return
    _style_sidebar(app)
    _style_status_band(app)
    _style_hardware(app)
    _style_charts(app)
    _install_chart_geometry_authority(app)
    render_ai_card(app)
    try:
        from gui.dashboard import request_native_card_surface_sync
        request_native_card_surface_sync(app)
    except Exception:
        pass
    _install_storage_route(app)
    _install_layout_authority(app)
    app._dashboard_layout_active = True
    app._corepulse_design_id = DESIGN_ID

    # V0.10.2.28w: aplica una geometría responsiva inicial aunque Windows no
    # emita otro <Configure> después de instalar la autoridad de layout.
    try:
        app.after_idle(lambda: _apply_layout(app, force=True))
    except Exception:
        _apply_layout(app)
