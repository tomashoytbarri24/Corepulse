"""CorePulse AI para REBUILD: nube opcional, sin LLM residente ni acciones Windows.

El motor no decide sensores. Esta primera integración no realiza RAG ni diagnósticos
confirmados: separa lecturas autorizadas, generación remota y controles verificables.
"""
from __future__ import annotations

import ctypes
import html
from ctypes import wintypes
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import json
import math
import os
import re
import urllib.error
import urllib.parse
import urllib.request

GROQ_TARGET = "CorePulse/AI/BackendGroqKey"  # reutiliza credencial de V463-V479
GROQ_BASE = "https://api.groq.com/openai/v1"
GROQ_MODEL = "openai/gpt-oss-120b"
USER_AGENT = "CorePulse-AI-REBUILD/060"


class FILETIME(ctypes.Structure):
    _fields_ = [("low", wintypes.DWORD), ("high", wintypes.DWORD)]


class CREDENTIALW(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD), ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR), ("Comment", wintypes.LPWSTR),
        ("LastWritten", FILETIME), ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
        ("Persist", wintypes.DWORD), ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p), ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]


PCREDENTIALW = ctypes.POINTER(CREDENTIALW)


def _advapi32():
    return ctypes.WinDLL("Advapi32.dll", use_last_error=True) if os.name == "nt" else None


def read_key() -> str:
    """Nunca leer GROQ_API_KEY del entorno inadvertidamente; solo el almacén de Windows."""
    api = _advapi32()
    if api is None:
        return ""
    api.CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(PCREDENTIALW)]
    api.CredReadW.restype = wintypes.BOOL
    api.CredFree.argtypes = [ctypes.c_void_p]
    api.CredFree.restype = None
    ptr = PCREDENTIALW()
    if not api.CredReadW(GROQ_TARGET, 1, 0, ctypes.byref(ptr)):
        return ""
    try:
        cred = ptr.contents
        if not cred.CredentialBlob or not cred.CredentialBlobSize:
            return ""
        return ctypes.string_at(cred.CredentialBlob, cred.CredentialBlobSize).decode("utf-16-le").strip()
    finally:
        api.CredFree(ptr)


def save_key(value: str) -> bool:
    """Credencial genérica cifrada/protegida por la sesión Windows, nunca en el ZIP."""
    api = _advapi32()
    key = str(value or "").strip()
    if api is None or not key or len(key) > 512 or "\n" in key or "\r" in key:
        return False
    blob = key.encode("utf-16-le")
    buffer = (ctypes.c_ubyte * len(blob)).from_buffer_copy(blob)
    record = CREDENTIALW()
    record.Type = 1
    record.TargetName = GROQ_TARGET
    record.UserName = "CorePulse"
    record.Persist = 2
    record.CredentialBlobSize = len(blob)
    record.CredentialBlob = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte))
    api.CredWriteW.argtypes = [ctypes.POINTER(CREDENTIALW), wintypes.DWORD]
    api.CredWriteW.restype = wintypes.BOOL
    return bool(api.CredWriteW(ctypes.byref(record), 0))


def valid_number(value, lower, upper):
    if isinstance(value, bool):
        return None
    if not isinstance(value, (int, float)) or not math.isfinite(value) or not lower <= value <= upper:
        return None
    return round(float(value), 2)


# Contrato explícito: nunca transmitir hostname, rutas, PID, seriales o inventario íntegro.
MEASURES = {
    "cpuPercent": (0, 100), "cpuTemp": (1, 115),
    "gpuPercent": (0, 100), "gpuTemp": (1, 125),
    "ramPercent": (0, 100), "diskPercent": (0, 100),
}


