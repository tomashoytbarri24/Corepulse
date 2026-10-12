"""Integra todas las páginas en la superficie compartida del Resumen."""
from __future__ import annotations

import tkinter as tk
import customtkinter as ctk

from gui.workspace_background import native_surface_color_at, render_native_workspace
from gui.card_workspace_surface import _configure_if_changed

PAGE_TAG = '_corepulse_flat_page_surface'


def _accent_strip(widget):
    if getattr(widget, '_cp_native_accent_strip', False):
        return True
    if not isinstance(widget, ctk.CTkFrame):
        return False
    try:
        # Las barras y separadores conservan su significado cromático.
        canvas = getattr(widget, '_canvas', None)
        leaf = all(child is canvas for child in widget.winfo_children())
        return leaf and min(float(widget.cget('width')), float(widget.cget('height'))) <= 6
    except (tk.TclError, ValueError, TypeError):
        return False


def _children(widget):
    try:
        return widget.winfo_children()
    except tk.TclError:
        return ()


def prepare_flat_page(page, controller):
    """Retira marcos al construir la página, antes de hacerla visible."""
    stack = [page]
    while stack:
        widget = stack.pop()
        if getattr(widget, '_cp_preserve_surface', False) or _accent_strip(widget):
            continue
        if isinstance(widget, ctk.CTkFrame):
            widget._cp_workspace_flat = True
            _configure_if_changed(widget, fg_color='transparent', border_width=0, corner_radius=0)
            if not getattr(widget, '_cp_flat_configure_bound', False):
                widget.bind('<Configure>', controller._on_configure, add='+')
                widget._cp_flat_configure_bound = True
        if isinstance(widget, (ctk.CTkFrame, ctk.CTkScrollableFrame, tk.Frame, tk.Canvas)):
            stack.extend(_children(widget))


def paint_flat_page(page, controller, offset=(0, 0)):
    """Pinta sólo la página visible; la geometría estable reutiliza su fondo."""
    root = controller.parent
    width, height = controller._last_size
    palette = controller._palette_last
    left = controller._workspace_left
    rx, ry = root.winfo_rootx() - offset[0], root.winfo_rooty() - offset[1]
    stack = [page]
    while stack:
        widget = stack.pop()
        try:
            if not widget.winfo_exists() or not widget.winfo_ismapped():
                continue
            if getattr(widget, '_cp_preserve_surface', False) or _accent_strip(widget):
                continue
            x, y = widget.winfo_rootx() - rx, widget.winfo_rooty() - ry
            w, h = widget.winfo_width(), widget.winfo_height()
            # No pintar contenido fuera del viewport de la página o ventana.
            if x + w <= 0 or y + h <= 0 or x >= width or y >= height:
                continue
            color = native_surface_color_at(x + w // 2, y + h // 2, width, height,
                                            palette=palette, workspace_left=left)
            if isinstance(widget, ctk.CTkFrame):
                widget._cp_workspace_flat = True
                _configure_if_changed(widget, fg_color=color, bg_color=color,
                                      border_width=0, corner_radius=0)
                if not getattr(widget, '_cp_flat_configure_bound', False):
                    widget.bind('<Configure>', controller._on_configure, add='+')
                    widget._cp_flat_configure_bound = True
                canvas = widget._canvas
                render_native_workspace(canvas, x=x, y=y, width=w, height=h,
                                        full_width=width, full_height=height,
                                        palette=palette, workspace_left=left, tag=PAGE_TAG)
                canvas.tag_raise(PAGE_TAG)
                # El canvas interno se acaba de pintar; recorrer sólo contenido real.
                stack.extend(child for child in _children(widget) if child is not canvas)
            elif isinstance(widget, ctk.CTkScrollableFrame):
                if str(widget.cget('fg_color')) != color:
                    widget.configure(fg_color=color)
                stack.extend(_children(widget))
            elif isinstance(widget, (ctk.CTkLabel, ctk.CTkButton, ctk.CTkProgressBar,
                                     ctk.CTkEntry, ctk.CTkTextbox, ctk.CTkOptionMenu,
                                     ctk.CTkComboBox, ctk.CTkCheckBox, ctk.CTkSwitch,
                                     ctk.CTkSlider, ctk.CTkRadioButton, ctk.CTkScrollbar)):
                _configure_if_changed(widget, bg_color=color)
                if isinstance(widget, ctk.CTkLabel) and widget.cget('fg_color') == 'transparent':
                    # CTkLabel tiene un canvas opaco aun siendo transparente.
                    # Pintar también ese canvas evita bandas detrás de títulos anchos.
                    canvas = widget._canvas
                    render_native_workspace(canvas, x=x, y=y, width=w, height=h,
                                            full_width=width, full_height=height,
                                            palette=palette, workspace_left=left, tag=PAGE_TAG)
                    canvas.tag_raise(PAGE_TAG)
                elif isinstance(widget, ctk.CTkTextbox):
                    _configure_if_changed(widget, fg_color=color, border_width=0)
            elif isinstance(widget, tk.Canvas):
                # Viewports de scroll: el fondo va debajo de las ventanas de contenido.
                if any(widget.type(item) == 'window' for item in widget.find_all()):
                    render_native_workspace(widget, x=x, y=y, width=w, height=h,
                                            full_width=width, full_height=height,
                                            palette=palette, workspace_left=left, tag=PAGE_TAG)
                    widget.tag_lower(PAGE_TAG)
                stack.extend(_children(widget))
            elif isinstance(widget, tk.Frame):
                if str(widget.cget('background')) != color:
                    widget.configure(background=color)
                stack.extend(_children(widget))
        except (tk.TclError, AttributeError, ValueError, TypeError):
            continue
