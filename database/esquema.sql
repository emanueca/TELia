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
    password_hash VARCHAR(255) NOT NULL,
	is_logged_in BOOLEAN DEFAULT FALSE,
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sessão ativa por chat do Telegram
CREATE TABLE IF NOT EXISTS chat_sessions (
    chat_id BIGINT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(chat_id) ON DELETE CASCADE,
    INDEX idx_chat_sessions_user (user_id)
);

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

-- Tarefas de lembrete usadas pelo scheduler e pela IA
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
);

-- Relatos enviados pelo comando /reportar
CREATE TABLE IF NOT EXISTS reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    issue TEXT NOT NULL,
    ai_reply TEXT NOT NULL,
    reporter_name VARCHAR(255) NULL,
    anonymous BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(chat_id) ON DELETE CASCADE,
    INDEX idx_reports_user_id (user_id)
);

-- Credenciais do RU (CPF e senha criptografados por usuario)
CREATE TABLE IF NOT EXISTS ru_credentials (
    user_id BIGINT PRIMARY KEY,
    cpf_enc TEXT NOT NULL,
    senha_enc TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(chat_id) ON DELETE CASCADE
);

-- ============================================================
-- SISTEMA DE TRANSFERÊNCIA DE ALMOÇO
-- ============================================================

-- Fila/Listão de pessoas oferecendo ou buscando almoço
CREATE TABLE IF NOT EXISTS lunch_queue (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    mode ENUM('offering', 'seeking') NOT NULL,
    cpf VARCHAR(20) NOT NULL,
    full_name VARCHAR(255),
    time_window ENUM('24h', '13h', '5h', '2h') NOT NULL DEFAULT '24h',
    entered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (user_id) REFERENCES users(chat_id) ON DELETE CASCADE,
    INDEX idx_lunch_queue_mode_active (mode, active),
    INDEX idx_lunch_queue_user (user_id)
);

-- Registro de transferências de almoço
CREATE TABLE IF NOT EXISTS lunch_transfers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    donor_id BIGINT NOT NULL,
    recipient_id BIGINT NOT NULL,
    donor_cpf VARCHAR(20) NOT NULL,
    recipient_cpf VARCHAR(20) NOT NULL,
    transfer_date DATE NOT NULL,
    status ENUM('pending', 'accepted', 'rejected', 'completed') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    completed_at DATETIME NULL,
    FOREIGN KEY (donor_id) REFERENCES users(chat_id) ON DELETE CASCADE,
    FOREIGN KEY (recipient_id) REFERENCES users(chat_id) ON DELETE CASCADE,
    INDEX idx_lunch_transfers_status (status),
    INDEX idx_lunch_transfers_date (transfer_date),
    INDEX idx_lunch_transfers_donor (donor_id),
    INDEX idx_lunch_transfers_recipient (recipient_id)
);

-- Notificações de transferência enviadas no chat
CREATE TABLE IF NOT EXISTS lunch_notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    transfer_id INT NOT NULL,
    message_text TEXT NOT NULL,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    read_at DATETIME NULL,
    FOREIGN KEY (user_id) REFERENCES users(chat_id) ON DELETE CASCADE,
    FOREIGN KEY (transfer_id) REFERENCES lunch_transfers(id) ON DELETE CASCADE,
    INDEX idx_lunch_notifications_user (user_id)
);

-- Limpeza opcional de tabelas antigas, se ainda existirem no banco:
-- SET FOREIGN_KEY_CHECKS=0;
-- DROP TABLE IF EXISTS reminders;
-- DROP TABLE IF EXISTS lembretes;
-- DROP TABLE IF EXISTS usuarios;
-- SET FOREIGN_KEY_CHECKS=1;

