"""Panel conversacional de CorePulse AI conectado al backend propio."""
from __future__ import annotations

import threading
import time
import re
import customtkinter as ctk

from core.theme_manager import role_color
from core.ai_client import (
    load_ai_settings,
    service_status,
    build_runtime_context,
    analyze_context,
    chat_context,
)
from gui.internal_navigation import show_dashboard

BG = role_color('bg')
SURFACE = role_color('surface')
SURFACE2 = role_color('surface_2')
BORDER = role_color('border')
TEXT = role_color('text')
TEXT2 = role_color('text_2')
MUTED = role_color('muted')
CYAN = role_color('accent')
CYAN2 = role_color('accent_2')
GREEN = '#16d98b'
AMBER = '#f3b54a'
RED = '#ff5d6c'
FONT = 'Segoe UI'


def _plain_ai_text(value: str) -> str:
    """Última barrera visual para respuestas de texto plano en el chat."""
    text = str(value or '').strip()
    text = re.sub(r'```(?:[A-Za-z0-9_+.-]+)?\s*', '', text)
    text = text.replace('```', '')
    text = re.sub(r'(?m)^\s{0,3}#{1,6}\s*', '', text)
    text = text.replace('**', '').replace('__', '')
    text = re.sub(r'`([^`\n]+)`', r'\1', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


class CorePulseAIPanel(ctk.CTkFrame):
    def __init__(self, app, parent):
        super().__init__(parent, fg_color=BG, corner_radius=0)
        self.app = app
        self.settings = load_ai_settings()
        self._busy = False
        self._last_submit_monotonic = 0.0
        self._request_seq = 0
        self._conversation: list[dict[str, str]] = []
        self.pack(fill='both', expand=True)
        self._build()
        self._refresh_status_async()

    def _build(self):
        header = ctk.CTkFrame(self, fg_color='transparent', height=88)
        header.pack(fill='x', padx=22, pady=(18, 8))
        header.pack_propagate(False)
        ctk.CTkButton(
            header, text='Volver al Resumen', width=160, height=34, corner_radius=9,
            fg_color='transparent', hover_color=SURFACE2, border_width=1,
            border_color=BORDER, text_color=TEXT, font=(FONT, 9, 'bold'),
            command=lambda: show_dashboard(self.app),
        ).pack(side='left', anchor='n', pady=5)
        title_box = ctk.CTkFrame(header, fg_color='transparent')
        title_box.pack(side='left', fill='both', expand=True, padx=(18, 12))
        ctk.CTkLabel(title_box, text='COREPULSE AI', font=(FONT, 8, 'bold'), text_color=CYAN, anchor='w').pack(anchor='w')
        ctk.CTkLabel(title_box, text='Asistente inteligente del equipo', font=(FONT, 25, 'bold'), text_color=TEXT, anchor='w').pack(anchor='w', pady=(2, 2))
        ctk.CTkLabel(
            title_box,
            text='CorePulse mide y clasifica. La IA conversa y explica únicamente a partir de evidencia real del equipo.',
            font=(FONT, 9), text_color=TEXT2, anchor='w', justify='left', wraplength=760,
        ).pack(anchor='w')
        self.status_chip = ctk.CTkLabel(
            header, text='● Comprobando', width=150, height=34, corner_radius=12,
            fg_color=SURFACE, text_color=MUTED, font=(FONT, 8, 'bold'),
        )
        self.status_chip.pack(side='right', anchor='n', pady=5)

        body = ctk.CTkFrame(self, fg_color='transparent')
        body.pack(fill='both', expand=True, padx=22, pady=(0, 20))

        service = ctk.CTkFrame(body, fg_color=SURFACE, border_width=1, border_color=BORDER, corner_radius=14)
        service.pack(fill='x', pady=(0, 10))
        top = ctk.CTkFrame(service, fg_color='transparent')
        top.pack(fill='x', padx=16, pady=(14, 4))
        ctk.CTkLabel(top, text='Servicio CorePulse AI', font=(FONT, 14, 'bold'), text_color=TEXT).pack(side='left')
        self.refresh_button = ctk.CTkButton(
            top, text='Actualizar estado', width=124, height=32, corner_radius=8,
            fg_color='transparent', hover_color=SURFACE2, border_width=1, border_color=CYAN,
            text_color=TEXT, font=(FONT, 8, 'bold'), command=self._refresh_status_async,
        )
        self.refresh_button.pack(side='right')
        self.service_line = ctk.CTkLabel(service, text='Comprobando conexión…', font=(FONT, 9), text_color=TEXT2, anchor='w')
        self.service_line.pack(fill='x', padx=16, pady=(0, 3))
        ctk.CTkLabel(
            service,
            text='Sin API keys del usuario · El modelo vive fuera de CorePulse Desktop · Sin seriales ni rutas personales enviados.',
            font=(FONT, 8), text_color=TEXT2, anchor='w', justify='left', wraplength=900,
        ).pack(fill='x', padx=16, pady=(0, 14))

        assistant = ctk.CTkFrame(body, fg_color=SURFACE, border_width=1, border_color=BORDER, corner_radius=14)
        assistant.pack(fill='both', expand=True)
        row = ctk.CTkFrame(assistant, fg_color='transparent')
        row.pack(fill='x', padx=16, pady=(14, 8))
        ctk.CTkLabel(row, text='Conversación con CorePulse AI', font=(FONT, 14, 'bold'), text_color=TEXT).pack(side='left')
        self.clear_button = ctk.CTkButton(
            row, text='Limpiar', width=78, height=34, corner_radius=9,
            fg_color='transparent', hover_color=SURFACE2, border_width=1, border_color=BORDER,
            text_color=TEXT, font=(FONT, 8, 'bold'), command=self._clear_conversation,
        )
        self.clear_button.pack(side='right', padx=(8, 0))
        self.analyze_button = ctk.CTkButton(
            row, text='Analizar mi equipo', width=140, height=34, corner_radius=9,
            fg_color=CYAN2, hover_color=CYAN, text_color=TEXT, font=(FONT, 8, 'bold'),
            command=self._analyze,
        )
        self.analyze_button.pack(side='right')

        self.output = ctk.CTkTextbox(
            assistant, fg_color=BG, border_width=1, border_color=BORDER, corner_radius=10,
            text_color=TEXT, font=(FONT, 9), wrap='word', activate_scrollbars=True,
        )
        self.output.pack(fill='both', expand=True, padx=16, pady=(0, 10))
        self._set_output(
            'CorePulse AI\n\nHola. Puedo explicarte el estado actual del equipo usando únicamente los datos reales que CorePulse tiene disponibles.'
        )

        question_row = ctk.CTkFrame(assistant, fg_color='transparent')
        question_row.pack(fill='x', padx=16, pady=(0, 16))
        self.question_entry = ctk.CTkEntry(
            question_row, placeholder_text='Pregúntale algo sobre tu equipo…',
            height=38, corner_radius=9, fg_color=BG, border_color=BORDER,
            text_color=TEXT, placeholder_text_color=MUTED, font=(FONT, 9),
        )
        self.question_entry.pack(side='left', fill='x', expand=True, padx=(0, 8))
        self.question_entry.bind('<Return>', self._on_enter)
        self.ask_button = ctk.CTkButton(
            question_row, text='Enviar', width=100, height=38, corner_radius=9,
            fg_color='transparent', hover_color=SURFACE2, border_width=1, border_color=CYAN,
            text_color=TEXT, font=(FONT, 8, 'bold'), command=self._ask,
        )
        self.ask_button.pack(side='right')

    def _set_busy(self, value: bool, message: str = ''):
        self._busy = bool(value)
        state = 'disabled' if value else 'normal'
        for widget in (self.refresh_button, self.analyze_button, self.ask_button, self.clear_button):
            try:
                widget.configure(state=state)
            except Exception:
                pass
        if message:
            self.service_line.configure(text=message, text_color=CYAN)

    def _refresh_status_async(self):
        if self._busy:
            return
        self._set_busy(True, 'Comprobando CorePulse AI…')
        def worker():
            result = service_status(self.settings)
            self.after(0, lambda: self._finish_status(result))
        threading.Thread(target=worker, daemon=True, name='CorePulseAIStatus').start()

    def _finish_status(self, result):
        self._set_busy(False)
        if result.get('ok'):
            model_ready = bool(result.get('model_ready'))
            model_configured = bool(result.get('model_configured', model_ready))
            self.status_chip.configure(text='● Conectado', text_color=GREEN, fg_color=SURFACE2)
            if model_ready:
                text = f"Servicio conectado · IA generativa lista: {result.get('model_name') or 'CorePulse AI'}"
                color = GREEN
            elif model_configured:
                text = 'Servicio conectado · Host generativo no responde; activo modo de evidencia segura.'
                color = AMBER
            else:
                text = 'Servicio conectado · Modelo aún no configurado; activo modo de evidencia segura.'
                color = AMBER
            self.service_line.configure(text=text, text_color=color)
        else:
            self.status_chip.configure(text='● Sin conexión', text_color=AMBER, fg_color=SURFACE2)
            self.service_line.configure(
                text='Servidor CorePulse AI no disponible. Inicia el backend de desarrollo o configura el endpoint de producción.',
                text_color=AMBER,
            )

    def _context(self):
        telemetry = getattr(self.app, 'latest_telemetry', None)
        disks = getattr(self.app, 'latest_disks', None)
        health = getattr(self.app, 'current_live_health', None)
        if not isinstance(telemetry, dict):
            return None
        return build_runtime_context(telemetry, disks, health)

    def _on_enter(self, _event=None):
        self._ask()
        return 'break'

    def _analyze(self):
        self._run_request('', kind='analyze')

    def _ask(self):
        question = self.question_entry.get().strip()
        if not question:
            return
        self._run_request(question, kind='chat')

    def _run_request(self, question: str, *, kind: str):
        if self._busy:
            return
        now = time.monotonic()
        if now - self._last_submit_monotonic < 1.25:
            return
        self._last_submit_monotonic = now
        context = self._context()
        if context is None:
            self._append_output('CorePulse AI', 'Aún no hay telemetría real disponible. Espera unos segundos y vuelve a intentar.')
            return

        self._request_seq += 1
        request_seq = self._request_seq
        history_snapshot = list(self._conversation[-8:])

        if kind == 'chat':
            self._append_output('Tú', question)
            self.question_entry.delete(0, 'end')
            busy_text = 'Consultando CorePulse AI con evidencia actual…'
        else:
            busy_text = 'Analizando evidencia real del equipo…'

        self._set_busy(True, busy_text)

        def worker():
            if kind == 'chat':
                result = chat_context(context, question=question, history=history_snapshot, settings=self.settings)
            else:
                result = analyze_context(context, question='', settings=self.settings)
            self.after(0, lambda: self._finish_request(result, request_seq, kind, question))

        threading.Thread(target=worker, daemon=True, name='CorePulseAIRequest').start()

    def _finish_request(self, result, request_seq, kind, question):
        if request_seq != self._request_seq:
            return
        self._set_busy(False)
        if result.get('ok'):
            mode = str(result.get('mode') or 'corepulse-ai')
            answer = _plain_ai_text(result.get('text') or '')
            label = 'CorePulse AI' if mode == 'model' else 'CorePulse Evidence Engine'
            self._append_output(label, answer)
            if kind == 'chat':
                self._conversation.extend([
                    {'role': 'user', 'content': question[:1800]},
                    {'role': 'assistant', 'content': answer[:1800]},
                ])
                self._conversation = self._conversation[-8:]
            remaining = result.get('remaining_today')
            suffix = f' · {remaining} consultas disponibles hoy' if isinstance(remaining, int) else ''
            state = 'Respuesta generativa completada.' if mode == 'model' else 'Respuesta segura completada sin modelo generativo.'
            self.service_line.configure(text=state + suffix, text_color=GREEN if mode == 'model' else AMBER)
        else:
            error = str(result.get('error') or 'Error desconocido.')
            self._append_output('CorePulse AI', 'No se pudo completar la solicitud.\n' + error)
            if '429' in error:
                self.service_line.configure(text='Límite del servidor alcanzado; no es un fallo de telemetría.', text_color=AMBER)
            else:
                self.service_line.configure(text='CorePulse AI no respondió correctamente.', text_color=RED)

    def _clear_conversation(self):
        if self._busy:
            return
        self._conversation.clear()
        self._set_output('CorePulse AI\n\nConversación limpia. La siguiente respuesta usará la evidencia actual del equipo.')

    def _append_output(self, author: str, text: str):
        self.output.configure(state='normal')
        current = self.output.get('1.0', 'end-1c').strip()
        block = f'{author}\n{text.strip()}'
        if current:
            self.output.insert('end', '\n\n' + block)
        else:
            self.output.insert('end', block)
        self.output.see('end')
        self.output.configure(state='disabled')

    def _set_output(self, text):
        self.output.configure(state='normal')
        self.output.delete('1.0', 'end')
        self.output.insert('1.0', str(text))
        self.output.configure(state='disabled')


__all__ = ['CorePulseAIPanel']
