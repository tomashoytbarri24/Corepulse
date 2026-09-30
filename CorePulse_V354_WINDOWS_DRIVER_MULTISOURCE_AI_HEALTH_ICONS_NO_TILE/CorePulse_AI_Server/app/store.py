from __future__ import annotations
import hashlib
import secrets
import sqlite3
import threading
from datetime import datetime, timezone
from .config import DB_PATH, DAILY_LIMIT

_lock = threading.Lock()

def _conn():
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.execute('PRAGMA journal_mode=WAL')
    con.execute('CREATE TABLE IF NOT EXISTS installations (installation_id TEXT PRIMARY KEY, token_hash TEXT NOT NULL, created_at TEXT NOT NULL, client_version TEXT, platform TEXT)')
    con.execute('CREATE TABLE IF NOT EXISTS usage (token_hash TEXT NOT NULL, day TEXT NOT NULL, count INTEGER NOT NULL, PRIMARY KEY(token_hash, day))')
    con.commit()
    return con

def _hash(token: str) -> str:
    return hashlib.sha256(token.encode('utf-8')).hexdigest()

def register_installation(installation_id: str, client_version: str, platform: str) -> str:
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc).isoformat()
    with _lock, _conn() as con:
        con.execute(
            'INSERT INTO installations(installation_id, token_hash, created_at, client_version, platform) VALUES(?,?,?,?,?) '
            'ON CONFLICT(installation_id) DO UPDATE SET token_hash=excluded.token_hash, client_version=excluded.client_version, platform=excluded.platform',
            (installation_id, _hash(token), now, client_version, platform),
        )
        con.commit()
    return token

def token_valid(token: str) -> bool:
    if not token:
        return False
    with _conn() as con:
        row = con.execute('SELECT 1 FROM installations WHERE token_hash=?', (_hash(token),)).fetchone()
    return bool(row)

def consume_request(token: str) -> tuple[bool, int]:
    key = _hash(token)
    day = datetime.now(timezone.utc).date().isoformat()
    with _lock, _conn() as con:
        row = con.execute('SELECT count FROM usage WHERE token_hash=? AND day=?', (key, day)).fetchone()
        count = int(row[0]) if row else 0
        if count >= DAILY_LIMIT:
            return False, 0
        count += 1
        con.execute('INSERT INTO usage(token_hash, day, count) VALUES(?,?,?) ON CONFLICT(token_hash, day) DO UPDATE SET count=excluded.count', (key, day, count))
        con.commit()
    return True, max(0, DAILY_LIMIT - count)
