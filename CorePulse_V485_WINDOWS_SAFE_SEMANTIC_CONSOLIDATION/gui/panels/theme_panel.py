"""Galería interna de temas de CorePulse (V361)."""
from __future__ import annotations

import customtkinter as ctk

from core.theme_manager import (
    get_theme,
    get_theme_profiles,
    preview_color,
    apply_theme_live,
    set_theme,
)

FONT = 'Segoe UI'


class ThemePanel:
    """Selector de temas embebido; nunca crea una Toplevel."""

    def __init__(self, app, parent):
        self.app = app
        self.parent = parent
        self._alive = True
        self.profiles = get_theme_profiles()
        self.selected_theme = get_theme()
        self._theme_buttons = {}
        self._preview_widgets = {}

        # La galería nace con la paleta exacta para evitar grises heredados
        # durante el primer render y al cambiar la previsualización.
        current = self.profiles.get(get_theme(), self.profiles['corepulse'])
        self._initial_palette = dict(current)
        self.root = ctk.CTkFrame(parent, fg_color=current['bg'], corner_radius=0)
        self.root.pack(fill='both', expand=True)
        self.root.grid_columnconfigure(0, minsize=290, weight=0)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_picker()
        self._build_preview()
        self._select(self.selected_theme)

    def widget(self):
        return self.root

    def set_active(self, active=True):
        self._alive = bool(active)

    def _build_header(self):
        p = self._initial_palette
        header = ctk.CTkFrame(self.root, fg_color=p['bg'], height=76)
        self.header = header
        # V440 · Cabecera superior eliminada por solicitud: sin título,
        # subtítulo, etiquetas ni zona reservada. Las referencias de
        # estado siguen vivas pero no se dibujan.
        # Sin grid(): el contenido funcional comienza arriba.
        header.grid_columnconfigure(0, weight=1)
        self.title = ctk.CTkLabel(header, text='Temas', font=(FONT, 24, 'bold'), anchor='w')
        self.title.grid(row=0, column=0, sticky='w')
        self.subtitle = ctk.CTkLabel(
            header,
            text='Elige una identidad visual completa. Al aplicar, CorePulse reemplaza la paleta actual por estos colores exactos, sin filtros.',
            font=(FONT, 10), anchor='w', justify='left',
        )
        self.subtitle.grid(row=1, column=0, sticky='w', pady=(3, 0))

    def _build_picker(self):
        p = self._initial_palette
        shell = ctk.CTkFrame(self.root, fg_color=p['surface'], border_color=p['border'], corner_radius=12, border_width=1)
        shell.grid(row=1, column=0, sticky='nsew', padx=(20, 9), pady=(0, 18))
        shell.grid_rowconfigure(1, weight=1)
        shell.grid_columnconfigure(0, weight=1)
        self.picker_shell = shell

        self.picker_title = ctk.CTkLabel(shell, text=f'{len(self.profiles)} temas oscuros disponibles', font=(FONT, 11, 'bold'), anchor='w')
        self.picker_title.grid(row=0, column=0, sticky='ew', padx=14, pady=(12, 7))

        self.scroll = ctk.CTkScrollableFrame(
            shell, fg_color=p['surface'], corner_radius=0,
            scrollbar_fg_color=p['surface'],
            scrollbar_button_color=p['border'],
            scrollbar_button_hover_color=p['accent_2'],
        )
        self.scroll.grid(row=1, column=0, sticky='nsew', padx=5, pady=(0, 6))
        self.scroll.grid_columnconfigure((0, 1), weight=1)

        for index, (key, profile) in enumerate(self.profiles.items()):
            card = ctk.CTkFrame(
                self.scroll, fg_color=profile['surface_2'], border_width=1,
                border_color=profile['border'], corner_radius=11, height=96,
            )
            card.grid(row=index // 2, column=index % 2, sticky='nsew', padx=4, pady=4)
            card.grid_propagate(False)
            card.grid_columnconfigure(0, weight=1)

            button = ctk.CTkButton(
                card, text=profile['name'], height=32, corner_radius=8,
                fg_color='transparent', hover_color=profile['border'],
                text_color=profile['text'], anchor='w',
                font=(FONT, 10, 'bold'),
                command=lambda value=key: self._select(value),
            )
            button.grid(row=0, column=0, columnspan=4, sticky='ew', padx=7, pady=(6, 0))

            desc = ctk.CTkLabel(
                card, text=profile['description'], font=(FONT, 7),
                text_color=profile['text_2'], anchor='w', justify='left',
                wraplength=126,
            )
            desc.grid(row=1, column=0, columnspan=4, sticky='ew', padx=10, pady=(0, 4))

            swatches = []
            colors = (profile['accent'], profile['accent_2'], profile['surface'], profile['bg'])
            for col, color in enumerate(colors):
                swatch = ctk.CTkFrame(card, height=6, fg_color=color, corner_radius=3)
                swatch._cp_preserve_surface = True
                swatch.grid(row=2, column=col, sticky='ew', padx=(10 if col == 0 else 2, 10 if col == 3 else 2), pady=(0, 7))
                card.grid_columnconfigure(col, weight=1)
                swatches.append(swatch)

            self._theme_buttons[key] = {
                'card': card, 'button': button, 'description': desc, 'swatches': swatches,
            }

    def _build_preview(self):
        p = self._initial_palette
        right = ctk.CTkFrame(self.root, fg_color=p['surface'], border_color=p['border'], corner_radius=12, border_width=1)
        right.grid(row=1, column=1, sticky='nsew', padx=(9, 20), pady=(0, 18))
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)
        self.preview_shell = right

        top = ctk.CTkFrame(right, fg_color=p['surface'])
        self.preview_top = top
        top.grid(row=0, column=0, sticky='ew', padx=16, pady=(12, 8))
        top.grid_columnconfigure(0, weight=1)
        self.preview_title = ctk.CTkLabel(top, text='Vista previa', font=(FONT, 11, 'bold'), anchor='w')
        self.preview_title.grid(row=0, column=0, sticky='w')
        self.selection_badge = ctk.CTkLabel(top, text='', font=(FONT, 9, 'bold'), corner_radius=8, padx=9, pady=4)
        self.selection_badge.grid(row=0, column=1, sticky='e')

        body = ctk.CTkFrame(right, fg_color=p['surface'])
        body.grid(row=1, column=0, sticky='nsew', padx=0, pady=0)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)
        self.preview_body = body

        info = ctk.CTkFrame(body, fg_color=p['surface_2'], border_color=p['border'], corner_radius=12, border_width=1, width=215)
        info.grid(row=0, column=0, sticky='ns', padx=(16, 8), pady=(0, 12))
        info.grid_propagate(False)
        self.preview_info = info

        self.info_kicker = ctk.CTkLabel(info, text='TEMA SELECCIONADO', font=(FONT, 8, 'bold'), anchor='w')
        self.info_kicker.pack(fill='x', padx=14, pady=(14, 4))
        self.info_name = ctk.CTkLabel(info, text='', font=(FONT, 18, 'bold'), anchor='w', justify='left')
        self.info_name.pack(fill='x', padx=14)
        self.info_desc = ctk.CTkLabel(info, text='', font=(FONT, 9), anchor='w', justify='left', wraplength=180)
        self.info_desc.pack(fill='x', padx=14, pady=(6, 10))

        self.info_divider = ctk.CTkFrame(info, fg_color=p['border'], height=1, corner_radius=0)
        self.info_divider.pack(fill='x', padx=14, pady=(0, 10))

        self.info_palette_title = ctk.CTkLabel(info, text='Paleta principal', font=(FONT, 9, 'bold'), anchor='w')
        self.info_palette_title.pack(fill='x', padx=14, pady=(0, 6))

        self.info_swatches = []
        for label in ('Acento', 'Acento suave', 'Superficie', 'Fondo'):
            row = ctk.CTkFrame(info, fg_color='transparent')
            row.pack(fill='x', padx=14, pady=3)
            row.grid_columnconfigure(1, weight=1)
            sw = ctk.CTkFrame(row, width=20, height=20, corner_radius=6)
            sw._cp_preserve_surface = True
            sw.grid(row=0, column=0, padx=(0, 10), sticky='w')
            sw.grid_propagate(False)
            text = ctk.CTkLabel(row, text=label, font=(FONT, 9), anchor='w')
            text.grid(row=0, column=1, sticky='ew')
            self.info_swatches.append((sw, text))

        self.info_meta = ctk.CTkLabel(
            info,
            text='La vista previa reproduce la jerarquía visual general del dashboard, el sidebar y las tarjetas.',
            font=(FONT, 8), anchor='w', justify='left', wraplength=182,
        )
        self.info_meta.pack(fill='x', padx=14, pady=(12, 14))

        mock = ctk.CTkFrame(body, fg_color=p['bg'], border_color=p['border'], corner_radius=12, border_width=1)
        mock.grid(row=0, column=1, sticky='nsew', padx=(8, 16), pady=(0, 12))
        mock.grid_columnconfigure(1, weight=1)
        mock.grid_rowconfigure(0, weight=1)
        self.mock = mock
        mock._cp_preserve_surface = True

        side = ctk.CTkFrame(mock, width=126, corner_radius=10, fg_color=p['sidebar'])
        side.grid(row=0, column=0, sticky='nsew', padx=10, pady=10)
        side.grid_propagate(False)
        self.mock_sidebar = side
        self.mock_brand = ctk.CTkLabel(side, text='COREPULSE', font=(FONT, 11, 'bold'))
        self.mock_brand.pack(anchor='w', padx=12, pady=(14, 14))
        self.mock_nav = []
        for text in ('Resumen', 'Diagnóstico', 'Mantenimiento', 'Historial'):
            label = ctk.CTkLabel(side, text=text, height=27, corner_radius=7, anchor='w', padx=10, font=(FONT, 8, 'bold'))
            label.pack(fill='x', padx=8, pady=2)
            self.mock_nav.append(label)

        content = ctk.CTkFrame(mock, fg_color=p['bg'])
        self.preview_content = content
        content.grid(row=0, column=1, sticky='nsew', padx=(0, 10), pady=10)
        content.grid_columnconfigure((0, 1, 2), weight=1)
        content.grid_rowconfigure(2, weight=1)
        self.mock_heading = ctk.CTkLabel(content, text='Estado del sistema', font=(FONT, 14, 'bold'), anchor='w')
        self.mock_heading.grid(row=0, column=0, columnspan=3, sticky='ew', pady=(2, 8))

        self.metric_cards = []
        for col, (name, value) in enumerate((('CPU', '42%'), ('RAM', '58%'), ('GPU', '31%'))):
            card = ctk.CTkFrame(content, fg_color=p['surface'], border_color=p['border'], corner_radius=9, border_width=1)
            card.grid(row=1, column=col, sticky='nsew', padx=(0 if col == 0 else 4, 0), pady=(0, 8))
            title = ctk.CTkLabel(card, text=name, font=(FONT, 7, 'bold'), anchor='w')
            title.pack(fill='x', padx=9, pady=(8, 1))
            metric = ctk.CTkLabel(card, text=value, font=(FONT, 14, 'bold'), anchor='w')
            metric.pack(fill='x', padx=9, pady=(0, 8))
            self.metric_cards.append((card, title, metric))

        chart = ctk.CTkFrame(content, fg_color=p['surface_2'], border_color=p['border'], corner_radius=9, border_width=1)
        chart.grid(row=2, column=0, columnspan=3, sticky='nsew')
        chart.grid_columnconfigure((0, 1, 2), weight=1)
        self.chart = chart
        self.chart_title = ctk.CTkLabel(chart, text='Actividad en tiempo real', font=(FONT, 8, 'bold'), anchor='w')
        self.chart_title.grid(row=0, column=0, columnspan=3, sticky='ew', padx=10, pady=(9, 5))
        self.bars = []
        for index, amount in enumerate((0.76, 0.48, 0.64)):
            track = ctk.CTkProgressBar(chart, height=5, corner_radius=3, fg_color=p['border'], progress_color=p['accent'])
            track.grid(row=1 + index, column=0, columnspan=3, sticky='ew', padx=10, pady=5)
            track.set(amount)
            self.bars.append(track)

        self.preview_stats = []
        for col, (title_text, value_text) in enumerate((('Sidebar', 'Claro'), ('Tarjetas', 'Uniformes'), ('Acentos', 'Activos'))):
            pill = ctk.CTkFrame(chart, fg_color=p['surface'], border_color=p['border'], corner_radius=8, border_width=1)
            pill.grid(row=4, column=col, sticky='ew', padx=(10 if col == 0 else 4, 10 if col == 2 else 4), pady=(10, 10))
            pill.grid_columnconfigure(0, weight=1)
            label = ctk.CTkLabel(pill, text=title_text, font=(FONT, 7, 'bold'), anchor='w')
            label.grid(row=0, column=0, sticky='ew', padx=8, pady=(7, 1))
            value = ctk.CTkLabel(pill, text=value_text, font=(FONT, 10, 'bold'), anchor='w')
            value.grid(row=1, column=0, sticky='ew', padx=8, pady=(0, 7))
            self.preview_stats.append((pill, label, value))

        footer = ctk.CTkFrame(right, fg_color=p['surface'])
        self.preview_footer = footer
        footer.grid(row=2, column=0, sticky='ew', padx=16, pady=(0, 14))
        footer.grid_columnconfigure(0, weight=1)
        self.apply_hint = ctk.CTkLabel(footer, text='Selecciona un tema para previsualizarlo.', font=(FONT, 9), anchor='w')
        self.apply_hint.grid(row=0, column=0, sticky='w')
        self.apply_button = ctk.CTkButton(
            footer, text='Aplicar tema', width=130, height=34, corner_radius=9,
            font=(FONT, 10, 'bold'), command=self._apply,
        )
        self.apply_button.grid(row=0, column=1, sticky='e')

    def _select(self, theme_key):
        if theme_key not in self.profiles:
            return
        self.selected_theme = theme_key
        p = self.profiles[theme_key]

        for key, widgets in self._theme_buttons.items():
            candidate = self.profiles[key]
            active = key == theme_key
            card = widgets['card']
            button = widgets['button']
            desc = widgets['description']
            card.configure(
                fg_color=candidate['surface_2'],
                border_color=candidate['accent'] if active else candidate['border'],
                border_width=2 if active else 1,
            )
            button.configure(
                fg_color=candidate['accent_2'] if active else 'transparent',
                hover_color=candidate['accent'] if active else candidate['border'],
                text_color=candidate['text'],
            )
            desc.configure(text_color=candidate['text_2'])
            for swatch, color in zip(widgets['swatches'], (candidate['accent'], candidate['accent_2'], candidate['surface'], candidate['bg'])):
                swatch.configure(fg_color=color)

        self.root.configure(fg_color=p['bg'])
        self.header.configure(fg_color=p['bg'])
        self.picker_shell.configure(fg_color=p['surface'], border_color=p['border'])
        self.scroll.configure(
            fg_color=p['surface'],
            scrollbar_fg_color=p['surface'],
            scrollbar_button_color=p['border'],
            scrollbar_button_hover_color=p['accent_2'],
        )
        self.preview_shell.configure(fg_color=p['surface'], border_color=p['border'])
        self.preview_top.configure(fg_color=p['surface'])
        self.preview_body.configure(fg_color=p['surface'])
        self.preview_footer.configure(fg_color=p['surface'])
        self.title.configure(text_color=p['text'])
        self.subtitle.configure(text_color=p['muted'])
        self.picker_title.configure(text_color=p['text_2'])
        self.preview_title.configure(text_color=p['text_2'])
        self.selection_badge.configure(text=p['name'], fg_color=p['accent_2'], text_color=p['text'])

        self.preview_info.configure(fg_color=p['surface_2'], border_color=p['border'])
        self.info_kicker.configure(text_color=p['accent'])
        self.info_name.configure(text=p['name'], text_color=p['text'])
        self.info_desc.configure(text=p['description'], text_color=p['text_2'])
        self.info_divider.configure(fg_color=p['border'])
        self.info_palette_title.configure(text_color=p['text'])
        for (sw, label), color in zip(self.info_swatches, (p['accent'], p['accent_2'], p['surface'], p['bg'])):
            sw.configure(fg_color=color)
            label.configure(text_color=p['text_2'])
        self.info_meta.configure(text_color=p['muted'])

        self.mock.configure(fg_color=p['bg'], border_color=p['border'])
        self.preview_content.configure(fg_color=p['bg'])
        self.mock_sidebar.configure(fg_color=p['sidebar'])
        self.mock_brand.configure(text_color=p['accent'])
        for index, label in enumerate(self.mock_nav):
            label.configure(
                text_color=p['text'] if index == 0 else p['text_2'],
                fg_color=p['accent_2'] if index == 0 else 'transparent',
            )
        self.mock_heading.configure(text_color=p['text'])
        for card, title, value in self.metric_cards:
            card.configure(fg_color=p['surface'], border_color=p['border'])
            title.configure(text_color=p['muted'])
            value.configure(text_color=p['text'])
        self.chart.configure(fg_color=p['surface_2'], border_color=p['border'])
        self.chart_title.configure(text_color=p['text_2'])
        for bar in self.bars:
            bar.configure(fg_color=p['border'], progress_color=p['accent'])
        for pill, label, value in self.preview_stats:
            pill.configure(fg_color=p['surface'], border_color=p['border'])
            label.configure(text_color=p['muted'])
            value.configure(text_color=p['text'])

        self.apply_hint.configure(text_color=p['muted'])
        self.apply_button.configure(fg_color=p['accent_2'], hover_color=p['accent'], text_color=p['text'])

        current = get_theme()
        if theme_key == current:
            self.apply_button.configure(text='Tema actual', state='disabled')
            self.apply_hint.configure(text='Este tema ya está aplicado en CorePulse.')
        else:
            self.apply_button.configure(text='Aplicar tema', state='normal')
            self.apply_hint.configure(text=f"Vista previa exacta de {p['name']}. Pulsa Aplicar para reemplazar la paleta actual.")

    def _apply(self):
        current = get_theme()
        if self.selected_theme == current:
            return
        try:
            self.apply_button.configure(text='Aplicando…', state='disabled')
            self.root.update_idletasks()
            selected = self.selected_theme
            set_theme(selected)
            apply_theme_live(self.app, current, selected)
            self._select(selected)
            self.apply_button.configure(text='Tema actual', state='disabled')
            self.apply_hint.configure(text='Tema aplicado al instante, sin reiniciar CorePulse.')
        except Exception:
            try:
                set_theme(current)
            except Exception:
                pass
            self.apply_button.configure(text='Aplicar tema', state='normal')
