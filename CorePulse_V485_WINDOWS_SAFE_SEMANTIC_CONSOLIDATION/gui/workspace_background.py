"""Surface Studio V414: superficie de interfaz maestra, sin wallpaper.

La capa inferior de CorePulse se construye mediante geometría Tk (superficies,
gradientes cromáticos continuos) utilizando los roles del tema activo.
No se carga ni se escala ningún PNG de fondo.

CustomTkinter no implementa alfa real en sus wrappers 'transparent'. Para que
no aparezcan rectángulos sólidos, las zonas estructurales reproducen la misma
composición en coordenadas absolutas del cliente. Las tarjetas, iconos,
textos, y controles conservan sus propias superficies independientes.
"""
from __future__ import annotations

import tkinter as tk
from functools import lru_cache
from PIL import Image, ImageDraw, ImageTk

from core.theme_manager import role_color

_DESIGN_TAG = '_corepulse_native_workspace_surface'
_CANVAS_DESIGN_TAG = '_corepulse_native_workspace_canvas'
_WORKSPACE_FLAT_COLORS = {'#06111f', '#08111f', '#071422', '#081624', '#0b1422', '#0d1828'}


def _rgb(value, fallback='#06111f'):
    """Color canónico para generar variaciones del tema sin valores aleatorios."""
    value = str(value or '').strip()
    if len(value) != 7 or not value.startswith('#'):
        value = fallback
    try:
        return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))
    except ValueError:
        return (6, 17, 31)


def _hex(rgb):
    return '#{:02x}{:02x}{:02x}'.format(*(max(0, min(255, round(v))) for v in rgb))


def _blend(a, b, fraction):
    return _blend_cached(str(a), str(b), max(0., min(1., float(fraction))))


@lru_cache(maxsize=8192)
def _blend_cached(a, b, fraction):
    a, b = _rgb(a), _rgb(b)
    return _hex(tuple(u * (1. - fraction) + v * fraction for u, v in zip(a, b)))


def _palette():
    # CorePulse admite varios temas oscuros. La capa sigue automáticamente los
    # colores elegidos por el usuario, sin reutilizar azules de una fotografía.
    bg = role_color('bg')
    surface = role_color('surface')
    border = role_color('border')
    accent = role_color('accent')
    return (bg, surface, border, accent)


