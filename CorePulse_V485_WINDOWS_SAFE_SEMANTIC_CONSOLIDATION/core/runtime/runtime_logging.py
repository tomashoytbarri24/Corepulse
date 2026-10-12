"""Observabilidad de ejecución para CorePulse.

Centraliza el registro de fallos sin convertirlos en datos de hardware. Los logs son
solo diagnósticos de software y nunca sustituyen la política REAL_OR_NA.
"""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import re
import sys
import threading
from typing import Optional
from core.runtime_paths import log_dir as runtime_log_dir

try:
    from platformdirs import user_log_dir
except Exception:  # pragma: no cover - fallback sin dependencia externa
    user_log_dir = None

_LOGGER_NAME = 'CorePulse'
_CONFIG_LOCK = threading.RLock()
_CONFIGURED = False
_LOG_PATH: Optional[Path] = None
_HOOKS_INSTALLED = False

_SECRET_PATTERNS = (
    re.compile(r'(?i)(COREPULSE_AI_TOKEN\s*[=:]\s*)[^\s,;]+'),
    re.compile(r'(?i)(api[_-]?key\s*[=:]\s*)[^\s,;]+'),
    re.compile(r'(?i)(authorization\s*[=:]\s*bearer\s+)[^\s,;]+'),
)


def redact_sensitive_text(value) -> str:
    """Elimina secretos reconocibles antes de persistir mensajes en un log."""
    text = str(value)
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub(r'\1<redacted>', text)
    return text


class _SecretRedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.msg = redact_sensitive_text(record.msg)
            if record.args:
                if isinstance(record.args, dict):
                    record.args = {k: redact_sensitive_text(v) for k, v in record.args.items()}
                else:
                    record.args = tuple(redact_sensitive_text(v) for v in record.args)
        except Exception:
            # El filtro jamás debe impedir que CorePulse continúe funcionando.
            pass
        return True


def _default_log_dir() -> Path:
    return runtime_log_dir()


def configure_runtime_logging(*, log_dir=None, level=None) -> Optional[Path]:
    """Configura un log rotativo e idempotente y devuelve su ruta real.

    Si el sistema no permite crear el archivo, CorePulse conserva un logger de
    consola y devuelve ``None``; un fallo de observabilidad nunca bloquea la app.
    """
    global _CONFIGURED, _LOG_PATH
    with _CONFIG_LOCK:
        if _CONFIGURED:
            return _LOG_PATH

        logger = logging.getLogger(_LOGGER_NAME)
        logger.setLevel(level or (logging.DEBUG if os.getenv('COREPULSE_DEBUG') == '1' else logging.INFO))
        logger.propagate = False
        redactor = _SecretRedactionFilter()

        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(threadName)s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
        )

        try:
            directory = Path(log_dir).expanduser() if log_dir else _default_log_dir()
            directory.mkdir(parents=True, exist_ok=True)
            path = directory / 'corepulse.log'
            handler = RotatingFileHandler(path, maxBytes=2 * 1024 * 1024, backupCount=3, encoding='utf-8')
            handler.setFormatter(formatter)
            handler.addFilter(redactor)
            logger.addHandler(handler)
            _LOG_PATH = path
        except Exception:
            _LOG_PATH = None

        if not logger.handlers:
            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(formatter)
            handler.addFilter(redactor)
            logger.addHandler(handler)

        _CONFIGURED = True
        logger.info('Runtime logging initialized')
        return _LOG_PATH


def get_logger(name=None) -> logging.Logger:
    configure_runtime_logging()
    suffix = str(name or '').strip()
    return logging.getLogger(f'{_LOGGER_NAME}.{suffix}' if suffix else _LOGGER_NAME)


def get_runtime_log_path() -> Optional[str]:
    configure_runtime_logging()
    return str(_LOG_PATH) if _LOG_PATH is not None else None


def install_exception_hooks() -> None:
    """Registra excepciones no controladas del hilo principal y de workers."""
    global _HOOKS_INSTALLED
    with _CONFIG_LOCK:
        if _HOOKS_INSTALLED:
            return
        logger = get_logger('uncaught')
        previous_sys_hook = sys.excepthook
        previous_thread_hook = getattr(threading, 'excepthook', None)

        def sys_hook(exc_type, exc_value, exc_traceback):
            if exc_type is KeyboardInterrupt:
                return previous_sys_hook(exc_type, exc_value, exc_traceback)
            logger.critical('Unhandled main-thread exception', exc_info=(exc_type, exc_value, exc_traceback))
            if previous_sys_hook:
                previous_sys_hook(exc_type, exc_value, exc_traceback)

        def thread_hook(args):
            logger.critical(
                'Unhandled worker exception in %s',
                getattr(getattr(args, 'thread', None), 'name', 'unknown'),
                exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
            )
            if previous_thread_hook:
                previous_thread_hook(args)

        sys.excepthook = sys_hook
        if previous_thread_hook is not None:
            threading.excepthook = thread_hook
        _HOOKS_INSTALLED = True

