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

DEVELOPER_PROMPTS = [
    "Olá, tudo bem?",
    "Como você tem passado ultimamente?",
    "O que você anda fazendo de bom hoje?",
    "Tem novidade por aí? Conta!",
    "Qual é a sua opinião sobre música brasileira?",
    "Me indica um filme bacana pra assistir?",
    "E aí, curtiu o fim de semana?",
    "Tá entendendo como usar esse bot?",
]


def resolve_ai_model_choice(text: str) -> str | None:
    choice = (text or "").strip().lower()
    if not choice:
        return None
    if choice in AI_MODEL_OPTIONS:
        return AI_MODEL_OPTIONS[choice][1]
    if choice in _AI_MODEL_ALIASES:
        return _AI_MODEL_ALIASES[choice]
    return None


async def _block_if_anon(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Retorna True e envia mensagem de bloqueio se o usuário estiver em modo anônimo."""
    try:
        # Permite explicitamente o comando /desenvolvedor mesmo em modo anônimo
        try:
            if update and getattr(update, "message", None) and isinstance(update.message.text, str):
                if update.message.text.strip().lower().startswith("/desenvolvedor"):
                    return False
        except Exception:
            pass

        if context.user_data.get("status") == "anonimo":
            msg = (
                "MODO ANÔNIMO ATIVO 👤\n\n"
                "Comandos de sistema estão desativados neste modo. Use /start para voltar ao menu inicial."
            )
            if update and getattr(update, "callback_query", None):
                try:
                    await update.callback_query.edit_message_text(msg)
                except Exception:
                    pass
            else:
                try:
                    await update.message.reply_text(msg)
                except Exception:
                    pass
            return True
    except Exception:
        pass
    return False


async def start_developer_mode(update: Update, context: ContextTypes.DEFAULT_TYPE, *, auto_message: str | None = None):
    """Ativa o modo desenvolvedor com um primeiro prompt fixo e próximos prompts aleatórios."""
    context.user_data["status"] = "anonimo"
    context.user_data["awaiting"] = "dev_reply"
    context.user_data["dev_prompts"] = list(DEVELOPER_PROMPTS)

    if auto_message:
        await update.message.reply_text(auto_message, parse_mode="Markdown")
    else:
        await update.message.reply_text(
            "Bem vindo ao modo desenvolvedor! Vou te enviar mensagens e tente replicar de forma informal "
            "(pode ter gírias, erros de digitação mas nada fora do contexto!)."
            "\n\nRespondendo, você ajuda no treinamento do modelo. Para sair, use /sair ou /start.",
        )

    await update.message.reply_text(DEVELOPER_PROMPTS[0])


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
    keyboard = [
        [
            InlineKeyboardButton(
                "Entrar como Anônimo 👤 (nenhuma informação vai ser salva e você terá acesso ao modo de treinamento para tirar pequenas dúvidas)",
                callback_data="entrada_anonimo",
            )
        ],
        [InlineKeyboardButton("Entrada Normal 💻", callback_data="agenda")],
    ]

    await update.message.reply_text(
        "Olá! Eu sou a *TELia*... Para começar a conversar crie uma conta ou entre como anônimo.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def entrada_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    # Entrada normal: mostra o menu padrão (antes do botão)
    if data == "agenda":
        await query.edit_message_text(
            "Oi! Sou a *TELia*, sua assistente pessoal com IA.\n\n"
            "*Menu inicial de comandos:*\n"
            "/start — abre este menu inicial\n"
            "/cadastrar — criar nova conta\n"
            "/login — entrar na conta\n"
            "/sair — encerrar sessão\n"
            "/clean — apagar as mensagens visíveis deste chat\n"
            "/reportar — relatar um problema\n"
            "/lembretes — listar, apagar ou mudar lembretes\n"
            "/ia — escolher o modelo de IA da sua conta\n"
            "/timezone — definir seu fuso horário\n"
            "/ajuda ou /help — ver explicações completas\n\n"
            "Dica: depois do login, é só conversar normalmente comigo." + MSG_GITHUB,
            parse_mode="Markdown",
        )
        return

    # Entrada anônima: ativa estado 'anonimo' no user_data e mostra o menu anônimo
    if data == "entrada_anonimo":
        context.user_data["status"] = "anonimo"
        await query.edit_message_text(
            "MODO ANÔNIMO ATIVO 👤\n\n"
            "Você está no chat de conversas banais da TELia (anônimas que vão ser salvas para treinamento da IA)."
            " Sinta-se à vontade para bater um papo, mas lembre-se que nenhuma informação pessoal sua será armazenada e esse modo contém MUITOS ERROS!!"
            "\n\nOs comandos de sistema estão desativados, exceto /desenvolvedor. Use /start para voltar ao modo normal.\n\n"
            "OBS: Se eu não responder em até 30 segundos, este modo será desativado automaticamente.",
        )
        return



async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await _block_if_anon(update, context):
        return
    await ajuda(update, context)


async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Primeira mensagem: explicação
    if await _block_if_anon(update, context):
        return
    await update.message.reply_text(
        "*🤖 Como a TELia funciona:*\n\n"
        "A TELia usa IA para entender suas mensagens, guardar contexto por usuário e responder de forma natural.\n\n"
        "*💡 Por que criar uma conta?*\n"
        "• Suas conversas ficam salvas por usuário e não vazam para outras contas\n"
        "• Lembretes ficam em reminder_tasks, com suporte a lembrete único e recorrente\n"
        "• O perfil do usuário guarda informações como nome, cidade, profissão, timezone e modelo de IA\n"
        "• Você pode apagar só as mensagens visíveis da conversa com /clean\n"
        "• Você também pode relatar problemas com /reportar\n\n"
        "*⚙️ Como a IA funciona:*\n"
        "Cada mensagem sua vai para o Gemini junto com o histórico recente da conta e o perfil salvo no banco.\n\n"
        "*✨ O que você pode fazer:*\n"
        "• *Conversar livremente* — faça perguntas, peça opiniões, bata papo\n"
        "• *Criar lembretes* — 'me lembra de tomar remédio às 10h'\n"
        "• *Compartilhar informações* — 'meu nome é Ana' — a IA vai lembrar!\n\n"
        "*📋 Comandos:*\n"
        "/cadastrar — criar nova conta\n"
        "/login — entrar na conta\n"
        "/sair — encerrar sessão\n"
        "/clean — apagar as mensagens visíveis do Telegram\n"
        "/reportar — relatar um problema\n"
        "/ia — escolher modelo de IA\n"
        "/lembretes — listar, apagar ou mudar lembretes\n"
        "/timezone — definir seu fuso horario\n"
        "/start — abrir o menu inicial\n"
        "/help — atalho para /ajuda\n"
        "/ajuda — esta mensagem\n\n"
        "*🧰 Bibliotecas usadas:*\n"
        "• `python-telegram-bot` — comandos, mensagens e botões\n"
        "• `mysql-connector-python` — conexão com o MySQL\n"
        "• `google-generativeai` — integração com o Gemini\n"
        "• `timezonefinder` — detecção automática de fuso horário\n"
        "• `python-dotenv` — carregamento das variáveis do .env"
        + MSG_GITHUB,
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
        "       ├─ user_profile (nome, cidade, timezone, IA)\n"
        "       └─ chat_sessions (qual conta está ativa neste chat)\n"
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
        "       ├─ reminder_tasks (se foi um lembrete)\n"
        "       └─ reports (quando você usa /reportar)\n"
        "       ↓\n"
        "  📤 Resposta enviada para você\n"
        "```",
        parse_mode="Markdown",
    )


async def clean(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await _block_if_anon(update, context):
        return

    context.user_data["awaiting"] = "clean_confirm"
    prompt = await update.message.reply_text(
        "Você tem certeza?\n\n"
        "Responda com *sim* para apagar as mensagens visíveis desta conversa no Telegram.\n"
        "Responda com *não* para cancelar.\n\n"
        "Isso não mexe no banco, só limpa o chat para não ficar cheio de mensagens."
        + MSG_GITHUB,
        parse_mode="Markdown",
    )

    cleanup_ids = context.chat_data.setdefault("cleanup_message_ids", [])
    if prompt.message_id not in cleanup_ids:
        cleanup_ids.append(prompt.message_id)


async def reportar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from database.queries import get_usuario
    if await _block_if_anon(update, context):
        return

    chat_id = update.effective_chat.id
    usuario = get_usuario(chat_id)
    if not usuario or not usuario["logado"]:
        await update.message.reply_text(
            "👋 Para relatar um problema, você precisa estar logado.\n"
            "Use /login ou /cadastrar." + MSG_GITHUB
        )
        return

    context.user_data["awaiting"] = "report_issue"
    context.user_data.pop("report_draft", None)
    await update.message.reply_text(
        "Qual problema você está relatando?\n\n"
        "Me descreva o que aconteceu e eu vou te ajudar a registrar isso." + MSG_GITHUB
    )


async def cadastrar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await _block_if_anon(update, context):
        return

    context.user_data["awaiting"] = "cadastrar"
    await update.message.reply_text(_FORM_CADASTRAR + MSG_GITHUB)


async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await _block_if_anon(update, context):
        return

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
    if await _block_if_anon(update, context):
        return

    from database.queries import get_usuario, get_profile

    chat_id = update.effective_chat.id
    usuario = get_usuario(chat_id)
    if not usuario or not usuario["logado"]:
        await update.message.reply_text(
            "👋 Para configurar o fuso horário, você precisa estar logado.\n"
            "Use /login ou /cadastrar." + MSG_GITHUB
        )
        return

    user_id = usuario["chat_id"]
    profile = get_profile(user_id)
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
    if await _block_if_anon(update, context):
        return

    from database.queries import get_usuario, get_active_reminder_tasks

    chat_id = update.effective_chat.id
    usuario = get_usuario(chat_id)
    if not usuario or not usuario["logado"]:
        await update.message.reply_text(
            "👋 Para ver seus lembretes, você precisa estar logado.\n"
            "Use /login ou /cadastrar." + MSG_GITHUB
        )
        return

    user_id = usuario["chat_id"]
    tasks = get_active_reminder_tasks(user_id)
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
    if await _block_if_anon(update, context):
        return

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
        upsert_profile(usuario["chat_id"], "timezone", tz)
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
    if await _block_if_anon(update, context):
        return

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

    upsert_profile(usuario["chat_id"], "timezone", tz)
    context.user_data.pop("awaiting", None)
    await update.message.reply_text(
        f"✅ Fuso detectado automaticamente: {tz}.\n"
        "Seus próximos lembretes já vão respeitar esse horário.",
        reply_markup=ReplyKeyboardRemove(),
    )


async def ia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from database.queries import get_usuario
    if await _block_if_anon(update, context):
        return

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


async def modo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await _block_if_anon(update, context):
        return

    keyboard = [
        [InlineKeyboardButton("🍽️ Reservar Almoço, IFFar-FW", callback_data="modo:reservar_almoco")],
        [InlineKeyboardButton("📊 Cálculo de Notas", callback_data="modo:calc_notas")],
        [InlineKeyboardButton("🤖 Testar IA", callback_data="modo:testar_ia")],
        [InlineKeyboardButton('📝 "Bloco de Notas"', callback_data="modo:bloco_notas")],
    ]
    await update.message.reply_text(
        "Escolha um desses modos abaixo:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def desenvolvedor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ativa o modo desenvolvedor: envia mensagens automáticas para o usuário replicar informalmente.

    O primeiro prompt é sempre o mesmo; prompts seguintes são sorteados.
    """
    await start_developer_mode(update, context)


async def modo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await _block_if_anon(update, context):
        return

    from database.queries import get_usuario, has_ru_credentials, get_ru_credentials
    from ru.credentials import decrypt
    from ru.booking import login_and_get_days

    query = update.callback_query
    await query.answer()
    data = query.data or ""

    if data == "modo:reservar_almoco":
        chat_id = update.effective_chat.id
        usuario = get_usuario(chat_id)
        if not usuario or not usuario["logado"]:
            await query.edit_message_text(
                "👋 Para usar este modo, você precisa estar logado.\n"
                "Use /login ou /cadastrar."
            )
            return

        user_id = usuario["chat_id"]
        ja_tem = has_ru_credentials(user_id)
        context.user_data["ru_user_id"] = user_id

        if ja_tem:
            keyboard = [
                [InlineKeyboardButton("🍽️ Reservar agora", callback_data="modo:iniciar_reserva")],
                [InlineKeyboardButton("🔑 Atualizar credenciais", callback_data="modo:atualizar_creds")],
            ]
            await query.edit_message_text(
                "🍽️ *Reserva Automática de Almoço — IFFar-FW*\n\n"
                "✅ Você já tem credenciais configuradas.\n\n"
                "O que deseja fazer?",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        else:
            context.user_data["awaiting"] = "ru_cpf"
            await query.edit_message_text(
                "🍽️ *Reserva Automática de Almoço — IFFar-FW*\n\n"
                "Para configurar, preciso das suas credenciais do portal IFFar.\n\n"
                "Envie seu CPF no formato:\n"
                "`CPF:XXXXXXXXXXX`\n"
                "_(11 dígitos, sem pontos ou traços)_\n\n"
                "Ou envie /cancelar para sair.",
                parse_mode="Markdown",
            )
        return

    if data == "modo:atualizar_creds":
        chat_id = update.effective_chat.id
        usuario = get_usuario(chat_id)
        if not usuario or not usuario["logado"]:
            await query.edit_message_text("👋 Faça login com /login.")
            return
        context.user_data["awaiting"] = "ru_cpf"
        context.user_data["ru_user_id"] = usuario["chat_id"]
        await query.edit_message_text(
            "🔑 *Atualizar credenciais do RU*\n\n"
            "Envie seu novo CPF no formato:\n"
            "`CPF:XXXXXXXXXXX`\n"
            "_(11 dígitos, sem pontos ou traços)_\n\n"
            "Ou envie /cancelar para sair.",
            parse_mode="Markdown",
        )
        return

    if data == "modo:iniciar_reserva":
        chat_id = update.effective_chat.id
        usuario = get_usuario(chat_id)
        if not usuario or not usuario["logado"]:
            await query.edit_message_text("👋 Faça login com /login.")
            return

        user_id = usuario["chat_id"]
        creds = get_ru_credentials(user_id)
        if not creds:
            await query.edit_message_text(
                "❌ Não encontrei suas credenciais. Use /modo → Reservar Almoço para configurar."
            )
            return

        await query.edit_message_text("⏳ Entrando no sistema do RU, aguarde...")
        try:
            cpf = decrypt(creds["cpf_enc"])
            senha = decrypt(creds["senha_enc"])
            result = await login_and_get_days(cpf, senha)
        except Exception:
            await query.edit_message_text(
                "⚠️ Erro ao acessar o sistema do RU. Tente novamente mais tarde."
            )
            return

        if not result["success"]:
            await query.edit_message_text(
                f"❌ Não consegui entrar no sistema do RU.\n\n"
                f"Motivo: {result['error']}\n\n"
                "Verifique suas credenciais com /modo → Reservar Almoço → Atualizar credenciais."
            )
            return

        raw_days = result["raw_days"]
        if not raw_days:
            await query.edit_message_text(
                "✅ Entrei com sucesso no sistema!\n\n"
                "Mas não encontrei dias disponíveis para agendamento no momento.\n"
                "Tente novamente mais tarde."
            )
            return

        dias_txt_lines = []
        available_to_book = []
        for d in raw_days:
            if d.get("is_booked"):
                dias_txt_lines.append(f"✅ {d['label']} *(Já agendado)*")
            else:
                available_to_book.append(d)
                idx = len(available_to_book)
                dias_txt_lines.append(f"*{idx}.* {d['label']}")

        context.user_data["ru_available_days"] = available_to_book
        context.user_data["ru_cpf_dec"] = cpf
        context.user_data["ru_senha_dec"] = senha
        context.user_data["awaiting"] = "ru_select_days"

        dias_txt = "\n".join(dias_txt_lines)
        
        msg = (
            "✅ *Entrei com sucesso no sistema do RU!*\n\n"
            "⚠️ *Regras de Agendamento:*\n"
            "• Você sempre tem um horizonte de *7 dias* para agendar.\n"
            "• Para agendar o almoço do *dia seguinte*, o limite é até as *17:00*.\n"
            "• Passou das 17:00, o sistema bloqueia o dia seguinte.\n\n"
            f"*Horizonte de dias:*\n\n{dias_txt}\n\n"
        )
        
        if available_to_book:
            msg += (
                "Quais dias disponíveis você quer agendar?\n"
                "Diga *todos*, ou cite os números: `1, 2, 3`\n"
                "Ou envie /cancelar para sair."
            )
        else:
            msg += "Todos os dias disponíveis já estão agendados! Envie /cancelar para sair."

        await query.edit_message_text(msg, parse_mode="Markdown")
        return

    labels = {
        "modo:calc_notas": "📊 Cálculo de Notas",
        "modo:testar_ia": "🤖 Testar IA",
        "modo:bloco_notas": '📝 "Bloco de Notas"',
    }
    label = labels.get(data, "Este modo")
    await query.edit_message_text(f"{label}\n\n⚙️ Ainda em Desenvolvimento.")


async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await _block_if_anon(update, context):
        return

    context.user_data.pop("awaiting", None)
    context.user_data.pop("ru_cpf_tmp", None)
    context.user_data.pop("ru_user_id", None)
    context.user_data.pop("ru_cpf_dec", None)
    context.user_data.pop("ru_senha_dec", None)
    context.user_data.pop("ru_available_days", None)
    await update.message.reply_text("Operação cancelada. Use /modo para começar novamente.")


async def sair(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from database.queries import get_usuario, set_logado, clear_chat_session

    chat_id = update.effective_chat.id
    usuario = get_usuario(chat_id)

    if context.user_data.get("status") == "anonimo":
        if context.user_data.get("awaiting") == "dev_reply":
            context.user_data.pop("awaiting", None)
            context.user_data.pop("dev_prompts", None)
            await update.message.reply_text(
                "Modo de treinamento encerrado. Você voltou para a conversa anônima normal.\n"
                "Se o ChatBot continuar offline, eu posso reativar esse modo automaticamente na próxima mensagem."
            )
        else:
            await update.message.reply_text(
                "Você já está no modo anônimo. Use /desenvolvedor para treinar a IA ou /start para voltar ao menu inicial."
            )
        return

    if await _block_if_anon(update, context):
        return

    context.user_data.pop("awaiting", None)
    context.user_data.pop("report_draft", None)

    if not usuario or not usuario["logado"]:
        await update.message.reply_text(
            "Você não está logado no momento.\n"
            "Use /login para entrar ou /cadastrar para criar uma conta." + MSG_GITHUB
        )
        return

    set_logado(usuario["chat_id"], False)
    clear_chat_session(chat_id)
    await update.message.reply_text(
        "Sessão encerrada com sucesso. Até logo! 👋\n"
        "Quando quiser voltar, use /login."
    )
