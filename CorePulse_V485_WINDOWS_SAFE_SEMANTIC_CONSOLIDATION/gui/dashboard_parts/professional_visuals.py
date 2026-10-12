"""Helpers visuales compartidos para una estética profesional y consistente."""
from __future__ import annotations

import customtkinter as ctk

from core.theme_manager import color as theme_color

FONT = 'Segoe UI'
TEXT = theme_color('#f4f7fb')
TEXT_2 = theme_color('#b8c4d4')
MUTED = theme_color('#8295ad')
CYAN = '#14b8ff'
GREEN = '#1fd18b'
AMBER = '#f59e0b'
PURPLE = '#a78bfa'
RED = '#ff5d6c'

_BADGE_STYLE = {
    CYAN: (theme_color('#0d2942'), theme_color('#1d5278'), theme_color('#9bddff')),
    '#38bdf8': (theme_color('#0d2942'), theme_color('#1d5278'), theme_color('#9bddff')),
    '#60a5fa': (theme_color('#0d2942'), theme_color('#1d5278'), theme_color('#b9ddff')),
    GREEN: (theme_color('#0d332b'), theme_color('#178967'), theme_color('#baf5dc')),
    '#10b981': (theme_color('#0d332b'), theme_color('#178967'), theme_color('#baf5dc')),
    '#22c993': (theme_color('#0d332b'), theme_color('#178967'), theme_color('#baf5dc')),
    AMBER: (theme_color('#241d0f'), theme_color('#6e5421'), theme_color('#f4b942')),
    '#f0a23a': (theme_color('#241d0f'), theme_color('#6e5421'), theme_color('#f4b942')),
    '#f2b84b': (theme_color('#241d0f'), theme_color('#6e5421'), theme_color('#f4b942')),
    PURPLE: (theme_color('#152750'), theme_color('#4a4772'), theme_color('#dac5ff')),
    '#a855f7': (theme_color('#152750'), theme_color('#4a4772'), theme_color('#dac5ff')),
    '#a064ff': (theme_color('#152750'), theme_color('#4a4772'), theme_color('#dac5ff')),
    RED: (theme_color('#2b1d26'), theme_color('#693343'), theme_color('#ffb8c0')),
    '#ef4444': (theme_color('#2b1d26'), theme_color('#693343'), theme_color('#ffb8c0')),
    '#ef5b67': (theme_color('#2b1d26'), theme_color('#693343'), theme_color('#ffb8c0')),
}
_DEFAULT_BADGE = (theme_color('#102235'), theme_color('#17314d'), TEXT_2)


def _badge_spec(item, default_accent=CYAN):
    if isinstance(item, dict):
        text = str(item.get('text') or '').strip()
        accent = item.get('accent') or default_accent
    elif isinstance(item, (list, tuple)):
        text = str(item[0] if item else '').strip()
        accent = item[1] if len(item) > 1 else default_accent
    else:
        text = str(item or '').strip()
        accent = default_accent
    return text, accent


def build_badge_row(parent, badges, *, default_accent=CYAN):
    items = list(badges or ())
    row = ctk.CTkFrame(parent, fg_color='transparent')
    for index, item in enumerate(items):
        text, accent = _badge_spec(item, default_accent=default_accent)
        if not text:
            continue
        bg, border, text_color = _BADGE_STYLE.get(accent, _DEFAULT_BADGE)
        pill = ctk.CTkFrame(row, fg_color=bg, border_width=1, border_color=border, corner_radius=999)
        pill.pack(side='left', padx=(0, 6 if index < len(items) - 1 else 0))
        ctk.CTkLabel(
            pill,
            text=text,
            font=(FONT, 8, 'bold'),
            text_color=text_color,
            anchor='center',
            justify='center',
        ).pack(padx=9, pady=4)
    return row


def build_title_block(parent, *, eyebrow, title, subtitle, accent=CYAN, badges=(), title_size=19):
    wrap = ctk.CTkFrame(parent, fg_color='transparent')
    eyebrow_label = ctk.CTkLabel(
        wrap,
        text=str(eyebrow),
        font=(FONT, 8, 'bold'),
        text_color=accent,
        anchor='w',
        justify='left',
    )
    eyebrow_label.pack(anchor='w', pady=(0, 1))
    title_label = ctk.CTkLabel(
        wrap,
        text=str(title),
        font=(FONT, title_size, 'bold'),
        text_color=TEXT,
        anchor='w',
        justify='left',
    )
    title_label.pack(anchor='w')
    subtitle_label = ctk.CTkLabel(
        wrap,
        text=str(subtitle),
        font=(FONT, 10),
        text_color=TEXT_2,
        anchor='w',
        justify='left',
        wraplength=720,
    )
    subtitle_label.pack(anchor='w', pady=(2, 0))
    badges_row = None
    if badges:
        badges_row = build_badge_row(wrap, badges, default_accent=accent)
        badges_row.pack(anchor='w', pady=(6, 0))
    return {
        'frame': wrap,
        'eyebrow': eyebrow_label,
        'title': title_label,
        'subtitle': subtitle_label,
        'badges': badges_row,
    }


