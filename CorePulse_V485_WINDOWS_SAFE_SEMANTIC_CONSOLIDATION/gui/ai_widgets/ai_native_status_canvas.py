"""Estado de CorePulse AI integrado al fondo del encabezado, sin tarjeta."""
from __future__ import annotations

import tkinter as tk


class _TextControl:
    """Adaptador para que el render existente actualice el texto de estado."""

    def __init__(self, canvas):
        self.canvas = canvas
        self.options = {
            'text': 'COMPROBANDO IA NUBE',
            'text_color': '#f4f7fb',
            'font': ('Segoe UI', 12, 'bold'),
            'anchor': 'nw',
            'justify': 'left',
            'wraplength': 260,
        }

    def cget(self, key):
        return self.options.get(key)

    def configure(self, **changes):
        edited = False
        for key, value in changes.items():
            if key in self.options and self.options[key] != value:
                self.options[key] = value
                edited = True
        if edited:
            self.canvas._update_text()


class _DetailControl:
    def __init__(self, canvas):
        self.canvas = canvas
        self.options = {'text': 'Servidor remoto sin configurar', 'text_color': '#9aadc2', 'font': ('Segoe UI', 8)}

    def cget(self, key):
        return self.options.get(key)

    def configure(self, **changes):
        edited = False
        for key, value in changes.items():
            if key in self.options and self.options[key] != value:
                self.options[key] = value
                edited = True
        if edited:
            self.canvas._update_detail()


class _AccentControl:
    """Acento dinámico vinculado al estado real de la IA local."""

    _cp_native_accent_strip = True

    def __init__(self, canvas, color):
        self.canvas = canvas
        self.color = color

    def cget(self, key):
        if key == 'fg_color':
            return self.color
        raise KeyError(key)

    def configure(self, **changes):
        color = changes.get('fg_color')
        if color is not None and color != self.color:
            self.color = str(color)
            self.canvas._update_accent()

    def winfo_exists(self):
        return self.canvas.winfo_exists()


