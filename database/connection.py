import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE"),
    )

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            chat_id BIGINT PRIMARY KEY,
            email   VARCHAR(255) UNIQUE NOT NULL,
            senha_hash VARCHAR(255) NOT NULL,
            logado  BOOLEAN DEFAULT FALSE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id         INT AUTO_INCREMENT PRIMARY KEY,
            chat_id    BIGINT NOT NULL,
            message    TEXT NOT NULL,
            remind_at  DATETIME NOT NULL,
            sent       BOOLEAN NOT NULL DEFAULT FALSE,
            FOREIGN KEY (chat_id) REFERENCES usuarios(chat_id)
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()
