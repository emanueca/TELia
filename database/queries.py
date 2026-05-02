from datetime import datetime, timezone
import time
import logging
from database.connection import get_connection

logger = logging.getLogger(__name__)
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


def save_report(user_id: int, issue: str, ai_reply: str, reporter_name: str | None, anonymous: bool):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO reports (user_id, issue, ai_reply, reporter_name, anonymous)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (user_id, issue, ai_reply, reporter_name, anonymous),
    )
    conn.commit()
    cursor.close()
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
    # Guarda contra duplicata: se já existe um lembrete ativo com o mesmo
    # schedule_code para o mesmo usuário, não insere novamente. Isso evita
    # duplicatas causadas por reenvio de updates do Telegram ou falha parcial
    # no fluxo de resposta.
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
        SELECT %s, %s, %s, %s, %s, %s, %s, TRUE
        FROM DUAL
        WHERE NOT EXISTS (
            SELECT 1 FROM reminder_tasks
            WHERE user_id = %s AND schedule_code = %s AND active = TRUE
        )
        """,
        (user_id, kind, message, schedule_code, recurrence_rule, timezone, next_run_at,
         user_id, schedule_code),
    )
    conn.commit()
    cursor.close()
    conn.close()


def get_due_reminder_tasks(limit: int = 100) -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    if _table_exists(cursor, "chat_sessions"):
        # O MIN(cs.chat_id) garante exatamente uma linha por usuário mesmo que
        # dois registros de chat_sessions tenham o mesmo updated_at (empate),
        # evitando entrega duplicada do lembrete.
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
                SELECT cs1.user_id, MIN(cs1.chat_id) AS chat_id
                FROM chat_sessions cs1
                INNER JOIN (
                    SELECT user_id, MAX(updated_at) AS max_updated
                    FROM chat_sessions
                    GROUP BY user_id
                ) latest
                    ON cs1.user_id = latest.user_id
                   AND cs1.updated_at = latest.max_updated
                GROUP BY cs1.user_id
            ) cs ON cs.user_id = rt.user_id
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


def get_overdue_reminder_tasks(user_id: int) -> list[dict]:
    """Retorna lembretes já enviados (active=FALSE, last_sent_at preenchido)
    que dispararam após o último login do usuário — serve para notificar
    lembretes perdidos ao fazer login."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT id, message, next_run_at, last_sent_at
        FROM reminder_tasks
        WHERE user_id = %s
          AND active = FALSE
          AND last_sent_at IS NOT NULL
          AND last_sent_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
        ORDER BY last_sent_at DESC
        LIMIT 10
        """,
        (user_id,),
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

# ── Credenciais do RU ─────────────────────────────────────

def save_ru_credentials(user_id: int, cpf_enc: str, senha_enc: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO ru_credentials (user_id, cpf_enc, senha_enc)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE cpf_enc = VALUES(cpf_enc), senha_enc = VALUES(senha_enc),
            updated_at = CURRENT_TIMESTAMP
        """,
        (user_id, cpf_enc, senha_enc),
    )
    conn.commit()
    cursor.close()
    conn.close()


def get_ru_credentials(user_id: int) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT cpf_enc, senha_enc FROM ru_credentials WHERE user_id = %s",
        (user_id,),
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row


def has_ru_credentials(user_id: int) -> bool:
    return get_ru_credentials(user_id) is not None


