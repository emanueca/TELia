CREATE DATABASE IF NOT EXISTS telia_db;
USE telia_db;

-- ============================================================
-- TELia schema oficial (compatível com o código Python atual)
-- Observação: no texto do bot pode aparecer "chatid", "userid",
-- "passwordhash" etc., mas no banco usamos snake_case:
-- chat_id, user_id, password_hash, is_logged_in, created_at...
-- ============================================================

-- Users
CREATE TABLE IF NOT EXISTS users (
	chat_id BIGINT PRIMARY KEY,
	email VARCHAR(255) UNIQUE NOT NULL,
	password_hash VARCHAR(64) NOT NULL,
	is_logged_in BOOLEAN DEFAULT FALSE,
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Reminders
CREATE TABLE IF NOT EXISTS reminders (
	id INT AUTO_INCREMENT PRIMARY KEY,
	user_id BIGINT NOT NULL,
	message TEXT NOT NULL,
	remind_at DATETIME NOT NULL,
	sent BOOLEAN DEFAULT FALSE,
	FOREIGN KEY (user_id) REFERENCES users(chat_id) ON DELETE CASCADE
);

-- Índice para o scheduler
-- Evita erro de índice duplicado ao rodar script múltiplas vezes.
SET @idx_exists := (
    SELECT COUNT(1)
    FROM information_schema.statistics
    WHERE table_schema = DATABASE()
      AND table_name = 'reminders'
      AND index_name = 'idx_pending_sent_remind_at'
);
SET @sql_idx := IF(
    @idx_exists = 0,
    'CREATE INDEX idx_pending_sent_remind_at ON reminders (sent, remind_at)',
    'SELECT 1'
);
PREPARE stmt_idx FROM @sql_idx;
EXECUTE stmt_idx;
DEALLOCATE PREPARE stmt_idx;

-- Conversation history
CREATE TABLE IF NOT EXISTS conversation_history (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    user_id    BIGINT NOT NULL,
    role       ENUM('user', 'assistant') NOT NULL,
    content    TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(chat_id) ON DELETE CASCADE
);

-- User profile
CREATE TABLE IF NOT EXISTS user_profile (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    user_id    BIGINT NOT NULL,
    key_name   VARCHAR(100) NOT NULL,
    value      TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(chat_id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_key (user_id, key_name)
);

-- (Opcional) Limpeza das tabelas antigas em pt-BR, se ainda existirem:
-- SET FOREIGN_KEY_CHECKS=0;
-- DROP TABLE IF EXISTS lembretes;
-- DROP TABLE IF EXISTS usuarios;
-- SET FOREIGN_KEY_CHECKS=1;
