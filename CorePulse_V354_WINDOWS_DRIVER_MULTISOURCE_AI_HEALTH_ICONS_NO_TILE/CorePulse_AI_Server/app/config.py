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
DATA_DIR = Path(os.getenv('COREPULSE_AI_DATA_DIR') or (ROOT / 'data')).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / 'corepulse_ai.sqlite3'
HOST = os.getenv('COREPULSE_AI_HOST', '127.0.0.1')
PORT = int(os.getenv('COREPULSE_AI_PORT', '8765'))
DAILY_LIMIT = max(1, int(os.getenv('COREPULSE_AI_DAILY_LIMIT', '200')))
DEDUP_SECONDS = max(0.0, float(os.getenv('COREPULSE_AI_DEDUP_SECONDS', '8')))

# Host de inferencia separado. En desarrollo usa llama.cpp en 127.0.0.1:8766.
# En producción basta con cambiar estas variables hacia el host privado de CorePulse AI.
MODEL_BASE_URL = os.getenv('COREPULSE_MODEL_BASE_URL', 'http://127.0.0.1:8766/v1').rstrip('/')
MODEL_NAME = os.getenv('COREPULSE_MODEL_NAME', 'Qwen/Qwen3-4B-GGUF:Q4_K_M').strip()
MODEL_API_KEY = os.getenv('COREPULSE_MODEL_API_KEY', '').strip()
MODEL_TIMEOUT = max(5, int(os.getenv('COREPULSE_MODEL_TIMEOUT', '60')))
MODEL_STATUS_TIMEOUT = max(1, min(10, int(os.getenv('COREPULSE_MODEL_STATUS_TIMEOUT', '3'))))
MODEL_TEMPERATURE = max(0.0, min(1.0, float(os.getenv('COREPULSE_MODEL_TEMPERATURE', '0.2'))))
MODEL_MAX_TOKENS = max(128, min(2048, int(os.getenv('COREPULSE_MODEL_MAX_TOKENS', '650'))))
CHAT_HISTORY_MESSAGES = max(0, min(20, int(os.getenv('COREPULSE_CHAT_HISTORY_MESSAGES', '8'))))
