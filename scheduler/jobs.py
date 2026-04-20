import asyncio
import logging
from apscheduler.schedulers.background import BackgroundScheduler

from database.connection import init_db
from database.queries import get_pending_reminders, mark_as_sent

logger = logging.getLogger(__name__)

def _check_reminders(app):
    try:
        reminders = get_pending_reminders()
        for reminder in reminders:
            try:
                asyncio.run_coroutine_threadsafe(
                    app.bot.send_message(
                        chat_id=reminder["chat_id"],
                        text=f"Lembrete: {reminder['message']}",
                    ),
                    app.updater.event_loop,
                )
                mark_as_sent(reminder["id"])
            except Exception as e:
                logger.exception(f"Erro ao enviar lembrete {reminder['id']}: {e}")
    except Exception as e:
        logger.exception(f"Erro ao verificar lembretes: {e}")

def start_scheduler(app):
    init_db()
    scheduler = BackgroundScheduler()
    scheduler.add_job(_check_reminders, "interval", seconds=30, args=[app])
    scheduler.start()
