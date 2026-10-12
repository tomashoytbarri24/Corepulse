"""Preferencia de encendido de CorePulse AI (nube); no cambia telemetría."""
from __future__ import annotations

import json
import os
from pathlib import Path
from core.runtime_paths import config_path


def _file() -> Path:
    return Path(config_path('ai_power.json'))


def load_ai_enabled() -> bool:
    """IA habilitada por defecto; la nube requiere consentimiento aparte."""
    try:
        data = json.loads(_file().read_text(encoding='utf-8'))
        return data['enabled'] if isinstance(data.get('enabled'), bool) else True
    except (FileNotFoundError, OSError, ValueError, TypeError, AttributeError):
        return True


def save_ai_enabled(enabled: bool) -> bool:
    """Preferencia persistente fuera del ZIP del proyecto, en AppData."""
    path = _file()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps({'enabled': bool(enabled)}, ensure_ascii=False), encoding='utf-8')
    os.replace(tmp, path)
    return bool(enabled)
