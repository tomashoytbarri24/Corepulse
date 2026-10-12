"""Hover animado, ligero y reversible del sidebar sobre la superficie original.

V456: anima 5 px el contenido (icono y texto) y desvanece el resaltado.
No mueve el CTkButton, no añade widgets/capas, no cambia comandos ni navegación.
Cada botón tiene como máximo un after() activo; se cancela al invertir el gesto.
"""
from __future__ import annotations

import time
import tkinter as tk

FRAME_MS = 16
ENTER_SECONDS = .145
LEAVE_SECONDS = .105
LEAVE_DEBOUNCE_MS = 36
CONTENT_SHIFT_PX = 5


def _repaint(app, button=None):
    controller = getattr(app, 'workspace_background', None)
    if controller is not None:
        try:
            controller._paint_sidebar_controls_target(button) if button is not None else controller._paint_sidebar_controls()
        except (AttributeError, ValueError, tk.TclError):
            pass


def _current_selected(app, attr):
    # La navegación real siempre prevalece sobre la selección al entrar.
    from gui.ui_consistency import CONTEXT_BUTTON
    context = str(getattr(app, '_navigation_context', 'dashboard') or 'dashboard').lower()
    return CONTEXT_BUTTON.get(context, '_btn_summary') == attr


def _padding_pair(value):
    """Normaliza la representación que devuelve grid_info() según Tcl/Tk."""
    if isinstance(value, (tuple, list)):
        parts = list(value)
    elif isinstance(value, str):
        parts = value.strip().replace('{', '').replace('}', '').split()
    else:
        parts = [value]
    try:
        left = int(float(parts[0])) if parts else 0
        right = int(float(parts[1])) if len(parts) > 1 else left
        return (left, right)
    except (ValueError, TypeError):
        return (0, 0)


def _motion_targets(button):
    """Usa SOLO los controles internos que ya pertenecen al CTkButton."""
    targets = []
    for name in ('_image_label', '_text_label'):
        label = getattr(button, name, None)
        if label is None:
            continue
        try:
            if not label.winfo_exists():
                continue
            manager = label.winfo_manager()
            if manager == 'grid':
                info = label.grid_info()
                targets.append((label, 'grid', _padding_pair(info.get('padx', (0, 0)))))
            elif manager == 'place':
                # Solo para controles con disposición place; CTk usa grid.
                targets.append((label, 'place', float(label.place_info().get('x', 0))))
        except (ValueError, AttributeError, tk.TclError):
            continue
    return targets


def _shift_content(app, button, state, progress):
    """El desplazamiento nunca modifica ancho/alto del botón ni sus vecinos."""
    progress = max(0., min(1., float(progress)))
    if getattr(app, '_sidebar_collapsed', False):
        progress = 0.
    offset = int(round(CONTENT_SHIFT_PX * progress))
    if state.get('offset') == offset:
        return
    targets = state.get('targets')
    if targets is None:
        targets = state['targets'] = _motion_targets(button)
    for label, manager, base in targets:
        try:
            if not label.winfo_exists() or label.winfo_manager() != manager:
                continue
            if manager == 'grid':
                # Unicamente aumenta el margen interno del propio icono/texto:
                # nunca el padding del boton ni la geometria de sus vecinos.
                left, right = base
                label.grid_configure(padx=(left + offset, right))
            else:
                label.place_configure(x=base + offset)
        except (ValueError, AttributeError, tk.TclError):
            continue
    state['offset'] = offset


def install_native_sidebar_hover(app, labels):
    """Instalación idempotente sobre TODAS las entradas, incluida Personalización."""
    for attr in labels:
        button = getattr(app, attr, None)
        if button is None or getattr(button, '_cp_sidebar_hover_installed', False):
            continue
        _bind_native_hover(app, attr, button)


