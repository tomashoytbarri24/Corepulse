"""Selección predecible de clave del proveedor, sin exponer el secreto."""
from __future__ import annotations


def choose_key(environment_key: str | None, credential_manager_key: str | None) -> tuple[str, str, bool, bool, bool]:
    """Prefiere la clave gestionada para la prueba Windows; env sólo como fallback.

    Retorna: (clave, origen, conflicto, existe_env, existe_gestor).
    No debe imprimirse nunca el primer valor.
    """
    env = (environment_key or '').strip()
    stored = (credential_manager_key or '').strip()
    return (stored or env,
            'WINDOWS_CREDENTIAL_MANAGER' if stored else ('GROQ_API_KEY_ENV' if env else 'NONE'),
            bool(stored and env and stored != env), bool(env), bool(stored))
