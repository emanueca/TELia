import logging
from dotenv import load_dotenv
import os

from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

from bot.commands import start, help_command
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
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    start_scheduler(app)

    app.run_polling()

if __name__ == "__main__":
    main()
