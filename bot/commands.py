from telegram import Update
from telegram.ext import ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Oi! Sou a TELia, sua assistente de lembretes.\n"
        "Me manda uma mensagem como:\n"
        "_'Me lembra de ligar pro João amanhã às 10h'_",
        parse_mode="Markdown",
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "*Como usar:*\n"
        "Escreva naturalmente o que quer lembrar e quando.\n\n"
        "Exemplos:\n"
        "• _Lembra de tomar remédio em 30 minutos_\n"
        "• _Me avisa amanhã às 9h para a reunião_",
        parse_mode="Markdown",
    )
