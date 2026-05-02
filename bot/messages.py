import asyncio
import hashlib
import logging
import re
from datetime import datetime, timedelta, timezone
from contextlib import suppress
from zoneinfo import ZoneInfo
from telegram import Update
from telegram.ext import ContextTypes

from bot.commands import MSG_GITHUB, resolve_ai_model_choice
from database.queries import (
    get_usuario,
    criar_usuario,
    verificar_login,
    email_existe,
    set_logado,
    set_chat_session,
    save_report,
    save_reminder_task,
    get_reminder_task_by_id,
    get_overdue_reminder_tasks,
    deactivate_reminder_task,
    update_reminder_task_schedule,
    save_message,
    get_history,
    get_profile,
    upsert_profile,
)
from ai.gemini import process_message, process_report_issue

logger = logging.getLogger(__name__)
_DEFAULT_TZ = "America/Sao_Paulo"
_THINKING_FRAMES = ["✍️ Cozinhando.", "✍️ Cozinhando..", "✍️ Cozinhando...", "✍️ Cozinhando.."]
_THINKING_ANIMATION_INTERVAL = 2.5
_THINKING_SLOW_LIMIT_SECONDS = 300
_THINKING_CANCEL_LIMIT_SECONDS = 480
_THINKING_SLOW_TEXT = "✍️ Receita difícil essa ein..."
_THINKING_TIMEOUT_TEXT = (
    "opss... Parece que queimei o pedido, envie um relatório sobre isso ou tente novamente mais tarde."
)


async def _safe_edit(msg, text: str, parse_mode: str | None = None):
    """Edita uma mensagem Telegram; se falhar com Markdown, tenta sem formatação."""
    try:
        await msg.edit_text(text, parse_mode=parse_mode)
    except Exception:
        if parse_mode:
            try:
                await msg.edit_text(text)
            except Exception:
                logger.exception("Falha ao editar mensagem (fallback sem parse_mode).")
        else:
            logger.exception("Falha ao editar mensagem.")
_DAY_TO_WEEKDAY = {
    "MON": 0,
    "TUE": 1,
    "WED": 2,
    "THU": 3,
    "FRI": 4,
    "SAT": 5,
    "SUN": 6,
}


def _hash(senha: str) -> str:
    return hashlib.sha256(senha.encode("utf-8")).hexdigest()


def _parse_form(text: str) -> tuple[str, str] | None:
    """Parses 'E-mail: x\\nSenha: y' and returns (email, senha) or None."""
    try:
        linhas = text.strip().split("\n")
        email = linhas[0].split(":", 1)[1].strip()
        senha = linhas[1].split(":", 1)[1].strip()
        if not email or not senha:
            return None
        return email, senha
    except Exception:
        return None


def _normalize_reporter_name(text: str) -> tuple[str | None, bool]:
    cleaned = (text or "").strip()
    if not cleaned:
        return None, True

    lowered = cleaned.lower()
    if cleaned == "..." or "..." in cleaned or lowered in {"anonimo", "anônimo", "anonymous", "anon"}:
        return None, True

    return cleaned, False


def _remember_chat_message(context: ContextTypes.DEFAULT_TYPE, message_id: int | None):
    if not message_id:
        return

    cleanup_ids = context.chat_data.setdefault("cleanup_message_ids", [])
    if message_id not in cleanup_ids:
        cleanup_ids.append(message_id)
        if len(cleanup_ids) > 200:
            del cleanup_ids[:-200]


async def _cleanup_chat_messages(context: ContextTypes.DEFAULT_TYPE, bot, chat_id: int) -> int:
    cleanup_ids = list(context.chat_data.pop("cleanup_message_ids", []))
    deleted = 0
    for message_id in reversed(cleanup_ids):
        try:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
            deleted += 1
        except Exception:
            pass
    return deleted


async def _animate_waiting_message(msg, stop_event: asyncio.Event):
    frame_index = 0
    try:
        while not stop_event.is_set():
            await _safe_edit(msg, _THINKING_FRAMES[frame_index])
            frame_index = (frame_index + 1) % len(_THINKING_FRAMES)
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=_THINKING_ANIMATION_INTERVAL)
            except asyncio.TimeoutError:
                continue
    except asyncio.CancelledError:
        raise


def _to_datetime(value) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        return None
    text = value.strip().replace(" ", "T")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _get_user_timezone(profile: dict | None) -> str:
    tz_value = str((profile or {}).get("timezone") or _DEFAULT_TZ).strip()
    try:
        ZoneInfo(tz_value)
        return tz_value
    except Exception:
        return _DEFAULT_TZ


def _local_to_utc_naive(dt_local: datetime, tz_name: str) -> datetime:
    local_aware = dt_local.replace(tzinfo=ZoneInfo(tz_name))
    return local_aware.astimezone(timezone.utc).replace(tzinfo=None)


