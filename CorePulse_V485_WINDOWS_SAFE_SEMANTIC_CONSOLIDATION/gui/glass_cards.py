"""V417 · Un único reflejo óptico por tarjeta, sin artefactos de subcapas.

CustomTkinter no proporciona alfa real en CTkFrame. El tinte glass del
material se obtiene desde los roles del tema. Un único reflejo RGBA temporal
queda dentro del Canvas de la tarjeta raíz. NUNCA se inyecta otro efecto en
CTkFrame transparentes anidados: allí Tk dibuja otra superficie y provocaba
los rectángulos oscuros de V416.

No toca datos, widgets funcionales ni el sustrato del workspace.
"""
from __future__ import annotations

import math
import tkinter as tk
import weakref
from PIL import Image, ImageChops, ImageDraw, ImageTk
from core.theme_manager import role_color

_TAG = '_cp_glass_v417'
_OLD_TAG = '_cp_glass_v416'


def glass_overlay_rgba(width: int, height: int, *, offset=(0, 0), extent=None,
                       accent=None, radius=0) -> Image.Image:
    """Produce una luz suave y continua, sin barras duras ni líneas horizontales.

    La transición llega a cero suavemente antes de 40 px. ``offset`` conserva
    la compatibilidad de la API, aunque V417 pinta exclusivamente la raíz.
    """
    width, height = int(width), int(height)
    if width <= 0 or height <= 0:
        raise ValueError('Dimensiones de capa inválidas')
    ox, oy = map(int, offset)
    ew, eh = extent if extent is not None else (width, height)
    ew, eh = max(1, int(ew)), max(1, int(eh))

    raw = str(accent or role_color('accent')).lstrip('#')
    try:
        rgb = tuple(int(raw[i:i + 2], 16) for i in (0, 2, 4))
    except (TypeError, ValueError):
        rgb = (20, 184, 255)
    cool = tuple(round(a * .24 + b * .76) for a, b in zip(rgb, (174, 215, 239)))
    light = Image.new('RGBA', (width, height), (*cool, 0))
    # El brillo no dibuja barras opacas. Desaparece tanto en los extremos X
    # como hacia el contenido Y, evitando un "techo" en cada subcontenedor.
    alpha = Image.new('L', (width, height), 0)
    pixels = alpha.load()
    for ly in range(min(height, max(0, 41 - oy))):
        gy = ly + oy
        if gy < 0 or gy >= 41 or gy >= eh:
            continue
        vertical = (1.0 - gy / 41.0) ** 2.2
        # Resplandor ancho + una reflexión alta, SIN remate horizontal recto.
        gleam = 27 * vertical + 10 * math.exp(-((gy - 3.0) / 4.5) ** 2)
        for lx in range(width):
            gx = lx + ox
            if gx < 0 or gx >= ew:
                continue
            # Más tenue cerca de las esquinas, intensidad máxima en el tercio
            # izquierdo. El fade es continuo, sin saltos de color/bandas.
            xf = (math.sin(math.pi * gx / ew) ** .75) * min(
                1.0, max(0.0, (gx - 5) / 22.0),
                max(0.0, (ew - 6 - gx) / 26.0),
            )
            bias = .84 + .16 * (1. - gx / ew)
            pixels[lx, ly] = max(0, min(255, round(gleam * xf * bias)))

    if radius:
        rounding = Image.new('L', (width, height), 0)
        # Reservamos al menos 2 px para que el borde original de CTk siga
        # visible y no aparezca una sombra cuadrada fuera de la tarjeta.
        ImageDraw.Draw(rounding).rounded_rectangle(
            (2, 2, max(2, width - 3), max(2, height - 3)),
            radius=max(0, int(radius) - 2), fill=255,
        )
        alpha = ImageChops.multiply(alpha, rounding)
    light.putalpha(alpha)
    return light


class GlassCardVisuals:
    """Acabado opt-in sin duplicación en widgets transparentes anidados."""

    def __init__(self, root):
        self.root = root
        self._cards = weakref.WeakSet()
        self._photos = weakref.WeakKeyDictionary()
        self._last_signature = weakref.WeakKeyDictionary()
        self._after_id = None

    def register(self, card):
        if card is None or getattr(card, '_canvas', None) is None:
            return False
        if card not in self._cards:
            self._cards.add(card)
            try:
                card.bind('<Configure>', lambda _event: self.schedule(), add='+')
            except (tk.TclError, AttributeError):
                pass
        # Nunca bajar al árbol de hijos. V416 pintaba reflejos adicionales en
        # cada CTkFrame transparent y dejaba cuadrados y barras superpuestos.
        self.schedule()
        return True

    def schedule(self):
        try:
            if self._after_id is not None:
                self.root.after_cancel(self._after_id)
            self._after_id = self.root.after(110, self.refresh)
        except (tk.TclError, AttributeError):
            self._after_id = None

    def refresh(self):
        self._after_id = None
        for card in list(self._cards):
            try:
                if not card.winfo_exists():
                    self._cards.discard(card)
                    self._photos.pop(card, None)
                    self._last_signature.pop(card, None)
                    continue
                if not card.winfo_ismapped():
                    continue
                canvas = card._canvas
                width, height = int(canvas.winfo_width()), int(canvas.winfo_height())
                if width < 25 or height < 35:
                    continue
                radius = max(0, int(card.cget('corner_radius')))
                signature = (width, height, radius, role_color('accent'))
                # Si hubiera un widget de una versión anterior en memoria,
                # retiramos la capa vieja en vez de acumular reflejos.
                canvas.delete(_OLD_TAG)
                photo = self._photos.get(card)
                if self._last_signature.get(card) != signature or photo is None:
                    photo = ImageTk.PhotoImage(
                        glass_overlay_rgba(width, height, accent=signature[3], radius=radius),
                        master=canvas,
                    )
                    self._photos[card] = photo
                    self._last_signature[card] = signature
                existing = canvas.find_withtag(_TAG)
                if existing:
                    canvas.itemconfigure(existing[0], image=photo)
                else:
                    canvas.create_image(0, 0, anchor='nw', image=photo, tags=(_TAG,))
                # Sobre el relleno CTk, debajo de las ventanas Tk hijas.
                canvas.tag_raise(_TAG)
            except (tk.TclError, AttributeError, ValueError, RuntimeError):
                continue


def install_glass_cards(app):
    controller = getattr(app, '_corepulse_glass_cards', None)
    if controller is None:
        controller = GlassCardVisuals(app)
        app._corepulse_glass_cards = controller
    # V428: la fila superior ya posee el tono glass en el material del card.
    # No dibujar una segunda película óptica encima de Salud, Supervisión,
    # Trazabilidad y Sesión: a escala Windows producía una falsa franja/marco.
    # El material, los acentos y sus datos se conservan intactos.
    cards = [getattr(app, '_ai_card', None), getattr(app, 'card_cpu', None),
             getattr(app, 'card_ram', None), getattr(app, 'card_gpu', None)]
    cards += [(w or {}).get('card') for w in (getattr(app, 'disk_widgets', {}) or {}).values()]
    for card in cards:
        controller.register(card)
    controller.schedule()
    return controller