def _render_workspace_vectors(canvas, *, x, y, width, height, full_width, full_height,
                            palette, tag, workspace_left=None):
    """V414 · Surface Studio: un solo sustrato de producto, sin wallpaper.

    Composición absoluta (referida a toda la ventana): cada contenedor CTk
    reproduce exactamente la parte del sustrato que le corresponde. No hay
    polígonos, raíles, retículas, ni inicios bruscos de color en la unión con
    el sidebar. Los módulos opacos siguen siendo los dueños de sus tarjetas.

    Son dos capas *cromáticas*, no capas de widgets: acabado mate vertical en
    toda la aplicación + luz suave en la mesa de trabajo, con entrada gradual
    desde el lateral izquierdo. El diseño escala tanto en ventana pequeña como
    maximizado y se adapta a la paleta del tema activo.
    """
    signature = (int(x), int(y), int(width), int(height), int(full_width),
                 int(full_height), tuple(palette), workspace_left)
    cache = getattr(canvas, '_cp_workspace_render_cache', None)
    if cache is None:
        cache = canvas._cp_workspace_render_cache = {}
    if cache.get(tag) == signature and canvas.find_withtag(tag):
        return False
    canvas.delete(tag)
    cache[tag] = signature
    if min(width, height, full_width, full_height) <= 0:
        return

    bg, surface, border, accent = palette
    x, y, width, height = int(x), int(y), int(width), int(height)
    full_width, full_height = int(full_width), int(full_height)
    workspace_left = int(workspace_left if workspace_left is not None else full_width * .205)
    workspace_left = max(0, min(workspace_left, full_width - 150))

    def rectangle(x0, y0, x1, y1, fill):
        # Recorte local con coordenadas maestras; jamás invade tarjetas.
        x0, y0 = max(x, int(x0)), max(y, int(y0))
        x1, y1 = min(x + width, int(x1)), min(y + height, int(y1))
        if x1 <= x0 or y1 <= y0:
            return
        canvas.create_rectangle(x0 - x, y0 - y, x1 - x, y1 - y,
                                fill=fill, outline='', width=0, tags=(tag,))

    # Zócalo mate. La transición superior e inferior se integra en TODA la
    # ventana; no arranca en x=sidebar+2, que en V413 dejaba una línea brillante.
    deck = _blend(bg, surface, .32)
    step = 10
    start_row = max(0, (y // step) * step)
    stop_row = min(full_height, y + height + step)
    for yy in range(start_row, stop_row, step):
        rel = yy / max(1, full_height)
        masthead = .035 * (max(0., 1. - yy / 275.) ** 2.1)
        # Una presencia azul tenue bajo las tarjetas, más pronunciada abajo.
        lower = .065 * (max(0., (rel - .43) / .57) ** 1.8)
        strength = .025 + masthead + lower
        tone = _blend(deck, accent, strength)
        rectangle(0, yy, full_width, min(full_height, yy + step), tone)

    # Luz ambiental lateral con caída suave. Empieza DESPUÉS de la unión con el
    # sidebar; no hay un panel extra, rail, contorno ni banda vertical.
    # Sólo ocupa el área superior: no cruza los módulos ni genera fragmentos.
    wash_top, wash_bottom = 0, min(215, full_height)
    col_step = 24
    row_step = 10
    first_x = max(workspace_left + 32, 0)
    for yy in range(max(wash_top, (y // row_step) * row_step),
                    min(wash_bottom, y + height + row_step), row_step):
        vertical = max(0., 1. - yy / max(1, wash_bottom)) ** 1.65
        if vertical < .003:
            continue
        # Recalcula el tono equivalente de la capa mate para dibujar una
        # composición idéntica tanto en el Canvas maestro como en wrappers.
        band_y = (yy // step) * step
        band_rel = band_y / max(1, full_height)
        baseline = _blend(deck, accent,
                          .025 + .035 * (max(0., 1. - band_y / 275.) ** 2.1)
                          + .065 * (max(0., (band_rel - .43) / .57) ** 1.8))
        start_col = first_x + max(0, (x - first_x) // col_step) * col_step
        for xx in range(start_col, min(full_width, x + width), col_step):
            distance = max(0., (xx + col_step / 2. - workspace_left - 32.) / 260.)
            entrance = min(1., distance) ** 1.7
            if entrance < .01:
                continue
            # Saturación moderada, sin neones ni bordes cromáticos artificiales.
            light = .255 * vertical * entrance
            tone = _blend(baseline, accent, light)
            rectangle(xx, yy, min(full_width, xx + col_step),
                      min(wash_bottom, yy + row_step), tone)


@lru_cache(maxsize=2)
def _workspace_bitmap(width, height, palette, workspace_left):
    """Un fondo calculado por tamaño y tema, compartido por todos los controles."""
    bitmap = Image.new('RGB', (width, height), palette[0])
    drawing = ImageDraw.Draw(bitmap)
    class Painter:
        def delete(self, _tag):
            pass
        def find_withtag(self, _tag):
            return ()
        def create_rectangle(self, x0, y0, x1, y1, *, fill, **_kwargs):
            drawing.rectangle((x0, y0, x1 - 1, y1 - 1), fill=fill)
    _render_workspace_vectors(Painter(), x=0, y=0, width=width, height=height,
                              full_width=width, full_height=height, palette=palette,
                              workspace_left=workspace_left, tag='surface')
    return bitmap


def render_native_workspace(canvas, *, x, y, width, height, full_width, full_height,
                            palette, tag, workspace_left=None):
    """Reutiliza una imagen en memoria en lugar de miles de rectángulos Tk."""
    x, y, width, height = map(int, (x, y, width, height))
    full_width, full_height = int(full_width), int(full_height)
    palette = tuple(palette)
    signature = (x, y, width, height, full_width, full_height, palette, workspace_left)
    cache = getattr(canvas, '_cp_workspace_render_cache', None)
    if cache is None:
        cache = canvas._cp_workspace_render_cache = {}
    if cache.get(tag) == signature and canvas.find_withtag(tag):
        return False
    canvas.delete(tag)
    cache[tag] = signature
    images = getattr(canvas, '_cp_workspace_images', None)
    if images is None:
        images = canvas._cp_workspace_images = {}
    images.pop(tag, None)
    if min(width, height, full_width, full_height) <= 0:
        return False
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(full_width, x + width), min(full_height, y + height)
    if x1 <= x0 or y1 <= y0:
        return False
    bitmap = _workspace_bitmap(full_width, full_height, palette, workspace_left)
    photo = ImageTk.PhotoImage(bitmap.crop((x0, y0, x1, y1)), master=canvas)
    images[tag] = photo
    canvas.create_image(x0 - x, y0 - y, image=photo, anchor='nw', tags=(tag,))
    return True


def native_surface_color_at(x, y, full_width, full_height, *, palette, workspace_left):
    """Color real del Surface Studio en coordenadas de la ventana (V425).

    Es el mismo cálculo que `render_native_workspace`, incluyendo las bandas
    verticales de 10 px. Los controles del sidebar lo necesitan porque CTk
    dibuja colores propios incluso con fg_color='transparent'.
    """
    if min(full_width, full_height) <= 0:
        return palette[0]
    bg, surface, _border, accent = palette
    deck = _blend(bg, surface, .32)
    band_y = max(0, min(int(y), int(full_height)-1)) // 10 * 10
    rel = band_y / max(1, full_height)
    masthead = .035 * (max(0., 1. - band_y / 275.) ** 2.1)
    lower = .065 * (max(0., (rel - .43) / .57) ** 1.8)
    baseline = _blend(deck, accent, .025 + masthead + lower)

    # El sidebar normalmente no entra en la iluminación superior, pero se
    # mantiene también ese tratamiento por compatibilidad con el colapso.
    wash_bottom = min(215, int(full_height))
    first_x = max(0, int(workspace_left) + 32)
    if not (0 <= band_y < wash_bottom and int(x) >= first_x):
        return baseline
    vertical = max(0., 1. - band_y / max(1, wash_bottom)) ** 1.65
    if vertical < .003:
        return baseline
    cell_x = first_x + ((int(x)-first_x)//24)*24
    distance = max(0., (cell_x + 12. - int(workspace_left) - 32.) / 260.)
    entrance = min(1., distance) ** 1.7
    if entrance < .01:
        return baseline
    return _blend(baseline, accent, .255 * vertical * entrance)


_SIDEBAR_CONTROL_TAG = '_corepulse_sidebar_native_control'



class WorkspaceBackground:
    """Autoridad de diseño compartida por Resumen y páginas internas."""

    def __init__(self, parent):
        self.parent = parent
        self._after_id = None
        self._last_size = (0, 0)
        self._palette_last = None
        self._workspace_left = None
        self._surfaces = set()
        self._canvases = set()
        self._native_cards = set()  # Superficies integradas del resumen.
        self._flat_pages = set()

        # Lienzo maestro real: 100% UI nativa, sin ImageTk y sin archivos PNG.
        self.label = tk.Canvas(parent, bd=0, highlightthickness=0, takefocus=0)
        self.label.place(x=0, y=0, relwidth=1, relheight=1)
        self.label.bind('<Configure>', self._on_configure, add='+')
        self._page_map_binding = parent.bind('<Map>', self._on_page_map, add='+')
        self._restack()
        self.refresh(force=True)

    def _on_configure(self, _event=None):
        self.schedule_refresh()

    def schedule_refresh(self):
        try:
            if self._after_id is not None:
                return
            self._after_id = self.label.after(50, self.refresh)
        except (tk.TclError, AttributeError):
            self._after_id = None

    def _restack(self):
        """Dibujo maestro detrás de los widgets reales, sobre la raíz CTk."""
        try:
            base = getattr(self.parent, '_canvas', None)
            if base is not None:
                self.label.tk.call('raise', self.label._w, base._w)
            else:
                self.label.lower()
        except (tk.TclError, AttributeError):
            pass
        try:
            base = getattr(self.parent, '_canvas', None)
            for child in self.parent.winfo_children():
                if child is self.label or child is base:
                    continue
                child.tkraise()
        except (tk.TclError, AttributeError):
            pass

    def _attach(self, frame):
        if frame is None or frame is self.parent or getattr(frame, '_canvas', None) is None:
            return False
        if frame not in self._surfaces:
            self._surfaces.add(frame)
            try:
                frame.bind('<Configure>', self._on_configure, add='+')
            except (tk.TclError, AttributeError):
                pass
        return True

    def register_surface(self, frame):
        """Registra únicamente contenedores estructurales transparentes."""
        if self._attach(frame):
            self.schedule_refresh()
            return True
        return False

    def register_native_card(self, card):
        """Registra la tarjeta para pintar exactamente su área del fondo maestro."""
        if card is None or getattr(card, '_canvas', None) is None:
            return False
        if card not in self._native_cards:
            self._native_cards.add(card)
            try:
                card.bind('<Configure>', self._on_configure, add='+')
            except (tk.TclError, AttributeError):
                pass
            self.schedule_refresh()
        return True

    def register_canvas(self, canvas):
        """Permite al encabezado pintar logo y nombre sin recuadros opacos."""
        if not isinstance(canvas, tk.Canvas):
            return False
        if canvas not in self._canvases:
            self._canvases.add(canvas)
            try:
                canvas.bind('<Configure>', self._on_configure, add='+')
            except tk.TclError:
                pass
        self.schedule_refresh()
        return True

    @staticmethod
    def _is_structural(frame):
        if getattr(frame, '_canvas', None) is None or type(frame).__name__ == 'CTkScrollableFrame':
            return False
        try:
            color = frame.cget('fg_color')
            if isinstance(color, (tuple, list)):
                color = color[0] if color else ''
            color = str(color or '').lower()
            border = int(frame.cget('border_width'))
            radius = int(frame.cget('corner_radius'))
            return not border and (color == 'transparent' or (color in _WORKSPACE_FLAT_COLORS and not radius))
        except (tk.TclError, AttributeError, TypeError, ValueError):
            return False

    def register_page(self, page_root, max_depth=3):
        """Propaga composición únicamente a wrappers, sin ingresar en tarjetas."""
        if page_root is None:
            return
        stack = [(page_root, 0)]
        while stack:
            widget, depth = stack.pop()
            if not self._is_structural(widget):
                continue
            self._attach(widget)
            if depth >= max_depth:
                continue
            try:
                children = list(widget.winfo_children())
            except (tk.TclError, AttributeError):
                children = []
            for child in children:
                if getattr(child, '_canvas', None) is not None:
                    stack.append((child, depth + 1))
        self.schedule_refresh()

    def _on_page_map(self, event):
        widget = getattr(event, 'widget', None)
        while widget is not None and widget is not self.parent:
            if widget in self._flat_pages:
                self.schedule_refresh()
                return
            widget = getattr(widget, 'master', None)

    def register_flat_page(self, page_root):
        if page_root is None:
            return
        if page_root in self._flat_pages:
            self.schedule_refresh()
            return
        ancestor = getattr(page_root, 'master', None)
        while ancestor is not None and ancestor is not self.parent:
            if ancestor in self._flat_pages:
                self.schedule_refresh()
                return
            ancestor = getattr(ancestor, 'master', None)
        self._flat_pages.add(page_root)
        from gui.flat_workspace_page import prepare_flat_page
        prepare_flat_page(page_root, self)
        self.schedule_refresh()

    def _covered_by_page(self, widget):
        host = getattr(self.parent, '_internal_page_host', None)
        main = getattr(self.parent, 'main_content', None)
        if not getattr(self.parent, '_active_internal_page', None) or host is None or widget is main:
            return False
        current = widget
        while current is not None and current is not self.parent:
            if current is host:
                return False
            if current is main:
                return True
            current = getattr(current, 'master', None)
        return False

    def _workspace_origin(self, total_width):
        """X real del área central; acompaña sidebar abierto/cerrado."""
        try:
            main = getattr(self.parent, 'main_content', None)
            if main is not None and main.winfo_exists() and main.winfo_ismapped():
                xx = main.winfo_rootx() - self.parent.winfo_rootx()
                if 0 <= xx < total_width - 160:
                    return int(xx)
        except (tk.TclError, AttributeError):
            pass
        return int(total_width * .205)

    def _paint(self, canvas, *, tag, top=False):
        if not canvas.winfo_exists() or not canvas.winfo_ismapped():
            return
        w, h = int(canvas.winfo_width()), int(canvas.winfo_height())
        if w < 20 or h < 20:
            return
        x = canvas.winfo_rootx() - self.parent.winfo_rootx()
        y = canvas.winfo_rooty() - self.parent.winfo_rooty()
        bw, bh = self._last_size
        if x <= -w or y <= -h or x >= bw or y >= bh:
            return
        render_native_workspace(canvas, x=x, y=y, width=w, height=h,
                                full_width=bw, full_height=bh,
                                palette=self._palette_last, tag=tag,
                                workspace_left=self._workspace_left)
        if top:
            canvas.tag_raise(tag)  # Transparencia simulada sobre CTkFrame.
        else:
            canvas.tag_lower(tag)  # Identidad del notebook por encima.

    def refresh(self, force=False):
        self._after_id = None
        try:
            w, h = int(self.parent.winfo_width()), int(self.parent.winfo_height())
        except (tk.TclError, AttributeError):
            return False
        if w < 40 or h < 40:
            try:
                self._after_id = self.label.after(100, self.refresh)
            except tk.TclError:
                pass
            return False
        palette = _palette()
        self._last_size = (w, h)
        self._palette_last = palette
        self._workspace_left = self._workspace_origin(w)
        self._restack()
        render_native_workspace(self.label, x=0, y=0, width=w, height=h,
                                full_width=w, full_height=h,
                                palette=palette, tag=_DESIGN_TAG,
                                workspace_left=self._workspace_left)
        for frame in tuple(self._surfaces):
            try:
                if not frame.winfo_exists():
                    self._surfaces.discard(frame)
                    continue
                if self._covered_by_page(frame):
                    continue
                if self._is_structural(frame):
                    self._paint(frame._canvas, tag=_DESIGN_TAG, top=True)
                else:
                    frame._canvas.delete(_DESIGN_TAG)
                    self._surfaces.discard(frame)
            except (tk.TclError, AttributeError, ValueError):
                self._surfaces.discard(frame)
        for canvas in tuple(self._canvases):
            try:
                if not canvas.winfo_exists():
                    self._canvases.discard(canvas)
                    continue
                if not self._covered_by_page(canvas):
                    self._paint(canvas, tag=_CANVAS_DESIGN_TAG)
            except (tk.TclError, AttributeError, ValueError):
                self._canvases.discard(canvas)
        # V436: el mismo render de la capa maestra llega a los módulos
        # sobrepuestos; no se usa un color sólido muestreado al centro.
        from gui.card_workspace_surface import paint_native_card_surface
        for card in tuple(self._native_cards):
            try:
                if not card.winfo_exists():
                    self._native_cards.discard(card)
                    continue
                if self._covered_by_page(card):
                    continue
                paint_native_card_surface(
                    card, parent=self.parent, palette=palette,
                    width=w, height=h, workspace_left=self._workspace_left,
                )
            except (tk.TclError, AttributeError, ValueError, TypeError):
                self._native_cards.discard(card)
        from gui.flat_workspace_page import paint_flat_page
        for page in tuple(self._flat_pages):
            if not page.winfo_exists():
                self._flat_pages.discard(page)
            elif page.winfo_ismapped() and not self._covered_by_page(page):
                paint_flat_page(page, self)
        self._paint_sidebar_controls()
        return True

    def _paint_sidebar_controls(self):
        """Compatibilidad: repinta todas las opciones en refresh general."""
        return self._paint_sidebar_controls_target()

    def _paint_sidebar_controls_target(self, target=None):
        """V425: integra botones/etiquetas a la misma capa nativa.

        A diferencia de los CTkFrame, cada CTkButton y CTkLabel tiene un
        Canvas/Label interno que CTk rellena de negro/azul sólido al usar
        `transparent`. No se crean controles nuevos ni se alteran comandos.
        Se repinta sólo el sustrato de los inactivos, respetando la selección
        azul y los indicadores de navegación.
        """
        glyph = getattr(self.parent, '_sidebar_reopen_button', None) if target is None else None
        try:
            if glyph is not None and glyph.winfo_exists() and glyph.winfo_ismapped():
                x = glyph.winfo_rootx() - self.parent.winfo_rootx()
                y = glyph.winfo_rooty() - self.parent.winfo_rooty()
                canvas = getattr(glyph, '_canvas', None)
                if canvas is not None and canvas.winfo_exists() and x >= -10 and y >= -10:
                    color = native_surface_color_at(
                        x + max(1, glyph.winfo_width() // 2),
                        y + max(1, glyph.winfo_height() // 2),
                        *self._last_size, palette=self._palette_last,
                        workspace_left=self._workspace_left,
                    )
                    glyph.configure(fg_color=color, bg_color=color)
                    self._paint(canvas, tag=_SIDEBAR_CONTROL_TAG, top=True)
                    label = getattr(glyph, '_text_label', None)
                    if label is not None and label.winfo_exists() and str(label.cget('bg')).lower() != color.lower():
                        label.configure(bg=color)
        except (tk.TclError, AttributeError, ValueError, TypeError):
            pass

        sidebar = getattr(self.parent, 'sidebar', None)
        if sidebar is None or not sidebar.winfo_exists() or not sidebar.winfo_ismapped():
            return

        stack = [sidebar]
        while stack:
            container = stack.pop()
            try:
                children = tuple(container.winfo_children())
            except (tk.TclError, AttributeError):
                continue
            for child in children:
                if target is not None and child is not target and type(child).__name__ != 'CTkFrame':
                    continue  # V456: durante un frame de animación solo se pinta ESTE botón.
                kind = type(child).__name__
                if kind == 'CTkFrame':
                    # Sólo descendemos por wrappers internos del propio menú.
                    stack.append(child)
                    continue
                if kind not in ('CTkButton', 'CTkLabel'):
                    continue
                try:
                    if not child.winfo_exists() or not child.winfo_ismapped():
                        continue
                    x = child.winfo_rootx() - self.parent.winfo_rootx()
                    y = child.winfo_rooty() - self.parent.winfo_rooty()
                    if x < -10 or y < -10:
                        continue
                    canvas = getattr(child, '_canvas', None)
                    if canvas is None or not canvas.winfo_exists():
                        continue

                    color = native_surface_color_at(
                        x+max(1, child.winfo_width()//2),
                        y+max(1, child.winfo_height()//2),
                        *self._last_size,
                        palette=self._palette_last,
                        workspace_left=self._workspace_left,
                    )
                    active = False
                    hovered = kind == 'CTkButton' and bool(getattr(child, '_cp_sidebar_hovered', False))
                    motion = 0.0
                    if kind == 'CTkButton':
                        try:
                            motion = max(0., min(1., float(getattr(child, '_cp_sidebar_hover_progress', 0.))))
                        except (TypeError, ValueError):
                            pass
                    label_bg = color
                    if kind == 'CTkButton':
                        current = str(child.cget('fg_color') or '').lower()
                        previous = str(getattr(child, '_cp_sidebar_last_flat_color', '')).lower()
                        active = current not in ('transparent', previous, '')
                        if motion > 0.0:
                            # V456: transicion progresiva SOBRE EL MISMO CTkButton.
                            # Se interpola la tonalidad desde el fondo maestro
                            # hasta el hover. No se crean rectangulos ni overlays.
                            child._cp_sidebar_last_flat_color = color
                            accent = self._palette_last[3]
                            selected = bool(getattr(child, '_cp_sidebar_hover_selected', False))
                            base = role_color('accent_soft') if selected else color
                            label_bg = _blend(base, accent, (.29 if selected else .23) * motion)
                            if (current != label_bg.lower()
                                    or str(child.cget('bg_color')).lower() != color.lower()
                                    or str(child.cget('hover_color')).lower() != label_bg.lower()):
                                child.configure(fg_color=label_bg, bg_color=color, hover_color=label_bg)
                        elif not active:
                            child._cp_sidebar_last_flat_color = color
                            # El control sin hover reproduce el fondo absoluto
                            # del workspace en vez de imponer una tarjeta sólida.
                            if (current != color.lower()
                                    or str(child.cget('bg_color')).lower() != color.lower()
                                    or str(child.cget('hover_color')).lower() != color.lower()):
                                child.configure(fg_color=color, bg_color=color, hover_color=color)
                        elif str(child.cget('bg_color')).lower() != color.lower():
                            child.configure(bg_color=color)
                    else:
                        if str(child.cget('fg_color')).lower() != color.lower() or str(child.cget('bg_color')).lower() != color.lower():
                            child.configure(fg_color=color, bg_color=color)

                    # En hover/selección el CTkButton pinta su propia pastilla;
                    # el bitmap plano sólo debe existir durante el estado neutro.
                    if active:
                        canvas.delete(_SIDEBAR_CONTROL_TAG)
                    elif motion > 0.0:
                        canvas.delete(_SIDEBAR_CONTROL_TAG)
                    else:
                        self._paint(canvas, tag=_SIDEBAR_CONTROL_TAG, top=True)

                    # CTk tiene tk.Label separados para texto/imagen. Su fondo
                    # también debe acompañar al hover para evitar huecos oscuros.
                    if not active or motion > 0.0:
                        for attr in ('_text_label', '_image_label'):
                            label = getattr(child, attr, None)
                            if label is not None and label.winfo_exists():
                                try:
                                    if str(label.cget('bg')).lower() != label_bg.lower():
                                        label.configure(bg=label_bg)
                                except (tk.TclError, AttributeError):
                                    pass
                except (tk.TclError, AttributeError, ValueError, TypeError):
                    continue

    def destroy(self):
        try:
            if self._after_id is not None:
                self.label.after_cancel(self._after_id)
            for frame in tuple(self._surfaces):
                if frame.winfo_exists():
                    frame._canvas.delete(_DESIGN_TAG)
            for canvas in tuple(self._canvases):
                if canvas.winfo_exists():
                    canvas.delete(_CANVAS_DESIGN_TAG)
            self._surfaces.clear()
            self._canvases.clear()
            self._native_cards.clear()
            self._flat_pages.clear()
            if self._page_map_binding:
                self.parent.unbind('<Map>', self._page_map_binding)
            self.label.destroy()
        except (tk.TclError, AttributeError):
            pass


def install_workspace_background(parent):
    """Idempotente: una sola capa maestra por ventana del producto."""
    if parent is None:
        return None
    existing = getattr(parent, '_corepulse_workspace_background', None)
    if existing is not None:
        try:
            if existing.label.winfo_exists():
                return existing
        except (tk.TclError, AttributeError):
            pass
    workspace = WorkspaceBackground(parent)
    parent._corepulse_workspace_background = workspace
    return workspace


def prepare_workspace_page(widget):
    """Conserva los módulos originales y expone la capa nativa bajo el host."""
    if widget is None:
        return False
    try:
        color = widget.cget('fg_color')
        if isinstance(color, (tuple, list)):
            color = color[0] if color else ''
        if str(color or '').lower() in _WORKSPACE_FLAT_COLORS and not int(widget.cget('border_width')):
            widget.configure(fg_color='transparent', corner_radius=0)
        controller = getattr(widget.winfo_toplevel(), '_corepulse_workspace_background', None)
        if controller is not None:
            controller.register_flat_page(widget)
            return True
    except (tk.TclError, AttributeError):
        pass
    return False
