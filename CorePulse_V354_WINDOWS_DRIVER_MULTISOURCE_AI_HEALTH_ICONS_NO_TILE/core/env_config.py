"""Carga segura de variables de entorno de CorePulse.

V331 ya no espera claves de proveedores de IA en el PC del usuario. El único
ajuste de IA de cliente es la URL del backend propio CorePulse AI.
"""
from __future__ import annotations
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
