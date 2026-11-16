-- CorePulse · Base de datos local de monitoreo (SQLite).
-- Archivo: %LOCALAPPDATA%\CorePulse\rebuild\monitoring_history.sqlite3
-- La crea la aplicación automáticamente al iniciar el monitoreo
-- (Aplicación/CorePulse_REBUILD_210/core/health/monitoring_insights.py).
-- Este script reproduce el esquema final, incluidas las columnas que la app agrega
-- con ALTER TABLE al actualizar bases de versiones anteriores.

PRAGMA journal_mode = WAL;

-- Una fila por cada arranque de Windows (sesión de Windows).
CREATE TABLE IF NOT EXISTS windows_sessions (
    id          TEXT PRIMARY KEY,   -- identificador de la sesión (derivado del arranque)
    boot_ts     REAL NOT NULL,      -- hora de arranque de Windows (epoch, segundos)
    first_seen  REAL NOT NULL,      -- primera muestra registrada en la sesión
    last_seen   REAL NOT NULL,      -- última muestra registrada en la sesión
    end_ts      REAL,               -- hora de cierre, si se conoce
    end_source  TEXT                -- de dónde se obtuvo el cierre
);

-- Muestras de uso cada 30 segundos. Se conservan 90 días.
CREATE TABLE IF NOT EXISTS samples (
    ts            REAL PRIMARY KEY, -- hora de la muestra (epoch, segundos)
    cpu           REAL,             -- uso de CPU (%)
    gpu           REAL,             -- uso de GPU (%)
    ram           REAL,             -- uso de RAM (%)
    disk          REAL,             -- uso de disco (%)
    session_id    TEXT,             -- sesión de Windows (windows_sessions.id)
    cpu_temp      REAL,             -- temperatura de CPU (°C); NULL si no hay sensor
    gpu_temp      REAL,             -- temperatura de GPU (°C); NULL si no hay sensor
    battery_state TEXT,             -- estado de batería informado por Windows
    disk_state    TEXT              -- estado del disco informado por Windows
);
CREATE INDEX IF NOT EXISTS idx_samples_session_ts ON samples(session_id, ts);

-- Cambios de estado de las alertas (por ejemplo, temperatura alta).
CREATE TABLE IF NOT EXISTS alert_events (
    id      INTEGER PRIMARY KEY,
    ts      REAL NOT NULL,          -- hora del evento
    key     TEXT NOT NULL,          -- identificador de la alerta
    title   TEXT NOT NULL,          -- texto visible
    state   TEXT NOT NULL,          -- estado nuevo (activa, resuelta, etc.)
    value   TEXT NOT NULL,          -- valor medido
    detail  TEXT NOT NULL,          -- explicación
    source  TEXT NOT NULL           -- fuente del dato (sensor, Windows, etc.)
);
CREATE INDEX IF NOT EXISTS idx_alert_events_ts ON alert_events(ts DESC);

-- Nota: samples.session_id se relaciona con windows_sessions.id de forma lógica
-- (la app no declara FOREIGN KEY para no perder muestras antiguas sin sesión).
