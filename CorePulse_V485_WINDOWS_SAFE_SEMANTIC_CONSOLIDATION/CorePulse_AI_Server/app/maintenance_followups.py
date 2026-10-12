"""V470 — seguimiento educativo acotado al tema vigente.

No consulta YouTube ni el LLM. Solo utiliza nombres de hardware del contexto
REAL_OR_NA ya saneado por el servidor. Nunca confunde el modelo de CPU con el
modelo de portátil, ni permite que el historial afirme sensores.
"""
from __future__ import annotations

import re
import unicodedata
from urllib.parse import quote_plus
from collections.abc import Iterable

_YOUTUBE = 'https://www.youtube.com/results?search_query='


def _norm(value: str) -> str:
    raw = unicodedata.normalize('NFKD', str(value or '').lower())
    return ''.join(ch for ch in raw if unicodedata.category(ch) != 'Mn').strip()


def _target(question: str) -> str | None:
    q = _norm(question)
    if re.search(r'\b(?:cpu|procesador)\b', q):
        return 'cpu'
    if re.search(r'\b(?:notebook|portatil|laptop)\b', q):
        return 'notebook'
    return None


def _is_elliptical(question: str) -> bool:
    q = _norm(question).lstrip('¿¡ ').strip()
    return bool(re.match(r'^(?:y\b|pero\b|para\s+mi\b|en\s+mi\b|mi\s+(?:cpu|notebook|portatil|laptop)\b)', q))


def _explicit_education(question: str) -> bool:
    q = _norm(question)
    return bool(re.search(r'\b(?:mantenimiento|mantencion|limpieza|limpiar)\b', q))


def _continuing_topic(history: Iterable[dict] | None) -> bool:
    """Busca una intención educativa reciente sin atravesar cambios de asunto.

    Las respuestas del asistente no pueden autorizar por sí solas la intención.
    Solo se admiten a lo sumo cuatro mensajes del usuario.
    """
    users = [str(item.get('content') or '')[:1200] for item in list(history or [])[-10:]
             if isinstance(item, dict) and str(item.get('role') or '').lower() == 'user']
    for message in reversed(users[-4:]):
        q = _norm(message).lstrip('¿¡ ').strip()
        if re.search(r'\b(?:mantenimiento|mantencion|limpieza|limpiar)\b', q):
            return True
        # 'enlace de YouTube' solo mantiene vivo el tema, no lo define.
        if re.search(r'\b(?:youtube|video|videos|enlace|link)\b', q) and not re.search(r'\b(?:ram|ssd|drivers|controladores|instalar|reemplazar)\b', q):
            continue
        # Una pregunta de seguimiento puede estar entre la solicitud inicial y la actual.
        if _target(q) and _is_elliptical(q) and not re.search(
            r'\b(?:temperatura|consumo|uso\s+de|frecuencia|rendimiento|fps|salud|driver|error)\b', q
        ):
            continue
        return False
    return False


def _public_name(value: object, max_length: int = 70) -> str:
    value = str(value or '').strip()
    if not value or _norm(value) in ('n/a', 'unknown', 'none', 'no disponible', 'to be filled by o.e.m.', 'system product name'):
        return ''
    # No introducir URLs, parámetros, seriales ni texto arbitrario en búsquedas.
    if re.search(r'(?i)(?:https?://|\bserial\b|\bs/?n\b|\buuid\b)', value):
        return ''
    return re.sub(r'\s+', ' ', re.sub(r'[^\w\s.\-+]', ' ', value, flags=re.UNICODE)).strip()[:max_length]


