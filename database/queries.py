from .connection import get_connection

def save_reminder(chat_id: int, message: str, remind_at: str) -> int:
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO reminders (chat_id, message, remind_at) VALUES (?, ?, ?)",
        (chat_id, message, remind_at),
    )
    conn.commit()
    reminder_id = cursor.lastrowid
    conn.close()
    return reminder_id

def get_pending_reminders():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM reminders WHERE sent = 0 AND remind_at <= datetime('now')"
    ).fetchall()
    conn.close()
    return rows

def mark_as_sent(reminder_id: int):
    conn = get_connection()
    conn.execute("UPDATE reminders SET sent = 1 WHERE id = ?", (reminder_id,))
    conn.commit()
    conn.close()
