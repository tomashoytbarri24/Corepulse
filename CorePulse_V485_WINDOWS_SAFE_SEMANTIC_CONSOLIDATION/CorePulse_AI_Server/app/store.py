"""SQLite: credenciales por instalación y códigos de vinculación de un solo uso.

El registro y consumo de cada código se hacen en una transacción IMMEDIATE:
ningún código puede utilizarse dos veces, incluso con solicitudes simultáneas.
Nunca se persisten los tokens ni los códigos originales.
"""
from __future__ import annotations
import hashlib
import secrets
import sqlite3
import threading
import time
from datetime import datetime, timezone
from .config import DB_PATH, DAILY_LIMIT

_lock = threading.Lock()


def _conn():
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.execute('PRAGMA journal_mode=WAL')
    con.execute('CREATE TABLE IF NOT EXISTS installations (installation_id TEXT PRIMARY KEY, token_hash TEXT NOT NULL, created_at TEXT NOT NULL, client_version TEXT, platform TEXT)')
    con.execute('CREATE TABLE IF NOT EXISTS usage (token_hash TEXT NOT NULL, day TEXT NOT NULL, count INTEGER NOT NULL, PRIMARY KEY(token_hash, day))')
    con.execute('CREATE TABLE IF NOT EXISTS pairing_codes (code_hash TEXT PRIMARY KEY, created_at INTEGER NOT NULL, expires_at INTEGER NOT NULL, used_at INTEGER, installation_id TEXT)')
    con.commit()
    return con


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def issue_pairing_code(minutes: int = 30) -> tuple[str, int]:
    """CLI administrativo: crear un código aleatorio válido entre 1 y 1440 minutos."""
    minutes = max(1, min(1440, int(minutes)))
    code = 'cp-' + secrets.token_urlsafe(30)
    now = int(time.time())
    expires = now + minutes * 60
    with _lock, _conn() as con:
        con.execute('DELETE FROM pairing_codes WHERE expires_at < ? OR used_at IS NOT NULL', (now,))
        con.execute('INSERT INTO pairing_codes(code_hash,created_at,expires_at) VALUES(?,?,?)', (_hash(code), now, expires))
        con.commit()
    return code, expires


def register_installation(installation_id: str, client_version: str, platform: str, pairing_code: str) -> str | None:
    """Canje único. Devuelve token individual o None sin modificar instalaciones."""
    if not pairing_code or len(pairing_code) > 160:
        return None
    now = int(time.time())
    token = secrets.token_urlsafe(36)
    now_iso = datetime.now(timezone.utc).isoformat()
    with _lock, _conn() as con:
        con.execute('BEGIN IMMEDIATE')
        row = con.execute('SELECT expires_at,used_at FROM pairing_codes WHERE code_hash=?', (_hash(pairing_code),)).fetchone()
        if not row or row[1] is not None or row[0] <= now:
            con.rollback()
            return None
        # Evita conservar gasto asociado a un token anterior tras reenrolar.
        old = con.execute('SELECT token_hash FROM installations WHERE installation_id=?', (installation_id,)).fetchone()
        if old:
            con.execute('DELETE FROM usage WHERE token_hash=?', (old[0],))
        con.execute(
            'INSERT INTO installations(installation_id, token_hash, created_at, client_version, platform) VALUES(?,?,?,?,?) '
            'ON CONFLICT(installation_id) DO UPDATE SET token_hash=excluded.token_hash, created_at=excluded.created_at, client_version=excluded.client_version, platform=excluded.platform',
            (installation_id, _hash(token), now_iso, client_version, platform),
        )
        con.execute('UPDATE pairing_codes SET used_at=?,installation_id=? WHERE code_hash=? AND used_at IS NULL',
                    (now, installation_id, _hash(pairing_code)))
        con.commit()
    return token


def revoke_installation(installation_id: str) -> bool:
    with _lock, _conn() as con:
        con.execute('BEGIN IMMEDIATE')
        item = con.execute('SELECT token_hash FROM installations WHERE installation_id=?', (installation_id,)).fetchone()
        if not item:
            con.rollback()
            return False
        con.execute('DELETE FROM installations WHERE installation_id=?', (installation_id,))
        con.execute('DELETE FROM usage WHERE token_hash=?', (item[0],))
        con.commit()
    return True


def list_installations() -> list[tuple[str, str, str]]:
    with _conn() as con:
        return con.execute('SELECT installation_id,created_at,client_version FROM installations ORDER BY created_at DESC').fetchall()


def token_valid(token: str) -> bool:
    if not token or len(token) > 160:
        return False
    with _conn() as con:
        row = con.execute('SELECT 1 FROM installations WHERE token_hash=?', (_hash(token),)).fetchone()
    return bool(row)


def consume_request(token: str) -> tuple[bool, int]:
    """Descuenta cuota atómicamente también entre workers independientes."""
    key = _hash(token)
    day = datetime.now(timezone.utc).date().isoformat()
    with _lock, _conn() as con:
        con.execute('BEGIN IMMEDIATE')
        count = con.execute('SELECT count FROM usage WHERE token_hash=? AND day=?', (key, day)).fetchone()
        used = int(count[0]) if count else 0
        if used >= DAILY_LIMIT:
            con.rollback()
            return False, 0
        used += 1
        con.execute('INSERT INTO usage(token_hash, day, count) VALUES(?,?,?) ON CONFLICT(token_hash, day) DO UPDATE SET count=excluded.count', (key, day, used))
        con.commit()
    return True, max(0, DAILY_LIMIT - used)
