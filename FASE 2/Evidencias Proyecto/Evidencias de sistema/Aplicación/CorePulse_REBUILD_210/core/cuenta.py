"""Cuenta de CorePulse: inicio de sesión a través de la web.

Flujo (como GitHub Desktop o Spotify, RFC 8252):
1. La app genera un verificador secreto y abre en el navegador
   ``/app/conectar`` con solo su huella SHA-256 (reto), un estado aleatorio
   y el puerto de un servidor local que escucha SOLO en 127.0.0.1.
2. El usuario inicia sesión y autoriza el equipo en la web.
3. La web devuelve el navegador a ``http://127.0.0.1:<puerto>/callback``
   con un código de un solo uso (2 min).
4. La app canjea código + verificador por un token de equipo.

La app nunca ve la contraseña. El token se guarda cifrado con DPAPI de
Windows (ligado al usuario de Windows); en otros sistemas solo vive en memoria.
Solo se contacta la web de CorePulse por HTTPS; no se envía telemetría.
"""
from __future__ import annotations

from concurrent.futures.thread import ThreadPoolExecutor
import ctypes
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from PySide6.QtCore import QObject, Property, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

WEB_PREDETERMINADA = "https://corepulse.cl"
ESPERA_NAVEGADOR = 600  # segundos: da tiempo a crear la cuenta y confirmar el email
RUTAS_WEB = {"/registro", "/cuenta", "/precios", "/login"}


def web_base() -> str:
    """HTTPS fijo; COREPULSE_WEB solo admite otra web HTTPS o localhost (pruebas)."""
    valor = (os.environ.get("COREPULSE_WEB") or WEB_PREDETERMINADA).strip().rstrip("/")
    u = urllib.parse.urlparse(valor)
    local = u.scheme == "http" and u.hostname in ("127.0.0.1", "localhost")
    if (u.scheme == "https" or local) and u.hostname and not u.username and not u.path.strip("/"):
        return valor
    return WEB_PREDETERMINADA


def nuevo_par_pkce() -> tuple[str, str]:
    """(verificador, reto): el reto es la huella SHA-256 en hexadecimal."""
    verificador = secrets.token_urlsafe(48)
    return verificador, hashlib.sha256(verificador.encode("ascii")).hexdigest()


def url_conectar(base: str, puerto: int, estado: str, reto: str) -> str:
    q = urllib.parse.urlencode({"puerto": puerto, "estado": estado, "reto": reto})
    return f"{base}/app/conectar?{q}"


# ---- Almacenamiento del token (DPAPI en Windows) -------------------------------------------

def _archivo_sesion() -> Path:
    home = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
    return home / "CorePulse" / "cuenta.dat"


class _Blob(ctypes.Structure):
    _fields_ = [("cbData", ctypes.c_uint32), ("pbData", ctypes.POINTER(ctypes.c_char))]


