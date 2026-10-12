"""Escrituras visuales sólo cuando cambia el valor real del widget.

Se consulta cget en lugar de cachear: otros módulos y el tema pueden modificar
el mismo control. Sin monkeypatches ni referencias globales a widgets destruidos.
"""


import time


def configure_changed(widget, **values):
    if widget is None:
        return False
    changed = {}
    for key, value in values.items():
        try:
            current = widget.cget(key)
            if isinstance(current, (list, tuple)) and isinstance(value, (list, tuple)):
                equal = tuple(current) == tuple(value)
            else:
                equal = current == value
            if equal:
                continue
        except Exception:
            # Opciones no consultables mantienen su comportamiento original.
            pass
        changed[key] = value
    if not changed:
        return False
    widget.configure(**changed)
    return True


def set_changed(widget, value):
    try:
        if widget.get() == value:
            return False
    except Exception:
        pass
    widget.set(value)
    return True


# V480: primitivas compartidas de fichas de hardware y red.
# Se mantienen semántica REAL_OR_NA (None/bool no son mediciones) y
# comportamiento CTk: no se generan nuevas lecturas ni timers.
def numeric_or_none(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except Exception:
        return None


def format_detail_number(value, digits=1, suffix=''):
    number = numeric_or_none(value)
    if number is None:
        return 'N/A'
    return f'{number:.{digits}f}{suffix}'


def format_detail_integer(value, suffix=''):
    number = numeric_or_none(value)
    if number is None:
        return 'N/A'
    return f'{int(number)}{suffix}'


def detail_age_text(timestamp):
    try:
        age = max(0.0, time.time() - float(timestamp))
    except Exception:
        return 'N/A'
    if age < 1:
        return '< 1 s'
    if age < 60:
        return f'{age:.1f} s'
    return f'{age / 60.0:.1f} min'


def detail_is_scrolling(panel):
    host = getattr(panel, 'body_scroll', None)
    return bool(host is not None and host.is_scrolling())


def set_detail_panel_active(panel, active):
    """Pausa refrescos de fichas cacheadas; una única implementación CPU/GPU/RAM."""
    active = bool(active)
    if panel._active == active:
        return
    panel._active = active
    if not active:
        if panel._after_id is not None:
            try:
                panel.frame.after_cancel(panel._after_id)
            except Exception:
                pass
            panel._after_id = None
        return
    if panel._alive:
        try:
            panel._after_id = panel.frame.after(1, panel.refresh)
        except Exception:
            panel._after_id = None


def create_detail_summary_card(parent, title, value, detail, accent, ctk, card_color, border_color, text_color, muted_color, font):
    """Una única construcción visual para cuatro paneles, sin cambiar su geometría."""
    card = ctk.CTkFrame(parent, fg_color=card_color, border_width=1, border_color=border_color, corner_radius=12, height=92)
    card.pack_propagate(False)
    ctk.CTkLabel(card, text=title, font=(font, 9, 'bold'), text_color=text_color).pack(anchor='w', padx=12, pady=(9, 0))
    value_label = ctk.CTkLabel(card, text=value, font=(font, 20, 'bold'), text_color=accent)
    value_label.pack(anchor='w', padx=12)
    detail_label = ctk.CTkLabel(card, text=detail, font=(font, 8), text_color=muted_color)
    detail_label.pack(anchor='w', padx=12, pady=(0, 7))
    return card, value_label, detail_label


def create_detail_section_card(parent, title, subtitle, ctk, card_color, border_color, text_color, muted_color, font):
    card = ctk.CTkFrame(parent, fg_color=card_color, border_width=1, border_color=border_color, corner_radius=12)
    ctk.CTkLabel(card, text=title, font=(font, 10, 'bold'), text_color=text_color).pack(anchor='w', padx=14, pady=(11, 0))
    ctk.CTkLabel(card, text=subtitle, font=(font, 8), text_color=muted_color).pack(anchor='w', padx=14, pady=(1, 7))
    return card
