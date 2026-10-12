"""V469: continuidad educativa con búsqueda de tutoriales sin inventar vídeos.

Las búsquedas se construyen con temas públicos genéricos: jamás contienen
telemetría, identificadores, nombre del equipo ni texto libre del usuario.
No realiza consultas de red ni selecciona un vídeo como verificado.
"""
from __future__ import annotations
import re
import unicodedata
from urllib.parse import quote_plus
from collections.abc import Iterable

_YOUTUBE = 'https://www.youtube.com/results?search_query='
_TOPICS = (
    ('ventilacion', ('ventilador', 'ventiladores', 'rejillas', 'polvo', 'limpiar por dentro', 'limpieza interna'),
     'limpieza de rejillas de ventilacion portatil sin desmontar mantenimiento seguro'),
    ('almacenamiento', ('ssd', 'disco', 'almacenamiento', 'espacio libre'),
     'Windows 11 limpieza de archivos temporales almacenamiento configuracion paso a paso'),
    ('ram', ('memoria ram', 'ampliar ram', 'instalar ram'),
     'Windows 11 revisar uso de memoria ram administrador de tareas'),
    ('gpu', ('gpu', 'tarjeta grafica'),
     'Windows 11 comprobar temperatura gpu diagnostico sin desmontar'),
    ('cpu', ('cpu', 'procesador', 'temperatura del procesador'),
     'Windows 11 comprobar temperatura procesador diagnostico sin desmontar'),
    ('drivers', ('drivers', 'controladores', 'actualizar controlador'),
     'Windows 11 actualizar controladores desde fabricante y windows update'),
    ('mantenimiento preventivo', ('mantencion', 'mantenimiento', 'preventivo', 'limpieza', 'limpiar', 'cuidar equipo'),
     'mantenimiento preventivo computador Windows 11 limpieza exterior sin desmontar'),
)

def _norm(value: str) -> str:
    value = unicodedata.normalize('NFKD', str(value or '').lower())
    return ''.join(ch for ch in value if unicodedata.category(ch) != 'Mn')

def _topic(text: str):
    norm = _norm(text)
    for topic, words, query in _TOPICS:
        if any(word in norm for word in words):
            return topic, query
    return None

def _video_intent(question: str) -> bool:
    q = _norm(question)
    # No secuestrar consultas de métricas o diagnóstico que no pidan vídeos.
    video = re.search(r'\b(?:youtube|video|videos)\b', q)
    link = re.search(r'\b(?:link|enlace|url)\b', q)
    return bool(video or (link and re.search(r'\b(?:tutorial|mantencion|mantenimiento|busqueda|dame|pasame|un|algun)\b', q)))

def video_followup_reply(question: str, history: Iterable[dict] | None = None) -> str | None:
    """None si no corresponde a vídeos; aclaración si no hay tema conocido."""
    if not _video_intent(question):
        return None
    found = _topic(question)
    direct_topic = found is not None
    # Continuidad limitada al historial proporcionado por la interfaz, solo usuario.
    # No inferir temas de las respuestas del LLM, que pueden estar equivocadas.
    if found is None:
        # Sólo el turno anterior del usuario; no rescatar temas antiguos si cambió de asunto.
        for item in reversed(list(history or [])[-8:]):
            if not isinstance(item, dict) or str(item.get('role')).lower() != 'user':
                continue
            found = _topic(str(item.get('content') or '')[:1200])
            break
    if found is None:
        return '¿Sobre qué mantenimiento o componente necesitas el tutorial de YouTube? Por ejemplo, limpieza preventiva, RAM o almacenamiento. Así preparo una búsqueda pertinente sin inventar un video.'
    topic, query = found
    link = _YOUTUBE + quote_plus(query)
    introduction = (f'Claro. Aquí tienes una búsqueda de tutoriales sobre {topic} en YouTube' if direct_topic
                    else f'Claro. Como hablábamos de {topic}, aquí tienes una búsqueda de tutoriales en YouTube')
    return (introduction + f' (no es un video exacto verificado):\n{link}\n\n'
            'CorePulse no ha comprobado los videos que aparecerán. Revisa su fecha, autor y compatibilidad con tu equipo antes de seguir pasos de desmontaje o reparación. La búsqueda solo se abrirá cuando tú lo decidas.')