def _next_daily_run(time_str: str, tz_name: str) -> datetime | None:
    try:
        hour, minute = time_str.split(":", 1)
        now_local = datetime.now(ZoneInfo(tz_name))
        target_local = now_local.replace(
            hour=int(hour),
            minute=int(minute),
            second=0,
            microsecond=0,
        )
        if target_local <= now_local:
            target_local = target_local + timedelta(days=1)
        return target_local.replace(tzinfo=None)
    except Exception:
        return None


def _next_weekly_run(time_str: str, days_csv: str, tz_name: str) -> datetime | None:
    try:
        hour, minute = time_str.split(":", 1)
        now_local = datetime.now(ZoneInfo(tz_name))
        base_local = now_local.replace(
            hour=int(hour),
            minute=int(minute),
            second=0,
            microsecond=0,
        )
        day_tokens = [token.strip().upper() for token in days_csv.split(",") if token.strip()]
        target_weekdays = {_DAY_TO_WEEKDAY[token] for token in day_tokens if token in _DAY_TO_WEEKDAY}
        if not target_weekdays:
            return None

        for offset in range(0, 8):
            candidate = base_local + timedelta(days=offset)
            if candidate.weekday() in target_weekdays and candidate > now_local:
                return candidate.replace(tzinfo=None)
        return None
    except Exception:
        return None


def _translate_logic_code(logic_code: str, reminder: dict | None, profile: dict | None) -> dict | None:
    if not logic_code or not isinstance(logic_code, str):
        return None

    cleaned = logic_code.strip()
    if cleaned.startswith("[") and cleaned.endswith("]"):
        cleaned = cleaned[1:-1].strip()

    parts = [part.strip() for part in cleaned.split("|")]
    if len(parts) < 2:
        return None

    kind = parts[0].upper()
    message = ((reminder or {}).get("message") or "Lembrete").strip()
    tz_name = _get_user_timezone(profile)

    if kind == "LU":
        run_at_local = _to_datetime(parts[1])
        if not run_at_local:
            return None
        run_at_utc = _local_to_utc_naive(run_at_local, tz_name)
        return {
            "kind": "LU",
            "message": message,
            "schedule_code": cleaned,
            "recurrence_rule": None,
            "timezone": tz_name,
            "next_run_at": run_at_utc.strftime("%Y-%m-%d %H:%M:%S"),
            "display_run_at": run_at_local.strftime("%Y-%m-%d %H:%M:%S"),
        }

    if kind == "LR" and len(parts) >= 3:
        if not re.match(r"^\d{2}:\d{2}$", parts[1]):
            return None
        recurrence_rule = parts[2].upper()
        next_run_local = None
        if recurrence_rule == "DAILY":
            next_run_local = _next_daily_run(parts[1], tz_name)
        elif recurrence_rule.startswith("WEEKLY:"):
            next_run_local = _next_weekly_run(parts[1], recurrence_rule.split(":", 1)[1], tz_name)
        else:
            return None
        if not next_run_local:
            return None
        next_run_utc = _local_to_utc_naive(next_run_local, tz_name)
        return {
            "kind": "LR",
            "message": message,
            "schedule_code": cleaned,
            "recurrence_rule": recurrence_rule,
            "timezone": tz_name,
            "next_run_at": next_run_utc.strftime("%Y-%m-%d %H:%M:%S"),
            "display_run_at": next_run_local.strftime("%Y-%m-%d %H:%M:%S"),
        }

    return None


async def _handle_reminder_menu_action(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    text: str,
) -> bool:
    match = re.match(r"^(?:(apagar|deletar|mudar|modificar)\s+)?(\d+)$", text.strip().lower())
    if not match:
        return False

    action = match.group(1)
    index = int(match.group(2)) - 1
    ids = context.user_data.get("lista_lembretes_recente") or []

    if not ids:
        await update.message.reply_text(
            "Não tenho uma lista recente de lembretes. Use /lembretes primeiro."
        )
        return True

    if index < 0 or index >= len(ids):
        await update.message.reply_text(
            "Número inválido. Use /lembretes para ver a lista atualizada."
        )
        return True

    task_id = ids[index]

    if not action:
        await update.message.reply_text(
            f"Você escolheu o lembrete {index + 1}.\n"
            f"Agora digite `apagar {index + 1}` ou `mudar {index + 1}`.",
            parse_mode="Markdown",
        )
        return True

    if action in {"apagar", "deletar"}:
        deleted = deactivate_reminder_task(chat_id, task_id)
        if not deleted:
            await update.message.reply_text(
                "Não consegui apagar esse lembrete. Use /lembretes e tente novamente."
            )
            return True

        new_ids = [rid for rid in ids if rid != task_id]
        if new_ids:
            context.user_data["lista_lembretes_recente"] = new_ids
        else:
            context.user_data.pop("lista_lembretes_recente", None)

        await update.message.reply_text("✅ Lembrete removido com sucesso!")
        return True

    if action in {"mudar", "modificar"}:
        context.user_data["awaiting"] = "edit_reminder_schedule"
        context.user_data["editing_task_id"] = task_id
        await update.message.reply_text(
            "Perfeito. Me diga como você quer alterar esse lembrete.\n"
            "Exemplo: `quero todo dia às 19:00` ou `mudar para segunda e sexta às 08:30`.",
            parse_mode="Markdown",
        )
        return True

    return False


