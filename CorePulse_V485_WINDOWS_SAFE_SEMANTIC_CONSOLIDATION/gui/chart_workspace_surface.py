"""V434: integra el lienzo Matplotlib en el fondo maestro de CorePulse.

La figura de Matplotlib es opaca por diseño: `fg_color='transparent'` no
alcanza para que el Figure muestre el workspace Tk. Esta capa reconstruye
exactamente la tonalidad de la superficie nativa en las coordenadas locales
ocupadas por el lienzo y la dibuja DEBAJO de los ejes, sin tocar las curvas.

No modifica datos, telemetría, ni la geometría de los ejes.
"""
from __future__ import annotations

import numpy as np

from gui.workspace_background import _palette, native_surface_color_at


def sampled_workspace_background(width, height, *, x, y, root_width, root_height,
                                  palette, workspace_left):
    """Matriz RGB de la capa maestra detrás de la figura Matplotlib.

    No hay iluminación X en la zona baja (donde aparecen los gráficos), pero
    se muestrea por columnas también si el bloque llega a ocupar el header.
    El cálculo se comparte con el sidebar aprobado en V425.
    """
    w, h = int(width), int(height)
    if w < 1 or h < 1:
        raise ValueError('Las dimensiones del lienzo deben ser positivas')
    out = np.empty((h, w, 3), dtype=np.uint8)
    palette = tuple(palette)
    left = int(workspace_left)
    root_w, root_h = int(root_width), int(root_height)
    if int(y) >= 215:
        # Para las posiciones normales de los gráficos no hay iluminación X;
        # los colores sólo varían en bandas verticales de 10 px.
        for row in range(h):
            c = native_surface_color_at(int(x), int(y) + row, root_w, root_h,
                                        palette=palette, workspace_left=left)
            rgb = tuple(int(c[i:i+2], 16) for i in (1, 3, 5))
            out[row, :] = rgb
    else:
        for row in range(h):
            for col in range(w):
                c = native_surface_color_at(int(x) + col, int(y) + row, root_w, root_h,
                                            palette=palette, workspace_left=left)
                out[row, col] = tuple(int(c[i:i+2], 16) for i in (1, 3, 5))
    return out



def ensure_seamless_chart_axes(app):
    """V444: tres gráficos sobre UNA sola capa, sin fondos o bordes propios.

    Es idempotente; no modifica datos, curvas, escalas, etiquetas ni geometría.
    Matplotlib conserva el eje y la grilla, pero el parche opaco de cada Axes
    deja visible la imagen del fondo maestro dibujada por la figura.
    """
    changed = False
    for name in ('ax_cpu', 'ax_ram', 'ax_gpu'):
        ax = getattr(app, name, None)
        if ax is None:
            continue
        try:
            ax.set_facecolor('none')
            for spine in ax.spines.values():
                spine.set_visible(False)
            # La línea de grilla en 100% coincide con el borde superior y
            # visualmente reconstruye un cuadro. Las referencias 25/50/75
            # permanecen para conservar lectura de la telemetría.
            for y, gridline in zip(ax.get_yticks(), ax.yaxis.get_gridlines()):
                gridline.set_visible(abs(float(y) - 100.0) > 1e-7)
            changed = True
        except (AttributeError, TypeError, ValueError):
            continue
    return changed


def sync_chart_workspace_surface(app):
    """Sincroniza el fondo del Figure con la superficie real en pantalla.

    Se invoca en el estilizado general y al hacer reflow; NO en el loop de
    muestras de telemetría. Mantiene una sola imagen de fondo por figura.
    """
    fig = getattr(app, 'fig', None)
    canvas = getattr(app, 'canvas', None)
    if fig is None or canvas is None:
        return False
    # Debe ejecutarse incluso con firma de fondo sin cambios: otros estilos
    # del dashboard pueden volver a configurar el aspecto del Axes.
    ensure_seamless_chart_axes(app)
    try:
        widget = canvas.get_tk_widget()
        root = app
        if not widget.winfo_exists() or not root.winfo_exists():
            return False
        figure_width = max(1, int(round(fig.bbox.width)))
        figure_height = max(1, int(round(fig.bbox.height)))
        if figure_width < 50 or figure_height < 50:
            return False
        root_width = max(1, int(root.winfo_width()))
        root_height = max(1, int(root.winfo_height()))
        x = int(widget.winfo_rootx() - root.winfo_rootx())
        y = int(widget.winfo_rooty() - root.winfo_rooty())
        workspace = getattr(app, 'workspace_background', None)
        # Consultar los roles ACTUALES: en un cambio de tema, el lienzo
        # puede refrescarse antes que WorkspaceBackground._palette_last.
        palette = _palette()
        main = getattr(app, 'main_content', None)
        if main is not None and main.winfo_exists() and main.winfo_ismapped():
            workspace_left = int(main.winfo_rootx() - root.winfo_rootx())
        else:
            workspace_left = (getattr(workspace, '_workspace_left', None)
                              if workspace is not None else None)
            if workspace_left is None:
                workspace_left = int(root_width * .205)
        signature = (figure_width, figure_height, x, y, root_width, root_height,
                     tuple(palette), int(workspace_left))
        background = getattr(app, '_chart_workspace_image', None)
        if signature == getattr(app, '_chart_workspace_signature', None) and background is not None:
            return True

        arr = sampled_workspace_background(
            figure_width, figure_height, x=x, y=y,
            root_width=root_width, root_height=root_height,
            palette=palette, workspace_left=workspace_left,
        )
        # origin='upper' corresponde a la fila 0 arriba de la pantalla.
        if background is not None and background in fig.images:
            background.set_data(arr)
        else:
            # figimage: zorder negativo = capa baja, antes que los ejes.
            background = fig.figimage(arr, xo=0, yo=0, origin='upper', zorder=-100)
            app._chart_workspace_image = background
        fig.patch.set_facecolor(tuple(arr[0, 0] / 255.0))
        fig.patch.set_edgecolor('none')
        fig.patch.set_linewidth(0)
        fig.set_frameon(True)
        widget.configure(bg='#%02x%02x%02x' % tuple(arr[0, 0]),
                         bd=0, highlightthickness=0, relief='flat')
        app._chart_workspace_signature = signature
        app.background = None  # Invalida el blitting al cambiar el fondo.
        return True
    except (AttributeError, ValueError, TypeError, RuntimeError):
        return False
