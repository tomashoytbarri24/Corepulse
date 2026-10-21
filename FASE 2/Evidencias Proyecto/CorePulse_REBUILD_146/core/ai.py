"""CorePulse AI para REBUILD: nube opcional, sin LLM residente ni acciones Windows.

El motor no decide sensores. CorePulse AI Cloud incorpora desde V118 recuperación
limitada de referencias técnicas curadas; esto no confirma diagnósticos ni implica
búsquedas de Internet en directo.
"""
from __future__ import annotations

import ctypes
import hashlib
import html
from ctypes import wintypes
from concurrent.futures.thread import ThreadPoolExecutor
from datetime import datetime
import json
import math
import os
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request

GROQ_TARGET = "CorePulse/AI/BackendGroqKey"  # reutiliza credencial de V463-V479
GROQ_BASE = "https://api.groq.com/openai/v1"
GROQ_MODEL = "openai/gpt-oss-120b"
USER_AGENT = "CorePulse-AI-REBUILD/128"
CLOUD_ORIGIN = "https://ai.corepulse.cl"


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
    "Una lectura es instantánea y no revela por sí sola que el PC esté en reposo ni cuánto duró una condición. "
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


def reject_unbacked_measures(answer: str, snapshot: dict, session_summary=None) -> bool:
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
        measured = float(raw.replace(",", "."))
        if isinstance(observed, (int, float)) and abs(observed - measured) <= 0.6:
            continue
        # Permit historical peaks ONLY when a separate consented summary exists
        # and the generated sentence explicitly describes session history.
        peak_name = {'cpuTemp': 'cpuTempPeak', 'gpuTemp': 'gpuTempPeak',
                     'ramPercent': 'ramPercentPeak'}.get(metric)
        prior = (session_summary or {}).get(peak_name) if peak_name else None
        preceding = answer[max(0,match.start()-90):match.start()].lower()
        historical = bool(re.search(r'pico|máxim[oa]|historial|sesión|durante|registrad', preceding))
        if historical and isinstance(prior, (float,int)) and abs(prior - measured) <= 0.6:
            continue
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


def cloud_url():
    """Cloud never receives login tokens at arbitrary origins."""
    raw = os.environ.get("COREPULSE_AI_CLOUD_URL", "").strip().rstrip("/")
    if not raw:
        return CLOUD_ORIGIN
    try:
        parsed = urllib.parse.urlsplit(raw)
        port = parsed.port  # malformed ports must degrade safely, not crash CorePulse
    except ValueError:
        return ""
    if parsed.scheme == "https" and parsed.hostname == "ai.corepulse.cl" and not any(
        (parsed.username, parsed.password, parsed.path, parsed.query, parsed.fragment, port)):
        return raw
    # Explicitly opt in to loopback-only testing (never ship with this enabled).
    if os.environ.get("COREPULSE_AI_DEV") == "1" and parsed.scheme == "http" and parsed.hostname in ("localhost", "127.0.0.1") and not any((parsed.username, parsed.password, parsed.query, parsed.fragment, parsed.path)):
        return raw
    return ""




def ai_preferences_path() -> Path:
    """Preferencias no sensibles. El token sigue únicamente en DPAPI de CuentaManager."""
    home = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
    return home / "CorePulse" / "ai-preferences.json"


