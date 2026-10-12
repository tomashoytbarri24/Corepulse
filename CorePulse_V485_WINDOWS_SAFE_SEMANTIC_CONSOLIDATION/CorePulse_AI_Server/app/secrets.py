"""Credenciales sólo del proceso backend, almacenadas en Windows Credential Manager."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from core.ai_credentials import read_secret, save_secret, delete_secret

GROQ_KEY_NAME = 'corepulse_groq_backend_key'


def read_groq_key() -> str:
    return str(read_secret(GROQ_KEY_NAME) or '').strip()


def save_groq_key(value: str) -> bool:
    return save_secret(GROQ_KEY_NAME, value)


def delete_groq_key() -> bool:
    return delete_secret(GROQ_KEY_NAME)
