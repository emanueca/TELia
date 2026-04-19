from telegram import Update
from telegram.ext import ContextTypes

from ai.gemini import extract_reminder
from database.queries import save_reminder

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    chat_id = update.effective_chat.id

    result = extract_reminder(text)

    if not result:
        await update.message.reply_text(
            "Não consegui identificar um lembrete. Tente algo como:\n"
            "_'Me lembra de X amanhã às 10h'_",
            parse_mode="Markdown",
        )
        return

    save_reminder(chat_id, result["message"], result["remind_at"])

    await update.message.reply_text(
        f"Lembrete salvo! Vou te avisar sobre *{result['message']}* em {result['remind_at']}.",
        parse_mode="Markdown",
    )
