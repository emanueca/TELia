# 📋 Guia de Deployment - TELia

## 🔄 Sincronizar com Servidor

### Opção 1: Usando `commitauto` (Recomendado)
```bash
cd /opt/lampp/htdocs/TELia
commitauto
```

Isso vai:
1. ✅ Fazer `git pull` (atualizar)
2. ✅ Fazer `git push` (enviar mudanças)
3. ✅ Instalar dependências (`pip install -r requirements.txt`)
4. ✅ Reiniciar o bot (`pkill -f 'python main.py'`)

### Opção 2: Manualmente
```bash
cd /opt/lampp/htdocs/TELia

# Atualizar repository
git pull origin main

# Enviar mudanças
git push origin main

# Instalar dependências (se necessário)
pip install -r requirements.txt

# Reiniciar bot
pkill -f "python main.py"

# Se usar start_server.py:
python3 start_server.py
```

---

## 🧪 Testes Locais (Antes de Enviar)

### 1. Validar Sintaxe Python
```bash
cd /opt/lampp/htdocs/TELia
python3 -m py_compile main.py bot/commands.py bot/messages.py database/queries.py database/connection.py ai/gemini.py scheduler/jobs.py
```
✅ Se não houver output, está tudo certo!

---

### 2. Verificar Dependências
```bash
pip list | grep -E "python-telegram-bot|apscheduler|google-generativeai|python-dotenv|mysql-connector"
```

✅ Deve mostrar todas as 5 dependências

---

### 3. Testar Conexão com MySQL (Local)
```bash
cd /opt/lampp/htdocs/TELia
python3 -c "
from database.connection import get_connection
try:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT 1')
    print('✅ Conexão com MySQL OK')
    cursor.close()
    conn.close()
except Exception as e:
    print(f'❌ Erro de conexão: {e}')
"
```

---

### 4. Testar Variáveis de Ambiente
```bash
cd /opt/lampp/htdocs/TELia
python3 -c "
from dotenv import load_dotenv
import os

load_dotenv()
bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
gemini_key = os.getenv('GEMINI_API_KEY')
mysql_host = os.getenv('MYSQL_HOST')

print(f'🤖 Bot Token: {\"✅ OK\" if bot_token else \"❌ Faltando\"}')
print(f'🧠 Gemini Key: {\"✅ OK\" if gemini_key else \"❌ Faltando\"}')
print(f'💾 MySQL Host: {mysql_host}')
"
```

---

### 5. Iniciar Bot Localmente para Testes
```bash
cd /opt/lampp/htdocs/TELia
python3 main.py
```

Você deve ver:
```
2026-04-20 10:30:45 - apscheduler.scheduler - INFO - Added job "check_reminders"
2026-04-20 10:30:45 - apscheduler.scheduler - INFO - Scheduler started
```

**No Telegram, teste:**
- `/start` → Deve mostrar menu
- `/ajuda` → Deve mostrar explicação da IA
- `/cadastrar` → Deve pedir email/senha
- `/login` → Deve pedir email/senha

---

## 🗄️ Verificar Banco de Dados

### 1. Verificar Novas Tabelas
```sql
-- MySQL
USE seu_banco;
SHOW TABLES;
DESCRIBE conversation_history;
DESCRIBE user_profile;
```

Deve mostrar:
- ✅ `conversation_history` (id, user_id, role, content, created_at)
- ✅ `user_profile` (id, user_id, key_name, value, updated_at)

---

### 2. Verificar Dados de Teste
```sql
SELECT * FROM users LIMIT 5;
SELECT * FROM conversation_history LIMIT 5;
SELECT * FROM user_profile LIMIT 5;
```

---

## ⚠️ Troubleshooting

### Erro: "conversation_history table does not exist"
```bash
# Reconectar ao banco para criar as tabelas
python3 -c "from database.connection import init_db; init_db()"
```

---

### Erro: "Gemini API key not found"
```bash
# Verificar .env
cat .env | grep GEMINI_API_KEY

# Se não existir, adicionar:
echo "GEMINI_API_KEY=sua_chave_aqui" >> .env
```

---

### Erro: "Bot token is invalid"
```bash
# Verificar token
cat .env | grep TELEGRAM_BOT_TOKEN

# Se não for válido, atualizar em .env
```

---

## 📊 Monitorar Bot em Produção

### Ver logs em tempo real
```bash
# Se usando systemd:
journalctl -u telia-bot -f

# Se usando screen/tmux:
screen -ls
screen -r telia-bot
```

---

### Verificar se bot está rodando
```bash
ps aux | grep "python main.py"
```

✅ Se aparecer processo, bot está ativo

---

### Reiniciar bot
```bash
pkill -f "python main.py"
sleep 2
python3 /opt/lampp/htdocs/TELia/main.py &
```

---

## ✅ Checklist Pré-Deploy

- [ ] Sintaxe Python validada (`py_compile`)
- [ ] Dependências instaladas (`pip list`)
- [ ] MySQL conectando (`get_connection()`)
- [ ] Variáveis de ambiente OK (`.env`)
- [ ] Bot iniciando sem erros (`python3 main.py`)
- [ ] Comandos respondendo no Telegram (`/start`, `/ajuda`)
- [ ] Cadastro funcionando (email + senha)
- [ ] Login funcionando (validação de credenciais)
- [ ] Conversa salvando histórico (check BD)
- [ ] Lembretes sendo salvos (check BD)
- [ ] Git commits locais prontos (`git log`)

---

## 🚀 Deploy Final

```bash
cd /opt/lampp/htdocs/TELia

# 1. Sincronizar com servidor
commitauto

# 2. Verificar status
git status
git log --oneline -3

# 3. Reiniciar bot no servidor
ssh seu_usuario@seu_servidor
pkill -f "python main.py"
cd /opt/lampp/htdocs/TELia
python3 start_server.py &
```

✅ Pronto! Bot rodando com todas as features novas.

---

## 📝 Commit Atual

```
🤖 Reengenharia completa: fluxo login/cadastro, conversa com IA, histórico e perfil
Commit: 8179b00
```

**Mudanças:**
- ✅ 7 arquivos modificados
- ✅ 418 linhas adicionadas
- ✅ 98 linhas removidas

---

## 🎯 Funcionalidades Entregues

1. ✅ `/login` com validação de email + senha
2. ✅ `/cadastrar` com proteção de email duplicado
3. ✅ `/ajuda` explicando integração com IA
4. ✅ IA responde conversa normal + lembretes + aprende perfil
5. ✅ Histórico de conversa (últimas 15 mensagens)
6. ✅ Perfil do usuário (palavras-chave)
7. ✅ `/sair` funciona corretamente
8. ✅ Compatível com BD servidor

---

**Alguma dúvida? Consulte `IMPLEMENTATION_SUMMARY.md` para mais detalhes!** 📖
