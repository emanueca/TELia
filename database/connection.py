import mysql.connector
from mysql.connector import pooling
import os
from dotenv import load_dotenv

load_dotenv()

_db_pool = None


def _get_pool():
    global _db_pool
    if _db_pool is None:
        _db_pool = pooling.MySQLConnectionPool(
            pool_name="telia_pool",
            pool_size=20,
            pool_reset_session=True,
            host=os.getenv("MYSQL_HOST"),
            user=os.getenv("MYSQL_USER"),
            password=os.getenv("MYSQL_PASSWORD"),
            database=os.getenv("MYSQL_DATABASE"),
        )
    return _db_pool

def get_connection():
    return _get_pool().get_connection()


def _ensure_pending_index(cursor):
    cursor.execute(
        """
        SELECT COUNT(1)
        FROM information_schema.statistics
        WHERE table_schema = DATABASE()
          AND table_name = 'reminder_tasks'
          AND index_name = 'idx_reminder_tasks_due'
        """
    )
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "CREATE INDEX idx_reminder_tasks_due ON reminder_tasks (active, next_run_at)"
        )

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id BIGINT PRIMARY KEY,
            email   VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            is_logged_in BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            chat_id BIGINT PRIMARY KEY,
            user_id BIGINT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(chat_id) ON DELETE CASCADE,
            INDEX idx_chat_sessions_user (user_id)
        )
    """)

    _ensure_pending_index(cursor)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversation_history (
            id         INT AUTO_INCREMENT PRIMARY KEY,
            user_id    BIGINT NOT NULL,
            role       ENUM('user', 'assistant') NOT NULL,
            content    TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(chat_id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reminder_tasks (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id BIGINT NOT NULL,
            kind ENUM('LU','LR') NOT NULL,
            message TEXT NOT NULL,
            schedule_code VARCHAR(120) NOT NULL,
            recurrence_rule VARCHAR(120) NULL,
            timezone VARCHAR(64) NOT NULL DEFAULT 'America/Sao_Paulo',
            next_run_at DATETIME NOT NULL,
            last_sent_at DATETIME NULL,
            active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(chat_id) ON DELETE CASCADE,
            INDEX idx_reminder_tasks_due (active, next_run_at)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_profile (
            id         INT AUTO_INCREMENT PRIMARY KEY,
            user_id    BIGINT NOT NULL,
            key_name   VARCHAR(100) NOT NULL,
            value      TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(chat_id) ON DELETE CASCADE,
            UNIQUE KEY unique_user_key (user_id, key_name)
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()
