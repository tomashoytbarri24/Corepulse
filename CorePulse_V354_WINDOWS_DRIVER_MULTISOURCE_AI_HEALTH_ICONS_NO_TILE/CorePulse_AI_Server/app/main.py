from __future__ import annotations
import hashlib
import json
import threading
import time
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from .config import DAILY_LIMIT, DEDUP_SECONDS, MODEL_NAME
from .store import register_installation, token_valid, consume_request
from .evidence import sanitize_context, fallback_summary, fallback_answer
from .model_gateway import model_ready, model_reachable, generate

app = FastAPI(title='CorePulse AI', version='1.3.0')

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
        'service_version': '1.3.0',
        'model_ready': configured and reachable,
        'model_configured': configured,
        'model_reachable': reachable,
        'model_name': MODEL_NAME or None,
        'daily_limit': DAILY_LIMIT,
        'dedup_seconds': DEDUP_SECONDS,
    }


@app.post('/v1/register')
def register(req: RegisterRequest):
    token = register_installation(req.installation_id, req.client_version, req.platform)
    return {'ok': True, 'token': token}


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
    if model_ready():
        try:
            text = generate(context, question, task='analysis')
            mode = 'model'
        except Exception:
            text = fallback_summary(context)
            mode = 'evidence_fallback'
    else:
        text = fallback_summary(context)
        mode = 'evidence_fallback'
    response = {'ok': True, 'mode': mode, 'text': text, 'remaining_today': remaining}
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
    if model_ready():
        try:
            text = generate(context, question, history=history, task='chat')
            mode = 'model'
        except Exception:
            text = fallback_answer(context, question)
            mode = 'evidence_fallback'
    else:
        text = fallback_answer(context, question)
        mode = 'evidence_fallback'
    response = {'ok': True, 'mode': mode, 'text': text, 'remaining_today': remaining}
    _remember_response(fingerprint, response)
    return response
