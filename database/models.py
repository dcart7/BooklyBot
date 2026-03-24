# ============================================================
# database/models.py — SQL-схема базы данных
# ============================================================

CREATE_SERVICES_TABLE = """
CREATE TABLE IF NOT EXISTS services (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL UNIQUE,
    duration_min    INTEGER NOT NULL  -- длительность в минутах
);
"""

CREATE_WORKING_DAYS_TABLE = """
CREATE TABLE IF NOT EXISTS working_days (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    date      TEXT    NOT NULL UNIQUE,  -- формат YYYY-MM-DD
    is_closed INTEGER NOT NULL DEFAULT 0
);
"""

CREATE_TIME_SLOTS_TABLE = """
CREATE TABLE IF NOT EXISTS time_slots (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    working_day_id INTEGER NOT NULL REFERENCES working_days(id) ON DELETE CASCADE,
    time_str       TEXT    NOT NULL,   -- формат HH:MM
    is_available   INTEGER NOT NULL DEFAULT 1,
    UNIQUE(working_day_id, time_str)
);
"""

CREATE_BOOKINGS_TABLE = """
CREATE TABLE IF NOT EXISTS bookings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    user_name       TEXT    NOT NULL,
    phone           TEXT    NOT NULL,
    service_id      INTEGER NOT NULL REFERENCES services(id),
    slot_id         INTEGER NOT NULL REFERENCES time_slots(id),
    date            TEXT    NOT NULL,  -- YYYY-MM-DD
    time_str        TEXT    NOT NULL,  -- HH:MM
    duration_min    INTEGER,          -- тривалість на момент запису
    status          TEXT    NOT NULL DEFAULT 'active',  -- active | cancelled
    reminder_job_id TEXT,             -- ID задачи в APScheduler
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""

CREATE_BOT_SETTINGS_TABLE = """
CREATE TABLE IF NOT EXISTS bot_settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""

ALL_TABLES = [
    CREATE_SERVICES_TABLE,
    CREATE_WORKING_DAYS_TABLE,
    CREATE_TIME_SLOTS_TABLE,
    CREATE_BOOKINGS_TABLE,
    CREATE_BOT_SETTINGS_TABLE,
]
