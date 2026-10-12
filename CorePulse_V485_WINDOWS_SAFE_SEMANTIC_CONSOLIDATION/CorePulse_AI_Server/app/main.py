from __future__ import annotations
import hashlib
import json
import threading
import time
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from .config import DAILY_LIMIT, DEDUP_SECONDS, MODEL_NAME, MODEL_PROVIDER, MODEL_BASE_URL
from .store import register_installation, token_valid, consume_request
from .evidence import sanitize_context, fallback_summary, fallback_answer
from .tutorial_followups import video_followup_reply
from .maintenance_followups import maintenance_followup_reply
from .model_gateway import model_ready, model_reachable, generate
from .guardrails import validate_model_response, evidence_fields, POLICY_VERSION
from .intelligence_engine import analyze_evidence, format_diagnostic_brief, is_diagnostic_request, ENGINE_VERSION

app = FastAPI(title='CorePulse AI', version='1.8.0')

# Las solicitudes demasiado grandes se rechazan antes de procesar evidencia y preguntas.
# Se cuenta también el cuerpo transferido en chunks, sin depender de Content-Length.
MAX_REQUEST_BYTES = 128 * 1024

class RequestSizeLimit:
    """ASGI: límite del cuerpo JSON, incluso sin Content-Length.

    Lee como máximo 128 KiB antes de entregar la solicitud al enrutador.
    Así nunca se inicia una respuesta y luego se intenta enviar un 413.
    """
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        from starlette.responses import JSONResponse
        length = dict(scope.get('headers') or []).get(b'content-length')
        if length is not None:
            try:
                if int(length) > MAX_REQUEST_BYTES:
                    return await JSONResponse({'detail': 'Solicitud demasiado grande.'}, status_code=413)(scope, receive, send)
            except ValueError:
                return await JSONResponse({'detail': 'Content-Length inválido.'}, status_code=400)(scope, receive, send)
        chunks = []
        read = 0
        while True:
            msg = await receive()
            if msg['type'] == 'http.disconnect':
                return
            if msg['type'] != 'http.request':
                return
            read += len(msg.get('body') or b'')
            if read > MAX_REQUEST_BYTES:
                return await JSONResponse({'detail': 'Solicitud demasiado grande.'}, status_code=413)(scope, receive, send)
            chunks.append(msg)
            if not msg.get('more_body', False):
                break
        async def replay():
            if chunks:
                return chunks.pop(0)
            return await receive()
        return await self.app(scope, replay, send)

app.add_middleware(RequestSizeLimit)

_recent_lock = threading.Lock()
_recent_responses: dict[str, tuple[float, dict]] = {}


def _fingerprint(token: str, payload: dict) -> str:
    text = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    return hashlib.sha256((token + '\n' + text).encode('utf-8')).hexdigest()


def _cached_response(key: str):
    if DEDUP_SECONDS <= 0:
        return None
    now = time.monotonic()
    with _recent_lock:
        stale = [k for k, (ts, _) in _recent_responses.items() if now - ts > DEDUP_SECONDS]
        for k in stale:
            _recent_responses.pop(k, None)
        item = _recent_responses.get(key)
        if item and now - item[0] <= DEDUP_SECONDS:
            out = dict(item[1])
            out['deduplicated'] = True
            return out
    return None


def _remember_response(key: str, response: dict):
    if DEDUP_SECONDS <= 0:
        return
    with _recent_lock:
        _recent_responses[key] = (time.monotonic(), dict(response))


class RegisterRequest(BaseModel):
    installation_id: str = Field(min_length=8, max_length=128)
    client_version: str = Field(default='', max_length=32)
    platform: str = Field(default='Windows', max_length=32)
    python: str = Field(default='', max_length=32)


class AnalyzeRequest(BaseModel):
    context: dict
    question: str = Field(default='', max_length=1200)


class ChatMessage(BaseModel):
    role: str = Field(max_length=16)
    content: str = Field(max_length=1800)


class ChatRequest(BaseModel):
    context: dict
    question: str = Field(min_length=1, max_length=1200)
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)


