from datetime import datetime, timezone
import time
from database.connection import get_connection

_schema_cache: dict[tuple[str, str], bool] = {}


def _count_from_row(row) -> int:
    """Supports both tuple rows and dictionary rows from mysql connector."""
    if row is None:
        return 0
    if isinstance(row, dict):
        return int(next(iter(row.values()), 0))
    return int(row[0])


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
    exists = _count_from_row(cursor.fetchone()) > 0
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
    exists = _count_from_row(cursor.fetchone()) > 0
    _schema_cache[key] = exists
    return exists

# ── Usuários ──────────────────────────────────────────────

def _new_user_id(cursor) -> int:
    while True:
        candidate = int(time.time_ns())
        cursor.execute("SELECT COUNT(1) FROM users WHERE chat_id = %s", (candidate,))
        if _count_from_row(cursor.fetchone()) == 0:
            return candidate

def verificar_login(email: str, senha_hash: str) -> dict | None:
    """Returns the user row if email+password match, else None."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT chat_id, email, is_logged_in AS logado
        FROM users
        WHERE email = %s AND password_hash = %s
        """,
        (email, senha_hash),
    )
    usuario = cursor.fetchone()
    cursor.close()
    conn.close()
    return usuario

def email_existe(email: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(1) FROM users WHERE email = %s", (email,))
    exists = cursor.fetchone()[0] > 0
    cursor.close()
    conn.close()
    return exists

def get_usuario(chat_id: int) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    if _table_exists(cursor, "users") and _table_exists(cursor, "chat_sessions"):
        cursor.execute(
            """
            SELECT
                u.chat_id,
                u.email,
                u.password_hash AS senha_hash,
                u.is_logged_in AS logado,
                u.created_at
            FROM users u
            INNER JOIN chat_sessions cs ON cs.user_id = u.chat_id
            WHERE cs.chat_id = %s
            """,
            (chat_id,),
        )
        usuario = cursor.fetchone()

        # Compatibilidade com sessão antiga: usa registro legado quando aplicável.
        if not usuario:
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
            usuario = cursor.fetchone()
            if usuario:
                cursor.execute(
                    """
                    INSERT INTO chat_sessions (chat_id, user_id)
                    VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE user_id = VALUES(user_id)
                    """,
                    (chat_id, usuario["chat_id"]),
                )
                conn.commit()
    elif _table_exists(cursor, "users"):
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
        usuario = cursor.fetchone()
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
        usuario = cursor.fetchone()
    else:
        cursor.close()
        conn.close()
        return None

    cursor.close()
    conn.close()
    return usuario

def criar_usuario(chat_id: int, email: str, senha_hash: str):
    conn = get_connection()
    cursor = conn.cursor()
    if _table_exists(cursor, "users") and _table_exists(cursor, "chat_sessions"):
        user_id = _new_user_id(cursor)
        cursor.execute(
            """
            INSERT INTO users (chat_id, email, password_hash, is_logged_in)
            VALUES (%s, %s, %s, TRUE)
            """,
            (user_id, email, senha_hash),
        )
        cursor.execute(
            """
            INSERT INTO chat_sessions (chat_id, user_id)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE user_id = VALUES(user_id)
            """,
            (chat_id, user_id),
        )
    elif _table_exists(cursor, "users"):
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

def set_logado(user_id: int, logado: bool):
    conn = get_connection()
    cursor = conn.cursor()
    if _table_exists(cursor, "users"):
        cursor.execute(
            "UPDATE users SET is_logged_in = %s WHERE chat_id = %s", (logado, user_id)
        )
    else:
        cursor.execute(
            "UPDATE usuarios SET logado = %s WHERE chat_id = %s", (logado, user_id)
        )
    conn.commit()
    cursor.close()
    conn.close()


def set_chat_session(chat_id: int, user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    if _table_exists(cursor, "chat_sessions"):
        cursor.execute(
            """
            INSERT INTO chat_sessions (chat_id, user_id)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE user_id = VALUES(user_id)
            """,
            (chat_id, user_id),
        )
    conn.commit()
    cursor.close()
    conn.close()


def clear_chat_session(chat_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    if _table_exists(cursor, "chat_sessions"):
        cursor.execute("DELETE FROM chat_sessions WHERE chat_id = %s", (chat_id,))
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
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        if _table_exists(cursor, "reminders"):
            if _column_exists(cursor, "reminders", "user_id"):
                cursor.execute(
                    """
                    SELECT
                        id,
                        user_id,
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
        if reminders and _table_exists(cursor, "chat_sessions"):
            user_ids = [row["user_id"] for row in reminders if row.get("user_id") is not None]
            if user_ids:
                placeholders = ",".join(["%s"] * len(user_ids))
                cursor.execute(
                    f"""
                    SELECT cs.user_id, cs.chat_id
                    FROM chat_sessions cs
                    INNER JOIN (
                        SELECT user_id, MAX(updated_at) AS max_updated
                        FROM chat_sessions
                        WHERE user_id IN ({placeholders})
                        GROUP BY user_id
                    ) latest
                        ON latest.user_id = cs.user_id
                       AND latest.max_updated = cs.updated_at
                    """,
                    tuple(user_ids),
                )
                session_rows = cursor.fetchall()
                chat_by_user = {row["user_id"]: row["chat_id"] for row in session_rows}
                reminders = [
                    {
                        "id": row["id"],
                        "chat_id": chat_by_user.get(row["user_id"]),
                        "message": row["message"],
                        "remind_at": row["remind_at"],
                        "sent": row["sent"],
                    }
                    for row in reminders
                    if chat_by_user.get(row["user_id"]) is not None
                ]
        cursor.close()
        return reminders
    finally:
        if conn:
            conn.close()


def save_reminder_task(
    user_id: int,
    kind: str,
    message: str,
    schedule_code: str,
    recurrence_rule: str | None,
    next_run_at: str,
    timezone: str = "America/Sao_Paulo",
):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO reminder_tasks (
            user_id,
            kind,
            message,
            schedule_code,
            recurrence_rule,
            timezone,
            next_run_at,
            active
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE)
        """,
        (user_id, kind, message, schedule_code, recurrence_rule, timezone, next_run_at),
    )
    conn.commit()
    cursor.close()
    conn.close()


def get_due_reminder_tasks(limit: int = 100) -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    if _table_exists(cursor, "chat_sessions"):
        cursor.execute(
            """
            SELECT
                rt.id,
                cs.chat_id,
                rt.kind,
                rt.message,
                rt.schedule_code,
                rt.recurrence_rule,
                rt.timezone,
                rt.next_run_at,
                rt.last_sent_at,
                rt.active
            FROM reminder_tasks rt
            INNER JOIN (
                SELECT user_id, MAX(updated_at) AS max_updated
                FROM chat_sessions
                GROUP BY user_id
            ) latest
                ON latest.user_id = rt.user_id
            INNER JOIN chat_sessions cs
                ON cs.user_id = latest.user_id
               AND cs.updated_at = latest.max_updated
            WHERE rt.active = TRUE
              AND rt.next_run_at <= %s
            ORDER BY rt.next_run_at ASC
            LIMIT %s
            """,
            (now, limit),
        )
    else:
        cursor.execute(
            """
            SELECT
                id,
                user_id AS chat_id,
                kind,
                message,
                schedule_code,
                recurrence_rule,
                timezone,
                next_run_at,
                last_sent_at,
                active
            FROM reminder_tasks
            WHERE active = TRUE
              AND next_run_at <= %s
            ORDER BY next_run_at ASC
            LIMIT %s
            """,
            (now, limit),
        )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def get_active_reminder_tasks(user_id: int) -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT id, user_id, kind, message, schedule_code, recurrence_rule, timezone, next_run_at, created_at
        FROM reminder_tasks
        WHERE user_id = %s AND active = TRUE
        ORDER BY created_at ASC
        """,
        (user_id,),
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def get_reminder_task_by_id(user_id: int, task_id: int) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT id, user_id, kind, message, schedule_code, recurrence_rule, timezone, next_run_at, active
        FROM reminder_tasks
        WHERE id = %s AND user_id = %s
        """,
        (task_id, user_id),
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row


def deactivate_reminder_task(user_id: int, task_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE reminder_tasks
        SET active = FALSE,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s AND user_id = %s
        """,
        (task_id, user_id),
    )
    changed = cursor.rowcount > 0
    conn.commit()
    cursor.close()
    conn.close()
    return changed


def update_reminder_task_schedule(
    user_id: int,
    task_id: int,
    kind: str,
    message: str,
    schedule_code: str,
    recurrence_rule: str | None,
    timezone_name: str,
    next_run_at: str,
) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE reminder_tasks
        SET kind = %s,
            message = %s,
            schedule_code = %s,
            recurrence_rule = %s,
            timezone = %s,
            next_run_at = %s,
            active = TRUE,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s AND user_id = %s
        """,
        (kind, message, schedule_code, recurrence_rule, timezone_name, next_run_at, task_id, user_id),
    )
    changed = cursor.rowcount > 0
    conn.commit()
    cursor.close()
    conn.close()
    return changed


def mark_reminder_task_sent(
    task_id: int,
    next_run_at: str | None = None,
    deactivate: bool = False,
):
    conn = get_connection()
    cursor = conn.cursor()
    if deactivate:
        cursor.execute(
            """
            UPDATE reminder_tasks
            SET active = FALSE,
                last_sent_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (task_id,),
        )
    elif next_run_at:
        cursor.execute(
            """
            UPDATE reminder_tasks
            SET next_run_at = %s,
                last_sent_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (next_run_at, task_id),
        )
    else:
        cursor.execute(
            """
            UPDATE reminder_tasks
            SET last_sent_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (task_id,),
        )
    conn.commit()
    cursor.close()
    conn.close()

# ── Histórico de conversa ──────────────────────────────────

def save_message(user_id: int, role: str, content: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO conversation_history (user_id, role, content) VALUES (%s, %s, %s)",
        (user_id, role, content),
    )
    conn.commit()
    cursor.close()
    conn.close()

def get_history(user_id: int, limit: int = 15) -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT role, content FROM (
            SELECT role, content, created_at
            FROM conversation_history
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        ) sub ORDER BY created_at ASC
        """,
        (user_id, limit),
    )
    history = cursor.fetchall()
    cursor.close()
    conn.close()
    return history

# ── Perfil do usuário ─────────────────────────────────────

def get_profile(user_id: int) -> dict:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT key_name, value FROM user_profile WHERE user_id = %s",
        (user_id,),
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return {row["key_name"]: row["value"] for row in rows}

def upsert_profile(user_id: int, key: str, value: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO user_profile (user_id, key_name, value)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE value = %s, updated_at = CURRENT_TIMESTAMP
        """,
        (user_id, key, value, value),
    )
    conn.commit()
    cursor.close()
    conn.close()

def mark_as_sent(reminder_id: int):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if _table_exists(cursor, "reminders"):
            cursor.execute("UPDATE reminders SET sent = TRUE WHERE id = %s", (reminder_id,))
        else:
            cursor.execute("UPDATE lembretes SET enviado = TRUE WHERE id = %s", (reminder_id,))
        conn.commit()
        cursor.close()
    finally:
        if conn:
            conn.close()
