"""Huella no secreta que ata autorización del cliente al destino alternativo real."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path


def provider_identity(path: Path | None = None) -> str:
    if path is None:
        appdata = os.getenv('LOCALAPPDATA', '')
        if not appdata:
            return ''
        path = Path(appdata) / 'CorePulse' / 'ai_compatible_provider.json'
    try:
        config = json.loads(path.read_text(encoding='utf-8'))
        endpoint = str(config['base_url']).strip()
        model = str(config['model']).strip()
        if not endpoint.startswith('https://') or not endpoint.endswith('/v1') or not model:
            return ''
        return hashlib.sha256((endpoint + '\n' + model).encode('utf-8')).hexdigest()
    except (OSError, ValueError, KeyError, TypeError):
        return ''
