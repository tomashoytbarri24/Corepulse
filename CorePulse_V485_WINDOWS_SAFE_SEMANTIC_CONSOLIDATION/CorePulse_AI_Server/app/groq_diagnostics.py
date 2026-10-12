"""Diagnóstico seguro de conexión Groq; una verificación GET sin datos del equipo.

No se imprimen credenciales, URLs de red, cabeceras, cuerpos HTTP ni excepciones.
"""
from __future__ import annotations
import json
import socket
import ssl
import urllib.error
import urllib.request
from . import model_gateway


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Impide redirigir credenciales del proveedor a otro host.
        return None


def _exception_chain(exc: BaseException):
    queue = [exc]
    seen = set()
    while queue and len(seen) < 12:
        current = queue.pop(0)
        if id(current) in seen:
            continue
        seen.add(id(current))
        yield current
        for candidate in (getattr(current, '__cause__', None),
                          getattr(current, '__context__', None),
                          getattr(current, 'reason', None)):
            if isinstance(candidate, BaseException):
                queue.append(candidate)


def _groq_permission_detail(error: urllib.error.HTTPError) -> tuple[str, str] | None:
    """Analiza sólo códigos permitidos; no muestra cuerpos ni mensajes remotos.

    Groq documenta claves `error.code` para bloqueos por organización/proyecto.
    Se limita a 8 KiB y únicamente se parsea JSON; no se guardan respuestas.
    """
    if int(error.code) != 403:
        return None
    try:
        raw = error.read(8193)
        if len(raw) > 8192:
            return ('GROQ_HTTP_403_UNKNOWN', 'Acceso rechazado (detalle del proveedor no interpretable).')
        # Cloudflare suele devolver un cuerpo corto en texto plano al bloquear
        # la firma del cliente; nunca imprimir texto arbitrario del proveedor.
        if b'error code: 1010' in raw.lower() or b'error code 1010' in raw.lower():
            return ('GROQ_EDGE_BLOCKED_1010',
                    'El perímetro de red rechazó la firma del cliente HTTP. Comprueba que usas V466 y prueba otra red si continúa.')
        payload = json.loads(raw.decode('utf-8'))
        obj = payload.get('error') if isinstance(payload, dict) else None
        code = obj.get('code') if isinstance(obj, dict) else None
    except (ValueError, UnicodeError, OSError, AttributeError, TypeError):
        return None
    known = {
        'model_permission_blocked_org': (
            'GROQ_BLOCKED_ORGANIZATION',
            'El proveedor indica que este modelo está bloqueado en la organización de la clave utilizada.'),
        'model_permission_blocked_project': (
            'GROQ_BLOCKED_PROJECT',
            'El proveedor indica que este modelo está bloqueado en el proyecto de la clave utilizada.'),
    }
    return known.get(code)


def credential_source_info() -> tuple[str, bool]:
    """Datos no sensibles para diagnosticar selección de clave, sin red."""
    from . import config
    return str(config.GROQ_KEY_SOURCE), bool(config.GROQ_KEY_CONFLICT)


def print_credential_source() -> None:
    origin, conflict = credential_source_info()
    print('Origen de credencial (sin mostrarla):', origin)
    if conflict:
        print('AVISO: Hay una clave distinta en GROQ_API_KEY; se prioriza Windows Credential Manager.')


