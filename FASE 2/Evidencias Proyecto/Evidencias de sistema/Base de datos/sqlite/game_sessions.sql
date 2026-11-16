-- CorePulse · Base de datos local de sesiones de juego (SQLite).
-- Archivo: %LOCALAPPDATA%\CorePulse\rebuild\game_sessions.sqlite3
-- La crea la aplicación automáticamente
-- (Aplicación/CorePulse_REBUILD_210/core/health/game_sessions.py).

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- Una fila por partida detectada.
CREATE TABLE IF NOT EXISTS sessions (
    id             INTEGER PRIMARY KEY,
    game_key       TEXT NOT NULL,              -- identificador del juego
    name           TEXT NOT NULL,              -- nombre visible
    source         TEXT NOT NULL,              -- cómo se detectó el juego
    executable     TEXT NOT NULL,              -- ejecutable del juego
    started        REAL NOT NULL,              -- inicio (epoch, segundos)
    ended          REAL,                       -- término; NULL si sigue en curso
    last_seen      REAL NOT NULL,              -- última lectura
    status         TEXT NOT NULL,              -- en curso, terminada, etc.
    active_seconds INTEGER NOT NULL DEFAULT 0, -- tiempo jugado
    fps_sum        REAL NOT NULL DEFAULT 0,    -- suma de FPS (para el promedio)
    fps_count      INTEGER NOT NULL DEFAULT 0, -- cantidad de lecturas de FPS
    fps_min        REAL,
    fps_max        REAL,
    low_1          REAL,                       -- 1 % low
    frame_count    INTEGER NOT NULL DEFAULT 0,
    cpu_peak       REAL,                       -- uso máximo de CPU (%)
    gpu_peak       REAL,                       -- uso máximo de GPU (%)
    plan_name      TEXT NOT NULL DEFAULT 'N/A' -- plan de energía usado
);

-- Lecturas durante la partida.
CREATE TABLE IF NOT EXISTS samples (
    id         INTEGER PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    ts         REAL NOT NULL,
    fps        REAL,
    cpu        REAL,
    gpu        REAL,
    ram        REAL,
    cpu_temp   REAL,
    gpu_temp   REAL
);
CREATE INDEX IF NOT EXISTS samples_session ON samples(session_id, ts);

-- Incidencias de la partida (caídas de FPS, temperatura alta, etc.).
CREATE TABLE IF NOT EXISTS events (
    id         INTEGER PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    ts         REAL NOT NULL,
    kind       TEXT NOT NULL,
    title      TEXT NOT NULL,
    detail     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS events_session ON events(session_id, ts);

-- Preferencias por juego.
CREATE TABLE IF NOT EXISTS profiles (
    game_key     TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    plan_guid    TEXT NOT NULL DEFAULT '',        -- plan de energía a aplicar
    corner       TEXT NOT NULL DEFAULT 'inherit', -- esquina del overlay
    temperatures TEXT NOT NULL DEFAULT 'inherit'  -- mostrar temperaturas
);