class AIStatusCanvas(tk.Canvas):
    """Icono, estado y modelo sobre la misma superficie del encabezado."""

    def __init__(self, parent, *, accent='#16d98b', fallback_bg='#06111f'):
        super().__init__(
            parent, bd=0, highlightthickness=0, relief='flat',
            background=fallback_bg, takefocus=0,
        )
        self.text_control = _TextControl(self)
        self.detail_control = _DetailControl(self)
        self.accent_control = _AccentControl(self, accent)
        self._accent = accent
        self._power_action = None
        self._power_enabled = True
        self._power_hover = False
        self._power_outline_id = self.create_oval(1, 1, 2, 2, outline='', width=1, tags=('ai_status_foreground', 'ai_power'))
        self._power_arc_id = self.create_arc(1, 1, 2, 2, start=45, extent=270,
                                              style='arc', outline='#d8e2ef', width=2,
                                              tags=('ai_status_foreground', 'ai_power'))
        self._power_line_id = self.create_line(1, 1, 2, 2, fill='#d8e2ef', width=2,
                                               capstyle='round', tags=('ai_status_foreground', 'ai_power'))
        self._power_hint_id = self.create_text(
            1, 1, text='Apagar IA', fill='#b8cadd', font=('Segoe UI', 9),
            anchor='e', state='hidden', tags=('ai_status_foreground', 'ai_power_hint'),
        )
        self._title_id = self.create_text(
            52, 12, text='COREPULSE AI',
            font=('Segoe UI', 9, 'bold'), fill='#d8e2ef',
            anchor='nw', justify='left', tags=('ai_status_foreground',),
        )
        self._status_dot_id = self.create_oval(
            52, 38, 59, 45, fill=accent, outline='',
            tags=('ai_status_foreground',),
        )
        self._text_id = self.create_text(
            68, 34, text=self.text_control.cget('text'),
            font=self.text_control.cget('font'), fill=self.text_control.cget('text_color'),
            anchor='nw', justify='left', width=250,
            tags=('ai_status_foreground',),
        )
        self._detail_id = self.create_text(
            52, 62, text=self.detail_control.cget('text'),
            font=self.detail_control.cget('font'), fill=self.detail_control.cget('text_color'),
            anchor='nw', justify='left', width=260,
            tags=('ai_status_foreground',),
        )
        self._icon_ids = self._create_spark_icon(accent)
        self.bind('<Configure>', self._layout, add='+')
        self.bind('<Motion>', self._power_motion, add='+')
        self.bind('<Leave>', self._power_leave, add='+')
        self.bind('<Button-1>', self._power_click, add='+')
        self._layout()

    def _create_spark_icon(self, color):
        # Destello geométrico sencillo, coherente con la identidad de CorePulse AI.
        points = [
            22, 8, 26, 19, 37, 23, 26, 27,
            22, 38, 18, 27, 7, 23, 18, 19,
        ]
        primary = self.create_polygon(
            *points, fill=color, outline='',
            tags=('ai_status_foreground', 'ai_status_icon'),
        )
        secondary = self.create_polygon(
            39, 7, 41, 13, 47, 15, 41, 17, 39, 23, 37, 17, 31, 15, 37, 13,
            fill='#d8e2ef', outline='',
            tags=('ai_status_foreground', 'ai_status_icon'),
        )
        return primary, secondary

    def _layout(self, _event=None):
        try:
            width = max(8, int(self.winfo_width()))
            height = max(8, int(self.winfo_height()))
            center_y = height / 2
            self.coords(self._icon_ids[0], 22, center_y - 15, 26, center_y - 4,
                        37, center_y, 26, center_y + 4, 22, center_y + 15,
                        18, center_y + 4, 7, center_y, 18, center_y - 4)
            self.coords(self._icon_ids[1], 39, center_y - 16, 41, center_y - 10,
                        47, center_y - 8, 41, center_y - 6, 39, center_y,
                        37, center_y - 6, 31, center_y - 8, 37, center_y - 10)
            text_x = 58
            title_y = max(7, center_y - 33)
            status_y = max(title_y + 19, center_y - 6)
            detail_y = min(height - 19, center_y + 17)
            text_width = max(100, width - text_x - 45)
            self.coords(self._title_id, text_x, title_y)
            self.coords(self._status_dot_id, text_x, status_y + 5, text_x + 7, status_y + 12)
            self.coords(self._text_id, text_x + 15, status_y)
            self.coords(self._detail_id, text_x, detail_y)
            self.itemconfigure(self._text_id, width=text_width)
            self.itemconfigure(self._detail_id, width=text_width)
            x = width - 23
            y = max(18, center_y - 26)
            self.coords(self._power_outline_id, x - 16, y - 16, x + 16, y + 16)
            self.coords(self._power_arc_id, x - 9, y - 9, x + 9, y + 9)
            self.coords(self._power_line_id, x, y - 12, x, y + 1)
            self.coords(self._power_hint_id, x - 22, y)
            self._redraw_power()
            self.tag_raise('ai_status_foreground')
        except (tk.TclError, TypeError, ValueError):
            pass

    def set_power_action(self, callback):
        self._power_action = callback if callable(callback) else None

    def set_power_enabled(self, enabled):
        enabled = bool(enabled)
        if enabled != self._power_enabled:
            self._power_enabled = enabled
            self._redraw_power()

    def _power_hit(self, x, y):
        width = self.winfo_width()
        height = self.winfo_height()
        cy = max(18, height / 2 - 26)
        return width - 45 <= x <= width - 1 and cy - 20 <= y <= cy + 20

    def _redraw_power(self):
        try:
            color = ('#22d995' if self._power_enabled else '#9badc2')
            if self._power_hover:
                color = '#f4f7fb'
            self.itemconfigure(self._power_arc_id, outline=color)
            self.itemconfigure(self._power_line_id, fill=color)
            self.itemconfigure(self._power_outline_id,
                               outline='#406782' if self._power_hover else '')
            self.itemconfigure(self._power_hint_id,
                               text='Apagar IA' if self._power_enabled else 'Encender IA',
                               state='normal' if self._power_hover else 'hidden')
        except tk.TclError:
            pass

    def _power_motion(self, event):
        hover = self._power_hit(event.x, event.y)
        if hover != self._power_hover:
            self._power_hover = hover
            self._redraw_power()
            self.configure(cursor='hand2' if hover else 'arrow')

    def _power_leave(self, _event=None):
        if self._power_hover:
            self._power_hover = False
            self._redraw_power()

    def _power_click(self, event):
        if self._power_hit(event.x, event.y):
            if self._power_action:
                self._power_action()
            return 'break'  # No abrir Centro de IA al pulsar el interruptor.

    def _update_text(self):
        opts = self.text_control.options
        try:
            self.itemconfigure(
                self._text_id, text=opts['text'], font=opts['font'],
                fill=opts['text_color'], anchor=opts['anchor'],
                justify=opts['justify'],
            )
            self._layout()
        except (tk.TclError, TypeError, ValueError):
            pass

    def _update_detail(self):
        opts = self.detail_control.options
        try:
            self.itemconfigure(
                self._detail_id, text=opts['text'], fill=opts['text_color'],
                font=opts['font'],
            )
            self._layout()
        except (tk.TclError, TypeError, ValueError):
            pass

    def _update_accent(self):
        self._accent = self.accent_control.color
        try:
            self.itemconfigure(self._status_dot_id, fill=self._accent)
            self.itemconfigure(self._icon_ids[0], fill=self._accent)
            self.tag_raise('ai_status_foreground')
        except tk.TclError:
            pass