def _dpapi(datos: bytes, cifrar: bool) -> bytes | None:
    if os.name != "nt":
        return None
    try:
        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32
        buf = ctypes.create_string_buffer(datos, len(datos))
        entrada = _Blob(len(datos), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
        salida = _Blob()
        funcion = crypt32.CryptProtectData if cifrar else crypt32.CryptUnprotectData
        # CRYPTPROTECT_UI_FORBIDDEN = 0x1: nunca mostrar diálogos.
        if not funcion(ctypes.byref(entrada), None, None, None, None, 0x1, ctypes.byref(salida)):
            return None
        try:
            return ctypes.string_at(salida.pbData, salida.cbData)
        finally:
            kernel32.LocalFree(salida.pbData)
    except (OSError, AttributeError, ValueError):
        return None


def guardar_sesion(token: str, perfil: dict) -> bool:
    cifrado = _dpapi(json.dumps({"token": token, "perfil": perfil}).encode("utf-8"), True)
    if cifrado is None:
        return False
    destino = _archivo_sesion()
    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
        temporal = destino.with_suffix(".tmp")
        temporal.write_bytes(cifrado)
        temporal.replace(destino)
        return True
    except OSError:
        return False


def leer_sesion() -> tuple[str, dict] | None:
    try:
        datos = _dpapi(_archivo_sesion().read_bytes(), False)
        contenido = json.loads(datos.decode("utf-8")) if datos else None
    except (OSError, ValueError, UnicodeError):
        return None
    if not isinstance(contenido, dict) or not isinstance(contenido.get("token"), str):
        return None
    perfil = contenido.get("perfil") if isinstance(contenido.get("perfil"), dict) else {}
    return contenido["token"], perfil


def borrar_sesion() -> None:
    try:
        _archivo_sesion().unlink(missing_ok=True)
    except OSError:
        pass


# ---- Red ---------------------------------------------------------------------------------

def _peticion(metodo: str, ruta: str, *, token: str = "", cuerpo: dict | None = None, espera: int = 60):
    """Devuelve (estado HTTP, JSON). Render gratuito puede tardar ~1 min en despertar."""
    datos = json.dumps(cuerpo).encode("utf-8") if cuerpo is not None else None
    cabeceras = {"User-Agent": "CorePulse-App/1.0", "Accept": "application/json"}
    if datos is not None:
        cabeceras["Content-Type"] = "application/json"
    if token:
        cabeceras["Authorization"] = f"Bearer {token}"
    peticion = urllib.request.Request(web_base() + ruta, data=datos, headers=cabeceras, method=metodo)
    try:
        with urllib.request.urlopen(peticion, timeout=espera) as r:
            return r.status, json.loads(r.read(65536) or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read(65536) or b"{}")
        except ValueError:
            return e.code, {}


PAGINA_VUELTA = """<!doctype html><html lang="es"><meta charset="utf-8"><title>CorePulse</title>
<body style="margin:0;display:grid;place-items:center;height:100vh;background:#08090d;color:#f1f4fb;font-family:system-ui,sans-serif">
<div style="text-align:center"><div style="font-size:44px">{icono}</div><h1 style="font-weight:700">{titulo}</h1>
<p style="color:#9aa7ba">{texto}</p></div></body></html>"""


class ServidorVuelta:
    """Servidor de un solo uso en 127.0.0.1 que recibe /callback desde el navegador."""

    def __init__(self, estado: str):
        self.estado = estado
        self.resultado: dict | None = None
        propietario = self

        class Manejador(BaseHTTPRequestHandler):
            def log_message(self, *args):  # sin registros en consola
                pass

            def do_GET(self):
                url = urllib.parse.urlparse(self.path)
                if url.path != "/callback":
                    self.send_error(404)
                    return
                q = urllib.parse.parse_qs(url.query)
                estado = (q.get("estado") or [""])[0]
                ok_estado = hmac.compare_digest(estado.encode(), propietario.estado.encode())
                codigo = (q.get("codigo") or [""])[0]
                error = (q.get("error") or [""])[0]
                if ok_estado and len(codigo) == 64 and all(c in "0123456789abcdef" for c in codigo):
                    propietario.resultado = {"codigo": codigo}
                    pagina = PAGINA_VUELTA.format(icono="✅", titulo="Sesión iniciada", texto="Ya puedes cerrar esta pestaña y volver a CorePulse.")
                elif ok_estado and error:
                    propietario.resultado = {"error": "cancelado" if error == "cancelado" else "servidor"}
                    pagina = PAGINA_VUELTA.format(icono="↩️", titulo="Inicio de sesión cancelado", texto="Puedes volver a CorePulse.")
                else:
                    pagina = PAGINA_VUELTA.format(icono="⚠️", titulo="Enlace no válido", texto="Vuelve a pulsar «Iniciar sesión» en CorePulse.")
                cuerpo = pagina.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(cuerpo)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(cuerpo)

        self.servidor = HTTPServer(("127.0.0.1", 0), Manejador)
        self.servidor.timeout = 0.5
        self.puerto = self.servidor.server_address[1]

    def esperar(self, cancelado: threading.Event, limite: float = ESPERA_NAVEGADOR) -> dict | None:
        fin = time.monotonic() + limite
        try:
            while self.resultado is None and not cancelado.is_set() and time.monotonic() < fin:
                self.servidor.handle_request()
        finally:
            self.servidor.server_close()
        return self.resultado


def _flujo_login(servidor: ServidorVuelta, verificador: str, cancelado: threading.Event):
    vuelta = servidor.esperar(cancelado)
    if cancelado.is_set():
        return {"error": "cancelado"}
    if not vuelta:
        return {"error": "tiempo"}
    if "error" in vuelta:
        return vuelta
    try:
        estado, datos = _peticion("POST", "/api/app/token", cuerpo={"codigo": vuelta["codigo"], "verificador": verificador})
    except (OSError, ValueError):
        return {"error": "red"}
    token = datos.get("token") if isinstance(datos, dict) else None
    if estado != 200 or not isinstance(token, str):
        return {"error": "codigo"}
    perfil = datos.get("perfil") if isinstance(datos.get("perfil"), dict) else {}
    return {"token": token, "perfil": perfil}


def _consultar_perfil(token: str):
    try:
        estado, datos = _peticion("GET", "/api/app/yo", token=token)
    except (OSError, ValueError):
        return {"error": "red"}
    if estado == 401:
        return {"error": "token"}
    perfil = datos.get("perfil") if isinstance(datos, dict) else None
    return {"perfil": perfil} if isinstance(perfil, dict) else {"error": "red"}


def _revocar(token: str):
    try:
        _peticion("POST", "/api/app/salir", token=token, espera=20)
    except (OSError, ValueError):
        pass
    return {}


MENSAJES = {
    "cancelado": "Inicio de sesión cancelado.",
    "tiempo": "Se agotó el tiempo de espera. Vuelve a intentarlo.",
    "red": "No se pudo conectar con la web de CorePulse. Revisa tu conexión.",
    "codigo": "La autorización no es válida o caducó. Vuelve a intentarlo.",
    "servidor": "La web no pudo completar el inicio de sesión. Inténtalo más tarde.",
}


class CuentaManager(QObject):
    changed = Signal()
    sesionIniciada = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="corepulse-cuenta")
        self._token = ""
        self._perfil: dict = {}
        self._mensaje = ""
        self._cerrado = False
        self._cancelar = threading.Event()
        self._login = None   # futuro del inicio de sesión en el navegador
        self._consulta = None  # futuro de la consulta de perfil
        self._token_consulta = ""
        self._sondeo = QTimer(self)
        self._sondeo.setInterval(200)
        self._sondeo.timeout.connect(self._revisar)
        guardada = leer_sesion()
        if guardada:
            self._token, self._perfil = guardada
            self.actualizar()

    # -- Propiedades para QML
    @Property(bool, notify=changed)
    def conectado(self):
        return bool(self._token)

    @Property(bool, notify=changed)
    def ocupado(self):
        return self._login is not None

    @Property(str, notify=changed)
    def mensaje(self):
        return self._mensaje

    def token_para_ai(self):
        """Uso interno Python: la credencial no se publica hacia la interfaz QML."""
        return self._token if not self._cerrado else ""

    @Property(str, notify=changed)
    def nombre(self):
        return str(self._perfil.get("nombre") or "")

    @Property(str, notify=changed)
    def email(self):
        return str(self._perfil.get("email") or "")

    @Property(str, notify=changed)
    def plan(self):
        return "pro" if self._perfil.get("plan") == "pro" else "free"

    @Property(str, constant=True)
    def web(self):
        return web_base()

    # -- Acciones
    @Slot()
    def iniciarSesion(self):
        if self._cerrado or self._login is not None:
            return
        verificador, reto = nuevo_par_pkce()
        estado = secrets.token_urlsafe(24)
        try:
            servidor = ServidorVuelta(estado)
        except OSError:
            self._avisar("No se pudo preparar el inicio de sesión en este equipo.")
            return
        self._cancelar = threading.Event()
        self._login = self._executor.submit(_flujo_login, servidor, verificador, self._cancelar)
        self._sondeo.start()
        self._avisar("Completa el inicio de sesión en tu navegador…")
        QDesktopServices.openUrl(QUrl(url_conectar(web_base(), servidor.puerto, estado, reto)))

    @Slot()
    def cancelar(self):
        self._cancelar.set()

    @Slot()
    def cerrarSesion(self):
        token = self._token
        self._token, self._perfil = "", {}
        borrar_sesion()
        self._avisar("Sesión cerrada en este equipo.")
        if token and not self._cerrado:
            self._executor.submit(_revocar, token)

    @Slot(str)
    def abrirWeb(self, ruta):
        if ruta in RUTAS_WEB:
            QDesktopServices.openUrl(QUrl(web_base() + ruta))

    @Slot()
    def actualizar(self):
        if self._token and self._consulta is None and not self._cerrado:
            self._token_consulta = self._token
            self._consulta = self._executor.submit(_consultar_perfil, self._token)
            self._sondeo.start()

    # -- Internos
    def _avisar(self, mensaje=None):
        if mensaje is not None:
            self._mensaje = mensaje
        self.changed.emit()

    @staticmethod
    def _resultado(futuro):
        try:
            return futuro.result()
        except Exception:
            return {"error": "red"}

    def _revisar(self):
        if self._login is not None and self._login.done():
            r, self._login = self._resultado(self._login), None
            if "token" in r:
                self._token, self._perfil = r["token"], r["perfil"]
                guardar_sesion(self._token, self._perfil)
                nombre = self._perfil.get("nombre") or self._perfil.get("email") or "tu cuenta"
                self._avisar(f"Sesión iniciada como {nombre}.")
                self.sesionIniciada.emit()
            else:
                self._avisar(MENSAJES.get(r.get("error"), MENSAJES["red"]))
        if self._consulta is not None and self._consulta.done():
            # Solo aplica si la sesión no cambió mientras se consultaba.
            vigente = bool(self._token) and self._token == self._token_consulta
            r, self._consulta = self._resultado(self._consulta), None
            if vigente and r.get("error") == "token":
                self._token, self._perfil = "", {}
                borrar_sesion()
                self._avisar("La sesión de este equipo se cerró desde la web.")
            elif vigente and "perfil" in r:
                self._perfil = r["perfil"]
                guardar_sesion(self._token, self._perfil)
                self._avisar()
            # Sin conexión: se conserva el último perfil conocido.
        if self._login is None and self._consulta is None:
            self._sondeo.stop()

    @Slot()
    def close(self):
        self._cerrado = True
        self._cancelar.set()
        self._sondeo.stop()
        self._executor.shutdown(wait=False, cancel_futures=True)