def build_empty_state(
    parent,
    *,
    icon='○',
    title='Sin datos todavía',
    description='',
    accent=CYAN,
    action_text=None,
    action_command=None,
    compact=False,
):
    """Estado vacío reutilizable con una acción clara y sin ruido visual."""
    bg, border, _text_color = _BADGE_STYLE.get(accent, _DEFAULT_BADGE)
    frame = ctk.CTkFrame(
        parent,
        fg_color=theme_color('#0a1726'),
        border_width=1,
        border_color=border,
        corner_radius=12,
    )
    frame.grid_columnconfigure(1, weight=1)

    size = 42 if compact else 50
    icon_box = ctk.CTkFrame(
        frame,
        width=size,
        height=size,
        fg_color=bg,
        border_width=1,
        border_color=border,
        corner_radius=12,
    )
    icon_box.grid(row=0, column=0, rowspan=2, sticky='nw', padx=(12, 10), pady=12)
    icon_box.grid_propagate(False)
    ctk.CTkLabel(
        icon_box,
        text=str(icon),
        font=(FONT, 20 if compact else 23, 'bold'),
        text_color=accent,
    ).pack(expand=True, fill='both')

    ctk.CTkLabel(
        frame,
        text=str(title),
        font=(FONT, 11 if compact else 12, 'bold'),
        text_color=TEXT,
        anchor='w',
        justify='left',
    ).grid(row=0, column=1, sticky='ew', padx=(0, 12), pady=(12, 2))

    ctk.CTkLabel(
        frame,
        text=str(description or ''),
        font=(FONT, 8 if compact else 9),
        text_color=MUTED,
        anchor='w',
        justify='left',
        wraplength=760,
    ).grid(row=1, column=1, sticky='new', padx=(0, 12), pady=(0, 12 if not action_text else 6))

    button = None
    if action_text and callable(action_command):
        button = ctk.CTkButton(
            frame,
            text=str(action_text),
            command=action_command,
            height=28 if compact else 31,
            width=132,
            corner_radius=8,
            border_width=1,
            border_color=border,
            fg_color=bg,
            hover_color=theme_color('#15314b'),
            text_color=TEXT,
            font=(FONT, 8 if compact else 9, 'bold'),
        )
        button.grid(row=2, column=1, sticky='w', padx=(0, 12), pady=(0, 12))

    return {'frame': frame, 'button': button}


# V481 · Implementación consolidada desde gui/dashboard_parts/header_identity_canvas.py (sin cambio de contrato público).
import tkinter as tk


class _DeviceTextControl:
    """Compatibilidad con _safe_config() y el layout responsive del Resumen."""

    def __init__(self, canvas):
        self.canvas = canvas
        self.options = {
            'text': 'Identificando equipo…',
            'font': ('Segoe UI', 17, 'bold'),
            'text_color': '#f4f7fb',
            'anchor': 'w',
            'justify': 'left',
            'wraplength': 650,
        }

    def cget(self, option):
        return self.options.get(option)

    def configure(self, **kwargs):
        changed = False
        for key, value in kwargs.items():
            if key in self.options and self.options[key] != value:
                self.options[key] = value
                changed = True
        if changed:
            self.canvas.update_identity_text()


