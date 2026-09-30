"""Compatibilidad V328: CorePulse AI ahora usa backend propio.

No contiene selectores OpenAI/Groq, claves de proveedor ni modelos locales.
"""
from core.ai_client import (
    DEFAULT_BASE_URL,
    load_ai_settings,
    save_ai_settings,
    service_status,
    ensure_registration,
    build_runtime_context,
    analyze_context,
    chat_context,
)

__all__ = [
    'DEFAULT_BASE_URL', 'load_ai_settings', 'save_ai_settings', 'service_status',
    'ensure_registration', 'build_runtime_context', 'analyze_context', 'chat_context',
]
