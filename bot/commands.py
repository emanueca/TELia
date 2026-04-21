from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import ContextTypes
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

try:
    from timezonefinder import TimezoneFinder
except Exception:
    TimezoneFinder = None

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
    "1": ("Flash (recomendado)", "gemini-flash-latest"),
    "2": ("Flash 2.5 (mais inteligente)", "gemini-2.5-flash"),
    "3": ("Pro 2.5 (qualidade maxima)", "gemini-2.5-pro"),
    "4": ("Flash-Lite (economico)", "gemini-flash-lite-latest"),
}

_AI_MODEL_ALIASES = {
    "flash": "gemini-flash-latest",
    "flash2": "gemini-flash-latest",
    "flash2.0": "gemini-flash-latest",
    "gemini-2.0-flash": "gemini-2.0-flash",
    "gemini-2.5-flash": "gemini-2.5-flash",
    "flash2.5": "gemini-2.5-flash",
    "pro": "gemini-2.5-pro",
    "gemini-2.5-pro": "gemini-2.5-pro",
    "flash-lite": "gemini-flash-lite-latest",
    "flashlite": "gemini-flash-lite-latest",
    "gemini-2.0-flash-lite": "gemini-2.0-flash-lite",
    "gemini-flash-latest": "gemini-flash-latest",
    "gemini-flash-lite-latest": "gemini-flash-lite-latest",
    "gemini-pro-latest": "gemini-pro-latest",
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


def _format_task_next_run(task: dict) -> str:
    next_run = task.get("next_run_at")
    tz_name = task.get("timezone") or "America/Sao_Paulo"
    try:
        dt_utc = datetime.fromisoformat(str(next_run).replace(" ", "T")).replace(tzinfo=timezone.utc)
        dt_local = dt_utc.astimezone(ZoneInfo(tz_name))
        return dt_local.strftime("%d/%m %H:%M")
    except Exception:
        return str(next_run)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("awaiting", None)
    await update.message.reply_text(
        "Oi! Sou a *TELia*, sua assistente pessoal com IA.\n\n"
        "*Menu inicial de comandos:*\n"
        "/start — abre este menu inicial\n"
        "/cadastrar — criar nova conta\n"
        "/login — entrar na conta\n"
        "/sair — encerrar sessão\n"
        "/lembretes — listar, apagar ou mudar lembretes\n"
        "/ia — escolher o modelo de IA da sua conta\n"
        "/timezone — definir seu fuso horário\n"
        "/ajuda ou /help — ver explicações completas\n\n"
        "Dica: depois do login, é só conversar normalmente comigo."
        + MSG_GITHUB,
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
        "/lembretes — listar, apagar ou mudar lembretes\n"
        "/timezone — definir seu fuso horario\n"
        "/start — abrir o menu inicial\n"
        "/help — atalho para /ajuda\n"
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


async def timezone_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from database.queries import get_usuario, get_profile

    chat_id = update.effective_chat.id
    usuario = get_usuario(chat_id)
    if not usuario or not usuario["logado"]:
        await update.message.reply_text(
            "👋 Para configurar o fuso horário, você precisa estar logado.\n"
            "Use /login ou /cadastrar." + MSG_GITHUB
        )
        return

    profile = get_profile(chat_id)
    atual = profile.get("timezone", "America/Sao_Paulo")
    context.user_data["awaiting"] = "timezone_select"

    keyboard = [
        [
            InlineKeyboardButton("Sao Paulo", callback_data="timezone:set:America/Sao_Paulo"),
            InlineKeyboardButton("Manaus", callback_data="timezone:set:America/Manaus"),
        ],
        [
            InlineKeyboardButton("Lisboa", callback_data="timezone:set:Europe/Lisbon"),
            InlineKeyboardButton("Londres", callback_data="timezone:set:Europe/London"),
        ],
        [
            InlineKeyboardButton("Nova York", callback_data="timezone:set:America/New_York"),
            InlineKeyboardButton("Toquio", callback_data="timezone:set:Asia/Tokyo"),
        ],
        [
            InlineKeyboardButton("Usar localizacao do Telegram", callback_data="timezone:share_location"),
        ],
    ]

    await update.message.reply_text(
        f"🕒 Fuso atual: {atual}\n\n"
        "Escolha um fuso nos botões abaixo ou use sua localização para detectar automaticamente.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def lembretes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from database.queries import get_usuario, get_active_reminder_tasks

    chat_id = update.effective_chat.id
    usuario = get_usuario(chat_id)
    if not usuario or not usuario["logado"]:
        await update.message.reply_text(
            "👋 Para ver seus lembretes, você precisa estar logado.\n"
            "Use /login ou /cadastrar." + MSG_GITHUB
        )
        return

    tasks = get_active_reminder_tasks(chat_id)
    if not tasks:
        context.user_data.pop("lista_lembretes_recente", None)
        await update.message.reply_text(
            "Você não tem lembretes ativos no momento.\n"
            "Me peça um lembrete para começar."
        )
        return

    context.user_data["lista_lembretes_recente"] = [task["id"] for task in tasks]

    lines = []
    for i, task in enumerate(tasks, start=1):
        when = _format_task_next_run(task)
        lines.append(f"{i}. {task['message']} ({when})")

    await update.message.reply_text(
        "📌 *Seus lembretes ativos:*\n\n"
        + "\n".join(lines)
        + "\n\n"
        + "Digite *apagar N* ou *mudar N*.\n"
        + "Exemplos: `apagar 1` ou `mudar 2`.",
        parse_mode="Markdown",
    )


async def timezone_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from database.queries import get_usuario, upsert_profile

    query = update.callback_query
    await query.answer()
    data = query.data or ""

    chat_id = update.effective_chat.id
    usuario = get_usuario(chat_id)
    if not usuario or not usuario["logado"]:
        await query.edit_message_text(
            "👋 Para configurar o fuso horário, faça login com /login."
        )
        return

    if data.startswith("timezone:set:"):
        tz = data.split(":", 2)[2]
        upsert_profile(chat_id, "timezone", tz)
        context.user_data.pop("awaiting", None)
        await query.edit_message_text(
            f"✅ Fuso horário atualizado para: {tz}.\n"
            "Seus lembretes agora seguem esse horário local."
        )
        return

    if data == "timezone:share_location":
        context.user_data["awaiting"] = "timezone_location"
        await query.message.reply_text(
            "Toque no botão abaixo para enviar sua localização.\n"
            "Com isso eu detecto seu fuso automaticamente.",
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton("Enviar localizacao", request_location=True)]],
                one_time_keyboard=True,
                resize_keyboard=True,
            ),
        )
        await query.edit_message_text(
            "📍 Aguardando sua localização pelo botão do Telegram..."
        )


