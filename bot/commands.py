from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes

GITHUB_URL = "https://github.com/emanueca/TELia/tree/main#"
MSG_GITHUB = f"\n\n🌟 Conheça o projeto: {GITHUB_URL}"

_FORM_LOGIN = (
    "Para entrar, copie a mensagem abaixo, preencha com seus dados e me envie de volta:\n\n"
    "E-mail: \nSenha: "
)

_FORM_CADASTRAR = (
    "Para se cadastrar, copie a mensagem abaixo, preencha com seus dados e me envie de volta:\n\n"
    "E-mail: \nSenha: "
)

AI_MODEL_OPTIONS = {
    "1": ("Flash 2.0 (recomendado)", "gemini-2.0-flash"),
    "2": ("Flash 2.5 (mais inteligente)", "gemini-2.5-flash"),
    "3": ("Pro 2.5 (qualidade maxima)", "gemini-2.5-pro"),
    "4": ("Flash-Lite 2.0 (economico)", "gemini-2.0-flash-lite"),
}

_AI_MODEL_ALIASES = {
    "flash": "gemini-2.0-flash",
    "flash2": "gemini-2.0-flash",
    "flash2.0": "gemini-2.0-flash",
    "gemini-2.0-flash": "gemini-2.0-flash",
    "gemini-2.5-flash": "gemini-2.5-flash",
    "flash2.5": "gemini-2.5-flash",
    "pro": "gemini-2.5-pro",
    "gemini-2.5-pro": "gemini-2.5-pro",
    "flash-lite": "gemini-2.0-flash-lite",
    "flashlite": "gemini-2.0-flash-lite",
    "gemini-2.0-flash-lite": "gemini-2.0-flash-lite",
}