def save_ru_credentials(user_id: int, cpf_enc: str, senha_enc: str) -> bool:
    """Salva ou atualiza credenciais do RU do usuário."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Tenta fazer update; se não afetar nada, faz insert
        cursor.execute(
            """
            UPDATE ru_credentials
            SET cpf_enc = %s, senha_enc = %s, updated_at = NOW()
            WHERE user_id = %s
            """,
            (cpf_enc, senha_enc, user_id)
        )
        
        if cursor.rowcount == 0:
            # Não tinha registro, faz insert
            cursor.execute(
                """
                INSERT INTO ru_credentials (user_id, cpf_enc, senha_enc)
                VALUES (%s, %s, %s)
                """,
                (user_id, cpf_enc, senha_enc)
            )
        
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar credenciais do RU: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


# ── Sistema de Transferência de Almoço ──────────────────────────────────────

def add_to_lunch_queue(user_id: int, mode: str, cpf: str, full_name: str | None, time_window: str) -> bool:
    """
    Adiciona usuário à fila de almoço (oferecendo ou buscando).
    mode: 'offering' ou 'seeking'
    time_window: '24h', '13h', '5h', '2h'
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Remove do listão se já existir para evitar duplicatas
        cursor.execute("DELETE FROM lunch_queue WHERE user_id = %s", (user_id,))
        
        # Calcula tempo de expiração
        from datetime import datetime, timedelta
        time_map = {'24h': 24, '13h': 13, '5h': 5, '2h': 2}
        hours = time_map.get(time_window, 24)
        expires_at = datetime.now() + timedelta(hours=hours)
        
        cursor.execute(
            """
            INSERT INTO lunch_queue (user_id, mode, cpf, full_name, time_window, expires_at, active)
            VALUES (%s, %s, %s, %s, %s, %s, TRUE)
            """,
            (user_id, mode, cpf, full_name, time_window, expires_at)
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Erro ao adicionar ao listão: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


def remove_from_lunch_queue(user_id: int) -> bool:
    """Remove usuário da fila de almoço."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("UPDATE lunch_queue SET active = FALSE WHERE user_id = %s", (user_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Erro ao remover do listão: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


def get_lunch_queue_entries(mode: str | None = None, active_only: bool = True) -> list[dict]:
    """
    Retorna entradas da fila de almoço.
    mode: 'offering', 'seeking' ou None para ambas.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        if mode:
            cursor.execute(
                """
                SELECT id, user_id, mode, cpf, full_name, time_window, entered_at, expires_at
                FROM lunch_queue
                WHERE mode = %s AND active = %s
                ORDER BY entered_at ASC
                """,
                (mode, active_only)
            )
        else:
            cursor.execute(
                """
                SELECT id, user_id, mode, cpf, full_name, time_window, entered_at, expires_at
                FROM lunch_queue
                WHERE active = %s
                ORDER BY entered_at ASC
                """,
                (active_only,)
            )
        return cursor.fetchall() or []
    except Exception as e:
        logger.error(f"Erro ao buscar fila de almoço: {e}")
        return []
    finally:
        cursor.close()
        conn.close()


def create_lunch_transfer(donor_id: int, recipient_id: int, donor_cpf: str, recipient_cpf: str, transfer_date) -> int | None:
    """
    Cria registro de transferência de almoço.
    Retorna o ID da transferência ou None em caso de erro.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """
            INSERT INTO lunch_transfers (donor_id, recipient_id, donor_cpf, recipient_cpf, transfer_date, status)
            VALUES (%s, %s, %s, %s, %s, 'pending')
            """,
            (donor_id, recipient_id, donor_cpf, recipient_cpf, transfer_date)
        )
        conn.commit()
        transfer_id = cursor.lastrowid
        return transfer_id
    except Exception as e:
        logger.error(f"Erro ao criar transferência: {e}")
        return None
    finally:
        cursor.close()
        conn.close()


def update_transfer_status(transfer_id: int, status: str) -> bool:
    """
    Atualiza status de uma transferência.
    status: 'pending', 'accepted', 'rejected', 'completed'
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        completed_at = None
        if status in ('accepted', 'completed'):
            from datetime import datetime
            completed_at = datetime.now()
        
        cursor.execute(
            """
            UPDATE lunch_transfers
            SET status = %s, updated_at = NOW(), completed_at = %s
            WHERE id = %s
            """,
            (status, completed_at, transfer_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Erro ao atualizar status: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


def get_pending_transfers_for_user(user_id: int, direction: str = 'received') -> list[dict]:
    """
    Busca transferências pendentes.
    direction: 'received' (como receptor) ou 'sent' (como doador)
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        if direction == 'received':
            cursor.execute(
                """
                SELECT id, donor_id, recipient_id, donor_cpf, recipient_cpf, 
                       transfer_date, status, created_at
                FROM lunch_transfers
                WHERE recipient_id = %s AND status = 'pending'
                ORDER BY created_at DESC
                """,
                (user_id,)
            )
        else:  # sent
            cursor.execute(
                """
                SELECT id, donor_id, recipient_id, donor_cpf, recipient_cpf, 
                       transfer_date, status, created_at
                FROM lunch_transfers
                WHERE donor_id = %s AND status = 'pending'
                ORDER BY created_at DESC
                """,
                (user_id,)
            )
        return cursor.fetchall() or []
    except Exception as e:
        logger.error(f"Erro ao buscar transferências pendentes: {e}")
        return []
    finally:
        cursor.close()
        conn.close()


def user_in_lunch_queue(user_id: int) -> dict | None:
    """Retorna entrada do usuário na fila se estiver lá, None caso contrário."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute(
            """
            SELECT id, mode, cpf, full_name, time_window, entered_at, expires_at
            FROM lunch_queue
            WHERE user_id = %s AND active = TRUE
            """,
            (user_id,)
        )
        return cursor.fetchone()
    except Exception as e:
        logger.error(f"Erro ao verificar se está no listão: {e}")
        return None
    finally:
        cursor.close()
        conn.close()


def find_matching_lunch_partner(seeker_id: int) -> dict | None:
    """
    Procura um parceiro na fila para fazer match.
    Se seeker_id está buscando ('seeking'), procura alguém oferecendo ('offering').
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Primeiro verifica o modo do seeker
        cursor.execute(
            "SELECT mode FROM lunch_queue WHERE user_id = %s AND active = TRUE",
            (seeker_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        
        seeker_mode = row['mode']
        target_mode = 'offering' if seeker_mode == 'seeking' else 'seeking'
        
        # Procura o primeiro parceiro disponível com modo oposto
        cursor.execute(
            """
            SELECT id, user_id, mode, cpf, full_name, time_window
            FROM lunch_queue
            WHERE mode = %s AND active = TRUE AND user_id != %s
            ORDER BY entered_at ASC
            LIMIT 1
            """,
            (target_mode, seeker_id)
        )
        return cursor.fetchone()
    except Exception as e:
        logger.error(f"Erro ao procurar parceiro: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