async def timezone_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from database.queries import get_usuario, upsert_profile

    if context.user_data.get("awaiting") != "timezone_location":
        return

    chat_id = update.effective_chat.id
    usuario = get_usuario(chat_id)
    if not usuario or not usuario["logado"]:
        await update.message.reply_text(
            "👋 Para configurar o fuso horário, faça login com /login.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    location = update.message.location
    if not location:
        await update.message.reply_text(
            "Não recebi uma localização válida. Tente novamente com /timezone.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    if TimezoneFinder is None:
        await update.message.reply_text(
            "Não consegui detectar o fuso automaticamente agora. "
            "Escolha manualmente com /timezone.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    tf = TimezoneFinder()
    tz = tf.timezone_at(lng=location.longitude, lat=location.latitude)
    if not tz:
        tz = tf.closest_timezone_at(lng=location.longitude, lat=location.latitude)

    if not tz:
        await update.message.reply_text(
            "Não consegui identificar seu fuso pela localização. "
            "Escolha manualmente com /timezone.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    upsert_profile(chat_id, "timezone", tz)
    context.user_data.pop("awaiting", None)
    await update.message.reply_text(
        f"✅ Fuso detectado automaticamente: {tz}.\n"
        "Seus próximos lembretes já vão respeitar esse horário.",
        reply_markup=ReplyKeyboardRemove(),
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
        "1. Flash: rapido, equilibrado e com boa cota gratis\n"
        "2. Flash 2.5: mais inteligente mantendo boa velocidade\n"
        "3. Pro 2.5: respostas de alta qualidade, mas cota menor\n"
        "4. Flash-Lite: super rapido e economico de cota\n\n"
        "Se nao escolher nada, o padrao continua sendo gemini-flash-latest.",
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
