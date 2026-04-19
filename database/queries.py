from datetime import datetime
from database.connection import get_connection

def save_reminder(chat_id: int, message: str, remind_at: str):
    conn = get_connection()
    conn.execute(
        "INSERT INTO reminders (chat_id, message, remind_at) VALUES (?, ?, ?)",
        (chat_id, message, remind_at)
    )
    conn.commit()
    conn.close()

def get_pending_reminders():
    conn = get_connection()
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    cursor = conn.execute(
        "SELECT * FROM reminders WHERE sent = 0 AND remind_at <= ?",
        (now,)
    )
    reminders = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return reminders

def mark_as_sent(reminder_id: int):
    conn = get_connection()
    conn.execute("UPDATE reminders SET sent = 1 WHERE id = ?", (reminder_id,))
    conn.commit()
    conn.close()
