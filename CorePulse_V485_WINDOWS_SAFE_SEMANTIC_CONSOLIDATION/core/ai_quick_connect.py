"""V473 — Asistente de conexión local de CorePulse AI Cloud.

El clic del usuario configura el flujo, pero NUNCA equivale a autorizar datos:
se exige un consentimiento independiente en ai_settings.json. Las funciones
administrativas sólo se invocan en la prueba local Groq (puerto 8765). Para un
servidor remoto el código debe emitirlo su administrador.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable

from core.ai_client import (
    LOCAL_GROQ_BRIDGE_URL, ENROLLMENT_NAME, _cloud_gate,
    delete_secret, ensure_registration, load_ai_settings, pairing_status,
    save_secret, service_status,
)
from core.ai_user_control import load_ai_enabled


def connection_plan(settings: dict) -> str:
    if not load_ai_enabled():
        return 'disabled'
    if not settings.get('cloud_telemetry_consent'):
        return 'consent_required'
    if settings.get('base_url') != LOCAL_GROQ_BRIDGE_URL:
        return 'advanced'
    return 'groq'


def _authorized_snapshot(snapshot: dict) -> bool:
    """Recomprueba estado persistente: revocar consentimiento interrumpe el asistente."""
    if not load_ai_enabled():
        return False
    current = load_ai_settings()
    return bool(current.get('cloud_telemetry_consent') and
                current.get('base_url') == snapshot.get('base_url') and
                current.get('local_groq_bridge') is True)


def _issue_local_code() -> str:
    """Emisión local bajo la cuenta de Windows. Nunca viaja al chat o a Groq."""
    if os.name != 'nt':
        return ''
    root = Path(__file__).resolve().parents[1]
    service_dir = root / 'CorePulse_AI_Server'
    if not (service_dir / 'app' / 'admin.py').is_file():
        return ''
    env = dict(os.environ)
    env['COREPULSE_MODEL_PROVIDER'] = 'groq'
    try:
        proc = subprocess.run(
            [sys.executable, '-m', 'app.admin', 'issue', '--minutes', '10'],
            cwd=str(service_dir), env=env, capture_output=True, text=True,
            timeout=12, check=False, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
        if proc.returncode:
            return ''
        match = re.search(r'cp-[A-Za-z0-9_-]{25,100}', proc.stdout)
        return match.group(0) if match else ''
    except (OSError, subprocess.SubprocessError):
        return ''


def quick_connect_local_groq(settings: dict, *, start_bridge: Callable[[], bool],
                              poll_seconds: float = 48, sleep: Callable[[float], None] = time.sleep,
                              clock: Callable[[], float] = time.monotonic,
                              issue_code: Callable[[], str] = _issue_local_code) -> dict:
    """Conectar sin pasos técnicos, nunca evitando consentimiento o validación de vínculo.

    No ejecuta modelos en el PC. Puede arrancar el puente local ligero; Groq
    continúa alojando la inferencia pesada. No crea códigos para servidores
    remotos, cuyos administradores conservan el control.
    """
    if connection_plan(settings) != 'groq' or not _cloud_gate(settings).get('ok'):
        return {'ok': False, 'error': 'Primero autoriza el envío a Groq en la casilla.',
                'hint': 'Revisa el permiso o el proveedor en Configuración avanzada.'}
    if not _authorized_snapshot(settings):
        return {'ok': False, 'error': 'La autorización de datos cambió; no se conectó.',
                'hint': 'Vuelve a autorizar antes de conectar.'}
    result = service_status(settings)
    if not result.get('ok'):
        if not start_bridge():
            return {'ok': False, 'error': 'No se pudo iniciar el puente de Groq.',
                    'hint': 'Comprueba Python y abre Configuración avanzada.'}
        deadline = clock() + max(0.0, float(poll_seconds))
        while clock() < deadline:
            sleep(1.0)
            if not _authorized_snapshot(settings):
                return {'ok': False, 'error': 'Conexión detenida porque se retiró el permiso.'}
            result = service_status(settings)
            if result.get('ok'):
                break
    if not result.get('ok'):
        return {'ok': False, 'error': 'El puente no respondió a tiempo.',
                'hint': 'Espera a que termine de iniciar y vuelve a pulsar Conectar IA.'}
    if result.get('model_provider') != 'groq':
        return {'ok': False, 'error': 'El servicio de este puerto no es el puente Groq esperado.',
                'hint': 'Cierra el servicio incorrecto y revisa Configuración avanzada.'}
    if not result.get('model_configured', False):
        return {'ok': False, 'error': 'Falta configurar la clave gratuita de Groq en este equipo.',
                'hint': 'Una sola vez: ejecuta herramientas\\ia\\10_CONFIGURAR_GROQ_V463.bat desde la carpeta de CorePulse.'}
    if not result.get('model_ready', False):
        return {'ok': False, 'error': 'El modelo en la nube todavía no responde.',
                'hint': 'Comprueba tu conexión a Internet y la clave de Groq.'}
    if not _authorized_snapshot(settings):
        return {'ok': False, 'error': 'Conexión detenida porque se retiró el permiso.'}
    paired = pairing_status(settings)
    if paired.get('ok'):
        return {'ok': True, 'state': 'CLOUD_PAIRED', 'new_pairing': False}
    code = issue_code()
    if not code or not re.fullmatch(r'cp-[A-Za-z0-9_-]{25,100}', code):
        return {'ok': False, 'error': 'No se pudo crear un vínculo temporal de forma automática.',
                'hint': 'Abre Configuración avanzada para crear y pegar un código.'}
    if not _authorized_snapshot(settings):
        return {'ok': False, 'error': 'Conexión detenida porque se retiró el permiso.'}
    if not save_secret(ENROLLMENT_NAME, code):
        return {'ok': False, 'error': 'Windows no pudo guardar el vínculo temporal.',
                'hint': 'Revisa Windows Credential Manager.'}
    try:
        result = ensure_registration(settings)
    finally:
        # No dejar códigos de uso único almacenados aunque el servicio falle.
        delete_secret(ENROLLMENT_NAME)
    if not result.get('ok'):
        return {'ok': False, 'error': 'El puente no aceptó la vinculación automática.',
                'hint': 'Revisa Configuración avanzada o vuelve a pulsar Conectar IA.'}
    if not _authorized_snapshot(settings):
        return {'ok': False, 'error': 'Se retiró el permiso antes de finalizar.'}
    paired = pairing_status(settings)
    if not paired.get('ok'):
        return {'ok': False, 'error': 'No fue posible confirmar la sesión después de vincular.',
                'hint': 'Vuelve a pulsar Conectar IA.'}
    return {'ok': True, 'state': 'CLOUD_PAIRED', 'new_pairing': True}
