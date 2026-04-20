import hashlib
import logging
from telegram import Update
from telegram.ext import ContextTypes

from bot.commands import MSG_GITHUB, resolve_ai_model_choice
from database.queries import (
    get_usuario,
    criar_usuario,
    verificar_login,
    email_existe,
    set_logado,
    save_reminder,
    save_message,
    get_history,
    get_profile,
    upsert_profile,
)
from ai.gemini import process_message

logger = logging.getLogger(__name__)


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


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = update.message.text.strip()
        chat_id = update.effective_chat.id
        awaiting = context.user_data.get("awaiting")

        if awaiting == "ia_model":
            selected_model = resolve_ai_model_choice(text)
            if not selected_model:
                await update.message.reply_text(
                    "❌ Opção inválida. Responda com 1, 2, 3 ou 4.\n"
                    "Exemplos válidos: 1, 2, 3, 4, gemini-2.0-flash"
                )
                return
            upsert_profile(chat_id, "ai_model", selected_model)
            context.user_data.pop("awaiting", None)
            await update.message.reply_text(
                f"✅ Modelo da sua conta atualizado para: {selected_model}."
            )
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

        # ── Conversa com IA ───────────────────────────────────
        aguarde = await update.message.reply_text("✍️ Pensando...")

        try:
            history = get_history(chat_id)
            profile = get_profile(chat_id)
            result = process_message(text, history, profile)
        except Exception:
            logger.exception("Falha na chamada ao Gemini.")
            await aguarde.edit_text("⚠️ Erro ao processar sua mensagem. Tente novamente.")
            return

        # Salva a troca no histórico
        try:
            save_message(chat_id, "user", text)
            save_message(chat_id, "assistant", result["reply"])
        except Exception:
            logger.exception("Falha ao salvar histórico.")

        # Salva atualizações de perfil detectadas pela IA
        for update_item in result.get("profile_updates") or []:
            try:
                upsert_profile(chat_id, update_item["key"], update_item["value"])
            except Exception:
                logger.exception("Falha ao salvar perfil.")

        # Salva lembrete se detectado
        reminder = result.get("reminder")
        if reminder:
            try:
                save_reminder(chat_id, reminder["message"], reminder["remind_at"])
                resposta = f"{result['reply']}\n\n✅ Lembrete salvo para *{reminder['remind_at']}*."
                await aguarde.edit_text(resposta, parse_mode="Markdown")
            except Exception:
                logger.exception("Falha ao salvar lembrete.")
                await aguarde.edit_text(
                    result["reply"] + "\n\n⚠️ Não consegui salvar o lembrete. Tente novamente."
                )
        else:
            await aguarde.edit_text(result["reply"])

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

    # Garante login no chat atual e encerra eventual sessão antiga do mesmo e-mail.
    if usuario["chat_id"] != chat_id:
        set_logado(usuario["chat_id"], False)
    set_logado(chat_id, True)
    context.user_data.pop("awaiting", None)
    await update.message.reply_text(
        "✅ Login realizado com sucesso! Bem-vindo(a) de volta! 😊\n\n"
        "Pode me mandar uma mensagem, pedir um lembrete ou contar novidades."
        + MSG_GITHUB
    )
