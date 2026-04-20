from telegram import Update
from telegram.ext import ContextTypes

GITHUB_URL = "https://github.com/emanueca/TELia/tree/main#"
MSG_GITHUB = f"\n\n🌟 Conheça o projeto: {GITHUB_URL}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Oi! Sou a *TELia*, sua assistente de lembretes com IA.\n\n"
        "Para começar, crie sua conta com /cadastrar ou entre com /login.\n"
        "Quando quiser sair da sessão atual, use /sair."
        + MSG_GITHUB,
        parse_mode="Markdown",
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "*Como usar:*\n"
        "Após o login, escreva naturalmente o que quer lembrar e quando.\n\n"
        "Exemplos:\n"
        "• _Lembra de tomar remédio em 30 minutos_\n"
        "• _Me avisa amanhã às 9h para a reunião_\n\n"
        "*Comandos:*\n"
        "/cadastrar — criar conta\n"
        "/login — entrar na conta\n"
        "/sair — encerrar sessão"
        + MSG_GITHUB,
        parse_mode="Markdown",
    )

async def cadastrar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Para se cadastrar, copie a mensagem abaixo, preencha com seus dados e me envie de volta:\n\n"
        "E-mail: x\nSenha: y"
        + MSG_GITHUB,
    )

async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from database.queries import get_usuario, set_logado
    chat_id = update.effective_chat.id
    usuario = get_usuario(chat_id)

    if not usuario:
        await update.message.reply_text(
            "Você ainda não tem conta. Use /cadastrar para criar uma." + MSG_GITHUB
        )
        return

    set_logado(chat_id, True)
    await update.message.reply_text("Você está logado! Me manda um lembrete. 😊")


async def sair(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from database.queries import get_usuario, set_logado

    chat_id = update.effective_chat.id
    usuario = get_usuario(chat_id)

    if not usuario:
        await update.message.reply_text(
            "Você ainda não tem conta ativa aqui. Use /cadastrar para criar uma." + MSG_GITHUB
        )
        return

    set_logado(chat_id, False)
    await update.message.reply_text(
        "Sessão encerrada com sucesso.\n"
        "Quando quiser voltar, use /login."
    )
