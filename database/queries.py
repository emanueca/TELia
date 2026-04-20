from datetime import datetime
from database.connection import get_connection

_schema_cache: dict[tuple[str, str], bool] = {}


def _table_exists(cursor, table_name: str) -> bool:
    key = ("table", table_name)
    if key in _schema_cache:
        return _schema_cache[key]

    cursor.execute(
        """
        SELECT COUNT(1)
        FROM information_schema.tables
        WHERE table_schema = DATABASE() AND table_name = %s
        """,
        (table_name,),
    )
    exists = cursor.fetchone()[0] > 0
    _schema_cache[key] = exists
    return exists


def _column_exists(cursor, table_name: str, column_name: str) -> bool:
    key = (f"column:{table_name}", column_name)
    if key in _schema_cache:
        return _schema_cache[key]

    cursor.execute(
        """
        SELECT COUNT(1)
        FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = %s
          AND column_name = %s
        """,
        (table_name, column_name),
    )
    exists = cursor.fetchone()[0] > 0
    _schema_cache[key] = exists
    return exists

# ── Usuários ──────────────────────────────────────────────

def get_usuario(chat_id: int) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    if _table_exists(cursor, "users"):
        cursor.execute(
            """
            SELECT
                chat_id,
                email,
                password_hash AS senha_hash,
                is_logged_in AS logado,
                created_at
            FROM users
            WHERE chat_id = %s
            """,
            (chat_id,),
        )
    elif _table_exists(cursor, "usuarios"):
        cursor.execute(
            """
            SELECT
                chat_id,
                email,
                senha_hash,
                logado,
                criado_em AS created_at
            FROM usuarios
            WHERE chat_id = %s
            """,
            (chat_id,),
        )
    else:
        cursor.close()
        conn.close()
        return None

    usuario = cursor.fetchone()
    cursor.close()
    conn.close()
    return usuario

def criar_usuario(chat_id: int, email: str, senha_hash: str):
    conn = get_connection()
    cursor = conn.cursor()
    if _table_exists(cursor, "users"):
        cursor.execute(
            """
            INSERT INTO users (chat_id, email, password_hash, is_logged_in)
            VALUES (%s, %s, %s, TRUE)
            ON DUPLICATE KEY UPDATE email = %s, password_hash = %s, is_logged_in = TRUE
            """,
            (chat_id, email, senha_hash, email, senha_hash),
        )
    else:
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
    if _table_exists(cursor, "users"):
        cursor.execute(
            "UPDATE users SET is_logged_in = %s WHERE chat_id = %s", (logado, chat_id)
        )
    else:
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
    if _table_exists(cursor, "reminders"):
        if _column_exists(cursor, "reminders", "user_id"):
            cursor.execute(
                "INSERT INTO reminders (user_id, message, remind_at) VALUES (%s, %s, %s)",
                (chat_id, message, remind_at),
            )
        else:
            cursor.execute(
                "INSERT INTO reminders (chat_id, message, remind_at) VALUES (%s, %s, %s)",
                (chat_id, message, remind_at),
            )
    else:
        cursor.execute(
            "INSERT INTO lembretes (user_id, mensagem, data_lembrete, enviado) VALUES (%s, %s, %s, FALSE)",
            (chat_id, message, remind_at),
        )
    conn.commit()
    cursor.close()
    conn.close()

def get_pending_reminders() -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    if _table_exists(cursor, "reminders"):
        if _column_exists(cursor, "reminders", "user_id"):
            cursor.execute(
                """
                SELECT
                    id,
                    user_id AS chat_id,
                    message,
                    remind_at,
                    sent
                FROM reminders
                WHERE sent = FALSE AND remind_at <= %s
                """,
                (now,),
            )
        else:
            cursor.execute(
                """
                SELECT
                    id,
                    chat_id,
                    message,
                    remind_at,
                    sent
                FROM reminders
                WHERE sent = FALSE AND remind_at <= %s
                """,
                (now,),
            )
    else:
        cursor.execute(
            """
            SELECT
                id,
                user_id AS chat_id,
                mensagem AS message,
                data_lembrete AS remind_at,
                enviado AS sent
            FROM lembretes
            WHERE enviado = FALSE AND data_lembrete <= %s
            """,
            (now,),
        )
    reminders = cursor.fetchall()
    cursor.close()
    conn.close()
    return reminders

def mark_as_sent(reminder_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    if _table_exists(cursor, "reminders"):
        cursor.execute("UPDATE reminders SET sent = TRUE WHERE id = %s", (reminder_id,))
    else:
        cursor.execute("UPDATE lembretes SET enviado = TRUE WHERE id = %s", (reminder_id,))
    conn.commit()
    cursor.close()
    conn.close()
