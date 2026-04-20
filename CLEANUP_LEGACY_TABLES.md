# 🧹 Limpeza de Tabelas Duplicadas - TELia

## ⚠️ Problema: Tabelas Duplicadas

Seu banco de dados tem **tabelas em português (antigas)** e **tabelas em inglês (novas)** que são duplicatas:

| Antiga (PT-BR) | Nova (EN) | Status |
|---|---|---|
| `usuarios` | `users` | ❌ DUPLICADA |
| `lembretes` | `reminders` | ❌ DUPLICADA |
| `(não existe)` | `conversation_history` | ✅ Nova |
| `(não existe)` | `user_profile` | ✅ Nova |

---

## 📊 Comparação das Tabelas

### Tabela Antiga: `usuarios` vs Nova: `users`
```
USUARIOS (português)          USERS (inglês)
├─ chat_id                   ├─ chat_id (PRIMARY KEY)
├─ email                     ├─ email (UNIQUE)
├─ senha_hash        vs      ├─ password_hash
├─ logado                    ├─ is_logged_in (BOOLEAN)
└─ (sem timestamp)           └─ created_at (TIMESTAMP)
```

### Tabela Antiga: `lembretes` vs Nova: `reminders`
```
LEMBRETES (português)        REMINDERS (inglês)
├─ id                        ├─ id (PRIMARY KEY)
├─ chat_id           vs      ├─ user_id (FOREIGN KEY → users)
├─ mensagem                  ├─ message
├─ data_lembrete             ├─ remind_at
└─ enviado                   └─ sent (BOOLEAN)
```

---

## ✅ Recomendação: Usar Tabelas Novas

### Por quê?
1. **Compatível com esquema.bd** - Schema padrão do projeto
2. **Melhor estrutura** - Relacionamentos com `FOREIGN KEY`
3. **Mais campos** - `created_at`, `updated_at` para auditoria
4. **Semântica clara** - Nomes em inglês (padrão de projetos)
5. **Tabelas de contexto** - `conversation_history` e `user_profile` só existem nas novas
6. **Índices otimizados** - `idx_pending_sent_remind_at` para performance

---

## 🗑️ Como Limpar as Tabelas Antigas

### ⚠️ IMPORTANTE: Fazer Backup Antes!

```bash
# No terminal MySQL:
cd /opt/lampp/htdocs/TELia
mysql -u seu_usuario -p seu_banco < cleanup_legacy_tables.sql
```

---

## 🔄 Passo a Passo

### 1. Verificar se há dados importantes em `usuarios` e `lembretes`

```bash
mysql -u seu_usuario -p seu_banco << 'EOF'
-- Ver quantos usuários tem em cada tabela
SELECT 'usuarios' as tabela, COUNT(*) as total FROM usuarios
UNION ALL
SELECT 'users' as tabela, COUNT(*) as total FROM users;

-- Ver quantos lembretes tem em cada tabela
SELECT 'lembretes' as tabela, COUNT(*) as total FROM lembretes
UNION ALL
SELECT 'reminders' as tabela, COUNT(*) as total FROM reminders;
EOF
```

---

### 2. Opção A: Se quiser PRESERVAR os dados (Migrar)

```sql
-- Copiar dados de usuarios para users
INSERT INTO users (chat_id, email, password_hash, is_logged_in, created_at)
SELECT chat_id, email, senha_hash, logado, NOW()
FROM usuarios
ON DUPLICATE KEY UPDATE
    password_hash = VALUES(password_hash),
    is_logged_in = VALUES(is_logged_in);

-- Copiar dados de lembretes para reminders
INSERT INTO reminders (user_id, message, remind_at, sent)
SELECT chat_id, mensagem, data_lembrete, enviado
FROM lembretes;

-- Depois deletar tabelas antigas
DROP TABLE lembretes;
DROP TABLE usuarios;
```

---

### 3. Opção B: Se os dados são TESTES (Limpar sem preservar)

```sql
-- Deletar direto (SEM BACKUP!)
DROP TABLE IF EXISTS lembretes;
DROP TABLE IF EXISTS usuarios;
```

---

### 4. Verificar o resultado

```sql
-- Devem aparecer SÓ as tabelas novas:
SHOW TABLES;

-- Resultado esperado:
-- - conversation_history
-- - reminders
-- - user_profile
-- - users
```

---

## 🎯 Minha Recomendação

### Se você está em desenvolvimento (dados de teste):
```bash
# Simplesmente delete:
mysql -u seu_usuario -p seu_banco << 'EOF'
DROP TABLE IF EXISTS lembretes;
DROP TABLE IF EXISTS usuarios;
EOF
```

### Se você tem dados reais de usuários em producção:
```bash
# 1. Faça backup
mysqldump -u seu_usuario -p seu_banco usuarios lembretes > backup_legacy_$(date +%Y%m%d_%H%M%S).sql

# 2. Migre os dados
# (use o script SQL na opção A acima)

# 3. Delete as antigas
mysql -u seu_usuario -p seu_banco << 'EOF'
DROP TABLE lembretes;
DROP TABLE usuarios;
EOF
```

---

## 📋 Checklist Final

- [ ] Verifiquei os dados em `usuarios` e `lembretes`
- [ ] Fiz backup se necessário
- [ ] Migrei dados (se aplicável)
- [ ] Deletei tabelas antigas
- [ ] Verifiquei com `SHOW TABLES` que só existem tabelas novas
- [ ] Testei `/cadastrar` no Telegram
- [ ] Testei `/login` no Telegram
- [ ] Testei enviar mensagem (salva em `conversation_history`)

---

## ✨ Após a Limpeza

O banco ficará assim:

```
telia_db
├── users (4 colunas + index)
├── reminders (5 colunas + index)
├── conversation_history (5 colunas)
└── user_profile (5 colunas + index)

✅ Sem duplicatas
✅ Esquema padronizado (inglês)
✅ Compatível com esquema.bd
✅ Pronto para production
```

---

## 🚀 Deploy

Após limpar as tabelas antigas, o fluxo será:

1. ✅ Usuário faz `/cadastrar` → Salva em `users`
2. ✅ Usuário faz `/login` → Valida contra `users`
3. ✅ Usuário envia mensagem → Salva em `conversation_history` + `user_profile`
4. ✅ Lembrete criado → Salva em `reminders`
5. ✅ IA lê contexto → De `conversation_history` + `user_profile`

---

## 📝 Arquivo Gerado

**Script:** `cleanup_legacy_tables.sql`

Execute com:
```bash
mysql -u seu_usuario -p seu_banco < cleanup_legacy_tables.sql
```

---

**Status:** Pronto para execução ✅
