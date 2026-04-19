# TELia — Bot de Lembretes com IA

Bot do telegram, com foco de ser leve e um agente de lembretes. Crie sua conta nele para que ele consiga salvar suas informações!

## Acesso

link telegram: 



## Variáveis de ambiente (`.env`)

| Variável | Descrição |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token do BotFather |
| `GEMINI_API_KEY` | Chave da API do Google Gemini |
| `MYSQL_HOST` | Host do MySQL (normalmente `localhost`) |
| `MYSQL_USER` | Usuário do MySQL |
| `MYSQL_PASSWORD` | Senha do MySQL |
| `MYSQL_DATABASE` | Nome do banco (`telia_db`) |

## Fluxo de uso

1. Usuário inicia o bot → recebe link do GitHub e instruções
2. `/cadastrar` → bot envia o formulário para copiar
3. Usuário cola: `E-mail: x` / `Senha: y` → conta criada com senha criptografada (bcrypt)
4. `/login` → entra na conta
5. A partir daí, mensagens livres são processadas pela IA e viram lembretes

## Estrutura do projeto

```
TELia/
├── .env                  # (NÃO VAI PRO GITHUB) Suas senhas e tokens
├── .gitignore            # Diz ao Git o que ignorar (como o .env e o banco de dados)
├── requirements.txt      # Lista de bibliotecas (python-telegram-bot, apscheduler, etc)
├── README.md             # Instruções de como rodar o seu bot
├── main.py               # O arquivo principal que dá a partida no motor
│
├── database/             # Tudo relacionado ao MySQL
│   ├── connection.py     # Cria o banco e as tabelas
│   └── queries.py        # Funções para salvar e buscar usuários e lembretes
│
├── bot/                  # Comunicação direta com o Telegram
│   ├── commands.py       # Comandos: /start, /help, /cadastrar, /login
│   └── messages.py       # Recebe textos, barreira de login, chama a IA
│
├── ai/                   # O "Cérebro"
│   └── gemini.py         # Conexão com a API da IA e o Prompt de extração
│
└── scheduler/            # O "Relógio"
    └── jobs.py           # Verifica lembretes pendentes a cada 30s
```