def maintenance_followup_reply(question: str, history: Iterable[dict] | None, context: dict) -> str | None:
    """Gestiona '¿y para mi notebook?' sin reinterpretarlo como diagnóstico."""
    target = _target(question)
    if not target:
        return None
    q = _norm(question)
    # Una solicitud explícita de diagnóstico no es un seguimiento de mantenimiento.
    if re.search(r'\b(?:temperatura|cuanto|cuanta|consumo|uso\s+de|frecuencia|rendimiento|fps|salud|problema|falla|averia|diagnostico)\b', q) and not _explicit_education(question):
        return None
    if not _explicit_education(question) and not (_is_elliptical(question) and _continuing_topic(history)):
        return None

    cpu = context.get('cpu') if isinstance(context.get('cpu'), dict) else {}
    device = context.get('device') if isinstance(context.get('device'), dict) else {}
    cpu_name = _public_name(cpu.get('name'))
    brand = _public_name(device.get('manufacturer'), 36)
    model = _public_name(device.get('model'), 56) or _public_name(device.get('display_model'), 56)
    # El fabricante aislado NO equivale al modelo exacto del portátil.
    model_parts = [s for s in (brand, model) if s] if model else []
    if len(model_parts) == 2 and _norm(model_parts[0]) in _norm(model_parts[1]):
        model_parts = [model_parts[1]]
    notebook_name = ' '.join(model_parts)

    if target == 'cpu':
        intro = (f'El modelo de CPU que CorePulse registra es {cpu_name}.' if cpu_name else
                 'El modelo exacto de CPU es N/A en la evidencia disponible.')
        advice = ('Para su mantenimiento preventivo, empieza por vigilar las lecturas térmicas con CorePulse, '
                  'revisar la ventilación exterior y mantener despejadas las rejillas. '
                  'El procesador por sí solo no determina cómo desmontar el notebook: para abrirlo o cambiar pasta térmica '
                  'necesitas el manual del modelo de equipo y un procedimiento compatible.')
        if notebook_name:
            intro += f' El equipo registrado es {notebook_name}.'
            query = f'{notebook_name} {cpu_name} limpieza ventiladores mantenimiento tutorial' if cpu_name else f'{notebook_name} limpieza ventiladores mantenimiento tutorial'
        else:
            query = (f'{cpu_name} temperatura mantenimiento ventilacion portatil sin desmontar' if cpu_name else
                     'procesador portatil mantenimiento ventilacion segura sin desmontar')
            if re.search(r'\b(?:exacto|desmontar|desarmar|pasta termica)\b', q):
                advice += ' No consta el modelo exacto del notebook en la evidencia; indícalo antes de buscar un desmontaje específico.'
    else:
        intro = (f'Para tu notebook {notebook_name}, según el modelo registrado por CorePulse:' if notebook_name else
                 'Para tu notebook, el modelo exacto es N/A en la evidencia actual:')
        advice = ('guarda tus archivos, apaga y desconecta el cargador antes de limpiar la parte exterior; '
                  'retira polvo superficial de las rejillas sin abrir la carcasa ni bloquear los ventiladores. '
                  'Para desmontar o intervenir el sistema de refrigeración, verifica antes el manual oficial del modelo; '
                  'el resultado de una búsqueda no demuestra compatibilidad.')
        query = (f'{notebook_name} mantenimiento limpieza ventilacion tutorial' if notebook_name else
                 'notebook limpieza ventilacion mantenimiento preventivo sin desmontar')

    # El enlace se construye, pero jamás se visita desde CorePulse. Se abre solo al pulsar el botón.
    search = _YOUTUBE + quote_plus(query[:125])
    privacy = ('Esta búsqueda incluye el modelo indicado y YouTube solo recibirá esos términos si pulsas abrir la búsqueda.'
               if (cpu_name if target == 'cpu' else notebook_name) else
               'YouTube solo recibirá los términos públicos de búsqueda cuando pulses abrirla.')
    return (f'{intro}\n\n{advice}\n\nBúsqueda de tutoriales de YouTube (no es un video verificado):\n'
            f'{search}\n\n{privacy} Revisa autor, fecha y compatibilidad antes de seguir instrucciones físicas.')


__all__ = ['maintenance_followup_reply']