class HeaderIdentityCanvas(tk.Canvas):
    """Icono de equipo y nombre, centrados sobre la superficie nativa."""

    def __init__(self, parent, *, foreground='#f4f7fb', fallback_bg='#06111f'):
        super().__init__(
            parent, height=82, bd=0, highlightthickness=0,
            relief='flat', background=fallback_bg, takefocus=0,
        )
        icon_color = '#dce8f4'
        self._icon_ids = (
            self.create_rectangle(15, 22, 53, 51, outline=icon_color, width=2, tags=('identity_foreground',)),
            self.create_line(12, 55, 56, 55, fill=icon_color, width=2, tags=('identity_foreground',)),
            self.create_line(7, 62, 61, 62, fill=icon_color, width=2, tags=('identity_foreground',)),
            self.create_line(12, 55, 7, 62, fill=icon_color, width=2, tags=('identity_foreground',)),
            self.create_line(56, 55, 61, 62, fill=icon_color, width=2, tags=('identity_foreground',)),
            self.create_line(27, 59, 41, 59, fill=icon_color, width=2, tags=('identity_foreground',)),
        )
        self._label_id = self.create_text(
            76, 41, anchor='w', text='Identificando equipo…',
            font=('Segoe UI', 17, 'bold'), fill=foreground, justify='left',
            width=620, tags=('identity_foreground',),
        )
        self.text_control = _DeviceTextControl(self)
        self.bind('<Configure>', lambda _event: self._relayout(), add='+')
        self._relayout()

    def _relayout(self):
        try:
            width = max(80, self.winfo_width())
            height = max(48, self.winfo_height())
            center = height // 2
            self.coords(self._icon_ids[0], 15, center - 19, 53, center + 10)
            self.coords(self._icon_ids[1], 12, center + 14, 56, center + 14)
            self.coords(self._icon_ids[2], 7, center + 21, 61, center + 21)
            self.coords(self._icon_ids[3], 12, center + 14, 7, center + 21)
            self.coords(self._icon_ids[4], 56, center + 14, 61, center + 21)
            self.coords(self._icon_ids[5], 27, center + 18, 41, center + 18)
            self.coords(self._label_id, 76, center)
            max_width = max(50, width - 92)
            intended = self.text_control.options.get('wraplength') or 650
            self.itemconfigure(self._label_id, width=min(max_width, int(intended)))
        except (tk.TclError, ValueError, TypeError):
            pass

    def update_identity_text(self):
        opts = self.text_control.options
        try:
            self.itemconfigure(
                self._label_id, text=opts['text'], font=opts['font'],
                fill=opts['text_color'], justify=opts['justify'],
                anchor=opts['anchor'],
            )
            self._relayout()
        except tk.TclError:
            pass


# V481 · Implementación consolidada desde gui/dashboard_parts/status_symbols.py (sin cambio de contrato público).
from functools import lru_cache
from PIL import Image, ImageDraw
import customtkinter as ctk

@lru_cache(maxsize=96)
def _symbol(kind, color, condition="unknown"):
    image = Image.new('RGBA', (160, 160))
    d = ImageDraw.Draw(image)
    def line(points):
        d.line([(x*4, y*4) for x,y in points], fill=color, width=7, joint='curve')
    if kind == 'health':
        line([(20,4),(33,9),(32,23),(28,30),(20,36),(12,30),(8,23),(7,9),(20,4)])
        line([(10,20),(15,20),(18,14),(22,26),(25,20),(30,20)])
    elif kind == 'watch':
        d.rounded_rectangle((20,28,140,116), radius=12, outline=color, width=7)
        line([(8,20),(13,20),(17,13),(22,25),(26,18),(32,18)])
        line([(20,29),(20,35)]); line([(13,35),(27,35)])
    elif kind == 'trace':
        line([(12,10),(29,10),(29,29),(12,29),(12,10)])
        line([(12,10),(29,29)])
        for x,y in [(12,10),(29,10),(12,29),(29,29)]:
            d.ellipse(((x-4)*4,(y-4)*4,(x+4)*4,(y+4)*4), fill=(0,0,0,0), outline=color, width=7)
    else:
        line([(10,5),(30,5)]); line([(10,35),(30,35)])
        line([(12,5),(12,12),(28,28),(28,35)])
        line([(28,5),(28,12),(12,28),(12,35)])
        line([(16,30),(24,30)])
    # Mantener el símbolo del módulo y añadir una señal de condición inequívoca.
    base = image.resize((128, 128), Image.Resampling.LANCZOS)
    image = Image.new('RGBA', (160, 160))
    image.alpha_composite(base, (0, 0))
    d = ImageDraw.Draw(image)
    if condition == 'normal':
        d.line([(113,137),(125,149),(151,120)], fill=color, width=8, joint='curve')
    elif condition == 'critical':
        d.line([(117,121),(150,151)], fill=color, width=8)
        d.line([(150,121),(117,151)], fill=color, width=8)
    elif condition == 'warning':
        d.line([(133,112),(133,137)], fill=color, width=8)
        d.ellipse((129,145,137,153), fill=color)
    elif condition == 'observing':
        d.ellipse((113,114,155,156), outline=color, width=6)
        d.line([(134,120),(134,135),(146,135)], fill=color, width=5)
    elif condition == 'active':
        d.polygon([(119,116),(151,136),(119,155)], fill=color)
    else:
        d.line([(116,137),(152,137)], fill=color, width=7)
    return ctk.CTkImage(light_image=image, dark_image=image, size=(36,36))