def _bearer(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith('bearer '):
        raise HTTPException(status_code=401, detail='Token requerido.')
    token = authorization.split(' ', 1)[1].strip()
    if not token_valid(token):
        raise HTTPException(status_code=401, detail='Token inválido o revocado.')
    return token


def _consume_or_raise(token: str) -> int:
    allowed, remaining = consume_request(token)
    if not allowed:
        raise HTTPException(status_code=429, detail='Límite diario de CorePulse AI alcanzado.')
    return remaining


@app.get('/v1/status')
def status():
    configured = model_ready()
    reachable = model_reachable() if configured else False
    return {
        'ok': True,
        'service': 'CorePulse AI',
        'service_version': '1.8.0',
        'intelligence_engine_version': ENGINE_VERSION,
        'safety_policy_version': POLICY_VERSION,
        'model_ready': configured and reachable,
        'model_configured': configured,
        'model_reachable': reachable,
        'model_name': MODEL_NAME or None,
        'model_provider': MODEL_PROVIDER,
        'model_binding': (hashlib.sha256((MODEL_BASE_URL + '\n' + MODEL_NAME).encode('utf-8')).hexdigest()
                          if MODEL_PROVIDER == 'openai_compatible' and MODEL_BASE_URL and MODEL_NAME else None),
        'daily_limit': DAILY_LIMIT,
        'dedup_seconds': DEDUP_SECONDS,
    }


@app.get('/v1/session')
def session(authorization: str | None = Header(default=None)):
    # Comprobacion segura del emparejamiento, sin costo de inferencia, sin
    # telemetria y sin consumir la cuota de consultas.
    _bearer(authorization)
    return {'ok': True, 'paired': True}


@app.post('/v1/register')
def register(req: RegisterRequest, x_corepulse_enrollment: str | None = Header(default=None)):
    # No se acepta un secreto maestro distribuido a todos los usuarios.
    # El código de un uso se genera fuera de la API mediante app.admin.
    code = str(x_corepulse_enrollment or '').strip()
    token = register_installation(req.installation_id, req.client_version, req.platform, code)
    if not token:
        raise HTTPException(status_code=403, detail='Código de vinculación inválido, usado o expirado.')
    return {'ok': True, 'token': token}


def _safe_generation(context: dict, question: str, *, task: str, history: list | None = None) -> tuple[str, str, dict]:
    """La verificación es externa al prompt y se ejecuta incluso si el LLM lo ignora."""
    diagnostic = is_diagnostic_request(question, task)
    def safe_fallback():
        return (format_diagnostic_brief(analyze_evidence(context)) if diagnostic
                else (fallback_summary(context) if task == 'analysis' else fallback_answer(context, question)))
    if not model_ready():
        text = safe_fallback()
        return text, 'evidence_fallback', {'allowed': True, 'codes': ['MODEL_NOT_CONFIGURED'], 'policy_version': POLICY_VERSION}
    try:
        text = generate(context, question, history=history, task=task) if history is not None else generate(context, question, task=task)
        verdict = validate_model_response(context, text, question=question)
        if verdict['allowed']:
            return text, 'model', verdict
        fallback = safe_fallback()
        return fallback, 'evidence_fallback', verdict
    except Exception:
        fallback = safe_fallback()
        return fallback, 'evidence_fallback', {'allowed': False, 'codes': ['MODEL_ERROR'], 'policy_version': POLICY_VERSION}


@app.post('/v1/analyze')
def analyze(req: AnalyzeRequest, authorization: str | None = Header(default=None)):
    token = _bearer(authorization)
    context = sanitize_context(req.context)
    question = req.question.strip()
    payload = {'kind': 'analyze', 'context': context, 'question': question}
    fingerprint = _fingerprint(token, payload)
    cached = _cached_response(fingerprint)
    if cached is not None:
        return cached
    remaining = _consume_or_raise(token)
    text, mode, guardrails = _safe_generation(context, question, task='analysis')
    response = {'ok': True, 'mode': mode, 'text': text, 'remaining_today': remaining,
                'guardrails': guardrails, 'evidence_fields': evidence_fields(context),
                'intelligence': analyze_evidence(context)}
    _remember_response(fingerprint, response)
    return response


@app.post('/v1/chat')
def chat(req: ChatRequest, authorization: str | None = Header(default=None)):
    token = _bearer(authorization)
    context = sanitize_context(req.context)
    question = req.question.strip()
    history = [item.model_dump() for item in req.history[-8:]]
    payload = {'kind': 'chat', 'context': context, 'question': question, 'history': history}
    fingerprint = _fingerprint(token, payload)
    cached = _cached_response(fingerprint)
    if cached is not None:
        return cached
    remaining = _consume_or_raise(token)
    video_reply = video_followup_reply(question, history)
    maintenance_reply = maintenance_followup_reply(question, history, context) if video_reply is None else None
    if video_reply is not None:
        # Ruta determinista propia: no consulta el LLM ni contacta YouTube.
        text, mode = video_reply, 'curated_search'
        guardrails = {'allowed': True, 'codes': ['PUBLIC_SEARCH_ONLY'], 'policy_version': POLICY_VERSION}
    elif maintenance_reply is not None:
        # V470: tema heredado, nombres SOLO de evidencia saneada del turno actual.
        text, mode = maintenance_reply, 'curated_search'
        guardrails = {'allowed': True, 'codes': ['PUBLIC_SEARCH_ONLY', 'CONTEXTUAL_MAINTENANCE'], 'policy_version': POLICY_VERSION}
    else:
        text, mode, guardrails = _safe_generation(context, question, history=history, task='chat')
    response = {'ok': True, 'mode': mode, 'text': text, 'remaining_today': remaining,
                'guardrails': guardrails, 'evidence_fields': evidence_fields(context),
                'intelligence': analyze_evidence(context)}
    _remember_response(fingerprint, response)
    return response
