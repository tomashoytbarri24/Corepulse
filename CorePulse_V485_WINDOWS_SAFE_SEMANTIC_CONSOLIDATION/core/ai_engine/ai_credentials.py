"""Credencial de acceso al servicio CorePulse AI.

El usuario no administra claves de proveedores. CorePulse recibe un token opaco
por instalación desde nuestro backend y lo guarda en Windows Credential Manager.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
from typing import Optional

CRED_TYPE_GENERIC = 1
CRED_PERSIST_LOCAL_MACHINE = 2
ERROR_NOT_FOUND = 1168
_TARGETS = {
    'corepulse_server': 'CorePulse/AI/BackendToken',  # legado V458, no usado por Cloud
    'corepulse_cloud_token': 'CorePulse/AI/CloudToken',
    'corepulse_cloud_enrollment': 'CorePulse/AI/CloudEnrollment',
    'corepulse_groq_backend_key': 'CorePulse/AI/BackendGroqKey',
}

class FILETIME(ctypes.Structure):
    _fields_ = [('dwLowDateTime', wintypes.DWORD), ('dwHighDateTime', wintypes.DWORD)]

class CREDENTIALW(ctypes.Structure):
    _fields_ = [
        ('Flags', wintypes.DWORD), ('Type', wintypes.DWORD), ('TargetName', wintypes.LPWSTR),
        ('Comment', wintypes.LPWSTR), ('LastWritten', FILETIME), ('CredentialBlobSize', wintypes.DWORD),
        ('CredentialBlob', ctypes.POINTER(ctypes.c_ubyte)), ('Persist', wintypes.DWORD),
        ('AttributeCount', wintypes.DWORD), ('Attributes', ctypes.c_void_p),
        ('TargetAlias', wintypes.LPWSTR), ('UserName', wintypes.LPWSTR),
    ]

PCREDENTIALW = ctypes.POINTER(CREDENTIALW)

def _target(name: str) -> str:
    key = str(name or '').strip().lower()
    if key not in _TARGETS:
        raise ValueError(f'Credencial no administrada: {name!r}')
    return _TARGETS[key]

def _advapi32():
    if os.name != 'nt':
        return None
    return ctypes.WinDLL('Advapi32.dll', use_last_error=True)

def save_secret(name: str, secret: str) -> bool:
    if os.name != 'nt':
        return False
    secret = str(secret or '').strip()
    if not secret:
        return False
    target = _target(name)
    blob = secret.encode('utf-16-le')
    blob_buf = (ctypes.c_ubyte * len(blob)).from_buffer_copy(blob)
    cred = CREDENTIALW()
    cred.Type = CRED_TYPE_GENERIC
    cred.TargetName = target
    cred.CredentialBlobSize = len(blob)
    cred.CredentialBlob = ctypes.cast(blob_buf, ctypes.POINTER(ctypes.c_ubyte))
    cred.Persist = CRED_PERSIST_LOCAL_MACHINE
    cred.UserName = 'CorePulse'
    api = _advapi32()
    if api is None:
        return False
    api.CredWriteW.argtypes = [ctypes.POINTER(CREDENTIALW), wintypes.DWORD]
    api.CredWriteW.restype = wintypes.BOOL
    return bool(api.CredWriteW(ctypes.byref(cred), 0))

def read_secret(name: str) -> Optional[str]:
    key_name = str(name).lower()
    env_name = 'COREPULSE_AI_TOKEN' if key_name == 'corepulse_server' else ''
    env_value = str(os.getenv(env_name) or '').strip() if env_name else ''
    if env_value:
        return env_value
    if os.name != 'nt':
        return None
    target = _target(name)
    api = _advapi32()
    if api is None:
        return None
    ptr = PCREDENTIALW()
    api.CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(PCREDENTIALW)]
    api.CredReadW.restype = wintypes.BOOL
    api.CredFree.argtypes = [ctypes.c_void_p]
    api.CredFree.restype = None
    if not bool(api.CredReadW(target, CRED_TYPE_GENERIC, 0, ctypes.byref(ptr))):
        return None
    try:
        cred = ptr.contents
        if not cred.CredentialBlob or not cred.CredentialBlobSize:
            return None
        raw = ctypes.string_at(cred.CredentialBlob, cred.CredentialBlobSize)
        return raw.decode('utf-16-le', errors='ignore').strip() or None
    finally:
        api.CredFree(ptr)

def delete_secret(name: str) -> bool:
    if os.name != 'nt':
        return False
    api = _advapi32()
    if api is None:
        return False
    target = _target(name)
    api.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
    api.CredDeleteW.restype = wintypes.BOOL
    ok = bool(api.CredDeleteW(target, CRED_TYPE_GENERIC, 0))
    return ok or ctypes.get_last_error() == ERROR_NOT_FOUND

def secret_present(name: str) -> bool:
    try:
        return bool(read_secret(name))
    except Exception:
        return False

__all__ = ['save_secret', 'read_secret', 'delete_secret', 'secret_present']