def classify_error(exc: BaseException) -> tuple[str, str]:
    """Traduce un error de red a código no sensible y siguiente paso."""
    chain = list(_exception_chain(exc))
    for item in chain:
        if isinstance(item, urllib.error.HTTPError):
            code = int(item.code)
            detail = _groq_permission_detail(item)
            if detail is not None:
                return detail
            by_http = {
                400: ('GROQ_HTTP_400', 'Solicitud inválida. Revisa compatibilidad de los parámetros del modelo.'),
                401: ('GROQ_HTTP_401', 'Clave API inválida o revocada. Ejecuta 10_CONFIGURAR_GROQ_V463.bat y vuelve a probar.'),
                403: ('GROQ_HTTP_403', 'Groq o un intermediario rechaza la operación; todavía no conocemos la causa exacta.'),
                404: ('GROQ_HTTP_404', 'No se encontró el modelo o endpoint solicitado.'),
                408: ('GROQ_HTTP_408', 'La solicitud expiró. Reintenta más tarde.'),
                413: ('GROQ_HTTP_413', 'Solicitud demasiado grande. Reduce contexto o historial.'),
                422: ('GROQ_HTTP_422', 'El proveedor rechazó el formato de la solicitud.'),
                429: ('GROQ_HTTP_429', 'Límite de solicitudes o tokens alcanzado. Espera el reinicio de la cuota gratuita.'),
                500: ('GROQ_HTTP_500', 'Fallo temporal del proveedor. Reintenta más tarde.'),
                502: ('GROQ_HTTP_502', 'Fallo temporal del proveedor. Reintenta más tarde.'),
                503: ('GROQ_HTTP_503', 'Servicio temporalmente no disponible. Reintenta más tarde.'),
                504: ('GROQ_HTTP_504', 'Tiempo de espera agotado por el proveedor.'),
            }
            return by_http.get(code, (f'GROQ_HTTP_{code}', 'Groq devolvió un estado HTTP no exitoso; revisa el estado del servicio.'))
    if any(isinstance(item, (ssl.SSLError, ssl.CertificateError)) for item in chain):
        return ('GROQ_TLS_ERROR', 'Error de conexión TLS/certificados. Comprueba fecha de Windows, certificados y antivirus/proxy.')
    if any(isinstance(item, (TimeoutError, socket.timeout)) for item in chain):
        return ('GROQ_TIMEOUT', 'Tiempo de espera agotado. Comprueba Internet o vuelve a probar.')
    if any(isinstance(item, (urllib.error.URLError, ConnectionError, OSError)) for item in chain):
        return ('GROQ_NETWORK_ERROR', 'No se pudo establecer conexión con Groq. Comprueba DNS, Internet, firewall o proxy.')
    if any(isinstance(item, (ValueError, json.JSONDecodeError, KeyError, TypeError)) for item in chain):
        return ('GROQ_RESPONSE_INVALID', 'El proveedor devolvió una respuesta no reconocida. Revisa compatibilidad y actualiza CorePulse.')
    if isinstance(exc, RuntimeError) and 'no devolvió texto visible' in str(exc).lower():
        return ('GROQ_EMPTY_ANSWER', 'El modelo devolvió contenido vacío; revisa límite de tokens y razonamiento.')
    if isinstance(exc, RuntimeError) and 'respuesta vacía' in str(exc).lower():
        return ('GROQ_EMPTY_RESPONSE', 'El proveedor no entregó alternativas de respuesta. Reintenta más tarde.')
    return ('GROQ_UNKNOWN_ERROR', 'Error no clasificado. No compartas la clave API. Ejecuta el diagnóstico de conexión V464.')


def check_connection() -> tuple[bool, str, str]:
    """Valida clave y disponibilidad del modelo mediante GET /models, sin telemetría."""
    if model_gateway.MODEL_PROVIDER != 'groq':
        return False, 'GROQ_MODE_DISABLED', 'Ejecuta el BAT 15: activa el modo groq solo en ese proceso.'
    if not model_gateway.model_ready():
        return False, 'GROQ_KEY_MISSING', 'No se detecta API key. Ejecuta 10_CONFIGURAR_GROQ_V463.bat.'
    req = urllib.request.Request(
        model_gateway.MODEL_BASE_URL + '/models',
        headers=model_gateway._headers(), method='GET')
    opener = urllib.request.build_opener(_NoRedirect())
    try:
        with opener.open(req, timeout=12) as resp:
            content = resp.read(1024*1024)
        data = json.loads(content.decode('utf-8'))
        models = data.get('data') if isinstance(data, dict) else None
        if not isinstance(models, list):
            return False, 'GROQ_RESPONSE_INVALID', 'Groq no devolvió una lista de modelos reconocible.'
        available = {str(entry.get('id')) for entry in models if isinstance(entry, dict)}
        if model_gateway.MODEL_NAME not in available:
            return False, 'GROQ_MODEL_UNAVAILABLE', 'La API responde, pero GPT-OSS 120B no aparece disponible para esta clave/proyecto.'
        return True, 'GROQ_MODEL_AVAILABLE', 'Clave aceptada y GPT-OSS 120B disponible. Puedes ejecutar el BAT 14.'
    except Exception as exc:
        code, message = classify_error(exc)
        return False, code, message


def main() -> int:
    print('[CorePulse V465] Diagnóstico seguro: consulta la lista de modelos de Groq.')
    print('No se transmiten sensores, historial, preguntas ni telemetría de este computador.')
    print_credential_source()
    ok, code, message = check_connection()
    print('Resultado:', code)
    print('Detalle:', message)
    print('No se muestran API keys ni información privada del proveedor.')
    return 0 if ok else 2


if __name__ == '__main__':
    raise SystemExit(main())