def read_ai_preferences() -> dict:
    """Cloud disponible por defecto; una negativa explícita se respeta al reiniciar."""
    try:
        payload = json.loads(ai_preferences_path().read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return {}
        return {key: payload[key] for key in ("enabled", "questions")
                if key in payload and type(payload[key]) is bool}
    except (OSError, ValueError, UnicodeError):
        return {}


def save_ai_preferences(*, enabled: bool, questions: bool) -> bool:
    """Solo guarda interruptores locales; nunca registra preguntas ni datos de hardware."""
    try:
        target = ai_preferences_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(".tmp")
        temporary.write_text(json.dumps({"enabled": bool(enabled), "questions": bool(questions)}),
                             encoding="utf-8")
        temporary.replace(target)
        return True
    except OSError:
        return False


class CorePulseCloudGateway:
    """Independent API transport. Groq's key must NEVER enter this client."""
    def __init__(self, base_url, opener=None):
        self.base_url = base_url
        self.opener = opener if opener is not None else urllib.request.build_opener(NoRedirect)

    def _request(self, path, token, payload=None):
        if not isinstance(token, str) or not token.strip():
            raise RuntimeError("CLOUD_ACCOUNT_REQUIRED")
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8") if payload is not None else None
        if body is not None and len(body) > 24 * 1024:
            raise RuntimeError("CLOUD_INVALID_REQUEST")
        headers = {"Authorization": "Bearer " + token, "Accept": "application/json", "User-Agent": USER_AGENT}
        if body is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(self.base_url + path, data=body, headers=headers,
                                     method="POST" if body is not None else "GET")
        try:
            with self.opener.open(req, timeout=28) as resp:
                if resp.status != 200:
                    raise RuntimeError("CLOUD_HTTP_ERROR")
                data = resp.read(64 * 1024 + 1)
                if len(data) > 64 * 1024:
                    raise RuntimeError("CLOUD_RESPONSE_TOO_LARGE")
                result = json.loads(data)
                if not isinstance(result, dict):
                    raise ValueError("not object")
                return result
        except urllib.error.HTTPError as exc:
            # El Worker responde errores públicos tipados. Mostrar solo claves
            # conocidas, NUNCA el cuerpo completo ni los tokens de la solicitud.
            public_errors = {
                (503, "service_not_configured"): "CLOUD_SERVICE_NOT_CONFIGURED",
                (503, "identity_unavailable"): "CLOUD_IDENTITY_UNAVAILABLE",
                (503, "provider_unavailable"): "CLOUD_PROVIDER_UNAVAILABLE",
                (503, "model_budget_unavailable"): "CLOUD_MODEL_BUDGET_UNAVAILABLE",
                (503, "rate_limit_unavailable"): "CLOUD_RATE_LIMIT_UNAVAILABLE",
                (429, "model_budget_reached"): "CLOUD_MODEL_BUDGET_REACHED",
                (429, "provider_rate_limited"): "CLOUD_PROVIDER_RATE_LIMITED",
                (429, "rate_limited"): "CLOUD_HTTP_429",
            }
            code = None
            if exc.code in (429, 503):
                try:
                    # Error JSON mínimo; límite estricto para no procesar HTML
                    # de intermediarios o texto no controlado por CorePulse.
                    payload = exc.read(1025)
                    if len(payload) <= 1024:
                        value = json.loads(payload)
                        if isinstance(value, dict):
                            code = public_errors.get((exc.code, value.get("error")))
                except (OSError, ValueError, TypeError, UnicodeError):
                    pass
            if code:
                raise RuntimeError(code) from None
            if exc.code in (401, 403, 429, 503):
                raise RuntimeError("CLOUD_HTTP_" + str(exc.code)) from None
            raise RuntimeError("CLOUD_HTTP_ERROR") from None
        except (TimeoutError, urllib.error.URLError, OSError):
            raise RuntimeError("CLOUD_CONNECTION_ERROR") from None
        except (ValueError, TypeError, UnicodeError):
            raise RuntimeError("CLOUD_INVALID_RESPONSE") from None

    def probe(self, token):
        return self._request("/v1/status", token).get("available") is True

    @staticmethod
    def _with_references(payload):
        """Añade únicamente URLs oficiales declaradas por el Worker; sin HTML/JS."""
        answer = payload.get("answer")
        if not isinstance(answer, str) or not answer.strip():
            raise RuntimeError("CLOUD_EMPTY_RESPONSE")
        answer = answer.strip()
        if len(answer) > 5100:
            return ("La explicación del modelo resultó demasiado extensa y no se mostrará "
                    "incompleta. Prueba una pregunta más específica.")
        refs = payload.get("sources", [])
        if not isinstance(refs, list):
            return answer
        allowed = {"support.microsoft.com", "learn.microsoft.com", "www.intel.com", "www.amd.com", "nvidia.custhelp.com"}
        names = set()
        items = []
        for source in refs[:3]:
            if not isinstance(source, dict):
                continue
            name, url = source.get("title"), source.get("url")
            if not isinstance(name, str) or not isinstance(url, str):
                continue
            name, url = name.strip(), url.strip()
            if not 3 <= len(name) <= 130 or not 10 <= len(url) <= 350:
                continue
            if any(ord(c) < 32 for c in name+url) or "<" in name+url or ">" in name+url:
                continue
            try:
                parsed = urllib.parse.urlsplit(url)
                if parsed.scheme != "https" or parsed.hostname not in allowed or parsed.username or parsed.password or parsed.port or parsed.fragment:
                    continue
            except ValueError:
                continue
            if url in names:
                continue
            names.add(url)
            items.append(name + "\n" + url)
        if not items:
            return answer
        # Jamás cortar una frase para hacer sitio a referencias. Si la respuesta
        # es extensa, mostrar solo las referencias que quepan completas.
        prefix = "\n\nDocumentación de referencia (catálogo CorePulse):\n"
        available = 5500 - len(answer) - len(prefix)
        fitted = []
        for item in items:
            needed = len(item) + (1 if fitted else 0)
            if needed <= available:
                fitted.append(item)
                available -= needed
        if not fitted:
            return answer
        return answer + prefix + "\n".join(fitted)

    @staticmethod
    def _safe_sources(payload):
        """Filtra enlaces de la nube: únicamente documentación oficial aprobada."""
        refs = payload.get("sources") if isinstance(payload, dict) else None
        if not isinstance(refs, list):
            return []
        allowed = {"support.microsoft.com", "learn.microsoft.com", "www.intel.com",
                   "www.amd.com", "nvidia.custhelp.com"}
        items, seen = [], set()
        for row in refs[:3]:
            if not isinstance(row, dict):
                continue
            title, url = row.get("title"), row.get("url")
            if not isinstance(title, str) or not isinstance(url, str):
                continue
            title, url = title.strip(), url.strip()
            if not 3 <= len(title) <= 130 or not 10 <= len(url) <= 350:
                continue
            if any(ord(c) < 32 for c in title + url) or any(c in title + url for c in "<>"):
                continue
            try:
                parsed = urllib.parse.urlsplit(url)
                if (parsed.scheme != "https" or parsed.hostname not in allowed or
                    parsed.username or parsed.password or parsed.port or parsed.fragment):
                    continue
            except ValueError:
                continue
            if url not in seen:
                seen.add(url)
                items.append({"title": title, "url": url})
        return items

    @staticmethod
    def _structured_content(payload):
        """Separa resumen, detalle verificable y referencias para la UI QML.

        No interpretar texto de Groq como dictamen propio. Un detalle solo se
        acepta cuando la respuesta declara el motor verificable autorizado.
        """
        answer = payload.get("answer") if isinstance(payload, dict) else None
        if not isinstance(answer, str) or not answer.strip():
            raise RuntimeError("CLOUD_EMPTY_RESPONSE")
        answer = answer.strip()
        if len(answer) > 5100:
            answer = ("La explicación del modelo resultó demasiado extensa y no se mostrará "
                      "incompleta. Prueba una pregunta más específica.")
        details = payload.get("details") if payload.get("assessmentEngine") == "corepulse-rules-v2" else None
        if not isinstance(details, str) or not details.strip() or len(details) > 5100:
            details = ""
        status = payload.get("assessmentStatus") if details else None
        if status not in ("recurrence_observed", "no_recurrence_in_recorded_events", "insufficient_data"):
            status = ""
        return {"text": answer, "details": details.strip(),
                "sources": CorePulseCloudGateway._safe_sources(payload),
                "verified": bool(details), "assessmentStatus": status}

    def chat_structured(self, token, question, snapshot, history, session_summary=None, session_comparison=None):
        """Chat cloud con tarjetas locales, sin segundo pedido para ver detalles."""
        recent = [{"role": x["role"], "content": x["text"][:1500]}
                  for x in (history or [])[-6:] if x.get("role") in ("user", "assistant")
                  and isinstance(x.get("text"), str)]
        payload = {"kind": "chat", "question": question[:1800],
                   "snapshot": snapshot, "history": recent}
        if isinstance(session_summary, dict):
            payload["sessionSummary"] = session_summary
        if isinstance(session_comparison, dict):
            payload["sessionComparison"] = session_comparison
        response = self._request("/v1/chat", token, payload)
        return self._structured_content(response)

    def chat(self, token, question, snapshot, history, session_summary=None, session_comparison=None):
        """Compatibilidad de integraciones anteriores que esperan texto plano."""
        recent = [{"role": x["role"], "content": x["text"].split("\n\nDocumentación de referencia (catálogo CorePulse):", 1)[0][:1500]}
                  for x in (history or [])[-6:] if x.get("role") in ("user", "assistant")
                  and isinstance(x.get("text"), str)]
        payload = {"kind": "chat", "question": question[:1800],
                   "snapshot": snapshot, "history": recent}
        if isinstance(session_summary, dict):
            payload["sessionSummary"] = session_summary
        if isinstance(session_comparison, dict):
            payload["sessionComparison"] = session_comparison
        response = self._request("/v1/chat", token, payload)
        return self._with_references(response)

    def diagnose(self, token, evidence):
        response = self._request("/v1/chat", token, {"kind": "diagnostic", "evidence": evidence})
        return self._with_references(response)


def cloud_token():
    # Reads the DPAPI-protected device token, never the account password.
    from core.cuenta import leer_sesion
    saved = leer_sesion()
    return saved[0] if saved else ""


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


def make_ai_controller(telemetry, system_health=None, cuenta=None, monitoring_insights=None):
    """Puente QObject único: red siempre en trabajador y QML solo recibe estados seguros."""
    from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot

    class AIController(QObject):
        changed = Signal()
        completed = Signal(int, str, str)

        def __init__(self):
            super().__init__()
            self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="CorePulseAI")
            self._generation = 0
            self._closed = False
            prefs = read_ai_preferences()
            self._enabled = prefs.get("enabled", True)
            # Preguntar es una acción explícita; nunca transmitimos texto al abrir CorePulse.
            self._consent = self._enabled and prefs.get("questions", True)
            self._hardware = False
            self._history_consent = False
            self._insights = monitoring_insights
            self._busy = False
            self._ready = False
            self._system_health = system_health
            self._diagnostic = {'status': 'idle', 'runId': 0, 'text': '',
                                'statusText': 'El diagnóstico con IA aún no se ha solicitado.'}
            self._status = ("Esperando conexión de CorePulse AI…" if self._enabled and self._consent
                            else "IA apagada o consultas deshabilitadas. No se transmiten datos.")
            self._messages = []
            self.completed.connect(self._finish)
            self._gateway = ModelGateway()  # compatibilidad interna; sin opción BYOK en la UI
            self._cloud = CorePulseCloudGateway(cloud_url() or CLOUD_ORIGIN)
            self._provider = "cloud"
            self._auto_probe_fingerprint = ""
            # Reintentos temporizados sin tráfico de telemetría ni preguntas.
            # singleShot evita dependencias nuevas y protege contra callbacks
            # que sobrevivan al logout o al apagado de la IA.
            self._reconnect_serial = 0
            self._reconnect_pending = False
            self._reconnect_attempt = 0
            self._account = cuenta
            if cuenta is not None:
                cuenta.changed.connect(self._account_changed)
            # Solo verifica sesión/servicio, nunca envía preguntas o hardware al iniciar.
            QTimer.singleShot(0, self._auto_connect_if_possible)

        def _account_token(self) -> str:
            # La credencial no se expone como propiedad QML. Se usa el token vivo
            # en memoria o el que se guardó cifrado con DPAPI en el inicio anterior.
            if not self._account or not self._account.conectado:
                return ""
            reader = getattr(self._account, "token_para_ai", None)
            token = reader() if callable(reader) else cloud_token()
            return token if isinstance(token, str) else ""

        def _cancel_reconnect(self):
            """Invalida esperas diferidas sin dejar timers persistentes activos."""
            self._reconnect_serial += 1
            self._reconnect_pending = False
            self._reconnect_attempt = 0

        def _schedule_reconnect(self, rate_limited=False):
            """Backoff máximo de 5 minutos. Nunca reenvía conversaciones."""
            if (self._closed or not self._enabled or not self._consent or
                    self._provider != "cloud" or not self._account_token() or
                    self._reconnect_pending):
                return
            delays = (15, 30, 60, 120, 300)
            seconds = delays[min(self._reconnect_attempt, len(delays)-1)]
            if rate_limited:
                seconds = max(seconds, 75)  # Worker: 8 solicitudes por 60 s
            self._reconnect_attempt += 1
            self._reconnect_pending = True
            serial = self._reconnect_serial
            fingerprint = hashlib.sha256(self._account_token().encode("utf-8")).hexdigest()
            self._status = f"Servicio temporalmente inaccesible. Reconectando en {seconds} s…"
            QTimer.singleShot(seconds * 1000,
                              lambda: self._scheduled_reconnect(serial, fingerprint))

        def _scheduled_reconnect(self, serial, fingerprint):
            if serial != self._reconnect_serial or self._closed or not self._reconnect_pending:
                return
            self._reconnect_pending = False
            token = self._account_token()
            if (not self._enabled or not self._consent or not token or
                    hashlib.sha256(token.encode("utf-8")).hexdigest() != fingerprint):
                return
            if self._ready:
                self._cancel_reconnect()
            elif self._busy:
                # No pisar una consulta explícita en curso ni crear varios probes.
                self._schedule_reconnect()
            else:
                self._auto_connect_if_possible(force=True)

        def _auto_connect_if_possible(self, force=False):
            if (self._closed or not self._enabled or not self._consent or self._busy
                    or self._ready or self._provider != "cloud"):
                return
            token = self._account_token()
            if not token:
                self._cancel_reconnect()
                self._status = "Inicia sesión en CorePulse para utilizar la IA."
                self.changed.emit()
                return
            fingerprint = hashlib.sha256(token.encode("utf-8")).hexdigest()
            if not force and fingerprint == self._auto_probe_fingerprint:
                return  # Sin bucles de reintento con una sesión/servicio caído.
            self._auto_probe_fingerprint = fingerprint
            self._status = "Conectando CorePulse AI Cloud…"
            self._run("connect", lambda: "available" if self._cloud.probe(token) else "missing")

        def _account_changed(self):
            if self._provider == "cloud" and (not self._account or not self._account.conectado):
                self._cancel_reconnect()
                if self._ready or self._busy:
                    self._generation += 1  # invalida resultados asíncronos de la sesión anterior
                    self._ready = self._busy = False
                    self._history_consent = False
                    self._messages.clear()
                self._auto_probe_fingerprint = ""
                self._status = "Inicia sesión en CorePulse para utilizar la IA."
            elif self._provider == "cloud":
                token = self._account_token()
                fingerprint = hashlib.sha256(token.encode("utf-8")).hexdigest() if token else ""
                if self._auto_probe_fingerprint and fingerprint != self._auto_probe_fingerprint:
                    # Cambio de cuenta: nunca reutilizar conversación, permiso de hardware
                    # ni resultado de una petición autenticada con la identidad anterior.
                    self._generation += 1
                    self._ready = self._busy = False
                    self._messages.clear()
                    self._hardware = self._history_consent = False
                    self._auto_probe_fingerprint = ""
                    self._cancel_reconnect()
                self._auto_connect_if_possible()
            self.changed.emit()

        @Property("QVariantMap", notify=changed)
        def state(self):
            return {"enabled": self._enabled, "consent": self._consent,
                    "hardware": self._hardware, "historyConsent": self._history_consent, "busy": self._busy,
                    "ready": self._ready, "provider": self._provider,
                    "cloudAvailable": self._cloud is not None,
                    "hasKey": bool(self._account and self._account.conectado) if self._provider == "cloud" else bool(read_key()),
                    "status": self._status, "messages": list(self._messages),
                    "diagnostic": dict(self._diagnostic)}

        @Slot(bool)
        def enable(self, value):
            self._enabled = bool(value)
            if not self._enabled:
                self._cancel_reconnect()
                self._generation += 1
                self._busy = self._ready = self._consent = self._hardware = self._history_consent = False
                self._messages.clear()
                self._diagnostic = {'status': 'idle', 'runId': 0, 'text': '',
                                    'statusText': 'La IA está apagada; no se enviaron lecturas.'}
                self._status = "IA apagada. No se transmiten datos."
            else:
                self._consent = read_ai_preferences().get("questions", True)
                self._auto_probe_fingerprint = ""
                self._status = "CorePulse AI se conectará a tu cuenta automáticamente."
            save_ai_preferences(enabled=self._enabled, questions=(self._consent if self._enabled else read_ai_preferences().get("questions", True)))
            if self._enabled and self._consent:
                self._auto_connect_if_possible()
            self.changed.emit()

        @Slot(bool)
        def allowQuestions(self, value):
            self._consent = bool(value) if self._enabled else False
            if not self._consent:
                self._cancel_reconnect()
                self._generation += 1
                self._ready = self._busy = self._hardware = self._history_consent = False
                self._messages.clear()
                self._diagnostic = {'status': 'idle', 'runId': 0, 'text': '',
                                    'statusText': 'Sin permiso de consulta; no se enviaron lecturas.'}
                self._status = "Permiso retirado. Conversación eliminada de la memoria de CorePulse."
            else:
                self._auto_probe_fingerprint = ""
                self._auto_connect_if_possible()
            save_ai_preferences(enabled=self._enabled, questions=self._consent)
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
            if not allowed:
                self._history_consent = False
            self.changed.emit()

        @Slot(bool)
        def allowHistory(self, value):
            allowed = (bool(value) and self._enabled and self._consent and
                       self._hardware and self._provider == "cloud" and self._insights is not None)
            if allowed != self._history_consent:
                self._generation += 1
                self._busy = False
                self._messages.clear()
                self._status = "Permiso de historial actualizado. Conversación anterior borrada."
            self._history_consent = allowed
            self.changed.emit()

        @Slot(str)
        def chooseProvider(self, provider):
            if provider not in ("cloud", "groq") or (provider == "cloud" and not self._cloud) or self._busy:
                return
            if provider == self._provider:
                return
            self._cancel_reconnect()
            self._provider = provider
            self._history_consent = False
            self._generation += 1
            self._ready = False
            self._messages.clear()
            self._diagnostic = {'status': 'idle', 'runId': 0, 'text': '',
                                'statusText': 'Proveedor cambiado; vuelve a conectar la IA.'}
            self._status = ("CorePulse AI Cloud requiere una sesión en corepulse.cl."
                            if provider == "cloud" else "Modo Groq: utiliza tu propia clave guardada en Windows.")
            self.changed.emit()

        @Slot(str, result=bool)
        def saveApiKey(self, value):
            if not self._enabled or self._busy or self._provider != "groq":
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
                        "CLOUD_RESPONSE_TOO_LARGE", "CLOUD_EMPTY_RESPONSE", "CLOUD_ACCOUNT_REQUIRED",
                        "CLOUD_INVALID_REQUEST", "CLOUD_HTTP_401", "CLOUD_HTTP_403",
                        "CLOUD_HTTP_429", "CLOUD_HTTP_503", "CLOUD_SERVICE_NOT_CONFIGURED",
                        "CLOUD_IDENTITY_UNAVAILABLE", "CLOUD_PROVIDER_UNAVAILABLE",
                        "CLOUD_MODEL_BUDGET_UNAVAILABLE", "CLOUD_RATE_LIMIT_UNAVAILABLE",
                        "CLOUD_MODEL_BUDGET_REACHED", "CLOUD_PROVIDER_RATE_LIMITED") else "CLOUD_CONNECTION_ERROR"
                if not self._closed:
                    self.completed.emit(seq, kind + ":" + code, str(result))
            future.add_done_callback(receive)

        @Slot()
        def connectCloud(self):
            if not self._enabled or not self._consent or self._busy:
                self._status = "Activa la IA y autoriza primero las consultas."
                self.changed.emit()
                return
            if self._provider == "cloud":
                if not self._account or not self._account.conectado:
                    self._status = "Inicia sesión en corepulse.cl para usar CorePulse AI Cloud."
                    self.changed.emit()
                    return
                self._cancel_reconnect()
                self._status = "Comprobando servicio CorePulse AI Cloud…"
                self._auto_connect_if_possible(force=True)
            else:
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
            key = self._account_token() if self._provider == "cloud" else read_key()
            if not key:
                self._ready = False
                self._status = "Sesión de CorePulse no disponible." if self._provider == "cloud" else "Clave no disponible. Vuelve a conectarte."
                self.changed.emit()
                return
            evidence = authorized_snapshot(dict(telemetry.metrics), self._hardware)
            history = list(self._messages)
            messages = make_messages(question, evidence, history)
            # Sólo enviar un agregado temporal bajo doble permiso y una pregunta
            # explícita de sesión/historial; nunca activar esto desde la IA.
            temporal_question = bool(re.search(
                r"(?i)\b(sesi[oó]n(?:es)?|tendencias?|historial|durante|sostenid[oa]s?|"
                r"prolongad[oa]s?|varios minutos|[uú]ltimas horas|"
                r"repit\w*|repet\w*|recurrente|compar\w*|reinicios)\b", question))
            share_session = (self._provider == "cloud" and self._hardware and
                             self._history_consent and temporal_question and self._insights is not None)
            session_summary = self._insights.ai_session_summary() if share_session else None
            # Separate cross-session intent: single-session questions never
            # authorize reading other boots, even when history permission is on.
            compare_question = bool(re.search(
                r"(?i)(compar\w*|repet\w*|repit\w*|"
                r"recurrente|varias sesiones|entre sesiones|sesiones anteriores|"
                r"sesiones pasadas|[uú]ltimas sesiones|distintos arranques|"
                r"varios reinicios|otras sesiones)", question))
            share_comparison = bool(share_session and compare_question)
            session_comparison = (self._insights.ai_multi_session_summary()
                                  if share_comparison else None)
            self._messages.append({"role": "user", "text": question})
            self._status = "Consultando CorePulse AI Cloud…" if self._provider == "cloud" else "Consultando GPT-OSS 120B…"
            def work():
                response = (self._cloud.chat_structured(key, question, evidence, history, session_summary, session_comparison)
                            if self._provider == "cloud" else {"text": self._gateway.chat(key, messages)})
                return json.dumps({"answer": response["text"], "evidence": evidence,
                                   "sessionSummary": session_summary, "details": response.get("details", ""),
                                   "sources": response.get("sources", []), "verified": response.get("verified", False),
                                   "assessmentStatus": response.get("assessmentStatus", "")}, ensure_ascii=False)
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
            key = self._account_token() if self._provider == "cloud" else read_key()
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
                answer = (self._cloud.diagnose(key, evidence) if self._provider == "cloud"
                          else self._gateway.chat(key, messages))
                return json.dumps({'answer': answer, 'evidence': snapshot, 'runId': run_id}, ensure_ascii=False)
            self._run('diagnostic', work)

        @Slot(int, str, str)
        def _finish(self, seq, event, result):
            if seq != self._generation or self._closed or not self._enabled or not self._consent:
                return
            self._busy = False
            if event == "connect:ok":
                self._ready = (result == "available" and
                               (self._provider != "cloud" or bool(self._account_token())))
                if self._ready:
                    self._cancel_reconnect()
                    self._status = "Conectada · CorePulse AI Cloud" if self._provider == "cloud" else "Conectada · GPT-OSS 120B en Groq"
                elif self._provider == "cloud":
                    self._schedule_reconnect()  # servicio temporalmente no disponible
                else:
                    self._status = "El servicio de IA no está disponible o no está configurado."
            elif event == "chat:ok":
                try:
                    payload = json.loads(result)
                    text = payload["answer"]
                    evidence = payload["evidence"]
                    session_summary = payload.get("sessionSummary")
                    normalized = readable_answer(text)
                    # Dos barreras: la salida original y la misma salida sin marcado.
                    # Markdown / HTML no deben permitir eludir REAL_OR_NA.
                    if reject_unbacked_measures(text, evidence, session_summary) or reject_unbacked_measures(normalized, evidence, session_summary):
                        self._messages.append({"role": "assistant", "text": fallback(evidence)})
                        self._status = "Se descartaron afirmaciones numéricas sin respaldo."
                    else:
                        details = payload.get("details", "")
                        verified = payload.get("verified") is True and isinstance(details, str)
                        # El desglose proviene exclusivamente del motor de reglas;
                        # las verificaciones de cifras del modelo siguen separadas.
                        items = payload.get("sources", [])
                        sources = items if isinstance(items, list) else []
                        self._messages.append({"role": "assistant", "text": normalized,
                                               "details": readable_answer(details) if verified else "",
                                               "detailsOpen": False, "sources": sources[:3],
                                               "sourcesOpen": False, "verified": verified,
                                               "assessmentStatus": payload.get("assessmentStatus", "") if verified else ""})
                        self._status = "Dictamen calculado por CorePulse." if verified else "Respuesta generada; no equivale a diagnóstico confirmado."
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
                labels.update({"CLOUD_HTTP_401": "Inicia sesión nuevamente en CorePulse.",
                               "CLOUD_HTTP_403": "Acceso a CorePulse AI no autorizado.",
                               "CLOUD_HTTP_429": "Límite de consultas alcanzado.",
                               "CLOUD_SERVICE_NOT_CONFIGURED": "Falta configurar un secreto o servicio en Cloudflare.",
                               "CLOUD_IDENTITY_UNAVAILABLE": "Cloudflare no pudo verificar tu cuenta en corepulse.cl.",
                               "CLOUD_PROVIDER_UNAVAILABLE": "Groq no está disponible desde el servicio cloud.",
                               "CLOUD_MODEL_BUDGET_UNAVAILABLE": "El control de presupuesto cloud no está disponible.",
                               "CLOUD_RATE_LIMIT_UNAVAILABLE": "El control de solicitudes cloud no está disponible.",
                               "CLOUD_MODEL_BUDGET_REACHED": "Se alcanzó el presupuesto de IA del servicio.",
                               "CLOUD_PROVIDER_RATE_LIMITED": "Groq alcanzó su límite de consultas.",
                               "CLOUD_HTTP_503": "El servicio cloud devolvió un error temporal (503).",
                               "CLOUD_ACCOUNT_REQUIRED": "Inicia sesión en corepulse.cl."})
                self._status = labels.get(result, "El servicio cloud no está disponible. Reintenta más tarde.")
                if event.startswith("chat:"):
                    self._messages.append({"role": "assistant", "text": "No fue posible obtener respuesta de la nube; no se realizó diagnóstico."})
                if event.startswith('diagnostic:'):
                    self._diagnostic = {'status': 'error', 'runId': int(self._diagnostic.get('runId', 0)), 'text': '',
                                        'statusText': 'La IA no respondió. El diagnóstico local sigue disponible; intenta de nuevo más tarde.'}
                # Solo los fallos de transporte/servicio pueden reconectar.
                # 401/403, presupuesto agotado y permisos requieren acción humana;
                # tampoco reenviar automáticamente la pregunta que falló.
                transient = {"CLOUD_CONNECTION_ERROR", "CLOUD_HTTP_503",
                             "CLOUD_IDENTITY_UNAVAILABLE", "CLOUD_RATE_LIMIT_UNAVAILABLE",
                             "CLOUD_HTTP_429"}
                if self._provider == "cloud" and result in transient:
                    self._ready = False
                    self._schedule_reconnect(rate_limited=(result == "CLOUD_HTTP_429"))
                elif self._provider == "cloud" and result in ("CLOUD_HTTP_401", "CLOUD_HTTP_403",
                            "CLOUD_ACCOUNT_REQUIRED", "CLOUD_MODEL_BUDGET_REACHED"):
                    self._cancel_reconnect()
                    self._ready = False if result != "CLOUD_MODEL_BUDGET_REACHED" else self._ready
            self._messages = self._messages[-20:]
            self.changed.emit()

        @Slot(int)
        def toggleMessageDetails(self, index):
            if not (self._enabled and self._consent and self._hardware and
                    self._history_consent and self._provider == "cloud"):
                return
            if 0 <= index < len(self._messages):
                row = self._messages[index]
                if row.get("role") == "assistant" and row.get("verified") and row.get("details"):
                    row["detailsOpen"] = not row.get("detailsOpen", False)
                    self.changed.emit()

        @Slot(int)
        def toggleMessageSources(self, index):
            if not (self._enabled and self._consent):
                return
            if 0 <= index < len(self._messages):
                row = self._messages[index]
                if row.get("role") == "assistant" and row.get("sources"):
                    row["sourcesOpen"] = not row.get("sourcesOpen", False)
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
            self._cancel_reconnect()
            self._generation += 1
            self._executor.shutdown(wait=False, cancel_futures=True)

    return AIController()