def authorized_snapshot(metrics: dict, allowed: bool) -> dict:
    if not allowed or not isinstance(metrics, dict):
        return {}
    out = {}
    for name in ("cpuName", "gpuName", "diskName"):
        raw = metrics.get(name)
        if isinstance(raw, str) and raw.strip() and raw.strip().lower() not in ("n/a", "unknown", "none"):
            # No incluir texto libre de longitud arbitraria procedente de un proveedor.
            out[name] = raw.strip()[:100]
    for name, (low, high) in MEASURES.items():
        val = valid_number(metrics.get(name), low, high)
        # Una temperatura sin fuente identificada no se autoriza como medición.
        if name == "cpuTemp" and str(metrics.get("cpuTempSource", "N/A")) == "N/A":
            val = None
        out[name] = val if val is not None else "N/A"
    # Los FPS no forman parte de la telemetría REBUILD 058; no se inventan.
    out["fps"] = "N/A"
    out["diskHealth"] = "N/A"  # nunca confundir ocupación con estado SMART
    return out


SYSTEM_POLICY = (
    "Eres CorePulse AI, asistente técnico especializado en hardware y Windows. "
    "No inventes mediciones de CPU/GPU/RAM/SSD/FPS, modelos, fuentes ni enlaces. "
    "Los datos N/A son desconocidos, no valores cero. "
    "Distingue observación verificada, hipótesis y prueba pendiente. "
    "Un disco lleno no demuestra daño SMART; temperatura elevada aislada no confirma avería. "
    "No afirmes haber ejecutado acciones ni modificado Windows. "
    "Para cambios de Windows pide autorización y no los ejecutes. "
    "Para mantenimiento general responde con pasos educativos seguros aun sin una avería. "
    "Sin un modelo exacto del equipo, evita instrucciones específicas de desmontaje. "
    "Si no hay datos verificados, indica exactamente qué falta. "
    "Habla con el usuario como una persona: español cercano, frases breves, pasos simples y términos técnicos explicados. "
    "Responde primero la pregunta concreta; no vuelques la telemetría ni estructuras internas sin que la soliciten. "
    "No utilices Markdown ni HTML: sin asteriscos, tablas de barras verticales, etiquetas br, "
    "bloques de código ni títulos con almohadillas. Presenta pasos cortos en líneas separadas. "
    "Si te piden código, puedes mostrarlo como texto claro. No afirmes que consultaste fuentes no verificadas."

)


def make_messages(question: str, snapshot: dict, history: list[dict] | None = None) -> list[dict]:
    context = ("Lecturas autorizadas de CorePulse (N/A significa no disponible): " +
               json.dumps(snapshot, ensure_ascii=False, separators=(",", ":"))) if snapshot else (
               "El usuario NO autorizó compartir lecturas del computador. No conoces sus sensores, "
               "modelo, FPS, temperaturas ni estado actual. Puedes responder preguntas educativas generales.")
    messages = [{"role": "system", "content": SYSTEM_POLICY},
                {"role": "system", "content": context}]
    # Solo contexto reciente de ESTA sesión y con permiso vigente.
    for item in (history or [])[-6:]:
        if item.get("role") in ("user", "assistant") and isinstance(item.get("text"), str):
            messages.append({"role": item["role"], "content": item["text"][:1500]})
    messages.append({"role": "user", "content": question[:1800]})
    return messages


