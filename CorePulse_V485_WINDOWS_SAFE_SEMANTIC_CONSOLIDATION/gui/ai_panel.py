"""CorePulse AI: asistente conversacional profesional basado en evidencia real."""
from __future__ import annotations

import copy
import webbrowser
import os
import socket
import subprocess
from pathlib import Path
import threading
import time
import re
import customtkinter as ctk

from core.theme_manager import role_color
from core.ai_client import (
    load_ai_settings,
    LOCAL_GROQ_BRIDGE_URL,
    LOCAL_COMPAT_BRIDGE_URL,
    save_ai_settings,
    service_status,
    pairing_status,
    build_runtime_context,
    analyze_context,
    chat_context,
    ensure_registration,
    _cloud_gate,
)
from core.ai_query_context import build_query_context
from core.ai_investigation_history import query_sample, append_sample
from core.ai_credentials import save_secret
from core.ai_quick_connect import quick_connect_local_groq, connection_plan
from core.ai_user_control import load_ai_enabled
from core.ai_chat_flow import paired_for_endpoint, request_snapshot, describe_preflight, safe_youtube_search_from_reply, display_reply_without_raw_youtube_search

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


def _fmt_number(value, digits=0, suffix='') -> str:
    if value is None:
        return 'N/A'
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 'N/A'
    return f'{number:.{digits}f}{suffix}'


