"""V472: proveedor OpenAI-compatible configurado sin almacenar secretos en archivos.

NO es un segundo modelo incluido: requiere un servidor HTTPS de inferencia elegido
por el usuario. Los destinos se validan antes de cualquier solicitud de red.
"""
from __future__ import annotations
import json
import hashlib
import os
import urllib.parse
from pathlib import Path

COMPATIBLE_KEY_NAME = "corepulse_compatible_backend_key"


def validate_upstream_url(value: str, *, allow_internal_http: bool = False) -> str:
    supplied = str(value or "")
    if any(ch.isspace() for ch in supplied):
        return ""
    raw = supplied.rstrip("/")
    if not raw or len(raw) > 2048:
        return ""
    try:
        parsed = urllib.parse.urlsplit(raw)
        if (parsed.scheme not in ({"https", "http"} if allow_internal_http else {"https"})
                or not parsed.hostname or parsed.username is not None or parsed.password is not None
                or parsed.query or parsed.fragment or parsed.path.rstrip("/") != "/v1"
                or not parsed.netloc or parsed.port == 0):
            return ""
        # Los puentes locales no deben aceptar destinos loopback al habilitar el servidor externo.
        if not allow_internal_http and parsed.hostname.lower() in {"localhost", "127.0.0.1", "::1", "0.0.0.0"}:
            return ""
        return raw
    except (TypeError, ValueError):
        return ""


def validate_model_id(value: str) -> str:
    model = str(value or "").strip()
    if not 1 <= len(model) <= 180 or any(ch.isspace() or ord(ch) < 32 for ch in model):
        return ""
    return model


def provider_settings_path(local_appdata: str | None = None) -> Path:
    base = local_appdata if local_appdata is not None else os.getenv('LOCALAPPDATA', '')
    if not base:
        # No introducir claves en la carpeta del ZIP. En Linux se prefiere configurar ENV.
        base = os.getenv('XDG_CONFIG_HOME', str(Path.home() / '.config'))
    return Path(base) / 'CorePulse' / 'ai_compatible_provider.json'


def load_provider_settings(path: Path | None = None) -> dict[str, str]:
    try:
        value = json.loads((path or provider_settings_path()).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}
    if not isinstance(value, dict):
        return {}
    endpoint = validate_upstream_url(value.get('base_url'))
    model = validate_model_id(value.get('model'))
    return {'base_url': endpoint, 'model': model} if endpoint and model else {}


def save_provider_settings(endpoint: str, model: str, *, path: Path | None = None) -> bool:
    endpoint = validate_upstream_url(endpoint)
    model = validate_model_id(model)
    if not (endpoint and model):
        return False
    dest = path or provider_settings_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix('.tmp')
    try:
        tmp.write_text(json.dumps({'base_url': endpoint, 'model': model}, ensure_ascii=False), encoding='utf-8')
        os.replace(tmp, dest)
    finally:
        try: tmp.unlink(missing_ok=True)
        except OSError: pass
    return True


def compatible_key_name(endpoint: str) -> str:
    """El secreto está ligado al ORIGEN, nunca se reusa al cambiar de host."""
    safe = validate_upstream_url(endpoint)
    if not safe:
        return ''
    return COMPATIBLE_KEY_NAME + '_' + hashlib.sha256(safe.encode('utf-8')).hexdigest()[:24]


def read_compatible_key(endpoint: str | None = None) -> str:
    from .secrets import read_secret
    destination = endpoint or load_provider_settings().get('base_url', '')
    name = compatible_key_name(destination)
    return str(read_secret(name) or '').strip() if name else ''


def save_compatible_key(value: str, endpoint: str) -> bool:
    from .secrets import save_secret
    name = compatible_key_name(endpoint)
    return bool(name and save_secret(name, value))