def _fallback_logic_from_reminder(reminder: dict | None) -> str | None:
    remind_at = (reminder or {}).get("remind_at")
    if not isinstance(remind_at, str) or not remind_at.strip():
        return None
    iso = remind_at.strip().replace(" ", "T")
    return f"[LU|{iso}]"


def _logic_from_informal_text(user_text: str, current_task: dict | None, profile: dict | None) -> str | None:
    text = (user_text or "").strip().lower()
    tz_name = _get_user_timezone(profile)
    now_local = datetime.now(ZoneInfo(tz_name)).replace(second=0, microsecond=0)

    rel = re.search(r"(?:daqui\s*(?:a\s*)?|a\s*partir\s*de\s*agora\s*)(\d+)\s*(minuto|minutos|min|hora|horas|h)\b", text)
    if rel:
        amount = int(rel.group(1))
        unit = rel.group(2)
        delta = timedelta(hours=amount) if unit.startswith("h") or "hora" in unit else timedelta(minutes=amount)
        target = now_local + delta
        return f"[LU|{target.strftime('%Y-%m-%dT%H:%M:%S')}]"

    abs_match = re.search(r"(?:às|as)?\s*(\d{1,2})[:h](\d{2})\b", text)
    if abs_match:
        hour = int(abs_match.group(1))
        minute = int(abs_match.group(2))
        if hour > 23 or minute > 59:
            return None

        if (current_task or {}).get("kind") == "LR":
            recurrence = str((current_task or {}).get("recurrence_rule") or "DAILY").upper()
            if recurrence != "DAILY" and not recurrence.startswith("WEEKLY:"):
                recurrence = "DAILY"
            return f"[LR|{hour:02d}:{minute:02d}|{recurrence}]"

        target = now_local.replace(hour=hour, minute=minute)
        if target <= now_local:
            target = target + timedelta(days=1)
        return f"[LU|{target.strftime('%Y-%m-%dT%H:%M:%S')}]"

    return None


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = update.message.text.strip()
        chat_id = update.effective_chat.id
        _remember_chat_message(context, update.message.message_id)
        awaiting = context.user_data.get("awaiting")
        usuario = None
        user_id = None

        # Fluxo de transferência de almoço
        lunch_flow = context.user_data.get("lunch_flow")
        if lunch_flow:
            from bot.lunch_transfer import handle_lunch_message
            await handle_lunch_message(update, context)
            return

        # Fluxo modo desenvolvedor: aceita respostas do usuário, grava em quarentena e envia próximo prompt
        if awaiting == "dev_reply":
            import random
            from ai.treino_quarentena import salvar_treino_quarentena

            prompts = context.user_data.get("dev_prompts") or []
            current = context.user_data.get("dev_current_prompt") or (prompts[0] if prompts else None)
            if not current:
                context.user_data.pop("awaiting", None)
                await update.message.reply_text("Modo desenvolvedor encerrado. Use /desenvolvedor para recomeçar.")
                return

            # Salva a resposta do usuário em quarentena para revisão manual posterior
            try:
                metadata = {
                    "chat_id": update.effective_chat.id,
                    "username": getattr(update.effective_user, "username", None),
                }
                salvar_treino_quarentena(current, text, metadata=metadata)
            except Exception:
                logger.exception("Falha ao salvar treino na quarentena.")

            candidates = prompts[1:] if len(prompts) > 1 else prompts
            next_prompt = random.choice(candidates) if candidates else prompts[0]
            context.user_data["dev_current_prompt"] = next_prompt
            await update.message.reply_text("Boa! Agora tenta essa aqui:")
            await update.message.reply_text(next_prompt)
            return

        # Modo anônimo: encaminha a mensagem para a IA externa sem tocar no banco
        if context.user_data.get("status") == "anonimo":
            from ai.anon_client import send_anonymous_to_brain

            offline_text = (
                "Parece que o ChatBot está desativado no momento. "
                "Use /desenvolvedor para treinar a IA ou /start para voltar ao menu inicial."
            )

            aguarde = await update.message.reply_text("✍️ Enviando ao modo anônimo...")
            _remember_chat_message(context, aguarde.message_id)
            try:
                reply = await asyncio.wait_for(send_anonymous_to_brain(text), timeout=30)
            except asyncio.TimeoutError:
                context.user_data.pop("awaiting", None)
                await _safe_edit(aguarde, offline_text)
                return
            except Exception:
                context.user_data.pop("awaiting", None)
                await _safe_edit(aguarde, offline_text)
                return

            if not reply:
                context.user_data.pop("awaiting", None)
                await _safe_edit(aguarde, offline_text)
            else:
                await _safe_edit(aguarde, reply)
            return

        if awaiting in {"edit_reminder_schedule", "ia_model", "report_issue", "report_name", "ru_cpf", "ru_senha", "ru_select_days", "ru_reservar_agora"}:
            usuario = get_usuario(chat_id)
            if not usuario or not usuario["logado"]:
                context.user_data.pop("awaiting", None)
                context.user_data.pop("editing_task_id", None)
                context.user_data.pop("report_draft", None)
                await update.message.reply_text(
                    "👋 Sua sessão expirou. Faça login novamente com /login."
                )
                return
            user_id = usuario["chat_id"]

        if awaiting == "clean_confirm":
            answer = (text or "").strip().lower()
            if answer in {"sim", "s", "yes", "y"}:
                deleted = await _cleanup_chat_messages(context, context.bot, chat_id)
                context.user_data.pop("awaiting", None)
                await update.message.reply_text(
                    f"✅ Pronto. Limpei as mensagens desta conversa no Telegram ({deleted} mensagens removidas quando possível).\n\n"
                    "Nada foi apagado do banco."
                )
                return
            if answer in {"não", "nao", "n", "no"}:
                context.user_data.pop("awaiting", None)
                await update.message.reply_text(
                    "Tudo bem. Não limpei nada. Se mudar de ideia, use /clean novamente."
                )
                return

            await update.message.reply_text(
                "Responda com sim ou não.\n"
                "Se quiser limpar só as mensagens do Telegram, diga sim."
            )
            return

        if awaiting == "report_issue":
            aguarde = await update.message.reply_text("✍️ Analisando seu relato...")
            _remember_chat_message(context, aguarde.message_id)
            try:
                profile = get_profile(user_id)
                ai_reply = process_report_issue(text, profile)
            except Exception:
                logger.exception("Falha ao processar relato com IA.")
                ai_reply = (
                    "Obrigado por ajudar a manter a comunidade em pé. "
                    "Digite na próxima mensagem qual seu nome; se preferir, pode enviar '...' para ficar anônimo."
                )

            context.user_data["report_draft"] = {
                "issue": text,
                "ai_reply": ai_reply,
            }
            context.user_data["awaiting"] = "report_name"
            await _safe_edit(aguarde, ai_reply)
            await update.message.reply_text(
                "Obrigado por ajudar a manter a comunidade em pé!!!\n"
                "Digite na próxima mensagem qual seu nome, se preferir pode adicionar um '...' para enviar como anônimo."
            )
            return

        if awaiting == "report_name":
            report_draft = context.user_data.get("report_draft") or {}
            issue = report_draft.get("issue")
            ai_reply = report_draft.get("ai_reply")
            if not issue or not ai_reply:
                context.user_data.pop("awaiting", None)
                context.user_data.pop("report_draft", None)
                await update.message.reply_text(
                    "Não encontrei o relato anterior. Use /reportar novamente para começar."
                )
                return

            reporter_name, anonymous = _normalize_reporter_name(text)
            try:
                save_report(user_id, issue, ai_reply, reporter_name, anonymous)
            except Exception:
                logger.exception("Falha ao salvar report.")
                await update.message.reply_text(
                    "⚠️ Não consegui salvar seu relato agora. Tente novamente em instantes."
                )
                return

            context.user_data.pop("awaiting", None)
            context.user_data.pop("report_draft", None)
            if anonymous:
                await update.message.reply_text(
                    "✅ Relato registrado como anônimo. Obrigado por ajudar a manter a comunidade em pé!"
                )
            else:
                await update.message.reply_text(
                    f"✅ Relato registrado, {reporter_name}. Obrigado por ajudar a manter a comunidade em pé!"
                )
            return

        if awaiting == "edit_reminder_schedule":
            task_id = context.user_data.get("editing_task_id")
            if not task_id:
                context.user_data.pop("awaiting", None)
                await update.message.reply_text(
                    "Não encontrei o lembrete em edição. Use /lembretes novamente."
                )
                return

            aguarde = await update.message.reply_text("✍️ Ajustando lembrete...")
            _remember_chat_message(context, aguarde.message_id)
            try:
                profile = get_profile(user_id)
                history = get_history(user_id)
                result = process_message(text, history, profile)
            except Exception:
                logger.exception("Falha ao processar edição de lembrete com IA.")
                await _safe_edit(
                    aguarde,
                    "⚠️ Não consegui processar a alteração agora. Tente novamente em instantes.",
                )
                return

            current_task = get_reminder_task_by_id(user_id, task_id)
            if not current_task:
                context.user_data.pop("awaiting", None)
                context.user_data.pop("editing_task_id", None)
                await _safe_edit(
                    aguarde,
                    "Não achei esse lembrete. Use /lembretes para recarregar sua lista.",
                )
                return

            reminder = result.get("reminder") or {}
            if not reminder.get("message"):
                reminder["message"] = current_task["message"]

            logic_code = result.get("logic_code")
            if not isinstance(logic_code, str):
                logic_code = None
            if not logic_code:
                logic_code = _fallback_logic_from_reminder(result.get("reminder"))
            if not logic_code:
                logic_code = _logic_from_informal_text(text, current_task, profile)

            translated = _translate_logic_code(logic_code, reminder, profile)
            if not translated:
                await _safe_edit(
                    aguarde,
                    "Não consegui entender o novo formato desse lembrete.\n"
                    "Tente algo como: `todo dia às 19:00`, `segunda e sexta às 08:30` ou `daqui a 15 minutos`.",
                )
                return

            changed = update_reminder_task_schedule(
                user_id=user_id,
                task_id=task_id,
                kind=translated["kind"],
                message=translated["message"],
                schedule_code=translated["schedule_code"],
                recurrence_rule=translated["recurrence_rule"],
                timezone_name=translated["timezone"],
                next_run_at=translated["next_run_at"],
            )
            if not changed:
                await _safe_edit(
                    aguarde,
                    "Não consegui atualizar esse lembrete agora. Tente de novo com /lembretes.",
                )
                return

            context.user_data.pop("awaiting", None)
            context.user_data.pop("editing_task_id", None)
            await _safe_edit(
                aguarde,
                "✅ Lembrete atualizado com sucesso!\n"
                f"Novo horário: *{translated['display_run_at']}* ({translated['timezone']}).",
                parse_mode="Markdown",
            )
            return

        if awaiting == "ia_model":
            selected_model = resolve_ai_model_choice(text)
            if not selected_model:
                await update.message.reply_text(
                    "❌ Opção inválida. Responda com 1, 2, 3 ou 4.\n"
                    "Exemplos válidos: 1, 2, 3, 4, gemini-2.0-flash"
                )
                return
            upsert_profile(user_id, "ai_model", selected_model)
            context.user_data.pop("awaiting", None)
            await update.message.reply_text(
                f"✅ Modelo da sua conta atualizado para: {selected_model}."
            )
            return

        if awaiting == "ru_cpf":
            raw = text.strip()
            # aceita "CPF:12345678901" ou "CPF: 12345678901"
            if ":" in raw and raw.upper().startswith("CPF"):
                cpf = raw.split(":", 1)[1].strip().replace(".", "").replace("-", "")
            else:
                cpf = raw.replace(".", "").replace("-", "")

            if not cpf.isdigit() or len(cpf) != 11:
                await update.message.reply_text(
                    "❌ CPF inválido. Envie exatamente 11 dígitos, sem pontos ou traços.\n"
                    "Exemplo: `CPF:12345678901`",
                    parse_mode="Markdown",
                )
                return

            context.user_data["ru_cpf_tmp"] = cpf
            context.user_data["awaiting"] = "ru_senha"
            await update.message.reply_text(
                "✅ CPF recebido!\n\n"
                "Agora envie sua senha do portal IFFar no formato:\n"
                "`SENHA:suasenha`\n\n"
                "Ou envie /cancelar para sair.",
                parse_mode="Markdown",
            )
            return

        if awaiting == "ru_senha":
            from database.queries import save_ru_credentials
            from ru.credentials import encrypt

            raw = text.strip()
            if ":" in raw and raw.upper().startswith("SENHA"):
                senha = raw.split(":", 1)[1].strip()
            else:
                senha = raw

            if not senha:
                await update.message.reply_text(
                    "❌ Senha não pode ser vazia. Tente novamente:\n`SENHA:suasenha`",
                    parse_mode="Markdown",
                )
                return

            cpf = context.user_data.pop("ru_cpf_tmp", None)
            if not cpf:
                context.user_data.pop("awaiting", None)
                await update.message.reply_text(
                    "❌ Sessão expirou. Use /modo para começar novamente."
                )
                return

            try:
                cpf_enc = encrypt(cpf)
                senha_enc = encrypt(senha)
                save_ru_credentials(user_id, cpf_enc, senha_enc)
            except Exception:
                logger.exception("Falha ao salvar credenciais do RU.")
                await update.message.reply_text(
                    "⚠️ Não consegui salvar suas credenciais. Tente novamente."
                )
                return

            context.user_data.pop("awaiting", None)
            context.user_data.pop("ru_user_id", None)
            context.user_data["ru_cpf_dec"] = cpf
            context.user_data["ru_senha_dec"] = senha
            await update.message.reply_text(
                "✅ *Credenciais do RU salvas com segurança!*\n\n"
                "Seu CPF e senha estão criptografados e vinculados apenas à sua conta.\n\n"
                "Quer reservar o almoço agora? Responda *sim* para entrar no sistema e ver os dias disponíveis, "
                "ou *não* para sair.",
                parse_mode="Markdown",
            )
            context.user_data["awaiting"] = "ru_reservar_agora"
            return

        if awaiting == "ru_reservar_agora":
            resp = text.strip().lower()
            if resp in {"sim", "s", "yes", "y"}:
                from ru.booking import login_and_get_days
                cpf = context.user_data.pop("ru_cpf_dec", None)
                senha = context.user_data.pop("ru_senha_dec", None)
                if not cpf or not senha:
                    context.user_data.pop("awaiting", None)
                    await update.message.reply_text("❌ Sessão expirou. Use /modo para começar novamente.")
                    return
                aguarde = await update.message.reply_text("⏳ Entrando no sistema do RU, aguarde...")
                try:
                    result = await login_and_get_days(cpf, senha)
                except Exception:
                    logger.exception("Falha ao acessar o RU.")
                    await _safe_edit(aguarde, "⚠️ Erro ao acessar o sistema do RU. Tente novamente mais tarde.")
                    context.user_data.pop("awaiting", None)
                    return

                if not result["success"]:
                    await _safe_edit(
                        aguarde,
                        f"❌ Não consegui entrar no sistema do RU.\n\nMotivo: {result['error']}"
                    )
                    context.user_data.pop("awaiting", None)
                    return

                raw_days = result["raw_days"]
                if not raw_days:
                    await _safe_edit(
                        aguarde,
                        "✅ Entrei com sucesso!\n\nNão há dias disponíveis para agendamento no momento."
                    )
                    context.user_data.pop("awaiting", None)
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

                await _safe_edit(aguarde, msg, parse_mode="Markdown")
                return
            else:
                context.user_data.pop("awaiting", None)
                context.user_data.pop("ru_cpf_dec", None)
                context.user_data.pop("ru_senha_dec", None)
                await update.message.reply_text(
                    "Tudo bem! Quando quiser reservar, use /modo → Reservar Almoço."
                )
                return

        if awaiting == "ru_select_days":
            from ru.booking import book_days as ru_book_days
            raw_days = context.user_data.get("ru_available_days") or []
            cpf = context.user_data.get("ru_cpf_dec")
            senha = context.user_data.get("ru_senha_dec")

            if not raw_days or not cpf or not senha:
                context.user_data.pop("awaiting", None)
                await update.message.reply_text("❌ Sessão expirou. Use /modo → Reservar Almoço novamente.")
                return

            # Parse selection
            raw_txt = text.strip().lower()
            if raw_txt in {"todos", "all", "tudo"}:
                chosen = list(range(len(raw_days)))
            else:
                chosen = []
                for token in re.split(r"[,\s]+", raw_txt):
                    token = token.strip()
                    if token.isdigit():
                        idx = int(token) - 1
                        if 0 <= idx < len(raw_days):
                            chosen.append(idx)

            if not chosen:
                await update.message.reply_text(
                    "❌ Não entendi sua seleção.\n"
                    "Diga *todos* ou cite os números dos dias: `1, 2, 3`",
                    parse_mode="Markdown",
                )
                return

            selected_values = [raw_days[i]["value"] for i in chosen]
            selected_labels = [raw_days[i]["label"] for i in chosen]

            aguarde = await update.message.reply_text(
                f"⏳ Agendando {len(selected_values)} dia(s)..."
            )
            try:
                result = await ru_book_days(cpf, senha, selected_values)
            except Exception:
                logger.exception("Falha ao reservar dias no RU.")
                await _safe_edit(aguarde, "⚠️ Erro ao reservar. Tente novamente.")
                return
            finally:
                context.user_data.pop("awaiting", None)
                context.user_data.pop("ru_available_days", None)
                context.user_data.pop("ru_cpf_dec", None)
                context.user_data.pop("ru_senha_dec", None)

            if not result["success"]:
                await _safe_edit(aguarde, f"❌ Erro ao reservar: {result.get('error', 'desconhecido')}")
                return

            booked_labels = selected_labels[: len(result["booked"])]
            failed_count = len(result.get("failed") or [])
            txt = "✅ *Agendamento concluído!*\n\n"
            if booked_labels:
                txt += "Dias reservados:\n" + "\n".join(f"• {l}" for l in booked_labels)
            if failed_count:
                txt += f"\n\n⚠️ {failed_count} dia(s) não puderam ser agendados (talvez já reservados ou indisponíveis)."
            await _safe_edit(aguarde, txt, parse_mode="Markdown")
            return

        # ── Fluxo de formulário (login ou cadastro) ───────────
        if text.startswith("E-mail:") and "Senha:" in text:
            if awaiting == "cadastrar":
                await _processar_cadastro(update, context, chat_id, text)
            elif awaiting == "login":
                await _processar_login(update, context, chat_id, text)
            else:
                await update.message.reply_text(
                    "Use /login para entrar ou /cadastrar para criar sua conta." + MSG_GITHUB
                )
            return

        # ── Barreira de acesso ────────────────────────────────
        try:
            usuario = get_usuario(chat_id)
        except Exception:
            logger.exception("Falha ao consultar usuario no banco.")
            await update.message.reply_text(
                "⚠️ Não consegui verificar seu login agora. Tente novamente."
            )
            return

        if not usuario or not usuario["logado"]:
            await update.message.reply_text(
                "👋 Para conversar comigo você precisa estar logado.\n\n"
                "👉 Digite /login para entrar ou /cadastrar para criar sua conta."
                + MSG_GITHUB
            )
            return

        user_id = usuario["chat_id"]

        handled_menu_action = await _handle_reminder_menu_action(update, context, user_id, text)
        if handled_menu_action:
            return

        if context.chat_data.get("ai_processing"):
            try:
                save_message(user_id, "user", text)
            except Exception:
                logger.exception("Falha ao salvar mensagem durante processamento em andamento.")

            wait_text = "⏳ Ainda estou finalizando seu pedido anterior. Aguarde alguns segundos e tente novamente."
            aviso = await update.message.reply_text(
                wait_text
            )
            _remember_chat_message(context, aviso.message_id)
            try:
                save_message(user_id, "assistant", wait_text)
            except Exception:
                logger.exception("Falha ao salvar aviso de processamento em andamento.")
            return

        context.chat_data["ai_processing"] = True

        # Persiste a mensagem do usuário antes da chamada da IA para não perder histórico
        # em caso de timeout, falha externa ou cancelamento do processamento.
        try:
            save_message(user_id, "user", text)
        except Exception:
            logger.exception("Falha ao salvar mensagem do usuário no histórico.")

        # ── Conversa com IA ───────────────────────────────────
        aguarde = await update.message.reply_text("✍️ Cozinhando.")
        _remember_chat_message(context, aguarde.message_id)

        thinking_stop = asyncio.Event()
        thinking_task = asyncio.create_task(_animate_waiting_message(aguarde, thinking_stop))

        try:
            history = get_history(user_id)
            profile = get_profile(user_id)

            process_task = asyncio.create_task(asyncio.to_thread(process_message, text, history, profile))

            try:
                await asyncio.wait_for(asyncio.shield(process_task), timeout=_THINKING_SLOW_LIMIT_SECONDS)
            except asyncio.TimeoutError:
                thinking_stop.set()
                with suppress(BaseException):
                    await thinking_task

                await _safe_edit(aguarde, _THINKING_SLOW_TEXT)

                try:
                    await asyncio.wait_for(
                        asyncio.shield(process_task),
                        timeout=_THINKING_CANCEL_LIMIT_SECONDS - _THINKING_SLOW_LIMIT_SECONDS,
                    )
                except asyncio.TimeoutError:
                    process_task.cancel()
                    await _safe_edit(aguarde, _THINKING_TIMEOUT_TEXT)
                    try:
                        save_message(user_id, "assistant", _THINKING_TIMEOUT_TEXT)
                    except Exception:
                        logger.exception("Falha ao salvar timeout no histórico.")
                    return

            result = process_task.result()

            thinking_stop.set()
            if not thinking_task.done():
                thinking_task.cancel()
                with suppress(BaseException):
                    await thinking_task
        except Exception:
            logger.exception("Falha na chamada ao Gemini.")
            error_text = "⚠️ Erro ao processar sua mensagem. Tente novamente."
            await _safe_edit(aguarde, error_text)
            try:
                save_message(user_id, "assistant", error_text)
            except Exception:
                logger.exception("Falha ao salvar erro no histórico.")
            return
        finally:
            thinking_stop.set()
            if not thinking_task.done():
                thinking_task.cancel()
                with suppress(BaseException):
                    await thinking_task
            context.chat_data["ai_processing"] = False

        # Salva resposta da IA no histórico
        try:
            save_message(user_id, "assistant", result["reply"])
        except Exception:
            logger.exception("Falha ao salvar resposta no histórico.")

        # Salva atualizações de perfil detectadas pela IA
        for update_item in result.get("profile_updates") or []:
            try:
                upsert_profile(user_id, update_item["key"], update_item["value"])
            except Exception:
                logger.exception("Falha ao salvar perfil.")

        # Salva lembrete se detectado
        reminder = result.get("reminder")
        logic_code = result.get("logic_code")

        saved_task = None

        if logic_code:
            task = _translate_logic_code(logic_code, reminder, profile)
            if task:
                try:
                    save_reminder_task(
                        user_id=user_id,
                        kind=task["kind"],
                        message=task["message"],
                        schedule_code=task["schedule_code"],
                        recurrence_rule=task["recurrence_rule"],
                        next_run_at=task["next_run_at"],
                        timezone=task["timezone"],
                    )
                    saved_task = task
                except Exception:
                    logger.exception("Falha ao salvar reminder_tasks.")

        if not saved_task and reminder:
            try:
                fallback_logic = _fallback_logic_from_reminder(reminder)
                task = _translate_logic_code(fallback_logic, reminder, profile) if fallback_logic else None
                if not task:
                    raise ValueError("não foi possível converter reminder em reminder_task")
                save_reminder_task(
                    user_id=user_id,
                    kind=task["kind"],
                    message=task["message"],
                    schedule_code=task["schedule_code"],
                    recurrence_rule=task["recurrence_rule"],
                    next_run_at=task["next_run_at"],
                    timezone=task["timezone"],
                )
                saved_task = task
            except Exception:
                logger.exception("Falha ao salvar lembrete.")

        if saved_task:
            tipo = "recorrente" if saved_task["kind"] == "LR" else "único"
            resposta = (
                f"{result['reply']}\n\n"
                f"✅ Lembrete {tipo} salvo para *{saved_task['display_run_at']}* ({saved_task['timezone']})."
            )
            await _safe_edit(aguarde, resposta, parse_mode="Markdown")
        elif reminder:
            await _safe_edit(
                aguarde,
                result["reply"] + "\n\n⚠️ Não consegui salvar o lembrete. Tente novamente.",
            )
        else:
            await _safe_edit(aguarde, result["reply"])

    except Exception:
        logger.exception("Erro inesperado no fluxo de mensagem.")
        if update.message:
            await update.message.reply_text(
                "⚠️ Ocorreu um erro inesperado. Tente novamente."
            )


