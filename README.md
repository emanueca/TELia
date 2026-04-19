# TELia — Bot de Lembretes com IA

Bot do Telegram que usa Gemini para extrair lembretes de mensagens em linguagem natural.

## Como rodar

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Preencher o .env com seus tokens
cp .env .env.local  # edite o .env diretamente

# 3. Iniciar o bot
python main.py
```

## Estrutura do projeto

```
TELia/
├── .env                  # (NÃO VAI PRO GITHUB) Suas senhas e tokens
├── .gitignore            # Diz ao Git o que ignorar (como o .env e o banco de dados)
├── requirements.txt      # Lista de bibliotecas (python-telegram-bot, apscheduler, etc)
├── README.md             # Instruções de como rodar o seu bot
├── main.py               # O arquivo principal que dá a partida no motor
│
├── database/             # Tudo relacionado ao SQLite
│   ├── connection.py     # Cria o banco e as tabelas
│   └── queries.py        # Funções para salvar e buscar lembretes
│
├── bot/                  # Comunicação direta com o Telegram
│   ├── commands.py       # Comandos como /start e /help
│   └── messages.py       # Onde chegam as mensagens de texto do usuário
│
├── ai/                   # O "Cérebro"
│   └── gemini.py         # Conexão com a API da IA e o Prompt de extração
│
└── scheduler/            # O "Relógio"
    └── jobs.py           # Funções que o APScheduler vai disparar (os lembretes)
```

## Variáveis de ambiente (`.env`)

| Variável | Descrição |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token do BotFather |
| `GEMINI_API_KEY` | Chave da API do Google Gemini |
