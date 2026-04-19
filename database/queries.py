from datetime import datetime
from database.connection import get_connection

# ── Usuários ──────────────────────────────────────────────

def get_usuario(chat_id: int) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM usuarios WHERE chat_id = %s", (chat_id,))
    usuario = cursor.fetchone()
    cursor.close()
    conn.close()
    return usuario

def criar_usuario(chat_id: int, email: str, senha_hash: bytes):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO usuarios (chat_id, email, senha_hash, logado)
        VALUES (%s, %s, %s, TRUE)
        ON DUPLICATE KEY UPDATE email = %s, senha_hash = %s, logado = TRUE
        """,
        (chat_id, email, senha_hash, email, senha_hash),
    )
    conn.commit()
    cursor.close()
    conn.close()

def set_logado(chat_id: int, logado: bool):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE usuarios SET logado = %s WHERE chat_id = %s", (logado, chat_id)
    )
    conn.commit()
    cursor.close()
    conn.close()

# ── Lembretes ─────────────────────────────────────────────

def save_reminder(chat_id: int, message: str, remind_at: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO reminders (chat_id, message, remind_at) VALUES (%s, %s, %s)",
        (chat_id, message, remind_at),
    )
    conn.commit()
    cursor.close()
    conn.close()

def get_pending_reminders() -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    cursor.execute(
        "SELECT * FROM reminders WHERE sent = FALSE AND remind_at <= %s", (now,)
    )
    reminders = cursor.fetchall()
    cursor.close()
    conn.close()
    return reminders

def mark_as_sent(reminder_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE reminders SET sent = TRUE WHERE id = %s", (reminder_id,))
    conn.commit()
    cursor.close()
    conn.close()