class StatusSymbol(ctk.CTkLabel):
    def __init__(self, master, kind, **kwargs):
        self.symbol_kind = kind
        self.symbol_condition = 'unknown'
        self.symbol_color = kwargs.get('text_color', '#21c7ff')
        kwargs.update(text='', fg_color='transparent', corner_radius=0,
                      image=_symbol(kind, self.symbol_color))
        super().__init__(master, **kwargs)

    def set_condition(self, condition, color=None):
        color = color or self.symbol_color
        if condition == self.symbol_condition and color == self.symbol_color:
            return
        self.symbol_condition = condition
        self.symbol_color = color
        super().configure(image=_symbol(self.symbol_kind, color, condition), text_color=color)

    def configure(self, require_redraw=False, **kwargs):
        kwargs.pop('text', None)
        kwargs.pop('font', None)
        kwargs['fg_color'] = 'transparent'
        kwargs['corner_radius'] = 0
        color = kwargs.get('text_color', self.symbol_color)
        if isinstance(color, (tuple, list)):
            color = color[-1]
        if color != self.symbol_color:
            self.symbol_color = color
            kwargs['image'] = _symbol(self.symbol_kind, color, self.symbol_condition)
        super().configure(require_redraw=require_redraw, **kwargs)


# V481 · Implementación consolidada desde gui/dashboard_parts/render_polish.py (sin cambio de contrato público).
import customtkinter as ctk

from core.theme_manager import is_light_theme, color as theme_color

LIGHT_CARD_RADIUS = 9
LIGHT_BUTTON_RADIUS = 7
LIGHT_BADGE_RADIUS = 7
GLOBAL_CARD_RADIUS = 12
GLOBAL_BUTTON_RADIUS = 8
GLOBAL_INPUT_RADIUS = 8
GLOBAL_BADGE_RADIUS = 8


def _safe_cget(widget, key, default=None):
    try:
        return widget.cget(key)
    except Exception:
        return default


def _safe_config(widget, **kwargs):
    try:
        widget.configure(**kwargs)
        return True
    except Exception:
        return False


def _numeric(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return float(default)


def polish_widget(widget):
    """Normaliza un widget ya creado sin invadir la lógica de negocio."""
    if widget is None:
        return

    light = is_light_theme()
    radius = _numeric(_safe_cget(widget, 'corner_radius', 0))
    border = _numeric(_safe_cget(widget, 'border_width', 0))

    if isinstance(widget, ctk.CTkFrame):
        fg = _safe_cget(widget, 'fg_color', 'transparent')
        if light and border > 0 and radius > LIGHT_CARD_RADIUS:
            _safe_config(widget, corner_radius=LIGHT_CARD_RADIUS)
        elif fg not in (None, 'transparent') and radius not in (0.0,) and radius < GLOBAL_CARD_RADIUS:
            _safe_config(widget, corner_radius=GLOBAL_CARD_RADIUS)
    elif isinstance(widget, ctk.CTkButton):
        target = LIGHT_BUTTON_RADIUS if light and radius > LIGHT_BUTTON_RADIUS else GLOBAL_BUTTON_RADIUS
        if radius < target or (light and radius > LIGHT_BUTTON_RADIUS):
            _safe_config(widget, corner_radius=target)
    elif isinstance(widget, (ctk.CTkEntry, ctk.CTkTextbox, ctk.CTkOptionMenu, ctk.CTkComboBox)):
        if radius < GLOBAL_INPUT_RADIUS:
            _safe_config(widget, corner_radius=GLOBAL_INPUT_RADIUS)
    elif isinstance(widget, ctk.CTkLabel):
        fg = _safe_cget(widget, 'fg_color', 'transparent')
        target = LIGHT_BADGE_RADIUS if light and radius > LIGHT_BADGE_RADIUS else GLOBAL_BADGE_RADIUS
        if fg not in (None, 'transparent') and (radius < target or (light and radius > LIGHT_BADGE_RADIUS)):
            _safe_config(widget, corner_radius=target)


def polish_widget_tree(root):
    """Aplica el pulido a un árbol CTk sin bloquear si un hijo desaparece."""
    if root is None:
        return
    stack = [root]
    seen = set()
    while stack:
        node = stack.pop()
        ident = id(node)
        if ident in seen:
            continue
        seen.add(ident)
        polish_widget(node)
        try:
            stack.extend(node.winfo_children())
        except Exception:
            pass


def install_hover_feedback(button, *, active=False):
    """Refuerza hover de botones CTk cuando su color era casi invisible."""
    if button is None:
        return
    normal = theme_color('#164f7d') if active else 'transparent'
    hover = theme_color('#1b5c8f') if active else theme_color('#0e1d2f')

    def on_enter(_event=None):
        _safe_config(button, fg_color=hover)

    def on_leave(_event=None):
        _safe_config(button, fg_color=normal)

    try:
        button.bind('<Enter>', on_enter, add='+')
        button.bind('<Leave>', on_leave, add='+')
    except Exception:
        pass