class CorePulseAIPanel(ctk.CTkFrame):
    """Interfaz profesional de CorePulse AI.

    CorePulse conserva la autoridad sobre sensores y estados. Este panel sólo
    presenta contexto real y conversa con el backend propio.
    """

    QUICK_PROMPTS = (
        ('Mantención', 'Dame un tutorial general de mantenimiento preventivo, paso a paso y sin asumir averías.'),
        ('Analizar mi PC', 'Analiza mi PC con los datos actuales y dime sólo lo que realmente merece atención.'),
        ('Temperaturas', '¿Cómo están las temperaturas actuales de mi CPU y GPU?'),
        ('RAM', '¿Cómo está el uso actual de mi memoria RAM?'),
        ('SSD', '¿Cómo está mi almacenamiento según los datos disponibles?'),
    )

    def __init__(self, app, parent):
        super().__init__(parent, fg_color=BG, corner_radius=0)
        self.app = app
        self.settings = load_ai_settings()
        self._busy = False
        self._last_submit_monotonic = 0.0
        self._request_seq = 0
        self._status_seq = 0
        self._connect_seq = 0
        self._request_endpoint = None
        self._conversation: list[dict[str, str]] = []
        self._investigation_samples: list[dict] = []  # sólo RAM, sesión de esta ventana
        self._message_widgets: list[ctk.CTkFrame] = []
        self._context_value_labels: dict[str, tuple[ctk.CTkLabel, ctk.CTkLabel]] = {}
        self.pack(fill='both', expand=True)
        self._build()
        self._sync_consent_controls()
        self._refresh_context_cards()
        self._refresh_status_async()

    def _build(self):
        # Cabecera compacta: producto primero, detalles internos fuera de la vista.
        header = ctk.CTkFrame(self, fg_color='transparent', height=82)
        # V440 · Cabecera superior eliminada por solicitud: sin título,
        # subtítulo, etiquetas ni zona reservada. Las referencias de
        # estado siguen vivas pero no se dibujan.
        # Sin pack(): el contenido funcional comienza arriba.
        header.pack_propagate(False)

        title_box = ctk.CTkFrame(header, fg_color='transparent')
        title_box.pack(side='left', fill='both', expand=True, padx=(0, 12))
        ctk.CTkLabel(
            title_box, text='COREPULSE AI', font=(FONT, 8, 'bold'),
            text_color=CYAN, anchor='w'
        ).pack(anchor='w')
        ctk.CTkLabel(
            title_box, text='Asistente de diagnóstico y rendimiento',
            font=(FONT, 24, 'bold'), text_color=TEXT, anchor='w'
        ).pack(anchor='w', pady=(1, 1))
        ctk.CTkLabel(
            title_box,
            text='Respuestas basadas en la telemetría real que CorePulse puede medir en este equipo.',
            font=(FONT, 9), text_color=TEXT2, anchor='w', justify='left', wraplength=760,
        ).pack(anchor='w')

        self.status_chip = ctk.CTkLabel(
            header, text='● Comprobando IA nube', width=164, height=34, corner_radius=10,
            fg_color=SURFACE, text_color=MUTED, font=(FONT, 8, 'bold'),
        )
        self.status_chip.pack(side='right', anchor='n', pady=5)

        # Barra discreta de estado/privacidad, sin exponer modelo, puertos o backend.
        status_bar = ctk.CTkFrame(
            self, fg_color=SURFACE, border_width=1, border_color=BORDER, corner_radius=11, height=44
        )
        status_bar.pack(fill='x', padx=24, pady=(0, 10))
        status_bar.pack_propagate(False)
        self.service_line = ctk.CTkLabel(
            status_bar, text='Comprobando disponibilidad…', font=(FONT, 8),
            text_color=TEXT2, anchor='w'
        )
        self.service_line.pack(side='left', fill='x', expand=True, padx=(14, 8))
        ctk.CTkLabel(
            status_bar, text='Datos en vivo · REAL_OR_NA', font=(FONT, 8, 'bold'),
            text_color=CYAN, anchor='e'
        ).pack(side='right', padx=(8, 8))
        self.refresh_button = ctk.CTkButton(
            status_bar, text='Actualizar', width=82, height=28, corner_radius=8,
            fg_color='transparent', hover_color=SURFACE2, border_width=1,
            border_color=BORDER, text_color=TEXT2, font=(FONT, 8, 'bold'),
            command=self._refresh_all,
        )
        self.refresh_button.pack(side='right', padx=(0, 8))
        self.cloud_settings_button = ctk.CTkButton(
            status_bar, text='Configuración avanzada', width=156, height=28, corner_radius=8,
            fg_color='transparent', hover_color=SURFACE2, border_width=1,
            border_color=BORDER, text_color=TEXT2, font=(FONT, 8, 'bold'),
            command=self._toggle_connection_settings,
        )
        self.cloud_settings_button.pack(side='right', padx=(0, 8))

        # V473 · Conexión cotidiana: una acción, consentimiento visible y estado honesto.
        connect_row = ctk.CTkFrame(self, fg_color=SURFACE, border_width=1,
                                   border_color=BORDER, corner_radius=11, height=67)
        connect_row.pack(fill='x', padx=24, pady=(0, 10))
        connect_row.pack_propagate(False)
        self.connect_button = ctk.CTkButton(
            connect_row, text='Conectar IA', width=132, height=38,
            fg_color=CYAN2, hover_color=CYAN, font=(FONT, 11, 'bold'),
            command=self._quick_connect,
        )
        self.connect_button.pack(side='left', padx=(12, 12), pady=12)
        status_stack = ctk.CTkFrame(connect_row, fg_color='transparent')
        status_stack.pack(side='left', fill='both', expand=True, pady=9)
        self.connection_state = ctk.CTkLabel(
            status_stack, text='● Sin conectar', text_color=AMBER,
            anchor='w', font=(FONT, 10, 'bold'))
        self.connection_state.pack(anchor='w')
        self.connection_help = ctk.CTkLabel(
            status_stack, text='Modelo en la nube · sin cargar una IA pesada en tu PC',
            text_color=TEXT2, anchor='w', font=(FONT, 8))
        self.connection_help.pack(anchor='w')
        self.simple_consent = ctk.CTkCheckBox(
            connect_row, text='Permito enviar preguntas y datos a Groq',
            font=(FONT, 8), text_color=TEXT2, width=25,
            command=self._toggle_simple_consent)
        self.simple_consent.pack(side='right', padx=(8, 14))
        if self.settings.get('cloud_telemetry_consent'):
            self.simple_consent.select()

        # CLOUD FIRST · Servidor elegido por el usuario. Consentimiento cerrado.
        cloud_bar = ctk.CTkFrame(self, fg_color=SURFACE, border_width=1,
                                 border_color=BORDER, corner_radius=11)
        self.cloud_bar = cloud_bar
        self._connection_expanded = False
        # Configuración técnica oculta por defecto; permanece disponible bajo demanda.
        url_row = ctk.CTkFrame(cloud_bar, fg_color='transparent')
        url_row.pack(fill='x', padx=11, pady=(8, 3))
        ctk.CTkLabel(url_row, text='Servidor IA', font=(FONT, 9, 'bold'),
                     text_color=TEXT2).pack(side='left', padx=(0, 8))
        self.cloud_url_entry = ctk.CTkEntry(
            url_row, placeholder_text='https://tu-servidor-corepulse.example',
            font=(FONT, 9), height=29)
        self.cloud_url_entry.pack(side='left', fill='x', expand=True, padx=(0, 8))
        if self.settings.get('base_url'):
            self.cloud_url_entry.insert(0, self.settings['base_url'])
        ctk.CTkButton(url_row, text='Guardar', width=76, height=29,
                      fg_color=CYAN2, text_color=TEXT,
                      command=self._save_cloud_server).pack(side='right')
        ctk.CTkButton(url_row, text='Groq (pruebas)', width=103, height=29,
                      fg_color='transparent', border_width=1, border_color=CYAN,
                      text_color=CYAN, command=self._use_groq_trial).pack(side='right', padx=(0, 8))
        ctk.CTkButton(url_row, text='Modelo alternativo', width=116, height=29,
                      fg_color='transparent', border_width=1, border_color=BORDER,
                      text_color=TEXT2, command=self._use_compatible_trial).pack(side='right', padx=(0, 8))
        privacy_row = ctk.CTkFrame(cloud_bar, fg_color='transparent')
        privacy_row.pack(fill='x', padx=11, pady=(3, 7))
        self.cloud_consent = ctk.CTkCheckBox(
            privacy_row, text='Autorizar preguntas y datos técnicos al servidor configurado',
            font=(FONT, 8), text_color=TEXT2, width=25,
            command=self._toggle_cloud_consent)
        self.cloud_consent.pack(side='left', padx=(0, 8))
        if self.settings.get('cloud_telemetry_consent'):
            self.cloud_consent.select()
        self.enrollment_entry = ctk.CTkEntry(
            privacy_row, show='●', placeholder_text='Código de un uso',
            width=182, height=28, font=(FONT, 8))
        self.enrollment_entry.pack(side='left', padx=(0, 6))
        ctk.CTkButton(privacy_row, text='Vincular equipo', width=110, height=28,
                      fg_color='transparent', border_width=1, border_color=BORDER,
                      text_color=TEXT2, command=self._save_cloud_access).pack(side='right')

        # Accesos explícitos a la prueba local, no arrancan nada al abrir el panel.
        helpers = ctk.CTkFrame(cloud_bar, fg_color='transparent')
        helpers.pack(fill='x', padx=11, pady=(0, 8))
        ctk.CTkLabel(helpers, text='1. Puente  ·  2. Código  ·  3. Permiso  ·  4. Chat',
                     font=(FONT, 8), text_color=MUTED).pack(side='left', padx=(0, 12))
        ctk.CTkButton(helpers, text='Iniciar puente', width=98, height=26,
                      fg_color='transparent', border_width=1, border_color=BORDER,
                      text_color=TEXT2, command=lambda: self._open_cloud_helper('start')).pack(side='left', padx=(0, 6))
        ctk.CTkButton(helpers, text='Crear código', width=90, height=26,
                      fg_color='transparent', border_width=1, border_color=BORDER,
                      text_color=TEXT2, command=lambda: self._open_cloud_helper('pair')).pack(side='left')

        body = ctk.CTkFrame(self, fg_color='transparent')
        self.body_frame = body
        body.pack(fill='both', expand=True, padx=24, pady=(0, 20))
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=0, minsize=238)
        body.grid_rowconfigure(0, weight=1)

        # Área conversacional principal.
        assistant = ctk.CTkFrame(
            body, fg_color=SURFACE, border_width=1, border_color=BORDER, corner_radius=14
        )
        assistant.grid(row=0, column=0, sticky='nsew', padx=(0, 10))
        assistant.grid_rowconfigure(1, weight=1)
        assistant.grid_columnconfigure(0, weight=1)

        row = ctk.CTkFrame(assistant, fg_color='transparent')
        row.grid(row=0, column=0, sticky='ew', padx=16, pady=(13, 8))
        ctk.CTkLabel(
            row, text='Conversación con CorePulse AI', font=(FONT, 13, 'bold'), text_color=TEXT
        ).pack(side='left')
        self.clear_button = ctk.CTkButton(
            row, text='Limpiar', width=72, height=30, corner_radius=8,
            fg_color='transparent', hover_color=SURFACE2, border_width=1, border_color=BORDER,
            text_color=TEXT2, font=(FONT, 8, 'bold'), command=self._clear_conversation,
        )
        self.clear_button.pack(side='right')

        self.chat_scroll = ctk.CTkScrollableFrame(
            assistant, fg_color=BG, border_width=1, border_color=BORDER, corner_radius=10,
            scrollbar_button_color=SURFACE2, scrollbar_button_hover_color=CYAN2,
        )
        self.chat_scroll.grid(row=1, column=0, sticky='nsew', padx=16, pady=(0, 8))
        self.chat_scroll.grid_columnconfigure(0, weight=1)

        self._append_output(
            'CorePulse AI',
            'Hola. Puedo ayudarte a interpretar CPU, GPU, RAM, almacenamiento, temperaturas y rendimiento usando los datos que CorePulse tenga disponibles.',
            source='Datos en vivo de CorePulse',
        )

        # Accesos rápidos: compactos y secundarios, no dominan la pantalla.
        quick = ctk.CTkFrame(assistant, fg_color='transparent')
        quick.grid(row=2, column=0, sticky='ew', padx=16, pady=(0, 7))
        ctk.CTkLabel(quick, text='Consultas rápidas', font=(FONT, 8, 'bold'), text_color=MUTED).pack(side='left', padx=(0, 8))
        for label, prompt in self.QUICK_PROMPTS:
            ctk.CTkButton(
                quick, text=label, height=28, corner_radius=8,
                fg_color='transparent', hover_color=SURFACE2, border_width=1,
                border_color=BORDER, text_color=TEXT2, font=(FONT, 8),
                command=lambda q=prompt: self._submit_quick_prompt(q),
            ).pack(side='left', padx=(0, 5))

        # Composer fijo al pie.
        composer = ctk.CTkFrame(
            assistant, fg_color=SURFACE2, border_width=1, border_color=BORDER, corner_radius=11
        )
        composer.grid(row=3, column=0, sticky='ew', padx=16, pady=(0, 14))
        self.question_entry = ctk.CTkEntry(
            composer, placeholder_text='Pregunta por una métrica, un problema o el estado de tu equipo…',
            height=40, corner_radius=9, fg_color=BG, border_color=BORDER,
            text_color=TEXT, placeholder_text_color=MUTED, font=(FONT, 9),
        )
        self.question_entry.pack(side='left', fill='x', expand=True, padx=(8, 7), pady=8)
        self.question_entry.bind('<Return>', self._on_enter)
        self.ask_button = ctk.CTkButton(
            composer, text='Enviar  →', width=94, height=40, corner_radius=9,
            fg_color=CYAN2, hover_color=CYAN, border_width=0,
            text_color=TEXT, font=(FONT, 8, 'bold'), command=self._ask,
        )
        self.ask_button.pack(side='right', padx=(0, 8), pady=8)

        # Contexto real del equipo, separado del chat para dar trazabilidad visual.
        context_rail = ctk.CTkFrame(
            body, fg_color=SURFACE, border_width=1, border_color=BORDER, corner_radius=14, width=238
        )
        context_rail.grid(row=0, column=1, sticky='nsew')
        context_rail.grid_propagate(False)

        ctk.CTkLabel(
            context_rail, text='CONTEXTO DEL EQUIPO', font=(FONT, 8, 'bold'),
            text_color=CYAN, anchor='w'
        ).pack(fill='x', padx=14, pady=(14, 2))
        ctk.CTkLabel(
            context_rail, text='Evidencia disponible ahora', font=(FONT, 13, 'bold'),
            text_color=TEXT, anchor='w'
        ).pack(fill='x', padx=14, pady=(0, 10))

        for key, title, accent in (
            ('cpu', 'CPU', CYAN),
            ('gpu', 'GPU', '#a855f7'),
            ('ram', 'RAM', GREEN),
            ('storage', 'SSD / Disco', AMBER),
        ):
            self._build_context_card(context_rail, key, title, accent)

        ctk.CTkFrame(context_rail, fg_color=BORDER, height=1).pack(fill='x', padx=14, pady=(10, 10))
        ctk.CTkLabel(
            context_rail,
            text='CorePulse AI no completa sensores ausentes. Si un dato no existe, se muestra como N/A.',
            font=(FONT, 8), text_color=TEXT2, anchor='w', justify='left', wraplength=205,
        ).pack(fill='x', padx=14, pady=(0, 8))
        self.analyze_button = ctk.CTkButton(
            context_rail, text='Analizar mi equipo', height=34, corner_radius=9,
            fg_color='transparent', hover_color=SURFACE2, border_width=1,
            border_color=CYAN, text_color=TEXT, font=(FONT, 8, 'bold'),
            command=self._analyze,
        )
        self.analyze_button.pack(fill='x', padx=14, pady=(0, 14))

    def _set_connection_state(self, label: str, help_text: str = '', color: str = AMBER):
        self.connection_state.configure(text='● ' + label, text_color=color)
        if help_text:
            self.connection_help.configure(text=help_text)
        self.connect_button.configure(text=('Comprobar IA' if label == 'Conectada' else 'Conectar IA'))

    def _sync_consent_controls(self):
        if self.settings.get('base_url') not in ('', LOCAL_GROQ_BRIDGE_URL):
            self.simple_consent.configure(text='Permito enviar datos al proveedor elegido')
        else:
            self.simple_consent.configure(text='Permito enviar preguntas y datos a Groq')
        enabled = self.settings.get('cloud_telemetry_consent') is True
        for checkbox in (self.simple_consent, self.cloud_consent):
            checkbox.select() if enabled else checkbox.deselect()

    def _toggle_simple_consent(self):
        # La casilla es una autorización explícita, nunca un cambio silencioso de proveedor.
        desired = bool(self.simple_consent.get())
        if desired and not self.settings.get('base_url'):
            self.settings = save_ai_settings({'base_url': LOCAL_GROQ_BRIDGE_URL,
                                              'local_groq_bridge': True,
                                              'local_compatible_bridge': False})
            self.cloud_url_entry.delete(0, 'end')
            self.cloud_url_entry.insert(0, LOCAL_GROQ_BRIDGE_URL)
        self.settings = save_ai_settings({'cloud_telemetry_consent': desired})
        if not desired:
            self._investigation_samples.clear()
        self._sync_consent_controls()
        self._connect_seq += 1  # invalidar intentos automáticos anteriores
        self._request_seq += 1
        self._set_busy(False)  # no dejar la IU bloqueada tras revocar durante la conexión
        if self.settings.get('cloud_telemetry_consent'):
            self.service_line.configure(text='Permiso activado para la conexión seleccionada.', text_color=GREEN)
            self._set_connection_state('Listo para conectar', 'Pulsa Conectar IA para iniciar la sesión.', AMBER)
        else:
            self.service_line.configure(text='Permiso retirado. No se enviarán nuevas preguntas ni sensores.', text_color=AMBER)
            self._set_connection_state('Desconectada', 'El chat no transmite datos sin autorización.', AMBER)

    def _quick_connect(self):
        # V473: flujo asistido sin compartir secretos ni asumir permisos cloud.
        if self._busy:
            return
        if not load_ai_enabled():
            self._set_connection_state('IA apagada', 'Actívala desde el control de CorePulse AI.', AMBER)
            return
        if not self.settings.get('base_url'):
            # Groq es la selección inicial, no una dependencia del motor propio.
            self._use_groq_trial()
        if not self.settings.get('cloud_telemetry_consent'):
            self._set_connection_state('Falta autorización', 'Marca la casilla antes de conectar.', AMBER)
            self.service_line.configure(text='Autoriza explícitamente el envío a la nube para continuar.', text_color=AMBER)
            return
        if self.settings.get('base_url') != LOCAL_GROQ_BRIDGE_URL:
            self._set_connection_state('Ajustes avanzados', 'Conecta tu otro proveedor desde Configuración avanzada.', AMBER)
            self._toggle_connection_settings(force_open=True)
            return
        self._connect_seq += 1
        seq = self._connect_seq
        selected = dict(self.settings)
        self._set_busy(True, 'Conectando CorePulse AI con Groq…')
        self._set_connection_state('Conectando…', 'Verificando el puente y la vinculación.', CYAN)

        def worker():
            def start_bridge():
                return self._launch_bridge_for_quick_connect()
            result = quick_connect_local_groq(selected, start_bridge=start_bridge)
            try:
                self.after(0, lambda: self._finish_quick_connect(result, seq, selected))
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True, name='CorePulseAIQuickConnect').start()

    def _launch_bridge_for_quick_connect(self):
        # Arranque local acotado a un BAT incluido en el ZIP, sin shells arbitrarias.
        if os.name != 'nt':
            return False
        root = Path(__file__).resolve().parents[1]
        script = root / 'herramientas' / 'ia' / '11_INICIAR_PUENTE_GROQ_V463.bat'
        if not script.is_file():
            return False
        try:
            subprocess.Popen(['cmd.exe', '/c', str(script)], cwd=str(root),
                             creationflags=getattr(subprocess, 'CREATE_NEW_CONSOLE', 0))
            return True
        except OSError:
            return False

    def _finish_quick_connect(self, result, seq, selected):
        if seq != self._connect_seq:
            return
        self._set_busy(False)
        if (not load_ai_enabled() or
                not self.settings.get('cloud_telemetry_consent') or
                self.settings.get('base_url') != selected.get('base_url')):
            self._set_connection_state('Sin confirmar', 'La configuración cambió durante la conexión.', AMBER)
            return
        if result.get('ok'):
            self._set_connection_state('Conectada', 'GPT-OSS 120B vía Groq · chat disponible.', GREEN)
            self.service_line.configure(text='IA conectada. Puedes enviar tu primera pregunta.', text_color=GREEN)
        else:
            self._set_connection_state('No conectada', result.get('hint') or 'Revisa Configuración avanzada.', AMBER)
            self.service_line.configure(text=result.get('error') or 'No se pudo conectar.', text_color=AMBER)

    def _toggle_connection_settings(self, force_open=False):
        """Oculta controles técnicos al chatear; nunca altera consentimiento."""
        if self._connection_expanded and not force_open:
            self.cloud_bar.pack_forget()
            self._connection_expanded = False
        elif not self._connection_expanded:
            self.cloud_bar.pack(fill='x', padx=24, pady=(0, 8), before=self.body_frame)
            self._connection_expanded = True

    def _build_context_card(self, parent, key: str, title: str, accent: str):
        card = ctk.CTkFrame(parent, fg_color=BG, border_width=1, border_color=BORDER, corner_radius=10)
        card.pack(fill='x', padx=12, pady=4)
        top = ctk.CTkFrame(card, fg_color='transparent')
        top.pack(fill='x', padx=11, pady=(9, 1))
        ctk.CTkLabel(top, text='■', width=12, font=(FONT, 8), text_color=accent).pack(side='left', padx=(0, 5))
        ctk.CTkLabel(top, text=title, font=(FONT, 9, 'bold'), text_color=TEXT).pack(side='left')
        value = ctk.CTkLabel(card, text='N/A', font=(FONT, 11, 'bold'), text_color=accent, anchor='w')
        value.pack(fill='x', padx=11, pady=(2, 0))
        detail = ctk.CTkLabel(card, text='Sin lectura disponible', font=(FONT, 8), text_color=TEXT2, anchor='w', wraplength=195)
        detail.pack(fill='x', padx=11, pady=(0, 9))
        self._context_value_labels[key] = (value, detail)

    def _use_groq_trial(self):
        # Activación local sólo para pruebas; el proveedor LLM continúa en la nube.
        # Al cambiar el destino se revoca cualquier consentimiento anterior.
        self._investigation_samples.clear()
        self.settings = save_ai_settings({'local_groq_bridge': True, 'local_compatible_bridge': False,
                                          'base_url': LOCAL_GROQ_BRIDGE_URL})
        self._connect_seq += 1
        self._set_busy(False)
        self.cloud_url_entry.delete(0, 'end')
        self.cloud_url_entry.insert(0, LOCAL_GROQ_BRIDGE_URL)
        self._sync_consent_controls()
        self.service_line.configure(
            text='Prueba Groq: inicia el puente V463; luego autoriza el envío a Groq.', text_color=AMBER)
        self._refresh_status_async()

    def _use_compatible_trial(self):
        # La inferencia está en otro servidor; sólo el puente HTTP loopback corre en Windows.
        # Puerto distinto => anulación automática del consentimiento y token anteriores.
        self._investigation_samples.clear()
        self.settings = save_ai_settings({'local_groq_bridge': False, 'local_compatible_bridge': True,
                                          'base_url': LOCAL_COMPAT_BRIDGE_URL})
        self._connect_seq += 1
        self._set_busy(False)
        self.cloud_url_entry.delete(0, 'end')
        self.cloud_url_entry.insert(0, LOCAL_COMPAT_BRIDGE_URL)
        self._sync_consent_controls()
        self.service_line.configure(
            text='Alternativo: configura el servidor con BAT 18, inicia BAT 19 y autoriza el envío.', text_color=AMBER)
        self._refresh_status_async()

    def _save_cloud_server(self):
        from core.ai_client import _allowed_base_url
        url = self.cloud_url_entry.get().strip()
        if not _allowed_base_url(url, allow_local_groq_bridge=self.settings.get('local_groq_bridge') is True,
                allow_local_compatible_bridge=self.settings.get('local_compatible_bridge') is True):
            self.service_line.configure(text='Se requiere HTTPS o un puente autorizado con su botón.',
                                        text_color=AMBER)
            return
        self._investigation_samples.clear()
        self.settings = save_ai_settings({'base_url': url, 'local_groq_bridge': url == LOCAL_GROQ_BRIDGE_URL,
                                          'local_compatible_bridge': url == LOCAL_COMPAT_BRIDGE_URL})
        self._connect_seq += 1
        self._set_busy(False)
        self._sync_consent_controls()
        self.service_line.configure(text='Servidor guardado. Autoriza el envío de datos para conectarlo.',
                                    text_color=AMBER)
        self._refresh_status_async()

    def _toggle_cloud_consent(self):
        enabled = bool(self.cloud_consent.get())
        self._connect_seq += 1
        self._request_seq += 1  # cancelación lógica de respuestas pendientes
        self._set_busy(False)
        if enabled and not self.settings.get('base_url'):
            self.cloud_consent.deselect()
            self._sync_consent_controls()
            self.service_line.configure(text='Configura primero el servidor CorePulse AI.', text_color=AMBER)
            return
        self.settings = save_ai_settings({'cloud_telemetry_consent': enabled})
        if not enabled:
            self._investigation_samples.clear()
        self._sync_consent_controls()
        if enabled and not self.settings.get('cloud_telemetry_consent'):
            self.cloud_consent.deselect()
            self._sync_consent_controls()
            self.service_line.configure(text='Configura primero el modelo alternativo con BAT 18.', text_color=AMBER)
            return
        self.service_line.configure(
            text=('Permiso cloud activado para el servidor indicado.' if enabled else
                  'Permiso revocado: CorePulse no enviará nuevas solicitudes.'),
            text_color=GREEN if enabled else AMBER)
        self._refresh_status_async()

    def _open_cloud_helper(self, action: str):
        """Solo abre BATs empaquetados y elegidos explícitamente por el usuario."""
        alternative = self.settings.get('base_url') == LOCAL_COMPAT_BRIDGE_URL
        allowed = {
            (False, 'start'): '11_INICIAR_PUENTE_GROQ_V463.bat',
            (False, 'pair'): '12_CREAR_CODIGO_GROQ_V463.bat',
            (True, 'start'): '19_INICIAR_PUENTE_COMPATIBLE_V472.bat',
            (True, 'pair'): '20_CREAR_CODIGO_COMPATIBLE_V472.bat',
        }
        name = allowed.get((alternative, action))
        root = Path(__file__).resolve().parents[1]
        script = root / 'herramientas' / 'ia' / (name or '')
        if name is None or os.name != 'nt' or not script.is_file():
            self.service_line.configure(text='Ejecuta los auxiliares desde la carpeta completa en Windows.', text_color=AMBER)
            return
        if not load_ai_enabled():
            self.service_line.configure(text='Activa CorePulse AI antes de iniciar el puente.', text_color=AMBER)
            return
        if action == 'start':
            port = 8766 if alternative else 8765
            try:
                with socket.create_connection(('127.0.0.1', port), timeout=0.25):
                    self.service_line.configure(text=f'Puerto {port} ocupado: verifica qué servicio está funcionando.', text_color=AMBER)
                    return
            except OSError:
                pass
        try:
            subprocess.Popen(['cmd.exe', '/c', str(script)], cwd=str(root),
                             creationflags=getattr(subprocess, 'CREATE_NEW_CONSOLE', 0))
            self.service_line.configure(text='Auxiliar iniciado en CMD. No cierres la ventana si es el puente.', text_color=CYAN)
        except OSError:
            self.service_line.configure(text='No se pudo abrir el auxiliar de la carpeta de CorePulse.', text_color=AMBER)

    def _save_cloud_access(self):
        if not self.settings.get('base_url'):
            self.service_line.configure(text='Primero selecciona Groq (pruebas) o configura tu servidor HTTPS.',
                                        text_color=AMBER)
            return
        secret = self.enrollment_entry.get().strip()
        if secret:
            if not save_secret('corepulse_cloud_enrollment', secret):
                self.service_line.configure(text='No se pudo proteger el código en Credential Manager.', text_color=AMBER)
                return
            self.enrollment_entry.delete(0, 'end')
        elif not paired_for_endpoint(self.settings, allow_enrollment=True):
            self.service_line.configure(text='Introduce el código temporal de vinculación.', text_color=AMBER)
            return
        if self.settings.get('cloud_telemetry_consent') is not True:
            self.service_line.configure(text='Código guardado. Marca el permiso de nube y pulsa Vincular equipo.',
                                        text_color=AMBER)
            return
        self._start_pairing()

    def _start_pairing(self):
        if self._busy:
            self.service_line.configure(text='Espera a que termine la comprobación actual y vuelve a pulsar Vincular.', text_color=AMBER)
            return
        self._set_busy(True, 'Vinculando equipo mediante código de un solo uso…')
        request_settings = dict(self.settings)
        self._status_seq += 1
        def worker():
            try:
                result = ensure_registration(request_settings)
            except Exception:
                result = {'ok': False, 'error': 'Error al conectar con el servicio de vinculación.'}
            try:
                self.after(0, lambda: self._finish_pairing(result, request_settings))
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True, name='CorePulseAIPairing').start()

    def _finish_pairing(self, result, request_settings):
        self._set_busy(False)
        if (not load_ai_enabled() or self.settings.get('base_url') != request_settings.get('base_url') or
                not self.settings.get('cloud_telemetry_consent')):
            self.service_line.configure(text='Se modificó el permiso o servidor; vuelve a verificar la vinculación.', text_color=AMBER)
            return
        if result.get('ok'):
            self.service_line.configure(text='Equipo vinculado. Ya puedes escribir en el chat de CorePulse AI.', text_color=GREEN)
            self._refresh_status_async()
        else:
            error = str(result.get('error') or 'Código inválido o servicio no disponible.')
            self.service_line.configure(text='No se pudo vincular: ' + error[:180], text_color=AMBER)

    def _refresh_all(self):
        self._refresh_context_cards()
        self._refresh_status_async()

    def _set_busy(self, value: bool, message: str = ''):
        self._busy = bool(value)
        state = 'disabled' if value else 'normal'
        for widget in (self.refresh_button, self.analyze_button, self.ask_button, self.clear_button, self.connect_button):
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
        self._status_seq += 1
        seq = self._status_seq
        request_settings = dict(self.settings)

        def worker():
            result = service_status(request_settings)
            if result.get('ok'):
                # La disponibilidad de Groq no prueba que este equipo esté
                # vinculado. Nunca anunciar "conectado" solo por token presente.
                result['pairing_status'] = pairing_status(request_settings)
            try:
                self.after(0, lambda: self._finish_status(result, seq, request_settings))
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True, name='CorePulseAIStatus').start()

    def _finish_status(self, result, seq=None, request_settings=None):
        if seq is not None and (seq != self._status_seq or
                (request_settings or {}).get('base_url') != self.settings.get('base_url') or
                (request_settings or {}).get('cloud_telemetry_consent') != self.settings.get('cloud_telemetry_consent')):
            self._set_busy(False)
            self._refresh_status_async()
            return
        self._set_busy(False)
        if result.get('ok'):
            model_ready = bool(result.get('model_ready'))
            model_configured = bool(result.get('model_configured', model_ready))
            pairing = result.get('pairing_status') or {}
            if model_ready and not pairing.get('ok'):
                self._set_connection_state('Falta vincular', 'Pulsa Conectar IA para completar la vinculación.', AMBER)
                self.status_chip.configure(text='● Falta vincular', text_color=AMBER, fg_color=SURFACE2)
                if pairing.get('state') == 'CLOUD_PAIRING_UNCONFIRMED':
                    self.service_line.configure(text='Modelo cloud disponible, pero no se pudo comprobar el vínculo; pulsa Actualizar.', text_color=AMBER)
                else:
                    self.service_line.configure(text='Modelo cloud disponible. Comprueba el código temporal y pulsa Vincular equipo.', text_color=AMBER)
            elif model_ready:
                self._set_connection_state('Conectada', 'GPT-OSS 120B está disponible para el chat.', GREEN)
                self.status_chip.configure(text='● IA nube conectada', text_color=GREEN, fg_color=SURFACE2)
                self.service_line.configure(
                    text=('GPT-OSS 120B vía Groq Cloud conectado. Respuestas sujetas a REAL_OR_NA.'
                          if result.get('model_provider') == 'groq' else
                          'CorePulse AI está listo. Las respuestas usarán la evidencia actual del equipo.'),
                    text_color=GREEN,
                )
            elif model_configured:
                self._set_connection_state('Servicio no listo', 'Vuelve a pulsar Conectar IA.', AMBER)
                self.status_chip.configure(text='● Modo seguro', text_color=AMBER, fg_color=SURFACE2)
                self.service_line.configure(
                    text='El motor generativo aún no responde. CorePulse mantiene disponible el modo de evidencia segura.',
                    text_color=AMBER,
                )
            else:
                self._set_connection_state('Modelo sin configurar', 'Configura la clave Groq una sola vez.', AMBER)
                self.status_chip.configure(text='● Modo seguro', text_color=AMBER, fg_color=SURFACE2)
                self.service_line.configure(
                    text=('Groq no está configurado: guarda tu clave con herramientas\\ia\\10_CONFIGURAR_GROQ_V463.bat.'
                          if result.get('model_provider') == 'groq' else
                          'Servicio cloud conectado; no hay LLM remoto disponible (modo seguro).'),
                    text_color=AMBER,
                )
        else:
            state = result.get('state')
            if state == 'CLOUD_CONSENT_REQUIRED':
                self._set_connection_state('Falta autorización', 'Marca la casilla para habilitar la conexión.', AMBER)
            elif state == 'DISABLED':
                self._set_connection_state('IA apagada', 'Puedes activarla desde CorePulse.', AMBER)
            else:
                self._set_connection_state('Sin conectar', 'Pulsa Conectar IA para iniciar el servicio.', AMBER)
            self.status_chip.configure(text='● IA no disponible', text_color=AMBER, fg_color=SURFACE2)
            self.service_line.configure(
                text=str(result.get('error') or 'IA nube no disponible; diagnóstico local activo.'),
                text_color=AMBER,
            )

    def _context(self):
        telemetry = getattr(self.app, 'latest_telemetry', None)
        disks = getattr(self.app, 'latest_disks', None)
        health = getattr(self.app, 'current_live_health', None)
        if not isinstance(telemetry, dict):
            return None
        context = build_runtime_context(telemetry, disks, health)

        # V359 — si ya existe un Diagnóstico Total finalizado, el chat hereda la
        # evaluación determinista, vigencia anual, identidad sanitizada y planes
        # de acción congelados de esa sesión. Así Qwen no vuelve a decidir si hay
        # una falla: sólo explica lo que CorePulse ya certificó.
        diagnostic = getattr(self.app, 'diagnostic_result', None)
        if isinstance(diagnostic, dict):
            complete = diagnostic.get('complete_diagnostic') if isinstance(diagnostic.get('complete_diagnostic'), dict) else {}
            ai = complete.get('ai_analysis') if isinstance(complete.get('ai_analysis'), dict) else diagnostic.get('_ai_analysis') if isinstance(diagnostic.get('_ai_analysis'), dict) else {}
            if isinstance(ai, dict) and ai:
                inventory = ai.get('inventory') if isinstance(ai.get('inventory'), dict) else {}
                device = inventory.get('device') if isinstance(inventory.get('device'), dict) else {}
                assessment = ai.get('deterministic_assessment') if isinstance(ai.get('deterministic_assessment'), dict) else {}
                if assessment:
                    context['deterministic_assessment'] = assessment
                if device:
                    context['device'] = device
                if ai.get('current_year'):
                    context['current_year'] = ai.get('current_year')
        return context

    def _query_snapshot(self):
        """Congela los parámetros reales que pertenecen a UNA consulta.

        El modelo nunca vuelve a leer sensores. La pregunta queda ligada a esta
        fotografía de CorePulse para que una respuesta lenta no mezcle muestras.
        """
        telemetry = copy.deepcopy(getattr(self.app, 'latest_telemetry', None))
        if not isinstance(telemetry, dict) or not telemetry:
            return None
        disks = getattr(self.app, 'latest_disks', [])
        health = getattr(self.app, 'current_live_health', {})
        diagnostic = getattr(self.app, 'diagnostic_result', {})
        try:
            agent_state = self.app.realtime_agent.get_state()
        except Exception:
            agent_state = {}
        return request_snapshot(telemetry, disks, health, diagnostic, agent_state)

    def _refresh_context_cards(self):
        context = self._context()
        if not isinstance(context, dict):
            return
        cpu = context.get('cpu') or {}
        gpu = context.get('gpu') or {}
        ram = context.get('ram') or {}
        storage = context.get('storage') or []

        cpu_value = _fmt_number(cpu.get('usage_percent'), 0, '% uso')
        cpu_detail_parts = []
        if cpu.get('temperature_c') is not None:
            cpu_detail_parts.append(_fmt_number(cpu.get('temperature_c'), 1, ' °C'))
        if cpu.get('frequency_ghz') is not None:
            cpu_detail_parts.append(_fmt_number(cpu.get('frequency_ghz'), 2, ' GHz'))
        self._set_context_card('cpu', cpu_value, ' · '.join(cpu_detail_parts) or 'Temperatura / frecuencia: N/A')

        gpu_value = _fmt_number(gpu.get('usage_percent'), 0, '% uso')
        gpu_detail = _fmt_number(gpu.get('temperature_c'), 1, ' °C') if gpu.get('temperature_c') is not None else 'Temperatura: N/A'
        self._set_context_card('gpu', gpu_value, gpu_detail)

        if ram.get('used_gb') is not None and ram.get('total_gb') is not None:
            ram_value = f"{float(ram['used_gb']):.1f} / {float(ram['total_gb']):.1f} GB"
        else:
            ram_value = _fmt_number(ram.get('usage_percent'), 0, '% uso')
        ram_detail = f"{_fmt_number(ram.get('usage_percent'), 0, '%')} en uso" if ram.get('usage_percent') is not None else 'Uso: N/A'
        self._set_context_card('ram', ram_value, ram_detail)

        disk = storage[0] if storage and isinstance(storage[0], dict) else {}
        disk_value = _fmt_number(disk.get('used_percent'), 0, '% usado')
        disk_parts = []
        if disk.get('temperature_c') is not None:
            disk_parts.append(_fmt_number(disk.get('temperature_c'), 1, ' °C'))
        if disk.get('health_percent') is not None:
            disk_parts.append(_fmt_number(disk.get('health_percent'), 0, '% salud'))
        self._set_context_card('storage', disk_value, ' · '.join(disk_parts) or 'Temperatura / SMART: N/A')

    def _set_context_card(self, key: str, value: str, detail: str):
        labels = self._context_value_labels.get(key)
        if not labels:
            return
        try:
            labels[0].configure(text=value)
            labels[1].configure(text=detail)
        except Exception:
            pass

    def _on_enter(self, _event=None):
        self._ask()
        return 'break'

    def _analyze(self):
        self._run_request('', kind='analyze')

    def _submit_quick_prompt(self, question: str):
        if self._busy:
            return
        self._run_request(question, kind='chat')

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
        # No consumir cuota ni poner información del equipo en la red sin permiso.
        gate = _cloud_gate(self.settings)
        if not gate['ok']:
            self.service_line.configure(text=describe_preflight(gate), text_color=AMBER)
            return
        snapshot = self._query_snapshot()
        # Para preguntas generales se permite contexto vacío: todo hardware será N/A.
        if snapshot is None and kind == 'chat':
            snapshot = request_snapshot({}, [], {}, {}, {})
        if snapshot is None:
            self.service_line.configure(text='Aún no hay mediciones para analizar. Puedes hacer preguntas generales.', text_color=AMBER)
            return

        self._refresh_context_cards()
        self._request_seq += 1
        request_seq = self._request_seq
        history_snapshot = list(self._conversation[-8:])
        previous_samples = list(getattr(self, '_investigation_samples', [])[-5:])
        request_settings = dict(self.settings)
        self._request_endpoint = request_settings.get('base_url')

        if kind == 'chat':
            self._append_output('Tú', question)
            try:
                self.question_entry.delete(0, 'end')
            except Exception:
                pass
            busy_text = 'Analizando tu pregunta con la evidencia actual…'
        else:
            busy_text = 'Analizando el estado actual del equipo…'

        self._set_busy(True, busy_text)

        def worker():
            # V395: el contexto detallado se construye dentro del worker desde la
            # fotografía congelada al pulsar Enviar. CorePulse decide hechos,
            # planes y N/A; el modelo sólo convierte esa evidencia en lenguaje.
            context = build_query_context(
                snapshot['telemetry'],
                snapshot['disks'],
                snapshot['health'],
                question=question,
                agent_state=snapshot['agent_state'],
                diagnostic_result=snapshot['diagnostic_result'],
                analysis_request=(kind == 'analyze'),
            )
            # V476: historial efímero de consultas previas, sólo si existe permiso.
            sample = query_sample(context)
            context['observation_history'] = previous_samples
            try:
                if kind == 'chat':
                    result = chat_context(context, question=question, history=history_snapshot, settings=request_settings)
                else:
                    result = analyze_context(context, question='', settings=request_settings)
            except Exception:
                result = {'ok': False, 'error': 'Error interno al preparar la consulta.'}
            try:
                self.after(0, lambda: self._finish_request(result, request_seq, kind, question, sample))
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True, name='CorePulseAIRequest').start()

    def _finish_request(self, result, request_seq, kind, question, sample=None):
        if request_seq != self._request_seq:
            return
        self._set_busy(False)
        if (not load_ai_enabled() or not self.settings.get('cloud_telemetry_consent') or
                self._request_endpoint != self.settings.get('base_url')):
            self.service_line.configure(text='La consulta terminó con el permiso revocado; no se mostrará la respuesta.', text_color=AMBER)
            return
        if result.get('ok'):
            self._investigation_samples = append_sample(getattr(self, '_investigation_samples', []), sample)
            mode = str(result.get('mode') or 'corepulse-ai')
            answer = _plain_ai_text(result.get('text') or '')
            source = ('CorePulse AI Cloud · respuesta filtrada automáticamente (no certifica diagnóstico)' if mode == 'model' else
                      'Búsqueda pública de tutoriales · videos no verificados' if mode == 'curated_search' else
                      'Orientación segura de CorePulse · sin datos inventados')
            self._append_output('CorePulse AI', answer, source=source)
            if kind == 'chat':
                self._conversation.extend([
                    {'role': 'user', 'content': question[:1800]},
                    {'role': 'assistant', 'content': answer[:1800]},
                ])
                self._conversation = self._conversation[-8:]
            remaining = result.get('remaining_today')
            suffix = f' · {remaining} consultas disponibles hoy' if isinstance(remaining, int) else ''
            guardrails = result.get('guardrails') if isinstance(result.get('guardrails'), dict) else {}
            codes = guardrails.get('codes') or []
            if mode != 'model' and any(str(c).startswith(('UNSUPPORTED_', 'UNVERIFIED_', 'FPS_', 'SEARCH_', 'UNAUTHORIZED_')) for c in codes):
                state = 'La respuesta remota incluyó datos no verificables; se mostró una orientación segura.'
            elif mode != 'model' and 'MODEL_ERROR' in codes:
                state = 'Modelo remoto no disponible. Se mostró evidencia segura.'
            else:
                state = ('Salida del modelo aceptada por controles automáticos (no certifica diagnóstico).' if mode == 'model' else
                         'Búsqueda preparada localmente; YouTube no se ha consultado.' if mode == 'curated_search' else
                         'Respuesta completada en modo seguro con evidencia real.')
            self.service_line.configure(text=state + suffix, text_color=GREEN if mode == 'model' else AMBER)
        else:
            error = str(result.get('error') or 'Error desconocido.')
            self._append_output(
                'CorePulse AI',
                'No pude completar esta consulta. ' + error,
                source='Solicitud no completada',
            )
            if '429' in error:
                self.service_line.configure(text='Límite temporal del servicio alcanzado. La telemetría local sigue disponible.', text_color=AMBER)
            else:
                self.service_line.configure(text='CorePulse AI no pudo completar la solicitud.', text_color=RED)

    def _clear_conversation(self):
        if self._busy:
            return
        self._conversation.clear()
        self._investigation_samples.clear()
        self._set_output(
            'Conversación limpia. Puedes preguntarme por una métrica concreta o pedirme un análisis del equipo.'
        )

    def _append_output(self, author: str, text: str, source: str = ''):
        """Añade una burbuja profesional al chat sin alterar la evidencia."""
        is_user = author.strip().lower() in {'tú', 'tu', 'usuario'}
        row = ctk.CTkFrame(self.chat_scroll, fg_color='transparent')
        row.pack(fill='x', padx=4, pady=5)

        bubble = ctk.CTkFrame(
            row,
            fg_color=SURFACE2 if is_user else SURFACE,
            border_width=1,
            border_color=CYAN2 if is_user else BORDER,
            corner_radius=11,
        )
        if is_user:
            bubble.pack(side='right', anchor='e', padx=(70, 4))
        else:
            bubble.pack(side='left', anchor='w', padx=(4, 52))

        heading = 'TÚ' if is_user else 'COREPULSE AI'
        ctk.CTkLabel(
            bubble, text=heading, font=(FONT, 8, 'bold'),
            text_color=CYAN if not is_user else TEXT2, anchor='w'
        ).pack(fill='x', padx=12, pady=(9, 2))
        ctk.CTkLabel(
            bubble, text=display_reply_without_raw_youtube_search(str(text).strip()), font=(FONT, 11), text_color=TEXT,
            anchor='w', justify='left', wraplength=630,
        ).pack(fill='x', padx=12, pady=(0, 4 if source else 10))
        tutorial_search = safe_youtube_search_from_reply(text) if not is_user else None
        if tutorial_search:
            ctk.CTkButton(
                bubble, text='Abrir búsqueda en YouTube  ↗',
                command=lambda url=tutorial_search: webbrowser.open(url),
                height=29, width=202, fg_color=CYAN2, text_color=TEXT,
            ).pack(anchor='w', padx=12, pady=(3, 8))
        if source and not is_user:
            ctk.CTkLabel(
                bubble, text='●  ' + source, font=(FONT, 7), text_color=MUTED, anchor='w'
            ).pack(fill='x', padx=12, pady=(0, 8))

        self._message_widgets.append(row)
        try:
            self.after(40, lambda: self.chat_scroll._parent_canvas.yview_moveto(1.0))
        except Exception:
            pass

    def _set_output(self, text):
        for widget in list(self._message_widgets):
            try:
                widget.destroy()
            except Exception:
                pass
        self._message_widgets.clear()
        self._append_output('CorePulse AI', str(text), source='Datos en vivo de CorePulse')


__all__ = ['CorePulseAIPanel']