# V483: configuración del entorno integrada con la observabilidad del runtime.
from core.version import VERSION_LABEL as VERSION

from pathlib import Path

from typing import Dict

import os

import re

from core.runtime_paths import env_candidates

ENV_POLICY = 'RUNTIME_DOTENV_ONLY_NO_ENV_EXAMPLE_DEPENDENCY'

ENV_EXAMPLE_POLICY = 'OPTIONAL_DOCUMENTATION_ONLY_NEVER_RUNTIME_INPUT'

_LOADED = False

_STATUS: Dict[str, object] = {'loaded': False, 'path': None, 'loader': None, 'python_dotenv_available': False, 'corepulse_ai_base_url_configured': False}

_ENV_LINE = re.compile(r'^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$')

def _candidate_env_files() -> list[Path]:
    candidates=[]
    explicit=os.getenv('COREPULSE_ENV_FILE','').strip()
    if explicit:
        try: candidates.append(Path(explicit).expanduser().resolve())
        except Exception: candidates.append(Path(explicit).expanduser())
    candidates.extend(env_candidates())
    out=[]; seen=set()
    for p in candidates:
        k=str(p).casefold()
        if k not in seen:
            seen.add(k); out.append(p)
    return out

def _parse_env_value(raw: str) -> str:
    value=raw.strip()
    if not value: return ''
    if value[0:1] in {'"', "'"}:
        q=value[0]; end=value.find(q,1)
        return value[1:end] if end >= 1 else value[1:]
    return re.split(r'\s+#', value, maxsplit=1)[0].strip()

def _load_builtin(path: Path) -> bool:
    try: text=path.read_text(encoding='utf-8-sig')
    except Exception: return False
    applied=False
    for raw in text.splitlines():
        line=raw.strip()
        if not line or line.startswith('#'): continue
        m=_ENV_LINE.match(line)
        if not m: continue
        key, raw_value=m.group(1),m.group(2)
        if key in os.environ: continue
        os.environ[key]=_parse_env_value(raw_value); applied=True
    return applied or path.is_file()

def load_corepulse_env() -> Dict[str, object]:
    global _LOADED, _STATUS
    if _LOADED:
        _STATUS['corepulse_ai_base_url_configured']=bool(str(os.getenv('COREPULSE_AI_BASE_URL') or '').strip())
        return dict(_STATUS)
    _LOADED=True
    load_dotenv=None
    try:
        from dotenv import load_dotenv as _load_dotenv
        load_dotenv=_load_dotenv; _STATUS['python_dotenv_available']=True
    except Exception:
        _STATUS['python_dotenv_available']=False
    for env_path in _candidate_env_files():
        try:
            if not env_path.is_file(): continue
            loaded=False
            if load_dotenv is not None:
                try:
                    load_dotenv(dotenv_path=env_path, override=False, encoding='utf-8-sig'); loaded=True; _STATUS['loader']='python-dotenv'
                except Exception: loaded=False
            if not loaded:
                loaded=_load_builtin(env_path)
                if loaded: _STATUS['loader']='builtin'
            if loaded:
                _STATUS['loaded']=True; _STATUS['path']=str(env_path); break
        except Exception: continue
    _STATUS['corepulse_ai_base_url_configured']=bool(str(os.getenv('COREPULSE_AI_BASE_URL') or '').strip())
    return dict(_STATUS)

def ai_runtime_status() -> Dict[str, object]:
    state=load_corepulse_env()
    base=str(os.getenv('COREPULSE_AI_BASE_URL') or 'http://127.0.0.1:8765').strip()
    return {
        'status':'CLIENT_CONFIGURED',
        'reason':'CorePulse AI se valida al consultar el backend; no requiere API key del usuario.',
        'ai_enabled':True,
        'base_url':base,
        'env_loaded':bool(state.get('loaded')),
        'env_path':state.get('path'),
        'env_loader':state.get('loader'),
        'secret_exposed':False,
    }

def env_status() -> Dict[str, object]:
    status=dict(_STATUS)
    status['corepulse_ai_base_url_configured']=bool(str(os.getenv('COREPULSE_AI_BASE_URL') or '').strip())
    return status

load_corepulse_env()

__all__=['load_corepulse_env','env_status','ai_runtime_status','VERSION','ENV_POLICY','ENV_EXAMPLE_POLICY']
