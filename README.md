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

## Reserva automática do RU

O modo IFFar pode usar automação com Playwright para reservar o almoço do RU de forma programada.

Fluxo resumido:

1. O usuário escolhe o modo IFFar no `/modo`.
2. A TELia salva as credenciais e preferências ligadas ao usuário logado.
3. Um job agendado chama o Playwright no servidor.
4. O Playwright abre o portal do RU, faz login e tenta executar a reserva.
5. Se der certo, a TELia avisa o usuário no Telegram e pode guardar o comprovante ou status da execução.

Observações:

1. O pacote `playwright` precisa ser instalado via `pip`.
2. Os navegadores do Playwright também precisam ser instalados no servidor com `playwright install chromium`.
3. Se o portal do IFFar usar captcha, bloqueio forte ou fluxo muito diferente, a automação pode quebrar e exigir ajuste.

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