def resolve_ai_model_choice(text: str) -> str | None:
    choice = (text or "").strip().lower()
    if not choice:
        return None
    if choice in AI_MODEL_OPTIONS:
        return AI_MODEL_OPTIONS[choice][1]
    if choice in _AI_MODEL_ALIASES:
        return _AI_MODEL_ALIASES[choice]
    return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("awaiting", None)
    await update.message.reply_text(
        "Oi! Sou a *TELia*, sua assistente pessoal com IA.\n\n"
        "Para começar, crie sua conta com /cadastrar ou entre com /login.\n"
        "Quando quiser sair da sessão, use /sair.\n"
        "Para saber mais, use /ajuda." + MSG_GITHUB,
        parse_mode="Markdown",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await ajuda(update, context)


async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Primeira mensagem: explicação
    await update.message.reply_text(
        "*🤖 Como a TELia funciona:*\n\n"
        "A TELia usa a IA para entender e responder suas mensagens "
        "com pythonde forma otimizada.\n\n"
        "*💡 Por que criar uma conta?*\n"
        "• Suas conversas ficam salvas — a IA lembra o contexto das últimas mensagens\n"
        "• Lembretes são vinculados à sua conta e enviados no horário certo\n"
        "• A IA aprende informações sobre você (nome, cidade, profissão...) e usa isso nas respostas\n"
        "• Seus dados ficam protegidos por senha\n\n"
        "*⚙️ Como a IA funciona:*\n"
        "Cada mensagem sua é enviada ao Gemini junto com:\n"
        "  1. Seu histórico recente de conversa (últimas 15 mensagens)\n"
        "  2. Seu perfil (informações que você compartilhou)\n"
        "Isso permite respostas com contexto e memória real.\n\n"
        "*✨ O que você pode fazer:*\n"
        "• *Conversar livremente* — faça perguntas, peça opiniões, bata papo\n"
        "• *Criar lembretes* — 'me lembra de tomar remédio às 10h'\n"
        "• *Compartilhar informações* — 'meu nome é Ana' — a IA vai lembrar!\n\n"
        "*📋 Comandos:*\n"
        "/cadastrar — criar nova conta\n"
        "/login — entrar na conta\n"
        "/sair — encerrar sessão\n"
        "/ia — escolher modelo de IA\n"
        "/ajuda — esta mensagem" + MSG_GITHUB,
        parse_mode="Markdown",
    )
    
    # Segunda mensagem: fluxo de dados
    await update.message.reply_text(
        "*📊 Fluxo de Dados e Banco de Dados:*\n\n"
        "```\n"
        "  📱 TELEGRAM (Você)\n"
        "       ↓\n"
        "  💬 Envia mensagem\n"
        "       ↓\n"
        "  🔐 TELia verifica LOGIN\n"
        "       ↓ (autenticado)\n"
        "  📚 Carrega CONTEXTO\n"
        "       ├─ conversation_history (últimas 15 msgs)\n"
        "       └─ user_profile (seu perfil)\n"
        "       ↓\n"
        "  🧠 Envia ao GEMINI\n"
        "       │\n"
        "       ├─ Sua mensagem\n"
        "       ├─ Histórico recente\n"
        "       └─ Seu perfil\n"
        "       ↓\n"
        "  💡 Gemini responde com:\n"
        "       ├─ reply (resposta natural)\n"
        "       ├─ reminder (lembrete, se houver)\n"
        "       └─ profile_updates (info aprendida)\n"
        "       ↓\n"
        "  💾 TELia SALVA no BD:\n"
        "       ├─ conversation_history (sua msg + resposta)\n"
        "       ├─ user_profile (dados aprendidos)\n"
        "       └─ reminders (se foi um lembrete)\n"
        "       ↓\n"
        "  📤 Resposta enviada para você\n"
        "```",
        parse_mode="Markdown",
    )


async def cadastrar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["awaiting"] = "cadastrar"
    await update.message.reply_text(_FORM_CADASTRAR + MSG_GITHUB)


async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from database.queries import get_usuario

    chat_id = update.effective_chat.id
    usuario = get_usuario(chat_id)

    if usuario and usuario["logado"]:
        await update.message.reply_text(
            "Você já está logado! Pode me enviar uma mensagem. 😊\n"
            "Para sair, use /sair."
        )
        return

    context.user_data["awaiting"] = "login"
    await update.message.reply_text(
        "No chat, adicione suas informações aqui!\n\n" + _FORM_LOGIN + MSG_GITHUB
    )


async def ia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from database.queries import get_usuario

    chat_id = update.effective_chat.id
    usuario = get_usuario(chat_id)

    if not usuario or not usuario["logado"]:
        await update.message.reply_text(
            "👋 Para escolher o modelo de IA, você precisa estar logado.\n"
            "Use /login ou /cadastrar." + MSG_GITHUB
        )
        return

    context.user_data["awaiting"] = "ia_model"
    keyboard = [["1", "2"], ["3", "4"]]
    await update.message.reply_text(
        "Escolha o modelo da IA para sua conta (responda com 1, 2, 3 ou 4):\n\n"
        "1. Flash 2.0: rapido, equilibrado e com boa cota gratis\n"
        "2. Flash 2.5: mais inteligente mantendo boa velocidade\n"
        "3. Pro 2.5: respostas de alta qualidade, mas cota menor\n"
        "4. Flash-Lite 2.0: super rapido e economico de cota\n\n"
        "Se nao escolher nada, o padrao continua sendo gemini-2.0-flash.",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True),
    )


async def sair(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from database.queries import get_usuario, set_logado

    chat_id = update.effective_chat.id
    usuario = get_usuario(chat_id)

    context.user_data.pop("awaiting", None)

    if not usuario or not usuario["logado"]:
        await update.message.reply_text(
            "Você não está logado no momento.\n"
            "Use /login para entrar ou /cadastrar para criar uma conta." + MSG_GITHUB
        )
        return

    set_logado(chat_id, False)
    await update.message.reply_text(
        "Sessão encerrada com sucesso. Até logo! 👋\n"
        "Quando quiser voltar, use /login."
    )
