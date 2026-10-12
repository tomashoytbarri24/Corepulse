from __future__ import annotations
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv(Path(__file__).resolve().parents[1] / '.env')

ROOT = Path(__file__).resolve().parents[1]
# El puente Groq es un proceso LOCAL distinto del LLM: sus vinculaciones deben
# sobrevivir a la sustitucion de la carpeta ZIP de CorePulse.
# El despliegue dedicado conserva COREPULSE_AI_DATA_DIR como override explicito.
def default_data_dir(root: Path, *, provider: str, windows: bool, local_appdata: str) -> Path:
    if provider in {'groq', 'openai_compatible'} and windows and local_appdata.strip():
        folder = 'ai_cloud_bridge' if provider == 'groq' else 'ai_compatible_bridge'
        return Path(local_appdata) / 'CorePulse' / folder
    return root / 'data'


DATA_DIR = Path(os.getenv('COREPULSE_AI_DATA_DIR') or default_data_dir(
    ROOT,
    provider=os.getenv('COREPULSE_MODEL_PROVIDER', '').strip().lower(),
    windows=os.name == 'nt',
    local_appdata=os.getenv('LOCALAPPDATA', ''),
)).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / 'corepulse_ai.sqlite3'
HOST = os.getenv('COREPULSE_AI_HOST', '127.0.0.1')
PORT = int(os.getenv('COREPULSE_AI_PORT', '8765'))
DAILY_LIMIT = max(1, int(os.getenv('COREPULSE_AI_DAILY_LIMIT', '200')))
DEDUP_SECONDS = max(0.0, float(os.getenv('COREPULSE_AI_DEDUP_SECONDS', '8')))

# V463: proveedor de inferencia intercambiable. Los secretos nunca se distribuyen
# a los clientes Windows; en pruebas el puente sólo escucha en 127.0.0.1.
MODEL_PROVIDER = os.getenv('COREPULSE_MODEL_PROVIDER', 'custom').strip().lower()
if MODEL_PROVIDER == 'groq':
    from .secrets import read_groq_key
    # Endpoint e ID fijos para evitar enviar la clave a un host arbitrario.
    MODEL_BASE_URL = 'https://api.groq.com/openai/v1'
    MODEL_NAME = 'openai/gpt-oss-120b'
    from .groq_credentials import choose_key
    (MODEL_API_KEY, GROQ_KEY_SOURCE, GROQ_KEY_CONFLICT,
     GROQ_KEY_PRESENT_ENV, GROQ_KEY_PRESENT_MANAGER) = choose_key(
         os.getenv('GROQ_API_KEY'), read_groq_key())
elif MODEL_PROVIDER == 'openai_compatible':
    from .provider_independence import load_provider_settings, read_compatible_key, validate_upstream_url, validate_model_id
    _settings = load_provider_settings()
    MODEL_BASE_URL = validate_upstream_url(os.getenv('COREPULSE_MODEL_BASE_URL') or _settings.get('base_url'))
    MODEL_NAME = validate_model_id(os.getenv('COREPULSE_MODEL_NAME') or _settings.get('model'))
    MODEL_API_KEY = read_compatible_key(MODEL_BASE_URL) if os.name == 'nt' else os.getenv('COREPULSE_MODEL_API_KEY', '').strip()
    GROQ_KEY_SOURCE = 'NONE'
    GROQ_KEY_CONFLICT = False
    GROQ_KEY_PRESENT_ENV = False
    GROQ_KEY_PRESENT_MANAGER = False
else:
    MODEL_BASE_URL = os.getenv('COREPULSE_MODEL_BASE_URL', '').rstrip('/')
    MODEL_NAME = os.getenv('COREPULSE_MODEL_NAME', '').strip()
    MODEL_API_KEY = os.getenv('COREPULSE_MODEL_API_KEY', '').strip()
    GROQ_KEY_SOURCE = 'NONE'
    GROQ_KEY_CONFLICT = False
    GROQ_KEY_PRESENT_ENV = False
    GROQ_KEY_PRESENT_MANAGER = False
MODEL_TIMEOUT = max(5, int(os.getenv('COREPULSE_MODEL_TIMEOUT', '90')))
MODEL_STATUS_TIMEOUT = max(1, min(10, int(os.getenv('COREPULSE_MODEL_STATUS_TIMEOUT', '3'))))
MODEL_TEMPERATURE = max(0.0, min(1.0, float(os.getenv('COREPULSE_MODEL_TEMPERATURE', '0.2'))))
MODEL_MAX_TOKENS = max(128, min(2048, int(os.getenv('COREPULSE_MODEL_MAX_TOKENS', '1600' if MODEL_PROVIDER == 'groq' else '900'))))
CHAT_HISTORY_MESSAGES = max(0, min(20, int(os.getenv('COREPULSE_CHAT_HISTORY_MESSAGES', '8'))))