async def _processar_cadastro(update: Update, context, chat_id: int, text: str):
    parsed = _parse_form(text)
    if not parsed:
        await update.message.reply_text(
            "❌ Formato inválido. Copie exatamente como mostrado e preencha:\n\n"
            "E-mail: seuemail@exemplo.com\nSenha: suasenha"
        )
        return

    email, senha = parsed
    try:
        criar_usuario(chat_id, email, _hash(senha))
        context.user_data.pop("awaiting", None)
        await update.message.reply_text(
            "✅ Conta criada e sessão iniciada!\n\n"
            "Agora você pode conversar comigo, pedir lembretes e muito mais.\n"
            "Tente me contar algo sobre você ou peça um lembrete! 😊" + MSG_GITHUB
        )
    except Exception as e:
        if "Duplicate entry" in str(e) and "email" in str(e):
            await update.message.reply_text(
                "❌ Esse e-mail já está cadastrado.\n"
                "Use /login para entrar ou use um e-mail diferente."
            )
        else:
            logger.exception("Falha ao criar usuario.")
            await update.message.reply_text(
                "❌ Erro ao criar conta. Tente novamente."
            )


async def _processar_login(update: Update, context, chat_id: int, text: str):
    parsed = _parse_form(text)
    if not parsed:
        await update.message.reply_text(
            "❌ Formato inválido. Copie exatamente como mostrado e preencha:\n\n"
            "E-mail: seuemail@exemplo.com\nSenha: suasenha"
        )
        return

    email, senha = parsed

    # Verifica se o e-mail existe antes de checar a senha (melhor feedback)
    if not email_existe(email):
        await update.message.reply_text(
            "❌ Essa conta ainda não existe.\n"
            "Use /cadastrar para criar uma nova conta."
        )
        return

    usuario = verificar_login(email, _hash(senha))
    if not usuario:
        await update.message.reply_text(
            "❌ Senha incorreta. Tente novamente ou recrie sua conta com /cadastrar."
        )
        return

    set_chat_session(chat_id, usuario["chat_id"])
    set_logado(usuario["chat_id"], True)
    context.user_data.pop("awaiting", None)
    await update.message.reply_text(
        "✅ Login realizado com sucesso! Bem-vindo(a) de volta! 😊\n\n"
        "Pode me mandar uma mensagem, pedir um lembrete ou contar novidades."
        + MSG_GITHUB
    )

    # Notifica lembretes que dispararam enquanto o usuário estava fora
    try:
        atrasados = get_overdue_reminder_tasks(usuario["chat_id"])
        if atrasados:
            linhas = "\n".join(f"• {t['message']}" for t in atrasados)
            await update.message.reply_text(
                f"⏰ Você tinha lembrete(s) enquanto estava fora:\n\n{linhas}\n\n"
                "Use /lembretes para ver todos os seus lembretes ativos."
            )
    except Exception:
        logger.exception("Falha ao verificar lembretes atrasados no login.")