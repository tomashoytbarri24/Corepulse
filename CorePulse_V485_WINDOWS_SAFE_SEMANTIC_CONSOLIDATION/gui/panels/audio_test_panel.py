"""Módulo integrado de audio. Toda operación nativa sucede fuera del hilo Tk."""
import queue
import threading
import customtkinter as ctk
from core.windows_audio import AudioTest, evidence_rows
from core.theme_manager import color


BG = color('#06111f')
SURFACE = color('#0d1828')
SURFACE_2 = color('#0a1524')
BORDER = color('#1b3048')
TEXT = color('#f4f7fb')
TEXT_2 = color('#b8c4d4')
MUTED = color('#7f90a6')
CYAN = '#14b8ff'
GREEN = '#10b981'
AMBER = '#f59e0b'
RED = '#ef4444'
TRACK = color('#17304a')
FONT = 'Segoe UI'


class AudioTestPanel(ctk.CTkFrame):
    """V360: prueba de audio guiada con jerarquía visual de producto final."""

    def __init__(self, master, service=None):
        super().__init__(master, fg_color='transparent')
        self.service = service or AudioTest()
        self.events = queue.Queue()
        self.busy = False
        self.closed = False
        self._poll_id = None
        self.bind('<Destroy>', self._destroyed, add='+')

        self.body = ctk.CTkFrame(self, fg_color='transparent')
        self.body.pack(fill='both', expand=True, padx=4, pady=(2, 8))

        self._build_intro()
        self._build_output_card()
        self._build_microphone_card()
        self._build_confirmation_card()
        self._build_summary_card()

        self._poll_id = self.after(50, self.poll)
        self.run(self.service.refresh, 'refresh')

    # ------------------------------------------------------------------ UI
    def _card(self, parent=None):
        return ctk.CTkFrame(
            parent or self.body,
            fg_color=SURFACE,
            border_width=1,
            border_color=BORDER,
            corner_radius=14,
        )

    def _section_title(self, parent, eyebrow, title, detail=None, accent=CYAN):
        head = ctk.CTkFrame(parent, fg_color='transparent')
        head.pack(fill='x', padx=16, pady=(13, 7))
        left = ctk.CTkFrame(head, fg_color='transparent')
        left.pack(side='left', fill='x', expand=True)
        ctk.CTkLabel(
            left, text=eyebrow.upper(), font=(FONT, 8, 'bold'),
            text_color=accent, anchor='w'
        ).pack(fill='x')
        ctk.CTkLabel(
            left, text=title, font=(FONT, 15, 'bold'),
            text_color=TEXT, anchor='w'
        ).pack(fill='x', pady=(2, 0))
        if detail:
            ctk.CTkLabel(
                left, text=detail, font=(FONT, 9), text_color=TEXT_2,
                anchor='w', justify='left', wraplength=760
            ).pack(fill='x', pady=(3, 0))
        return head

    def _build_intro(self):
        card = self._card()
        card.pack(fill='x', pady=(0, 10))
        row = ctk.CTkFrame(card, fg_color='transparent')
        row.pack(fill='x', padx=16, pady=12)
        copy = ctk.CTkFrame(row, fg_color='transparent')
        copy.pack(side='left', fill='x', expand=True)
        ctk.CTkLabel(
            copy, text='VERIFICACIÓN LOCAL DE AUDIO', font=(FONT, 8, 'bold'),
            text_color=CYAN, anchor='w'
        ).pack(fill='x')
        ctk.CTkLabel(
            copy, text='Comprueba salida estéreo y micrófono', font=(FONT, 17, 'bold'),
            text_color=TEXT, anchor='w'
        ).pack(fill='x', pady=(2, 1))
        ctk.CTkLabel(
            copy,
            text='La prueba se ejecuta de forma local. La voz sólo permanece en memoria durante la sesión y no se envía.',
            font=(FONT, 9), text_color=TEXT_2, anchor='w', justify='left', wraplength=760
        ).pack(fill='x')
        self.state_chip = ctk.CTkLabel(
            row, text='● Preparando', width=128, height=30,
            corner_radius=10, fg_color=SURFACE_2,
            text_color=CYAN, font=(FONT, 8, 'bold')
        )
        self.state_chip.pack(side='right', padx=(12, 0))

    def _build_output_card(self):
        card = self._card()
        card.pack(fill='x', pady=(0, 10))
        self._section_title(
            card, '01 · Salida', 'Prueba de canales',
            'Reproduce una señal corta y confirma manualmente si escuchas cada canal.', CYAN
        )
        device_row = ctk.CTkFrame(card, fg_color=SURFACE_2, corner_radius=10, border_width=1, border_color=BORDER)
        device_row.pack(fill='x', padx=16, pady=(0, 10))
        ctk.CTkLabel(device_row, text='DISPOSITIVO', font=(FONT, 8, 'bold'), text_color=MUTED).pack(side='left', padx=(12, 8), pady=9)
        self.output = ctk.CTkLabel(device_row, text='Consultando…', font=(FONT, 10, 'bold'), text_color=TEXT, anchor='w')
        self.output.pack(side='left', fill='x', expand=True, pady=9)
        self.stereo = ctk.CTkLabel(device_row, text='', font=(FONT, 8, 'bold'), text_color=CYAN, anchor='e')
        self.stereo.pack(side='right', padx=12, pady=9)

        buttons = ctk.CTkFrame(card, fg_color='transparent')
        buttons.pack(fill='x', padx=13, pady=(0, 14))
        for column in range(3):
            buttons.grid_columnconfigure(column, weight=1, uniform='audio_channels')

        # V360: Ambos ocupa explícitamente la posición CENTRAL.
        self.left_button = ctk.CTkButton(
            buttons, text='Izquierdo', height=38, corner_radius=10,
            fg_color=SURFACE_2, hover_color=color('#12304b'), border_width=1, border_color=BORDER,
            text_color=TEXT, command=lambda: self.run(lambda: self.service.play('left'), 'left')
        )
        self.both_button = ctk.CTkButton(
            buttons, text='Ambos', height=38, corner_radius=10,
            fg_color=color('#0d2942'), hover_color=color('#164f7d'), border_width=1, border_color=CYAN,
            text_color=TEXT, font=(FONT, 10, 'bold'),
            command=lambda: self.run(lambda: self.service.play('both'), 'both')
        )
        self.right_button = ctk.CTkButton(
            buttons, text='Derecho', height=38, corner_radius=10,
            fg_color=SURFACE_2, hover_color=color('#12304b'), border_width=1, border_color=BORDER,
            text_color=TEXT, command=lambda: self.run(lambda: self.service.play('right'), 'right')
        )
        self.left_button.grid(row=0, column=0, sticky='ew', padx=3)
        self.both_button.grid(row=0, column=1, sticky='ew', padx=3)
        self.right_button.grid(row=0, column=2, sticky='ew', padx=3)

        self.actions = [self.left_button, self.both_button, self.right_button]

    def _build_microphone_card(self):
        card = self._card()
        card.pack(fill='x', pady=(0, 10))
        self._section_title(
            card, '02 · Entrada', 'Micrófono',
            'Graba 5 segundos, revisa la señal capturada y reproduce la muestra antes de confirmar.', GREEN
        )
        device_row = ctk.CTkFrame(card, fg_color=SURFACE_2, corner_radius=10, border_width=1, border_color=BORDER)
        device_row.pack(fill='x', padx=16, pady=(0, 10))
        ctk.CTkLabel(device_row, text='DISPOSITIVO', font=(FONT, 8, 'bold'), text_color=MUTED).pack(side='left', padx=(12, 8), pady=9)
        self.input = ctk.CTkLabel(device_row, text='Consultando…', font=(FONT, 10, 'bold'), text_color=TEXT, anchor='w')
        self.input.pack(side='left', fill='x', expand=True, pady=9)

        control = ctk.CTkFrame(card, fg_color='transparent')
        control.pack(fill='x', padx=16, pady=(0, 8))
        self.record_button = ctk.CTkButton(
            control, text='●  Grabar 5 s', width=160, height=36, corner_radius=10,
            fg_color=color('#0d2942'), hover_color=color('#164f7d'), border_width=1, border_color=CYAN,
            text_color=TEXT, font=(FONT, 10, 'bold'), command=self.record
        )
        self.record_button.pack(side='left')
        self.replay = ctk.CTkButton(
            control, text='Reproducir muestra', width=170, height=36, corner_radius=10,
            fg_color=SURFACE_2, hover_color=color('#12304b'), border_width=1, border_color=BORDER,
            text_color=TEXT, command=lambda: self.run(lambda: self.service.play('microphone'), 'microphone')
        )
        self.replay.pack(side='left', padx=(8, 0))
        self.level_text = ctk.CTkLabel(
            control, text='Nivel de entrada: N/A', font=(FONT, 9, 'bold'), text_color=MUTED, anchor='e'
        )
        self.level_text.pack(side='right', fill='x', expand=True)

        self.level = ctk.CTkProgressBar(card, height=7, corner_radius=7, fg_color=TRACK, progress_color=GREEN)
        self.level.pack(fill='x', padx=16, pady=(0, 14))
        self.level.set(0)
        self.actions.extend([self.record_button, self.replay])

    def _build_confirmation_card(self):
        card = self._card()
        card.pack(fill='x', pady=(0, 10))
        top = ctk.CTkFrame(card, fg_color='transparent')
        top.pack(fill='x', padx=16, pady=(12, 8))
        self.status = ctk.CTkLabel(top, text='Preparando dispositivos…', font=(FONT, 10, 'bold'), text_color=CYAN, anchor='w')
        self.status.pack(side='left', fill='x', expand=True)
        self.refresh_button = ctk.CTkButton(
            top, text='Actualizar dispositivos', width=150, height=30, corner_radius=9,
            fg_color='transparent', hover_color=SURFACE_2, border_width=1, border_color=BORDER,
            text_color=TEXT_2, command=lambda: self.run(self.service.refresh, 'refresh')
        )
        self.refresh_button.pack(side='right')
        self.actions.append(self.refresh_button)

        self.question = ctk.CTkLabel(
            card, text='Completa una reproducción para habilitar la confirmación.',
            font=(FONT, 11, 'bold'), text_color=TEXT, anchor='w', justify='left'
        )
        self.question.pack(fill='x', padx=16, pady=(2, 8))

        answers = ctk.CTkFrame(card, fg_color='transparent')
        answers.pack(fill='x', padx=13, pady=(0, 14))
        for column in range(3):
            answers.grid_columnconfigure(column, weight=1, uniform='audio_answers')
        self.answers = []
        for column, answer in enumerate(('Sí', 'No estoy seguro', 'No')):
            tone = GREEN if answer == 'Sí' else AMBER if answer == 'No estoy seguro' else RED
            button = ctk.CTkButton(
                answers, text=answer, height=36, corner_radius=10, state='disabled',
                fg_color=SURFACE_2, hover_color=color('#12304b'), border_width=1, border_color=tone,
                text_color=TEXT, command=lambda a=answer: self.run(lambda: self.service.confirm(a), 'confirm')
            )
            button.grid(row=0, column=column, sticky='ew', padx=3)
            self.answers.append(button)

    def _build_summary_card(self):
        card = self._card()
        card.pack(fill='both', expand=True, pady=(0, 2))
        head = ctk.CTkFrame(card, fg_color='transparent')
        head.pack(fill='x', padx=16, pady=(12, 6))
        ctk.CTkLabel(head, text='RESULTADO DE LA PRUEBA', font=(FONT, 8, 'bold'), text_color=CYAN, anchor='w').pack(side='left')
        self.summary_badge = ctk.CTkLabel(
            head, text='NO EVALUADO', width=125, height=26, corner_radius=9,
            fg_color=SURFACE_2, text_color=MUTED, font=(FONT, 8, 'bold')
        )
        self.summary_badge.pack(side='right')

        self.summary = ctk.CTkLabel(
            card, text='Esperando evidencia…', font=(FONT, 9), text_color=TEXT_2,
            anchor='nw', justify='left', wraplength=920
        )
        self.summary.pack(fill='both', expand=True, padx=16, pady=(2, 12))

        footer = ctk.CTkFrame(card, fg_color='transparent')
        footer.pack(fill='x', padx=16, pady=(0, 12))
        ctk.CTkLabel(
            footer, text='REAL_OR_NA · La confirmación humana se conserva separada de la evidencia técnica.',
            font=(FONT, 8), text_color=MUTED, anchor='w'
        ).pack(side='left', fill='x', expand=True)
        self.stop_button = ctk.CTkButton(
            footer, text='Detener prueba', width=115, height=28, corner_radius=8,
            fg_color='transparent', hover_color=SURFACE_2, border_width=1, border_color=BORDER,
            text_color=TEXT_2, command=self.service.cancel.set
        )
        self.stop_button.pack(side='right')

    # -------------------------------------------------------------- behavior
    def record(self):
        self.level.set(0)
        self.run(lambda: self.service.record(lambda value: self.events.put(('level', value))), 'record')

    def run(self, fn, key):
        if self.busy or self.closed:
            return
        self.busy = True
        self.service.cancel.clear()
        self.question.configure(text='Procesando…')
        for widget in self.actions + self.answers:
            widget.configure(state='disabled')
        text = '● Grabando · 5 segundos' if key == 'record' else 'Reproduciendo señal…' if key in ('left', 'right', 'both', 'microphone') else 'Consultando dispositivos…'
        self.status.configure(text=text, text_color=CYAN)
        self.state_chip.configure(text='● En prueba', text_color=CYAN)

        def worker():
            try:
                fn()
                self.events.put(('done', key))
            except Exception as exc:
                self.events.put(('error', str(exc)))
        threading.Thread(target=worker, daemon=True, name='CorePulse-AudioTest').start()

    def poll(self):
        if self.closed:
            return
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == 'level':
                    self.level.set(min(1.0, value))
                    self.level_text.configure(text=f'Amplitud real: {value:.4f}')
                    continue
                self.busy = False
                if kind == 'error':
                    self.status.configure(text='Error · ' + value, text_color=RED)
                    self.state_chip.configure(text='● Revisar', text_color=RED)
                elif value == 'record':
                    self.status.configure(text='Grabación lista · reproduce la muestra para verificarla.', text_color=GREEN)
                    self.state_chip.configure(text='● Grabación lista', text_color=GREEN)
                elif self.service.pending:
                    self.status.configure(text='Reproducción terminada · confirma lo que escuchaste.', text_color=GREEN)
                    self.state_chip.configure(text='● Confirmación', text_color=GREEN)
                else:
                    self.status.configure(text='Listo para continuar.', text_color=GREEN)
                    self.state_chip.configure(text='● Listo', text_color=GREEN)
                self.update_state()
        except queue.Empty:
            pass
        self._poll_id = self.after(50, self.poll)

    def update_state(self):
        devices = self.service.result.get('devices', {})
        output, source = devices.get('output', {}), devices.get('input', {})
        output_name = output.get('name') or 'N/A'
        input_name = source.get('name') or 'N/A'
        self.output.configure(text=output_name, text_color=TEXT if output.get('available') else MUTED)
        self.input.configure(text=input_name, text_color=TEXT if source.get('available') else MUTED)
        self.stereo.configure(
            text='Estéreo disponible' if output.get('stereo') else 'Estéreo N/A',
            text_color=GREEN if output.get('stereo') else MUTED,
        )

        # Estados explícitos: no dependen del orden de self.actions.
        stereo_ok = bool(output.get('available') and output.get('stereo'))
        output_ok = bool(output.get('available'))
        self.left_button.configure(state='normal' if stereo_ok else 'disabled')
        self.right_button.configure(state='normal' if stereo_ok else 'disabled')
        self.both_button.configure(state='normal' if output_ok else 'disabled')
        self.record_button.configure(state='normal' if source.get('available') else 'disabled')
        self.replay.configure(state='normal' if self.service.recording and output_ok else 'disabled')
        self.refresh_button.configure(state='normal')

        pending = self.service.pending
        self.question.configure(text=(
            '¿La grabación se escucha correctamente?' if pending == 'microphone' else
            '¿Escuchaste correctamente esta reproducción?'
        ) if pending else 'Completa una reproducción para habilitar la confirmación.')
        for button in self.answers:
            button.configure(state='normal' if pending else 'disabled')

        from core.windows_audio import summary
        result_status = summary(self.service.result)
        status_color = GREEN if result_status == 'AUDIO VERIFICADO' else RED if result_status == 'PROBLEMA REPORTADO' else AMBER if result_status == 'VERIFICACIÓN PARCIAL' else MUTED
        self.summary_badge.configure(text=result_status, text_color=status_color)
        rows = evidence_rows(self.service.result)
        self.summary.configure(text='\n'.join(f'{key:<25}  {value}' for key, value in rows))

    def _destroyed(self, event):
        if event.widget is self:
            self.closed = True
            self.service.close()

    def destroy(self):
        if not self.closed:
            self.closed = True
            self.service.close()
            if self._poll_id is not None:
                try:
                    self.after_cancel(self._poll_id)
                except Exception:
                    pass
        super().destroy()


def open_audio_test(app):
    return app.open_health_center(tab='audio')
