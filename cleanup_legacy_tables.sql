-- 🧹 Script de Limpeza - Remover Tabelas Antigas em Português
-- ============================================================
-- 
-- AVISO: Este script remove as tabelas ANTIGAS (usuarios, lembretes)
-- que estão DUPLICADAS com as novas (users, reminders)
-- 
-- A estrutura nova é compatível com esquema.bd e mais otimizada
-- 
-- ✅ SEMPRE FAZER BACKUP ANTES DE EXECUTAR!

-- 1. Verificar se as tabelas antigas existem
SELECT TABLE_NAME 
FROM INFORMATION_SCHEMA.TABLES 
WHERE TABLE_SCHEMA = 'telia_db' 
AND TABLE_NAME IN ('usuarios', 'lembretes');

-- 2. Remover constraints (se necessário)
-- DELETE CASCADE funcionará se forem chaves estrangeiras

-- 3. Remover tabelas antigas
-- ⚠️ CUIDADO: Você PERDERÁ os dados se não fizer backup!

-- Opção A: Se quiser fazer backup primeiro
CREATE TABLE usuarios_backup AS SELECT * FROM usuarios WHERE FALSE;
CREATE TABLE lembretes_backup AS SELECT * FROM lembretes WHERE FALSE;

-- Opção B: Remover direto (SEM BACKUP)
DROP TABLE IF EXISTS lembretes;
DROP TABLE IF EXISTS usuarios;

-- 4. Verificar tabelas restantes (devem ser só as novas)
SHOW TABLES;

-- ✅ Deve mostrar:
--   - users (nova)
--   - reminders (nova)
--   - conversation_history (nova)
--   - user_profile (nova)
--   - Nada de "usuarios" ou "lembretes"

-- 5. Opcional: Se quiser migrar dados das tabelas antigas
-- (só faça isso se os dados atuais em usuarios/lembretes forem importantes)

-- ⚠️ Exemplo: Migrar usuários de "usuarios" para "users"
/*
INSERT INTO users (chat_id, email, password_hash, is_logged_in, created_at)
SELECT chat_id, email, senha_hash, logado, created_at
FROM usuarios;

-- Depois migrar lembretes
INSERT INTO reminders (user_id, message, remind_at, sent)
SELECT chat_id, mensagem, data_lembrete, enviado
FROM lembretes;
*/

-- 6. Resumo final
SELECT 
    'users' as table_name,
    COUNT(*) as num_records
FROM users
UNION ALL
SELECT 
    'reminders' as table_name,
    COUNT(*) as num_records
FROM reminders
UNION ALL
SELECT 
    'conversation_history' as table_name,
    COUNT(*) as num_records
FROM conversation_history
UNION ALL
SELECT 
    'user_profile' as table_name,
    COUNT(*) as num_records
FROM user_profile;
