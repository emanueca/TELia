import hashlib
import logging
from telegram import Update
from telegram.ext import ContextTypes

from bot.commands import MSG_GITHUB
from database.queries import get_usuario, criar_usuario, save_reminder
from ai.gemini import extract_reminder


logger = logging.getLogger(__name__)


def gerar_hash_senha(senha_plana: str) -> str:
    return hashlib.sha256(senha_plana.encode("utf-8")).hexdigest()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = update.message.text.strip()
        chat_id = update.effective_chat.id

        # ── Fluxo de cadastro ─────────────────────────────────
        if text.startswith("E-mail:") and "Senha:" in text:
            await _processar_cadastro(update, chat_id, text)
            return

        # ── Barreira de acesso ────────────────────────────────
        try:
            usuario = get_usuario(chat_id)
        except Exception:
            logger.exception("Falha ao consultar usuario no banco.")
            await update.message.reply_text(
                "⚠️ Não consegui verificar seu login agora. Tente novamente em instantes."
            )
            return

        if not usuario or not usuario["logado"]:
            await update.message.reply_text(
                "👋 Olá! Para eu salvar seus lembretes, você precisa estar logado.\n\n"
                "👉 Digite /login para entrar ou /cadastrar para criar sua conta."
                + MSG_GITHUB
            )
            return

        # ── Lógica principal: extração de lembrete via IA ─────
        mensagem_aguarde = await update.message.reply_text("Processando seu lembrete...")

        try:
            result = extract_reminder(text)
        except Exception:
            logger.exception("Falha ao extrair lembrete com IA.")
            await mensagem_aguarde.edit_text(
                "⚠️ Tive um erro ao processar sua mensagem agora. Tente novamente."
            )
            return

        if not result:
            await mensagem_aguarde.edit_text(
                "Não consegui identificar um lembrete. Tente algo como:\n"
                "_'Me lembra de beber água amanhã às 10h'_",
                parse_mode="Markdown",
            )
            return

        try:
            save_reminder(chat_id, result["message"], result["remind_at"])
        except Exception:
            logger.exception("Falha ao salvar lembrete no banco.")
            await mensagem_aguarde.edit_text(
                "⚠️ Não consegui salvar seu lembrete agora. "
                "Use /login novamente e tente mais uma vez."
            )
            return

        await mensagem_aguarde.edit_text(
            f"✅ Lembrete salvo! Vou te avisar sobre *{result['message']}* em {result['remind_at']}.",
            parse_mode="Markdown",
        )
    except Exception:
        logger.exception("Erro inesperado no fluxo de mensagem.")
        if update.message:
            await update.message.reply_text(
                "⚠️ Ocorreu um erro inesperado. Tente novamente em alguns segundos."
            )

async def _processar_cadastro(update: Update, chat_id: int, text: str):
    try:
        linhas = text.split("\n")
        email = linhas[0].split(":", 1)[1].strip()
        senha_plana = linhas[1].split(":", 1)[1].strip()

        if not email or not senha_plana:
            raise ValueError("campos vazios")

        senha_hash = gerar_hash_senha(senha_plana)
        criar_usuario(chat_id, email, senha_hash)

        await update.message.reply_text(
            "✅ Cadastro realizado com sucesso! Já pode me pedir lembretes." + MSG_GITHUB
        )
    except Exception:
        await update.message.reply_text(
            "❌ Formato inválido. Copie exatamente como mostrado e preencha:\n\n"
            "E-mail: seuemail@exemplo.com\nSenha: suasenha"
        )
