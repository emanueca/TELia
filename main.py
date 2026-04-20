import logging
from dotenv import load_dotenv
import os

from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from bot.commands import (
    start,
    help_command,
    cadastrar,
    login,
    sair,
    ajuda,
    ia,
    lembretes,
    timezone_command,
    timezone_callback,
    timezone_location,
)
from bot.messages import handle_message
from scheduler.jobs import start_scheduler

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("ajuda", ajuda))
    app.add_handler(CommandHandler("cadastrar", cadastrar))
    app.add_handler(CommandHandler("login", login))
    app.add_handler(CommandHandler("sair", sair))
    app.add_handler(CommandHandler("ia", ia))
    app.add_handler(CommandHandler("lembretes", lembretes))
    app.add_handler(CommandHandler("timezone", timezone_command))
    app.add_handler(CallbackQueryHandler(timezone_callback, pattern=r"^timezone:"))
    app.add_handler(MessageHandler(filters.LOCATION, timezone_location))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    start_scheduler(app)

    app.run_polling()

if __name__ == "__main__":
    main()