def _bind_native_hover(app, attr, button):
    state = {
        'pending': None, 'animation': None, 'progress': 0.,
        'offset': None, 'targets': None, 'started': 0.,
        'start': 0., 'target': 0., 'duration': ENTER_SECONDS,
    }
    button._cp_sidebar_hover_installed = True
    button._cp_sidebar_hovered = False
    button._cp_sidebar_hover_progress = 0.
    button._cp_sidebar_motion_state = state

    def cancel(name):
        task = state.get(name)
        if task is not None:
            try:
                button.after_cancel(task)
            except (ValueError, AttributeError, tk.TclError):
                pass
            state[name] = None

    def pointer_inside():
        try:
            x, y = button.winfo_pointerxy()
            return (button.winfo_rootx() <= x < button.winfo_rootx() + button.winfo_width()
                    and button.winfo_rooty() <= y < button.winfo_rooty() + button.winfo_height())
        except (ValueError, AttributeError, tk.TclError):
            return False

    def render(value):
        value = max(0., min(1., value))
        state['progress'] = value
        button._cp_sidebar_hover_progress = value
        _shift_content(app, button, state, value)
        _repaint(app, button)

    def tick():
        state['animation'] = None
        try:
            if not button.winfo_exists():
                return
            dt = max(0., time.monotonic() - state['started'])
            t = min(1., dt / max(.001, state['duration']))
            eased = 1. - (1. - t) ** 3  # salida suave sin sobrepasarse
            value = state['start'] + (state['target'] - state['start']) * eased
            render(value)
            if t < 1.:
                state['animation'] = button.after(FRAME_MS, tick)
            else:
                finish()
        except (ValueError, AttributeError, tk.TclError):
            cancel('animation')

    def finish():
        if state['target'] > 0.:
            return
        try:
            # Devolver el fondo neutro ANTES del siguiente repintado maestro.
            # Es fundamental: de otro modo el tono del último frame se confunde
            # con una selección persistente al abandonar el botón.
            if _current_selected(app, attr):
                from core.theme_manager import role_color
                button.configure(fg_color=role_color('accent_soft'))
            else:
                button.configure(fg_color='transparent')
            _repaint(app, button)
            # La siguiente animación debe partir de la geometría REAL, que puede
            # haber cambiado por DPI, tema, ancho del sidebar o CustomTkinter.
            state['targets'] = None
        except (ValueError, AttributeError, tk.TclError):
            pass

    def animate(target):
        cancel('animation')
        state['start'] = state['progress']
        state['target'] = float(target)
        state['duration'] = ((ENTER_SECONDS if target else LEAVE_SECONDS)
                             * max(.25, abs(float(target) - state['progress'])))
        state['started'] = time.monotonic()
        # Mostrar reacción en este mismo evento, no 16 ms después.
        if target and not state['progress']:
            render(.055)
            state['start'] = .055
        if state['start'] == state['target']:
            render(state['target'])
            if not target:
                finish()
            return
        state['animation'] = button.after(FRAME_MS, tick)

    def force_leave():
        """Otro botón recibió el puntero: evita hovers acumulados."""
        cancel('pending')
        button._cp_sidebar_hovered = False
        button._cp_sidebar_hover_selected = _current_selected(app, attr)
        animate(0.)

    button._cp_sidebar_force_leave = force_leave

    def enter(_event=None):
        cancel('pending')
        try:
            if str(button.cget('state')).lower() == 'disabled':
                return
            previous = getattr(app, '_cp_sidebar_hover_owner', None)
            if previous is not None and previous is not button:
                exit_previous = getattr(previous, '_cp_sidebar_force_leave', None)
                if callable(exit_previous):
                    exit_previous()
            app._cp_sidebar_hover_owner = button
            button._cp_sidebar_hover_selected = _current_selected(app, attr)
            button._cp_sidebar_hovered = True
            animate(1.)
        except (ValueError, AttributeError, tk.TclError):
            pass

    def finalize_leave():
        state['pending'] = None
        try:
            if not button.winfo_exists() or pointer_inside():
                return
            if getattr(app, '_cp_sidebar_hover_owner', None) is button:
                app._cp_sidebar_hover_owner = None
            force_leave()
        except (ValueError, AttributeError, tk.TclError):
            pass

    def leave(_event=None):
        cancel('pending')
        try:
            # Debounce corto al cruzar etiquetas internas de CTk.
            state['pending'] = button.after(LEAVE_DEBOUNCE_MS, finalize_leave)
        except (ValueError, AttributeError, tk.TclError):
            finalize_leave()

    def cleanup(_event=None):
        cancel('pending')
        cancel('animation')
        if getattr(app, '_cp_sidebar_hover_owner', None) is button:
            app._cp_sidebar_hover_owner = None
        state['targets'] = None

    try:
        button.configure(cursor='hand2', hover=False)
        button.bind('<Enter>', enter, add='+')
        button.bind('<Leave>', leave, add='+')
        button.bind('<Destroy>', cleanup, add='+')
    except (ValueError, AttributeError, tk.TclError):
        button._cp_sidebar_hover_installed = False
