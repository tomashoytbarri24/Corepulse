"""V436 · Tarjetas con la misma superficie nativa del espacio de trabajo.

No simula transparencia con un azul fijo: los CTkFrame tienen un Canvas opaco,
y se dibuja sobre ese lienzo la porción EXACTA del Surface Studio que existiría
detrás del widget. Así no aparecen cajas extra ni variaciones del fondo al hacer
hover, cambiar el tema o redimensionar la ventana.

El contenido de los controles (datos, colores, iconos, botones, barras y acciones)
continúa siendo gestionado por sus módulos originales.
"""
from __future__ import annotations

import tkinter as tk
import math

from gui.workspace_background import _blend, _palette, native_surface_color_at, render_native_workspace
from core.theme_manager import role_color

CARD_TAG = '_corepulse_native_card_layer_v436'
CARD_GLOW_TAG = '_corepulse_card_edge_glow_v442'
_SURFACE_ROLES = ('glass_surface', 'glass_surface_2', 'surface')


def _color_at(widget, root, width, height, palette, workspace_left):
    x = widget.winfo_rootx() - root.winfo_rootx() + max(1, widget.winfo_width() // 2)
    y = widget.winfo_rooty() - root.winfo_rooty() + max(1, widget.winfo_height() // 2)
    return native_surface_color_at(x, y, width, height,
                                   palette=palette, workspace_left=workspace_left)


def _configure_if_changed(widget, **changes):
    to_apply = {}
    for key, value in changes.items():
        try:
            if str(widget.cget(key)).lower() != str(value).lower():
                to_apply[key] = value
        except (tk.TclError, AttributeError, ValueError):
            pass
    if to_apply:
        widget.configure(**to_apply)


def card_hover_tone(base, accent, horizontal_fraction, vertical_fraction=0.5):
    """V438: diffuse edge illumination instead of a full rectangular wash.

    The color falls off in BOTH dimensions, reaching the exact original
    workspace tone at the right edge and at the upper/lower borders. This
    keeps the hovered module visually part of the master canvas.
    """
    x = max(0.0, min(1.0, float(horizontal_fraction)))
    y = max(0.0, min(1.0, float(vertical_fraction)))
    if x >= 0.62 or y <= 0.0 or y >= 1.0:
        return base
    horizontal = (1.0 - x / 0.62) ** 2.35
    vertical = max(0.0, math.sin(math.pi * y)) ** 1.35
    strength = 0.145 * horizontal * vertical
    return _blend(base, accent, strength) if strength > 0.002 else base


def _paint_hover_glow(canvas, *, root_card, root, palette, root_size, workspace_left):
    """Compatibilidad: no pintar jamás rectángulos de hover sobre los módulos.

    En V437/V438 se dibujaban rectángulos sobre CTkCanvas anidados. Debido a
    que CTkLabel/CTkFrame gestionan sus fondos de forma separada, estos
    rectángulos creaban parches cuadrados detrás de iconos y textos, incluso
    durante la transición del cursor de una tarjeta a otra.
    """
    canvas.delete(CARD_TAG + '_hover')


def _accent_hover_color(accent):
    """Aclarado discreto del acento real, sin alterar geometría ni superficies."""
    return _blend(accent, '#ffffff', 0.36)


def apply_card_hover_accent(card, active):
    """Sólo cambia la barra de acento existente, nunca crea capas nuevas."""
    if card is None:
        return False
    strip = getattr(card, '_cp_native_hover_strip', None)
    if strip is None:
        return False
    try:
        if not strip.winfo_exists():
            return False
        accent = getattr(card, '_cp_hover_accent', None)
        if not accent:
            return False
        color = _accent_hover_color(accent) if active else accent
        if str(strip.cget('fg_color')).lower() != str(color).lower():
            strip.configure(fg_color=color)
        strip._cp_native_accent_strip = True
        return True
    except (tk.TclError, AttributeError, ValueError, TypeError):
        return False


def _rounded_perimeter_points(left, top, right, bottom, radius, *, subdivisions=6):
    """Puntos de un contorno realmente redondeado, sin píxeles en las esquinas.

    Devuelve un trazado cerrado. Se crean únicamente tres líneas Tk por canvas
    en lugar de los cientos de segmentos de V442.
    """
    radius = max(0., min(float(radius), (right - left) / 2., (bottom - top) / 2.))
    points = []
    for cx, cy, start in (
        (right - radius, top + radius, -90),
        (right - radius, bottom - radius, 0),
        (left + radius, bottom - radius, 90),
        (left + radius, top + radius, 180),
    ):
        for step in range(subdivisions + 1):
            angle = math.radians(start + 90 * step / subdivisions)
            points.extend((round(cx + radius * math.cos(angle), 2),
                           round(cy + radius * math.sin(angle), 2)))
    points.extend(points[:2])
    return points


def _paint_card_edge_glow(canvas, *, widget, root_card, root, width, height,
                          palette, workspace_left):
    """Glow económico: 3 trazos redondeados y caché, nunca miles de segmentos.

    Un trazo completo se recorta automáticamente a los límites de cada canvas
    Tk; por eso acompaña al área visible de la tarjeta incluso si sus hijos
    cubren el canvas exterior. Las esquinas respetan corner_radius.
    """
    previous = getattr(canvas, '_cp_edge_glow_signature', None)
    if not getattr(root_card, '_cp_hover_active', False):
        had_glow = previous is not None or bool(canvas.find_withtag(CARD_GLOW_TAG))
        if had_glow:
            canvas.delete(CARD_GLOW_TAG)
        canvas._cp_edge_glow_signature = None
        return had_glow
    accent = getattr(root_card, '_cp_hover_accent', None)
    if not accent:
        return False
    try:
        card_x = int(root_card.winfo_rootx() - root.winfo_rootx())
        card_y = int(root_card.winfo_rooty() - root.winfo_rooty())
        cw, ch = int(root_card.winfo_width()), int(root_card.winfo_height())
        canvas_x = int(canvas.winfo_rootx() - root.winfo_rootx())
        canvas_y = int(canvas.winfo_rooty() - root.winfo_rooty())
        pw, ph = int(canvas.winfo_width()), int(canvas.winfo_height())
        try:
            radius = float(root_card.cget('corner_radius'))
        except (tk.TclError, AttributeError, TypeError, ValueError, KeyError):
            radius = 14.0
    except (tk.TclError, AttributeError, ValueError, TypeError):
        return False
    if cw < 24 or ch < 24 or pw < 5 or ph < 5:
        return False
    # No se generan capas en canvas interiores que no toquen el perímetro.
    reach = 8
    if (canvas_x >= card_x + cw - reach or canvas_x + pw <= card_x + reach
            or canvas_y >= card_y + ch - reach or canvas_y + ph <= card_y + reach):
        return False
    if (canvas_x > card_x + reach and canvas_x + pw < card_x + cw - reach
            and canvas_y > card_y + reach and canvas_y + ph < card_y + ch - reach):
        return False
    signature = (card_x, card_y, cw, ch, canvas_x, canvas_y, pw, ph,
                 round(radius, 2), str(accent), palette, width, height, workspace_left)
    if previous == signature and canvas.find_withtag(CARD_GLOW_TAG):
        canvas.tag_raise(CARD_GLOW_TAG)
        return True
    canvas.delete(CARD_GLOW_TAG)
    # 3 niveles con caída hacia dentro; el borde exterior es más nítido.
    for inset, intensity, thickness in ((2.0, 0.58, 1.65),
                                        (4.2, 0.29, 1.8),
                                        (6.2, 0.12, 1.6)):
        x0, y0 = card_x + inset, card_y + inset
        x1, y1 = card_x + cw - inset - 1, card_y + ch - inset - 1
        if x1 <= x0 or y1 <= y0:
            continue
        rr = max(4.0, radius - inset)
        coords = _rounded_perimeter_points(x0, y0, x1, y1, rr)
        local = []
        for idx in range(0, len(coords), 2):
            local.extend((coords[idx] - canvas_x, coords[idx+1] - canvas_y))
        # Muestreo una vez por trazo, en lugar de hacerlo por cada segmento.
        base = native_surface_color_at(card_x + cw // 2, card_y + ch // 2,
                width, height, palette=palette, workspace_left=workspace_left)
        color = _blend(base, accent, intensity)
        canvas.create_line(*local, fill=color, width=thickness,
                           joinstyle='round', capstyle='round', tags=(CARD_GLOW_TAG,))
    canvas._cp_edge_glow_signature = signature
    canvas.tag_raise(CARD_GLOW_TAG)
    return True


def _paint_frame(widget, root, width, height, palette, workspace_left, *, root_card=None):
    canvas = getattr(widget, '_canvas', None)
    if canvas is None or not canvas.winfo_exists() or not canvas.winfo_ismapped():
        return False
    w = canvas.winfo_width()
    h = canvas.winfo_height()
    if w < 10 or h < 10:
        return False
    x = canvas.winfo_rootx() - root.winfo_rootx()
    y = canvas.winfo_rooty() - root.winfo_rooty()
    render_native_workspace(
        canvas, x=x, y=y, width=w, height=h,
        full_width=width, full_height=height, palette=palette,
        workspace_left=workspace_left, tag=CARD_TAG,
    )
    canvas.tag_raise(CARD_TAG)
    if root_card is not None:
        canvas._cp_native_root_card = root_card
        _paint_hover_glow(canvas, root_card=root_card, root=root,
            palette=palette, root_size=(width, height), workspace_left=workspace_left)
        _paint_card_edge_glow(canvas, widget=widget, root_card=root_card, root=root,
            width=width, height=height, palette=palette, workspace_left=workspace_left)
    else:
        canvas.delete(CARD_GLOW_TAG)
    return True


def repaint_card_hover(card, controller):
    """Hover inmediato SIN repintar el fondo ni sus CTkFrames descendientes.

    Sólo se actualiza el brillo en los canvas registrados en el último pintado
    nativo normal. Evita lag de V442 al mover el cursor entre controles.
    """
    did_accent = apply_card_hover_accent(card, bool(getattr(card, '_cp_hover_active', False)))
    canvases = tuple(getattr(card, '_cp_native_glow_canvases', ()) or ())
    if controller is None:
        return did_accent
    try:
        width, height = controller._last_size
        palette = controller._palette_last or _palette()
        left = controller._workspace_left
        root = controller.parent
        if width <= 20 or height <= 20:
            return did_accent
        if not canvases and getattr(card, '_cp_hover_active', False):
            # Únicamente la primera vez, si el hover llegó antes del primer
            # refresco de la superficie. No repinta en los cambios siguientes.
            paint_native_card_surface(card, parent=root, palette=palette,
                width=width, height=height, workspace_left=left)
            canvases = tuple(getattr(card, '_cp_native_glow_canvases', ()) or ())
        painted = False
        for canvas in canvases:
            if canvas.winfo_exists() and canvas.winfo_ismapped():
                painted = (_paint_card_edge_glow(canvas, widget=card, root_card=card,
                    root=root, width=width, height=height, palette=palette,
                    workspace_left=left) or painted)
        return bool(painted or did_accent)
    except (tk.TclError, AttributeError, ValueError, TypeError):
        return did_accent


def paint_native_card_surface(card, *, parent, palette, width, height, workspace_left):
    """Reproduce la capa maestra en una tarjeta y sus envoltorios internos.

    El efecto es sin bordes extra. Las barras laterales de color, pastillas,
    botones contextuales y barras de porcentaje NO se sobrepintan.
    """
    if not card.winfo_exists() or not card.winfo_ismapped():
        return False
    # CTk's transparent frame may still have an opaque canvas; both are synced.
    # All child labels use their own Tk background and require a matching fill.
    bright_accents = {
        role_color('accent').lower(), '#16d98b', '#f3b54a',
        '#ff5d6c', '#a064ff',
    }
    painted_canvases = []
    stack = [(card, True)]
    while stack:
        widget, is_root = stack.pop()
        try:
            if not widget.winfo_exists() or not widget.winfo_ismapped():
                continue
            kind = type(widget).__name__
            sampled = _color_at(widget, parent, width, height, palette, workspace_left)
            if kind == 'CTkFrame':
                foreground = str(widget.cget('fg_color')).lower()
                # Solid colored accent bars are the only deliberate paint
                # owned by CTkFrame. All other nested frames are structural
                # even if V435 left an old opaque glass tone on them.
                if not is_root and (getattr(widget, '_cp_native_accent_strip', False) or foreground in bright_accents):
                    continue
                if not is_root:
                    _configure_if_changed(widget, fg_color=sampled, bg_color=sampled,
                                          border_width=0, border_color=sampled)
                # Top-level fill is managed by the dashboard; this local color
                # only covers the CTk underlayer for anti-aliased corners.
                widget._cp_native_flat_fill = sampled
                if _paint_frame(widget, parent, width, height, palette, workspace_left,
                                root_card=card):
                    painted_canvases.append(widget._canvas)
                stack.extend((child, False) for child in widget.winfo_children()
                             if type(child).__name__ in ('CTkFrame', 'CTkLabel', 'CTkButton', 'CTkProgressBar'))
            elif kind in ('CTkLabel', 'CTkButton', 'CTkProgressBar'):
                # Keep child text, pills, icons, progress bars and buttons on
                # their EXACT native workspace color. V437 replaced each one's
                # background with a different flat hover tone, exposing hard
                # rectangles behind controls. The soft accent stays on the
                # underlying frame canvas only.
                _configure_if_changed(widget, bg_color=sampled)
        except (tk.TclError, AttributeError, ValueError, TypeError):
            continue
    # La AI V447 dibuja su único texto en el lienzo nativo de la tarjeta:
    # preservar el mismo halo de hover de V445 sobre ese lienzo, no detrás.
    # Para todas las demás tarjetas el comportamiento queda idéntico.
    ai_canvas = getattr(card, '_cp_ai_native_canvas', None)
    if ai_canvas is not None:
        try:
            if ai_canvas.winfo_exists() and ai_canvas.winfo_ismapped():
                _paint_card_edge_glow(
                    ai_canvas, widget=card, root_card=card, root=parent,
                    width=width, height=height, palette=palette,
                    workspace_left=workspace_left,
                )
                painted_canvases.append(ai_canvas)
        except (tk.TclError, AttributeError, ValueError, TypeError):
            pass
    card._cp_native_glow_canvases = painted_canvases
    return True