# Presentación exclusivamente visual: no extrae ni inventa lecturas del equipo.
# Debe ejecutarse DESPUÉS de la validación de las mediciones del texto original.
def readable_answer(raw: str) -> str:
    """Convierte Markdown/HTML común a texto seguro y legible para QML PlainText."""
    text = str(raw or "")[:12000].replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\\n", "\n") if "\n" not in text and "\\n" in text else text
    # [documentación](https://...) => documentación (https://...), sin perder origen.
    text = re.sub(r"\[([^\]\n]+)\]\((https?://[^)\s]+)\)", r"\1 (\2)", text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"(?m)^\s*```[^\n]*$", "", text)
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s+", "", text)
    text = re.sub(r"(?m)^[ \t]*[-*+][ \t]+", "• ", text)
    # Formato de tablas Markdown. Se convierte cada fila en un bloque de lectura.
    lines = text.split("\n")
    rebuilt = []
    i = 0
    divider = re.compile(r"^:?-{3,}:?$")
    while i < len(lines):
        line = lines[i].strip()
        if "|" in line and i + 1 < len(lines):
            head = [v.strip() for v in line.strip("|").split("|")]
            separator = [v.strip() for v in lines[i + 1].strip().strip("|").split("|")]
            if len(head) >= 2 and len(head) == len(separator) and all(divider.fullmatch(v) for v in separator):
                i += 2
                while i < len(lines) and "|" in lines[i]:
                    vals = [v.strip() for v in lines[i].strip().strip("|").split("|")]
                    if len(vals) != len(head):
                        break
                    if any(vals):
                        rebuilt.append("")
                        if (len(vals) == 2 and vals[0].strip().lower() in
                                {"cpu", "gpu", "ram", "ssd", "disco", "fps"}):
                            rebuilt.append(f"{vals[0]}: {vals[1]}")
                            i += 1
                            continue
                        rebuilt.append(vals[0] or "Información")
                        for col, val in zip(head[1:], vals[1:]):
                            if val:
                                rebuilt.append(f"{col}: {val}" if col else val)
                    i += 1
                continue
        rebuilt.append(lines[i])
        i += 1
    text = "\n".join(rebuilt)
    # Los <br> dentro de celdas se convierten tras interpretar la tabla.
    text = re.sub(r"(?i)<\s*br\s*/?\s*>", "\n", text)
    text = re.sub(r"(?i)<\s*/?\s*(?:p|div|ul|ol|table|thead|tbody|tr)\b[^>]*>", "\n", text)
    text = re.sub(r"(?i)<\s*li\b[^>]*>", "\n• ", text)
    text = re.sub(r"(?i)<\s*/\s*li\s*>", "\n", text)
    text = re.sub(r"<[^>\n]{1,200}>", "", text)
    text = html.unescape(text)
    # Markdown de énfasis, código inline, separadores y backslashes de formato.
    text = re.sub(r"(?m)^\s*[-*_]{3,}\s*$", "", text)
    text = re.sub(r"\*\*([^*\n]+)\*\*|__([^_\n]+)__", lambda m: m.group(1) or m.group(2), text)
    text = re.sub(r"(?<!\w)\*([^*\n]+)\*(?!\w)|(?<!\w)_([^_\n]+)_(?!\w)", lambda m: m.group(1) or m.group(2), text)
    text = re.sub(r"(?<!~)~~([^~\n]+)~~(?!~)", r"\1", text)
    text = re.sub(r"`([^`\n]+)`", r"\1", text)
    text = re.sub(r"\\([*_`#|])", r"\1", text)
    # Líneas de tablas incompletas: nunca mostrar tuberías visuales en el chat.
    text = re.sub(r"(?m)^\s*\|?\s*(?:[:-]+\s*\|)+\s*[:-]*\|?\s*$", "", text)
    text = re.sub(r"\s*\|\s*", " — ", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()[:5500] or "No recibí una respuesta legible. Intenta reformular tu pregunta."


# Un número presentado como medición personal debe coincidir con la evidencia.
PERSONAL_METRIC = re.compile(
    r"(?:\b(?:tu|tus|mi|mis)\s+)?\b(cpu|gpu|ram|ssd|disco|fps)\b"
    r"\s*(?:tiene|está|marca|registra|alcanza|:|=|es|a|en|de|usa|utiliza)?"
    r"\s*(?:a|en)?\s*(?:aproximadamente|unos?|alrededor de)?\s*(\d+(?:[.,]\d+)?)\s*(°\s*c|%|fps)",
    re.IGNORECASE,
)


def reject_unbacked_measures(answer: str, snapshot: dict) -> bool:
    """Bloquea algunas afirmaciones numéricas de lecturas personales; no certifica precisión global."""
    # No hay ningún dato de salud SMART en este flujo. Nunca inferirlo de espacio usado.
    smart_claim = re.compile(
        r"(?:\b(?:ssd|disco|smart)\b.{0,45}\b(?:salud|desgaste|vida útil)\b|"
        r"\b(?:salud|desgaste|vida útil)\b.{0,35}\b(?:ssd|disco)\b)"
        r".{0,20}\b\d+(?:[.,]\d+)?\s*%", re.IGNORECASE)
    if smart_claim.search(answer):
        return True
    for match in PERSONAL_METRIC.finditer(answer):
        subject, raw, unit = match.groups()
        subject = subject.lower()
        metric = {"cpu": "cpuTemp" if "°" in unit else "cpuPercent",
                  "gpu": "gpuTemp" if "°" in unit else "gpuPercent",
                  "ram": "ramPercent", "ssd": "diskPercent", "disco": "diskPercent",
                  "fps": "fps"}[subject]
        observed = snapshot.get(metric)
        if not isinstance(observed, (int, float)) or abs(observed - float(raw.replace(",", "."))) > 0.6:
            return True
    return False


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class ModelGateway:
    """Adaptador compatible OpenAI; el proveedor se configura, no determina diagnóstico."""
    def __init__(self, base_url=GROQ_BASE, model=GROQ_MODEL, opener=None):
        parsed = urllib.parse.urlsplit(base_url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("El motor cloud exige HTTPS sin credenciales en la URL.")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.opener = opener if opener is not None else urllib.request.build_opener(NoRedirect)

    def _request(self, path: str, key: str, data=None):
        headers = {"Authorization": "Bearer " + key, "User-Agent": USER_AGENT, "Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(self.base_url + path, data=data, headers=headers,
                                     method="POST" if data is not None else "GET")
        try:
            with self.opener.open(req, timeout=24) as response:
                if response.status != 200:
                    raise RuntimeError("CLOUD_HTTP_ERROR")
                raw = response.read(128 * 1024 + 1)
                if len(raw) > 128 * 1024:
                    raise RuntimeError("CLOUD_RESPONSE_TOO_LARGE")
                return json.loads(raw)
        except urllib.error.HTTPError as ex:
            if ex.code in (401, 403, 404, 429):
                raise RuntimeError("GROQ_HTTP_" + str(ex.code)) from None
            raise RuntimeError("CLOUD_HTTP_ERROR") from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise RuntimeError("CLOUD_CONNECTION_ERROR") from None
        except (UnicodeError, ValueError, TypeError, json.JSONDecodeError):
            raise RuntimeError("CLOUD_INVALID_RESPONSE") from None

    def probe(self, key: str) -> bool:
        data = self._request("/models", key)
        return self.model in [m.get("id") for m in data.get("data", []) if isinstance(m, dict)]

    def chat(self, key: str, messages: list[dict]) -> str:
        body = json.dumps({"model": self.model, "messages": messages,
                           "max_completion_tokens": 800, "temperature": 0.2}, ensure_ascii=False).encode("utf-8")
        data = self._request("/chat/completions", key, body)
        try:
            content = data["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise ValueError("empty")
            return content.strip()[:5500]
        except (ValueError, TypeError, KeyError, IndexError):
            raise RuntimeError("CLOUD_EMPTY_RESPONSE") from None


def fallback(snapshot: dict) -> str:
    if not snapshot:
        return "No hay respuesta verificada del modelo. No se compartieron lecturas; puedo ayudarte con orientación general cuando el servicio vuelva a estar disponible."
    parts = []
    for key, label, suffix in (("cpuTemp", "CPU", "°C"), ("gpuTemp", "GPU", "°C"),
                               ("ramPercent", "RAM", "%"), ("diskPercent", "Espacio utilizado del disco", "%")):
        value = snapshot.get(key, "N/A")
        parts.append(f"{label}: {value}{suffix if isinstance(value, (int, float)) else ''}")
    return ("La respuesta remota no superó las comprobaciones. Lecturas compartidas: " +
            "; ".join(parts) + ". Esto no confirma una avería; faltan pruebas para diagnosticar.")


def make_ai_controller(telemetry, system_health=None):
    """Puente QObject único: red siempre en trabajador y QML solo recibe estados seguros."""
    from PySide6.QtCore import QObject, Property, Signal, Slot

    class AIController(QObject):
        changed = Signal()
        completed = Signal(int, str, str)

        def __init__(self):
            super().__init__()
            self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="CorePulseAI")
            self._generation = 0
            self._closed = False
            self._enabled = False
            self._consent = False
            self._hardware = False
            self._busy = False
            self._ready = False
            self._system_health = system_health
            self._diagnostic = {'status': 'idle', 'runId': 0, 'text': '',
                                'statusText': 'El diagnóstico con IA aún no se ha solicitado.'}
            self._status = "IA apagada. No se transmiten datos."
            self._messages = []
            self.completed.connect(self._finish)
            self._gateway = ModelGateway()

        @Property("QVariantMap", notify=changed)
        def state(self):
            return {"enabled": self._enabled, "consent": self._consent,
                    "hardware": self._hardware, "busy": self._busy,
                    "ready": self._ready, "hasKey": bool(read_key()),
                    "status": self._status, "messages": list(self._messages),
                    "diagnostic": dict(self._diagnostic)}

        @Slot(bool)
        def enable(self, value):
            self._enabled = bool(value)
            if not self._enabled:
                self._generation += 1
                self._busy = self._ready = self._consent = self._hardware = False
                self._messages.clear()
                self._diagnostic = {'status': 'idle', 'runId': 0, 'text': '',
                                    'statusText': 'La IA está apagada; no se enviaron lecturas.'}
                self._status = "IA apagada. No se transmiten datos."
            else:
                self._status = "Configura tu conexión. No se envía nada automáticamente."
            self.changed.emit()

        @Slot(bool)
        def allowQuestions(self, value):
            self._consent = bool(value) if self._enabled else False
            if not self._consent:
                self._generation += 1
                self._ready = self._busy = self._hardware = False
                self._messages.clear()
                self._diagnostic = {'status': 'idle', 'runId': 0, 'text': '',
                                    'statusText': 'Sin permiso de consulta; no se enviaron lecturas.'}
                self._status = "Permiso retirado. Conversación eliminada de la memoria de CorePulse."
            self.changed.emit()

        @Slot(bool)
        def allowHardware(self, value):
            allowed = bool(value) if self._enabled and self._consent else False
            if allowed != self._hardware:
                # Al cambiar el alcance de datos, descartar todo el contexto anterior.
                self._generation += 1
                self._busy = False
                self._messages.clear()
                self._diagnostic = {'status': 'idle', 'runId': 0, 'text': '',
                                    'statusText': 'El permiso técnico cambió; vuelve a ejecutar el diagnóstico.'}
                self._status = "Permisos técnicos actualizados. Conversación anterior borrada."
            self._hardware = allowed
            self.changed.emit()

        @Slot(str, result=bool)
        def saveApiKey(self, value):
            if not self._enabled or self._busy:
                return False
            ok = save_key(value)
            self._ready = False
            self._generation += 1
            self._messages.clear()  # impedir transferencia de conversación entre cuentas
            self._status = "Clave almacenada en Windows. Conecta para comprobar el modelo." if ok else "No se pudo guardar la clave en Windows."
            self.changed.emit()
            return ok

        def _run(self, kind, work):
            self._busy = True
            self._generation += 1
            seq = self._generation
            self.changed.emit()
            future = self._executor.submit(work)
            def receive(done):
                try:
                    result = done.result()
                    code = "ok"
                except Exception as exc:
                    code, result = "error", str(exc) if str(exc) in (
                        "GROQ_HTTP_401", "GROQ_HTTP_403", "GROQ_HTTP_404", "GROQ_HTTP_429",
                        "CLOUD_HTTP_ERROR", "CLOUD_CONNECTION_ERROR", "CLOUD_INVALID_RESPONSE",
                        "CLOUD_RESPONSE_TOO_LARGE", "CLOUD_EMPTY_RESPONSE") else "CLOUD_CONNECTION_ERROR"
                if not self._closed:
                    self.completed.emit(seq, kind + ":" + code, str(result))
            future.add_done_callback(receive)

        @Slot()
        def connectCloud(self):
            if not self._enabled or not self._consent or self._busy:
                self._status = "Activa la IA y autoriza primero las consultas."
                self.changed.emit()
                return
            key = read_key()
            if not key:
                self._status = "Falta la clave Groq. Guárdala una sola vez."
                self.changed.emit()
                return
            self._status = "Comprobando disponibilidad de GPT-OSS 120B…"
            self._run("connect", lambda: "available" if self._gateway.probe(key) else "missing")

        @Slot(str)
        def send(self, question):
            question = str(question or "").strip()
            if not (self._enabled and self._consent and self._ready) or self._busy or not question or len(question) > 1800:
                return
            key = read_key()
            if not key:
                self._ready = False
                self._status = "Clave no disponible. Vuelve a conectarte."
                self.changed.emit()
                return
            evidence = authorized_snapshot(dict(telemetry.metrics), self._hardware)
            messages = make_messages(question, evidence, self._messages)
            self._messages.append({"role": "user", "text": question})
            self._status = "Consultando GPT-OSS 120B…"
            def work():
                text = self._gateway.chat(key, messages)
                return json.dumps({"answer": text, "evidence": evidence}, ensure_ascii=False)
            self._run("chat", work)

        @Slot()
        def diagnose(self):
            report = getattr(self._system_health, 'diagnostic', {}) or {}
            run_id = int(report.get('runId', 0)) if isinstance(report, dict) else 0
            if not (self._enabled and self._consent and self._hardware and self._ready):
                self._diagnostic = {'status': 'unavailable', 'runId': run_id, 'text': '',
                                    'statusText': 'El resultado local está listo. Para pedir análisis de IA, activa la IA, conecta tu cuenta y autoriza compartir lecturas técnicas.'}
                self.changed.emit()
                return
            if self._busy:
                return
            if self._system_health is None:
                self._diagnostic = {'status': 'unavailable', 'runId': run_id, 'text': '',
                                    'statusText': 'No se pudo leer el resumen local de salud.'}
                self.changed.emit()
                return
            key = read_key()
            if not key:
                self._ready = False
                self._diagnostic = {'status': 'unavailable', 'runId': run_id, 'text': '',
                                    'statusText': 'La clave de IA no está disponible; el resultado local sigue listo.'}
                self.changed.emit()
                return
            summary = report.get('summary') if isinstance(report, dict) else None
            if not isinstance(summary, dict) or not summary:
                summary = dict(getattr(self._system_health, 'data', {}) or {})
            checks = []
            for check in summary.get('checks') or []:
                if not isinstance(check, dict):
                    continue
                checks.append({name: str(check.get(name) or 'N/A')[:220]
                               for name in ('key', 'title', 'value', 'state', 'detail', 'source')})
            snapshot = authorized_snapshot(dict(self._system_health.telemetry.metrics), True)
            evidence = {'lecturas': snapshot,
                        'resumen': {'estado': str(summary.get('headline') or 'N/A')[:120],
                                    'cobertura': str(summary.get('coverage') or 'N/A')[:20],
                                    'indicadores': checks},
                        'año_actual': datetime.now().year}
            prompt = (
                'Analiza este diagnóstico local de CorePulse para el año ' + str(evidence['año_actual']) +
                '. Usa únicamente la evidencia JSON adjunta. Separa lo correcto, la atención preventiva y los datos sin confirmar. ' 
                'No presentes una lectura preventiva como avería. Explica qué problema concreto requiere atención y pasos seguros para revisarlo. ' 
                'Si CPU o GPU tienen modelo exacto, estima su generación y vigencia para el año indicado solo si lo conoces con confianza; ' 
                'si no, dilo claramente. No inventes antigüedad, salud SMART ni enlaces. Para cada problema menciona insumos solo si hacen falta ' 
                'y añade consejos concretos. Si faltan mediciones, no declares que todo está en orden. No uses Markdown ni HTML; responde en español, ' 
                'con párrafos breves y etiquetas simples. Mantén el informe bajo 2200 caracteres. Evidencia: ' +
                json.dumps(evidence, ensure_ascii=False, separators=(',', ':'))
            )
            messages = [{'role': 'system', 'content': SYSTEM_POLICY +
                         ' En diagnósticos, no sustituyas la observación por una causa hipotética y conserva los valores N/A como desconocidos.'},
                        {'role': 'user', 'content': prompt}]
            self._diagnostic = {'status': 'running', 'runId': run_id, 'text': '',
                                'statusText': 'Consultando IA con las lecturas autorizadas…'}
            self._status = 'Preparando análisis del diagnóstico…'
            def work():
                answer = self._gateway.chat(key, messages)
                return json.dumps({'answer': answer, 'evidence': snapshot, 'runId': run_id}, ensure_ascii=False)
            self._run('diagnostic', work)

        @Slot(int, str, str)
        def _finish(self, seq, event, result):
            if seq != self._generation or self._closed or not self._enabled or not self._consent:
                return
            self._busy = False
            if event == "connect:ok":
                self._ready = result == "available"
                self._status = "Conectada · GPT-OSS 120B en Groq" if self._ready else "La cuenta no ofrece el modelo solicitado."
            elif event == "chat:ok":
                try:
                    payload = json.loads(result)
                    text = payload["answer"]
                    evidence = payload["evidence"]
                    normalized = readable_answer(text)
                    # Dos barreras: la salida original y la misma salida sin marcado.
                    # Markdown / HTML no deben permitir eludir REAL_OR_NA.
                    if reject_unbacked_measures(text, evidence) or reject_unbacked_measures(normalized, evidence):
                        self._messages.append({"role": "assistant", "text": fallback(evidence)})
                        self._status = "Se descartaron afirmaciones numéricas sin respaldo."
                    else:
                        self._messages.append({"role": "assistant", "text": normalized})
                        self._status = "Respuesta generada; no equivale a diagnóstico confirmado."
                except (ValueError, KeyError, TypeError):
                    self._status = "No se pudo interpretar la respuesta."
            elif event == "diagnostic:ok":
                try:
                    payload = json.loads(result)
                    text = payload['answer']
                    evidence = payload['evidence']
                    normalized = readable_answer(text)
                    if reject_unbacked_measures(text, evidence) or reject_unbacked_measures(normalized, evidence):
                        self._diagnostic = {'status': 'rejected', 'runId': payload.get('runId', 0), 'text': '',
                                            'statusText': 'La IA generó afirmaciones que no coinciden con las lecturas; se descartaron.'}
                    else:
                        self._diagnostic = {'status': 'ready', 'runId': payload.get('runId', 0), 'text': normalized,
                                            'statusText': 'Análisis de IA basado en lecturas autorizadas.'}
                    self._status = 'Análisis del diagnóstico terminado.'
                except (ValueError, KeyError, TypeError):
                    self._diagnostic = {'status': 'error', 'runId': int(self._diagnostic.get('runId', 0)), 'text': '',
                                        'statusText': 'No se pudo interpretar el análisis de IA.'}
                    self._status = 'No se pudo interpretar la respuesta.'
            else:
                self._ready = False if event.startswith("connect:") else self._ready
                labels = {"GROQ_HTTP_401": "Clave Groq rechazada (401).", "GROQ_HTTP_403": "Acceso denegado (403).",
                          "GROQ_HTTP_429": "Límite gratuito alcanzado (429).", "GROQ_HTTP_404": "Modelo no encontrado (404)."}
                self._status = labels.get(result, "El servicio cloud no está disponible. Reintenta más tarde.")
                if event.startswith("chat:"):
                    self._messages.append({"role": "assistant", "text": "No fue posible obtener respuesta de la nube; no se realizó diagnóstico."})
                if event.startswith('diagnostic:'):
                    self._diagnostic = {'status': 'error', 'runId': int(self._diagnostic.get('runId', 0)), 'text': '',
                                        'statusText': 'La IA no respondió. El diagnóstico local sigue disponible; intenta de nuevo más tarde.'}
            self._messages = self._messages[-20:]
            self.changed.emit()

        @Slot()
        def clearChat(self):
            self._generation += 1
            self._busy = False
            self._messages.clear()
            self._status = "Conversación borrada en CorePulse."
            self.changed.emit()

        def close(self):
            self._closed = True
            self._generation += 1
            self._executor.shutdown(wait=False, cancel_futures=True)

    return AIController()
