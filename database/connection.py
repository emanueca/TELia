import sqlite3

DB_PATH = "database/telia.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id   INTEGER NOT NULL,
            message   TEXT    NOT NULL,
            remind_at TEXT    NOT NULL,
            sent      INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()
