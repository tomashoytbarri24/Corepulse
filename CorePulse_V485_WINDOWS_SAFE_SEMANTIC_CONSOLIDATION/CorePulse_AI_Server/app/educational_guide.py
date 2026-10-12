"""V468: orientación preventiva verificable sin invención de diagnósticos.

No consulta Internet, no acciona Windows y no produce enlaces ni especificaciones
particulares que exijan manual del fabricante. Las respuestas complejas quedan
en el LLM, pero esta guía es un fallback seguro ante errores o alucinaciones.
"""
from __future__ import annotations
import re
import unicodedata


def _norm(s: str) -> str:
    s = unicodedata.normalize('NFKD', str(s or '').lower())
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn')


def educational_intent(question: str) -> str:
    """Diferencia una instrucción educativa de una evaluación de sensores."""
    q = _norm(question)
    if not q.strip():
        return ''
    if re.search(r'\b(?:mantenimiento|mantencion|mantener|limpieza|limpiar|cuidar|cuidado)\b', q) and (
        re.search(r'\b(?:tutorial|pasos?|guia|como|hacer|ensen|explic|preventiv|recomend|consejos?)\b', q)
        or re.search(r'\b(?:mantenimiento|mantencion)\b', q)
    ):
        return 'preventive_maintenance'
    if re.search(r'\b(?:tutorial|paso a paso)\b', q):
        return 'general_tutorial'
    return ''


def safe_educational_fallback(question: str, ctx: dict | None = None) -> str | None:
    kind = educational_intent(question)
    if not kind:
        return None
    if kind == 'general_tutorial':
        return ('Claro. ¿Sobre qué tarea quieres el tutorial: limpieza preventiva, '
                'revisión de software, almacenamiento o ampliación de hardware? '
                'Puedo explicarte pasos generales, pero para desmontar piezas necesito '
                'el modelo exacto y un manual compatible.')
    q = _norm(question)
    wants_hardware = bool(re.search(r'\b(?:desmont|abrir|desarm|disipador|pasta termica|ventiladores?|gpu|cpu|ram|ssd|pieza)\b', q))
    intro = 'Aquí tienes una guía general de mantenimiento preventivo; no es un diagnóstico de una avería.'
    if wants_hardware:
        return (intro + '\n\n1. Guarda tu trabajo, apaga Windows y desconecta el cargador o alimentación.\n'
                '2. Consulta el manual oficial de tu modelo y revisa las precauciones del fabricante antes de abrirlo.\n'
                '3. Limpia sólo rejillas accesibles con útiles apropiados; evita líquidos dentro del equipo '
                'y no fuerces ventiladores ni conectores.\n'
                '4. Si necesitas desmontar refrigeración, cambiar pasta térmica o retirar componentes, '
                'confirma modelo y procedimiento oficial o acude a un técnico.'
                '\nNo tengo un tutorial de video específico verificado para este equipo. '
                'Dime fabricante y modelo si deseas instrucciones físicas más precisas.')
    return (intro + '\n\n1. Guarda tu trabajo y comprueba que tus archivos importantes tengan copia de seguridad.\n'
            '2. Instala actualizaciones de Windows desde Configuración, revisándolas antes de aplicarlas.\n'
            '3. Usa las opciones de almacenamiento de Windows para revisar archivos temporales antes de eliminarlos.\n'
            '4. Comprueba el espacio libre del disco sin confundir ocupación con salud SMART.\n'
            '5. Con el PC apagado y desconectado, revisa que las rejillas accesibles no estén obstruidas; '
            'no abras el equipo sin consultar el manual del fabricante.'
            '\nSi quieres un tutorial específico de desmontaje o limpieza interna, '
            'dime el modelo exacto para buscar un procedimiento compatible. '
            'No he verificado ningún video concreto.')
