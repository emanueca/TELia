import logging
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from telegram.ext import ContextTypes

from database.connection import init_db
from database.queries import get_due_reminder_tasks, mark_reminder_task_sent

logger = logging.getLogger(__name__)
_DEFAULT_TZ = "America/Sao_Paulo"
_scheduler_started = False
_DAY_TO_WEEKDAY = {
    "MON": 0,
    "TUE": 1,
    "WED": 2,
    "THU": 3,
    "FRI": 4,
    "SAT": 5,
    "SUN": 6,
}


def _to_datetime(value) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace(" ", "T"))
        except ValueError:
            return None
    return None


def _safe_zoneinfo(tz_name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(tz_name or _DEFAULT_TZ)
    except Exception:
        return ZoneInfo(_DEFAULT_TZ)


def _utc_naive_to_local(utc_naive: datetime, tz_name: str | None) -> datetime:
    tzinfo = _safe_zoneinfo(tz_name)
    utc_aware = utc_naive.replace(tzinfo=timezone.utc)
    return utc_aware.astimezone(tzinfo).replace(tzinfo=None)


def _local_to_utc_naive(local_naive: datetime, tz_name: str | None) -> datetime:
    tzinfo = _safe_zoneinfo(tz_name)
    local_aware = local_naive.replace(tzinfo=tzinfo)
    return local_aware.astimezone(timezone.utc).replace(tzinfo=None)


def _parse_schedule_code(schedule_code: str) -> tuple[str, str, str] | None:
    cleaned = (schedule_code or "").strip()
    if cleaned.startswith("[") and cleaned.endswith("]"):
        cleaned = cleaned[1:-1].strip()
    parts = [part.strip() for part in cleaned.split("|")]
    if len(parts) < 3:
        return None
    kind = parts[0].upper()
    hhmm = parts[1]
    recurrence = parts[2].upper()
    if kind != "LR":
        return None
    if not re.match(r"^\d{2}:\d{2}$", hhmm):
        return None
    return kind, hhmm, recurrence


def _next_weekly_local(now_local: datetime, hhmm: str, recurrence: str) -> datetime | None:
    if not recurrence.startswith("WEEKLY:"):
        return None
    day_tokens = [token.strip().upper() for token in recurrence.split(":", 1)[1].split(",") if token.strip()]
    target_weekdays = {_DAY_TO_WEEKDAY[token] for token in day_tokens if token in _DAY_TO_WEEKDAY}
    if not target_weekdays:
        return None

    hour, minute = map(int, hhmm.split(":"))
    base = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
    for offset in range(0, 8):
        candidate = base + timedelta(days=offset)
        if candidate.weekday() in target_weekdays and candidate > now_local:
            return candidate
    return None


def _next_run_for_task(task: dict) -> str | None:
    if task.get("kind") != "LR":
        return None

    parsed = _parse_schedule_code(task.get("schedule_code") or "")
    if not parsed:
        return None
    _, hhmm, recurrence = parsed

    tz_name = task.get("timezone") or _DEFAULT_TZ
    now_local = datetime.now(_safe_zoneinfo(tz_name)).replace(tzinfo=None)

    if recurrence == "DAILY":
        hour, minute = map(int, hhmm.split(":"))
        next_local = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if next_local <= now_local:
            next_local += timedelta(days=1)
    elif recurrence.startswith("WEEKLY:"):
        next_local = _next_weekly_local(now_local, hhmm, recurrence)
        if not next_local:
            return None
    else:
        return None

    next_run_utc = _local_to_utc_naive(next_local, tz_name)
    return next_run_utc.strftime("%Y-%m-%d %H:%M:%S")

async def _check_reminders(context: ContextTypes.DEFAULT_TYPE):
    try:
        logger.info("[scheduler] Verificando lembretes pendentes...")

        tasks = get_due_reminder_tasks()
        sent_tasks = 0
        for task in tasks:
            try:
                await context.bot.send_message(
                    chat_id=task["chat_id"],
                    text=f"Lembrete: {task['message']}",
                )

                if task.get("kind") == "LU":
                    mark_reminder_task_sent(task["id"], deactivate=True)
                else:
                    next_run_at = _next_run_for_task(task)
                    if next_run_at:
                        mark_reminder_task_sent(task["id"], next_run_at=next_run_at)
                    else:
                        mark_reminder_task_sent(task["id"], deactivate=True)
                sent_tasks += 1
            except Exception as e:
                logger.exception(f"Erro ao enviar reminder_task {task['id']}: {e}")

        logger.info(
            "[scheduler] Ciclo concluído. tasks_due=%s sent_tasks=%s",
            len(tasks),
            sent_tasks,
        )
    except Exception as e:
        logger.exception(f"Erro ao verificar lembretes: {e}")

def start_scheduler(app):
    global _scheduler_started

    init_db()
    if _scheduler_started:
        logger.info("[scheduler] Já está em execução. Ignorando nova inicialização.")
        return

    app.job_queue.run_repeating(
        _check_reminders,
        interval=30,
        first=5,
        name="telia-reminder-check",
    )
    _scheduler_started = True
    logger.info("[scheduler] Iniciado com intervalo de 30s.")
